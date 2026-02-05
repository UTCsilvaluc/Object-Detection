# routes/save_routes.py

from flask import Blueprint, request, redirect, url_for, current_app , render_template
import json

from utils.helper import (
    get_form_metadata,
    build_img_temp_path,
    handle_save_images,
    handle_detected_objects,
    build_json,
    empty_to_none,
    load_analysis_json
)
from routes.main_routes import clear_temp
from utils.database import (
    insert_point,
    insert_metadata_point,
    insert_link_type,
    insert_link,
    insert_link_endpoint,
    insert_link_metadata,
    insert_link_geometry
)
from utils.analysis_queue import consume_queue_item

save_bp = Blueprint("save", __name__)

@save_bp.route('/save_metadata', methods=['POST'])
def save_metadata():
    metadata = get_form_metadata(request)
    img_name = metadata.get("name", "unnamed")
    model = empty_to_none(request.form.get("model"))
    num_objects = int(request.form.get("num_objects", 0))
    max_objects_detected = int(request.form.get("max_object_detected", num_objects))
    json_data , json_path = load_analysis_json(img_name)
    image_id, version_number , img_path = handle_save_images(
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
    clear_temp(
        json_name=img_name,
        img_annotated_path=build_img_temp_path(request.form.get("annotated_image")),
        img_original_path=build_img_temp_path(request.form.get("original_image"))
    )
    preanalysis_id = request.form.get("preanalysis_id")
    if preanalysis_id:
        consume_queue_item(preanalysis_id)
    if (metadata.get("csrf_token")):
        image = {
            "image_id": image_id,
            "title": img_name,
            "file_path": img_path,
            "description": metadata.get("desc", ""),
            "type": metadata.get("type", ""),
            "capture_date": metadata.get("capture_date", ""),
            "location_name": metadata.get("location", ""),
            "latitude": float(metadata.get("latitude")) if metadata.get("latitude") else None,
            "longitude": float(metadata.get("longitude")) if metadata.get("longitude") else None,
            "source_type": metadata.get("source", ""),
        }
        return render_template('success.html', token=metadata.get("csrf_token") , image=image)
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
    point_id = insert_point(name, description , loc , lat, lng, svg_key, color)
    if not point_id:
        return {"success": False, "status": "error", "message": "Failed to insert point"}, 500
    for key, value in metadata.items():
        insert_metadata_point(point_id, key, value)
    return {"success": True, "message": "Point saved successfully", "status": "success" , "point_id": point_id}, 200

@save_bp.route('/save_link_type', methods=['POST'])
def save_link_type():
    data = request.get_json()
    if not data:
        return {"success": False, "message": "No data provided"}, 400
    key = data.get("key")
    label = data.get("label")
    if not key or not label:
        return {"success": False, "message": "Key and label are required"}, 400
    success = insert_link_type(key, label)
    if not success:
        return {"success": False, "message": "Failed to insert link type"}, 500
    return {"success": True, "message": "Link type saved successfully"}, 200

@save_bp.route('save_link', methods=['POST'])
def save_link():
    data = request.get_json()
    if not data:
        return {"success": False, "message": "No data provided"}, 400
    link = data.get("link")
    if not link:
        return {"success": False, "message": "No link data provided"}, 400
    title = link.get("title")
    description = link.get("description")
    link_type = link.get("link_type")
    endpoints = link.get("endpoints", []) # id , latitude , longitude
    metadata = link.get("metadata", {})
    geometry = link.get("geometry" , None)
    role = None
    link_id = insert_link(title, description, link_type)
    if not link_id:
        return {"success": False, "message": "Failed to insert link"}, 500
    idx = 0
    success = True
    for item in endpoints:
        if item.get("entity_type") == "image":
            insert_link_endpoint(link_id, item.get("entity_type"), item.get("image_id"), None, "waypoint", idx)
        elif item.get("entity_type") == "point":
            insert_link_endpoint(link_id, item.get("entity_type"), None, item.get("point_id"), "waypoint", idx)
        idx += 1 
    for key, value in metadata.items():
        success = insert_link_metadata(link_id, key, value)
        if not success:
            return {"success": False, "message": f"Failed to insert metadata key: {key}"}, 500
    if geometry:
        success = insert_link_geometry(link_id, json.dumps(geometry), None)
    if not success:
        return {"success": False, "message": "Failed to insert link geometry"}, 500
    return {"status": 'success' ,"success": True, "message": "Link saved successfully" , "link_id": link_id}, 200
