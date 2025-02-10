from osgeo import gdal
import os

BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(__file__))
DATA_DIR=os.path.join(BASE_DIR,'data')

def folder_check(dir):
    if os.path.exists(dir):
        pass
    else:
        os.mkdir(dir)

[folder_check(dir) for dir in (DATA_DIR,BASE_DIR)]

def polygonize_raster(raster):
    dx=0
    dy=0

class orto():
    def __init__(self,route=None,raster=None,):
        if raster is None  and route is None:
            print('raster no creado!')
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
        for i in range(int(self.X_min),int(self.X_max)+1,step):
            for j in range(int(self.Y_max),int(self.Y_min)+1,-step):
                name=os.path.join(DATA_DIR,f'result{i}{j}.tif')
                bounds=(i,j,i+step,j-step)
                gdal.Warp(name,self.raster,outputBounds=bounds,dstNodata=0)

                
                #os.execute()
    


if __name__=='__main__':

    base_image=orto('ORTO_PORT.tif')
    base_image.polygonize(1024)


    base_image.height