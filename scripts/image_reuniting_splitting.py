import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

import geopandas as gpd
import shapely
from pruebas_samgeo import *
shapely.Polygon.interpolate
import scipy.interpolate
import numpy as np
import pandas as pd
if __name__=="__main__":

    t0=time()

    gdf=gpd.read_file(os.path.join(BASE_DIR,'collab','rotonda.geojson'))

    #[folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,SCRIPTS_DIR]]

    #base_image = Ortophoto(os.path.join(DATA_DIR,'ORTO_PORT.tif'))
    #print(base_image.Y_pixel)
    #base_image.polygonize(1024)
    from math import isnan

    exterior=list(gdf['geometry'][0].convex_hull.exterior.coords)

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