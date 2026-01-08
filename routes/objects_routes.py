# routes/objects_routes.py

from flask import Blueprint, request , url_for
import os
import cv2
import numpy as np

from utils.helper import (
    build_json_temp_path,
    build_img_temp_path,
    save_json,
    save_temp_img,
    draw_annotations,
    load_analysis_json,
    load_analysis_context,
    add_new_detected_object,
    build_temp_webp_path,
    ensure_display_webp
)

from utils.data_objects import build_object_links

from models.factory import ModelFactory
object_bp = Blueprint("objects", __name__)

@object_bp.route('/merge_objects', methods=['POST'])
def merge_objects():
    data = request.get_json()
    img_name = data.get('img_name')
    object_ids = data.get('obj_ids', [])
    result_data, error, image, img_original_path, img_annotated_path = load_analysis_context(
        img_name,
        data.get("img_original_path", ""),
        data.get("img_annotated_path", ""),
        require_json=True
    )
    if error:
        return {"error": error}, 404
    result_data , json_file_path = load_analysis_json(img_name)
    objects = result_data.get("objects", [])
    # Convert object_ids to integers for comparison
    object_ids = [int(oid) for oid in object_ids if str(oid).isdigit()]
    if not object_ids:
        return {"error": "No valid object IDs provided."}, 400
    objects_to_merge = [obj for obj in objects if obj.get("id") in object_ids]
    if len(objects_to_merge) < 2:
        return {"error": "At least two valid objects are required for merging."}, 400
    model = ModelFactory.get_model("sam")
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
    new_object, new_id = add_new_detected_object(result_data=result_data, obj_img=obj_img, bbox=bbox, contour=contours , score=1.0)
    object_img_rgb = cv2.cvtColor(obj_img, cv2.COLOR_BGR2RGB)
    _ , temp_object_name = save_temp_img(object_img_rgb, new_id)
    webp_abs, webp_rel = build_temp_webp_path(temp_object_name)
    temp_object_display = webp_rel if ensure_display_webp(build_img_temp_path(temp_object_name), webp_abs) else temp_object_name
    save_json(result_data, build_json_temp_path(), img_name)
    image = draw_annotations(image, result_data["objects"])
    cv2.imwrite(img_annotated_path, image)
    webp_abs, _ = build_temp_webp_path(os.path.basename(img_annotated_path))
    ensure_display_webp(img_annotated_path, webp_abs)
    return {"success": True , "num_objects": int(len(result_data["objects"])) , "img_annotated_path": str(img_annotated_path) , "nameNewObj":str(temp_object_name) , "pathObj":url_for('main_routes.temp_img', filename=temp_object_display) , "bbox":str(bbox) , "new_object_id":int(new_id) , "num_objects": int(len(result_data["objects"])) , "simObj": new_object}, 200

@object_bp.route('/remove_object', methods=['POST'])
def remove_object():
    data = request.get_json()
    try:
        obj_id = int(data.get('id'))
    except (TypeError, ValueError):
        return {"error": "Invalid object id"}, 400

    img_name = (data.get('img_name') or '').strip()
    result_data, error, image, img_original_path, img_annotated_path = load_analysis_context(
        img_name,
        data.get("img_original_path", ""),
        data.get("img_annotated_path", ""),
        require_json=True
    )
    if error or result_data is None or image is None:
        return {"error": error or "Analysis context not found"}, 404

    objects = result_data.get("objects", [])
    obj_to_delete = next((obj for obj in objects if obj.get("id") == obj_id), None)
    if not obj_to_delete:
        return {"error": "Object not found in JSON"}, 404

    # Remove the object from the in-memory list and persist it to disk
    objects[:] = [obj for obj in objects if obj.get("id") != obj_id]
    result_data["num_objects"] = len(objects)

    crop_path = obj_to_delete.get("obj_crop_path")
    if crop_path:
        crop_abs = crop_path if os.path.isabs(crop_path) else build_img_temp_path(crop_path)
        if os.path.exists(crop_abs):
            os.remove(crop_abs)

    save_json(result_data, build_json_temp_path(), img_name)

    annotated_image = draw_annotations(image.copy(), objects)
    cv2.imwrite(img_annotated_path, annotated_image)
    webp_abs, _ = build_temp_webp_path(os.path.basename(img_annotated_path))
    ensure_display_webp(img_annotated_path, webp_abs)

    return {"success": True, "num_objects": len(objects)}, 200


@object_bp.route('/link_between_objects', methods=['POST'])
def link_between_objects():
    object_datas , shared_objects = build_object_links()
    return {
        "status": "success",
        "success": True,
        "object_datas": object_datas,
        "shared_objects": shared_objects
    }, 200
