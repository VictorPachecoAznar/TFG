from apb_spatial_computer_vision import DATA_DIR, DUCKDB, OUT_DIR, duckdb
from apb_spatial_computer_vision.raster_utilities import Ortophoto,folder_check

from concurrent.futures import ProcessPoolExecutor

import os
import geopandas as gpd, pandas as pd, numpy as np
import time
from functools import partial
from collections import ChainMap
from collections.abc import Iterable
from apb_spatial_computer_vision.lang_sam_utilities import LangSAM_apb
from apb_spatial_computer_vision.sam_utilities import SamGeo_apb

def choose_model(name):
    #CREAR DATASET
    pass

def prediction_to_bbox(gdf: gpd.GeoDataFrame, crs=25831):
    """Generates the oriented envelope of a geodataframe

    Args:
        gdf (gpd.GeoDataFrame): Polygon geometry
        crs (int, optional):  CRS as EPSG code. Defaults to 25831.

    Returns:
        gpd.GeoDataFrame: Rotated envelope geometry
    """
    wkts=[g.boundary.oriented_envelope.wkt for g in gdf.geometry]
    #nl= [x for xs in li for x in xs]
    newgdf=gpd.GeoDataFrame(gdf,geometry=gpd.GeoSeries.from_wkt(wkts),crs=crs)
    return newgdf

def read_file(paths,DUCKDB=DUCKDB,layer=None):
    """Geospatial data reader for DuckDB

    Args:
        paths (Iterable | str): Path/s to the file/s
        DUCKDB (duckdb.DuckDBPyConnection, optional): Defaults to DUCKDB (environment variable).

    Returns:
        duckdb.DuckDBPyRelation: Table containing the elements
    """
    if isinstance(paths,str):
        if layer is None:
            command=f'''SELECT *
                FROM ST_READ('{paths}')'''
        elif isinstance(layer,str):
            command=f'''SELECT *
            FROM ST_READ('{paths}',layer="{layer}")'''
            
    elif isinstance(paths,Iterable):
        if layer is None:
            command = " UNION ALL ".join(
                [f"SELECT *  FROM st_read('{path}')" for path in paths]
                                )
        elif isinstance(layer,str):
            command = " UNION ALL ".join(
                [f"SELECT *  FROM st_read('{path}',layer='{layer}')" for path in paths]
                                )
        elif isinstance(layer,Iterable):
            command = " UNION ALL ".join(
                [f"SELECT *  FROM st_read('{path}',layer='{single_layer}')" for (path,single_layer) in zip(paths,layer)]
                                )
    else: 
        pass
    
    
    no_geometry_column_db=DUCKDB.sql(command)
    geometry_column=DUCKDB.sql(f'''SELECT column_name FROM (DESCRIBE no_geometry_column_db) WHERE column_type='GEOMETRY' ''').fetchdf()['column_name'][0]
    geometry_column_db=DUCKDB.sql(f'''SELECT *,{geometry_column} AS geom from no_geometry_column_db''')
    return geometry_column_db
    
    
def duckdb_2_gdf(tab: duckdb.DuckDBPyRelation,geometry_column,crs=25831):
    """Generates a GeoDataFrame from DuckDB

    Args:
        tab (duckdb.DuckDBPyRelation): Geospatial able to export from DUCKDB
        geometry_column (str): Name for the geometry column
        crs (int, optional):  CRS as EPSG code. Defaults to 25831.

    Returns:
        gpd.GeoDataFrame: Returngs the same data wiht 
    """
    temp='affected.csv'
    DUCKDB.sql(f'''COPY tab TO '{temp}' WITH (HEADER, DELIMITER ';')''')
    df=pd.read_csv(temp,sep=';')
    geodf=gpd.GeoDataFrame(df,geometry=gpd.GeoSeries.from_wkt(df[geometry_column]),crs=crs)
    geodf=geodf.drop(columns=[geometry_column])
    os.remove(temp)
    return geodf


