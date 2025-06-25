import tempfile
from osgeo import gdal, osr
import subprocess
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from time import time
from math import sqrt,log,pi,sin,cos,asin
import geopandas as gpd, pandas as pd, numpy as np
from collections.abc import Iterable
import asyncio

from apb_spatial_computer_vision import *


def folder_check(dir):
    if os.path.exists(dir):
        #print(f'{dir} correctly there!')
        return dir
    else:
        os.mkdir(dir)
        return dir

def _warp_single_raster(name,bounds,raster):
    options= gdal.WarpOptions(dstSRS=raster.dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=raster.dstSRS_wkt,multithread=True)
    gdal.Warp(name,raster.raster,outputBounds=bounds,options=options)

def _warp_single_raster_shell(name,bounds,raster):
    options= gdal.WarpOptions(dstSRS=raster.dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=raster.dstSRS_wkt,multithread=True)
    
    #para reproyecciones grandes se puede hacer -wo NUM_THREADS=ALL_CPUS-2, sólo en casos individuales no paralelizados por mí.
    #subprocess allows for arguments to be given in lists

    command=f'gdalwarp -q -multi -wm 5000 -te  {bounds[0]} {bounds[1]} {bounds[2]} {bounds[3]} "{raster.raster_path}" "{name}"'
    subprocess.Popen(command,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    gdal.Warp(name,raster.raster,options=options)

def _simplify_single_raster(name,xRes,yRes,bounds,raster):
    options= gdal.WarpOptions(dstSRS=raster.dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=raster.dstSRS_wkt,
                              multithread=True,
                              xRes=xRes,yRes=yRes,resampleAlg='bilinear')
    gdal.Warp(name,raster.raster,options=options)

def _async_simplify_single_raster(name,xRes,yRes,bounds,raster,dstSRS_wkt):
    options= gdal.WarpOptions(dstSRS=dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=dstSRS_wkt,
                              multithread=True,
                              xRes=xRes,yRes=yRes,resampleAlg='bilinear')
    gdal.Warp(name,gdal.Open(raster),options=options)
    
def _generalize_single_raster(name,bounds,xRes,yRes,raster):
    options= gdal.WarpOptions(dstSRS=raster.dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=raster.dstSRS_wkt,multithread=True,xRes=xRes,yRes=yRes,resampleAlg='bilinear')
    gdal.Warp(name,raster.raster,options=options)

def _native_parallelized_simplifly_single_raster(name,xRes,yRes,bounds,raster):
    options= gdal.WarpOptions(dstSRS=raster.dstSRS_wkt,dstNodata=0,outputBounds=bounds,outputBoundsSRS=raster.dstSRS_wkt,multithread=True,warpOptions='NUM_THREADS=ALL_CPUS',xRes=xRes,yRes=yRes,resampleAlg='bilinear')
    gdal.Warp(name,raster.raster,options=options)


def closest_base_power(x,power=2):
    return power**int(log(x,power))    

def bounds2wkt(bounds):
    (X_min,Y_min,X_max,Y_max)=bounds
    poly_str = f"POLYGON(({X_min} {Y_min},{X_max} {Y_min},{X_max} {Y_max},{X_min} {Y_max},{X_min} {Y_min}))"
    return poly_str

def bounds_gdf(bounds,crs):
   return gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt([bounds2wkt(bounds)]),crs=crs)

[folder_check(dir) for dir in  [DATA_DIR,BASE_DIR,PACKAGE_DIR,STATIC_DIR]]


