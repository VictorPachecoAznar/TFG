import os
BASE_DIR=os.getenv('BASE_DIR',os.path.dirname(os.path.dirname(__file__)))
DATA_DIR=os.path.join(BASE_DIR,'data')
SCRIPTS_DIR=os.path.join(BASE_DIR,'scripts')
STATIC_DIR=os.path.join(BASE_DIR,'static')

__all__=['pruebas_samgeo.py']