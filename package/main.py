from package import *
from package.raster_utilities import Ortophoto,Tile,folder_check

from concurrent.futures import ProcessPoolExecutor

import geopandas as gpd, pandas as pd, numpy as np
import time
from functools import partial
from collections import ChainMap

print(folder_check(TEMP_DIR))

def choose_model(name):
    #CREAR DATASET
    pass

def prediction_to_bbox(gdf):
    wkts=[g.boundary.oriented_envelope.wkt for g in gdf.geometry]
    #nl= [x for xs in li for x in xs]
    newgdf=gpd.GeoDataFrame(gdf,geometry=gpd.GeoSeries.from_wkt(wkts),crs=25831)
    return newgdf

def read_file(path,DUCKDB=DUCKDB):
    return DUCKDB.sql(f'''SELECT *
            FROM ST_READ('{path}')''')
    
def duckdb_2_gdf(duck:duckdb.DuckDBPyRelation,geometry_column):
    temp='affected.csv'
    DUCKDB.sql(f'''COPY duck TO '{temp}' WITH (HEADER, DELIMITER ';')''')
    df=pd.read_csv(temp,sep=';')
    geodf=gpd.GeoDataFrame(df,geometry=gpd.GeoSeries.from_wkt(df[geometry_column]),crs=25831)
    geodf=geodf.drop(columns=[geometry_column])
    os.remove(temp)
    return geodf

def filter_level(detections,pyramid_dir,depth,geometry_column):
    
    tiles=read_file(os.path.join(pyramid_dir,'vector',f"subset_{depth}.geojson"))
    detections=detections.select('*')
    #CONNECT PREDICTION TO TILE
    intersection=DUCKDB.sql(
        f'''SELECT t.NAME, t.geom AS tile_geom, g.{geometry_column} AS predict_geom
            FROM tiles t 
            JOIN detections g
                ON ST_INTERSECTS(t.geom,g.{geometry_column})''')
    
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
    
    relation_gdf=duckdb_2_gdf(combi,'geom')
    
    #fun=lambda x:[i for i in x]
    array=[i for i in cleans_indexed['unique_tiles'].fetchnumpy()['unique_tiles']]
    names=[os.path.join(f'virtuals_{depth}',str(i)) for i in range(1,len(cleans_indexed)+1)]
    
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
    db=table.filter(f"{column}= '{name}'")
    DUCKDB.sql(
        f'''COPY db
            TO '{file_name}.geojson'
            WITH (FORMAT gdal, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES',SRS 'EPSG:{crs}');
        ''')
    
def create_files_from_sql(tab,column,tile_names,file_names,crs=25831):
    for (name,filename) in zip(tile_names,file_names):
        create_file_from_sql(tab,column,name,filename,crs)

