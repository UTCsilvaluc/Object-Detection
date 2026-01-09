import os
import math
import threading
from config import Config
from utils.paths import TEMP_ROOT

def _lazy_import_torch():
    import torch
    return torch

def _lazy_import_cv2():
    import cv2
    return cv2

def _lazy_import_np():
    import numpy as np
    return np

def get_sam_device():
    torch = _lazy_import_torch()
    return torch.device(
        "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    )

SAM_MAX_SIDE = int(os.getenv("SAM_MAX_SIDE", "1024"))

#YOLO
_YOLO_MODEL = None

def get_yolo_model():
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        from ultralytics import YOLO
        _YOLO_MODEL = YOLO('yolov8n.pt')
    return _YOLO_MODEL

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
BASE_MODELGEN_DIR = os.path.join(TEMP_ROOT, "modelgen")

SAM_MODEL_MAP = {
    "sam_vit_h": ("vit_h", "sam_vit_h.pth"),
    "sam_vit_l": ("vit_l", "sam_vit_l.pth"),
    "sam_vit_b": ("vit_b", "sam_vit_b.pth"),
    "vit_h": ("vit_h", "sam_vit_h.pth"),
    "vit_l": ("vit_l", "sam_vit_l.pth"),
    "vit_b": ("vit_b", "sam_vit_b.pth"),
    "sam_min": ("vit_b", "sam_vit_b.pth")
}

def resolve_sam_config():
    model_key = getattr(Config, "SAM_MODEL", "sam_vit_h")
    if model_key not in SAM_MODEL_MAP:
        raise ValueError(f"Unknown SAM model '{model_key}'. Expected one of: {', '.join(SAM_MODEL_MAP)}")
    registry_key, checkpoint_file = SAM_MODEL_MAP[model_key]
    checkpoint_path = os.path.join(CHECKPOINTS_DIR, checkpoint_file)
    return registry_key, checkpoint_path

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
        registry_key, default_checkpoint = resolve_sam_config()
        self._registry_key = registry_key
        self._checkpoint_path = checkpoint_path or default_checkpoint
        self._GLOBAL_SAM_MODEL = None
        self._PREDICTOR_IMAGE_ID = None
        self._PREDICTOR_LOCK = threading.Lock()
        self._GENERATOR_LOCK = threading.Lock()

    def _set_sam_model(self, checkpoint_path: str = None):
        if checkpoint_path is None:
            checkpoint_path = self._checkpoint_path
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"SAM checkpoint not found: {checkpoint_path}")
        from segment_anything import sam_model_registry
        self._GLOBAL_SAM_MODEL = sam_model_registry[self._registry_key](
            checkpoint=checkpoint_path
        ).to(device=get_sam_device())

    def get_sam_model(self):
        if self._GLOBAL_SAM_MODEL is None:
            self._set_sam_model()
        return self._GLOBAL_SAM_MODEL

    def _set_sam_predictor(self):
        if self._GLOBAL_SAM_MODEL is None:
            self._set_sam_model()
        from segment_anything import SamPredictor
        self._GLOBAL_SAM_PREDICTOR = SamPredictor(self._GLOBAL_SAM_MODEL)

    def get_mask_predictor(self, image_rgb=None):
        if not hasattr(self, "_GLOBAL_SAM_PREDICTOR") or self._GLOBAL_SAM_PREDICTOR is None:
            self._set_sam_predictor()
        if image_rgb is not None:
            image_id = id(image_rgb)
            if self._PREDICTOR_IMAGE_ID != image_id:
                with self._PREDICTOR_LOCK:
                    self._GLOBAL_SAM_PREDICTOR.set_image(image_rgb)
                    self._PREDICTOR_IMAGE_ID = image_id
        return self._GLOBAL_SAM_PREDICTOR

    def create_mask_generator(self, sam_parameters):
        model = self.get_sam_model()
        from segment_anything import SamAutomaticMaskGenerator
        return SamAutomaticMaskGenerator(model, **sam_parameters)

    def get_predictor_lock(self):
        return self._PREDICTOR_LOCK

    def get_generator_lock(self):
        return self._GENERATOR_LOCK


# GLOBAL INSTANCE SINGLETON OF SAMModel
SAM_GLOBAL_INSTANCE = SAMModel()

def _resize_for_sam(image_rgb, max_side):
    if max_side is None:
        return image_rgb, 1.0
    h, w = image_rgb.shape[:2]
    max_dim = max(h, w)
    if max_dim <= max_side:
        return image_rgb, 1.0
    scale = max_side / float(max_dim)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    cv2 = _lazy_import_cv2()
    resized = cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale

def _upsample_mask(mask, target_shape):
    h, w = target_shape[:2]
    cv2 = _lazy_import_cv2()
    np = _lazy_import_np()
    return cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)