def filter_level(detections,pyramid_dir,depths,geometry_column, segmentation_name):
    """Finds which elements are contained and limiting to each tile, prompting the creation of virtual layers

    Args:        
        detections (duckdb.DuckDBPyRelation): Table with the polygon geometries to be used as box prompts
        pyramid_dir (str): Path to the image pyramid
        depth (int): The level of the pyramid to be built.
        geometry_column (str): : Name for the geometry column.

    Returns:
        duckdb.DuckDBPyRelation: Contained geometries and their respective tile names
        duckdb.DuckDBPyRelation: Limit geometries and their respective virtual raster layer (GDAL VRT) tile names
    """
    command = " UNION ALL ".join(
            [f"SELECT *, '{depth}' depth  FROM st_read('{os.path.join(pyramid_dir,'vector',f'subset_{depth}.geojson')}')" for depth in depths])
                            
    tiles=DUCKDB.sql('CREATE TABLE IF NOT EXISTS tiles AS '+command)

    detections=detections.select('*')
    #CONNECT PREDICTION TO TILE
    extent_total=DUCKDB.sql('''
        SELECT ST_EXTENT_AGG(geom) geom
            from tiles t
            group by depth
                having depth=1''')
    
    detections=DUCKDB.sql(f'''
        SELECT ST_INTERSECTION(d.{geometry_column},e.geom) AS geom
            FROM detections d
                JOIN extent_total e
                on ST_intersects(d.{geometry_column},e.geom)''')


    intersection=DUCKDB.sql(
        f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.geom AS predict_geom
            FROM tiles t 
            JOIN detections g
                ON ST_INTERSECTS(t.geom,g.geom)''')
    
    within=DUCKDB.sql(
        f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.geom AS predict_geom
            FROM tiles t 
            JOIN detections g
                ON ST_CONTAINS(t.geom,g.geom)
                ''')
    
    contained=DUCKDB.sql(
        f'''SELECT t1.depth,t2.predict_geom geom,t1.NAME FROM within t1
         JOIN
            (SELECT MAX(depth) depth, w.predict_geom
               FROM within w
               GROUP BY w.predict_geom) t2
               ON t1.depth=t2.depth AND t1.predict_geom=t2.predict_geom
                ''')
    
    limiting=DUCKDB.sql(
        f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.geom AS predict_geom
                FROM tiles t 
                JOIN detections g
                    ON ST_INTERSECTS(t.geom,g.geom) AND NOT ST_CONTAINS(t.geom,g.geom)
                    WHERE predict_geom NOT IN (SELECT distinct geom FROM contained)''')
    
    affected=DUCKDB.sql(
        f'''SELECT t1.affected_tiles, t1.depth, t1.geom
            FROM (SELECT LIST(NAME) AS affected_tiles, count(depth),predict_geom as geom,depth
            FROM limiting
                group by predict_geom,depth
                having count(NAME) =2) t1
                JOIN(
                    SELECT MAX(depth) depth,geom
                    FROM (SELECT count(NAME) AS affected_tiles, count(depth),predict_geom as geom,depth
                            FROM limiting
                            group by predict_geom,depth
                            having count(NAME) =2)
                    group by geom) t2
        on t1.depth=t2.depth and t1.geom=t2.geom
                    ''')
    
    cleans=DUCKDB.sql(f'''SELECT DISTINCT affected_tiles AS unique_tiles
                      FROM affected''')
    
    DUCKDB.sql('CREATE TABLE IF NOT EXISTS mosaics (MOSAIC VARCHAR, geom GEOMETRY, affected_tiles VARCHAR[], depth INTEGER)')

    if len(cleans)>0:
        
        #CREATES INDICES TO NAME THE ELEMENTS OF THE VIRTUAL LAYERS
        cleans_indexed=DUCKDB.sql(f'''SELECT *,ROW_NUMBER() OVER (ORDER BY unique_tiles) AS row_index
                            FROM cleans
            ''')

        combi=DUCKDB.sql(
            """
            SELECT *
                FROM cleans_indexed c JOIN affected a
                    ON c.unique_tiles=a.affected_tiles
                            """)


        array=[i for i in cleans_indexed['unique_tiles'].fetchnumpy()['unique_tiles']]
        virtuals_dir=folder_check(os.path.join(os.path.dirname(pyramid_dir),f'virtuals_{segmentation_name}'))
        names=[os.path.join(virtuals_dir,str(i)) for i in range(1,len(cleans_indexed)+1)]

        with ProcessPoolExecutor(5) as Executor:
            mosaics=list(Executor.map(Ortophoto.mosaic_rasters,array,names))

        mosaic_index=[int(os.path.splitext(os.path.basename(i))[0]) for i in mosaics]

        mosaics_data=[{'MOSAIC':i,'INDEX':j} for (i,j) in zip(mosaics,mosaic_index)]
        mosaics_df=pd.DataFrame(mosaics_data)

        DUCKDB.sql(f''' 
            INSERT INTO mosaics(
                SELECT m.MOSAIC,c.geom, c.affected_tiles,c.depth
                    FROM mosaics_df m JOIN 
                        (SELECT u.row_index, a.geom, a.affected_tiles,depth
                            FROM cleans_indexed u JOIN affected a 
                                on a.affected_tiles=u.unique_tiles) c
                    ON m.INDEX=c.row_index)''')
        
    new_contained=DUCKDB.sql('''SELECT NAME,depth, geom
                                    FROM contained
                                        UNION 
                                    (SELECT MOSAIC, depth, geom FROM mosaics)''')
    return tiles, new_contained

def create_file_from_sql(table,column,name,file_name,crs):
    """Creates a GeoJSON file from an SQL projection ("SELECT" operation into a column)

    Args:
        table (duckdb.DuckDBPyRelation): Table to which the select operation will be applied to 
        column (str): The name of the column to filter by.
        name (str): The value to filter the column by.
        file_name (str): Output file name without extension. It will be stored as GeoJSON
        crs (str): CRS as EPSG code.

    """
    try:
        db=table.filter(f"{column}= '{name}'")

        DUCKDB.sql(f'''
        COPY db
        TO '{file_name}.geojson'
        WITH (FORMAT gdal, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES',SRS 'EPSG:{crs}');
        ''')
    except:
        pass

def create_files_from_sql(tab: duckdb.DuckDBPyRelation, column:str, tile_names: Iterable,file_names:Iterable,crs=25831):
    """ Creates multiple GeoJSON files from an SQL projection ("SELECT" operation into a column) for each tile name.
    Args:
        tab (duckdb.DuckDBPyRelation): Table to which the select operation will be applied to 
        column (str): The name of the column to filter by.
        tile_names (Iterable): Paths for each tile
        file_names (Iterable): Output file names without extension. They will be stored as GeoJSON
        crs (int, optional):  CRS as EPSG code. Defaults to 25831.
    """
    for (name,filename) in zip(tile_names,file_names):
        create_file_from_sql(tab,column,name,filename,crs)
        
def create_bboxes_sam(table: duckdb.DuckDBPyRelation,name_field: str,crs=25831,geometry_column='geom'):
    """Generation of Bounding Boxes to be used as prompts for SAM. They will be stored in CRS EPSG:4326.

    Args:
        table (duckdb.DuckDBPyRelation):  Table containing the geometries and the tiles (original or virtual) they are associated with.
        name_field (str): Name field containing the data for the element.
        crs (int, optional): Input CRS as EPSG code. Defaults to 25831.
        geometry_column (str, optional): Name for the geometry column. Defaults to 'geom'.

    Returns:
        tile_names (list): Paths to the output tiles
        boxes (list [list]): list of lists of the kind [minx, miny, maxx, maxy] for each polygon included in each tile
    """
    tile_names, boxes=[],[]
    if table is not None:
        sel_table=table.select('*')
        boxes_table=DUCKDB.sql(f'''SELECT LIST({name_field}) AS {name_field}, LIST(geom) geom,depth
                FROM(
                    SELECT {name_field},depth,LIST(geom) geom
                        FROM(
                            SELECT {name_field}, depth, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM(t1.geom,'EPSG:{crs}','EPSG:4326'))) geom
                                 FROM (
                                 SELECT NAME,depth,unnest(ST_DUMP({geometry_column}),recursive:=true) geom
                                    FROM sel_table)t1)
                GROUP BY {name_field},depth)
                    GROUP BY depth''')
        df=boxes_table.fetchdf().reset_index()
        tile_names=df[name_field].tolist()
        #boxes=[list([list(j.values()) for j in i]) for i in df['geom']]
        boxes=[list([list([list(k.values()) for k in j]) for j in i]) for i in df['geom']]
        depths=df['depth'].astype(np.uint8).tolist()
        
    return tile_names, boxes, depths

def create_geojson_mass(table: duckdb.DuckDBPyRelation, name_field:str, output_directory:str, crs=25831, geometry_column ='geom'):
    """Mass generation of GeoJSON files

    Args:
        table (duckdb.DuckDBPyRelation): Table containing the geometries and the tiles (original or virtual) they are associated with.
        name_field (str): Name field containing the data for the element 
        output_directory (str): Path to output directory.
        crs (int, optional): CRS as EPSG code. Defaults to 25831.
        geometry_column (str, optional): Name of the geometry column. Defaults to 'geom'.

    Returns:
        tiles_names (list): Paths to the intersected tiles
        files_names (list): Paths to the output GeoJSON files
    """
    sel_tab=table.select('*')

    # TO RECOVER THE BBOXES AS A GEOMETRY
    # sel_tab2=DUCKDB.sql(f'''SELECT {name_field},ST_ENVELOPE({geometry_column}) geom
    #     FROM sel_tab
    # ''')

    sel_tab=DUCKDB.sql(f'''SELECT {name_field},{geometry_column} geom
        FROM sel_tab
    ''')
    tiles_names=np.unique(sel_tab.fetchdf()[name_field])
    files_names=[os.path.join(output_directory,os.path.splitext(os.path.basename(i))[0]) for i in tiles_names]

    create_files_from_sql(tab=sel_tab,column=name_field,tile_names=tiles_names,file_names=files_names,crs=crs)
    return tiles_names,files_names

