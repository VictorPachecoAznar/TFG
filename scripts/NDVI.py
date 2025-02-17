import os,sys
import time

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *
import cv2 as cv
import numpy as np

def safe_divide(a,b):
    return np.divide(a,b,out=np.zeros_like(a),where=b!=0)

if __name__=="__main__":
    t0=time()
    complete_image=Ortophoto(os.path.join(DATA_DIR,"RS_ZAL_BCN_LARGER_pyramid\subset0/tile_1024.0_grid_0_0.tif"))
    interesting_bands=complete_image
    mat=complete_image.raster.ReadAsArray()

    nir=mat[9].astype(np.float64)
    red=mat[3].astype(np.float64)
    ndvi=safe_divide(nir-red,nir+red)
    ndvi=np.nan_to_num(ndvi,-99999)
    binary=np.where(ndvi>0.5,255,0)

    image=binary.astype(np.uint8)
    fileformat = "GTiff"
    driver = gdal.GetDriverByName(fileformat)

    #######################################################################
    ################ INFORMACIÓN SOBRE LOS METADATOS  #####################
    #######################################################################

    # metadata = driver.GetMetadata()
    # if metadata.get(gdal.DCAP_CREATE) == "YES":
    #     print("Driver {} supports Create() method.".format(fileformat))

    # if metadata.get(gdal.DCAP_CREATECOPY) == "YES":
    #     print("Driver {} supports CreateCopy() method.".format(fileformat))

    dst_filename=os.path.join(DATA_DIR,'NDVI.TIF')
    driver=gdal.GetDriverByName('GTiff')
    complete_image.cloneBand(image)

    ndvi_ds= driver.Create(dst_filename, xsize=image.shape[1], ysize=image.shape[0],
                    bands=1, eType=gdal.GDT_Byte)
    ndvi_ds.SetGeoTransform(complete_image.GT)
    ndvi_ds.SetProjection(complete_image.dstSRS_wkt)
    ndvi_ds.GetRasterBand(1).WriteArray(image)
    ndvi_ds=None


    cv.imshow('foto',image)
    cv.waitKey(0)

    
    #complete_image.create_pyramid(1024)
    t1=time()
    print(f'TIEMPO TRANSCURRIDO {t1-t0}')