#from package.pruebas_samgeo import *
from .__init__ import *
import os
from osgeo import ogr,osr
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

def reproject_ogr(dataset,src_crs,dst_crs):
    
    # Define source and destination CRS
    src_srs = osr.SpatialReference()
    src_srs.ImportFromEPSG(src_crs)
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(dst_crs)

    # Create a coordinate transformation object
    transform = osr.CoordinateTransformation(src_srs, dst_srs)

    # Transform the geometry
    dataset.Transform(transform)
    return dataset


class VectorDataset():
    def __init__(self,path):
        self.vector_path=path
        extension=os.path.splitext(path)[1]
        self.driver=ogr.GetDriverByName(driverDict[extension])
        self.dataset=self.driver.Open(self.vector_path)
        self.layer=self.dataset.GetLayer()
        self.crs=self._get_crs()
        pass
    
    def _get_crs(self):
        """identifies CRS from the layer"""
        spatial_ref = self.layer.GetSpatialRef()
        spatial_ref.AutoIdentifyEPSG()
        epsg_code = spatial_ref.GetAuthorityCode(None)
        return int(epsg_code)
    
    def curve_geometry(self):
        curvas=[]
        for feature in self.layer:
            geometry=feature.GetGeometryRef()

            outjson=geometry.ExportToJson()
            #curvas.append(geometry.GetCurveGeometry())
        return curvas
    
    def to_crs(self,dst_crs):
        pass
    
    #gdf
    #least_squares(circle,,puntos)
            
    pass    

