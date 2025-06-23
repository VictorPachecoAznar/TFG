import fire
from apb_spatial_computer_vision.main import pyramid_sam_apply,text_to_bbox_lowres_complete,point_prompt_based_sam
from functools import partial,update_wrapper
from apb_spatial_computer_vision.lang_sam_utilities import LangSAM_apb
from apb_spatial_computer_vision.sam_utilities import SamGeo_apb

def smart_partial(function,**kwargs):
    """
    Partial function that keeps documentation
    
    Args:
        function (function): The original function
        **kwargs: The arguments to be stored onto the funtion
    Returns:
        function (function): Partialized function with all documentation
    """
    return update_wrapper(partial(function,**kwargs),function)

if __name__ == '__main__':
    
    sam = SamGeo_apb(
       model_type="vit_h",
       automatic=False,
       sam_kwargs=None,
       )
    
    lang_sam=LangSAM_apb()
    
    fire.Fire({
        'dino': smart_partial(text_to_bbox_lowres_complete,sam=lang_sam),
        'sam' : smart_partial(pyramid_sam_apply,sam=sam),
        'second_iteration': smart_partial(point_prompt_based_sam,sam=sam)
    })
    
    partial(pyramid_sam_apply,sam=sam)
