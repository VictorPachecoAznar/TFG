import os,sys

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pruebas_samgeo import *
import fire
import subprocess


def find_extension(args)
    input_strings=list(args)
    extensions=[]
    for i in input_strings
        ins=i.split()
        extensions.append(ins[len(ins)-1])
    return extensions

def _translate_single_raster(out_epsg,args):
    '''
    args input file, output file

    '''
    crs=str(out_epsg)
    in_file, out_file=args
    in_ext, out_ext= find_extension(in_file,out_file)
    driverDict={'tif':'GTiff'}
    if 

    in_path,out_path=

    if driverDict[out_ext]:
        translate_command=f'''gdal_translate -a_srs EPSG:{crs} -of {driverDict[out_ext]} {input.sid} {output.tif}'''
        subprocess.run(
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

    RASTER_TRANSLATION_FOLDER=pruebas_samgeo.folder_check(os.path.join(DATA_DIR,'raster_translation'))
    
    if RASTER_TRANSLATION_FOLDER is not None:
        fire.Fire(
         {
             'transform_raster': transform_raster
         }
        )