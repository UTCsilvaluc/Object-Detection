from flask import Blueprint, request, redirect, url_for, current_app
import os

from utils.helper import (
    get_form_metadata,
    build_img_temp_path,
    handle_save_images,
    handle_detected_objects,
    build_json,
    empty_to_none,
    load_json,
    build_json_temp_path
)
from utils.database import (
    insert_point,
    insert_metadata_point,
    get_all_metadata_keys 
)

save_bp = Blueprint("save", __name__)

@save_bp.route('/save_metadata', methods=['POST'])
def save_metadata():
    metadata = get_form_metadata(request)
    img_name = metadata.get("name", "unnamed")
    model = empty_to_none(request.form.get("model"))
    num_objects = int(request.form.get("num_objects", 0))
    max_objects_detected = int(request.form.get("max_object_detected", num_objects))
    json_data = load_json(build_json_temp_path(f"{img_name}.json"))

    image_id, version_number = handle_save_images(
        metadata,
        img_name,
        model,
        current_app.config["UPLOAD_FOLDER"],
        build_img_temp_path(request.form.get("annotated_image")),
        build_img_temp_path(request.form.get("original_image"))
    )
    objects_data = handle_detected_objects(request, img_name, image_id, version_number, max_objects_detected , current_app.config["UPLOAD_FOLDER"] , json_data=json_data)

    json_data = build_json(metadata, img_name, num_objects, objects_data)
    #save_json(json_data, build_json_temp_path(), img_name)

    return redirect(url_for("main_routes.gallery"))

@save_bp.route('/save_point', methods=['POST'])
def save_point():
    data = request.get_json()
    if not data:
        return {"success": False, "status": "error", "message": "No data provided"}, 400
    point = data.get("point")
    if not point:
        return {"success": False, "status": "error", "message": "No point data provided"}, 400
    name = point.get("name")
    description = point.get("description")
    loc = point.get("location")
    lat = point.get("latitude")
    lng = point.get("longitude")
    svg_key = point.get("svgKey")
    color = point.get("color" , "#000000")
    metadata = point.get("metadata" , {})
    print("Received point data:", point)
    point_id = insert_point(name, description , loc , lat, lng, svg_key, color)
    print("Inserted point ID:", point_id)
    if not point_id:
        return {"success": False, "status": "error", "message": "Failed to insert point"}, 500
    for key, value in metadata.items():
        insert_metadata_point(point_id, key, value)
    print("Inserted metadata for point ID:", point_id)
    return {"success": True, "message": "Point saved successfully", "status": "success"}, 200
