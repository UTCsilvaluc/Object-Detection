import cv2
import numpy as np
from utils.helper import save_temp_img, create_new_object

def process_yolo_results(self,results, img, img_result):
    """
    Traite les résultats YOLO :
    - Retourne le nombre d'objets détectés
    - Retourne les infos des objets (classe, score, bbox, crop en base64)
    - Retourne l'image complète annotée en base64
    :param results: Résultats bruts de YOLO
    :param img: Image originale (BGR)
    :param img_result: Image annotée (RGB)
    :return: Dictionnaire avec les informations des objets détectés
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
        # dans process_yolo_results, même principe
        _ , obj_crop_path = save_temp_img(obj_crop, idx)
        embedding_vector = self.generate_embedding(img_rgb , box).tolist()
        objects.append({
            "class_id": int(cls_id),
            "id": int(idx),
            "score": float(score),
            "bbox": [float(x_min), float(y_min), float(x_max), float(y_max)],
            "obj_crop_path": obj_crop_path,   # chemin relatif pour template # chemin absolu pour sauvegarde
            "embedding": embedding_vector
        })


    return {
        "num_objects": len(objects),
        "objects": objects
    }

def process_SAM(self,masks , img):
    """
    Handle SAM results:
    - Returns the number of detected objects
    - Returns object info (id, score, bbox, contour, crop path)
    - Returns the full annotated image path
    :param masks: Raw results from SAM
    :param img: Original image (BGR)
    :param img_result: Annotated image (RGB)
    :return: Dictionary with detected object information
    """
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
        contours , _ = cv2.findContours(segment , cv2.RETR_EXTERNAL , cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            contour_points = [[int(x) , int(y)] for x , y in contours[0].squeeze().tolist()]
        else:
            contour_points = []
        objects.append(create_new_object(
            obj_img=obj_img,
            bbox=[float(x_min), float(y_min), float(x_max), float(y_max)],
            contour=contour_points,
            new_id=idx,
            score=1.0
        ))

    return {
        "num_objects": len(objects),
        "objects": objects
    }
