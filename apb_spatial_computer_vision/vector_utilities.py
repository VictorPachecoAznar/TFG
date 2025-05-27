from apb_spatial_computer_vision import *
from osgeo import ogr,osr
import numpy as np
from scipy.optimize import least_squares
from math import sqrt,log,pi,sin,cos,asin
import geopandas as gpd

import shapely
from functools import partial
from scipy.optimize import least_squares
from apb_spatial_computer_vision.main import prediction_to_bbox
from concurrent.futures import ProcessPoolExecutor
from math import isnan,sin,cos,pi,asin,sqrt
from apb_spatial_computer_vision.main import read_file

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

def regress_circle(polygon:shapely.Polygon,threshold=0.001):
    """Regresses approximately circular geometries into the least-squares best fit circle using Levenberg-Marquardt algorithm (MINIPACK)

    Args:
        polygon (shapely.Polygon): Polygon to be regressed
        threshold (float, optional): _description_. Defaults to 0.001.

    Returns:
        shapely.Polygon: Polygon with an edge length equal to the threshold and a circular shape based on the least squares-regressed equation.
    """
    
    pred_center=polygon.centroid
    np_exterior=np.array(polygon.boundary.coords)
    # if len(np_exterior)==4:
    #     return polygon
    
    x=np_exterior[:,0]
    y=np_exterior[:,1]
    
    f=least_squares(circle,x0=[pred_center.x,pred_center.y,10],args=(x,y),method='lm')

    a,b,r=float(f.x[0]),float(f.x[1]),float(f.x[2])
    v=np.transpose(np.array([(x-np.full_like(x,a))**2+(y-np.full_like(x,b))**2-np.full_like(a,r**2)]))
    std=sqrt(float(np.matmul(np.transpose(v),v))/(v.shape[0]-len(f.x)))
    #/(v.shape[0]-len(f.x)))
    #print(std, v.shape[0])
    if std>sqrt(threshold)*r**2:
        #print(f'{counter,v.shape[0]}')
        return polygon,std,False
    
    angles=np.linspace(0,2*pi,int(2*pi/asin(threshold/r)+1))
    
    x=np.full_like(angles,a)+np.sin(angles)*np.full_like(angles,r)
    y=np.full_like(angles,b)+np.cos(angles)*np.full_like(angles,r)
    puntos_2=np.column_stack((x,y))
    polygon=shapely.Polygon(puntos_2)
    return polygon,std,True

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
    
    def regularize_circles_file(file,output:str=None,threshold: float = 0.01,file_gpkg_layer=None):
        """Recovers a circular geometry as 

        Args:
            file (_type_): _description_
            output (str, optional): _description_. Defaults to None.
            threshold (float, optional): _description_. Defaults to 0.01.
            file_gpkg_layer (_type_, optional): _description_. Defaults to None.

        Raises:
            Exception: _description_
            Exception: _description_

        Returns:
            _type_: _description_
        """

        if isinstance(file,str):
            if os.path.exists(file):
                if file_gpkg_layer is not None:
                    gdf=gpd.read_file(file,layer=file_gpkg_layer)
                else:
                    gdf=gpd.read_file(file)
            else:
                raise Exception('Path does not exist')
            
        elif isinstance(file,gpd.GeoDataFrame):
            gdf=file.copy()
    
        else:
            raise Exception('Only valid paths recognized by GeoPandas or GeoDataFrames accepted')
                
        convex_hull=gdf.geometry.convex_hull
        polygons=gpd.GeoDataFrame([regress_circle(polygon,threshold) for polygon in convex_hull],
                                  columns=['geom','std','regressed'],
                                  geometry='geom',crs=gdf.crs)
        #polygons['regressed']=polygons['std']<sqrt(threshold)
        
        if output is not None:
            extension=os.path.splitext(output)[1]
            if extension=='':
                extension='.parquet'
                output+=extension
            if extension=='.parquet':
                polygons.to_parquet(output)
            else:
                polygons.to_file(output)
        else:
            return polygons
        
    def to_crs(self,dst_crs):
        pass

            
    pass    

