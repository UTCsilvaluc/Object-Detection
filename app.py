from flask import Flask , render_template , request , redirect , url_for , send_from_directory
from ultralytics.utils.plotting import colors
from utils.models import *
from utils.process_detection import *
from utils.database import *
from utils.helper import *
import os
import json
import shutil
app = Flask(__name__)

UPLOAD_FOLDER = "static/img/Images" #Flask travaille automatiquement avec le dossier static
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # crée le dossier s'il n'existe pas
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
@app.route('/temp/img/<path:filename>')
def temp_img(filename):
    return send_from_directory(build_img_temp_path() , filename)
@app.route('/')
def index():
    return render_template('index.html')

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
    results, img, img_result, save_path = detect_yolo(img_path)

    # Traitement des résultats YOLO
    result_data = process_yolo_results(results, img, img_result)
    model = "YOLOv8"
    if result_data["num_objects"] == 0:
        print("No objects detected with YOLO, switching to SAM...")
        masks, _, img_result = segment_sam(img_path)
        result_data = process_SAM(masks, img, img_result)
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
    return render_template(
        "result.html",
        result=result_data,
        **metadata,  # injection directe des métadonnées dans le template
        model=model,
        annotated_image_path=annotated_rel_path,
        original_image_path=original_rel_path
    )

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
def clear_temp():
    data = request.get_json()
    json_name = data.get("img_name", "")
    json_dir = build_json_temp_path(f"{json_name}.json")
    img_original_path = build_img_temp_path(data.get('img_original_path'))
    img_annotated_path = build_img_temp_path(data.get('img_annotated_path'))
    if os.path.exists(json_dir):
        with open(json_dir, 'r', encoding='utf-8') as json_file:
            result_data = json.load(json_file)
        for obj in result_data.get("objects", []):
            crop_path = obj.get("obj_crop_abs_path")
            if crop_path and os.path.exists(crop_path):
                os.remove(crop_path)
        os.remove(img_original_path) if os.path.exists(img_original_path) else None
        os.remove(img_annotated_path) if os.path.exists(img_annotated_path) else None
        os.remove(json_dir)
        return {"success": True}, 200
    else:
        return {"error": "JSON file not found"}, 404
if __name__ == '__main__':
    cleanup_temp_dir()
    app.run(debug=True) 