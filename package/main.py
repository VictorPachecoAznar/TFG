from package import *
from package.raster_utilities import Ortophoto,Tile,folder_check

from concurrent.futures import ProcessPoolExecutor

import geopandas as gpd, pandas as pd, numpy as np
import time
from functools import partial
from collections import ChainMap
from collections.abc import Iterable
import cv2

print(folder_check(TEMP_DIR))

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

def read_file(paths,DUCKDB=DUCKDB):
    """Geospatial data reader for DuckDB

    Args:
        paths (Iterable | str): Path/s to the file/s
        DUCKDB (duckdb.DuckDBPyConnection, optional): Defaults to DUCKDB (environment variable).

    Returns:
        duckdb.DuckDBPyRelation: Table containing the elements
    """
    if isinstance(paths,str):
        command=f'''SELECT *
            FROM ST_READ('{paths}')'''
    elif isinstance(paths,Iterable):
        command = " UNION ALL ".join(
            [f"SELECT *  FROM st_read('{path}')" for path in paths]
                            )
    else: 
        pass
    return DUCKDB.sql(command)
    
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


def filter_level(detections,pyramid_dir,depths,geometry_column):
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
            [f"SELECT *, '{depth}' depth  FROM st_read('{os.path.join(pyramid_dir,'vector',f"subset_{depth}.geojson")}')" for depth in depths])
                            
    tiles=DUCKDB.sql(command)

    #tiles=read_file([os.path.join(pyramid_dir,'vector',f"subset_{depth}.geojson")for depth in depths])

    detections=detections.select('*')
    #CONNECT PREDICTION TO TILE
    extent_total=DUCKDB.sql('''
        SELECT ST_EXTENT_AGG(geom) geom
            from tiles t
            group by depth
                having depth=1''')
    
    detections=DUCKDB.sql('''
        SELECT ST_INTERSECTION(d.geom,e.geom) AS geom
            FROM detections d
                JOIN extent_total e
                on ST_intersects(d.geom,e.geom)''')


    intersection=DUCKDB.sql(
        f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.{geometry_column} AS predict_geom
            FROM tiles t 
            JOIN detections g
                ON ST_INTERSECTS(t.geom,g.{geometry_column})''')
    
    within=DUCKDB.sql(
        f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.{geometry_column} AS predict_geom
            FROM tiles t 
            JOIN detections g
                ON ST_CONTAINS(t.geom,g.{geometry_column})
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
        f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.{geometry_column} AS predict_geom
                FROM tiles t 
                JOIN detections g
                    ON ST_INTERSECTS(t.geom,g.{geometry_column}) AND NOT ST_CONTAINS(t.geom,g.{geometry_column})
                    WHERE predict_geom NOT IN (SELECT distinct geom FROM contained)''')
    
    # DUCKDB.sql(
    #     f'''SELECT l.NAME, l.depth,l.tile_geom, l.predict_geom
    #         FROM(SELECT t.NAME, t.depth,t.geom AS tile_geom, g.{geometry_column} AS predict_geom
    #             FROM tiles t 
    #             JOIN detections g
    #                 ON ST_INTERSECTS(t.geom,g.{geometry_column}) AND NOT ST_CONTAINS(t.geom,g.{geometry_column}))l
                
    #                 on c.geom=l.predict_geom and c.depth=c.depth''')
    
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
    final=None

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

        relation_gdf=duckdb_2_gdf(combi,'geom',25831)

        #fun=lambda x:[i for i in x]
        array=[i for i in cleans_indexed['unique_tiles'].fetchnumpy()['unique_tiles']]
        virtuals_dir=folder_check(os.path.join(os.path.dirname(pyramid_dir),'virtuals'))
        names=[os.path.join(virtuals_dir,str(i)) for i in range(1,len(cleans_indexed)+1)]

        with ProcessPoolExecutor(5) as Executor:
            mosaics=list(Executor.map(Ortophoto.mosaic_rasters,array,names))

        mosaic_index=[int(os.path.splitext(os.path.basename(i))[0]) for i in mosaics]

        mosaics_data=[{'MOSAIC':i,'INDEX':j} for (i,j) in zip(mosaics,mosaic_index)]
        mosaics_df=pd.DataFrame(mosaics_data)

        final=DUCKDB.sql(f'''
            SELECT m.MOSAIC,c.geom, c.affected_tiles,c.depth
                FROM mosaics_df m JOIN 
                    (SELECT u.row_index, a.geom, a.affected_tiles,depth
                        FROM cleans_indexed u JOIN affected a 
                            on a.affected_tiles=u.unique_tiles) c
                ON m.INDEX=c.row_index''')
        
        new_contained=DUCKDB.sql('''SELECT NAME,depth, geom
                                    FROM contained
                                        UNION 
                                    (SELECT MOSAIC, depth, geom FROM final)''')
    return tiles, new_contained

    # DUCKDB.sql(
    #     f'''SELECT t1.depth,t2.predict_geom geom,t1.NAME FROM within t1
    #      JOIN
    #         (SELECT MAX(depth) depth, w.predict_geom
    #            FROM within w
    #            GROUP BY w.predict_geom) t2
    #            ON t1.depth=t2.depth AND t1.predict_geom=t2.predict_geom
    #             ''')
    
    limit=DUCKDB.sql('''SELECT NAME, predict_geom
                      FROM intersection
                      WHERE predict_geom 
                     NOT IN (SELECT geom FROM contained)
                      GROUP BY predict_geom''')
    # DUCKDB.sql(
    #     f'''JOIN (SELECT geom from contained) c
        
    #             ''')
    # DUCKDB.sql(
    #     f'''SELECT LIST(i3.NAME),i2.geom
    #         FROM(SELECT MAX(depth), c.geom
    #             FROM intersection i1
    #             JOIN (SELECT geom from contained) c
    #             ON c.geom=i1.predict_geom
    #             GROUP BY c.geom) i2 join intersection i3
    #             on i2.geom=i3.predict_geom and i2.depth=i3.depth
    #             GROUP BY i2.geom
    #             ''')
    
    # duckdb_2_gdf(DUCKDB.sql(
    #     f'''SELECT LIST(i3.NAME) CONTAINED_ELEMENTS,i2.geom
    #         FROM(SELECT MAX(depth) depth, c.geom
    #             FROM intersection i1
    #             JOIN (SELECT geom from contained) c
    #             ON c.geom=i1.predict_geom
    #             GROUP BY c.geom) i2 join intersection i3
    #             on i2.geom=i3.predict_geom and i2.depth=i3.depth
    #             WHERE ST_CONTAINS(i2.geom,i2.tile_geom)
    #             GROUP BY i2.geom
    #             '''),'geom').to_file(os.path.join(OUT_DIR,'prueba_teselas_limite_3.geojson'))

    # duckdb_2_gdf(DUCKDB.sql(
    #     f'''SELECT LIST(i3.NAME) CONTAINED_ELEMENTS,ST_COLLECT(LIST(ST_INTERSECTION(i3.predict_geom,i3.tile_geom))) geom, i3.predict_geom
    #         FROM(SELECT MAX(depth) depth, c.geom
    #             FROM intersection i1
    #             JOIN (SELECT geom from contained) c
    #             ON c.geom=i1.predict_geom
    #             GROUP BY c.geom) i2 join intersection i3
    #             on i2.geom=i3.predict_geom and i2.depth=i3.depth
    #             WHERE NOT ST_CONTAINS(i3.predict_geom,i3.tile_geom)
    #             GROUP BY i3.predict_geom,i3.tile_geom 
                
    #             '''),'geom').to_file(os.path.join(OUT_DIR,'prueba_teselas_limite_15.geojson'))

    if len(intersection)==0:
        raise Exception('THE PYRAMID DOES NOT CONTAIN THESE ELEMENTS')
    
    #FIND PREDICTIONS BETWEEN TILES
    predict_geom_repes=DUCKDB.sql('''
        SELECT predict_geom,NAME
            FROM intersection
                WHERE predict_geom IN ( SELECT predict_geom
                                        FROM intersection
                                            GROUP BY predict_geom
                                            HAVING COUNT(*)>1)''')
    predict_geom_repes=DUCKDB.sql('''
            SELECT predict_geom,NAME,depth
            FROM intersection
               JOIN (SELECT predict_geom,depth
                                        FROM intersection
                                            GROUP BY predict_geom,depth
                                            HAVING COUNT(*)>1)t2
               ON t2.predict_geom=intersection.predict_geom''')

    #LIST TILES IN WHICH BETWEEN WHICH THE PREDICTIONS LAY
    affected=DUCKDB.sql(
        '''SELECT LIST(NAME) affected_tiles, predict_geom geom
            FROM predict_geom_repes
                GROUP BY predict_geom''')
    
    #FIND GEOMETRIES THAT WILL BE FURTHER CALCULATED 
    exiters=DUCKDB.sql(
        '''SELECT i.NAME, i.predict_geom AS geom
                FROM intersection i 
                    FULL OUTER JOIN  predict_geom_repes a
                    ON i.predict_geom=a.predict_geom
                        WHERE a.predict_geom IS NULL
                        OR i.predict_geom IS NULL''')
     
    # FINDS THE UNIQUE VIRTUAL LAYERS TO BE CREATED
    cleans=DUCKDB.sql(f'''SELECT DISTINCT affected_tiles AS unique_tiles
                      FROM affected''')
    final=None

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

        relation_gdf=duckdb_2_gdf(combi,'geom',25831)

        #fun=lambda x:[i for i in x]
        array=[i for i in cleans_indexed['unique_tiles'].fetchnumpy()['unique_tiles']]
        virtuals_dir=folder_check(os.path.join(os.path.dirname(pyramid_dir),'virtuals'))
        level_virtual_dir=folder_check(os.path.join(virtuals_dir,f'virtuals_{depth}'))
        names=[os.path.join(level_virtual_dir,str(i)) for i in range(1,len(cleans_indexed)+1)]

        with ProcessPoolExecutor(5) as Executor:
            mosaics=list(Executor.map(Ortophoto.mosaic_rasters,array,names))

        mosaic_index=[int(os.path.splitext(os.path.basename(i))[0]) for i in mosaics]

        mosaics_data=[{'MOSAIC':i,'INDEX':j} for (i,j) in zip(mosaics,mosaic_index)]
        mosaics_df=pd.DataFrame(mosaics_data)

        final=DUCKDB.sql(f'''
            SELECT m.MOSAIC,c.geom, c.affected_tiles
                FROM mosaics_df m JOIN 
                    (SELECT u.row_index, a.geom, a.affected_tiles
                        FROM cleans_indexed u JOIN affected a 
                            on a.affected_tiles=u.unique_tiles) c
                ON m.INDEX=c.row_index''')


    return exiters, final
    


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
        # boxes_table=DUCKDB.sql(f'''
        #         SELECT {name_field},LIST(geom) geom
        #         FROM(SELECT {name_field}, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM({geometry_column},'EPSG:{crs}','EPSG:4326'))) geom
        #                 FROM sel_table)
        #         GROUP BY {name_field}''')
        # boxes_table=DUCKDB.sql(f'''SELECT LIST({name_field}) AS {name_field}, LIST(geom) geom,depth
        #         FROM(
        #         SELECT {name_field},depth,LIST(geom) geom
        #         FROM(SELECT {name_field},depth, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM({geometry_column},'EPSG:{crs}','EPSG:4326'))) geom
        #                 FROM sel_table)
        #         GROUP BY {name_field},depth)
        #         GROUP BY depth''')
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
                    geometry_column='geom'
):
    """Function to store in arrays files the detections into several different elements in order to find out what happened inside the process.

    Args:
        depth (int): The level of the pyramid to be built.
        pyramid_dir (str): Path to the image pyramid
        detections (duckdb.DuckDBPyRelation): Table with the polygon geometries to be used as box prompts
        
    Returns:
        dict: Contains the names for the tiles and the arrays (minx,miny,maxx,maxy) for the boxes grouped by name of tile 
    """
    tiles, contained=filter_level(detections,pyramid_dir,depths,geometry_column)
    contained_tiles,contained_boxes,depths=create_bboxes_sam(contained,'NAME')
    #limit_tiles,limit_boxes=create_bboxes_sam(limit,'MOSAIC')
    return tiles,[{depths[i]:{'CONTAINED_TILES':contained_tiles[i],'CONTAINED_BOXES':contained_boxes[i]}} for i in range(len(depths))]