def create_level_dirs(results_dir, depth):
    """Generates the directories for contained and limit dirs in a given pyramid level.

    Args:
        results_dir (str): Original dir in which all the layers are to be placed.
        depth (int): The level of the pyramid to be built.

    Returns:
        contained_dir (str): Path to the dir to host the contained entities' GeoJSON files.
        limit_dir (str):  Path to the dir to host the limit entities' GeoJSON files. 
    """
    level_dir=folder_check(os.path.join(results_dir,str(depth)))
    contained_dir=folder_check(os.path.join(level_dir,'contained'))
    limit_dir=folder_check(os.path.join(level_dir,'limit'))
    return contained_dir,limit_dir

def post_processing(depths: Iterable[int],
                    pyramid_dir: str,
                    detections: duckdb.DuckDBPyRelation,
                    geometry_column='geom',
                    segmentation_name='',
):
    """Function to store in arrays files the detections into several different elements in order to find out what happened inside the process.

    Args:
        depth (int): The level of the pyramid to be built.
        pyramid_dir (str): Path to the image pyramid
        detections (duckdb.DuckDBPyRelation): Table with the polygon geometries to be used as box prompts
        
    Returns:
        list[dict]: Contains the names for the tiles and the arrays (minx,miny,maxx,maxy) for the boxes grouped by name of tile 
    """
    tiles,contained=filter_level(detections,pyramid_dir,depths,geometry_column,segmentation_name)
    contained_tiles,contained_boxes,depths=create_bboxes_sam(contained,'NAME')
    #limit_tiles,limit_boxes=create_bboxes_sam(limit,'MOSAIC')
    return tiles, [{depths[i]:{'CONTAINED_TILES':contained_tiles[i],'CONTAINED_BOXES':contained_boxes[i]}} for i in range(len(depths))]

def post_processing_geojson(depths: Iterable[int],
                            pyramid_dir: str,
                            detections: duckdb.DuckDBPyRelation,
                            output_dir: str,
                            geometry_column='geom',
                            segmentation_name='',):
    
    """Function to store in GeoJSON files the detections into several different elements in order to find out what happened inside the process.

    Args:
        depth (int): The level of the pyramid to be built.
        pyramid_dir (str): Path to the image pyramid
        detections (duckdb.DuckDBPyRelation): Table with the polygon geometries to be used as box prompts
        output_dir (str): Output directory

    Returns:
        dict: Contains the names for the tiles and the arrays for the boxes
    """
    tiles,contained=filter_level(detections,pyramid_dir,depths,geometry_column,segmentation_name)

    for depth in depths:
        contained_dir,limit_dir=create_level_dirs(output_dir,depth)
        contained_depth=DUCKDB.sql(f'SELECT * from contained where depth={depth}')
        contained_tiles,contained_boxes=create_geojson_mass(contained_depth,'NAME',contained_dir)
        #limit_tiles,limit_boxes=create_geojson_mass(limit,'MOSAIC',limit_dir)
    return tiles, [{depths[i]:{'CONTAINED_TILES':contained_tiles[i],'CONTAINED_BOXES':contained_boxes[i]}} for i in range(len(depths))]

