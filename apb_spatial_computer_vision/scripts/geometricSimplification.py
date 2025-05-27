import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from apb_spatial_computer_vision.raster_utilities import Tile
from apb_spatial_computer_vision.vector_utilities import VectorDataset,list_to_html
from apb_spatial_computer_vision.__init__ import DATA_DIR,BASE_DIR

import geopandas as gpd

def safe_append(list,element):
    if element is not None:
        list.append(element)

if __name__=="__main__":
    points=[]
    first_image=Tile(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_pyramid','subset_4','tile_1024_grid_10_07.tif'))
    tiles=[Tile(i) for i in first_image.get_siblings()]

    # print(tiles)
    # print(first_image.get_parents()[3][0])
    # print(Tile(first_image.get_parents()[3][0]).get_siblings())

    rotonda=VectorDataset(os.path.join(BASE_DIR,'collab','rotonda.geojson'))
    gdf=gpd.read_file(os.path.join(BASE_DIR,'collab','rotonda.geojson'))

    # gdf=gpd.read_file(os.path.join(DATA_DIR,'multipolygon.shp'))
    
    # for image in ortos_to_check:
    #     complete_image=Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_Am_pyramid','subset4',image))  
    #     safe_append(points,find_intersection_centroid(complete_image,gdf))
    point_list=[t.find_intersection_centroid(gdf) for t in tiles]
    from math import isnan
    clean=[i for i in point_list if i is not None]
    list_to_html(clean,'punticos.html')