
import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *

def text_prompt_to_json(file,text_prompt,root,box_threshold=0.24,text_threshold=0.24):
    tile=Tile(os.path.join(root,file))
    image=tile.raster_path
    if os.path.exists(image):
        return image    
    else:
        raise FileNotFoundError


if __name__=="__main__":
    t0=time()
    r=os.path.join(DATA_DIR,'ORTO_ZAL_BCN_pyramid','subset_0')
    f1=partial(text_prompt_to_json,root=r)
    
    ejemplo='tile_16384_grid_0_1.tif'
    t=Tile(route=os.path.join(r,ejemplo))
    
    a=f1(file=ejemplo,text_prompt='libro')

    wkts=[]
    for i in range(len(t.get_children())):
        for image in t.children:
            print(image)
            wkt=Tile(image).wkt
            wkts.append(wkt)


    gdf=gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(wkts),crs=25831)
    m=gdf.explore()
    m.save(os.path.join(STATIC_DIR,'TILES.html'))
    
    t1=time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')

