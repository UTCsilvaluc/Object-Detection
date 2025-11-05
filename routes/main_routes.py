from flask import Blueprint, render_template, request, send_from_directory
import os

from utils.helper import build_json_temp_path, build_img_temp_path, load_json
from utils.database import (
    get_all_images,
    get_image_by_id,
    get_versions_by_image_id,
    get_objects_by_image_version,
    get_metadata_by_object_id,
    get_all_image_title,
    get_all_classes,
    get_all_metadata_keys,
    get_all_icons,
    get_all_points,
    get_metadata_by_point_id,
    get_link_between_objects,
    get_all_links,
    get_all_link_types
)

main_routes_bp = Blueprint("main_routes", __name__)

@main_routes_bp.route('/')
def index():
    titles = get_all_image_title()
    return render_template('index.html', titles=titles)

@main_routes_bp.route('/gallery')
def gallery():
    try:
        images = get_all_images() 
    except Exception as e:
        print(f"Error fetching images: {e}")
        images = []

    return render_template('gallery.html', images=images)

@main_routes_bp.route('/view_image/<int:image_id>')
def view_image(image_id):
    image_data = get_image_by_id(image_id)
    if not image_data:
        return "Image not found", 404
    versionedImages = get_versions_by_image_id(image_id)
    objects = get_objects_by_image_version(image_id , versionedImages[0]['version_number']) if versionedImages else []
    idx = 0
    for obj in objects:
        obj_metadata = get_metadata_by_object_id(image_id=image_id, object_id=obj['object_id'])
        objects[idx]['metadatas'] = obj_metadata
        idx += 1
    return render_template('viewer.html', image=image_data, versions=versionedImages, objects=objects, object_number=len(objects))

@main_routes_bp.route('/clear_temp', methods=['POST'])
def clear_temp(json_name=None , img_original_path=None , img_annotated_path=None):
    data = request.get_json() if json_name is None else {}
    json_name = data.get("img_name", "") if not json_name else json_name
    json_dir = build_json_temp_path(f"{json_name}.json")
    img_original_path = data.get("img_original_path", "") if not img_original_path else img_original_path
    img_annotated_path = data.get("img_annotated_path", "") if not img_annotated_path else img_annotated_path
    result_data = load_json(json_dir)
    if result_data is None:
        return {"error": f"Failed to load JSON file: {json_dir}"}, 404
    for obj in result_data.get("objects", []):
        crop_path = obj.get("obj_crop_abs_path")
        if crop_path and os.path.exists(crop_path):
            os.remove(crop_path)
            os.remove(img_original_path) if os.path.exists(img_original_path) else None
            os.remove(img_annotated_path) if os.path.exists(img_annotated_path) else None
    os.remove(json_dir)
    return {"success": True}, 200

@main_routes_bp.route('/temp/img/<path:filename>')
def temp_img(filename):
    return send_from_directory(build_img_temp_path(), filename)

@main_routes_bp.route('/map')
def map_view():
    images = get_all_images()
    classes = get_all_classes()
    metadata_keys = get_all_metadata_keys()
    icons = get_all_icons()
    points = get_all_points()
    grouped = {}
    object_links = get_link_between_objects()
    link_types = get_all_link_types()
    links = get_all_links()
    for object_link in object_links:
        if object_link['object_id'] not in grouped:
            grouped[object_link['object_id']] = []
        grouped[object_link['object_id']].append({
            'latitude': object_link['latitude'],
            'longitude': object_link['longitude'],
            'image_id': object_link['image_id']
        })
    for point in points:
        point['metadata'] = get_metadata_by_point_id(point['point_id'])
    return render_template('map.html', images=images, classes=classes, metadata_keys=metadata_keys, icons=icons, points=points, object_links=grouped , links=links, link_types=link_types)
