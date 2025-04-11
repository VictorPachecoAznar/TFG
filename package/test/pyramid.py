import os,sys
import time

from package.raster_utilities import Ortophoto
from package import *
import shutil
import matplotlib.pyplot as plt
if __name__=="__main__":
    t0=time.time()
#         complete_image.create_gdal_parallelized_resolutions(5)

#         own_parallelized.append(t1-t0)
    complete_image=Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif'),folder=os.path.join(DATA_DIR,'ORTO_ZAL_BCN'))    

    #shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ME_BCN_pyramid'))   

    # DEGRADE RESOLUTION
    #gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_58_98.tif'),xRes=0.1,yRes=0.1)
    #gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_0_0.tif'),xRes=0.1,yRes=0.1,resampleAlg='average')
    complete_image.create_pyramid(1024)
    t1=time.time()
    print(f'TIEMPO TRANSCURRIDO{t1-t0}')
    own_parallelized=[]
    for i in range(1):
        t0=time.time()
        complete_image.create_gdal_parallelized_resolutions(5)
        t1=time.time()
        own_parallelized.append(t1-t0)
#       shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_resolutions'))
        
    # times_parallelized=[]
    # for i in range(1):
    #     t0=time.time()
    #     complete_image.create_resolutions(5)
    #     t1=time.time()
    #     times_parallelized.append(t1-t0)
    #     #shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_resolutions'))

    # print(complete_image.area)
    # parallelized_time=t1-t0
    # print(f'TIEMPO TRANSCURRIDO {parallelized_time}')
    
    # times_non_parallelized=[]
    # for i in range(1):
    #     t2=time.time()
    #     complete_image.create_non_parallelized_resolutions(5)
    #     t3=time.time()
    #     times_non_parallelized.append(t3-t2)
    #     shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_resolutions'))
        


    # data=[times_parallelized,times_non_parallelized,own_parallelized]
    # # [[81.96791672706604], [181.64886450767517], [179.33391308784485]]
    
    # print(data)
    # ax=plt.axes()
    # plt.boxplot(data)    
    # plt.title('CREACIÓN DE IMÁGENES CON DISTINTAS RESOLUCIONES')
    # #ax.
    # plt.show()
    # print('picture')
    
        
    
    
    
