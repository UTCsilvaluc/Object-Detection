# utils/helper.py

# Imports

import os
import grp
import ast
import tempfile
import cv2
import shutil
import json
import html
import re
import unicodedata
from utils.database import *
from ultralytics.utils.plotting import colors
import io
from PIL import Image , ImageOps
import regex
import numpy as np
from models.object_embedding import generate_embedding_from_crop
from utils.database import get_instance_object_by_object_id
from utils.paths import ROOT_DIR , MEDIA_ROOT , MEDIA_IMAGES_DIR , MEDIA_THUMBS_DIR , MEDIA_CROPS_DIR , TEMP_IMG_DIR , TEMP_JSON_DIR  , TEMP_ROOT , TEMP_THUMBS_DIR , MEDIA_URL

# Thumbnail configurations
THUMB_MAX_SIZE = (320, 320)
THUMB_QUALITY = 70
DISPLAY_WEBP_QUALITY = 95

def ensure_directories():
    """
    Ensure that all necessary media and temporary directories exist.
    """
    os.makedirs(MEDIA_IMAGES_DIR, exist_ok=True)
    os.makedirs(MEDIA_THUMBS_DIR, exist_ok=True)
    os.makedirs(MEDIA_CROPS_DIR, exist_ok=True)
    os.makedirs(TEMP_IMG_DIR, exist_ok=True)
    os.makedirs(TEMP_JSON_DIR, exist_ok=True)
    os.makedirs(TEMP_THUMBS_DIR, exist_ok=True)

def media_url(rel_path: str) -> str:
    """
    Build the full media URL for a given relative path.
    :rel_path: relative path under the media directory
    Returns the full URL to access the media file.
    """
    rel_path = rel_path.lstrip(os.sep)
    return f"{MEDIA_URL}/{rel_path.replace(os.sep, '/')}"

def make_public_media_file(path: str, group: str = "www-data") -> None:
    """
    Ensure generated media files are readable by nginx (www-data).
    """
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(MEDIA_ROOT + os.sep) and not abs_path.startswith(TEMP_ROOT + os.sep):
        return
    try:
        gid = grp.getgrnam(group).gr_gid
        os.chown(abs_path, -1, gid)
    except (KeyError, PermissionError):
        pass
    try:
        os.chmod(abs_path, 0o644)  
    except PermissionError:
        pass

def _sanitize_filename(name: str) -> str:
    """Normalize filenames coming from the frontend (HTML entities, extra spaces)."""
    if not name:
        return name
    return html.unescape(name).strip()

def safe_filename(name: str, fallback: str = "image", max_length: int = 80) -> str:
    """
    Produce a filesystem-safe ASCII filename stem.
    Keeps letters, numbers, dot, dash, underscore. Collapses spaces/invalid chars to underscores.
    """
    raw = _sanitize_filename(name) or ""
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace(" ", "_")
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("._-")
    if not normalized:
        normalized = fallback
    return normalized[:max_length]

def build_json_temp_path(extension=None):
    """
    Build and normalize the path for temporary JSON storage. 
    :extension: (optional) The filename (e.g., 'data.json'). 
    If not provided, returns the directory path.
    """
    ensure_directories()
    return TEMP_JSON_DIR if extension is None else os.path.join(TEMP_JSON_DIR, extension)

def build_img_temp_path(extension=None):
    """
    Build and normalize the path used for temporary image storage.
    :extension: (optional) The filename (e.g., 'data.jpg').
    If not provided, returns the directory path.
    """
    ensure_directories()
    return TEMP_IMG_DIR if extension is None else os.path.join(TEMP_IMG_DIR, extension)

def build_image_path(file_name: str) -> str:
    """
    Build the absolute path for an image stored in static/img/Images.
    """
    if not file_name:
        return None
    if os.path.isabs(file_name):
        return file_name
    ensure_directories()
    return os.path.join(MEDIA_IMAGES_DIR, file_name)

def build_image_thumb_absolute(file_name: str, ext: str = "webp") -> str:
    ensure_directories()
    base = os.path.splitext(os.path.basename(file_name))[0]
    return os.path.join(MEDIA_THUMBS_DIR, f"{base}.{ext}")

def build_image_thumb_relative(file_name: str, ext: str = "webp") -> str:
    base = os.path.splitext(os.path.basename(file_name))[0]
    return f"thumbs/{base}.{ext}"


def build_image_thumb_absolute_temp(file_name: str, ext: str = "webp") -> str:
    ensure_directories()
    base = os.path.splitext(os.path.basename(file_name))[0]
    return os.path.join(TEMP_THUMBS_DIR, f"{base}.{ext}")

