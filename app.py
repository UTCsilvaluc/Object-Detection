from flask import Flask , render_template , request , redirect , url_for
from utils.models import *
from utils.process_detection import process_yolo_results
import os
app = Flask(__name__)

# Dossier local pour stocker les images
UPLOAD_FOLDER = "img/Images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
def process_image(image_path):
    print(f"Processing with Yolo: {image_path}")
    detect_yolo(image_path)

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
    results = yolo_model(img_rgb)
    img_result = results[0].plot()

    # Traitement des résultats YOLO
    result_data = process_yolo_results(results, img, img_result)

    return render_template(
        "result.html",
        result=result_data,
        img_name=img_name,
        img_desc=img_desc,
        img_date=img_date,
        img_location=img_location,
        img_latitude=img_latitude,
        img_longitude=img_longitude,
        img_source=img_source
    )
    
if __name__ == '__main__':
    app.run(debug=True) 