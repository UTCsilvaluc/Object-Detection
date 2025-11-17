# utils/data_objects.py

from utils.database import (
    get_all_full_objects_instances,
    find_shared_objects_between_images
)

def build_object_links():
    """
    Return:
        grouped: dict {object_id: [ {lat, lon, image_id}, ... ]}
        object_datas: dict {object_id: {...instance data...}}
    """
    shared_objects = find_shared_objects_between_images()
    object_datas = get_all_full_objects_instances()

    return object_datas , shared_objects
