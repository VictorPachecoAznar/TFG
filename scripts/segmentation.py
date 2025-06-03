# from samgeo import SamGeo
import os,sys
import time
# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from apb_spatial_computer_vision.__init__ import DATA_DIR,OUT_DIR
from apb_spatial_computer_vision.raster_utilities import Tile


def text_prompt():
    
    from samgeo.text_sam import LangSAM
    langSam = LangSAM()
    image=os.path.join(DATA_DIR,'ORTO_ZAL_BCN_pyramid','subset4','tile_1024_grid_08_12.tif')
    langSam.set_image(image)
    text_prompt = "buildings"
    langSam.predict(image, text_prompt, box_threshold=0.24, text_threshold=0.3)
    langSam.show_anns(
    cmap="Greens",
    box_color="red",
    title="Automatic Segmentation of buildings",
    blend=True,
    output='out.tif'
    )
    langSam.raster_to_vector('out.tif','edificios2.geojson')

def box_prompt():
    from apb_spatial_computer_vision.sam_utilities import SamGeo_apb
    sam = SamGeo_apb(
    model_type="vit_h",
    automatic=False,
    sam_kwargs=None,
    )   
    tile=Tile(r'D:\VICTOR_PACHECO\CUARTO\PROCESADO_IMAGEN\data\ORTO_ME_BCN_pyramid\subset_2\tile_4096_grid_2_2.tif')
    images=tile.get_siblings()
    boxes=os.path.join(OUT_DIR,'tanks_50c_40iou.geojson')
    count=0
    for image in images:
        sam.set_image(image)
        sam.predict(boxes=boxes, point_crs="EPSG:25831", output=os.path.join(folder_check(os.path.join(OUT_DIR,'sammed')),f"mask{count}.tif"), dtype="uint8")
        count+=1
        
if __name__=="__main__":
    #complete_image=Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN.TIF'))           
        # DEGRADE RESOLUTION
        #gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_58_98.tif'),xRes=0.1,yRes=0.1)
        #gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_0_0.tif'),xRes=0.1,yRes=0.1,resampleAlg='average')
    #complete_image.create_pyramid(1024)
    # sam = SamGeo(
    #     model_type="vit_h",
    #     sam_kwargs=None,
    # )
    # sam.image_to_image
    t0=time()
    boxes=os.path.join(OUT_DIR,'tanks_50c_40iou.geojson')
    gdf=gpd.read_file(boxes)
    gdf['WIDTH']=gdf.geometry.convex_hull.bounds['maxx']-gdf.geometry.convex_hull.bounds['minx']
    gdf['HEIGHT']=gdf.geometry.convex_hull.bounds['maxy']-gdf.geometry.convex_hull.bounds['miny']
    gdf['ASPECT_RATIO']=gdf['HEIGHT']/gdf['WIDTH']
    outliars=gdf[(gdf['ASPECT_RATIO']>1.2)|(gdf['ASPECT_RATIO']<0.8)]
    
    #box_prompt()
    t1=time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')
    print('HELLO WORLD!')
