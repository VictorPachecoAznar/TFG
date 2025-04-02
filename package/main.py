import os,sys
# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from package import *
import geopandas as gpd
from package.raster_utilities import Ortophoto,Tile,folder_check
from concurrent.futures import ProcessPoolExecutor
import time
import pandas as pd
from functools import partial
folder_check(TEMP_DIR)

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
            WITH (FORMAT gdal, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES',SRS 'EPSG:{crs}' );
        ''')
    
def create_files_from_sql(tab,column,tile_names,file_names,crs=25831):
    
    for (name,filename) in zip(tile_names,file_names):
        create_file_from_sql(tab,column,name,filename,crs)

if __name__=="__main__":
    #choose_model
    #model class has optimal resolution attribute
    from samgeo import SamGeo
    
    sam = SamGeo(
      model_type="vit_h",
      automatic=False,
      sam_kwargs=None,
      )
    
    t0=time.time()
    #gdf=gpd.read_file(os.path.join(OUT_DIR,'tanks_50c_40iou.geojson'))
    #gdf=prediction_to_bbox(gdf)
    input_image=Tile(os.path.join(DATA_DIR,'ORTO_ZAL_BCN','ORTO_ZAL_BCN_pyramid','raster','subset_2','tile_4096_grid_0_2.tif'))
    results_dir=folder_check(os.path.join(OUT_DIR,'intersection_results'))
    
    for depth in range(input_image.pyramid_depth):
        
        detections=read_file(os.path.join(OUT_DIR,'QGIS_BUILDINGS','ORIENTED_BOXES.GEOJSON'))
        pyramid_dir=input_image.pyramid
        exiters,final=filter_level(detections,pyramid_dir,depth,'geom')

        level_dir=folder_check(os.path.join(results_dir,str(depth)))
        contained_dir=folder_check(os.path.join(level_dir,'contained'))
        limit_dir=folder_check(os.path.join(level_dir,'limit'))
        
        def create_geojson_mass(table,name_field,output_directory,crs=25831,geometry_column='geom'):
            table_relation=table.select('*')
            select=DUCKDB.sql(f'''SELECT {name_field},ST_COLLECT(LIST({geometry_column})) geom
                FROM table_relation
                GROUP BY {name_field}
            ''')
            tile_names=list(select.fetchnumpy()[name_field])
            file_names=[os.path.join(output_directory,os.path.splitext(os.path.basename(t))[0]) for t in tile_names]
            create_files_from_sql(select,name_field,tile_names,file_names,crs)
        
        create_geojson_mass(exiters,'NAME',contained_dir)
        create_geojson_mass(final,'MOSAIC',limit_dir)
        
        # tile_names=list(out.fetchnumpy()['NAME'])
        
        # tile_ids=[os.path.basename(t) for t in tile_names]
        # file_names=[os.path.join(contained_dir,os.path.basename(t)) for t in tile_names]
        
        # create_files_from_sql(out,'NAME',tile_names,file_names)
        # create_file_from_sql(final,'MOSAIC')
    

            
    
    # def create_file_from_sql(query,file_name):
    #     DUCKDB.sql(
    #         f'''COPY {query} TO '{file_name}.geojson'
    #         WITH (FORMAT gdal, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES');
    #         ''')

        
    # create_from_name=partial(create_file_from_sql,
    #                         query='''
    #     SELECT {}
    #     FROM {}
    #     ''')
    
    #input_image=Ortophoto(os.path.join(DATA_DIR,'ORTO_ME_BCN_resolutions','5cm','0.tif'))
    #input_image=Tile(os.path.join(DATA_DIR,'ORTO_ME_BCN_pyramid','subset_2','tile_4096_grid_0_2.tif'))
    #input_image2=Ortophoto(r'd:\VICTOR_PACHECO\CUARTO\PROCESADO_IMAGEN\data\ORTO_ME_BCN_pyramid\subset_3\tile_2048_grid_03_07.tif')
    #images=[input_image,input_image2]
    count=0

    #geojson=os.path.join(OUT_DIR,)
    #sam.predict(boxes=geojson, point_crs="EPSG:4326", output="mask9.tif", dtype="uint8")

    # for image in images:
    #     sam.set_image(image.raster_path)
    #     sam.predict(boxes=geojson, point_crs="EPSG:4326", output=os.path.join(folder_check(os.path.join(OUT_DIR,'sammed')),f"mask{count}.tif"), dtype="uint8")
    #     count+=1
    
    out_name=os.path.join(folder_check(os.path.join(OUT_DIR,'sammed')),f"mask{count}.tif")
    
    def predict_tile(image_path,geojson,out_name):
        sam.set_image(image_path)
        sam.predict(boxes=geojson, point_crs="EPSG:4326", output=out_name, dtype="uint8")
    
    #predict_tile(input_image2.raster_path,)


    #pyramid_dir=folder_check(os.path.join(DATA_DIR,os.path.basename(input_image.raster_path).split('.')[0])+'_pyramid')

    #pyramid_dir=os.path.join(DATA_DIR,'ORTO_ME_BCN_pyramid')
    #depth=2
    

        
    t1=time.time()
    print(f'{t1-t0}')
    pass    