def safe_predict_point(img_rgb , x , y):
    np = _lazy_import_np()
    torch = _lazy_import_torch()
    predictor = SAM_GLOBAL_INSTANCE.get_mask_predictor(img_rgb)
    with SAM_GLOBAL_INSTANCE.get_predictor_lock(), torch.inference_mode():
        masks, scores, logits = predictor.predict(
            point_coords=np.array([[x, y]]),
            point_labels=np.array([1]),
            multimask_output=False
        )
    return masks , scores , logits

def segment_sam(image_path, save=True, sam_parameters=None, min_area=15000, iou_thresh=0.9, merge_thresh=0.3, max_side=None):
    """
    Segment objects in an image using the SAM model.
    :image_path: Path to the input image.
    :save: Whether to save the annotated images.
    :min_area: Minimum area for filtering segments.
    :iou_thresh: IoU threshold for deduplication.
    :merge_thresh: IoU threshold for merging segments.
    :returns: Tuple (masks, original_image, annotated_image)
    """
    cv2 = _lazy_import_cv2()
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_for_sam, scale = _resize_for_sam(image_rgb, SAM_MAX_SIDE if max_side is None else max_side)
    generator = SAM_GLOBAL_INSTANCE.create_mask_generator(sam_parameters or defautlSamParameters())
    torch = _lazy_import_torch()
    with SAM_GLOBAL_INSTANCE.get_generator_lock(), torch.inference_mode():
        masks = generator.generate(image_for_sam)
    scaled_min_area = max(1, int(round(min_area * (scale ** 2)))) if scale < 1.0 else min_area
    # Filter, deduplicate, and merge segments
    from models.helpers import filter_and_merge_segments
    masks = filter_and_merge_segments(masks, min_area=scaled_min_area,
                                      iou_thresh=iou_thresh, 
                                      merge_thresh=merge_thresh)
    if scale != 1.0:
        for mask in masks:
            mask["segmentation"] = _upsample_mask(mask["segmentation"], image_rgb.shape)

    annotated = image_rgb.copy()
    if masks:
        for mask in masks:
            seg = mask["segmentation"]
            np = _lazy_import_np()
            contours, _ = cv2.findContours(seg.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(annotated, contours, -1, (0, 255, 0), 2)

    if save:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_dir = os.path.join(BASE_MODELGEN_DIR, "sam", base_name)
        os.makedirs(save_dir, exist_ok=True)
        # Save each isolated object
        for idx, mask in enumerate(masks):
            np = _lazy_import_np()
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
    return (masks, image_rgb, annotated)

def segment_sam_tiled(image_path , save=True , sam_parameters=None , min_area=10000 , iou_thresh=0.7 , merge_thresh=0.2 , tile_size=1024 , overlap=100, max_side=None):
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
    cv2 = _lazy_import_cv2()
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    H , W , _ = image_rgb.shape
    image_for_sam, scale = _resize_for_sam(image_rgb, SAM_MAX_SIDE if max_side is None else max_side)
    if scale != 1.0:
        H, W = image_for_sam.shape[:2]
    generator = SAM_GLOBAL_INSTANCE.create_mask_generator(sam_parameters or defautlSamParameters())
    scaled_min_area = max(1, int(round(min_area * (scale ** 2)))) if scale < 1.0 else min_area
    all_masks = []

    stride = max(1, tile_size - overlap)
    tiles_x = math.ceil((W - tile_size) / stride) + 1
    tiles_y = math.ceil((H - tile_size) / stride) + 1

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            x1 = tx * stride
            y1 = ty * stride
            x2 = min(x1 + tile_size, W)
            y2 = min(y1 + tile_size, H)
            tile = image_for_sam[y1:y2, x1:x2]
            torch = _lazy_import_torch()
            with SAM_GLOBAL_INSTANCE.get_generator_lock(), torch.inference_mode():
                local_masks = generator.generate(tile)
            if local_masks:
                from models.helpers import filter_and_merge_segments
                local_masks = filter_and_merge_segments(
                    local_masks,
                    min_area=scaled_min_area,
                    iou_thresh=iou_thresh,
                    merge_thresh=merge_thresh
                )
            for mask in local_masks:
                seg = mask["segmentation"]
                np = _lazy_import_np()
                full_seg = np.zeros((H, W), dtype=seg.dtype)
                full_seg[y1:y2, x1:x2] = seg
                mask_reproj = {
                    "segmentation": full_seg,
                    "score": mask.get("score", 0)
                }
                all_masks.append(mask_reproj)
        
    from models.helpers import filter_and_merge_segments
    merged_masks = filter_and_merge_segments(all_masks, min_area=scaled_min_area,
                                             iou_thresh=iou_thresh, 
                                             merge_thresh=merge_thresh)
    if scale != 1.0:
        for mask in merged_masks:
            mask["segmentation"] = _upsample_mask(mask["segmentation"], image_rgb.shape)
    annotated = image_rgb.copy()
    if merged_masks:
        for m in merged_masks:
            seg = m["segmentation"]
            np = _lazy_import_np()
            contours , _ = cv2.findContours(seg.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(annotated, contours, -1, (0,255,0), 2)
    return (merged_masks, image_rgb, annotated)
