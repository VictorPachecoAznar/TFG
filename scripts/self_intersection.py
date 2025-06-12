import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from apb_spatial_computer_vision import DUCKDB,OUT_DIR
from apb_spatial_computer_vision.main import read_file,prediction_to_bbox,duckdb_2_gdf
import geopandas as gpd
import numpy as np

def self_intersection(file):
    gdf=read_file(file)
    
    DUCKDB.sql('''
        SELECT*
        FROM gdf
        ''')
    broken_up=DUCKDB.sql('''
        SELECT unnest(ST_DUMP(geom_1),recursive:=true) geom
        FROM gdf
        ''')
  
    repeated=DUCKDB.sql(
        '''
        SELECT b1.geom
            FROM broken_up b1
                JOIN broken_up b2
                    ON ST_INTERSECTS(b1.geom,b2.geom) 
                        WHERE b1.geom!=b2.geom 
                            GROUP BY b1.geom
    ''')
    
    iou_gdf=DUCKDB.sql(
        '''
        SELECT 
                b1.geom,
                SUM(ST_AREA(ST_UNION(b1.geom,b2.geom))) AS GEOM_UNION,
                SUM(ST_AREA(ST_INTERSECTION(b1.geom,b2.geom))) AS GEOM_INTERSECTION
                    FROM broken_up b1 JOIN broken_up b2
                        ON ST_INTERSECTS(b1.geom,b2.geom)
                            WHERE b1.geom!=b2.geom
                                GROUP BY b1.geom
        ''')
    
    final_iou_gdf=DUCKDB.sql(
        '''
        SELECT *,
            CASE 
                WHEN GEOM_INTERSECTION = 0 THEN NULL 
                ELSE GEOM_INTERSECTION/GEOM_UNION 
            END AS result 
        FROM iou_gdf
        WHERE result IS NOT NULL
        ''')
    print(final_iou_gdf)
    
    #FIX LATER BECAUSE ORIENTED BOUNDING BOXES SHOULD COME FROM THE RESULTS.
    clean=duckdb_2_gdf(iou_gdf,'geom')
    oriented=prediction_to_bbox(clean)
    #temp_oriented=os.path.join(TEMP_DIR,'oriented.geojson')
    #oriented.to_file(temp_oriented)
    #oriented=read_file(temp_oriented)
    
    oriented_coords=[np.array(g.boundary.coords) for g in oriented['geometry']]
    distances=[np.linalg.norm(points[1:] - points[:-1], axis=1) for points in oriented_coords]
    rectangularity=np.array([i.sum()/(i[0]*4) for i in distances])

    clean['rectangularity']=rectangularity
    print(clean)
    # rectangularity=DUCKDB.sql(
    # f''' SELECT 
    #     geom AS bbox,
    #     ST_XMax(bbox) - ST_XMin(bbox) AS width,
    #     ST_YMax(bbox) - ST_YMin(bbox) AS height,
    #     width / height AS aspect_ratio
    # FROM 
    #     oriented ;''')
    
    # os.remove(temp_oriented)

#self_intersection_stats=self_intersection(os.path.join(OUT_DIR,'tanks_50c_40iou.geojson'))
self_intersection(os.path.join(OUT_DIR,'QGIS_BOXES','ORIENTED_BOXES.GEOJSON'))

