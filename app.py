from flask import Flask , render_template , request , redirect , url_for
from utils.models import *
from utils.process_detection import *
from utils.database import *
from utils.helper import *
import os
import ast
import psycopg2
import shutil
app = Flask(__name__)

# Dossier local pour stocker les images
UPLOAD_FOLDER = "img/Images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    image = request.files['image']
    if not image:
        return "No image uploaded", 400

    # Sauvegarde temporaire
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(f"Saving image to: {img_path}")
    image.save(img_path)

    # Récupération des métadonnées du formulaire
    img_name = request.form.get("img_name")
    img_desc = request.form.get("img_desc")
    img_date = request.form.get("img_date")
    img_location = request.form.get("img_location")
    img_latitude = request.form.get("img_latitude")
    img_longitude = request.form.get("img_longitude")
    img_source = request.form.get("img_source")

    # Chargement image + YOLO
    img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results , img , img_result , save_path = detect_yolo(img_path)


    # Traitement des résultats YOLO
    result_data = process_yolo_results(results, img, img_result)
    model = "YOLOv8"
    if (result_data["num_objects"] == 0):
        print("No objects detected with YOLO, switching to SAM...")
        masks, _, img_result = segment_sam(img_path)
        result_data = process_SAM(masks, img, img_result)
        model = "SAM"
    print(f"Detected {result_data['num_objects']} objects using {model}")
    annotated_img_path = save_temp_img(img_result, "annotated")
    original_img_path = save_temp_img(img, "original")
    return render_template(
        "result.html",
        result=result_data,
        img_name=img_name,
        img_desc=img_desc,
        img_date=img_date,
        img_location=img_location,
        img_latitude=img_latitude,
        img_longitude=img_longitude,
        img_source=img_source,
        model=model,
        annotated_image_path=annotated_img_path,
        original_image_path=original_img_path
    )

def save_image_permanently(temp_path, dest_dir, new_name):
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, new_name)
    if not os.path.exists(temp_path):
        raise FileNotFoundError(f"Temporary file {temp_path} does not exist.")
    if os.path.exists(dest_path):
        os.remove(dest_path)
    shutil.move(temp_path, dest_path)
    return dest_path
@app.route('/save_metadata', methods=['POST'])
def save_metadata():
    img_name = empty_to_none(request.form.get("img_name"))
    img_desc = empty_to_none(request.form.get("img_desc"))
    img_date = empty_to_none(request.form.get("img_date"))
    img_location = empty_to_none(request.form.get("img_location"))
    img_latitude = empty_to_none(request.form.get("img_latitude"))
    img_longitude = empty_to_none(request.form.get("img_longitude"))
    img_source = empty_to_none(request.form.get("img_source"))
    annotated_image_path = empty_to_none(request.form.get("annotated_image")) #temp path of annotated image
    original_image_path = empty_to_none(request.form.get("original_image")) #temp path of original image
    num_objects = int(request.form.get("num_objects", 0))
    model = empty_to_none(request.form.get("model")) 

    if original_image_path.startswith("/static/"):
        original_image_path = os.path.join(os.getcwd(), original_image_path.lstrip("/"))
    if annotated_image_path.startswith("/static/"):
        annotated_image_path = os.path.join(os.getcwd(), annotated_image_path.lstrip("/"))

    img_path = save_image_permanently(original_image_path, app.config['UPLOAD_FOLDER'], f"{img_name}_original.jpg")
    image_id = insert_image(img_path, img_name, img_desc, img_date, img_location, img_latitude, img_longitude, img_source)
    img_annotated_path = save_image_permanently(annotated_image_path, app.config['UPLOAD_FOLDER'], f"{img_name}_annotated.jpg")
    version_number = insert_annoted_image(image_id, img_annotated_path, model=model)

    objects = []
    for i in range(num_objects):
        class_id = request.form.get(f"objects[{i}][class_id]")
        score = request.form.get(f"objects[{i}][score]")
        bbox = request.form.get(f"objects[{i}][bbox]")
        bbox = request.form.get(f"objects[{i}][bbox]")
        if bbox:
            bbox = ast.literal_eval(bbox)
            bbox = [float(x) for x in bbox]  
        else:
            bbox = [None, None, None, None]

        coords_x, coords_y, width, height = bbox
        score = float(score) if score is not None else None
        crop_path = request.form.get(f"objects[{i}][crop_path]")
        if crop_path.startswith("/static/"):
            crop_path = os.path.join(os.getcwd(), crop_path.lstrip("/"))
        
        object_path = save_image_permanently(crop_path, app.config['UPLOAD_FOLDER'], f"{img_name}_obj{i}.jpg")
        object_id = create_object(name=f"{img_name}_obj{i}", description=f"Detected object {i} in image {img_name}", type=class_id)
        create_instance_object(object_id=object_id, version_number=version_number, image_id=image_id, coords_x=coords_x, coords_y=coords_y, width=width, height=height, confidence_score=score, cropped_file_path=object_path)
        # Récupération des métadonnées dynamiques
        meta_index = 0
        while True:
            meta_key = request.form.get(f"objects[{i}][metadata][{meta_index}][key]")
            meta_value = request.form.get(f"objects[{i}][metadata][{meta_index}][value]")
            if meta_key is None or meta_value is None:
                break
            insert_metadata(object_id, image_id, meta_key, meta_value)
            meta_index += 1
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    app.run(debug=True) 