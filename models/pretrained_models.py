import torch
from ultralytics import YOLO
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator , SamPredictor
import os   
import math
import threading
import numpy as np
import cv2
from PIL import Image
from models.helpers import filter_and_merge_segments
from segment_anything import sam_model_registry , SamAutomaticMaskGenerator , SamPredictor
#Device
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
SAM_DEVICE = torch.device("cpu")

#YOLO
yolo_model = YOLO('yolov8n.pt')

#SAM

def defautlSamParameters():
    return {
        "points_per_side": 16, 
        "pred_iou_thresh": 0.90,
        "stability_score_thresh": 0.90,
        "min_mask_region_area": 10000
    }

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINTS_DIR = os.path.join(PROJECT_ROOT, "checkpoints")
sam_checkpoint = os.path.join(CHECKPOINTS_DIR, "sam_vit_h.pth")
base_save_dir = "img/ModelGen"
os.makedirs(base_save_dir, exist_ok=True)
sam_dir = os.path.join(base_save_dir, "SAM")

class SAMModel:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SAMModel, cls).__new__(cls)
        return cls._instance

    def __init__(self, checkpoint_path: str = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._checkpoint_path = checkpoint_path or sam_checkpoint
        self._GLOBAL_SAM_MODEL = None
        self._PREDICTOR_LOCK = threading.Lock()
        self._GENERATOR_LOCK = threading.Lock()

    def _set_sam_model(self, checkpoint_path: str = None):
        if checkpoint_path is None:
            checkpoint_path = sam_checkpoint
        self._GLOBAL_SAM_MODEL = sam_model_registry["vit_h"](
            checkpoint=checkpoint_path
        ).to(device=SAM_DEVICE)

    def get_sam_model(self):
        if self._GLOBAL_SAM_MODEL is None:
            self._set_sam_model()
        return self._GLOBAL_SAM_MODEL

    def _set_sam_predictor(self):
        if self._GLOBAL_SAM_MODEL is None:
            self._set_sam_model()
        self._GLOBAL_SAM_PREDICTOR = SamPredictor(self._GLOBAL_SAM_MODEL)

    def get_mask_predictor(self):
        if not hasattr(self, "_GLOBAL_SAM_PREDICTOR") or self._GLOBAL_SAM_PREDICTOR is None:
            self._set_sam_predictor()
        return self._GLOBAL_SAM_PREDICTOR

    def create_mask_generator(self, sam_parameters):
        model = self.get_sam_model()
        return SamAutomaticMaskGenerator(model, **sam_parameters)

    def get_predictor_lock(self):
        return self._PREDICTOR_LOCK

    def get_generator_lock(self):
        return self._GENERATOR_LOCK


# GLOBAL INSTANCE SINGLETON OF SAMModel
SAM_GLOBAL_INSTANCE = SAMModel()

def safe_predict_point(img_rgb , x , y):
    predictor = SamPredictor(SAM_GLOBAL_INSTANCE.get_sam_model())
    with SAM_GLOBAL_INSTANCE.get_predictor_lock():
        predictor.set_image(img_rgb)
    masks , scores , logits = predictor.predict(
        point_coords = np.array([[x , y]]),
        point_labels = np.array([1]),
        multimask_output=False
    )
    return masks , scores , logits

def segment_sam(image_path, save=True, sam_parameters=None, min_area=15000, iou_thresh=0.9, merge_thresh=0.3):
    """
    Segment objects in an image using the SAM model.
    :image_path: Path to the input image.
    :save: Whether to save the annotated images.
    :min_area: Minimum area for filtering segments.
    :iou_thresh: IoU threshold for deduplication.
    :merge_thresh: IoU threshold for merging segments.
    :returns: Tuple (masks, original_image, annotated_image)
    """
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    generator = SAM_GLOBAL_INSTANCE.create_mask_generator(sam_parameters or defautlSamParameters())
    with SAM_GLOBAL_INSTANCE.get_generator_lock():
        masks = generator.generate(image_rgb)
    # Filter, deduplicate, and merge segments
    masks = filter_and_merge_segments(masks, min_area=min_area, 
                                      iou_thresh=iou_thresh, 
                                      merge_thresh=merge_thresh)

    if save:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_dir = os.path.join(sam_dir, base_name)
        os.makedirs(save_dir, exist_ok=True)
        for mask in masks:
            seg = mask["segmentation"]
            contours , _ = cv2.findContours(seg.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(image_rgb, contours, -1, (0,255,0), 2)

        img_pil = Image.fromarray(image_rgb)


        # Save each isolated object
        for idx, mask in enumerate(masks):
            seg = mask["segmentation"].astype(np.uint8)
            obj_img = cv2.bitwise_and(image_rgb, image_rgb, mask=seg)

            ys, xs = np.where(seg > 0)
            if len(xs) > 0 and len(ys) > 0:
                x_min, x_max = xs.min(), xs.max()
                y_min, y_max = ys.min(), ys.max()
                obj_crop = obj_img[y_min:y_max, x_min:x_max]
            else:
                obj_crop = obj_img

            obj_path = os.path.join(save_dir, f"{base_name}_obj_{idx+1}.png")
            cv2.imwrite(obj_path, cv2.cvtColor(obj_crop, cv2.COLOR_RGB2BGR))
    # Convert img_pil to numpy array
    img_pil = np.array(img_pil)

    return (masks , image_rgb , img_pil)

def segment_sam_tiled(image_path , save=True , sam_parameters=None , min_area=10000 , iou_thresh=0.7 , merge_thresh=0.2 , tile_size=1024 , overlap=100):
    """
    Segment objects in an image using the SAM model with tiling.
    :image_path: Path to the input image.
    :save: Whether to save the annotated images.
    :min_area: Minimum area for filtering segments.
    :iou_thresh: IoU threshold for deduplication.
    :merge_thresh: IoU threshold for merging segments.
    :tile_size: Size of each tile.
    :overlap: Overlap between tiles.
    :returns: Tuple (masks, original_image, annotated_image)
    """
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    H , W , _ = image_rgb.shape
    generator = SAM_GLOBAL_INSTANCE.create_mask_generator(sam_parameters or defautlSamParameters())
    all_masks = []
    tile_masks_count = 0

    tiles_x = math.ceil(W / tile_size)
    tiles_y = math.ceil(H / tile_size)

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            x1 = tx * tile_size
            y1 = ty * tile_size
            x2 = min(x1 + tile_size, W)
            y2 = min(y1 + tile_size, H)
            tile = image_rgb[y1:y2, x1:x2]
            with SAM_GLOBAL_INSTANCE.get_generator_lock():
                local_masks = generator.generate(tile)
            for mask in local_masks:
                seg = mask["segmentation"]
                full_seg = np.zeros((H, W), dtype=seg.dtype)
                full_seg[y1:y2, x1:x2] = seg
                
                mask_reproj = {
                    "segmentation": full_seg,
                    "score": mask.get("score", 0)
                }
                all_masks.append(mask_reproj)
            tile_masks_count += len(local_masks)
        
    merged_masks = filter_and_merge_segments(all_masks, min_area=min_area, 
                                             iou_thresh=iou_thresh, 
                                             merge_thresh=merge_thresh)
    annotated = image_rgb.copy()
    if save and merged_masks:
        for m in merged_masks:
            seg = m["segmentation"]
            contours , _ = cv2.findContours(seg.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(annotated, contours, -1, (0,255,0), 2)
    annotated_pil = Image.fromarray(annotated)
    return (merged_masks , image_rgb , np.array(annotated_pil))
