from samgeo import SamGeo
import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from package.raster_utilities import *
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
    t1=time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')
    print('HELLO WORLD!')
