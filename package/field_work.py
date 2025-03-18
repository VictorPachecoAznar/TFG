import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from package import *

import geopandas as gpd , pandas as pd

def quality_control_point_creation():
    """Data processing from the points with averaging
    """
    df=pd.read_csv(os.path.join(DATA_DIR,'COMPROV ORTO.txt'),sep=' ')
    gdf=gpd.GeoDataFrame(df,geometry=gpd.points_from_xy(df['X'],df['Y']),crs=25831)
    gdf.to_file(os.path.join(DATA_DIR,'ORTOFOTO_CHECK.geojson'))