from flask import Blueprint, request, render_template , jsonify
from utils.database import (
    get_all_images,
    get_all_full_points,
    get_all_metadata_keys,
    get_all_full_objects_from_value, 
    get_ThreadCategory
)

from utils.thread_research import build_thread_from_objectID , build_thread_from_imageID , build_thread_from_metadata

thread_bp = Blueprint("thread", __name__)

@thread_bp.route('/thread')
def thread_view():
    images = get_all_images() 
    points = get_all_full_points()
    metadata_keys = get_all_metadata_keys()
    thread_categories = get_ThreadCategory()
    return render_template(
        'thread.html',
        images=images,
        points=points,
        metadata_keys=metadata_keys,
        thread_categories=thread_categories
    )
@thread_bp.route('/generate', methods=['POST'])
def generate_thread():
    data = request.get_json() or {}
    mode = data.get("mode")

    if not mode:
        return jsonify({"success": False, "error": "Missing 'mode'"}), 400

    if mode == "object":
        object_id = data.get("object_id")
        if not object_id:
            return jsonify({"success": False, "error": "object_id is required"}), 400

        threads = build_thread_from_objectID(object_id)

        return jsonify({
            "success": True,
            "threads": threads
        })

    elif mode == "image":
        image_id = data.get("image_id")
        if not image_id:
            return jsonify({"success": False, "error": "image_id is required"}), 400
        threads = build_thread_from_imageID(image_id)
        return jsonify({
            "success": True,
            "threads": threads
        })

    elif mode == "thread":
        selectorsValues = data.get("threads", [])
        if not selectorsValues:
            return jsonify({"success": False, "error": "threads metadata is required"}), 400
        threads = build_thread_from_metadata(selectorsValues)
        return jsonify({
            "success": True,
            "threads": threads
        })

    else:
        return jsonify({"success": False, "error": f"Unknown mode '{mode}'"}), 400

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
    objects = get_all_full_objects_from_value(query)
    return jsonify({
        "status": True,
        "success": True,
        "objects": objects
    })