if __name__=="__main__":
    #choose_model
    #model class has optimal resolution attribute
    from package.sam_utilities import SamGeo_apb
    
    sam = SamGeo_apb(
       model_type="vit_h",
       automatic=False,
       sam_kwargs=None,
       )
    
    t0=time.time()
    #gdf=gpd.read_file(os.path.join(OUT_DIR,'tanks_50c_40iou.geojson'))
    #gdf=prediction_to_bbox(gdf)
    input_image=Tile(os.path.join(DATA_DIR,'ORTO_ZAL_BCN','ORTO_ZAL_BCN_pyramid','raster','subset_2','tile_4096_grid_0_2.tif'))
    results_dir=folder_check(os.path.join(OUT_DIR,'intersection_results'))
    
    def create_bboxes_sam(table,name_field,crs=25831,geometry_column='geom'):
        sel_table=table.select('*')
        # boxes_table=DUCKDB.sql(f'''
        #     SELECT {name_field},LIST(geom) geom
        #     FROM(SELECT {name_field}, ST_FLIPCOORDINATES(ST_EXTENT(ST_TRANSFORM({geometry_column},'EPSG:25831','EPSG:4326'))) geom
        #             FROM sel_table)
        #     GROUP BY {name_field}''')
        boxes_table=DUCKDB.sql(f'''
             SELECT {name_field},LIST(geom) geom
             FROM(SELECT {name_field}, ST_EXTENT({geometry_column}) geom
                     FROM sel_table)
             GROUP BY {name_field}''')
        tile_names=boxes_table.fetchnumpy()[name_field]
        boxes=[list([list(j.values()) for j in i]) for i in boxes_table.fetchnumpy()['geom']]
        return tile_names, boxes
    
    def create_geojson_mass(table,name_field,output_directory,crs=25831,geometry_column='geom'):
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
        tiles_matrices=[Ortophoto(i).raster.ReadAsArray() for i in tiles_names]
        create_files_from_sql(tab=sel_tab,column=name_field,tile_names=tiles_names,file_names=files_names,crs=crs)
        return tiles_matrices,files_names

    def create_level_dirs(results_dir,depth):
        level_dir=folder_check(os.path.join(results_dir,str(depth)))
        contained_dir=folder_check(os.path.join(level_dir,'contained'))
        limit_dir=folder_check(os.path.join(level_dir,'limit'))
        return contained_dir,limit_dir
        
    def post_processing(depth,input_image,detections):
        pyramid_dir=input_image.pyramid
        contained,limit=filter_level(detections,pyramid_dir,depth,'geom')
        contained_tiles,contained_boxes=create_bboxes_sam(contained,'NAME')
        limit_tiles,limit_boxes=create_bboxes_sam(limit,'MOSAIC')
        return {depth:{'CONTAINED_TILES':contained_tiles,'CONTAINED_BOXES':contained_boxes,'LIMIT_TILES':limit_tiles,'LIMIT_BOXES':limit_boxes}}
    
    def post_processing_geojson(depth,input_image,detections,results_dir):
        pyramid_dir=input_image.pyramid
        contained_dir,limit_dir=create_level_dirs(results_dir,depth)
        contained,limit=filter_level(detections,pyramid_dir,depth,'geom')
        contained_tiles,contained_boxes=create_geojson_mass(contained,'NAME',contained_dir)
        limit_tiles,limit_boxes=create_geojson_mass(limit,'MOSAIC',limit_dir)
        return {depth:{'CONTAINED_TILES':contained_tiles,'CONTAINED_BOXES':contained_boxes,'LIMIT_TILES':limit_tiles,'LIMIT_BOXES':limit_boxes}}
    
    detections=read_file(os.path.join(OUT_DIR,'QGIS_BUILDINGS','ORIENTED_BOXES.GEOJSON'))
    data_loaded_post_processing=partial(post_processing,input_image=input_image,detections=detections)
    data_loaded_geojson_post_processing=partial(post_processing_geojson,results_dir=results_dir,input_image=input_image,detections=detections)
    depths=[depth for depth in range(input_image.pyramid_depth)]
    
    with ProcessPoolExecutor() as Executor:
        result=list(map(data_loaded_post_processing,depths))
        geojson_result=list(map(data_loaded_geojson_post_processing,depths))
    results=dict(ChainMap(*result))
    results=dict(ChainMap(*geojson_result))
    
    from itertools import chain
    
    contained_boxes=list(chain(*[results[i].get('CONTAINED_BOXES','NO') for i in results.keys()]))
    contained_tiles=list(chain(*[results[i].get('CONTAINED_TILES','NO') for i in results.keys()]))
    limit_boxes=list(chain(*[results[i].get('LIMIT_BOXES','NO') for i in results.keys()]))
    limit_tiles=list(chain(*[results[i].get('LIMIT_TILES','NO') for i in results.keys()]))

    
    
    def predict_tile(image_path,boxes,out_name):
        """Apply SAM using BBOX.

        Args:
            image_path (str | np.array): Path to the tile or numpy array stemming from GDAL ReadAsArray(), or in this package tems, Ortophoto.raster.ReadAsArray()
            boxes (Iterable [-str] |str [GeoJSON]): Nested list of bounds (X_min,Y_min,X_max,Y_max), or the path to a GeoJSON path containing Polygon geometries.          
            out_name (str): Name for the output file, can be either vector (GeoJSON) or Raster (GeoTIFF)
        """
        if isinstance(boxes,str):
            boxes+='.geojson'
            if os.path.exists(boxes):
                sam.set_image(image_path)
                try:
                    sam.predict(boxes=boxes, point_crs="EPSG:4326", output=out_name, dtype="uint8")
                except:
                    print(f'{out_name} could not be loaded')

    sam_out_dir=folder_check(os.path.join(OUT_DIR,'sammed_images'))
    sam_contained_dir=folder_check(os.path.join(sam_out_dir,'contained'))
    sam_limit_dir=folder_check(os.path.join(sam_out_dir,'limit'))

    contained_sam_out_images=[os.path.join(sam_contained_dir,os.path.basename(i)) for i in contained_boxes]
    limit_sam_out_images=[os.path.join(sam_limit_dir,os.path.basename(i)) for i in limit_boxes]

    #running
    list(map(predict_tile,contained_tiles,contained_boxes,contained_sam_out_images))
    list(map(predict_tile,limit_tiles,limit_boxes,limit_sam_out_images))
    
        
    t1=time.time()
    print(f'{t1-t0}')
    pass    