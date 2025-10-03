import cv2
import numpy as np
import tempfile, os
from flask import url_for

def save_temp_img(img_array, obj_index):
    temp_dir = os.path.join("static", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    fd, path = tempfile.mkstemp(suffix=f"_obj{obj_index}.png", dir=temp_dir)
    os.close(fd)

    # Sauvegarder directement l'image numpy
    cv2.imwrite(path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

    # Chemin relatif utilisable par Flask
    rel_path = os.path.relpath(path, "static")
    return url_for("static", filename=rel_path)

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
        obj_crop_path = save_temp_img(obj_crop, idx)

        objects.append({
            "class_id": int(cls_id),
            "score": float(score),
            "bbox": [float(x_min), float(y_min), float(x_max), float(y_max)],
            "obj_crop_path": obj_crop_path
        })

    return {
        "num_objects": len(objects),
        "objects": objects
    }

def process_SAM(masks , img , img_result):
    image_rgb = cv2.cvtColor(img , cv2.COLOR_BGR2RGB)
    objects = []
    for idx, mask in enumerate(masks):
        segment = mask["segmentation"].astype(np.uint8)
        obj_img = cv2.bitwise_and(image_rgb , image_rgb , mask=segment)

        ys , xs = np.where(segment > 0)
        if (len(xs) > 0 and len(ys) > 0):
            """Automatic calcilation of bounding box"""
            x_min , x_max = xs.min() , xs.max()
            y_min , y_max = ys.min() , ys.max()
            obj_crop = obj_img[y_min:y_max , x_min:x_max]
        else:
            obj_crop = obj_img
        obj_crop_path = save_temp_img(obj_crop, idx)
        objects.append({
            "class_id": int(idx),
            "score": float(mask.get("score", 1.0)),
            "bbox": [float(x_min), float(y_min), float(x_max), float(y_max)],
            "obj_crop_path": obj_crop_path
        })

    return {
        "num_objects": len(objects),
        "objects": objects
    }
