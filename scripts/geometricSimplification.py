import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *
import geopandas as gpd
import shapely

def find_intersection_centroid(tile,gdf):
    
    s1=gdf['geometry']
    s3=gpd.GeoSeries.from_wkt([tile.wkt],crs=tile.crs)
    puntos_inside=s1.intersection(s3[0])
    newdf=gpd.GeoDataFrame(geometry=puntos_inside,crs=tile.crs)
    geo_prompt=newdf[newdf['geometry'].area==newdf['geometry'].area.max()].reset_index(drop=True)['geometry'][0].centroid
    if geo_prompt.is_empty==False:
        coords= [geo_prompt.x,geo_prompt.y]
        return coords

def safe_append(list,element):
    if element is not None:
        list.append(element)

if __name__=="__main__":
    t0=time()
    points=[]

    ortos_to_check=['tile_1024.0_grid_11_8.tif','tile_1024.0_grid_10_7.tif','tile_1024.0_grid_11_7.tif','tile_1024.0_grid_10_8.tif']
    gdf=gpd.read_file(os.path.join(BASE_DIR,'collab','rotonda.geojson'))
    #gdf=gpd.read_file(os.path.join(DATA_DIR,'multipolygon.shp'))
    for image in ortos_to_check:
        complete_image=Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_Am_pyramid','subset4',image))  
        safe_append(points,find_intersection_centroid(complete_image,gdf))
    
    t1=time()

    import numpy as np
    p=np.array(points)
    result=gpd.GeoDataFrame(geometry=gpd.points_from_xy(p[:,0],p[:,1]),crs=25831)
    m=result.explore()
    m.save('puntos.html')
    print(points)
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')