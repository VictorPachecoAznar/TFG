from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision import *
from apb_spatial_computer_vision.vector_utilities import VectorDataset

#shapely.Polygon.interpolate
#import scipy.interpolate
import numpy as np, pandas as pd
import geopandas as gpd, shapely
import time
if __name__=="__main__":

    # cir=VectorDataset(os.path.join(BASE_DIR,'collab','rotonda.geojson'))
    
    # cir.curve_geometry()

    #gdf=gpd.read_file(os.path.join(BASE_DIR,'collab','rotonda.geojson'))

    #[folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,SCRIPTS_DIR]]

    #base_image = Ortophoto(os.path.join(DATA_DIR,'ORTO_PORT.tif'))
    #print(base_image.Y_pixel)
    #base_image.polygonize(1024)
    
    #gdf=gpd.read_file(os.path.join(DATA_DIR,'repo_gis.gpkg'),layer='diposit-perimetre_base')
    #gdf=prediction_to_bbox(diposits)
    
    # VectorDataset.regularize_circles_file(file=os.path.join(DATA_DIR,'repo_gis.gpkg'),
    #                                      output=os.path.join(TEMP_DIR,'resultado'),
    #                                      file_gpkg_layer='diposit-perimetre_base')
    
    # VectorDataset.regularize_circles_file(
    #     file=os.path.join(DATA_DIR,'ORTO_ME_BCN','first_iteration.geojson'),
    #     output=os.path.join(TEMP_DIR,'FIRST_ITERATION')
    #     )
    gdf=gpd.read_parquet(os.path.join(DATA_DIR,'ORTO_ME_BCN','clean_second_iteration_buffer.parquet'))

    
    simplegdf=gdf.explode()
    polygon_gdf=simplegdf[simplegdf.geometry.type=='Polygon'].reset_index(drop=True)
    VectorDataset.regularize_circles_file(
        file=polygon_gdf,
        output=os.path.join(TEMP_DIR,'COMBINED_ITERATIONS')
        )
    exterior=[i.convex_hull for i in gdf['geometry']]

    # np_exterior=np.array(exterior)
    # x=np_exterior[:,0]
    # y=np_exterior[:,1].flatten()
    

    
    # geometries=gpd.GeoDataFrame(geometry=exterior,crs=gdf.crs)
    # t0=time.time()
    # polygons=gpd.GeoSeries([regress_circle(polygon,0.01) for polygon in geometries.geometry])
    # # partial_circle_regression=partial(regress_circle,threshold=0.01)
    # rounded_p=gpd.GeoDataFrame(geometry=polygons,crs=gdf.crs)

    # # t1=time.time()
    # # oriented_bboxes=prediction_to_bbox(rounded_p)
    # # t2=time.time()
    # # print(f'tiempo bbox{t2-t1}')   
    # #rounded_p.to_file(os.path.join(BASE_DIR,'out','diposits_regressed.geojson'))
    # rounded_p.to_parquet(os.path.join(BASE_DIR,'out','diposits_regressed.parquet'))
    # t1=time.time()
    
    # print(f'tiempo{t1-t0}') #138S to 3s-numpy optimization
    # #rounded_p=gpd.GeoDataFrame(geometry=polygons,crs=gdf.crs)
    # DUCKDB.sql('''
    #     SELECT *
    #     FROM rounded_p'''  )
    # rounded_p.to_file(os.path.join(BASE_DIR,'out','diposits_regressed.geojson'))
    # rounded_p.to_parquet()
    
    # x=p[:,0]
    # y=p[:,1]
    # rounded=gpd.GeoDataFrame(data={'x':x,'y':y},geometry=gpd.points_from_xy(x,y),crs=gdf.crs)
    # rounded.to_file(os.path.join(BASE_DIR,'out','rotonda_redonda.geojson'))

    # x=pd.Series([i for (i,j) in gdf['geometry'][0].convex_hull.exterior.coords])
    # y=pd.Series([j for (i,j) in gdf['geometry'][0].convex_hull.exterior.coords])

    # vectorTranslate=gdal.VectorTranslateOptions(geometryType='CONVERT_TO_CURVE')
    # gdal.VectorTranslate()

    # gdalDriver=ogr.GetDriverByName('GeoJSON')
    # rotonda=gdalDriver.Open(os.path.join(BASE_DIR,'collab','rotonda.geojson'))


    # df=pd.DataFrame({'x':x,'y':y})
    # df['GRAD']=np.gradient(df['y'],df['x'])
    # df=df.dropna().reset_index(drop=True)

    # dydx=np.gradient(y,x).tolist()
    # newx,newy,newdydx=[],[],[]
    # for i in range(len(dydx)):
    #     if isnan(dydx[i]):
    #         print(i)
    #     else:
    #         newx.append(x[i])
    #         newy.append(y[i])
    #         newdydx.append(dydx[i])
    
    # newdydx

    # import pandas as pd
    # pd.DataFrame()
    

    # inter=scipy.interpolate.CubicHermiteSpline(newx,newy,newdydx)

    # t1=time()
    # print(f'TIME OCURRED:{t1-t0}')