def predict_tile(image_path,boxes,out_name,sam):
    """Apply SAM using BBOX.
    Args:
        image_path (str | np.array): Path to the tile or numpy array stemming from GDAL ReadAsArray(), or in this package tems, Ortophoto.raster.ReadAsArray()
        boxes (Iterable | str [GeoJSON]): Nested list of bounds (X_min,Y_min,X_max,Y_max), or the path to a GeoJSON path containing Polygon geometries.          
        out_name (str): Name for the output file, can be either vector (GeoJSON) or Raster (GeoTIFF)
        sam (SamGeo_apb): The SAM model
    """

    if isinstance(boxes,str):
        boxes+='.geojson'
        if os.path.exists(boxes):
            sam.set_image(image_path)
            try:
                sam.predict(boxes=boxes, output=out_name, dtype="uint8")
                return out_name
            except:
                print(f'{out_name} could not be loaded')
                            
    elif isinstance(boxes,list) and isinstance(boxes[0],Iterable) and not isinstance(boxes[0],str) :
        sam.set_image(image_path)
        try:
                sam.predict(boxes=boxes,point_crs='EPSG:4326', output=out_name, dtype="uint8")
                return out_name
        except:
                print(f'{out_name} could not be loaded')  
    else:
        print('only GeoJSON or BOX POINT lists allowed')

def predict_tile_points(image_path,boxes,out_name,point_coords,point_labels,sam):
    """Calls SAM predict using point prompts

    Args:
        image_path (str): Image path
        boxes (Iterable): Nested list of bounds (X_min,Y_min,X_max,Y_max), or the path to a GeoJSON path containing Polygon geometries.
        out_name (str): Name of the output file.
        point_coords (Iterable): [(x1,y1),...,(xn,yn)] with the points
        point_labels (Iterable): 0 (negative) or 1 (positive) labeling of the points
        sam (SamGeo_apb): The SAM model

    Returns:
        _type_: _description_
    """
    if isinstance(boxes,str):
        boxes+='.geojson'
        if os.path.exists(boxes):
            sam.set_image(image_path)
            try:
                sam.predict(point_coords=point_coords,point_labels=point_labels, output=out_name, dtype="uint8")
                return out_name
            except:
                print(f'{out_name} could not be loaded')
                               
    elif isinstance(boxes,list) and isinstance(boxes[0],Iterable) and not isinstance(boxes[0],str) :
        sam.set_image(image_path)
        try:
            sam.predict(point_coords=point_coords,point_labels=point_labels,point_crs='EPSG:4326', output=out_name, dtype="uint8")
            return out_name
        except:
            print(f'{out_name} could not be loaded')
            
    else:
        print('only GeoJSON or BOX POINT lists allowed')
 
def create_sam_dirs(sam_out_dir,results,depth,contained_sam_out_images=[],limit_sam_out_images=[]):
    """Generate the dirs for the batch SAM prediction and finds the available files to be found.    
    Meant for recursion.

    Args:
        sam_out_dir (str): Path to the general dir in which the SAM predictions are desired
        depth (int): Level of depth in the image pyramid desired
        contained_sam_out_images (list, optional): Names of the images with prompts totally contained into the tiles. Defaults to [].
        limit_sam_out_images (list, optional): Name of the images whose prompts are within several tiles and are thus saved in GDAL VRT virtual layers. Defaults to [].

    Returns:
        contained_sam_out_images, contained_sam_out_images: Returns new added file paths into original arrays. Meant for recursive use
    """
    level_sam_dir=folder_check(os.path.join(sam_out_dir,f'subset_{depth}'))
    sam_contained_dir=folder_check(os.path.join(level_sam_dir,'contained'))
    sam_limit_dir=folder_check(os.path.join(level_sam_dir,'limit'))

    contained_sam_out_images.extend([os.path.join(sam_contained_dir,os.path.splitext(os.path.basename(i))[0]+'.tif') for i in results[depth].get('CONTAINED_TILES','NO')])
    limit_sam_out_images.extend([os.path.join(sam_limit_dir,os.path.splitext(os.path.basename(i))[0]+'.tif') for i in results[depth].get('LIMIT_TILES','NO')])
    return contained_sam_out_images,limit_sam_out_images

