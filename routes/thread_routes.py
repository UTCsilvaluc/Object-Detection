from flask import Blueprint, request, render_template , jsonify
from utils.database import (
    get_all_images,
    get_all_full_points,
    get_all_metadata_keys,
    get_all_full_objects_from_value, 
    get_ThreadCategory
)

from utils.thread_research import (
    build_thread_from_objectID,
    build_thread_from_imageID,
    build_thread_from_metadata,
    get_map_results_for_object,
    get_map_results_for_image,
    get_map_results_for_thread
)

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


@thread_bp.route('/show_results', methods=['POST'])
def show_results():
    data = request.get_json() or {}
    mode = data.get("mode")

    if mode == "object":
        object_id = data.get("object_id")
        relation = data.get("relation", "cooccurrence")
        co_occurrence_images = data.get("co_occurrence_images", [])
        if not object_id:
            return jsonify({"success": False, "error": "object_id is required"}), 400
        results = get_map_results_for_object(object_id, relation, co_occurrence_images)
        images = results.get("images", []) if isinstance(results, dict) else results
        links = results.get("links", []) if isinstance(results, dict) else []
        focus_id = images[0]["image_id"] if images else None
        return jsonify({"success": True, "images": images, "links": links, "focus_image_id": focus_id, "relation": relation})

    if mode == "image":
        image_id = data.get("image_id")
        if not image_id:
            return jsonify({"success": False, "error": "image_id is required"}), 400
        images = get_map_results_for_image(image_id)
        return jsonify({"success": True, "images": images, "focus_image_id": image_id, "relation": "image"})

    if mode == "thread":
        selectors = data.get("threads", [])
        if not selectors:
            return jsonify({"success": False, "error": "threads metadata is required"}), 400
        results = get_map_results_for_thread(selectors)
        if isinstance(results, dict):
            images = results.get("images", [])
            links = results.get("links", [])
            focus_id = results.get("focus_image_id") or (images[0]["image_id"] if images else None)
        else:
            images = results or []
            links = []
            focus_id = images[0]["image_id"] if images else None
        return jsonify({"success": True, "images": images, "links": links, "focus_image_id": focus_id, "relation": "thread"})

    return jsonify({"success": False, "error": "Unknown mode"}), 400
