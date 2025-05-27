import fire
from apb_spatial_computer_vision.main import pyramid_sam_apply,pyramid_sam_apply_geojson
from functools import partial

if __name__ == '__main__':
    
    from apb_spatial_computer_vision.sam_utilities import SamGeo_apb
    
    sam = SamGeo_apb(
       model_type="vit_h",
       automatic=False,
       sam_kwargs=None,
       )
    
    fire.Fire({
        'pyramid_sam_apply': partial(pyramid_sam_apply,sam=sam),
        'pyramid_sam_apply_geojson': partial(pyramid_sam_apply_geojson,sam=sam)
    })
    partial(pyramid_sam_apply,sam=sam)
