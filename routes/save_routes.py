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
