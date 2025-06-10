import os
from apb_spatial_computer_vision.lang_sam_utilities import LangSAM_apb
from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision import *
from apb_spatial_computer_vision.main import text_to_bbox_lowres_complete
from functools import partial
import time

import unittest

class TestDINO(unittest.TestCase):
    test_folder: str
    path_orto: str
    complete_image: Ortophoto
    text_prompt: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_folder =  os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        cls.path_orto = os.path.join(cls.test_folder, os.getenv('NAME_ORTOFOTO', 'ORTO_ME_BCN_2023.tif'))
        cls.text_prompt = os.getenv('TEXT_PROMPT','building')
        vector_file=os.getenv('VECTOR_FILE',None)
        cls.complete_image = Ortophoto(cls.path_orto)
        
        if vector_file is not None:
            if os.path.exists(vector_file):
                cls.output_file=vector_file
            else:
                cls.output_file=os.path.join(cls.complete_image.folder, vector_file)
        else:
            cls.output_file=vector_file

    def test_text_prompt(self):
        self.complete_image.pyramid=os.path.join(self.complete_image.folder,os.path.splitext(self.complete_image.basename)[0]+'_pyramid')
        self.complete_image.resolutions=os.path.join(self.complete_image.folder,os.path.splitext(self.complete_image.basename)[0]+'_resolutions')
        t0=time.time()
        text_to_bbox_lowres_complete(self.complete_image,self.text_prompt,output=self.output_file)
        t1=time.time()


if __name__ == '__main__':
    unittest.main()