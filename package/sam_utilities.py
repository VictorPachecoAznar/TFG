from package import *
from package.raster_utilities import Ortophoto,Tile,folder_check
import cv2, numpy as np
from samgeo import SamGeo
from samgeo.common import *

class SamGeo_apb(SamGeo):
    def __init__(self,
        model_type="vit_h",
        automatic=True,
        device=None,
        checkpoint_dir=None,
        sam_kwargs=None,
        **kwargs,):
        super().__init__(model_type,
        automatic,
        device,
        checkpoint_dir,
        sam_kwargs,
        **kwargs,)

    def set_image(self, image, image_format="RGB"):
        """Set the input image as a numpy array.

        Args:
            image (np.ndarray): The input image as a numpy array.
            image_format (str, optional): The image format, can be RGB or BGR. Defaults to "RGB".
        """
        if isinstance(image, str):
            if image.startswith("http"):
                image = download_file(image)

            if not os.path.exists(image):
                raise ValueError(f"Input path {image} does not exist.")

            self.source = image

            image = cv2.imread(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            self.image = image
        elif isinstance(image, np.ndarray):
            ar=image[:3,:,:]
            arr=np.transpose(ar,(2,1,0))
            rgb_image=cv2.cvtColor(arr,cv2.COLOR_BGR2RGB)
            self.image=rgb_image
        else:
            raise ValueError("Input image must be either a path or a numpy array.")

        self.predictor.set_image(self.image, image_format=image_format)
    