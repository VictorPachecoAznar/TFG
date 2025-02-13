from osgeo import gdal, osr
import os
from subprocess import Popen
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from time import time
#from fire import Fire

BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(__file__))
DATA_DIR=os.path.join(BASE_DIR,'data')
SCRIPTS_DIR=os.path.join(BASE_DIR,'scripts')

def folder_check(dir):
    if os.path.exists(dir):
        print(f'{dir} correctly there!')
        return dir
    else:
        os.mkdir(dir)
        return dir

def _warp_single_raster(name,bounds,raster):
    options= gdal.WarpOptions(dstSRS=raster.dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=raster.dstSRS_wkt)
    gdal.Warp(name,raster.raster,outputBounds=bounds,options=options)
    
class Ortophoto():
    def __init__(self,route=None,raster=None,crs=25831):
        if raster is None  and route is None:
            print('raster wasn\'t kiaded')
            return None
        else:
            try:
                self.raster=gdal.Open(route)
            except:
                if raster is not None:
                    self.raster=raster
                else:
                    return None
            
            self.raster_path=route
            [self.X_min, self.X_pixel, self.X_spin, self.Y_max, self.Y_spin, self.Y_pixel]=self.raster.GetGeoTransform()
            self.X_max = self.X_min + self.X_pixel * self.raster.RasterXSize
            self.Y_min = self.Y_max + self.Y_pixel * self.raster.RasterYSize
            self.width=self.X_max-self.X_min
            self.height=self.Y_max-self.Y_min
            self.pixel_width=self.raster.RasterXSize
            self.pixel_height=self.raster.RasterYSize
            self.crs=crs
            self.wkt=self.get_wkt()
            self.getSRS()

    # PICKLE FOR SERIALIZATION get and set state functions. 
    # These work by using a dict

    def __getstate__(self):
         state = self.__dict__.copy()
         del state['raster']
         return state
    
    def __setstate__(self,state):
         self.__dict__.update(state)
         self.raster = gdal.Open(self.raster_path)
        
    def getSRS(self):
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(self.crs)
        self.dstSRS_wkt = srs.ExportToWkt()
        
    def get_wkt(self):
         poly_str = f"POLYGON(({self.X_min} {self.Y_min},{self.X_max} {self.Y_min},{self.X_max} {self.Y_max},{self.X_min} {self.Y_max},{self.X_min} {self.Y_min}))"

    def polygonize(self,step,horizontal_skew=False,vertical_skew=False):
        
        name_list=[]
        bound_list=[]
        # Generación de las ventanas para los recortes
        ncol,nrow=0,0
        tiles_dir=folder_check(os.path.join(DATA_DIR,f'tiles_{step}'))
        metric_x=step*self.X_pixel
        metric_y=step*self.Y_pixel

        cols=abs(int(self.width/metric_x))#+1
        rows=abs(int(self.height/metric_y))#+1

        for i in range(cols):
            for j in range(rows):
                name=os.path.join(tiles_dir,f'result_{step}_grid_{nrow}_{ncol}.tif')
                bounds=(self.X_min+metric_x*i,self.Y_max+metric_y*j,self.X_min+metric_x*(i+1),self.Y_max+metric_y*(j+1))
                name_list.append(name)
                bound_list.append(bounds) 
                nrow+=1

            ncol+=1
            nrow=0     

        processing=partial(_warp_single_raster,raster=self)

        # PARALELIZADO CON MAP REDUCE
        with ProcessPoolExecutor() as executor:
             results = list(executor.map(processing,name_list,bound_list,chunksize=2000))
        
        return name_list
    
        #EJECUCIÓN SIN MAPREDUCE
        #tareas=[]
        #for name,bound in zip(name_list,bound_list):
        #    tareas.append(processing(name=name,bounds=bounds))
             
    


if __name__=='__main__':

    t0=time()
    [folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,SCRIPTS_DIR]]
    base_image = Ortophoto(os.path.join(DATA_DIR,'ORTO_PORT.tif'))
    print(base_image.Y_pixel)
    base_image.polygonize(1024)
    t1=time()
    print(f'TIME OCURRED:{t1-t0}')