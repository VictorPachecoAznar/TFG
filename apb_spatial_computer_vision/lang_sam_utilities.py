from samgeo.text_sam import LangSAM
import os
import rasterio
from PIL import Image

class LangSAM_apb(LangSAM):
    """Class on top of LangSAM to be able to call Grounding DINO separately from 

    Args:
        LangSAM (samgeo.text_sam class): LangSAM class from SamGeo (Segment-geospatial package, by Qiusheng Wu)
    """
    def __init__(
        self,
        model_type="vit_h",
        checkpoint=None):
        super().__init__(model_type,
        checkpoint)

    def path_to_pil(self,image):
        if isinstance(image, str):
            if not os.path.exists(image):
                raise ValueError(f"Input path {image} does not exist.")
            # Load the georeferenced image
            with rasterio.open(image) as src:
                image_np = src.read().transpose(
                    (1, 2, 0)
                )  # Convert rasterio image to numpy array
                self.transform = src.transform  # Save georeferencing information
                self.crs = src.crs  # Save the Coordinate Reference System
                self.source=image
                image_pil = Image.fromarray(
                    image_np[:, :, :3]
                )  # Convert numpy array to PIL image, excluding the alpha channel
            return image_pil
