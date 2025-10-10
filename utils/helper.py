import os
import ast
import tempfile, os
import cv2
import shutil
import json
from utils.database import *
import regex

def build_json_temp_path(extension=None):
    """
    :extension: yourfile.json
    """
    if extension is None:
        return os.path.join("static", "temp", "json")
    return os.path.join("static", "temp", "json", extension)

def build_img_temp_path(extension=None):
    """
    :extension: yourfile.jpg
    """
    if extension is None:
        return os.path.join("static", "temp", "img")
    return os.path.join("static", "temp", "img", extension)

def save_temp_img(img_array, obj_index):
    temp_dir = build_img_temp_path()
    os.makedirs(temp_dir, exist_ok=True)
    fd, abs_path = tempfile.mkstemp(suffix=f"_obj{obj_index}.png", dir=temp_dir)
    os.close(fd)

    cv2.imwrite(abs_path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

    # On récupère juste le nom du fichier
    filename = os.path.basename(abs_path)
    return abs_path, filename

def empty_to_none(value):
    if value is None or value.strip() == "" or value.strip().lower() == "none":
        return None
    return value

def normalize_path(path):
    if path is None:
        return None
    if not os.path.isabs(path):
        return os.path.join(os.getcwd(), build_img_temp_path(path))
    return path

def save_image_permanently(temp_path, dest_dir, new_name):
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, new_name)
    if not os.path.exists(temp_path):
        raise FileNotFoundError(f"Temporary file {temp_path} does not exist.")
    if os.path.exists(dest_path):
        os.remove(dest_path)
    shutil.move(temp_path, dest_path)
    return dest_path

