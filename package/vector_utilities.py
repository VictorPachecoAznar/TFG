#from package.pruebas_samgeo import *
from .__init__ import *
import os
from osgeo import ogr
import numpy as np
from scipy.optimize import least_squares
from math import sqrt,log,pi,sin,cos,asin
import geopandas as gpd

def circle(x,px,py):
    return np.array((px-x[0])**2+(py-x[1])**2-x[2]**2)

def save_HTML(gdf,out_name):
    m=gdf.explore()
    m.save(os.path.join(STATIC_DIR,out_name))

def list_to_html(point_list,out_name):
    p=np.array(point_list)
    gdf=gpd.GeoDataFrame(geometry=gpd.points_from_xy(p[:,0],p[:,1]),crs=25831)
    save_HTML(gdf,out_name)

class VectorDataset():
    def __init__(self,path):
        self.vector_path=path
        extension=(os.path.basename(path).split('.'))[-1]
        self.driver=ogr.GetDriverByName(driverDict[extension])
        pass

    def curve_geometry(self):
        dataset=self.driver.Open(self.vector_path)
        layer=dataset.GetLayer()
        curvas=[]
        for feature in layer:
            geometry=feature.GetGeometryRef()
            outjson=geometry.ExportToJson()
            curvas.append(geometry.GetCurveGeometry())
        return curvas

    def circle(x,px,py):
        return np.array((px-x[0])**2+(py-x[1])**2-x[2]**2)
    
    #gdf
    #least_squares(circle,,puntos)
            
    pass    