class Ortophoto():

    def __init__(self,path=None,folder=None,crs=25831):
        """Raster algorithm containing the different values to be kept.

        Args:
            path (str, optional): The path to the image, with the GDAL-accepted formats. Defaults to None.
            folder (str, optional): The default folder for all computations to be performed. Defaults to None, and will be stored in with a name like DATA_DIR/{path}.
            crs (int): CRS of the tile to be loaded. Defaults to 25831.

        Raises:
            Exception: File is not valid
        """
        try:
            #os.path.exists(path):
            self.raster=gdal.Open(path)
        except:
            raise Exception('Name does not exist')
            
        self.raster_path=path
        self.basename=os.path.basename(path)
        self.folder=self._get_dirname(folder)
        self.GT=[self.X_min, self.X_pixel, self.X_spin, self.Y_max, self.Y_spin, self.Y_pixel]=self.raster.GetGeoTransform()
        self.X_max = self.X_min + self.X_pixel * self.raster.RasterXSize
        self.Y_min = self.Y_max + self.Y_pixel * self.raster.RasterYSize
        self.bounds=(self.X_min,self.Y_min,self.X_max,self.Y_max)
        self.width=self.X_max-self.X_min
        self.height=self.Y_max-self.Y_min
        self.area=self.width*self.height
        self.pixel_width=self.raster.RasterXSize
        self.pixel_height=self.raster.RasterYSize
        self.crs=crs
        self.wkt=self._get_wkt()
        self.dstSRS_wkt=self.getSRS()
        self.pyramid = None
        self.resolutions =None
        self.resolutions_tiles=None
        self.lowest_pixel_size=1024

    def __repr__(self):
        return self.raster_path

    def _get_dirname(self,folder):
        """Auxiliary function to find the folder for the Ortophoto

        Args:
            folder (str): Path to a different folder

        Returns:
            str: Bar
        """
        if folder is not None:
            return folder_check(folder)
        else:
            base=os.path.dirname(self.raster_path)
            orto_dir=os.path.splitext(self.basename)[0]
            return folder_check(os.path.join(base,orto_dir))
         
    # PICKLE FOR SERIALIZATION get and set state functions. 
    # These work by using a dict

    def __getstate__(self):
         state = self.__dict__.copy()
         del state['raster']
         return state
    
    def __setstate__(self,state):
         self.__dict__.update(state)
         self.raster = gdal.Open(self.raster_path)
    
    @staticmethod
    def mosaic_rasters(im_input:Iterable,name:str,fetch=False, pixel_value_to_be_ignored=''):
        """Returns the ortophoto object of the addition of the imput elements' iterable
        
        Args:
            im_input (Iterable): a list of Ortophoto objects or paths
            name (str): Output name for the mosaic
            fetch (bool, optional): Wether to return the Ortophoto object. Defaults to False.
            pixel_value_to_be_ignored (str, optional): Pixel value that will not override other previous values in case of overlap. Defaults to ''.

        Returns:
            outname (str): Output file name.
            out_orto (Ortophoto): Generated ortophoto object for the output file, only created if fetch equals True.
        """
        
       
        valid_images=[]

        def check_image(valid_images,im):
            if isinstance(im,str):
                if os.path.exists(im):
                    valid_images.append(im)
                    return valid_images
            else:
                try:
                    if os.path.exists(im.raster_path):
                        valid_images.append(im)
                        return valid_images
                except AttributeError:
                    raise (f'{im} COULD NOT BE ADDED AS IT IS NOT A VALID PATH OR ORTOPHOTO/TILE OBJECT.')

        if isinstance(im_input,Iterable) and not isinstance(im_input,str):
            for im in im_input:
                valid_images=check_image(valid_images,im)
        else:
            valid_images=check_image(valid_images,im_input)
            
        if len(valid_images)<2:
            print('NONE OF THE ITEMS TO ADD WAS GOOD ENOUGH')
            return im_input[0]
        else:
            root,ext=os.path.splitext(name)
            if ext=='':
                ext='.vrt' 
                
            if not os.path.exists(name):
                outdir=folder_check(os.path.join(DATA_DIR,os.path.dirname(name)))
            else:
                outdir=os.path.dirname(root)
            outname=os.path.join(outdir,f'{os.path.basename(root)}{ext}')

            if pixel_value_to_be_ignored!='':
                pixel_value_to_be_ignored=f'-srcnodata {pixel_value_to_be_ignored} -vrtnodata {pixel_value_to_be_ignored}'

            def create_virtual_tiles(output_virtual_file_path):
                """Generate a VRT file with the configurations to be added

                Args:
                    output_virtual_file_path (str): Path to the output VRT file
                """
                with tempfile.NamedTemporaryFile(mode='w',delete=False, suffix=".txt") as tmp:
                    tiles_list_file = tmp.name
                    for image_path in valid_images:
                        tmp.write(image_path + '\n')
                command = f'''gdalbuildvrt -o "{output_virtual_file_path}" {pixel_value_to_be_ignored} -input_file_list "{tiles_list_file}"'''
                subprocess.call(command)
                os.remove(tiles_list_file)

            if ext=='.vrt':
                create_virtual_tiles(outname)
            else:
                provisional_virtual_file=os.path.join(outdir,f'tmp.vrt')
                create_virtual_tiles(provisional_virtual_file)
                gdal.Translate(destName=outname,srcDS=provisional_virtual_file)
                os.remove(provisional_virtual_file)
            
            if fetch is True:
                return Ortophoto(outname)
            else:
                return outname

    def __add__(self,im_input,fetch=True):
        im_input.insert(0,self)
        return self.mosaic_rasters(im_input,name=f'augmented_{self.basename}')
    
    def getSRS(self):
        """
        Get the OSGEO/OSR WKT CRS 
        
        Returns:
            str: OSGEO/OSR Well-known Text (WKT) CRS 
        """
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(self.crs)
        dstSRS_wkt = srs.ExportToWkt()
        return dstSRS_wkt
        
    def _get_wkt(self):
        return f"POLYGON(({self.X_min} {self.Y_min},{self.X_max} {self.Y_min},{self.X_max} {self.Y_max},{self.X_min} {self.Y_max},{self.X_min} {self.Y_min}))"

    def gdf(self):
        return gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt([self.wkt]),crs=self.crs)
    
    @staticmethod
    def nice_write(num):
        """Computes the needed digits to be applied to zfill for succesful number ordering

        Args:
            num (int): input number

        Returns:
            int: The number of digits to be applied into zfill
        """
        '''Devuelve los ceros necesarios para la función zfill que permiten ordenar los números'''
        return int(log(num,10))+1

            
    def get_pyramid(self,lowest_pixel_size):
        """
        Gets the pyramid directory or creates it if not yet implemented

        Args:
            lowest_pixel_size (int, optional): Number of pixels for each tile in the pyramid. Defaults to 1024.
            
        Returns:
            self.pyramid (str) : Path to the pyramid
        """
        if self.pyramid is None:
            self.pyramid=self.create_pyramid(lowest_pixel_size=self.lowest_pixel_size)
            return self.pyramid
        else:
            return self.pyramid
    
    def get_pyramid_depth(self,lowest_pixel_size :int=1024):
        """
        Calculates the depth of the image pyramid, creates it too if it hasn't been done yet

        Args:
            lowest_pixel_size (int, optional): Number of pixels for each tile in the pyramid. Defaults to 1024.

        Returns:
            self.pyramid_depth (int): Number of levels of the pyramid
        """
        if not hasattr(self,"pyramid_depth"):
            self.pyramid=self.get_pyramid(lowest_pixel_size)
            self.raster_pyramid=os.path.join(self.pyramid,'raster')
            self.pyramid_depth=len([i for i in os.listdir(self.raster_pyramid) if os.path.isfile(os.path.join(self.raster_pyramid,i))==False])
            return self.pyramid_depth
        else:
            return self.pyramid_depth
    
    def get_pyramid_tiles(self,lowest_pixel_size=1024):
        """Fetches the list containing the paths for all files in the pyramid

        Args:
            lowest_pixel_size (int, optional): Number of pixels for each tile in the pyramid. Defaults to 1024.

        Returns:
            self.pyramid_tiles (list): Paths for the tiles in the pyramid
        """
        if not hasattr(self,'pyramid_tiles'):
            pyramid_tiles=[]
            for root, dirs, files in os.walk(os.path.join(self.get_pyramid(lowest_pixel_size),'raster')):
                pyramid_tiles+=[os.path.join(root,name) for name in files if os.path.splitext(name)[1]=='.tif']
            self.pyramid_tiles=pyramid_tiles

        return self.pyramid_tiles

    def get_resolutions(self,depth=None):
        if self.resolutions is None:
            if depth is None:
                depth=self.get_pyramid_depth()
            self.resolutions=self.create_resolutions(depth)

        return self.resolutions
    
    def get_resolution_tiles(self,depth=None):
        if self.resolutions_tiles is None:
            resolutions_tiles=[]
            for root, dirs, files in os.walk(self.get_resolutions(depth)):
                resolutions_tiles+=[os.path.join(root,name) for name in files if os.path.splitext(name)[1]=='.tif']
            self.resolutions_tiles=resolutions_tiles

        return self.resolutions_tiles


    def create_tiles_duckdb_table(self,lowest_pixel_size=1024):
        """
        Generates a DUCKDB table named tiles, containing the image pyramid data and its information. May trigger pyramid_depth or pyramid calculation if not abailable.

        Args:
            lowest_pixel_size (int, optional): Number of pixels for each tile in the pyramid. Defaults to 1024.
        """

        command = " UNION ALL ".join(
                [f"SELECT *, '{depth}' depth  FROM st_read('{os.path.join(self.get_pyramid(lowest_pixel_size),'vector',f'subset_{depth}.geojson')}')" for depth in range(self.get_pyramid_depth(lowest_pixel_size))])
                                
        DUCKDB.sql('CREATE TABLE IF NOT EXISTS tiles AS '+command)
                        
    def tesselation(self,dir,step_x,step_y=None):
        """
        Generation of tesselation algorithms

        Args:
            dir (str): Output directory
            step_x (int): Pixel width of the image crops.
            step_y (int, optional): Pixel heigh to the image crops if different. Defaults to None.

        Returns:
            name_list (list): Names for the tiles' files
            bound_list (list[tuple]):  Nested bounding box list like [(xmin,ymin,xmax,ymax),...,(...)]
        """
        if step_y is None:
            step_y=step_x
        metric_x=step_x*self.X_pixel
        metric_y=step_y*self.Y_pixel

        cols=abs(int(self.width/metric_x))
        rows=abs(int(self.height/metric_y))

        zcols,zrows =self.nice_write(cols), self.nice_write(rows)

        name_list,bound_list=[],[]
        ncol,nrow=0,0
        step_x=int(step_x)
        for i in range(cols):
            for j in range(rows):
                name=os.path.join(dir,f'tile_{step_x}_grid_{str(nrow).zfill(zrows)}_{str(ncol).zfill(zcols)}.tif')
                bounds=(self.X_min+metric_x*i,self.Y_max+metric_y*(j+1),self.X_min+metric_x*(i+1),self.Y_max+metric_y*j)
                name_list.append(name)
                bound_list.append(bounds) 
                nrow+=1
            ncol+=1
            nrow=0  
        return name_list, bound_list

    
    def polygonize(self,step_x,step_y=None):
        """
        Creates GDAL-based image cropping given an image size. Concurrently-sped up. 

        Args:
            step_x (int): The size of the resulting elements
            horizontal_skew (int, optional): The pixel units to add from to step in the X direction (cols or i). Defaults to None.
            vertical_skew (int, optional): The pixel units to add from to step in the Y direction (rows or j). Defaults to None.
        """
        name_list=[]
        bound_list=[]

        # Generación de las ventanas para los recortes
        tiles_dir=folder_check(os.path.join(self.folder,f'tiles_{os.path.basename(self.raster_path).split(".")[0]}_{step_x}'))

        name_list,bound_list=self.tesselation(tiles_dir,step_x,step_y)
    
        # Partial application of the function to avoid raster reopening
        processing=partial(_warp_single_raster,raster=self)

        # PARALELIZADO CON PROCESOS CONCURRENTES
        with ProcessPoolExecutor() as executor:
             results = list(executor.map(processing,name_list,bound_list,chunksize=2000))


    @staticmethod
    def partition_image(image_array):
        channels,height,width=image_array.shape
        
        #for channel in channels:
        #    image_array
        pass
    

    def explore(self,bound_list,tile_size):
        """
        Generates an interactive map in HTML for the tiles

        Args:
            bound_list (Iterable [tuple [float]]): list of bounds, like from the tiles
            tile_size (Iterable [str]): tile size with which the bounds have been developed.
        """
        wkts=[bounds2wkt(b)for b in bound_list]
        gdf=gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(wkts),crs=self.crs)
        gdf['area']=gdf['geometry'].area
        m=gdf.explore()
        m.save(os.path.join(STATIC_DIR,f'{tile_size}.html'))

    def create_resolutions(self,depth):
        """
        Generate images with degraded resolutions using bilineal interpolation

        Args:
            depth (int): The amount of numbers to be used in the development of the data.

        Returns:
            resolutions_dir (str): The path where the resolutions are stored (within the ortophoto /project folder) 
        """
        resolutions_dir=folder_check(os.path.join(self.folder,os.path.basename(self.raster_path).split('.')[0])+'_resolutions')
        gen=partial(_simplify_single_raster,raster=self,bounds=self.bounds)
        args={i:{'Name':os.path.join(folder_check(os.path.join(resolutions_dir,str(int(100*self.X_pixel*2**i))+'cm')),f'{i}.tif'),'xRes':self.X_pixel*2**i,'yRes':self.Y_pixel*2**i} for i in range(depth)}
        df=pd.DataFrame(args)
        df=df.transpose()
        with ProcessPoolExecutor() as executor:
            results=list(executor.map(gen,df['Name'],df['xRes'],df['yRes']))
        return resolutions_dir

    def create_non_parallelized_resolutions(self,depth):
        resolutions_dir=folder_check(os.path.join(self.folder,os.path.basename(self.raster_path).split('.')[0])+'_resolutions')
        args={i:{'Name':os.path.join(folder_check(os.path.join(resolutions_dir,str(int(100*self.X_pixel*2**i))+'cm')),f'{i}.tif'),'xRes':self.X_pixel*2**i,'yRes':self.Y_pixel*2**i} for i in range(depth)}
        df=pd.DataFrame(args)
        df=df.transpose()
        for i in range(len(df)):
            _simplify_single_raster(name=df['Name'][i],xRes=df['xRes'][i],yRes=df['yRes'][i],bounds=self.bounds,raster=self)

    def create_gdal_parallelized_resolutions(self,depth):
        resolutions_dir=folder_check(os.path.join(self.folder,os.path.basename(self.raster_path).split('.')[0])+'_resolutions')
        args={i:{'Name':os.path.join(folder_check(os.path.join(resolutions_dir,str(int(100*self.X_pixel*2**i))+'cm')),f'{i}.tif'),'xRes':self.X_pixel*2**i,'yRes':self.Y_pixel*2**i} for i in range(depth)}
        df=pd.DataFrame(args)
        df=df.transpose()
        for i in range(len(df)):
            _native_parallelized_simplifly_single_raster(name=df['Name'][i],xRes=df['xRes'][i],yRes=df['yRes'][i],bounds=self.bounds,raster=self)

    def create_pyramid(self,lowest_pixel_size):
        """
        Generates a log_2 based image pyramid with the most available tiles.

        Args:
            lowest_pixel_size (int): Number of pixels of the size for each tile

        Returns:
            pyramid_dir: The path to where the pyramid was stored
        """
        
        largest_side=max(self.pixel_width,self.pixel_height)
        smallest_side=min(self.pixel_width,self.pixel_height)    

        #finding the biggest available 2-power aspect relationship
        aspect_relationship=self.pixel_width/self.pixel_height
        quadratic_aspect_relationship=closest_base_power(aspect_relationship)

        largest_tile=closest_base_power(smallest_side)
        depth=int(log(largest_tile,2))-int(log(lowest_pixel_size,2))

        if depth<=0:
            print('LA TESELA PEDIDA NO ES DE UN TAMAÑO SUFICIENTE')

        pyramid_dir=folder_check(os.path.join(self.folder,os.path.basename(self.raster_path).split('.')[0])+'_pyramid')
        pyramid_raster_dir=folder_check(os.path.join(pyramid_dir,'raster'))
        pyramid_vector_dir=folder_check(os.path.join(pyramid_dir,'vector'))  

        dirs=[folder_check(os.path.join(pyramid_raster_dir,f'subset_{str(i).zfill(self.nice_write(depth))}')) for i in range(depth+1)]
        image_loaded_generalization=partial(_simplify_single_raster,raster=self)   
        #image_loaded_generalization=partial(_generalize_single_raster,raster=self) 
  
        layers=[layer for layer in range(depth,-1,-1)]
        divisors=[int(2**layer) for layer in layers]
        directories=[dirs[layer] for layer in  layers]
        tile_sizes=[largest_tile/divisor for divisor in divisors]
        teselas=list(map(self.tesselation,directories,tile_sizes))
        m=[t[0] for t in teselas]
        blueprint=[np.array(a) for a in m]
        
        xRes=[self.X_pixel*2**(depth-layer) for layer in layers]
        yRes=[self.Y_pixel*2**(depth-layer) for layer in layers]
        
        xRes=[np.full_like(sample,x).astype(np.float64).tolist() for (sample,x) in zip(blueprint,xRes)]
        yRes=[np.full_like(sample,y).astype(np.float64).tolist() for (sample,y) in zip(blueprint,yRes)]
        xRes_flattened=[i for inte in xRes for i in inte]
        yRes_flattened=[i for inte in yRes for i in inte]
        
        name_lists=[t[0] for t in teselas]
        bound_lists=[t[1] for t in teselas]
        
        bound_gdfs=[gpd.GeoDataFrame({'NAME':name_list},geometry=gpd.GeoSeries.from_wkt([bounds2wkt(bound) for bound in bound_list]),crs=25831) for (name_list,bound_list) in zip(name_lists,bound_lists)]
        [bound_gdf.to_file(os.path.join(pyramid_vector_dir,f'subset_{layer}.geojson')) for (bound_gdf,layer) in zip(bound_gdfs,layers)]
        name_lists_flattened=[t for tesela in teselas for t in tesela[0]]
        bounds_lists_flattened=[t for tesela in teselas for t in tesela[1]]
        
        with ProcessPoolExecutor() as executor:
                results=list(executor.map(image_loaded_generalization,name_lists_flattened,xRes_flattened,yRes_flattened,bounds_lists_flattened))

        return pyramid_dir

    def cloneBand(self,image,dst_filename,driver_name = None):
        """
        Creates a new raster file just like the current, given a matrix 

        Args:
            image (np.array): [[row, col],[row,col],...] pixel-level description of the image
            dst_filename (str): Absolute path of the file to be written to
            driver_name (str, optional): GDAL-Driver to run the create command.If not specified it will guess from the dst_filename, or if it fails as GTiff. Defaults to None.
        """
        
        if driver_name is None:
            extension=os.path.splitext(dst_filename)[1]
            driver_name=driverDict.get(extension,driverDict['.tif'])
        driver = gdal.GetDriverByName(driver_name)
        ndvi_ds= driver.Create(dst_filename, xsize=image.shape[1], ysize=image.shape[0],
                    bands=1, eType=gdal.GDT_Byte)
        ndvi_ds.SetGeoTransform(self.GT)
        ndvi_ds.SetProjection(self.dstSRS_wkt)
        ndvi_ds.GetRasterBand(1).WriteArray(image)
        ndvi_ds=None
    

    
    def find_intersection_centroid(self,gdf):
        """ 
        Intersects an image and a gdf and returns intersection centroid

        Args:
            gdf (gpd.GeoDataFrame): Geospatial table containing a 'geometry' column

        Returns:
            coords: The XY coordinates of the centroid of the intersection
        """
        s1=gdf.geometry
        s3=gpd.GeoSeries.from_wkt([self.wkt],crs=self.crs)
        puntos_inside=s1.intersection(s3[0])
        newdf=gpd.GeoDataFrame(geometry=puntos_inside,crs=self.crs)
        geo_prompt=newdf[newdf['geometry'].area==newdf['geometry'].area.max()].reset_index(drop=True)['geometry'][0].centroid
        if geo_prompt.is_empty==False:
            coords= [geo_prompt.x,geo_prompt.y]
            return coords

