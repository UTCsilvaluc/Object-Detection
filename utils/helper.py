import os
import ast
def empty_to_none(value):
    if value is None or value.strip() == "":
        return None
    return value

def normalize_path(path):
    if path and path.startswith("/static/"):
        return os.path.join(os.getcwd(), path.lstrip("/"))
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
