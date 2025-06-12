
import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from apb_spatial_computer_vision.raster_utilities import *

def text_prompt_to_json(tile,text_prompt,box_threshold=0.24,text_threshold=0.24):
    image=tile.raster_path
    tile.get_children()
    print(tile.smallest_children)

    # if os.path.exists(image):
    #     return image    
    # else:
    #     raise FileNotFoundError
    
if __name__=="__main__":
    t0=time()
    r=os.path.join(DATA_DIR,'ORTO_ZAL_BCN_pyramid','subset_3')
    #f1=partial(text_prompt_to_json,root=r)
    
    #ejemplo='tile_16384_grid_0_1.tif'
    ejemplo='tile_2048_grid_5_00.tif'
    ejemplo2='tile_2048_grid_5_01.tif'

    t=Tile(path=os.path.join(r,ejemplo))
    t2=Tile(os.path.join(r,ejemplo2))

    t==t2
    t.get_children()
    t.get_parents()
    t.get_siblings()
    tiles=[Tile(s) for s in t.siblings]
    Ortophoto.mosaic_rasters([t.siblings[0],t.siblings[2],tiles[1]])
    print(t.parents[-1])

    for layer in t.children:
        new=t.children[1][0]
        #print(new.width)
        for tile in layer:
            individual=Tile(tile)

    print(new.width)
    # text_prompt_to_json(t,'tree')
    

    #a=f1(file=ejemplo,text_prompt='libro')
wkts=0
gdf=gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(wkts),crs=25831)
m=gdf.explore()
m.save(os.path.join(STATIC_DIR),'curve_poly.html')
    # wkts=[]
    # for i in range(len(t.get_children())):
    #      for image in t.children[i]:
    #          print(image)
    #          wkt=Tile(image).wkt
    #          wkts.append(wkt)

t1=time()
print(f'TIEMPO TRANSCURRIDO {t1-t0}')

