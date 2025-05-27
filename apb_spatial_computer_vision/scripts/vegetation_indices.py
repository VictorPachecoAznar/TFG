from apb_spatial_computer_vision import *
from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision.scripts.NDVI import safe_divide
import numpy as np

import cv2 as cv
image=os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif')
zal=Ortophoto(os.path.join(DATA_DIR,'ORTO_ZAL_BCN.tif'))#,'ORTO_ZAL_BCN_pyramid','raster','subset_4','tile_1024_grid_00_00.tif'))
r,b,g=mat=zal.raster.ReadAsArray()
#passar a float
gli=(2*g-r-b)/(2*g+r+b)
#Cbinary=np.where(gli>50,255,0)
zal.cloneBand(gli,(os.path.join(DATA_DIR,'gli_float.tif')))
# rgbi=((g*g)-(r*b))/((g*g)+(r*b))
# rgbi_bin=np.where(rgbi>2,255,0)
# zal.cloneBand(rgbi_bin,(os.path.join(DATA_DIR,'rgbi.tif')))
out_file=(os.path.join(DATA_DIR,'gli_float.tif'))
# f'''gdal_calc -R {zal} --R_band=1 -G {zal} --G_band=2 -B {zal} --B_band=3  \
#   --outfile={out_file} --calc="(2*G-R-B)/(2*G+R+B)
#  '''
  
#   gdal_calc -R C:\dev\TFG\data\ORTO_ZAL_BCN.tif --R_band=1 -G C:\dev\TFG\data\ORTO_ZAL_BCN.tif --G_band=2 -B C:\dev\TFG\data\ORTO_ZAL_BCN.tif --B_band=3 --outfile=C:\dev\TFG\data\raster_alggdal.tif --calc="(2*G-R-B)/(2*G+R+B)"

# --calc="B*logical_and(A>100,A<150)