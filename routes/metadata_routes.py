# routes/metadata_routes.py

from flask import Blueprint, request

from utils.database import (
    check_if_metadata_key_exist,
    create_new_metadata_key,
    check_if_class_exist,
    create_new_class,
    find_similar_objects_by_metadatas,
    find_similar_objects_by_value
)
from utils.helper import return_regex_by_name , get_similar_objects_by_metadatas

metadata_bp = Blueprint("metadata", __name__)

@metadata_bp.route('/add_metadata_key', methods=['POST'])
def add_metadata_key():
    data = request.get_json() or {}
    key = data.get("key" , "")
    desc = data.get("description" , "")
    metric = data.get("metric" , "")
    type = data.get("type" , "text")
    required = data.get("metric_required" , False)
    enum_values = data.get("enum_values", "") if type == "enum" else None
    thread_required = data.get("thread_required", False)
    thread_category = data.get("thread_category", "")
    if not required:
        metric = None
    if not thread_required:
        thread_category = None
    if not key:
        return {"success": False, "error": "Metadata key is required."}, 400
    if (check_if_metadata_key_exist(key=key)):
        return {"success":False , "error": "Metadata key already exists."}, 409
    regex = return_regex_by_name(type , enum_values=enum_values)
    req = create_new_metadata_key(key , desc , metric=metric , type=type , enum_values=enum_values , format_pattern=regex, thread_category=thread_category)
    if req:
        return {"success":True , "regex": regex} , 201
    return {"success":False , "error": "insertion failed."} , 500

@metadata_bp.route('/add_class', methods=['POST'])
def add_class():
    data = request.get_json() or {}
    name = data.get("name" , "")
    desc = data.get("description" , "")
    if not name:
        return {"success": False, "error": "Class name is required."}, 400
    if (check_if_class_exist(name=name)):
        return {"success":False , "error": "Class already exists."}, 409
    req = create_new_class(name , desc)
    if req:
        return {"success":True} , 201
    return {"success":False , "error": "insertion failed."} , 500

@metadata_bp.route('/search_by_metadata', methods=['POST'])
def search_by_metadata():
    data = request.get_json() or {}
    metadata = data.get("metadata" , [])
    searchValue = data.get("searchValue" , "")
    if not metadata and not searchValue:
        return {"success": False, "error": "Metadata or search value is required."}, 400
    if metadata:
        similar_objects = find_similar_objects_by_metadatas(metadata)
    else:
        similar_objects = find_similar_objects_by_value(searchValue)
    similar_objects_datas = get_similar_objects_by_metadatas(similar_objects)
    if similar_objects_datas is None:
        return {"success": False, "error": "Error retrieving similar objects."}, 500   
    return {"success": True, "metadata_received": metadata, "similar_objects": similar_objects_datas}, 200