def create_first_iteration(result,segmentation_name,input_image,sam):    
    """Create a first segmentation with the best available contained bounding boxes in the tiles

    Args:
        result (list[dict]): Contains the names for the tiles and the arrays (minx,miny,maxx,maxy) for the boxes grouped by name of tile 

        segmentation_name (str): The name for the segmentation object. Should be defaulted to ''
        input_image (_type_): _description_
        sam (SamGeo_apb): The SAM model    

    Returns:
        _type_: _description_
    """
    results=dict(ChainMap(*result))
    
    from itertools import chain

    contained_boxes=list(chain(*[results[i].get('CONTAINED_BOXES',None) for i in results.keys()]))
    contained_tiles=list(chain(*[results[i].get('CONTAINED_TILES',None) for i in results.keys()]))

    sam_out_dir=folder_check(os.path.join(input_image.folder,f'sam_results_{segmentation_name}')) 
    contained_sam_out_images,limit_sam_out_images=[],[]

    for depth in list(results.keys()):
        contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,results,depth,contained_sam_out_images,limit_sam_out_images) 

    sam_loaded_predict_tile=partial(predict_tile,sam=sam)

    successful_contained=list(map(sam_loaded_predict_tile,contained_tiles,contained_boxes,contained_sam_out_images))
    successful_contained=[x for x in successful_contained if x is not None]

    first_iteration_sammed_mosaic=os.path.join(sam_out_dir,f'resultado_final1_{segmentation_name}.tif')
    first_iteration_sammed_vector=os.path.join(sam_out_dir,f'first_iteration_{segmentation_name}.geojson')

    Ortophoto.mosaic_rasters(successful_contained,first_iteration_sammed_mosaic,pixel_value_to_be_ignored=0)
    wkt_first_iteration=SamGeo_apb.raster_to_vector(first_iteration_sammed_mosaic,output=first_iteration_sammed_vector,dst_crs=input_image.crs)
    df_first_iteration=pd.DataFrame(
        {'wkt':np.array(wkt_first_iteration)},
        index=[1])    
    
    first_iteration_predictions_tile=DUCKDB.sql('''SELECT ST_GEOMFROMTEXT(d.wkt) as geom
               from df_first_iteration d''')
    return first_iteration_predictions_tile,contained_sam_out_images
    
    
def create_random_points(extents_list,tile_extents):
    """Generates random points along a set of boxes and also around their tiles. 
        Stores them in table random_points in the DUCKDB connection

    Args:
        extents_list (Iterable): DUCKDB extent list (format achieved using ST_EXTENT())
        tile_extents (Iterable): Paths to the files where the random points are to be placed
    """
    DUCKDB.execute(f"CREATE TABLE random_points AS SELECT * geom FROM ST_GENERATEPOINTS({extents_list[0]}::BOX_2D,100)")

    for i in range(1,len(extents_list)):
        DUCKDB.execute(f'''INSERT INTO random_points SELECT * geom FROM ST_GENERATEPOINTS({extents_list[i]}::BOX_2D,100)''')
    for i in range(len(tile_extents)):
        DUCKDB.execute(f'''INSERT INTO random_points SELECT * geom FROM ST_GENERATEPOINTS({tile_extents[i]}::BOX_2D,100)''')

def file_pyramid_sam_apply(image_path:str,
                      geospatial_prompt_file_path:str,
                      geometry_column:str,
                      segmentation_name:str,
                      sam:SamGeo_apb,
                      min_expected_element_area:float=0.5,
                      lowest_pixel_size:int=1024,):
    """Iteratively generate SAM segmentations

    Args:
        image_path (str): Aerial image to be segmented
        geospatial_prompt_file_path (str): Path to any geospatial file. 
                                        Available formats: see ST_READ drivers in DuckDB (run DUCKDB.sql('SELECT * FROM ST_Drivers();')).
        geometry_column (str): Geometry column in the geospatial prompt file
        segmentation_name (str): The name for the segmentation object. Should be defaulted to ''
        sam (SamGeo_apb): The SAM model
        min_expected_element_area (float, optional): Area of the smallest element to be expected. Defaults to 0.5.
        lowest_pixel_size (int, optional): Pixel size for all tiles, which will have different resolutions. Defaults to 1024.

    """
       
    input_image=Ortophoto(image_path)
    detections=read_file(geospatial_prompt_file_path)
        
    pyramid_sam_apply(input_image,
                      detections,
                      lowest_pixel_size,
                      geometry_column,
                      min_expected_element_area,
                      segmentation_name,
                      sam)  

    
    
def pyramid_sam_apply(input_image:Ortophoto,
                      detections:duckdb.DuckDBPyRelation,
                      geometry_column:str,
                      segmentation_name:str,
                      sam:SamGeo_apb,
                      min_expected_element_area:float=0.5,
                      lowest_pixel_size:int=1024,
                    ):
    
    """Iteratively generate SAM segmentations using image pyramid algorithms. First through bounding box and then refined using point prompts

    Args:
        input_image (Ortophoto): The complete image, whose pyramid will be dynamically created if not already loaded into the object
        detections (duckdb.DuckDBPyRelation | str | Iterable): Polygon geometry with a detection to be better segmented
                                                               Available formats: see ST_READ drivers in DuckDB (run DUCKDB.sql('SELECT * FROM ST_Drivers();')).
        geometry_column (str): Geometry column in the geospatial prompt file
        segmentation_name (str): The name for the segmentation object. Should be defaulted to ''
        sam (SamGeo_apb): The SAM model
        lowest_pixel_size (int): Pixel size for all tiles, which will have different resolutions. Defaults to 1024.
        min_expected_element_area (float, optional): Area of the smallest element to be expected. Defaults to 0.5.

    """

    if not isinstance(detections,duckdb.DuckDBPyRelation):
        try:
            detections=read_file(detections)
        except:
            raise TypeError
        
    pyramid=input_image.get_pyramid(lowest_pixel_size)    
    depths=[depth for depth in range(input_image.get_pyramid_depth())]
    
    tiles,result=post_processing(pyramid_dir=pyramid,detections=detections,geometry_column=geometry_column,depths=depths,segmentation_name=segmentation_name)

    first_iteration_predictions_tile,contained_sam_out_images=create_first_iteration(result,
                                                                                     segmentation_name,
                                                                                     input_image,
                                                                                     sam)
    create_second_iteration(input_image=input_image,
                            low_resolution_geometries_duckdb=first_iteration_predictions_tile,
                            segmentation_name=segmentation_name,
                            sam=sam,
                            min_expected_element_area=min_expected_element_area,
                            lowest_pixel_size=lowest_pixel_size,
                            contained_sam_out_images=contained_sam_out_images,
                            )
    
