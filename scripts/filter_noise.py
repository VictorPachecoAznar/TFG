from apb_spatial_computer_vision.main import read_file,duckdb_2_gdf
from apb_spatial_computer_vision import *

# first_iteration=read_file(os.path.join(DATA_DIR,'ORTO_ME_BCN','first_iteration.geojson'))
# second_iteration=read_file(os.path.join(DATA_DIR,'ORTO_ME_BCN','second_iteration.geojson'))
first_iteration=read_file(r'D:\VICTOR_PACHECO\CUARTO\PROCESADO_IMAGEN\data\ORTO_ZAL_BCN\sam_results_qgis_building\first_iteration_qgis_building.geojson')
second_iteration=read_file(r'D:\VICTOR_PACHECO\CUARTO\PROCESADO_IMAGEN\data\ORTO_ZAL_BCN\sam_results_qgis_building\second_iteration_qgis_building.geojson')

duckdb_2_gdf(DUCKDB.sql('''
    SELECT ST_INTERSECTION(a.geom,b.geom) as geom
        FROM
            (SELECT ST_BUFFER(geom,0.5) geom FROM first_iteration
                 ) a
        JOIN (SELECT geom
            FROM second_iteration
                WHERE ST_AREA(geom)>0.5) b
           on ST_INTERSECTS(a.geom,b.geom)'''),'geom').to_parquet(r'D:\VICTOR_PACHECO\CUARTO\PROCESADO_IMAGEN\data\ORTO_ZAL_BCN\refined_segmentation_qgis_building.parquet')
           #os.path.join(DATA_DIR,'ORTO_ME_BCN','clean_second_iteration_buffer.parquet'))