# routes/analysis_routes.py

from flask import Blueprint, request, jsonify, render_template, current_app , url_for
import os
import cv2
import numpy as np

from utils.helper import (
    build_img_temp_path,
    build_json_temp_path,
    save_json,
    save_temp_img,
    draw_annotations,
    get_next_id_available,
    get_form_metadata,
    fileStorage_to_image,
    control_coordinate_format,
    get_similar_objects, 
    load_analysis_json,
    add_new_detected_object
)

from .main_routes import clear_temp
from models.factory import ModelFactory
from models.pretrained_models import (
    SAM_GLOBAL_INSTANCE,
    defautlSamParameters
)
from utils.database import (
    get_all_classes,
    get_all_metadata_keys,
    check_if_title_exist,
    get_all_metadatas_values
)

def run_detection_pipeline(img_path, img_cv, force_sam=False, sam_params=None, tiled=False):
    # YOLO → default
    if not force_sam:
        yolo = ModelFactory.get_model("yolo")
        raw_results, _, img_result = yolo.run(img_path)
        result_data = yolo.process_results(raw_results, img_cv, img_result)

        if result_data["num_objects"] > 0:
            return result_data, img_result, "YOLOv8"

    # Fallback SAM
    sam = ModelFactory.get_model("sam")
    raw, _, img_result = sam.run(
        img_path,
        tiled=tiled,
        defaultParameters=sam_params
    )
    result_data = sam.process_results(raw, img_cv)

    return result_data, img_result, "SAM"


analysis_bp = Blueprint("analysis", __name__)

def load_analysis_context(img_name, original_path, annotated_path, require_json=True):
    img_original = build_img_temp_path(original_path)
    img_annotated = build_img_temp_path(annotated_path)

    # Load JSON data
    data, json_path = load_analysis_json(img_name, required=require_json)
    if require_json and data is None:
        return None, f"JSON file not found: {json_path}", None, None, None

    # Load image
    img = cv2.imread(img_original)
    if img is None:
        return None, f"Failed to read image at {img_original}", None, None, None

    return data, None, img, img_original, img_annotated

@analysis_bp.route('/analyse_point', methods=['POST'])
def analyse_point():
    from models.pretrained_models import safe_predict_point
    data = request.get_json() or {}
    img_name = data.get("img_name", "")
    result_data, error, img, _ , img_annotated_path = load_analysis_context(
        img_name,
        data.get("img_original_path", ""),
        data.get("img_annotated_path", ""),
        require_json=True
    )
    if error:
        return {"error": error}, 404
    x, y = int(data.get("x", 0)), int(data.get("y", 0))
    masks , scores , logits = safe_predict_point(img, x, y)
    if masks is None or masks.shape[0] == 0:
        bbox = [x - 100, y - 100, x + 100, y + 100]
        obj_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2]]
        contour_points = []
    else:
        mask = masks[0].astype(np.uint8) * 255
        obj_img = cv2.bitwise_and(img, img, mask=mask)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 0:
            cnt = max(contours, key=cv2.contourArea)
            contour_points = cnt.reshape(-1, 2).astype(int).tolist()
            # Extracting bounding box from mask
            ys, xs = np.where(mask > 0) #Raw ys and columns xs where mask is not zero : couple (y,x) of pixels.
            #Allows to get the bounding box with min and max of raw and columns.
            if len(xs) > 0 and len(ys) > 0:
                x_min, x_max = int(xs.min()), int(xs.max())
                y_min, y_max = int(ys.min()), int(ys.max())
                bbox = [x_min, y_min, x_max, y_max]
                obj_img = obj_img[y_min:y_max, x_min:x_max]
            else:
                bbox = [x - 100, y - 100, x + 100, y + 100]
        else:
            contour_points = []
            # If no contours found, fallback to bounding box only
            print("No contours found in mask — fallback to bounding box only.")
            bbox = [x - 100, y - 100, x + 100, y + 100]
            contour_points = []
            cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
    try:
        result_data , json_path = load_analysis_json(img_name , required=False)
        if result_data is None:
            return {"error": f"JSON file not found: {json_path}"}, 404
    except Exception as e:
        return {"error": f"Failed to read JSON: {e}"}, 500
    new_id = int(get_next_id_available(result_data["objects"]))
    obj_img_rgb = cv2.cvtColor(obj_img, cv2.COLOR_BGR2RGB)
    _ , temp_object_name = save_temp_img(obj_img_rgb , new_id)
    new_object = add_new_detected_object(result_data=result_data, obj_img=obj_img, bbox=bbox, contour=contour_points , score=float(scores[0]) if masks is not None and scores is not None else 1.0)
    new_annotated_img = draw_annotations(img, result_data["objects"])
    cv2.imwrite(img_annotated_path, new_annotated_img)
    save_json(result_data, build_json_temp_path(), img_name)
    return {"success": True, "num_objects": result_data["num_objects"] , "image_id": new_id , "image_path": url_for('main_routes.temp_img', filename=temp_object_name), "bbox": bbox , "tmpName": temp_object_name , "simObj": new_object}, 200