def pyramid_sam_apply_geojson(image_path:str,
                            geospatial_prompt_file_path:str,
                            geometry_column:str,
                            segmentation_name:str,
                            sam:SamGeo_apb,                            
                            lowest_pixel_size:int=1024,
                            min_expected_element_area:float=0.5,
                            results_dir:str= None,
):
    """
    Generate a pyramid with intermediate GeoJSON files. Slower performance but allows for repeatability

    Args:
        image (str): Aerial image to be segmented
        geospatial_prompt_file_path (str): Path to any geospatial file. 
                                        Available formats: see ST_READ drivers in DuckDB (run DUCKDB.sql('SELECT * FROM ST_Drivers();')).
        geometry_column (str): Geometry column in the geospatial prompt file
        segmentation_name (str): The name for the segmentation object. Should be defaulted to ''
        sam (SamGeo_apb): The SAM model
        lowest_pixel_size (int, optional): Pixel size for all tiles, which will have different resolutions. Defaults to 1024.
        min_expected_element_area (float, optional): Area of the smallest element to be expected. Defaults to 0.5.
        results_dir (str, optional): Where to store the GeoJSON files. Defaults to None, thus storing in the project folder using under "GeoJSON_bboxes_{segmentation_name}"
    """

    input_image=Ortophoto(image_path)
    detections=read_file(geospatial_prompt_file_path)
    
    
    if results_dir is None:
        results_dir=folder_check(os.path.join(input_image.folder,f"GeoJSON_bboxes_{segmentation_name}"))
    
    input_image.pyramid=folder_check(os.path.join(input_image.folder,os.path.basename(input_image.raster_path).split('.')[0])+'_pyramid')
    depths=[depth for depth in range(input_image.get_pyramid_depth())]
    tiles,result=post_processing_geojson(pyramid_dir=input_image.get_pyramid(lowest_pixel_size),output_dir=results_dir,detections=detections,geometry_column=geometry_column,depths=depths,segmentation_name=segmentation_name)


    results=dict(ChainMap(*result))
    first_iteration_predictions_tile,contained_sam_out_images=create_first_iteration(result,
                                                                                     segmentation_name,
                                                                                     input_image,
                                                                                     sam)
    create_second_iteration(input_image=input_image,
                            low_resolution_geometries_duckdb=first_iteration_predictions_tile,
                            segmentation_name=segmentation_name,
                            sam=sam,
                            min_expected_element_area=min_expected_element_area,
                            lowest_pixel_size=lowest_pixel_size,
                            contained_sam_out_images=contained_sam_out_images,
                            )
    

def point_prompt_based_sam(
    image_path:str,
    geospatial_prompt_file_path:str,
    segmentation_name:str,
    sam:SamGeo_apb,
    min_expected_element_area:float=0.5,
    lowest_pixel_size:int=1024,   
    contained_sam_out_images=[],):
    """
    Reads geospatial prompt files to improve segmentation

    Args:
        image_path (str): Path to the image to be segmented
        geospatial_prompt_file_path (str): Geospatial prompt file to be called
        segmentation_name (str): The name for the segmentation object
        sam (SamGeo_apb): The SAM model
        min_expected_element_area (float, optional): Area of the smallest element to be expected. Defaults to 0.5.
        lowest_pixel_size (int, optional): Pixel size for each tile of the pyramid.  Defaults to 1024.
        contained_sam_out_images (list, optional): Paths to the files to be created. Defaults to [].
    """
    input_image=Ortophoto(image_path)
    low_resolution_geometries_duckdb=read_file(geospatial_prompt_file_path) 

    create_second_iteration(input_image,low_resolution_geometries_duckdb,segmentation_name,sam,min_expected_element_area,lowest_pixel_size,contained_sam_out_images)

