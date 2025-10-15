import torch
from ultralytics import YOLO
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
import os   
import numpy as np
import cv2
import matplotlib.pyplot as plt
import io
from PIL import Image
from models.helpers import filter_and_merge_segments
import matplotlib     
matplotlib.use('Agg')  # Utiliser le backend 'Agg' pour matplotlib

#Device
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

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
model_type = "vit_h"
sam_model = sam_model_registry[model_type](checkpoint=sam_checkpoint)
sam_model.to(device='cpu')  # erreur float32 mps
mask_generator = SamAutomaticMaskGenerator(
    sam_model,
    **defautlSamParameters()
)
base_save_dir = "img/ModelGen"
os.makedirs(base_save_dir, exist_ok=True)
sam_dir = os.path.join(base_save_dir, "SAM")
def segment_sam(image_path, save=True, min_area=15000, iou_thresh=0.9, merge_thresh=0.3 , mask_generator=mask_generator):
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
    masks = mask_generator.generate(image_rgb)

    # Filter, deduplicate, and merge segments
    masks = filter_and_merge_segments(masks, min_area=min_area, 
                                      iou_thresh=iou_thresh, 
                                      merge_thresh=merge_thresh)

    if save:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_dir = os.path.join(sam_dir, base_name)
        os.makedirs(save_dir, exist_ok=True)

        # Save the picture with all masks overlaid
        plt.figure(figsize=(10, 10))
        plt.imshow(image_rgb)
        for mask in masks:
            seg = mask["segmentation"]
            plt.contour(seg, colors=np.random.rand(3,), linewidths=1)
        plt.axis("off")
        global_path = os.path.join(save_dir, f"{base_name}_all_masks.png")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        buf.seek(0)
        img_pil = Image.open(buf)
        plt.close()
        print(f"Global SAM result saved to {global_path}")

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
            print(f"Saved merged object {idx+1} to {obj_path}")
    # Convert img_pil to numpy array
    img_pil = np.array(img_pil)

    return (masks , image_rgb , img_pil)