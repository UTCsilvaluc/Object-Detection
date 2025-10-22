from flask import Blueprint, request, jsonify, render_template, current_app , url_for
import os
import cv2
import numpy as np
from segment_anything import SamAutomaticMaskGenerator

from utils.helper import (
    build_img_temp_path,
    build_json_temp_path,
    load_json,
    save_json,
    save_temp_img,
    draw_annotations,
    get_next_id_available,
    get_form_metadata,
    fileStorage_to_image,
    control_coordinate_format,
    get_similar_objects
)

from .main_routes import clear_temp

from models.factory import ModelFactory
from models.pretrained_models import (
    sam_model,
    sam_predictor,
    defautlSamParameters
)
from utils.database import (
    get_all_classes,
    get_all_metadata_keys,
    check_if_title_exist,
)

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route('/analyse_point', methods=['POST'])
def analyse_point():
    data = request.get_json() or {}
    img_name = data.get("img_name", "")
    img_annotated_path = build_img_temp_path(data.get("img_annotated_path", "")) #For annotated image path
    img_original_path = build_img_temp_path(data.get("img_original_path", ""))
    json_path = build_json_temp_path(f"{img_name}.json")
    if not os.path.exists(img_original_path):
        return {"error": f"Image not found: {img_original_path}"}, 404
    result_data = load_json(json_path)
    if result_data is None:
        return {"error": f"JSON file not found: {json_path}"}, 404

    x, y = int(data.get("x", 0)), int(data.get("y", 0))
    img = cv2.imread(img_original_path)
    if img is None:
        return {"error": "Failed to read image"}, 500
    # --- SAM Prediction ---
    sam_predictor.set_image(img)
    input_point = np.array([[x, y]])
    input_label = np.array([1])

    masks, scores, logits = sam_predictor.predict(
        point_coords=input_point,
        point_labels=input_label,
        multimask_output=False
    ) #Return a np.darray of masks (N,H,W) , scores (N,) and logits (N,H,W)
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
        result_data = load_json(json_path)
        if result_data is None:
            return {"error": f"JSON file not found: {json_path}"}, 404
    except Exception as e:
        return {"error": f"Failed to read JSON: {e}"}, 500
    new_id = int(get_next_id_available(result_data["objects"]))
    _ , temp_object_name = save_temp_img(obj_img , new_id)
    path = build_img_temp_path(temp_object_name)
    new_object = {
        "class_id": 0,
        "id": new_id,
        "score": float(scores[0]) if masks is not None and scores is not None else 1.0,
        "bbox": bbox,
        "contour": contour_points,
        "obj_crop_path": path,
    }
    result_data["objects"].append(new_object)
    result_data["num_objects"] = len(result_data["objects"])
    result_data = result_data
    new_annotated_img = draw_annotations(img, result_data["objects"])
    cv2.imwrite(img_annotated_path, new_annotated_img)
    save_json(result_data, build_json_temp_path(), img_name)
    return {"success": True, "num_objects": result_data["num_objects"] , "image_id": new_id , "image_path": url_for('main_routes.temp_img', filename=temp_object_name), "bbox": bbox , "tmpName": temp_object_name}, 200

@analysis_bp.route('/re_run_analysis', methods=['POST'])
def re_run_analysis():
    img_name = request.form.get("img_name", "")
    img_annotated_path = request.form.get("img_annotated_path", "")
    img_original_path = request.form.get("img_original_path", "")
    img_original_path = build_img_temp_path(img_original_path)
    img_annotated_path = build_img_temp_path(img_annotated_path)
    if not os.path.exists(img_original_path):
        return {"error": "Image not found"}, 404
    DEFAULT_SAM_PARAMS = defautlSamParameters()
    sam_parameters = {k: type(DEFAULT_SAM_PARAMS[k])(request.form.get(k, v))
                  for k, v in DEFAULT_SAM_PARAMS.items()}
    #Sauvegarder une nouvelle image localement
    img_cv = cv2.imread(img_original_path)
    model = ModelFactory.get_model("sam")
    mask_generator = SamAutomaticMaskGenerator(
        sam_model,
        points_per_side=sam_parameters["points_per_side"],
        pred_iou_thresh=sam_parameters["pred_iou_thresh"],
        stability_score_thresh=sam_parameters["stability_score_thresh"],
        min_mask_region_area=sam_parameters["min_mask_region_area"]
    )
    results , img_original , img_result  = model.run(img_original_path , mask_generator=mask_generator)
    result_data = model.process_results(results , img_original)
    read_json = build_json_temp_path(f"{img_name}.json")
    img_data = {}
    if os.path.exists(read_json):
        old_data = load_json(read_json)
        if old_data is None:
            return {"error": f"JSON file not found: {read_json}"}, 404
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
        "result.html",
        result=result_data,
        name=img_name,
        **img_data,
        **sam_parameters,
        model=model,
        annotated_image_path=annotated_rel_path,
        original_image_path=original_rel_path,
        class_name=class_name,
        metadata_keys=metadata_keys
    )
@analysis_bp.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    if not file:
        return "No file uploaded", 400
    filename = file.filename
    if check_if_title_exist(filename):
        return f"The image name '{filename}' already exists. Please choose a different name. 画像名 '{filename}' は既に存在します。別の名前を選んでください。", 400
    img_cv = fileStorage_to_image(file)
    if img_cv is None:
        return "Invalid image file", 400
    img_path = build_img_temp_path(filename)
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(build_img_temp_path() , exist_ok=True)
    success = cv2.imwrite(img_path, img_cv)
    if not success:
        return "Failed to save image", 500

    # Récupération des métadonnées via helper
    metadata = get_form_metadata(request)
    img_name = metadata.get("name", "unnamed")
    # Chargement image + YOLO
    model_name = "yolo"
    model = ModelFactory.get_model(model_name)
    raw_results , _ , img_result  = model.run(img_path)
    result_data = model.process_results(raw_results , img_cv , img_result)

    # Traitement des résultats YOLO
    model = "YOLOv8"
    if result_data["num_objects"] == 0:
        print("No objects detected with YOLO, switching to SAM...")
        model = ModelFactory.get_model("sam")
        raw_results , _ , img_result  = model.run(img_path)
        result_data = model.process_results(raw_results , img_cv)
        model = "SAM"
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
    os.remove(img_path)
    return render_template(
        "result.html",
        result=result_data,
        **metadata,  # injection directe des métadonnées dans le template
        **defautlSamParameters(), 
        model=model,
        annotated_image_path=annotated_rel_path,
        original_image_path=original_rel_path,
        class_name=class_name,
        metadata_keys=metadata_keys
    )
