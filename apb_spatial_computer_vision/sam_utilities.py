from apb_spatial_computer_vision import *
from apb_spatial_computer_vision.raster_utilities import Ortophoto,Tile,folder_check
import cv2, numpy as np
from samgeo import *
from samgeo.common import *
# from apb_spatial_computer_vision.sam_predictor_utilities import SamPredictorAPB

# def bbox_to_xy(
#     src_fp: str, coords: list, coord_crs: str = "epsg:4326", **kwargs
# ) -> list:
#     """Converts a list of coordinates to pixel coordinates, i.e., (col, row) coordinates.
#         Note that map bbox coords is [minx, miny, maxx, maxy] from bottomleft to topright
#         While rasterio bbox coords is [minx, max, maxx, min] from topleft to bottomright

#     Args:
#         src_fp (str): The source raster file path.
#         coords (list): A list of coordinates in the format of [[minx, miny, maxx, maxy], [minx, miny, maxx, maxy], ...]
#         coord_crs (str, optional): The coordinate CRS of the input coordinates. Defaults to "epsg:4326".

#     Returns:
#         list: A list of pixel coordinates in the format of [[minx, maxy, maxx, miny], ...] from top left to bottom right.
#     """

#     if isinstance(coords, str):
#         gdf = gpd.read_file(coords)
#         coords = gdf.geometry.bounds.values.tolist()
#         if gdf.crs is not None:
#             coord_crs = f"epsg:{gdf.crs.to_epsg()}"
#     elif isinstance(coords, np.ndarray):
#         coords = coords.tolist()
#     if isinstance(coords, dict):
#         import json

#         geojson = json.dumps(coords)
#         gdf = gpd.read_file(geojson, driver="GeoJSON")
#         coords = gdf.geometry.bounds.values.tolist()

#     elif not isinstance(coords, list):
#         raise ValueError("coords must be a list of coordinates.")

#     if not isinstance(coords[0], list):
#         coords = [coords]

#     new_coords = []

#     with rasterio.open(src_fp) as src:
#         #transform=src.transform
#         #(x_step,min_width,y_step,max_height)=transform[0],transform[2],transform[4],transform[5]
#         #max_width = min_width+src.width*x_step
#         #min_height = max_height+src.height*y_step
#         min_width,min_height=0,0
#         max_width,max_height=src.width,src.height
#         for coord in coords:
#             minx, miny, maxx, maxy = coord

#             if coord_crs != src.crs:
#                 minx, miny = transform_coords(minx, miny, coord_crs, src.crs, **kwargs)
#                 maxx, maxy = transform_coords(maxx, maxy, coord_crs, src.crs, **kwargs)

#                 rows1, cols1 = rasterio.transform.rowcol(
#                     src.transform, minx, miny, **kwargs
#                 )
#                 rows2, cols2 = rasterio.transform.rowcol(
#                     src.transform, maxx, maxy, **kwargs
#                 )

#                 new_coords.append([cols1, rows1, cols2, rows2])

#             else:
#                 new_coords.append([minx, miny, maxx, maxy])

#     result = []

#     for coord in new_coords:
#         minx, maxy, maxx, miny = coord

#         if (
#             minx >= 0
#             and miny >= 0
#             and maxx >= 0
#             and maxy >= 0
#             and minx > min_width
#             and miny > min_height
#             and maxx < max_width
#             and maxy < max_height
#         ):
#             # Note that map bbox coords is [minx, miny, maxx, maxy] from bottomleft to topright
#             # While rasterio bbox coords is [minx, max, maxx, min] from topleft to bottomright
#             result.append([minx, maxy, maxx, miny])

#     if len(result) == 0:
#         print("No valid pixel coordinates found.")
#         return None
#     elif len(result) == 1:
#         return result[0]
#     elif len(result) < len(coords):
#         print("Some coordinates are out of the image boundary.")

