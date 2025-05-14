from package.main import read_file,duckdb_2_gdf
from package import *

first_iteration=read_file(os.path.join(DATA_DIR,'ORTO_ME_BCN','first_iteration.geojson'))
second_iteration=read_file(os.path.join(DATA_DIR,'ORTO_ME_BCN','second_iteration.geojson'))

duckdb_2_gdf(DUCKDB.sql('''
    SELECT ST_INTERSECTION(a.geom,b.geom) as geom
        FROM
            (SELECT ST_BUFFER(geom,0.5) geom FROM first_iteration
                 ) a
        JOIN (SELECT geom
            FROM second_iteration
                WHERE ST_AREA(geom)>0.5) b
           on ST_INTERSECTS(a.geom,b.geom)'''),'geom').to_parquet(os.path.join(DATA_DIR,'ORTO_ME_BCN','clean_second_iteration_buffer.parquet'))