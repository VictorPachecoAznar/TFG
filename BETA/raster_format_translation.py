import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from apb_spatial_computer_vision.raster_utilities import *
import subprocess


def find_extension(args):
    input_strings=list(args)
    extensions=[]
    for i in input_strings:
        ins=i.split()
        extensions.append(ins[len(ins)-1])
    return extensions

def _translate_single_raster(out_epsg,args):
    '''
    args input file, output file

    '''
    crs=str(out_epsg)
    in_path, out_path=args
    in_ext, out_ext= find_extension(in_path,out_path)
    driverDict={'tif':'GTiff'}

    if driverDict[out_ext]:
        translate_command=f'''gdal_translate -a_srs EPSG:{crs} -of {driverDict[out_ext]} {in_path} {out_path}'''
        subprocess.call(
            translate_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

def transform_raster(args):
    '''
    Takes in tuples and changes their format accordingly
    '''
    translate_tasks=list(args)
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(_translate_single_raster, translate_tasks))

if __name__ == '__main__':

    RASTER_TRANSLATION_FOLDER=folder_check(os.path.join(DATA_DIR,'raster_translation'))
    
    if RASTER_TRANSLATION_FOLDER is not None:
        fire.Fire(
         {
             'transform_raster': transform_raster
         }
        )