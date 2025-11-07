from flask import Blueprint, request, jsonify , url_for
import os
import cv2
import numpy as np

from utils.helper import (
    build_img_temp_path,
    build_json_temp_path,
    load_json,
    save_json,
    save_temp_img,
    draw_annotations,
    get_next_id_available
)

from utils.database import (
    get_link_between_objects
)
from models.factory import ModelFactory

object_bp = Blueprint("objects", __name__)

@object_bp.route('/merge_objects', methods=['POST'])
def merge_objects():
    data = request.get_json()
    img_name = data.get('img_name')
    object_ids = data.get('obj_ids', [])
    if not img_name or not object_ids:
        return {"error": "Image name and object IDs are required."}, 400
    img_original_path = build_img_temp_path(data.get('img_original_path'))
    img_annotated_path = build_img_temp_path(data.get('img_annotated_path'))
    json_file_path = build_json_temp_path(f"{img_name}.json")
    if not os.path.exists(json_file_path):
        return {"error": "JSON file not found"}, 404
    result_data = load_json(json_file_path)
    if result_data is None:
        return {"error": f"Failed to load JSON file: {json_file_path}"}, 404
    objects = result_data.get("objects", [])
    # Convert object_ids to integers for comparison
    object_ids = [int(oid) for oid in object_ids if str(oid).isdigit()]
    if not object_ids:
        return {"error": "No valid object IDs provided."}, 400
    objects_to_merge = [obj for obj in objects if obj.get("id") in object_ids]
    if len(objects_to_merge) < 2:
        return {"error": "At least two valid objects are required for merging."}, 400
    model = ModelFactory.get_model("sam")
    image = cv2.imread(img_original_path)
    merged_data = model.merge_objects(image , *objects_to_merge)
    if not merged_data:
        return {"error": "Object merging failed."}, 500 
    merged_mask = merged_data.get("mask")
    bbox = merged_data.get("bbox", [0, 0, 0, 0])
    contours = merged_data.get("contour", [])
    obj_img = cv2.bitwise_and(image, image, mask=merged_mask.astype(np.uint8))
    for id in object_ids:
        obj_to_delete = next((obj for obj in objects if obj.get("id") == id), None)
        if obj_to_delete:
            normalize_path = obj_to_delete.get("obj_crop_path")
            objects.remove(obj_to_delete)
            if normalize_path and os.path.exists(normalize_path):
                os.remove(normalize_path)
    #Suppression des anciens objets dans le JSON (later)
    #Ajout du nouvel objet
    new_id = int(get_next_id_available(objects))
    _ , temp_object_name = save_temp_img(obj_img, new_id)
    path = build_img_temp_path(temp_object_name)
    new_object = {
        "class_id": 0,
        "id": new_id,
        "score": 1.0,
        "bbox": bbox,
        "contour": contours,
        "obj_crop_path": temp_object_name,
    }
    result_data["objects"].append(new_object)
    result_data["num_objects"] = len(result_data["objects"])
    save_json(result_data, build_json_temp_path(), img_name)
    #Réannotation de l'image
    image = draw_annotations(image, result_data["objects"])
    cv2.imwrite(img_annotated_path, image)
    return {"success": True , "num_objects": int(len(result_data["objects"])) , "img_annotated_path": str(img_annotated_path) , "nameNewObj":str(temp_object_name) , "pathObj":url_for('main_routes.temp_img', filename=temp_object_name) , "bbox":str(bbox) , "new_object_id":int(new_id) , "num_objects": int(len(result_data["objects"]))}, 200

@object_bp.route('/remove_object', methods=['POST'])
def remove_object():
    data = request.get_json()
    id = int(data.get('id'))
    img_name = data.get('img_name')
    img_original_path = build_img_temp_path(data.get('img_original_path'))
    img_annotated_path = build_img_temp_path(data.get('img_annotated_path'))
    json_file_path = build_json_temp_path(f"{img_name}.json")
    result_data = load_json(json_file_path)
    if result_data is None:
        return {"error": f"Failed to load JSON file: {json_file_path}"}, 404
    objects = result_data.get("objects", [])
    obj_to_delete = next((obj for obj in objects if obj.get("id") == id), None)
    if obj_to_delete:
        objects.remove(obj_to_delete)
        crop_path = obj_to_delete.get("obj_crop_path")
        if crop_path and os.path.exists(crop_path):
            os.remove(crop_path)
    else:
        return {"error": "Object not found in JSON"}, 404

    save_json(result_data, build_json_temp_path(), img_name)
    image = cv2.imread(img_original_path)
    image = draw_annotations(image, objects)
    if os.path.exists(img_annotated_path):
        os.remove(img_annotated_path)

    cv2.imwrite(img_annotated_path, image)

    return {"success": True, "num_objects": len(objects)}, 200

@object_bp.route('/link_between_objects', methods=['POST'])
def link_between_objects():
    object_links = get_link_between_objects()
    grouped = {}
    if object_links is None:
        return {"status": 'error' ,"success": False, "message": "Failed to retrieve links"}, 500
    for object_link in object_links:
        if object_link['object_id'] not in grouped:
            grouped[object_link['object_id']] = []
        grouped[object_link['object_id']].append({
            'latitude': object_link['latitude'],
            'longitude': object_link['longitude'],
            'image_id': object_link['image_id']
        })
    return {"status": 'success' ,"success": True, "links": grouped}, 200
