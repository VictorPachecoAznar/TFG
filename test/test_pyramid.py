import os
import time

from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision import *

import matplotlib.pyplot as plt
import tqdm
import unittest

class TestPyramid(unittest.TestCase):
    test_folder: str
    path_orto: str
    complete_image: Ortophoto

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_folder =  os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        cls.path_orto = os.path.join(cls.test_folder, os.getenv('NAME_ORTOFOTO', 'ORTO_ME_BCN_2023.tif'))
        cls.complete_image = Ortophoto(cls.path_orto)

    def test_create_ortophoto(self):
        self.assertTrue(os.path.exists(self.path_orto), f"Ortophoto file does not exist: {self.path_orto}")
        self.assertIsInstance(self.complete_image, Ortophoto, "Complete image should be an instance of Ortophoto")

    def test_create_pyramid(self):
        #         complete_image.create_gdal_parallelized_resolutions(5)

        #         own_parallelized.append(t1-t0)
        # folder=os.path.join(DATA_DIR,'ORTO_ZAL_BCN')

        # shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ME_BCN_pyramid'))

        # DEGRADE RESOLUTION
        # gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_58_98.tif'),xRes=0.1,yRes=0.1)
        # gdal.Warp(os.path.join(dirs[0],'out.tif'),os.path.join(DATA_DIR,'tiles_1024_safe','result_1024_grid_0_0.tif'),xRes=0.1,yRes=0.1,resampleAlg='average')

        t0 = time.time()
        self.complete_image.get_pyramid(1024)
        t1 = time.time()
        print(f'TIEMPO TRANSCURRIDO{t1 - t0}')

        # own_parallelized=[]
        # for i in range(1):
        #     t0=time.time()
        #     complete_image.create_gdal_parallelized_resolutions(5)
        #     t1=time.time()
        #     own_parallelized.append(t1-t0)
        #       shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_resolutions'))

        # times_parallelized=[]
        # for i in range(1):
        #     t0=time.time()
        #     complete_image.create_resolutions(5)
        #     t1=time.time()
        #     times_parallelized.append(t1-t0)
        #     #shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_resolutions'))

        # print(complete_image.area)
        # parallelized_time=t1-t0
        # print(f'TIEMPO TRANSCURRIDO {parallelized_time}')

        # times_non_parallelized=[]
        # for i in range(1):
        #     t2=time.time()
        #     complete_image.create_non_parallelized_resolutions(5)
        #     t3=time.time()
        #     times_non_parallelized.append(t3-t2)
        #     shutil.rmtree(os.path.join(DATA_DIR,'ORTO_ZAL_BCN_resolutions'))

        # data=[times_parallelized,times_non_parallelized,own_parallelized]
        # # [[81.96791672706604], [181.64886450767517], [179.33391308784485]]

        # print(data)
        # ax=plt.axes()
        # plt.boxplot(data)
        # plt.title('CREACIÓN DE IMÁGENES CON DISTINTAS RESOLUCIONES')
        # #ax.
        # plt.show()
        # print('picture')
        
    def test_polygonize_with_gdal(self):
        t0 = time.time()
        self.complete_image.polygonize(1024)
        t1 = time.time()
        print(f'TIME OCURRED:{t1 - t0}')
    
    def test_resolutions(self):
        print(self.complete_image.pyramid)
        self.complete_image.get_resolutions()
    

if __name__ == '__main__':
    unittest.main()
