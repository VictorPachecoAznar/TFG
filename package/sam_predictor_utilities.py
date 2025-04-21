from package import *
from samgeo import SamGeoPredictor

class SamPredictorAPB(SamGeoPredictor):
    def __init__(
        self,
        sam_model,):
        self.predictor=
        from segment_anything.utils.transforms import ResizeLongestSide

        self.model = sam_model
        self.transform = ResizeLongestSide(sam_model.image_encoder.img_size)