def build_image_thumb_relative_temp(file_name: str, ext: str = "webp") -> str:
    base = os.path.splitext(os.path.basename(file_name))[0]
    return f"temp/thumbs/{base}.{ext}"

def build_temp_webp_path(file_name: str) -> tuple[str, str]:
    ensure_directories()
    base = os.path.splitext(os.path.basename(file_name))[0]
    rel = f"{base}.webp"
    abs_path = os.path.join(TEMP_IMG_DIR, rel)
    return abs_path, rel


def ensure_image_thumbnail(source_path: str, thumb_path: str) -> bool:
    """
    Generate a thumbnail if it does not exist.
    Returns True if the thumbnail exists or was created successfully.
    """
    if not source_path or not os.path.exists(source_path):
        return False
    if os.path.exists(thumb_path):
        return True
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    try:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail(THUMB_MAX_SIZE, Image.LANCZOS)
            img.save(thumb_path, "WEBP", quality=THUMB_QUALITY, method=6, optimize=True)
        make_public_media_file(thumb_path)
        return True
    except Exception:
        return False

def ensure_display_webp(source_path: str, webp_path: str, quality: int = DISPLAY_WEBP_QUALITY) -> bool:
    """
    Generate (or refresh) a WebP display file from a source image.
    """
    if not source_path or not os.path.exists(source_path):
        return False
    if os.path.exists(webp_path):
        try:
            if os.path.getmtime(webp_path) >= os.path.getmtime(source_path):
                return True
        except OSError:
            pass
    os.makedirs(os.path.dirname(webp_path), exist_ok=True)
    try:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.save(webp_path, "WEBP", quality=quality, method=6)
        make_public_media_file(webp_path)
        return True
    except Exception:
        return False

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
        return os.path.join(ROOT_DIR, build_img_temp_path(path))
    return path

def save_image_permanently(temp_path: str, dest_dir: str, new_name: str):
    ensure_directories()
    temp_path = normalize_path(temp_path)  

    if dest_dir == "images":
        final_dir = MEDIA_IMAGES_DIR
    elif dest_dir == "crops":
        final_dir = MEDIA_CROPS_DIR
    else:
        final_dir = dest_dir if os.path.isabs(dest_dir) else os.path.join(MEDIA_ROOT, dest_dir)
    os.makedirs(final_dir, exist_ok=True)
    dest_path = os.path.join(final_dir, new_name)

    if not os.path.exists(temp_path):
        raise FileNotFoundError(f"Temporary file {temp_path} does not exist.")
    if os.path.exists(dest_path):
        raise FileExistsError(f"Destination file {dest_path} already exists.")

    shutil.move(temp_path, dest_path)
    make_public_media_file(dest_path)
    return dest_path


def load_analysis_json(img_name, required=True):
    img_name = _sanitize_filename(img_name)
    json_path = build_json_temp_path(f"{img_name}.json")
    data = load_json(json_path)
    if required and data is None:
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    return data, json_path

