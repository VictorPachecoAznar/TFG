import os
import sys
import duckdb
# import ibis
# from ibis import _
# ibis.options.interactive=True

BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(os.path.dirname(__file__)))
DATA_DIR=os.getenv('DATA_DIR',os.path.join(BASE_DIR,'data'))
PACKAGE_DIR=os.path.join(BASE_DIR,'apb_spatial_computer_vision')
STATIC_DIR=os.path.join(BASE_DIR,'static')
SHELL_DIR=os.path.join(PACKAGE_DIR,'shell')
OUT_DIR=os.path.join(BASE_DIR,'out')
TEMP_DIR=os.path.join(BASE_DIR,'temp')

driverDict={'.tif':'GTiff','.geojson':'GeoJSON'}
modelDict={'buildings':{'SIZE':256,'PIXEL':40},
           'roads':{'SIZE':512,'PIXEL':20},
            'oil':{'SIZE':512,'SIZE':150}
           }

DUCKDB=duckdb.connect()
DUCKDB.install_extension('spatial')
DUCKDB.load_extension('spatial')