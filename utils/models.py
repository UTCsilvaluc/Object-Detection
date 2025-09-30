import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from torchvision.transforms import functional as F

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

    return results


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

def segment_sam(image_path, save=True):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    masks = mask_generator.generate(image_rgb)

    # Visualisation
    plt.figure(figsize=(10,10))
    plt.imshow(image_rgb)
    for mask in masks:
        seg = mask["segmentation"]
        plt.contour(seg, colors=np.random.rand(3,), linewidths=1)
    plt.axis("off")
    #plt.show()

    if save:
        save_path = os.path.join(sam_dir, os.path.basename(image_path))
        plt.savefig(save_path)
        plt.close()
        print(f"SAM result saved to {save_path}")

    return masks

# =====================
# Exemple : parcours toutes les images
# =====================
image_folder = "img/Images"
images = sorted([f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg','.jpeg','.png'))])

for img_file in images:
    img_path = os.path.join(image_folder, img_file)
    print(f"\nProcessing {img_file} with YOLO...")
    detect_yolo(img_path)
    print(f"Processing {img_file} with Faster R-CNN...")
    detect_fasterrcnn(img_path)
    print(f"Processing {img_file} with SAM...")
    segment_sam(img_path)
