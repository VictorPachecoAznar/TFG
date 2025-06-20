# from apb_spatial_computer_vision import *
from apb_spatial_computer_vision.main import *
from apb_spatial_computer_vision.raster_utilities import Ortophoto
    
def create_first_iteration(result,segmentation_name,):    
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
    
    


def create_second_iteration(
    input_image: Ortophoto,
    low_resolution_geometries_duckdb:duckdb.DuckDBPyRelation,
    min_expected_element_area:float=0.5,
    lowest_pixel_size:int=1024
                                ):
    
    # INPUTS
    input_image.create_tiles_duckdb_table(lowest_pixel_size)
    first_iteration_predictions_tile=low_resolution_geometries_duckdb.select('geom')
    
    first_iteration_predictions_tile=DUCKDB.sql('''SELECT ST_GEOMFROMTEXT(d.wkt) as geom
               from wkt_first_iteration d''')
    
    first_iteration_predictions=DUCKDB.sql('''SELECT unnest(ST_DUMP(ST_GEOMFROMTEXT(d.wkt)),recursive:=true) as geom
               from df_first_iteration d''')

    DUCKDB.sql(
            f'''CREATE TABLE unido AS SELECT t.NAME, t.depth,t.geom AS tile_geom, g.geom AS predict_geom 
                FROM (SELECT parse_filename(NAME, false, 'system') as parsed_NAME, depth, geom, NAME
                    FROM tiles) t 
                JOIN (SELECT geom
                    FROM first_iteration_predictions_tile) g
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
    #box_prompts=list(zip(tile_names,extents_list))

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
    
    sam_out_dir=folder_check(os.path.join(input_image.folder,'sam_results')) 
    limit_tiles=[out_prompts['NAME'].to_list()]
    positive_point_prompt=[out_prompts['positive_coords'].to_list()]
    negative_point_prompt=[out_prompts['negative_coords'].to_list()]

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
    
    
    
    ####################################################### TODA ESTA ZONA ES SUSCEPTIBLE DE SER OTRA FUNCIÓN #####################################
    
    second_iteration_sammed_mosaic=os.path.join(sam_out_dir,'resultado_final2.tif')
    second_iteration_sammed_vector=os.path.join(input_image.folder,'second_iteration.geojson')

    Ortophoto.mosaic_rasters(successful_contained_2,second_iteration_sammed_mosaic,pixel_value_to_be_ignored=0,)
    wkt_second_iteration=SamGeo_apb.raster_to_vector(second_iteration_sammed_mosaic,output=second_iteration_sammed_vector,dst_crs=input_image.crs)
    
    df_second_iteration=pd.DataFrame(
        {'wkt':np.array(wkt_second_iteration)},
        index=[1])
    
    second_iteration_predictions=DUCKDB.sql('''SELECT ST_GEOMFROMTEXT(d.wkt) as geom
                from df_second_iteration d''')
    
    duckdb_2_gdf(DUCKDB.sql('''
        SELECT ST_INTERSECTION(a.geom,b.geom) as geom
            FROM
                (SELECT ST_BUFFER(geom,0.5) geom FROM first_iteration_predictions
                    ) a
            JOIN (SELECT geom
                FROM second_iteration_predictions
                    WHERE ST_AREA(geom)>0.5) b
            on ST_INTERSECTS(a.geom,b.geom)'''),'geom').to_parquet(os.path.join(input_image.folder,'clean_second_iteration_buffer.parquet'))  
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
