
import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *

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
    r=os.path.join(DATA_DIR,'ORTO_ZAL_BCN_pyramid','subset_0')
    #f1=partial(text_prompt_to_json,root=r)
    
    ejemplo='tile_16384_grid_0_1.tif'
    t=Tile(route=os.path.join(r,ejemplo))
    t.get_children()
    t.get_parents()
    for layer in t.children:
        for tile in layer:
            individual=Tile(tile)
            print(individual.area)
    # text_prompt_to_json(t,'tree')
    

    #a=f1(file=ejemplo,text_prompt='libro')


    # wkts=[]
    # for i in range(len(t.get_children())):
    #      for image in t.children[i]:
    #          print(image)
    #          wkt=Tile(image).wkt
    #          wkts.append(wkt)

    t1=time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')