class Tile(Ortophoto):
    '''
    Class Tile (Ortophoto)
        Child class from parent Ortophoto
    '''
    def __init__(self,path:str,crs=25831):
        '''
        Args: 
            path (str): Complete path to the tile as a string
            crs (int): CRS of the tile to be loaded. Defaults to 25831.
        '''
        super().__init__(path,
                         os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(path)))),
                         crs
                         )
        self.original_size,self.row,self.col=self.get_row_col()
        self.pyramid=os.path.dirname(os.path.dirname(os.path.dirname(self.raster_path)))
        self.raster_pyramid=os.path.join(self.pyramid,'raster')
        self.pyramid_layer=int(os.path.dirname(self.raster_path).split('_')[-1])
        self.pyramid_depth=len([i  for i in os.listdir(self.raster_pyramid) if os.path.isfile(os.path.join(self.raster_pyramid,i))==False])
        self.folder=os.path.dirname(self.pyramid)
        #self.children=self.get_children()

    def __eq__(self,t2: Ortophoto):
        """
        Args:   
            self(Tile)
            t2(Ortophoto): Tile to be compared
        Returns:
            bool, True if in the same layer of the pyramid
        Exceptions:
            Raise if not an instance of the Ortophoto class 
        """              
        
        if isinstance(t2,(Ortophoto,Tile)):
            return self.pyramid_layer==t2.pyramid_layer
        else:
            raise('NOT AN INSTANCE OF THE CLASS ORTOPHOTO OR TILE')

    def get_pyramid(self,lowest_pixel_size=1024):
        return self.pyramid

    def get_pyramid_depth(self):
        return self.pyramid_depth
        
    def get_row_col(self,path=None):
        """
        Get the original size, row and col of a certain tile

        Args:
            raster (str, optional): Raster path to be added. Defaults to None.

        Returns:
            original_size (int): original size of the parent class from where it has been resampled
            row (int): row in the current pyramid layer
            col (int): col in the current pyramid layer
        """
        raster=self.raster_path
        if path is not None:
            if os.path.exists(path):
                raster=path
            else:
                pass
        metadata_list=os.path.basename(raster).split('.')[0].split('_')
        original_size,row,col=int(metadata_list[1]),int(metadata_list[3]),int(metadata_list[4])
        return  original_size,row,col
        
    def get_n_rows_cols(self):
        """
        Get the number of rows and columns of a certain level in a pyramid

        Returns:
            n_row (int): number of rows at the current level
            n_col (int): number of columns at the current level
        """
        curdir=os.path.join(self.raster_pyramid,f'subset_{self.pyramid_layer}')
        current_siblings=os.listdir(curdir)
        init_size,n_row,n_col=self.get_row_col(os.path.join(curdir,current_siblings[-1]))
        return n_row,n_col
    
    def get_children(self):
        """
        Retrieves the tiles which have a higher resolution for the same point (lower levels of the pyramid for a given tile)

        Returns:
            out_list (list): 2D-list. Each list contains a level of deepness, from closer to the current level until the lowest layer of the pyramid.
        """

        base=self.pyramid_layer
        out_list=[]
        n_row,n_col=self.get_n_rows_cols()
        
        for k in range(1,self.pyramid_depth-base):
            i_min=self.row*2**k
            i_max=i_min+2**k-1
            j_min=self.col*2**k
            j_max=j_min+2**k-1
            current=[]
            for l in range(j_min,j_max+1): 
                for m in range(i_min,i_max+1):
                    current.append((str(m).zfill(self.nice_write((n_row+1)*2**k)),str(l).zfill(self.nice_write((n_col+1)*2**k))))
            out_list.append([os.path.join(self.raster_pyramid,f'subset_{base+k}',f'tile_{int(self.original_size/(2**k))}_grid_{i}_{j}.tif') for i,j in current])
        self.children=out_list
        #self.smallest_children=out_list[-1]
        return out_list
        
    def get_parents(self):
        """
        Retrieves the tiles which have a higher resolution for the same point (lower levels of the pyramid for a given tile)

        Returns:
            out_list (list): 2D-list. Each list contains a level of deepness, from closer to the current level until the lowest layer of the pyramid.
        """
        base=self.pyramid_layer
        out_list=[]
        n_row,n_col=self.get_n_rows_cols()

        for k in range(1,base+1):
            i=int(self.row/2**k)
            j=int(self.col/2**k)
            current=[]
            current.append((str(i).zfill(self.nice_write((n_row+1)/2**k)),str(j).zfill(self.nice_write((n_col+1)/2**k))))
            out_list.append([os.path.join(self.raster_pyramid,f'subset_{base-k}',f'tile_{int(self.original_size*(2**k))}_grid_{i}_{j}.tif') for i,j in current])
        self.parents=out_list
        #self.biggest_parent=out_list[-1]
        return out_list
    
    def get_siblings(self):
        """
        Finds the four tiles which come from one level higher in the pyramid. It is equivalent to finding the first parent and looking at its first children 

        Returns:
            self.siblings (list): A list of the four immediate siblings in the current level of the pyramid

        """
        base=self.pyramid_layer
        size=self.original_size
        i_min=self.row+self.row%-2
        j_min=self.col+self.col%-2
        i_max=i_min+1
        j_max=j_min+1
        sibling_list=[(i_min,j_min),(i_max,j_min),(i_min,j_max),(i_max,j_max)]
        n_row,n_col=self.get_n_rows_cols()
        candidates=[os.path.join(self.raster_pyramid,f'subset_{base}',f'tile_{size}_grid_{str(i).zfill(self.nice_write(n_row+1))}_{str(j).zfill(self.nice_write(n_col+1))}.tif') for i,j in sibling_list]
        
        self.siblings= [c for c in candidates if os.path.exists(c)]
        return self.siblings

        
