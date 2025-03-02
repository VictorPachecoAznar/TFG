import os
BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(os.path.dirname(__file__)))
DATA_DIR=os.path.join(BASE_DIR,'data')
PACKAGE_DIR=os.path.join(BASE_DIR,'package')
STATIC_DIR=os.path.join(BASE_DIR,'static')

driverDict={'tif':'GTiff','geojson':'GeoJSON'}
