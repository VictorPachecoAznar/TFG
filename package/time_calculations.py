import os
import time

def attempt(command):
    t0=time.time()
    os.system(command)
    t1=time.time()
    print(f'TIEMPO TRANSCURRIDO:{t1-t0}')

from osgeo import gdal

comandas=['gdalwarp -te 427314 4574847 428988 4575367 "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_PORT.tif" "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_ZAL_BCN_NOwm.tif"',
          'gdalwarp -te 427314 4574847 428988 4575367 -wm 5000 "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_PORT.tif" "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_ZAL_BCN_NOCPU.tif"',
          'gdalwarp -wo NUM_THREADS=ALL_CPUS -te 427000 4574000 429000 4575500 -wm 5000 "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/raster_translation/FAV20240413_EPSG25831_5cm_F50_MRSID3.sid" "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_ZAL_BCN_A.tif"',
          'gdalwarp -te 427314 4574847 428988 4575367 "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/raster_translation/FAV20240413_EPSG25831_5cm_F50_MRSID3.sid" "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_ZAL_BCN_Rm.tif"']

gdalwarp -wo NUM_THREADS=ALL_CPUS -te 427000 4574680.8 428638.4 4575500 -wm 5000 "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/raster_translation/FAV20240413_EPSG25831_5cm_F50_MRSID3.sid" "C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_ZAL_BCN_A.tif"
bounds=(427314, 4574847, 428988, 4575367)

#-wo NUM_THREADS=ALL_CPUS
#options= gdal.WarpOptions(outputBounds=bounds,multithread=True,warpMemoryLimit=500,warpOptions='NUM_THREADS=8')
# t0=time.time() 
#raster=gdal.Open("C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/raster_translation/FAV20240413_EPSG25831_5cm_F50_MRSID3.sid")
#gdal.Warp("C:/Users/pachecvi/OneDrive - Port de Barcelona/Escritorio/VICTOR/TFG/data/ORTO_ZAL_BCN_intento.tif",raster,options=options)
# t1=time.time()
# print('TIEMPO TRANSCURRIDO:{:4f}'.format(t1-t0))

attempt(comandas[3])

#for comanda in comandas:
#    attempt(comanda)