def save_json(data, json_dir, filename):
    os.makedirs(json_dir, exist_ok=True)
    with open(os.path.join(json_dir, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_bbox(bbox_str):
    if bbox_str:
        return [float(x) for x in ast.literal_eval(bbox_str)]
    return [None, None, None, None]


def get_form_metadata(request):
    return {
        "name": empty_to_none(request.form.get("img_name")),
        "desc": empty_to_none(request.form.get("img_desc")),
        "date": empty_to_none(request.form.get("img_date")),
        "location": empty_to_none(request.form.get("img_location")),
        "latitude": empty_to_none(request.form.get("img_latitude")),
        "longitude": empty_to_none(request.form.get("img_longitude")),
        "source": empty_to_none(request.form.get("img_source")),
    }

def handle_save_images(metadata , img_name , model , upload_folder , annotated_image_path , original_image_path):
    """
    :annotated_image_path: Temp path of annotated image, please have it in static folder
    :original_image_path: Temp path of original image please have it in static folder
    """
    img_path = save_image_permanently(
        original_image_path, upload_folder, f"{img_name}_original.jpg"
    )
    file_name_in_db = f"{img_name}_original.jpg"
    latitude = metadata.get("latitude")
    longitude = metadata.get("longitude")
    if latitude is not None:
        try:
            latitude = latitude.replace(',', '.')
            latitude = float(latitude)
        except ValueError:
            latitude = None
    if longitude is not None:
        try:
            longitude = longitude.replace(',', '.')
            longitude = float(longitude)
        except ValueError:
            longitude = None
    image_id = insert_image(
        file_name_in_db,
        img_name,
        metadata.get("desc"),
        metadata.get("date"),
        metadata.get("location"),
        latitude,
        longitude,
        metadata.get("source"),
        metadata.get("type")
    )
    img_annotated_path = save_image_permanently(
        annotated_image_path, upload_folder, f"{img_name}_annotated.jpg"
    )
    version_file_name_in_db = f"{img_name}_annotated.jpg"
    version_number = insert_annoted_image(image_id, version_file_name_in_db, model=model)
    return image_id , version_number 

def handle_metadata(request , obj_index , object_id , image_id):
    meta_index = 0
    metadata = {}
    while True:
        meta_key = request.form.get(f"objects[{obj_index}][metadata][{meta_index}][key]")
        meta_value = request.form.get(f"objects[{obj_index}][metadata][{meta_index}][value]")
        if meta_key is None or meta_value is None:
            break
        insert_metadata(object_id, image_id, meta_key, meta_value)
        metadata[meta_key] = meta_value
        meta_index += 1
    return metadata

def handle_detected_objects(request, img_name, image_id, version_number, max_objects , upload_folder):
    objects_data = {}

    for i in range(max_objects):
        class_id = request.form.get(f"objects[{i}][class_id]")
        if class_id is None:
            continue

        score = request.form.get(f"objects[{i}][score]")
        bbox = request.form.get(f"objects[{i}][bbox]")
        coords_x, coords_y, width, height = parse_bbox(bbox)
        score = float(score) if score is not None else None
        instance_value = request.form.get(f"objects[{i}][value]")

        # Sauvegarde du crop
        crop_path = normalize_path(request.form.get(f"objects[{i}][crop_path]"))
        object_path = save_image_permanently(crop_path, upload_folder, f"{img_name}_obj{i}.jpg")
        object_file_name = os.path.basename(object_path)

        # Insertion en base
        object_id = create_object(
            name=f"{img_name}_obj{i}",
            description=f"Detected object {i} in image {img_name}",
            type=class_id,
        )

        create_instance_object(
            object_id=object_id,
            version_number=version_number,
            image_id=image_id,
            coords_x=coords_x,
            coords_y=coords_y,
            width=width,
            height=height,
            confidence_score=score,
            cropped_file_path=object_file_name,
            instance_value=instance_value
        )

        # Métadonnées spécifiques à l'objet
        obj_metadata = handle_metadata(request, i, object_id, image_id)

        objects_data[f"object_{i}"] = {
            "class_id": class_id,
            "score": score,
            "bbox": {"x": coords_x, "y": coords_y, "width": width, "height": height},
            "cropped_file_path": object_file_name,
            "metadata": obj_metadata,
        }

    return objects_data

def build_json(metadata, img_name, num_objects, objects_data):
    return {
        "image_name": img_name,
        "description": metadata.get("desc"),
        "date": metadata.get("date"),
        "location": metadata.get("location"),
        "latitude": metadata.get("latitude"),
        "longitude": metadata.get("longitude"),
        "source": metadata.get("source"),
        "num_objects": num_objects,
        "objects": objects_data
    }

def cleanup_temp_dir():
    temp_dir_img = build_img_temp_path()
    temp_json_dir = build_json_temp_path()
    if os.path.exists(temp_dir_img):
        shutil.rmtree(temp_dir_img)
    if os.path.exists(temp_json_dir):
        shutil.rmtree(temp_json_dir)
    os.makedirs(temp_dir_img, exist_ok=True)
    os.makedirs(temp_json_dir, exist_ok=True)

def return_regex_by_name(name: str , enum_values: str = None) -> str:
    """
    $ : correspond jusqu'à la fin de la chaîne pour la condition.
    p{L} : toute lettre (alphabets de toutes les langues, y compris japonais).
    :enum_values: liste des valeurs séparées par des points-virgules (ex: val1;val2;val3)
    """
    if enum_values:
        enum_pattern = "|".join([v.strip() for v in enum_values.split(";") if v.strip()])
        return f'^(?:{enum_pattern})$'
    patterns = {
        "short": r'^[\p{L}\p{M}\'’\-\s]{1,40}$',  
        "text": r'^.{1,}$',                         
        "int": r'^-?\d+$',  
        "short_float": r'^-?\d+([.,]\d{1,2})?$',                           
        "float": r'^-?\d+([.,]\d+)?$',                    
        "coordinate": r'^-?\d{1,3}([.,]\d+)?$',        
        "bool": r'^(true|false)$',                      
        "date": r'^\d{4}-\d{2}-\d{2}$',                
        "date-hr-sec": r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$',
        "string": r'^.*$',                                          
    }
    return patterns.get(name, r'^.*$')
