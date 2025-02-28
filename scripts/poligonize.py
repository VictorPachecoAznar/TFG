import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *

if __name__=="__main__":
    t0=time()
    [folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,SCRIPTS_DIR]]
    base_image = Ortophoto(os.path.join(DATA_DIR,'ORTO_PORT.tif'))
    print(base_image.Y_pixel)
    #base_image.polygonize(1024)
    t1=time()
    print(f'TIME OCURRED:{t1-t0}')