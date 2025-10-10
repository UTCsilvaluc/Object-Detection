import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib
matplotlib.use('Agg') 
from torchvision.transforms import functional as F
import io
from PIL import Image
# YOLO
from ultralytics import YOLO

# Faster R-CNN
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

# SAM
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

# =====================
# CONFIGURATION
# =====================

# Device
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print("Using device:", device)

# Dossiers de sauvegarde
base_save_dir = "img/ModelGen"
os.makedirs(base_save_dir, exist_ok=True)

# Créer sous-dossiers pour chaque modèle
yolo_dir = os.path.join(base_save_dir, "YOLO")
faster_dir = os.path.join(base_save_dir, "FasterRCNN")
sam_dir = os.path.join(base_save_dir, "SAM")
for d in [yolo_dir, faster_dir, sam_dir]:
    os.makedirs(d, exist_ok=True)

# =====================
# 1. YOLO
# =====================
yolo_model = YOLO('yolov8n.pt')  

def detect_yolo(image_path, save=True):
    """
    Detect objects in an image using the YOLO model.
    :image_path: Path to the input image.
    :save: Whether to save the annotated image.
    :returns: Tuple (results, original_image, annotated_image, save_path)
    """
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    results = yolo_model(img_rgb)
    #results[0].show()  # affichage

    if save:
        # YOLOv8 save fonctionne via .plot() ou .save() sans save_dir
        save_path = os.path.join(yolo_dir, os.path.basename(image_path))
        
        # Méthode recommandée pour YOLOv8 >= 8.x
        img_result = results[0].plot()  # renvoie un np.array avec les boxes et labels
        cv2.imwrite(save_path, cv2.cvtColor(img_result, cv2.COLOR_RGB2BGR))
        print(f"YOLO result saved to {save_path}")

    return (results , img , img_result , save_path)


# =====================
# 2. Faster R-CNN
# =====================
faster_model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
faster_model.to(device)
faster_model.eval()

COCO_INSTANCE_CATEGORY_NAMES = [
    '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
    'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
    'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana',
    'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
    'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'dining table',
    'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock',
    'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

def detect_fasterrcnn(image_path, threshold=0.3, save=True):
    """
    Not used in the main app, but kept for reference.
    Detect objects in an image using the Faster R-CNN model.
    :image_path: Path to the input image.
    :threshold: Score threshold for displaying boxes.
    :save: Whether to save the annotated image.
    :returns: The raw output from the model.
    """
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_tensor = F.to_tensor(img_rgb).to(device)

    with torch.no_grad():
        outputs = faster_model([img_tensor])

    out = outputs[0]
    boxes = out['boxes'].detach().cpu().numpy()
    scores = out['scores'].detach().cpu().numpy()
    labels = out['labels'].detach().cpu().numpy()

    fig, ax = plt.subplots(1, figsize=(12, 8))
    ax.imshow(img_rgb)

    for box, score, label_id in zip(boxes, scores, labels):
        if score < threshold:
            continue
        label_name = COCO_INSTANCE_CATEGORY_NAMES[label_id] if label_id < len(COCO_INSTANCE_CATEGORY_NAMES) else f"class_{label_id}"
        x1, y1, x2, y2 = box
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2, edgecolor='red', facecolor='none')
        ax.add_patch(rect)
        ax.text(x1, y1-6, f"{label_name} {score:.2f}", fontsize=9, color='white',
                bbox=dict(facecolor='red', alpha=0.6, pad=1))

    plt.axis("off")
    #plt.show()

    if save:
        save_path = os.path.join(faster_dir, os.path.basename(image_path))
        fig.savefig(save_path)
        plt.close(fig)
        print(f"Faster R-CNN result saved to {save_path}")

    return out

# =====================
# 3. SAM
# =====================
sam_checkpoint = "checkpoints/sam_vit_h.pth"
model_type = "vit_h"

sam_model = sam_model_registry[model_type](checkpoint=sam_checkpoint)
sam_model.to(device='cpu')  # erreur float32 mps

mask_generator = SamAutomaticMaskGenerator(
    sam_model,
    points_per_side=16,
    pred_iou_thresh=0.90,
    stability_score_thresh=0.90,
    min_mask_region_area=10000
)

def filter_and_merge_segments(masks, min_area=15000, iou_thresh=0.9, merge_thresh=0.3):
    """
    Filter, deduplicate, and merge partial segments. 
    Allows to narrow down to distinct objects.
    - min_area : minimum area in pixels
    - iou_thresh : inclusion threshold to remove duplicates
    - merge_thresh : IoU threshold to merge two partial masks
    """
    # Step 1: Filter by area
    filtered = []
    for mask in masks:
        seg = mask["segmentation"].astype(np.uint8)
        area = np.sum(seg)
        if area >= min_area:
            filtered.append(seg)

    # Step 2: Remove duplicates (inclusions)
    unique_masks = []
    for i, seg1 in enumerate(filtered):
        keep = True
        for j, seg2 in enumerate(filtered):
            if i == j:
                continue
            inter = np.logical_and(seg1, seg2).sum()
            area1 = seg1.sum()
            if area1 > 0 and inter / area1 > iou_thresh:
                keep = False
                break
        if keep:
            unique_masks.append(seg1)

    # Step 3: Merge overlapping masks
    merged = []
    used = [False] * len(unique_masks)

    for i in range(len(unique_masks)):
        if used[i]:
            continue
        seg_i = unique_masks[i].copy()
        for j in range(i + 1, len(unique_masks)):
            if used[j]:
                continue
            seg_j = unique_masks[j]
            inter = np.logical_and(seg_i, seg_j).sum()
            union = np.logical_or(seg_i, seg_j).sum()
            iou = inter / union if union > 0 else 0
            if iou > merge_thresh:
                # Fusion → OR logique
                seg_i = np.logical_or(seg_i, seg_j).astype(np.uint8)
                used[j] = True
        merged.append(seg_i)
        used[i] = True

    # Build final list of masks
    final_masks = [{"segmentation": m.astype(np.uint8)} for m in merged]
    return final_masks


def segment_sam(image_path, save=True, min_area=15000, iou_thresh=0.9, merge_thresh=0.3):
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