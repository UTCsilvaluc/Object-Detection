from flask import Flask , render_template , request , redirect , url_for , send_from_directory
from ultralytics.utils.plotting import colors
from utils.database import *
from utils.helper import *
from models.factory import ModelFactory
from models.pretrained_models import sam_model
import cv2
import numpy as np
from segment_anything import SamAutomaticMaskGenerator
from models.pretrained_models import defautlSamParameters , sam_predictor
import os
import json
app = Flask(__name__)

UPLOAD_FOLDER = "static/img/Images" #Flask travaille automatiquement avec le dossier static
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # crée le dossier s'il n'existe pas
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_rectangle', methods=['POST'])
def add_rectangle():
    data = request.get_json() or {}
    img_name = data.get("img_name", "")
    img_annotated_path = build_img_temp_path(data.get("img_annotated_path", ""))
    json_path = build_json_temp_path(f"{img_name}.json")

    if not os.path.exists(img_annotated_path):
        return {"error": f"Image not found: {img_annotated_path}"}, 404
    if not os.path.exists(json_path):
        return {"error": f"JSON not found: {json_path}"}, 404

    x, y = int(data.get("x", 0)), int(data.get("y", 0))
    img = cv2.imread(img_annotated_path)
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
    )

    # --- If no mask generated ---
    if masks is None or masks.shape[0] == 0:
        print("No mask generated — fallback to bounding box only.")
        bbox = [x - 100, y - 100, x + 100, y + 100]
        cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        obj_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2]]
        contour_points = []
    else:
        mask = masks[0].astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        obj_img = cv2.bitwise_and(img, img, mask=mask)
        if len(contours) > 0:
            cv2.drawContours(img, contours, -1, (0, 255, 0), 2)

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

            # Convert contour to list of points. 
            contour_points = [[int(px), int(py)] for px, py in contours[0].squeeze().tolist()] #squeeze to remove single-dimensional entries from the shape of an array.
        else:
            # If no contours found, fallback to bounding box only
            bbox = [x - 100, y - 100, x + 100, y + 100]
            contour_points = []
            cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

    cv2.imwrite(img_annotated_path, img)
    try:
        with open(json_path, 'r', encoding='utf-8') as json_file:
            result_data = json.load(json_file)
    except Exception as e:
        return {"error": f"Failed to read JSON: {e}"}, 500

    new_id = (result_data["objects"][-1]["id"] + 1) if result_data.get("objects") else 1
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

    save_json(result_data, build_json_temp_path(), img_name)
    return {"success": True, "num_objects": result_data["num_objects"] , "image_id": new_id , "image_path": path , "bbox": bbox , "tmpName": temp_object_name}, 200

