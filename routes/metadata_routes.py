from flask import Blueprint, request, jsonify
import os

from utils.database import (
    check_if_metadata_key_exist,
    create_new_metadata_key,
    check_if_class_exist,
    create_new_class
)
from utils.helper import return_regex_by_name

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
    if not required:
        metric = None
    if not key:
        return {"success": False, "error": "Metadata key is required."}, 400
    if (check_if_metadata_key_exist(key=key)):
        return {"success":False , "error": "Metadata key already exists."}, 409
    regex = return_regex_by_name(type , enum_values=enum_values)
    req = create_new_metadata_key(key , desc , metric=metric , type=type , enum_values=enum_values , format_pattern=regex)
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
