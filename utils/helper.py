import os
import ast
import tempfile, os
import cv2
import shutil
import json
from utils.database import *
import regex
import numpy as np

def build_json_temp_path(extension=None):
    """
    Build and normalize the path for temporary JSON storage. 
    :extension: (optional) The filename (e.g., 'data.json'). 
    If not provided, returns the directory path.
    """
    if extension is None:
        return os.path.join("static", "temp", "json")
    return os.path.join("static", "temp", "json", extension)

def build_img_temp_path(extension=None):
    """
    Build and normalize the path used for temporary image storage.
    :extension: (optional) The filename (e.g., 'data.jpg').
    If not provided, returns the directory path.
    """
    if extension is None:
        return os.path.join("static", "temp", "img")
    return os.path.join("static", "temp", "img", extension)

def save_temp_img(img_array, obj_index: int):
    """
    Save a temporary image to use it in /upload
    :img_array: numpy array of the image in RGB format
    :obj_index: index of the object (for naming purposes)
    Returns the absolute path and filename of the saved image.
    """
    temp_dir = build_img_temp_path()
    os.makedirs(temp_dir, exist_ok=True)
    fd, abs_path = tempfile.mkstemp(suffix=f"_obj{obj_index}.png", dir=temp_dir)
    os.close(fd)

    cv2.imwrite(abs_path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

    # On récupère juste le nom du fichier
    filename = os.path.basename(abs_path)
    return abs_path, filename

def empty_to_none(value):
    """
    Aims to convert empty strings or "None" strings to actual None values.
    :value: input string
    Returns None if the input is empty or "None" (case insensitive), otherwise returns the original value.
    """
    if value is None or value.strip() == "" or value.strip().lower() == "none":
        return None
    return value

def normalize_path(path):
    """
    Normalize a file path by converting it to an absolute path.
    Simplify the maintenability of the code.
    Allow to switch between Flask and HTML contexts.
    :path: input file path (can be relative or absolute)
    """
    if path is None:
        return None
    if not os.path.isabs(path):
        return os.path.join(os.getcwd(), build_img_temp_path(path))
    return path

def save_image_permanently(temp_path, dest_dir, new_name):
    """
    move a temporary image to a permanent location if the user saves metadata.
    :temp_path: absolute path of the temporary image
    :dest_dir: directory where the image should be moved
    :new_name: new name for the image file (e.g., 'image1.jpg')
    Returns the absolute path of the moved image.
    """
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, new_name)
    if not os.path.exists(temp_path):
        raise FileNotFoundError(f"Temporary file {temp_path} does not exist.")
    if os.path.exists(dest_path):
        os.remove(dest_path)
    shutil.move(temp_path, dest_path)
    return dest_path

def save_json(data, json_dir, filename) -> None:
    """
    Save JSON data to a file.
    :data: dictionary to be saved as JSON
    :json_dir: directory where the JSON file should be saved
    :filename: name of the JSON file (without .json extension)
    """
    os.makedirs(json_dir, exist_ok=True)
    with open(os.path.join(json_dir, f"{filename}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_bbox(bbox_str):
    """
    Parse a bounding box string representation into a list of floats.
    :bbox_str: string representation of the bounding box (e.g., "[x1, y1, width, height]")
    Returns a list of four floats: [x1, y1, width, height]
    If bbox_str is None or empty, returns [None, None, None, None].
    """
    if bbox_str:
        return [float(x) for x in ast.literal_eval(bbox_str)]
    return [None, None, None, None]


def get_form_metadata(request):
    """
    Extract metadata from the form in the request.
    :request: Flask request object containing form data
    Returns a dictionary with metadata fields. 
    """
    return {
        "name": empty_to_none(request.form.get("img_name")),
        "desc": empty_to_none(request.form.get("img_desc")),
        "date": empty_to_none(request.form.get("img_date")),
        "location": empty_to_none(request.form.get("img_location")),
        "latitude": empty_to_none(request.form.get("img_latitude")),
        "longitude": empty_to_none(request.form.get("img_longitude")),
        "source": empty_to_none(request.form.get("img_source")),
        "type": empty_to_none(request.form.get("type"))
    }

def handle_save_images(metadata , img_name , model , upload_folder , annotated_image_path , original_image_path):
    """
    Handle saving original and annotated images permanently and inserting their records into the database.
    :metadata: dictionary containing image metadata
    :img_name: base name for the image files
    :model: model name used for annotation (can be None)
    :upload_folder: directory where images should be saved permanently
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
    """
    Handle metadata for a detected object from the form in the request.
    Return metadata for a specific object.
    Use the HTML inputs : objects[{obj_index}][metadata][{meta_index}][key] and objects[{obj_index}][metadata][{meta_index}][value]
    :request: Flask request object containing form data
    :obj_index: index of the object (to identify its metadata fields)
    :object_id: ID of the object in the database
    :image_id: ID of the image in the database
    """
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
    """
    Handle detected objects from the form in the request and insert them into the database.
    :request: Flask request object containing form data
    :img_name: base name for the image files
    :image_id: ID of the image in the database
    :version_number: version number of the annotated image
    :max_objects: maximum number of objects to process, allow to delete false detections.
    :upload_folder: directory where cropped object images should be saved permanently
    Returns a dictionary with data of all processed objects.
    """
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
    """
    Build a JSON structure containing image and detected objects metadata.
    :metadata: dictionary containing image metadata
    :img_name: base name for the image files
    :num_objects: number of detected objects
    :objects_data: dictionary containing data of detected objects
    Returns a dictionary representing the JSON structure.
    """
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
    """
    Clean up temporary directories for images and JSON files.
    This function removes all files in the temporary directories to free up space.
    """
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
    Return a regex pattern based on the provided name.
    :name: type of the regex pattern to return. Supported types are:
        - short: short text (1-40 characters, letters, spaces, hyphens, apostrophes)
        - text: any text (at least 1 character)
        - int: integer (positive or negative)
        - short_float: float with up to 2 decimal places (positive or negative)
        - float: float with any number of decimal places (positive or negative)
        - coordinate: coordinate format (degrees with optional decimal places)
        - bool: boolean value (true or false)
        - date: date in YYYY-MM-DD format
        - date-hr-sec: date and time in YYYY-MM-DD HH:MM:SS format
        - string: any string (including empty)
        - enum: enumeration of specific values (provided in enum_values)
    The regex patterns use Unicode properties for better international support:
    ^ : Beginning of the string.
    $ : End of the string.
    p{L} : Any letter (alphabets from all languages, including Japanese).
    :enum_values: List of values separated by semicolons (e.g., val1;val2;val3)
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

def clean_numpy(obj):
    if isinstance(obj, np.generic):  # ex: np.int64, np.float32
        return obj.item()
    elif isinstance(obj, list):
        return [clean_numpy(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}
    else:
        return obj
