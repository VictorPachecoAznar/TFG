import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *
if __name__=="__main__":
    t0=time()
    complete_image=Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN.TIF'))           
    # DEGRADE RESOLUTION
    #gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_58_98.tif'),xRes=0.1,yRes=0.1)
    #gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_0_0.tif'),xRes=0.1,yRes=0.1,resampleAlg='average')
    complete_image.create_pyramid(1024)
    t1=time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')