from osgeo import gdal
import os
from subprocess import Popen
from concurrent.futures import ProcessPoolExecutor

BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(__file__))
DATA_DIR=os.path.join(BASE_DIR,'data')
SCRIPTS_DIR=os.path.join(BASE_DIR,'scripts')

def folder_check(dir):
    if os.path.exists(dir):
        return dir
    else:
        os.mkdir(dir)
        return None


def polygonize_raster(raster):
    dx=0
    dy=0

def _warp_single_raster(self,args):
    name, bounds,raster=args
    options= gdal.WarpOptions(dstSRS=self.crs)
    gdal.Warp(name,raster,outputBounds=bounds,dstNodata=0,options=options)
    

class orto():
    def __init__(self,route=None,raster=None,crs=25831):
        if raster is None  and route is None:
            print('raster wasn\'t kiaded')
            pass
        else:
            try:
                self.raster=gdal.Open(route)
            except:
                self.raster=raster
            
            [self.X_min, self.X_pixel, self.X_spin, self.Y_max, self.Y_spin, self.Y_pixel]=self.raster.GetGeoTransform()
            self.X_max = self.X_min + self.X_pixel * self.raster.RasterXSize
            self.Y_min = self.Y_max + self.Y_pixel * self.raster.RasterYSize
            self.width=self.X_max-self.X_min
            self.height=self.Y_max-self.Y_min
            self.pixel_width=self.raster.RasterXSize
            self.pixel_height=self.raster.RasterYSize
            self.wkt=self.get_wkt()

        
    def get_wkt(self):
         poly_str = f"POLYGON(({self.X_min} {self.Y_min},{self.X_max} {self.Y_min},{self.X_max} {self.Y_max},{self.X_min} {self.Y_max},{self.X_min} {self.Y_min}))"
    

        
    def polygonize(self,step):

        warp_tasks=[]

        # Generación de las ventanas para los recortes

        for i in range(int(self.X_min),int(self.X_max)+1,step):
            for j in range(int(self.Y_max),int(self.Y_min)+1,-step):
                name=os.path.join(DATA_DIR,f' result{i}{j}.tif')
                metric_x=step*self.X_pixel
                metric_y=step*self.Y_pixel

                bounds=(i,j,i+metric_x,j-metric_y)
                warp_tasks.append((name,bounds,self.raster))      

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(self.crs)
        dstSRS_wkt = srs.ExportToWkt()
        
        results=list(map(_warp_single_raster, warp_tasks))

        #with ProcessPoolExecutor() as executor:
        #    results=list(executor.map(_warp_single_raster, warp_tasks))
                
    


if __name__=='__main__':
    [folder_check(dir) for dir in (DATA_DIR,BASE_DIR,SCRIPTS_DIR)]
    base_image=orto(os.path.join(DATA_DIR,'ORTO_PORT.tif'))
    #print(base_image.pixel_height)
    base_image.polygonize(1024)
    #print(base_image.height)