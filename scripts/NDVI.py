import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision.sam_utilities import raster_to_vector
import subprocess
from apb_spatial_computer_vision import DATA_DIR,OUT_DIR
import time
#import cv2 as cv
import numpy as np

def safe_divide(a,b):
    """Divides float numpy arrays avoiding zero division errors

    Args:
        a (np.array (dtype:float*)): Numeric array of the same 
        b (np.array (dtype:float*)): Contains numbers

    Returns:
        np.array: array with the divided values, and zero where b=0.
        
    """
    return np.divide(a,b,out=np.zeros_like(a),where=b!=0)


if __name__=="__main__":
    t0=time.time()
    complete_image=Ortophoto(os.path.join(DATA_DIR,"RS_ZAL_BCN.tif"))
    interesting_bands=complete_image
    mat=complete_image.raster.ReadAsArray()

    nir=mat[9].astype(np.float64)
    red=mat[3].astype(np.float64)
    ndvi=safe_divide(nir-red,nir+red)
    ndvi=np.nan_to_num(ndvi,-99999)
    binary=np.where(ndvi>0.5,255,0)

    image=binary.astype(np.uint8)

    #######################################################################
    ################ INFORMACIÓN SOBRE LOS METADATOS  #####################
    #######################################################################

    # metadata = driver.GetMetadata()
    # if metadata.get(gdal.DCAP_CREATE) == "YES":
    #     print("Driver {} supports Create() method.".format(fileformat))

    # if metadata.get(gdal.DCAP_CREATECOPY) == "YES":
    #     print("Driver {} supports CreateCopy() method.".format(fileformat))

    dst_filename=os.path.join(DATA_DIR,'RS_NDVI_COMPLETE.TIF')
    complete_image.cloneBand(image,dst_filename)
    dst_geojson=os.path.join(OUT_DIR,'ndvi.geojson')
    raster_to_vector(dst_filename,dst_geojson,dst_crs=complete_image.crs)
    
    # command=f'gdal_polygonize {dst_filename} -f "GeoJSON" {dst_geojson}'
    # subprocess.Popen(command,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t1=time.time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')
    #cv.imshow('foto',image)
    #cv.waitKey(0)

    #complete_image.create_pyramid(1024)