@app.route('/upload', methods=['POST'])
def upload():
    image = request.files['image']
    if not image:
        return "No image uploaded", 400

    img_path = build_img_temp_path(image.filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(build_img_temp_path() , exist_ok=True)
    image.save(img_path)

    # Récupération des métadonnées via helper
    metadata = get_form_metadata(request)
    img_name = metadata.get("name", "unnamed")
    # Chargement image + YOLO
    img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    model_name = "yolo"
    model = ModelFactory.get_model(model_name)
    raw_results , img , img_result  = model.run(img_path)
    result_data = model.process_results(raw_results , img , img_result)

    # Traitement des résultats YOLO
    model = "YOLOv8"
    if result_data["num_objects"] == 0:
        print("No objects detected with YOLO, switching to SAM...")
        model = ModelFactory.get_model("sam")
        raw_results , img , img_result  = model.run(img_path)
        result_data = model.process_results(raw_results , img , img_result)
        model = "SAM"

    _ , annotated_rel_path = save_temp_img(img_result, "annotated")
    _ , original_rel_path = save_temp_img(img, "original")

    json_dir = build_json_temp_path()
    os.makedirs(json_dir, exist_ok=True)
    os.remove(img_path)

    JSON_data = {
        "image_name": img_name,
        "description": metadata.get("desc"),
        "date": metadata.get("date"),
        "location": metadata.get("location"),
        "latitude": metadata.get("latitude"),
        "longitude": metadata.get("longitude"),
        "source": metadata.get("source"),
        "num_objects": result_data["num_objects"],
        "objects": result_data.get("objects", [])
    }
    save_json(JSON_data, json_dir, img_name)
    class_name = get_all_classes()
    metadata_keys = get_all_metadata_keys()
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
@app.route('/re_run_analysis', methods=['POST'])
def re_run_analysis():
    img_name = request.form.get("img_name", "")
    img_annotated_path = request.form.get("img_annotated_path", "")
    img_original_path = request.form.get("img_original_path", "")
    img_original_path = build_img_temp_path(img_original_path)
    img_annotated_path = build_img_temp_path(img_annotated_path)
    if not os.path.exists(img_original_path):
        return {"error": "Image not found"}, 404
    sam_parameters = {}
    sam_parameters["points_per_side"] = int(request.form.get("points_per_side", 16))
    sam_parameters["pred_iou_thresh"] = float(request.form.get("pred_iou_thresh", 0.9))
    sam_parameters["stability_score_thresh"] = float(request.form.get("stability_score_thresh", 0.9))
    sam_parameters["min_mask_region_area"] = int(request.form.get("min_mask_region_area", 10000))
    print(f"Re-running analysis with SAM parameters: {sam_parameters}")
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
    result_data = model.process_results(results , img_original , img_result)
    read_json = build_json_temp_path(f"{img_name}.json")
    img_data = {}
    if os.path.exists(read_json):
        with open(read_json, 'r', encoding='utf-8') as json_file:
            old_data = json.load(json_file)
        for key in ["description", "date", "location", "latitude", "longitude", "source"]:
            if key in old_data:
                img_data[key] = old_data[key]
    model = "SAM"
    _ , annotated_rel_path = save_temp_img(img_result, "annotated")
    _ , original_rel_path = save_temp_img(img_cv, "original")
    clear_temp(json_name=img_name , img_original_path=img_original_path , img_annotated_path=img_annotated_path)

    json_dir = build_json_temp_path()
    os.makedirs(json_dir, exist_ok=True)
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

@app.route('/add_metadata_key', methods=['POST'])
def add_metadata_key():
    data = request.get_json() or {}
    key = data.get("key" , "")
    desc = data.get("description" , "")
    metric = data.get("metric" , "")
    type = data.get("type" , "text")
    required = data.get("metric_required" , False)
    enum_values = data.get("enum_values", "") if type == "enum" else None
    if not required:
        metric = None
    if not key:
        return {"success": False, "error": "Metadata key is required."}, 400
    if (check_if_metadata_key_exist(key=key)):
        return {"success":False , "error": "Metadata key already exists."}, 409
    regex = return_regex_by_name(type , enum_values=enum_values)
    req = create_new_metadata_key(key , desc , metric=metric , type=type , enum_values=enum_values , format_pattern=regex)
    if req:
        return {"success":True , "regex": regex} , 201
    return {"success":False , "error": "insertion failed."} , 500
@app.route('/add_class' , methods=['POST'])
def add_class():
    data = request.get_json() or {}
    name = data.get("name" , "")
    desc = data.get("description" , "")
    if not name:
        return {"success": False, "error": "Class name is required."}, 400
    if (check_if_class_exist(name=name)):
        return {"success":False , "error": "Class already exists."}, 409
    req = create_new_class(name , desc)
    if req:
        return {"success":True} , 201
    return {"success":False , "error": "insertion failed."} , 500
@app.route('/temp/img/<path:filename>')
def temp_img(filename):
    return send_from_directory(build_img_temp_path() , filename)
@app.route('/save_metadata', methods=['POST'])
def save_metadata():
    metadata = get_form_metadata(request)
    img_name = metadata.get("name", "unnamed")
    model = empty_to_none(request.form.get("model"))
    num_objects = int(request.form.get("num_objects", 0))
    max_objects_detected = int(request.form.get("max_object_detected", num_objects))

    image_id, version_number = handle_save_images(
        metadata,
        img_name,
        model,
        app.config["UPLOAD_FOLDER"],
        build_img_temp_path(request.form.get("annotated_image")),
        build_img_temp_path(request.form.get("original_image"))
    )
    objects_data = handle_detected_objects(request, img_name, image_id, version_number, max_objects_detected , app.config["UPLOAD_FOLDER"])

    json_data = build_json(metadata, img_name, num_objects, objects_data)
    #save_json(json_data, build_json_temp_path(), img_name)

    return redirect(url_for("gallery"))

@app.route('/gallery')
def gallery():
    try:
        images = get_all_images() 
    except Exception as e:
        print(f"Error fetching images: {e}")
        images = []

    return render_template('gallery.html', images=images)
@app.route('/view_image/<int:image_id>')
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

@app.route('/remove_object', methods=['POST'])
def remove_object():
    data = request.get_json()
    id = int(data.get('id'))
    img_name = data.get('img_name')
    img_original_path = build_img_temp_path(data.get('img_original_path'))
    img_annotated_path = build_img_temp_path(data.get('img_annotated_path'))
    json_file_path = build_json_temp_path(f"{img_name}.json")
    if not os.path.exists(json_file_path):
        return {"error": "JSON file not found"}, 404
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        result_data = json.load(json_file)
    # Supprimer l'objet correspondant
    objects = result_data.get("objects", [])
    obj_to_delete = next((obj for obj in objects if obj.get("id") == id), None)
    if obj_to_delete:
        objects.remove(obj_to_delete)
        crop_path = obj_to_delete.get("obj_crop_abs_path")
        if crop_path and os.path.exists(crop_path):
            os.remove(crop_path)
    else:
        return {"error": "Object not found in JSON"}, 404

    # Sauvegarde du JSON mis à jour
    save_json(result_data, build_json_temp_path(), img_name)
    # Réannotation de l'image
    image = cv2.imread(img_original_path)
    for i, obj in enumerate(objects):
        color = colors(int(obj.get("class_id", 0)), True)  # Couleur unique par class_id
        color_bgr = (int(color[2]), int(color[1]), int(color[0]))  
        if "contour" in obj and obj["contour"]:
            contour = np.array(obj["contour"]).reshape((-1, 1, 2)).astype(np.int32)
            cv2.drawContours(image, [contour], -1, color_bgr, 2)
        else:
            bbox = obj.get("bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = map(int, bbox)
            print(f"Drawing bbox for object {i}: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            cv2.rectangle(image, (x1, y1), (x2, y2), color_bgr, 2)
            cv2.putText(image, f"{obj['class_id']}:{obj['score']:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)

    # Remplacer l'ancienne image annotée
    print(f"Suppression de l'ancien fichier annoté: {img_annotated_path}")
    if os.path.exists(img_annotated_path):
        os.remove(img_annotated_path)

    cv2.imwrite(img_annotated_path, image)

    return {"success": True, "num_objects": len(objects)}, 200

@app.route('/clear_temp', methods=['POST'])
def clear_temp(json_name=None , img_original_path=None , img_annotated_path=None):
    data = request.get_json() if json_name is None else {}
    json_name = data.get("img_name", "") if not json_name else json_name
    json_dir = build_json_temp_path(f"{json_name}.json")
    img_original_path = data.get("img_original_path", "") if not img_original_path else img_original_path
    img_annotated_path = data.get("img_annotated_path", "") if not img_annotated_path else img_annotated_path
    if os.path.exists(json_dir):
        with open(json_dir, 'r', encoding='utf-8') as json_file:
            result_data = json.load(json_file)
        for obj in result_data.get("objects", []):
            crop_path = obj.get("obj_crop_abs_path")
            if crop_path and os.path.exists(crop_path):
                os.remove(crop_path)
        os.remove(img_original_path) if os.path.exists(img_original_path) else None
        os.remove(img_annotated_path) if os.path.exists(img_annotated_path) else None
        print(f"La suppression a été réalisée pour {json_dir}")
        os.remove(json_dir)
        return {"success": True}, 200
    else:
        return {"error": "JSON file not found"}, 404
if __name__ == '__main__':
    cleanup_temp_dir()
    app.run(debug=True) 