#     return result

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
            image=Ortophoto(image).raster.ReadAsArray()
            ar=image[:3,:,:]
            arr=np.transpose(ar,(1,2,0))
            rgb_image=cv2.cvtColor(arr,cv2.COLOR_BGR2RGB)
            self.image=rgb_image
        elif isinstance(image, np.ndarray):
            pass
        else:
            raise ValueError("Input image must be either a path or a numpy array.")
        try:
            self.predictor.set_image(self.image, image_format=image_format)
        except torch.OutOfMemoryError:
            pass

    def predict(
        self,
        point_coords=None,
        point_labels=None,
        boxes=None,
        point_crs=None,
        mask_input=None,
        multimask_output=True,
        return_logits=False,
        output=None,
        index=None,
        mask_multiplier=255,
        dtype="float32",
        return_results=False,
        **kwargs,
    ):
        """Predict masks for the given input prompts, using the currently set image.

        Args:
            point_coords (str | dict | list | np.ndarray, optional): A Nx2 array of point prompts to the
                model. Each point is in (X,Y) in pixels. It can be a path to a vector file, a GeoJSON
                dictionary, a list of coordinates [lon, lat], or a numpy array. Defaults to None.
            point_labels (list | int | np.ndarray, optional): A length N array of labels for the
                point prompts. 1 indicates a foreground point and 0 indicates a background point.
            point_crs (str, optional): The coordinate reference system (CRS) of the point prompts.
            boxes (list | np.ndarray, optional): A length 4 array given a box prompt to the
                model, in XYXY format.
            mask_input (np.ndarray, optional): A low resolution mask input to the model, typically
                coming from a previous prediction iteration. Has form 1xHxW, where for SAM, H=W=256.
                multimask_output (bool, optional): If true, the model will return three masks.
                For ambiguous input prompts (such as a single click), this will often
                produce better masks than a single prediction. If only a single
                mask is needed, the model's predicted quality score can be used
                to select the best mask. For non-ambiguous prompts, such as multiple
                input prompts, multimask_output=False can give better results.
            return_logits (bool, optional): If true, returns un-thresholded masks logits
                instead of a binary mask.
            output (str, optional): The path to the output image. Defaults to None.
            index (index, optional): The index of the mask to save. Defaults to None,
                which will save the mask with the highest score.
            mask_multiplier (int, optional): The mask multiplier for the output mask, which is usually a binary mask [0, 1].
            dtype (np.dtype, optional): The data type of the output image. Defaults to np.float32.
            return_results (bool, optional): Whether to return the predicted masks, scores, and logits. Defaults to False.

        """
        out_of_bounds = []

        if isinstance(boxes, str):
            gdf = gpd.read_file(boxes)
            if gdf.crs is not None:
                gdf = gdf.to_crs("epsg:4326")
            boxes = gdf.geometry.bounds.values.tolist()
        elif isinstance(boxes, dict):
            import json

            geojson = json.dumps(boxes)
            gdf = gpd.read_file(geojson, driver="GeoJSON")
            boxes = gdf.geometry.bounds.values.tolist()

        if isinstance(point_coords, str):
            point_coords = vector_to_geojson(point_coords)

        if isinstance(point_coords, dict):
            point_coords = geojson_to_coords(point_coords)

        if hasattr(self, "point_coords"):
            point_coords = self.point_coords

        if hasattr(self, "point_labels"):
            point_labels = self.point_labels

        if (point_crs is not None) and (point_coords is not None):
            point_coords, out_of_bounds = coords_to_xy(
                self.source, point_coords, point_crs, return_out_of_bounds=True
            )

        if isinstance(point_coords, list):
            point_coords = np.array(point_coords)

        if point_coords is not None:
            if point_labels is None:
                point_labels = [1] * len(point_coords)
            elif isinstance(point_labels, int):
                point_labels = [point_labels] * len(point_coords)

        if isinstance(point_labels, list):
            if len(point_labels) != len(point_coords):
                if len(point_labels) == 1:
                    point_labels = point_labels * len(point_coords)
                elif len(out_of_bounds) > 0:
                    print(f"Removing {len(out_of_bounds)} out-of-bound points.")
                    point_labels_new = []
                    for i, p in enumerate(point_labels):
                        if i not in out_of_bounds:
                            point_labels_new.append(p)
                    point_labels = point_labels_new
                else:
                    raise ValueError(
                        "The length of point_labels must be equal to the length of point_coords."
                    )
            point_labels = np.array(point_labels)

        predictor = self.predictor

        input_boxes = None
        if isinstance(boxes, list) and (point_crs is not None):
            coords = bbox_to_xy(self.source, boxes, point_crs)
            input_boxes = np.array(coords)
            if isinstance(coords[0], int):
                input_boxes = input_boxes[None, :]
            else:
                input_boxes = torch.tensor(input_boxes, device=self.device)
                
                input_boxes = predictor.transform.apply_boxes_torch(
                    input_boxes, self.image.shape[:2]
                )
        elif isinstance(boxes, list) and (point_crs is None):
            input_boxes = np.array(boxes)
            if isinstance(boxes[0], int):
                input_boxes = input_boxes[None, :]

        self.boxes = input_boxes

        if (
            boxes is None
            or (len(boxes) == 1)
            or (len(boxes) == 4 and isinstance(boxes[0], float))
        ):
            if isinstance(boxes, list) and isinstance(boxes[0], list):
                boxes = boxes[0]
            if isinstance(input_boxes,torch.Tensor):
                masks, scores, logits = predictor.predict(
                    point_coords,
                    point_labels,
                    np.array(input_boxes.cpu()),
                    mask_input,
                    multimask_output,
                    return_logits,
                )
            else:
                masks, scores, logits = predictor.predict(
                    point_coords,
                    point_labels,
                    input_boxes,
                    mask_input,
                    multimask_output,
                    return_logits,
                )
        else:
            masks, scores, logits = predictor.predict_torch(
                point_coords=point_coords,
                point_labels=point_coords,
                boxes=input_boxes,
                multimask_output=True,
            )

        self.masks = masks
        self.scores = scores
        self.logits = logits

        if output is not None:
            if boxes is None or (not isinstance(boxes[0], list)):
                self.save_prediction(output, index, mask_multiplier, dtype, **kwargs)
            else:
                self.tensor_to_numpy(
                    index, output, mask_multiplier, dtype, save_args=kwargs
                )

        if return_results:
                return masks, scores, logits

    def raster_to_vector(source, output=None, simplify_tolerance=None, dst_crs=None, **kwargs):
        """Vectorize a raster dataset.

        Args:
            source (str): The path to the tiff file.
            output (str): The path to the vector file.
            simplify_tolerance (float, optional): The maximum allowed geometry displacement.
                The higher this value, the smaller the number of vertices in the resulting geometry.
        """
        from rasterio import features

        with rasterio.open(source) as src:
            band = src.read()

            mask = band != 0
            shapes = features.shapes(band, mask=mask, transform=src.transform)
            src.close()
        fc = [
            {"geometry": shapely.geometry.shape(shape), "properties": {"value": value}}
            for shape, value in shapes
        ]
        if simplify_tolerance is not None:
            for i in fc:
                i["geometry"] = i["geometry"].simplify(tolerance=simplify_tolerance)
            
        gdf = gpd.GeoDataFrame.from_features(fc)
        if src.crs is not None:
            gdf.set_crs(crs=src.crs, inplace=True)

        if dst_crs is not None:
            gdf = gdf.to_crs(dst_crs)        
        
        if output is not None:
            gdf.to_file(output)     
        
        n_gdf=gpd.tools.collect(gdf.geometry)
        return n_gdf.wkt

    @staticmethod    
    def full_to_tif(origin_tile,out_tile,multiplier=255):
        origen=Ortophoto(origin_tile)
        arr=np.full((origen.pixel_height,origen.pixel_width),multiplier)
        origen.cloneBand(arr,out_tile)
    