def post_processing_geojson(depth: int,
                            pyramid_dir: str,
                            detections: duckdb.DuckDBPyRelation,
                            output_dir: str):
    """Function to store in GeoJSON files the detections into several different elements in order to find out what happened inside the process.

    Args:
        depth (int): The level of the pyramid to be built.
        pyramid_dir (str): Path to the image pyramid
        detections (duckdb.DuckDBPyRelation): Table with the polygon geometries to be used as box prompts
        output_dir (str): Output directory

    Returns:
        dict: Contains the names for the tiles and the arrays for the boxes
    """
    contained_dir,limit_dir=create_level_dirs(output_dir,depth)
    contained,limit=filter_level(detections,pyramid_dir,depth,'geom')
    contained_tiles,contained_boxes=create_geojson_mass(contained,'NAME',contained_dir)
    limit_tiles,limit_boxes=create_geojson_mass(limit,'MOSAIC',limit_dir)
    return {depth:{'CONTAINED_TILES':contained_tiles,'CONTAINED_BOXES':contained_boxes,'LIMIT_TILES':limit_tiles,'LIMIT_BOXES':limit_boxes}}

def predict_tile(image_path,boxes,out_name,sam):
    """Apply SAM using BBOX.
    Args:
        image_path (str | np.array): Path to the tile or numpy array stemming from GDAL ReadAsArray(), or in this package tems, Ortophoto.raster.ReadAsArray()
        boxes (Iterable | str [GeoJSON]): Nested list of bounds (X_min,Y_min,X_max,Y_max), or the path to a GeoJSON path containing Polygon geometries.          
        out_name (str): Name for the output file, can be either vector (GeoJSON) or Raster (GeoTIFF)
        sam (SamGeo_apb): SAM model instance to be used
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
                print('out')
                return out_name
        except:
                print(f'{out_name} could not be loaded')  
    else:
        print('only GeoJSON or BOX POINT lists allowed')

def predict_tile_points(image_path,boxes,out_name,point_coords,point_labels,sam):
   
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
            print('out')
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

    contained_sam_out_images.extend([os.path.join(sam_contained_dir,os.path.basename(i)) for i in results[depth].get('CONTAINED_TILES','NO')])
    limit_sam_out_images.extend([os.path.join(sam_limit_dir,os.path.splitext(os.path.basename(i))[0]+'.tif') for i in results[depth].get('LIMIT_TILES','NO')])
    return contained_sam_out_images,limit_sam_out_images


def pyramid_sam_apply(image,prompt_file,lowest_pixel_size,geometry_column,sam):
    """Iteratively generate SAM segmentations

    Args:
        image (_type_): _description_
        prompt_file (_type_): _description_
        lowest_pixel_size (_type_): _description_
    """
    input_image=Ortophoto(image)
    detections=read_file(prompt_file)
    input_image.pyramid=folder_check(os.path.join(input_image.folder,os.path.basename(input_image.raster_path).split('.')[0])+'_pyramid')
    pyramid=input_image.get_pyramid(lowest_pixel_size)    
    depths=[depth for depth in range(input_image.get_pyramid_depth())]
    
    tiles,result=post_processing(pyramid_dir=pyramid,detections=detections,geometry_column=geometry_column,depths=depths)
    results=dict(ChainMap(*result))
    
    from itertools import chain
    
    # contained_boxes=results.get('CONTAINED_BOXES','NO')
    # contained_tiles=results.get('CONTAINED_TILES','NO')
    
    contained_boxes=list(chain(*[results[i].get('CONTAINED_BOXES','NO') for i in results.keys()]))
    contained_tiles=list(chain(*[results[i].get('CONTAINED_TILES','NO') for i in results.keys()]))
    
    # limit_boxes=list(chain(*[results[i].get('LIMIT_BOXES','NO') for i in results.keys()]))
    # limit_tiles=list(chain(*[results[i].get('LIMIT_TILES','NO') for i in results.keys()]))

    sam_out_dir=folder_check(os.path.join(input_image.folder,'sammed_DEMO_ERNESTO_2')) 
    contained_sam_out_images,limit_sam_out_images=[],[]

    for depth in list(reversed(depths)):
        contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,results,depth,contained_sam_out_images,limit_sam_out_images) 
    sam_loaded_predict_tile=partial(predict_tile,sam=sam)
    #n=os.path.splitext(contained_sam_out_images[110])[0]+'_nombrado.geojson'
    #sam.raster_to_vector(contained_sam_out_images[110],n)
    successful_contained=list(map(sam_loaded_predict_tile,contained_tiles,contained_boxes,contained_sam_out_images))
    successful_contained=[x for x in successful_contained if x is not None]
    vectorize=partial(SamGeo_apb.raster_to_vector,dst_crs=input_image.crs)
    new_geometries=np.array(list(map(vectorize,successful_contained)))
    datos_wkt=pd.DataFrame({'wkt':new_geometries,'tiles':successful_contained})
    refined_predictions=DUCKDB.sql('''SELECT ST_GEOMFROMTEXT(d.wkt) as geom, tiles as tile_names
               from datos_wkt d''')
        
    unido=DUCKDB.sql(
            f'''SELECT t.NAME, t.depth,t.geom AS tile_geom, g.geom AS predict_geom 
                FROM (SELECT parse_filename(NAME, false, 'system') as parsed_NAME, depth, geom, NAME
                    FROM tiles) t 
                JOIN (SELECT parse_filename(tile_names, false, 'system') as parsed_tile_names, geom
                    FROM refined_predictions) g
                    ON ST_INTERSECTS(t.geom,g.geom)''')
    
    boxes=DUCKDB.sql('''SELECT NAME,depth,st_collect(list(geom)) geom 
                        FROM
                        (SELECT NAME,tile_geom,geom,depth
                        FROM (SELECT t1.NAME,t1.tile_geom, st_intersection(t1.tile_geom,t2.predict_geom) geom, t2.depth
                                FROM unido t1
                            JOIN (SELECT max(depth) depth,predict_geom FROM unido GROUP BY predict_geom) t2
                                on t1.depth=t2.depth and t1.predict_geom=t2.predict_geom)
                        WHERE ST_AREA(geom)>1 and NOT ST_CONTAINS(geom,tile_geom))
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
    
    name_field='NAME'

    extents=DUCKDB.sql(f'''SELECT NAME,ST_EXTENT(t1.geom) geom
            FROM (
                SELECT NAME,depth,unnest(ST_DUMP(geom),recursive:=true) geom
                            FROM boxes
                            )t1''')

    df=extents.fetchdf().reset_index()
    tile_names=df[name_field].tolist()
    extents_list=df['geom'].to_list()
    #box_prompts=list(zip(tile_names,extents_list))
    tile_extents=DUCKDB.sql('''SELECT ST_EXTENT(geom) as box FROM tiles''').fetchdf()['box'].tolist()

    DUCKDB.execute(f"CREATE TABLE resultado AS SELECT * geom FROM ST_GENERATEPOINTS({extents_list[0]}::BOX_2D,1000)")
    t0=time.time()
    for i in range(1,len(extents_list)):
        DUCKDB.execute(f'''INSERT INTO resultado SELECT * geom FROM ST_GENERATEPOINTS({extents_list[i]}::BOX_2D,1000)''')
    for i in range(len(tile_extents)):
        DUCKDB.execute(f'''INSERT INTO resultado SELECT * geom FROM ST_GENERATEPOINTS({tile_extents[i]}::BOX_2D,1000)''')
    t1=time.time()
    print(f'{t1-t0}')

    puntos_interes=DUCKDB.sql(f'''
        SELECT positive.NAME, positive.X pos_X, positive.Y pos_Y, negative.X neg_X, negative.Y neg_Y
            FROM (SELECT NAME, LIST(st_x(geom)) X,LIST(st_y(geom)) Y, ST_COLLECT(LIST(geom::GEOMETRY)) geom
                    from(
                        SELECT b.NAME,ST_FLIPCOORDINATES(ST_TRANSFORM(r.geom,'EPSG:{input_image.crs}','epsg:4326')) geom, 
                        from resultado r 
                            join(SELECT ST_BUFFER(geom,-0.5) geom,NAME, geom AS original_geom FROM boxes) b
                                on st_intersects(b.geom,r.geom) )
                    GROUP BY NAME)positive 
            join
            (SELECT NAME, LIST(st_x(geom)) X,LIST(st_y(geom)) Y, ST_COLLECT(LIST(geom::GEOMETRY)) geom
                    FROM (SELECT ST_FLIPCOORDINATES(ST_TRANSFORM(r.geom,'EPSG:{input_image.crs}','epsg:4326')) geom ,u.NAME 
                            from(select NAME,tile_geom from unido) u
                                join(SELECT ST_BUFFER(geom,0.5) geom,NAME FROM boxes) b
                                    on u.NAME=b.NAME 
                                join resultado r
                                    ON st_intersects(r.geom,u.tile_geom) and not st_intersects(b.geom,r.geom) )
                group by NAME) negative
            on positive.NAME=negative.NAME
            ''')
    
    # boxes_table=DUCKDB.sql(f'''
    #                 SELECT {name_field},LIST(geom) geom
    #                     FROM(
    #                         SELECT {name_field}, depth, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM(t1.geom,'EPSG:{input_image.crs}','EPSG:4326'))) geom
    #                              FROM (
    #                              SELECT NAME,depth,unnest(ST_DUMP({geometry_column}),recursive:=true) geom
    #                                 FROM boxes)t1)
    #             GROUP BY {name_field}''')
    crs=25831
    boxes_table=DUCKDB.sql(f'''
                    SELECT {name_field},LIST(geom) geom
                        FROM(
                            SELECT {name_field}, depth, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM(t1.geom,'EPSG:{crs}','EPSG:4326'))) geom
                                 FROM (
                                 SELECT NAME,depth,unnest(ST_DUMP(geom),recursive:=true) geom
                                    FROM boxes)t1 where st_area(t1.geom)>1)
                GROUP BY {name_field}''')
    
    out_prompts=DUCKDB.sql('''SELECT p.NAME, p.pos_x, p.pos_y,p.neg_X,p.neg_Y,b.geom
                from puntos_interes p
                join boxes_table b
                on p.NAME=b.NAME''').fetchdf()
    

    #list(map(sam_loaded_predict_tile,limit_tiles,limit_boxes,limit_sam_out_images))

    sam_out_dir=folder_check(os.path.join(input_image.folder,'sammed_DEMO_ERNESTO_2')) 
    limit_tiles=[out_prompts['NAME'].to_list()]
    positive_point_prompt=[list(zip(*list(zip(out_prompts['pos_X'],out_prompts['pos_Y']))[i])) for i in range(len(out_prompts))]
    negative_point_prompt=[list(zip(*list(zip(out_prompts['neg_X'],out_prompts['neg_Y']))[i])) for i in range(len(out_prompts))]    
    point_prompt=[positive_point_prompt[i]+negative_point_prompt[i] for i in range(len(out_prompts))]
    point_labels=[[1 for j in range(len(positive_point_prompt[i]))]+[0 for j in range(len(negative_point_prompt[i]))]for i in range(len(out_prompts))]
    #point_labels=[[1 for j in range(len(positive_point_prompt[i]))] for i in range(len(out_prompts))]

    limit_boxes=[list([list(j.values()) for j in i]) for i in out_prompts['geom']]
    depths=[4]
    depth=4
    limit_sam_out_images=[]
    limit_result=[{depths[i]:{'LIMIT_TILES':limit_tiles[i],'LIMIT_BOXES':limit_boxes[i]}for i in range(len(depths))} ]
    results=dict(ChainMap(*limit_result))


    contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,results,depth,contained_sam_out_images,limit_sam_out_images) 
    level_sam_dir=folder_check(os.path.join(sam_out_dir,f'subset_{depth}'))
    sam_limit_dir=os.path.join(level_sam_dir,'limit')

    out_fulls=[os.path.join(sam_limit_dir,os.path.splitext(os.path.basename(p))[0]+'.tif') for p in paths_to_complete]
    [SamGeo_apb.full_to_tif(i,j) for (i,j) in zip(paths_to_complete,out_fulls)]
    contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,results,depth,contained_sam_out_images,limit_sam_out_images) 
    
    sam_loaded_predict_tile_point=partial(predict_tile_points,sam=sam)

    # list(map(sam_loaded_predict_tile_point,limit_tiles[0],limit_boxes,limit_sam_out_images,point_prompt,point_labels))
    list(map(sam_loaded_predict_tile_point,limit_tiles[0],limit_boxes,limit_sam_out_images,point_prompt,point_labels))

    #list(map(sam_loaded_predict_tile,limit_tiles[0],limit_boxes,limit_sam_out_images))
    

def pyramid_sam_apply_geojson(image,prompt_file,lowest_pixel_size,geometry_column,sam):
    
    input_image=Ortophoto(image)
    detections=read_file(prompt_file)
    data_loaded_post_processing=partial(post_processing,pyramid_dir=input_image.get_pyramid(lowest_pixel_size),detections=detections,geometry_column=geometry_column)
    
    data_loaded_geojson_post_processing=partial(post_processing_geojson,output_dir=results_dir,pyramid_dir=input_image.get_pyramid(lowest_pixel_size),detections=detections)
    depths=[depth for depth in range(input_image.pyramid_depth)]

    with ProcessPoolExecutor(5) as Executor:
        geojson_result=list(map(data_loaded_geojson_post_processing,depths))

    results=dict(ChainMap(*geojson_result))
    
    from itertools import chain
    
    contained_boxes=list(chain(*[results[i].get('CONTAINED_BOXES','NO') for i in results.keys()]))
    contained_tiles=list(chain(*[results[i].get('CONTAINED_TILES','NO') for i in results.keys()]))
    limit_boxes=list(chain(*[results[i].get('LIMIT_BOXES','NO') for i in results.keys()]))
    limit_tiles=list(chain(*[results[i].get('LIMIT_TILES','NO') for i in results.keys()]))
    
    sam_out_dir=folder_check(os.path.join(input_image.folder,'sammed_images')) 
    contained_sam_out_images,limit_sam_out_images=[],[]
    for depth in list(reversed(depths)):
        contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,depth,contained_sam_out_images,limit_sam_out_images) 
        
    sam_loaded_predict_tile=partial(predict_tile,sam=sam)
    list(map(sam_loaded_predict_tile,contained_tiles,contained_boxes,contained_sam_out_images))
    list(map(sam_loaded_predict_tile,limit_tiles,limit_boxes,limit_sam_out_images))
    
if __name__=="__main__":
    #choose_model
    #model class has optimal resolution attribute
    from package.sam_utilities import SamGeo_apb
    
    sam = SamGeo_apb(
       model_type="vit_h",
       automatic=False,
       sam_kwargs=None,
       )
    # sam = SamGeo_apb(
    #    model_type="vit_h",
    #    automatic=False,
    #    sam_kwargs={
    #             'points_per_side': 32,
    #             'points_per_batch': 32,
    #             'pred_iou_thresh': 0.88,
    #             'stability_score_thresh': 0.95,
    #             'stability_score_offset': 1.0,
    #             'box_nms_thresh': 0.7,
    #             'crop_n_layers': 0,
    #             'crop_nms_thresh': 0.7,
    #             'crop_overlap_ratio': 512 / 1500,
    #             'crop_n_points_downscale_factor': 1,
    #             'point_grids':  None,
    #             'min_mask_region_area': 0,
    #             'output_mode': "binary_mask",}
    #    )
    #forma=SamGeo_apb.raster_to_vector(r'C:\dev\TFG\data\ORTO_ZAL_BCN\sammed_images_2\subset_2\contained\tile_4096_grid_2_4.tif',
    #                     r'C:\dev\TFG\data\ORTO_ZAL_BCN\sammed_images_2\subset_2\contained\tile_4096_grid_2_4_r.geojson')
    #print(forma)
    t0=time.time()
    #gdf=gpd.read_file(os.path.join(OUT_DIR,'tanks_50c_40iou.geojson'))
    #gdf=prediction_to_bbox(gdf,crs)
    
    #input_image=os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif')
                                  #'ORTO_ZAL_BCN_pyramid','raster','subset_2','tile_4096_grid_0_2.tif'
                                  
    #results_dir=folder_check(os.path.join(input_image.folder,'intersection_results'))
    #grande=Tile('D:\\VICTOR_PACHECO\\CUARTO\\PROCESADO_IMAGEN\\data\\ORTO_ME_BCN\\ORTO_ME_BCN_pyramid\\raster\\subset_2\\tile_4096_grid_4_1.tif')
    #grande.get_children()
    input_image=os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif')
    
    


    #    FAILED ATTEMPT AT USING PREVIOUS IMAGES AS PROMPTS
    # sam.set_image( os.path.join(DATA_DIR,"ORTO_ME_BCN","ORTO_ME_BCN_pyramid","raster","subset_2","tile_4096_grid_4_1.tif"))
    # sam.predict(
    #    mask_input=np.array([cv2.resize(Ortophoto(os.path.join(DATA_DIR,"ORTO_ME_BCN","sammed_images","subset_2","contained","tile_4096_grid_4_1.tif")).raster.ReadAsArray(),
    #                          (256,256),
    #                          interpolation=cv2.INTER_LINEAR)]),
    #    output='prueba_image_prompt.tif',
    #    dtype="uint8"
    # 
    detections=os.path.join(OUT_DIR,'QGIS_BUILDINGS','ORIENTED_BOXES.GEOJSON')
    #detections=os.path.join(OUT_DIR,'tanks_50c_40iou.geojson')
    pyramid_sam_apply(input_image,detections,1024,'geom',sam)
    
    #data_loaded_post_processing=partial(post_processing,pyramid_dir=input_image.pyramid,detections=detections)
    #data_loaded_geojson_post_processing=partial(post_processing_geojson,output_dir=results_dir,,pyramid_dir=input_image.pyramid,detections=detections)
    #depths=[depth for depth in range(input_image.pyramid_depth)]
    
    # t1=time.time()
    # with ProcessPoolExecutor(5) as Executor:
    #     result=list(map(data_loaded_post_processing,depths))
    #     #geojson_result=list(map(data_loaded_geojson_post_processing,depths))
    # results=dict(ChainMap(*result))
    #results=dict(ChainMap(*geojson_result))
    
    # t2=time.time()
    # from itertools import chain
    
    # contained_boxes=list(chain(*[results[i].get('CONTAINED_BOXES','NO') for i in results.keys()]))
    # contained_tiles=list(chain(*[results[i].get('CONTAINED_TILES','NO') for i in results.keys()]))
    # limit_boxes=list(chain(*[results[i].get('LIMIT_BOXES','NO') for i in results.keys()]))
    # limit_tiles=list(chain(*[results[i].get('LIMIT_TILES','NO') for i in results.keys()]))
    
    # [contained_tiles,contained_boxes,limit_tiles,limit_boxes] =[[{level:results[level].get(element,'NO')} for level in results.keys()] for element in results.keys().mapping[0].keys()]
    # contained_boxes=[{i:results[i].get('CONTAINED_BOXES','NO')} for i in results.keys()]
    # contained_tiles=[{i:results[i].get('CONTAINED_TILES','NO')} for i in results.keys()]
    # limit_boxes=[{i:results[i].get('LIMIT_BOXES','NO')} for i in results.keys()]
    # limit_tiles=[{i:results[i].get('LIMIT_TILES','NO')} for i in results.keys()]

    # sam_out_dir=folder_check(os.path.join(input_image.folder,'sammed_images')) 
    # contained_sam_out_images,limit_sam_out_images=[],[]
    # for depth in list(reversed(depths)):
    #     contained_sam_out_images,limit_sam_out_images=create_sam_dirs(sam_out_dir,depth,contained_sam_out_images,limit_sam_out_images) 

    #running
    
    #predict_tile(limit_tiles[0],limit_boxes[0],limit_sam_out_images[0])
    #predict_tile(contained_tiles[0],contained_boxes[0],contained_sam_out_images[0])
    #predict_tile(limit_tiles[245],limit_boxes[245],limit_sam_out_images[245])
    #predict_tile(contained_tiles[183],contained_boxes[183],contained_sam_out_images[183])

    # t3=time.time()
    
    # print(f'''{t1-t0} INICIAL
    #       {t2-t1} PREPARALELEO
    #       {t3-t2} final''')
    # list(map(predict_tile,contained_tiles,contained_boxes,contained_sam_out_images))
    # list(map(predict_tile,limit_tiles,limit_boxes,limit_sam_out_images))
        
    #list(map(predict_tile,contained_tiles,contained_boxes,contained_sam_out_images))
    #predict_tile(limit_tiles[0],limit_boxes[0],limit_sam_out_images[0])
    #predict_tile(contained_tiles[100],contained_boxes[100],contained_sam_out_images[100])

    pass    