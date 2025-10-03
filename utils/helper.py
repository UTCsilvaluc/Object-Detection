def empty_to_none(value):
    if value is None or value.strip() == "":
        return None
    return value

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