def load_json(json_path):
    """
    Load JSON data from a file.
    :json_path: path to the JSON file
    Returns the loaded JSON data as a dictionary.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file {json_path} does not exist.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

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
    longitude = empty_to_none(request.form.get("img_longitude"))
    latitude = empty_to_none(request.form.get("img_latitude"))
    token = empty_to_none(request.form.get("csrf_token"))
    if longitude is not None:
        longitude = longitude.replace(',', '.')
    if latitude is not None:
        latitude = latitude.replace(',', '.')
    return {
        "name": empty_to_none(request.form.get("img_name")),
        "desc": empty_to_none(request.form.get("img_desc")),
        "event_date": empty_to_none(request.form.get("img_event_date")),
        "event_date_time_toggle": empty_to_none(request.form.get("event_date_time_toggle")),
        "picture_date": empty_to_none(request.form.get("img_picture_date")),
        "picture_date_time_toggle": empty_to_none(request.form.get("picture_date_time_toggle")),
        "location": empty_to_none(request.form.get("img_location")),
        "latitude": latitude,
        "longitude": longitude,
        "source": empty_to_none(request.form.get("img_source")),
        "type": empty_to_none(request.form.get("type")),
        "csrf_token": token
    }

def handle_save_images(metadata , img_name , model , upload_folder , annotated_image_path , original_image_path , json_data = None):
    """
    Handle saving original and annotated images permanently and inserting their records into the database.
    :metadata: dictionary containing image metadata
    :img_name: base name for the image files
    :model: model name used for annotation (can be None)
    :upload_folder: directory where images should be saved permanently
    :annotated_image_path: Temp path of annotated image, please have it in static folder
    :original_image_path: Temp path of original image please have it in static folder
    """
    safe_name = safe_filename(img_name)
    img_path = save_image_permanently(
        original_image_path, "images", f"{safe_name}_original.jpg"
    )
    file_name_in_db = f"{safe_name}_original.jpg"
    thumb_path = build_image_thumb_absolute(file_name_in_db)
    ensure_image_thumbnail(img_path, thumb_path)
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
        metadata.get("event_date"),
        metadata.get("picture_date"),
        metadata.get("location"),
        latitude,
        longitude,
        metadata.get("source"),
        metadata.get("type")
    )
    img_annotated_path = save_image_permanently(
        annotated_image_path, "images", f"{safe_name}_annotated.jpg"
    )
    version_file_name_in_db = f"{safe_name}_annotated.jpg"
    version_number = insert_annoted_image(image_id, version_file_name_in_db, model=model)
    return image_id , version_number , file_name_in_db

def handle_metadata(request , obj_index , object_id , version_number , image_id):
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
        insert_metadata(object_id, version_number , image_id, meta_key, meta_value)
        metadata[meta_key] = meta_value
        meta_index += 1
    return metadata

def handle_detected_objects(request, img_name, image_id, version_number, max_objects , upload_folder , json_data = None):
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
    safe_name = safe_filename(img_name)
    objects = json_data.get("objects", []) if json_data else []
    for i in range(max_objects):
        class_id = request.form.get(f"objects[{i}][class_id]")
        if class_id is None:
            continue
        similar_object = request.form.get(f"objects[{i}][default_object]")
        if not similar_object or similar_object == "":
            similar_object = None
        score = request.form.get(f"objects[{i}][score]")
        bbox = request.form.get(f"objects[{i}][bbox]")
        coords_x, coords_y, width, height = parse_bbox(bbox)
        score = float(score) if score is not None else None
        current_object_json = next((obj for obj in objects if obj.get("id") == i), {})
        embedding = current_object_json.get("embedding", None)
        instance_value = empty_to_none(request.form.get(f"objects[{i}][value]"))

        crop_path = normalize_path(request.form.get(f"objects[{i}][crop_path]"))
        object_path = save_image_permanently(crop_path, "crops", f"{safe_name}_obj{i}.jpg")
        object_file_name = os.path.basename(object_path)

        if similar_object:
            object_id = int(similar_object)
        else:
            object_id = create_object(
                name=f"{img_name}_obj{i}",
                description=f"Detected object {i} in image {img_name}",
                type=class_id,
                embedding=embedding
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
        obj_metadata = handle_metadata(request, i, object_id, version_number, image_id)

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
    temp_thumb_dir = TEMP_THUMBS_DIR
    if os.path.exists(temp_dir_img):
        shutil.rmtree(temp_dir_img)
    if os.path.exists(temp_json_dir):
        shutil.rmtree(temp_json_dir)
    if os.path.exists(temp_thumb_dir):
        shutil.rmtree(temp_thumb_dir)
    os.makedirs(temp_dir_img, exist_ok=True)
    os.makedirs(temp_json_dir, exist_ok=True)
    os.makedirs(temp_thumb_dir, exist_ok=True)

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

def control_coordinate_format(value: str) -> bool:
    """
    Validate if the provided value matches the coordinate format.
    :value: string representation of the coordinate
    Returns True if the value matches the coordinate regex pattern, otherwise False.
    """
    reg = regex.compile(r"^-?\d{1,3}(?:[.,]\d+)?$")
    return bool(reg.match(value))

def clean_numpy(obj):
    if isinstance(obj, np.generic):  # ex: np.int64, np.float32
        return obj.item()
    elif isinstance(obj, list):
        return [clean_numpy(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}
    else:
        return obj

def get_next_id_available(objects):
    for i in range(len(objects) + 1):
        if all(obj.get("id", 0) != i for obj in objects):
            return i
    return max(obj.get("id", 0) for obj in objects) + 1

def draw_annotations(image, objects):
    for obj in objects:
        color = colors(int(obj.get("class_id", 0)), True)
        color_bgr = (int(color[2]), int(color[1]), int(color[0]))  
        if "contour" in obj and obj["contour"]:
            contour = np.array(obj["contour"]).reshape((-1, 1, 2)).astype(np.int32)
            cv2.drawContours(image, [contour], -1, color_bgr, 2)
        elif "contours" in obj and obj["contours"]:
            for cnt in obj["contours"]:
                contour = np.array(cnt).reshape((-1, 1, 2)).astype(np.int32)
                cv2.drawContours(image, [contour], -1, color_bgr, 2)
        else:
            x1, y1, x2, y2 = map(int, obj.get("bbox", [0, 0, 0, 0]))
            cv2.rectangle(image, (x1, y1), (x2, y2), color_bgr, 2)
            cv2.putText(image, f"{obj['class_id']}:{obj['score']:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
    return image

def fileStorage_to_image(file_storage):
    """
    Convert a Flask FileStorage object to an OpenCV image.
    Handle image orientation based on EXIF data in case of images taken from mobile devices.
    :param file_storage: Flask FileStorage object
    :return: OpenCV image (numpy array) or None if conversion fails
    """
    img_bytes = file_storage.read()
    img_bytes = io.BytesIO(img_bytes)
    try:
        img = Image.open(img_bytes)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            pass
        img = img.convert("RGB")
    except Exception as e:
        return None
    img_array = np.array(img)
    #PIL -> OpenCV
    img = cv2.cvtColor(img_array , cv2.COLOR_RGB2BGR)
    return img

def get_similar_objects(objects, top_k=5):
    for idx, obj in enumerate(objects):
        objects[idx]['similar_objects'] = get_all_full_instances_from_embedding(obj["embedding"] , limit=top_k)
    return objects

def get_similar_objects_by_metadatas(similar_objects: list):
    """
    :param metadata_list: List of metadata dictionaries. Format : [{"key": str , "value": str}, ...]
    :return: List of similar objects matching the provided metadata.
    Each object contains its details along with the matching metadata.
    """
    results = []

    for sim_obj in similar_objects:
        instance = get_instance_object_by_object_id(sim_obj['object_id'])
        data_sim_obj = {
            "object_id": sim_obj['object_id'],
            "class": None,
            "cropped_file_path": None,
            "metadata": []
        }

        # --- Cas 1 : get_instance return a dict ---
        if isinstance(instance, dict):
            data_sim_obj["class"] = instance.get("class")
            data_sim_obj["cropped_file_path"] = instance.get("cropped_file_path")
            if "metadata" in instance:
                data_sim_obj["metadata"] = instance["metadata"]

        # --- Cas 2 : get_instance return a list of items ---
        elif isinstance(instance, list):
            for item in instance:
                if "class" in item:
                    data_sim_obj["class"] = item["class"]
                if "cropped_file_path" in item:
                    data_sim_obj["cropped_file_path"] = item["cropped_file_path"]
                if "metadata_key" in item and "metadata_value" in item and item["metadata_key"] and item["metadata_value"]:
                    data_sim_obj["metadata"].append({ "key": item["metadata_key"], "value": item["metadata_value"] , "obj_image_id": item.get("image_id" , None) , "obj_version_number": item.get("version_number" , None)})

        if data_sim_obj["class"] and data_sim_obj["cropped_file_path"]:
            results.append(data_sim_obj)

    return results

def create_new_object(obj_img, bbox, contour, new_id, score=1.0):
    # Save crop
    abs_path, crop_name = save_temp_img(obj_img, new_id)

    # Embedding
    crop_full_path = abs_path  # necessary for embedding function
    embedding = generate_embedding_from_crop(crop_full_path).tolist()

    # JSON must store ONLY the filename, not full path
    new_obj = {
        "class_id": 0,
        "id": new_id,
        "score": score,
        "bbox": bbox,
        "contour": contour,
        "obj_crop_path": crop_name,  
        "embedding": embedding,
    }

    similar = get_similar_objects([new_obj], top_k=5)
    new_obj["similar_objects"] = similar[0]["similar_objects"]
    return new_obj

def load_analysis_context(img_name, original_path, annotated_path, require_json=True):
    img_name = _sanitize_filename(img_name)
    original_path = _sanitize_filename(original_path)
    annotated_path = _sanitize_filename(annotated_path)

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

def add_new_detected_object(result_data, obj_img, bbox, contour, score):
    new_id = int(get_next_id_available(result_data["objects"]))

    new_object = create_new_object(
        obj_img=obj_img,
        bbox=bbox,
        contour=contour,
        new_id=new_id,
        score=score
    )

    similar = get_similar_objects([new_object])
    new_object["similar_objects"] = similar[0]["similar_objects"]

    result_data["objects"].append(new_object)
    result_data["num_objects"] = len(result_data["objects"])

    return new_object, new_id