def create_second_iteration(
    input_image: Ortophoto,
    low_resolution_geometries_duckdb:duckdb.DuckDBPyRelation,
    segmentation_name:str,
    sam:SamGeo_apb,
    min_expected_element_area:float=0.5,
    lowest_pixel_size:int=1024,
    contained_sam_out_images=[],):
    """Improves an existing segmentation by applying point prompting, then compares it to the input for a cleaner refined iteration

    Args:
        input_image (Ortophoto): Aerial image to be segmented
        low_resolution_geometries_duckdb (duckdb.DuckDBPyRelation): Previous iteration or read file using the read_file() function in this modules
                 Available formats: see ST_READ drivers in DuckDB (run DUCKDB.sql('SELECT * FROM ST_Drivers();')). 
        segmentation_name (str):  The name for the segmentation object.
        sam (SamGeo_apb): The SAM model
        min_expected_element_area (float, optional): Area of the smallest element to be expected. Defaults to 0.5.
        lowest_pixel_size (int, optional): Pixel size for each tile of the pyramid. Defaults to 1024.
        contained_sam_out_images (list, optional): Paths to the files to be created. Defaults to []. If not declared, it will be stored in a subfolder of the image folder 
    """
    # INPUTS
    input_image.create_tiles_duckdb_table(lowest_pixel_size)
    first_iteration_predictions=low_resolution_geometries_duckdb.select('geom')

    DUCKDB.sql(
            f'''CREATE TABLE unido AS SELECT t.NAME, t.depth,t.geom AS tile_geom, g.geom AS predict_geom 
                FROM (SELECT parse_filename(NAME, false, 'system') as parsed_NAME, depth, geom, NAME
                    FROM tiles) t 
                JOIN first_iteration_predictions g
                    ON ST_INTERSECTS(t.geom,g.geom)''')
    
    boxes=DUCKDB.sql(f'''SELECT NAME,depth,st_collect(list(geom)) geom 
                        FROM
                        (SELECT NAME,tile_geom,geom,depth
                        FROM (SELECT t1.NAME,t1.tile_geom, st_intersection(t1.tile_geom,t2.predict_geom) geom, t2.depth
                                FROM unido t1
                            JOIN (SELECT max(depth) depth,predict_geom FROM unido GROUP BY predict_geom) t2
                                on t1.depth=t2.depth and t1.predict_geom=t2.predict_geom)
                        WHERE ST_AREA(geom)>{min_expected_element_area} and NOT ST_CONTAINS(geom,tile_geom))
                    GROUP BY NAME,tile_geom,depth''')
    
    all_tiles=DUCKDB.sql('''SELECT t1.NAME,t1.tile_geom, st_intersection(t1.tile_geom,t2.predict_geom) geom, t2.depth
                                FROM unido t1
                            JOIN (SELECT max(depth) depth,predict_geom FROM unido GROUP BY predict_geom) t2
                                on t1.depth=t2.depth and t1.predict_geom=t2.predict_geom
                        WHERE ST_AREA(geom)>1 ''')
    
    tiles_completas=DUCKDB.sql('''SELECT a.NAME
                               from (SELECT DISTINCT NAME FROM all_tiles) a
                               left join (SELECT NAME from boxes)b
                               on a.NAME=b.NAME
                               WHERE b.NAME IS NULL''')

    paths_to_complete=tiles_completas.fetchdf()['NAME'].tolist()
    
    extents=DUCKDB.sql(f'''SELECT NAME,ST_EXTENT(t1.geom) geom
            FROM (
                SELECT NAME,depth,unnest(ST_DUMP(geom),recursive:=true) geom
                            FROM boxes
                            )t1''')

    df=extents.fetchdf().reset_index()
    tile_names=df['NAME'].tolist()
    extents_list=df['geom'].to_list()
    tile_extents=DUCKDB.sql('''SELECT ST_EXTENT(geom) as box FROM tiles''').fetchdf()['box'].tolist()
    create_random_points(extents_list=extents_list,tile_extents=tile_extents)

    puntos_interes=DUCKDB.sql(f'''
        SELECT positive.NAME, positive.coords positive_coords, negative.coords negative_coords
            FROM (SELECT NAME, LIST(LIST_VALUE(ST_X(geom), ST_Y(geom))) coords, ST_COLLECT(LIST(geom::GEOMETRY)) geom
                    from(
                        SELECT b.NAME,ST_FLIPCOORDINATES(ST_TRANSFORM(r.geom,'EPSG:{input_image.crs}','epsg:4326')) geom, 
                        from random_points r 
                            join(SELECT ST_BUFFER(geom,-0.5) geom,NAME, geom AS original_geom FROM boxes) b
                                on st_intersects(b.geom,r.geom) )
                    GROUP BY NAME)positive 
            join
            (SELECT NAME, LIST(LIST_VALUE(ST_X(geom), ST_Y(geom))) coords, ST_COLLECT(LIST(geom::GEOMETRY)) geom
                    FROM (SELECT ST_FLIPCOORDINATES(ST_TRANSFORM(r.geom,'EPSG:{input_image.crs}','epsg:4326')) geom ,u.NAME 
                            from(select NAME,tile_geom from unido) u
                                join(SELECT ST_BUFFER(geom,0.5) geom,NAME FROM boxes) b
                                    on u.NAME=b.NAME 
                                join random_points r
                                    ON st_intersects(r.geom,u.tile_geom) and not st_intersects(b.geom,r.geom) )
                group by NAME) negative
            on positive.NAME=negative.NAME
            ''')
    
    boxes_table=DUCKDB.sql(f'''
                    SELECT NAME,depth,LIST(geom) geom
                        FROM(
                            SELECT NAME, depth, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM(t1.geom,'EPSG:{input_image.crs}','EPSG:4326'))) geom
                                 FROM (
                                 SELECT NAME,depth,unnest(ST_DUMP(geom),recursive:=true) geom
                                    FROM boxes)t1 where st_area(t1.geom)>1)
                GROUP BY NAME,depth''')
    
    out_prompts=DUCKDB.sql('''SELECT p.NAME, p.positive_coords,p.negative_coords,b.depth, b.geom
                from puntos_interes p
                join boxes_table b
                on p.NAME=b.NAME''').fetchdf()
    
    sam_out_dir=folder_check(os.path.join(input_image.folder,f'sam_results_{segmentation_name}')) 
    limit_tiles=[out_prompts['NAME'].to_list()]
    positive_point_prompt=out_prompts['positive_coords'].to_list()
    negative_point_prompt=out_prompts['negative_coords'].to_list()

    point_prompt=[[*p,*n] for p,n in zip(positive_point_prompt,negative_point_prompt)]
    point_labels=[[*np.full_like(p,1),*np.full_like(n,0)] for p,n in zip(positive_point_prompt,negative_point_prompt)]    
    limit_boxes=[list([list(j.values()) for j in i]) for i in out_prompts['geom']]

    depths=out_prompts['depth'].unique().astype(np.int8)
    limit_sam_out_images=[]
    limit_result=[{depths[i]:{'LIMIT_TILES':limit_tiles[i],'LIMIT_BOXES':limit_boxes[i]} for i in range(len(depths))} ]
    results=dict(ChainMap(*limit_result))

    contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,results,depths[0],contained_sam_out_images,limit_sam_out_images) 
    level_sam_dir=folder_check(os.path.join(sam_out_dir,f'subset_{depths[0]}'))
    sam_limit_dir=os.path.join(level_sam_dir,'limit')

    out_fulls=[os.path.join(sam_limit_dir,os.path.splitext(os.path.basename(p))[0]+'.tif') for p in paths_to_complete]
    [SamGeo_apb.full_to_tif(i,j) for (i,j) in zip(paths_to_complete,out_fulls)]
    
    sam_loaded_predict_tile_point=partial(predict_tile_points,sam=sam)

    # list(map(sam_loaded_predict_tile_point,limit_tiles[0],limit_boxes,limit_sam_out_images,point_prompt,point_labels))
    successful_contained_2=list(map(sam_loaded_predict_tile_point,limit_tiles[0],limit_boxes,limit_sam_out_images,point_prompt,point_labels))
    successful_contained_2=[x for x in successful_contained_2 if x is not None]

    
    
    ####################################################### TODA ESTA ZONA ES SUSCEPTIBLE DE SER OTRA FUNCIÓN #####################################
    second_iteration_sammed_mosaic=os.path.join(sam_out_dir,f'resultado_final2_{segmentation_name}.tif')
    second_iteration_sammed_vector=os.path.join(sam_out_dir,f'second_iteration_{segmentation_name}.geojson')
    
    successful_contained_2.extend(out_fulls)
    Ortophoto.mosaic_rasters(successful_contained_2,second_iteration_sammed_mosaic,pixel_value_to_be_ignored=0,)
    wkt_second_iteration=SamGeo_apb.raster_to_vector(second_iteration_sammed_mosaic,output=second_iteration_sammed_vector,dst_crs=input_image.crs)
    
    df_second_iteration=pd.DataFrame(
        {'wkt':np.array(wkt_second_iteration)},
        index=[1])
    
    second_iteration_predictions=DUCKDB.sql('''SELECT ST_GEOMFROMTEXT(d.wkt) as geom
                from df_second_iteration d''')
    
    duckdb_2_gdf(DUCKDB.sql(f'''
        SELECT ST_INTERSECTION(a.geom,b.geom) as geom
            FROM
                (SELECT ST_BUFFER(geom,0.5) geom FROM first_iteration_predictions
                    ) a
            JOIN (SELECT geom
                FROM second_iteration_predictions
                    WHERE ST_AREA(geom)>{min_expected_element_area}) b
            on ST_INTERSECTS(a.geom,b.geom)'''),'geom').to_parquet(os.path.join(input_image.folder,f'refined_segmentation_{segmentation_name}.parquet')) 

