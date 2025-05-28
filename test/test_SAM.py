import os
from apb_spatial_computer_vision.sam_utilities import SamGeo_apb
from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision.main import pyramid_sam_apply
from apb_spatial_computer_vision import *
from BETA.text_prompts import text_to_bbox_lowres_complete
from functools import partial
import time

import unittest

class TestSAM(unittest.TestCase):
    vector_file: str
    path_orto: str
    complete_image: Ortophoto

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_folder =  os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        cls.path_orto = os.path.join(cls.test_folder, os.getenv('NAME_ORTOFOTO', 'ORTO_ME_BCN_2023.tif'))
        cls.complete_image = Ortophoto(cls.path_orto)
        cls.vector_file = os.path.join(cls.complete_image.folder,os.getenv('VECTOR_FILE',''))


    def test_sam_from(self):
        sam = SamGeo_apb(
        model_type="vit_h",
        automatic=False,
        sam_kwargs=None,
        )
        self.complete_image.pyramid=os.path.join(self.complete_image.folder,os.path.splitext(self.complete_image.basename)[0]+'_pyramid')
        t0=time.time()
        pyramid_sam_apply(self.complete_image,self.vector_file,1024,'geom',1,sam)
        t1=time.time()


if __name__ == '__main__':
    unittest.main()