@analysis_bp.route('/re_run_analysis', methods=['POST'])
def re_run_analysis():
    img_name = request.form.get("img_name", "")
    result_data, error, _, img_original_path, img_annotated_path = load_analysis_context(
        img_name,
        request.form.get("img_original_path", ""),
        request.form.get("img_annotated_path", ""),
        require_json=True
    )
    if error:
        return {"error": error}, 404
    csrf_token = request.form.get("csrf_token", "")
    tile = request.form.get("tile-based-analysis", "off") == "on"
    if not os.path.exists(img_original_path):
        return {"error": "Image not found"}, 404
    DEFAULT_SAM_PARAMS = defautlSamParameters()
    sam_parameters = {k: type(DEFAULT_SAM_PARAMS[k])(request.form.get(k, v))
                  for k, v in DEFAULT_SAM_PARAMS.items()}
    #Sauvegarder une nouvelle image localement
    img_cv = cv2.imread(img_original_path)
    result_data, img_result, model_name = run_detection_pipeline(
        img_original_path, img_cv,
        force_sam=True,
        sam_params=sam_parameters,
        tiled=tile
    )
    old_data , json_path = load_analysis_json(img_name , required=False)
    img_data = {}
    if os.path.exists(json_path):
        if old_data is None:
            return {"error": f"JSON file not found: {json_path}"}, 404
        for key in ["description", "date", "location", "latitude", "longitude", "source"]:
            if key in old_data:
                img_data[key] = old_data[key]
    model = "SAM"
    _ , annotated_rel_path = save_temp_img(img_result, "annotated")
    _ , original_rel_path = save_temp_img(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB), "original")
    clear_temp(json_name=img_name , img_original_path=img_original_path , img_annotated_path=img_annotated_path)

    json_dir = build_json_temp_path()
    os.makedirs(json_dir, exist_ok=True)
    objects = result_data.get("objects", [])
    get_similar_objects(objects , top_k=5)
    result_data["objects"] = objects
    JSON_data = {
        "image_name": img_name,
        "desc": img_data.get("description"),
        "date": img_data.get("date"),
        "location": img_data.get("location"),
        "latitude": img_data.get("latitude"),
        "longitude": img_data.get("longitude"),
        "source": img_data.get("source"),
        "num_objects": result_data["num_objects"],
        "objects": result_data.get("objects", [])
    }
    save_json(JSON_data, json_dir, img_name)
    class_name = get_all_classes()
    metadata_keys = get_all_metadata_keys()
    return render_template(
        "upload.html",
        result=result_data,
        img_name=img_name,
        **img_data,
        **sam_parameters,
        model=model,
        annotated_image_path=annotated_rel_path,
        original_image_path=original_rel_path,
        class_name=class_name,
        metadata_keys=metadata_keys,
        csrf_token=csrf_token
    )
@analysis_bp.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    # Récupération des métadonnées via helper
    metadata = get_form_metadata(request)
    img_name = metadata.get("name", "unnamed")
    if not file:
        return "No file uploaded", 400
    if check_if_title_exist(img_name):
        return f"The image name '{img_name}' already exists. Please choose a different name. 画像名 '{img_name}' は既に存在します。別の名前を選んでください。", 400
    img_cv = fileStorage_to_image(file)
    if img_cv is None:
        return "Invalid image file", 400
    img_path = build_img_temp_path(f"{img_name}.jpg")
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(build_img_temp_path() , exist_ok=True)
    success = cv2.imwrite(img_path, img_cv)
    if not success:
        return "Failed to save image", 500

    result_data, img_result, model = run_detection_pipeline(img_path, img_cv)
    _ , annotated_rel_path = save_temp_img(img_result, "annotated")
    _ , original_rel_path = save_temp_img(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB), "original")

    json_dir = build_json_temp_path()
    os.makedirs(json_dir, exist_ok=True)
    if (metadata.get("latitude") and not control_coordinate_format(metadata.get("latitude"))) or \
       (metadata.get("longitude") and not control_coordinate_format(metadata.get("longitude"))):
        os.remove(img_path)
        return "Invalid coordinate format for latitude or longitude. 緯度または経度の座標形式が無効です。", 400
    # Getting similar objects of detected objects :
    objects = result_data.get("objects", [])
    get_similar_objects(objects , top_k=5)
    JSON_data = {
        "image_name": img_name,
        "description": metadata.get("desc"),
        "date": metadata.get("date"),
        "location": metadata.get("location"),
        "latitude": metadata.get("latitude"),
        "longitude": metadata.get("longitude"),
        "source": metadata.get("source"),
        "num_objects": result_data["num_objects"],
        "objects": objects
    }
    save_json(JSON_data, json_dir, img_name)
    if (result_data.get("objects")):
        result_data["objects"] = objects
    class_name = get_all_classes()
    metadata_keys = get_all_metadata_keys()
    metadatas_values = get_all_metadatas_values()
    os.remove(img_path)
    return render_template(
        "upload.html",
        img_name=img_name,
        result=result_data,
        **metadata,  # injection directe des métadonnées dans le template
        **defautlSamParameters(), 
        model=model,
        annotated_image_path=annotated_rel_path,
        original_image_path=original_rel_path,
        class_name=class_name,
        metadata_keys=metadata_keys,
        metadatas_values=metadatas_values
    )
