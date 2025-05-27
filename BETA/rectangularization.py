import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)
from apb_spatial_computer_vision import *
import geopandas as gpd, numpy as np

# gdf=gpd.read_file(os.path.join(OUT_DIR,'GOOGLE_COLLAB_GEOAI_BUILDINGS_AI','building_masks.geojson'))
gdf=gpd.read_file(os.path.join(OUT_DIR,'GOOGLE_COLLAB_CHINA','EDIFICIO.geojson'))

def oriented_bbox(gdf):
    #coords=gdf.geometry[0].boundary.coords
    wkts=[g.boundary.oriented_envelope.wkt for g in gdf.geometry]
    #nl= [x for xs in li for x in xs]
    newgdf=gpd.GeoDataFrame(gdf,geometry=gpd.GeoSeries.from_wkt(wkts),crs=25831)
    newgdf.to_file(os.path.join(OUT_DIR,'QGIS_BUILDINGS','ORIENTED_BOXES.GEOJSON'))

oriented_bbox(gdf)

