from flask import Blueprint, request, render_template , jsonify
from utils.database import (
    get_all_images,
    get_all_full_points,
    get_all_metadata_keys,
    get_all_full_objets_from_value, 
    search_objects_by_metadata
)

from utils.thread_research import get_threads_from_object , build_thread_from_objectID

thread_bp = Blueprint("thread", __name__)

@thread_bp.route('/thread')
def thread_view():
    images = get_all_images() 
    points = get_all_full_points()
    metadata_keys = get_all_metadata_keys()
    return render_template(
        'thread.html',
        images=images,
        points=points,
        metadata_keys=metadata_keys
    )

@thread_bp.route('/start_thread', methods=['POST'])
def start_thread():
    data = request.get_json()
    object_id = data.get("object_id")
    if not object_id:
        return {"error": "object_id is required"}, 400
    
    threads = build_thread_from_objectID(object_id)
    
    if not threads:
        return {"error": "No threads found or error occurred"}, 500

    return jsonify({"success": True, "status": True, "threads": threads}), 200

@thread_bp.route('/thread_search_values', methods=['POST'])
def thread_search_values():
    data = request.get_json()
    query = data.get("query", "")
    objects = get_all_full_objets_from_value(query)
    return jsonify({
        "status": True,
        "success": True,
        "objects": objects
    })

@thread_bp.route('/build_objects', methods=['POST'])
def build_objects():
    data = request.get_json()

    identity = data.get("identity")
    place = data.get("place")
    date = data.get("date")

    objects = search_objects_by_metadata(identity, place, date)
    
    return jsonify({
        "status": True,
        "success": True,
        "objects": objects
    })
