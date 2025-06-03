# from samgeo.text_sam import LangSAM
from apb_spatial_computer_vision.lang_sam_utilities import LangSAM_apb
from apb_spatial_computer_vision import *
from apb_spatial_computer_vision.raster_utilities import Ortophoto
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import pandas as pd
from PIL import Image
import rasterio 
import numpy as np
import time
from apb_spatial_computer_vision.main import duckdb_2_gdf




def text_to_bbox_dino(input_image,text_prompt,output=None):
    tiles_to_check=input_image.get_pyramid_tiles()

    sam = LangSAM_apb()
    predict_prompt=partial(sam.predict_dino,text_prompt=text_prompt,box_threshold=0.24, text_threshold=0.2)

    def predict_save(image):
        pil_image=sam.path_to_pil(image)
        boxes,logits,phrases=predict_prompt(pil_image)
        sam.boxes=boxes
        print('out')
        return sam.save_boxes(dst_crs=input_image.crs)

        
    t0=time.time()
    gdf_list_bboxes_DINO=list(map(predict_save,tiles_to_check))
    t1=time.time()
    print(f'TIME SPENT DOING DINO {t1-t0}')

    for i in range(len(tiles_to_check)):
        gdf_list_bboxes_DINO[i]['NAME']=tiles_to_check[i]

    single_gdf_bboxes_DINO=pd.concat(gdf_list_bboxes_DINO)
    #single_gdf_bboxes_DINO.to_file(os.path.join(OUT_DIR,'groundedDINO','only_dino.geojson'))
    single_gdf_bboxes_DINO['geom']=single_gdf_bboxes_DINO.geometry.to_wkt()
    df_bounding_boxes_DINO=single_gdf_bboxes_DINO[['NAME','geom']]

    input_image.create_tiles_duckdb_table()

    bounding_boxes_DINO=DUCKDB.sql('''
        SELECT ST_GEOMFROMTEXT(geom) AS geom, NAME, CAST(parse_dirpath(name)[-1] AS INTEGER) depth
            FROM df_bounding_boxes_DINO''')


    non_complete_boxes=DUCKDB.sql('''
    SELECT b.geom,b.NAME,b.depth
        from bounding_boxes_DINO b
            JOIN
        tiles AS t
            ON t.NAME=b.NAME
            where ST_area(b.geom)/st_area(t.geom)<0.8''')

    duckdb_2_gdf(DUCKDB.sql(
            '''
            SELECT * FROM non_complete_boxes WHERE depth<2
            '''),'geom').to_file(os.path.join(OUT_DIR,'groundedDINO','buildings_depth_0_1.geojson'))

    DUCKDB.sql('''
        SELECT geom 
            from bounding_boxes_DINO
            GROUP BY name
            ''')

    repeated=DUCKDB.sql(
            '''
            SELECT b1.geom,b1.depth
                FROM bounding_boxes_DINO b1
                    JOIN bounding_boxes_DINO b2
                        ON ST_INTERSECTS(b1.geom,b2.geom) and not ST_CONTAINS(b2.geom,b1.geom)
                            WHERE b1.geom!=b2.geom 
                                GROUP BY b1.geom, b1.depth
        ''')
        

    iou_gdf=DUCKDB.sql(
            '''
            SELECT 
                    b1.geom,LIST(b2.geom)
                    SUM(ST_AREA(ST_UNION(b1.geom,b2.geom))) AS GEOM_UNION,
                    SUM(ST_AREA(ST_INTERSECTION(b1.geom,b2.geom))) AS GEOM_INTERSECTION, b1.depth
                        FROM bounding_boxes_DINO b1 JOIN bounding_boxes_DINO b2
                            ON ST_INTERSECTS(b1.geom,b2.geom)
                                WHERE b1.geom!=b2.geom
                                    GROUP BY b1.geom, b1.depth
            ''')
        
    final_iou_gdf=DUCKDB.sql(
            '''
            SELECT *,
                CASE 
                    WHEN GEOM_INTERSECTION = 0 THEN NULL 
                    ELSE GEOM_UNION/GEOM_INTERSECTION 
                END AS result 
            FROM iou_gdf
            WHERE result IS NOT NULL
            ''')
    
    if output is not None:
        duckdb_2_gdf(bboxes_duckdb).to_file(output)
    
    return bboxes_duckdb
   
# pruebas

# duckdb_2_gdf(DUCKDB.sql(
#         '''        SELECT geom,result FROM(SELECT geom,MAX(result) result FROM(SELECT geom,
#             CASE 
#                 WHEN GEOM_INTERSECTION = 0 THEN NULL 
#                 ELSE GEOM_INTERSECTION/GEOM_UNION
#             END AS result
#             FROM
#         (SELECT 
#                 b1.geom,b2.geom other_geoms,
#                 ST_AREA(ST_UNION(b1.geom,b2.geom)) AS GEOM_UNION,
#                 ST_AREA(ST_INTERSECTION(b1.geom,b2.geom)) AS GEOM_INTERSECTION, b1.depth
#                     FROM non_complete_boxes b1 JOIN non_complete_boxes b2
#                         ON ST_INTERSECTS(b1.geom,b2.geom) and not ST_CONTAINS(b2.geom,b1.geom)
#                             WHERE b1.geom!=b2.geom
#                                 GROUP BY b1.geom, b1.depth,b2.geom,b2.depth)
#                     )group by geom)where result <0.4


#         '''),'geom').to_file(os.path.join(OUT_DIR,'groundedDINO','geom_04_max_.geojson'))


def text_to_bbox_lowres(
        input_image:Ortophoto,
        text_prompt:str,
    ):
    
    tiles_to_check=input_image.get_pyramid_tiles()
    sam = LangSAM_apb()
    predict_prompt=partial(sam.predict_dino,text_prompt=text_prompt,box_threshold=0.24, text_threshold=0.2)

    def predict_save(image):
        pil_image=sam.path_to_pil(image)
        boxes,logits,phrases=predict_prompt(pil_image)
        sam.boxes=boxes
        print('out')
        return sam.save_boxes(dst_crs=input_image.crs)
        
    gdf_list_bboxes_DINO=list(map(predict_save,tiles_to_check))

    for i in range(len(tiles_to_check)):
        gdf_list_bboxes_DINO[i]['NAME']=tiles_to_check[i]

    single_gdf_bboxes_DINO=pd.concat(gdf_list_bboxes_DINO)
    #single_gdf_bboxes_DINO.to_file(os.path.join(OUT_DIR,'groundedDINO','only_dino.geojson'))
    single_gdf_bboxes_DINO['geom']=single_gdf_bboxes_DINO.geometry.to_wkt()
    df_bounding_boxes_DINO=single_gdf_bboxes_DINO[['NAME','geom']]

    input_image.create_tiles_duckdb_table()
    bounding_boxes_DINO=DUCKDB.sql('''
        SELECT ST_GEOMFROMTEXT(geom) AS geom, NAME, CAST(parse_dirpath(name)[-1] AS INTEGER) depth
            FROM df_bounding_boxes_DINO''')
    
    bboxes_duckdb=DUCKDB.sql('''
        SELECT b.geom,b.NAME,b.depth
            from bounding_boxes_DINO b
            where depth=(SELECT MIN(depth) from bounding_boxes_DINO )''')



if __name__=='__main__':
    text_prompt = "building"
    input_image_path=os.path.join(DATA_DIR,"ORTO_ZAL_BCN.tif")
    input_image=Ortophoto(input_image_path)