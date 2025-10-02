import cv2
import base64
import numpy as np

def encode_image_to_base64(img_array):
    """Convertit une image (numpy array) en string base64 pour HTML."""
    _, buffer = cv2.imencode(".png", cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
    return base64.b64encode(buffer).decode("utf-8")

def process_yolo_results(results, img, img_result):
    """
    Traite les résultats YOLO :
    - Retourne le nombre d'objets détectés
    - Retourne les infos des objets (classe, score, bbox, crop en base64)
    - Retourne l'image complète annotée en base64
    """
    boxes = results[0].boxes.xyxy.cpu().numpy()   # [x_min, y_min, x_max, y_max]
    cls_ids = results[0].boxes.cls.cpu().numpy().astype(int)
    scores = results[0].boxes.conf.cpu().numpy()

    # Convertir image originale en RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    objects = []
    for idx, (box, cls_id, score) in enumerate(zip(boxes, cls_ids, scores)):
        x_min, y_min, x_max, y_max = map(int, box)
        obj_crop = img_rgb[y_min:y_max, x_min:x_max]

        # Encoder crop en base64
        obj_b64 = encode_image_to_base64(obj_crop)

        objects.append({
            "class_id": int(cls_id),
            "score": float(score),
            "bbox": [x_min, y_min, x_max, y_max],
            "crop_base64": obj_b64
        })

    # Encoder image annotée YOLO
    annotated_b64 = encode_image_to_base64(img_result)
    image = encode_image_to_base64(img)
    return {
        "num_objects": len(objects),
        "objects": objects,
        "annotated_image": annotated_b64,
        "image": image
    }
