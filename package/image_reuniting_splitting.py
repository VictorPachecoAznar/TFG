import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from package.raster_utilities import Ortophoto
from package.__init__ import *

#shapely.Polygon.interpolate
#import scipy.interpolate
import numpy as np, pandas as pd
import geopandas as gpd, shapely
from time import time

from functools import partial
from scipy.optimize import least_squares
from package.vector_utilities import circle,VectorDataset

if __name__=="__main__":

    t0=time()

    cir=VectorDataset(os.path.join(BASE_DIR,'collab','rotonda.geojson'))
    
    cir.curve_geometry()

    gdf=gpd.read_file(os.path.join(BASE_DIR,'collab','rotonda.geojson'))

    #[folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,SCRIPTS_DIR]]

    #base_image = Ortophoto(os.path.join(DATA_DIR,'ORTO_PORT.tif'))
    #print(base_image.Y_pixel)
    #base_image.polygonize(1024)

    from math import isnan,sin,cos,pi,asin

    exterior=list(gdf['geometry'][0].convex_hull.exterior.coords)
    np_exterior=np.array(exterior)
    x=np_exterior[:,0]
    y=np_exterior[:,1]
    geometries=gpd.GeoDataFrame(data={'x':x,'y':y},geometry=gpd.points_from_xy(x,y),crs=gdf.crs)
    
    pred_center=gdf['geometry'][0].centroid

    f=least_squares(circle,x0=[pred_center.x,pred_center.y,10],args=(x,y),method='lm')
    
    a,b,r=float(f.x[0]),float(f.x[1]),float(f.x[2])
    
    def get_circle_coords(angle,R,a,b):
        x=a+R*sin(angle)
        y=b+R*cos(angle)
        return (x,y)
    
    threshold=0.001
    angles=np.linspace(0,2*pi,int(2*pi/asin(threshold/r)+1))

    compute_circle=partial(get_circle_coords,R=r,a=a,b=b)
    puntos_2=list(map(compute_circle,angles))
    p=np.array(puntos_2)
    
    polygon=shapely.Polygon(puntos_2)

    rounded_p=gpd.GeoDataFrame(geometry=[polygon],crs=gdf.crs)
    rounded_p.to_file(os.path.join(BASE_DIR,'out','rotonda_redonda_poly_5cm.geojson'))
    
    x=p[:,0]
    y=p[:,1]
    rounded=gpd.GeoDataFrame(data={'x':x,'y':y},geometry=gpd.points_from_xy(x,y),crs=gdf.crs)
    rounded.to_file(os.path.join(BASE_DIR,'out','rotonda_redonda.geojson'))

    x=pd.Series([i for (i,j) in gdf['geometry'][0].convex_hull.exterior.coords])
    y=pd.Series([j for (i,j) in gdf['geometry'][0].convex_hull.exterior.coords])

    vectorTranslate=gdal.VectorTranslateOptions(geometryType='CONVERT_TO_CURVE')
    gdal.VectorTranslate()

    gdalDriver=ogr.GetDriverByName('GeoJSON')
    rotonda=gdalDriver.Open(os.path.join(BASE_DIR,'collab','rotonda.geojson'))


    df=pd.DataFrame({'x':x,'y':y})
    df['GRAD']=np.gradient(df['y'],df['x'])
    df=df.dropna().reset_index(drop=True)

    dydx=np.gradient(y,x).tolist()
    newx,newy,newdydx=[],[],[]
    for i in range(len(dydx)):
        if isnan(dydx[i]):
            print(i)
        else:
            newx.append(x[i])
            newy.append(y[i])
            newdydx.append(dydx[i])
    
    newdydx

    import pandas as pd
    pd.DataFrame()
    

    inter=scipy.interpolate.CubicHermiteSpline(newx,newy,newdydx)

    t1=time()
    print(f'TIME OCURRED:{t1-t0}')