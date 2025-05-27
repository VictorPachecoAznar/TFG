import os
from apb_spatial_computer_vision.lang_sam_utilities import LangSAM_apb
from apb_spatial_computer_vision.raster_utilities import Ortophoto
from functools import partial
import time

import unittest

class TestDINO(unittest.TestCase):
    test_folder: str
    path_orto: str
    complete_image: Ortophoto

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_folder =  os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        cls.path_orto = os.path.join(cls.test_folder, os.getenv('NAME_ORTOFOTO', 'ORTO_ME_BCN_2023.tif'))
        cls.text_prompt = os.getenv('TEXT_PROMPT','building')
        cls.complete_image = Ortophoto(cls.path_orto)

    def test_text_prompt(self):
       
        tiles_to_check=self.complete_image.get_pyramid_tiles()
        sam = LangSAM_apb()
        predict_prompt=partial(sam.predict_dino,text_prompt=self.text_prompt,box_threshold=0.24, text_threshold=0.2)

        def predict_save(image):
            pil_image=sam.path_to_pil(image)
            boxes,logits,phrases=predict_prompt(pil_image)
            sam.boxes=boxes
            print('out')
            return sam.save_boxes(dst_crs=self.complete_image.crs)
            
        t0=time.time()
        gdf_list_bboxes_DINO=list(map(predict_save,tiles_to_check))
        t1=time.time()
        print(f'TIME SPENT DOING DINO {t1-t0}')

if __name__ == '__main__':
    unittest.main()
