# routes/main_routes.py

from flask import Blueprint, render_template, request, send_from_directory , jsonify, send_file
import os
from urllib.parse import unquote

from utils.helper import (
    ROOT_DIR,
    build_json_temp_path,
    build_img_temp_path,
    load_analysis_json,
    build_image_path,
    build_image_thumb_absolute,
    build_image_thumb_relative,
    ensure_image_thumbnail,
    build_image_thumb_absolute_temp,
    build_temp_webp_path
)
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
    get_all_link_types,
    get_all_full_images,
    get_all_full_points,
    get_all_full_links
)

from utils.data_objects import (
    build_object_links
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

    for image in images:
        file_path = image.get("file_path")
        if not file_path:
            image["thumb_path"] = None
            continue
        source_path = build_image_path(file_path)
        thumb_abs = build_image_thumb_absolute(file_path)
        thumb_rel = build_image_thumb_relative(file_path)
        image["thumb_path"] = thumb_rel if ensure_image_thumbnail(source_path, thumb_abs) else None

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
    try:
        result_data, _ = load_analysis_json(json_name, required=False)
    except FileNotFoundError:
        result_data = {"objects": []}

    def _remove_if_exists(path):
        if path and os.path.exists(path):
            os.remove(path)

    def _remove_related_temp(path):
        if not path:
            return
        _remove_if_exists(path)
        _remove_if_exists(build_image_thumb_absolute_temp(path))
        webp_abs, _ = build_temp_webp_path(path)
        _remove_if_exists(webp_abs)

    for obj in result_data.get("objects", []):
        crop_path = obj.get("obj_crop_abs_path") or obj.get("obj_crop_path")
        if not crop_path:
            continue
        crop_abs = crop_path if os.path.isabs(crop_path) else build_img_temp_path(crop_path)
        _remove_related_temp(crop_abs)

    _remove_related_temp(img_original_path)
    _remove_related_temp(img_annotated_path)
    _remove_if_exists(json_dir)
    return {"success": True}, 200

@main_routes_bp.route('/temp/img/<path:filename>')
def temp_img(filename):
    return send_from_directory(build_img_temp_path(), filename)

@main_routes_bp.route('/images/<path:filename>')
def image_file(filename):
    images_root = os.path.join(ROOT_DIR, "static", "img", "Images")
    safe_name = unquote(filename or "").lstrip("/")
    if safe_name.startswith("img/Images/"):
        safe_name = safe_name[len("img/Images/"):]
    if os.path.isabs(safe_name):
        abs_path = os.path.abspath(safe_name)
        if abs_path.startswith(images_root + os.sep) and os.path.exists(abs_path):
            return send_file(abs_path)
        return ("", 404)
    return send_from_directory(images_root, safe_name)

@main_routes_bp.route('/map')
def map_view():
    classes = get_all_classes() 
    metadata_keys = get_all_metadata_keys() 
    link_types = get_all_link_types() 
    return render_template(
        'map.html',
        classes=classes,
        metadata_keys=metadata_keys,
        links=get_all_full_links(),
        link_types=link_types
    )

@main_routes_bp.route("/api/map-data" , methods=["POST"])
def map_data():
    object_datas , shared_objects = build_object_links()
    images = get_all_full_images()
    for image in images:
        file_path = image.get("file_path")
        if not file_path:
            image["thumb_path"] = None
            continue
        source_path = build_image_path(file_path)
        thumb_abs = build_image_thumb_absolute(file_path)
        thumb_rel = build_image_thumb_relative(file_path)
        image["thumb_path"] = thumb_rel if ensure_image_thumbnail(source_path, thumb_abs) else None
    return jsonify({
        "status": True,
        "success": True,
        "images": images,
        "icons": get_all_icons(),
        "points": get_all_full_points(),
        "shared_objects": shared_objects,
        "object_datas": object_datas
    })


@main_routes_bp.route('/objects-overview')
def objects_overview():
    from utils.database import get_objects_overview_sql

    # 1. Fetch everything from SQL
    objects = get_objects_overview_sql()

    # 2. Extract class list
    classes = sorted({obj["class"] for obj in objects if obj["class"]})

    # 3. Extract metadata key list
    metadata_keys = sorted({
        md["key"]
        for obj in objects
        for md in (obj["metadata"] or [])
    })

    # 4. Count total instances
    total_instances = sum(obj["instance_count"] for obj in objects)

    return render_template(
        'objects.html',
        objects=objects,
        classes=classes,
        metadata_keys=metadata_keys,
        total_instances=total_instances
    )