def text_to_bbox_lowres_complete(
        input_image:Ortophoto,
        text_prompt:str,
        output:str = None,
        sam:LangSAM_apb=None
    ):
    """Generate bouding boxes from a text prompt. Calls the Grounding DINO parts of LangSAM excluding SAM use, speeding up the prediction of this task.

    Args:
        input_image (Ortophoto): Aerial image where the element should be identified
        text_prompt (str): Prompt for Grounding DINO.
        output (str, optional): Path of where to store the bounding box geometries. Defaults to None
        sam (LangSAM_apb,optional). Modified SAMGeo object to allow for selfstanding DINO. If not provided, creates a LangSAM_apb object with default parameters. Defaults to None

    Returns:
        bboxes_duckdb (duckdb.DuckdbPyRelation): Spatial database table with the bounding boxes found by Grounding DINO.
    """
    largest_tile=input_image.get_resolution_tiles()[-1]
    if sam is None:
        sam = LangSAM_apb()
    predict_prompt=partial(sam.predict_dino,text_prompt=text_prompt,box_threshold=0.24, text_threshold=0.2)

    def predict_save(image):
        pil_image=sam.path_to_pil(image)
        boxes,logits,phrases=predict_prompt(pil_image)
        sam.boxes=boxes
        return sam.save_boxes(dst_crs=input_image.crs)
        
    single_gdf_bboxes_DINO=predict_save(largest_tile)

    single_gdf_bboxes_DINO['NAME']=largest_tile
    #single_gdf_bboxes_DINO.to_file(os.path.join(OUT_DIR,'groundedDINO','only_dino.geojson'))
    single_gdf_bboxes_DINO['geom']=single_gdf_bboxes_DINO.geometry.to_wkt()
    df_bounding_boxes_DINO=single_gdf_bboxes_DINO[['NAME','geom']]
    bounding_boxes_DINO=DUCKDB.sql('''
        SELECT ST_GEOMFROMTEXT(geom) AS geom, NAME
            FROM df_bounding_boxes_DINO''')
    
    bboxes_duckdb=DUCKDB.sql('''
        SELECT b.geom,b.NAME
            from bounding_boxes_DINO b''')
    print(output)
    if output is not None:
        duckdb_2_gdf(bboxes_duckdb,'geom').to_file(output)
    
    return bboxes_duckdb

if __name__=="__main__":
    #choose_model
    #model class has optimal resolution attribute
    from apb_spatial_computer_vision.sam_utilities import SamGeo_apb
    sam = SamGeo_apb(
       model_type="vit_h",
       automatic=False,
       sam_kwargs=None,
       )
    input_image=os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif')
    # 
    detections=os.path.join(OUT_DIR,'QGIS_BUILDINGS','ORIENTED_BOXES.GEOJSON')
    #detections=os.path.join(OUT_DIR,'tanks_50c_40iou.geojson')
    pyramid_sam_apply_geojson(input_image,detections,1024,'geom',0.5,'qgis_buildings',sam)
    

    pass    