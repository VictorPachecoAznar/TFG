from package.raster_utilities import *

if __name__=="__main__":

    [folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,PACKAGE_DIR]]
    base_image = Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif'))
    print(base_image.Y_pixel)
    t0=time()
    base_image.polygonize(1024)
    t1=time()
    print(f'TIME OCURRED:{t1-t0}')