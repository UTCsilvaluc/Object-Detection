import os
import ast
import tempfile, os
import cv2
def save_temp_img(img_array, obj_index):
    temp_dir = os.path.join("static", "img", "Images", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    fd, abs_path = tempfile.mkstemp(suffix=f"_obj{obj_index}.png", dir=temp_dir)
    os.close(fd)

    cv2.imwrite(abs_path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

    # Chemin relatif pour template
    rel_path = os.path.relpath(abs_path, "static")

    # Retourne les deux
    return abs_path, rel_path
def empty_to_none(value):
    if value is None or value.strip() == "" or value.strip().lower() == "none":
        return None
    return value

def normalize_path(path):
    if path is None:
        return None
    # Si ce n'est pas un chemin absolu, le considérer relatif à static
    if not os.path.isabs(path):
        return os.path.join(os.getcwd(), "static", path)
    return path


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
