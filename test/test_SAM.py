import os
from apb_spatial_computer_vision.sam_utilities import SamGeo_apb
from apb_spatial_computer_vision.raster_utilities import Ortophoto
from apb_spatial_computer_vision.main import pyramid_sam_apply

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
        cls.complete_image.pyramid=(os.path.join(cls.complete_image.folder,os.path.basename(cls.complete_image.raster_path).split('.')[0])+'_pyramid')
        vector_file=os.getenv('VECTOR_FILE',None)
        if vector_file is not None:
            if os.path.exists(vector_file):
                cls.vector_file=vector_file
            else:
                cls.vector_file=os.path.join(cls.complete_image.folder, vector_file)
        else:
            cls.vector_file=vector_file
        cls.segmentation_name= os.getenv('TEXT_PROMPT','')


    def test_sam_from(self):
        sam = SamGeo_apb(
        model_type="vit_h",
        automatic=False,
        sam_kwargs=None,)

        self.complete_image.pyramid=os.path.join(self.complete_image.folder,os.path.splitext(self.complete_image.basename)[0]+'_pyramid')

        pyramid_sam_apply(input_image=self.complete_image,
                          detections=self.vector_file,
                          lowest_pixel_size=1024,
                          geometry_column='geom',
                          min_expected_element_area=1,
                          segmentation_name=self.segmentation_name,
                          sam=sam)


if __name__ == '__main__':
    unittest.main()