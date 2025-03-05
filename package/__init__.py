import os
BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(os.path.dirname(__file__)))
DATA_DIR=os.path.join(BASE_DIR,'data')
PACKAGE_DIR=os.path.join(BASE_DIR,'package')
STATIC_DIR=os.path.join(BASE_DIR,'static')
SHELL_DIR=os.path.join(PACKAGE_DIR,'shell')

driverDict={'tif':'GTiff','geojson':'GeoJSON'}
modelDict={'buildings':{'SIZE':256,'PIXEL':40},
           'roads':{'SIZE':512,'PIXEL':20},
            'oil':{'SIZE':512,'SIZE':150}
           }
