import json
import os
import uuid
from datetime import datetime, timezone

from utils.helper import safe_filename, build_json_temp_path
from utils.paths import TEMP_ROOT

QUEUE_DIR = os.path.join(TEMP_ROOT, "queue")
QUEUE_UPLOADS_DIR = os.path.join(QUEUE_DIR, "uploads")
QUEUE_FILE = os.path.join(QUEUE_DIR, "queue.json")


def _ensure_queue_dirs() -> None:
    os.makedirs(QUEUE_DIR, exist_ok=True)
    os.makedirs(QUEUE_UPLOADS_DIR, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_queue() -> dict:
    _ensure_queue_dirs()
    if not os.path.exists(QUEUE_FILE):
        return {"items": []}
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"items": []}
    if isinstance(data, list):
        return {"items": data}
    if not isinstance(data, dict) or "items" not in data:
        return {"items": []}
    return data


def _save_queue(queue: dict) -> None:
    _ensure_queue_dirs()
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def add_queue_files(files) -> list:
    queue = _load_queue()
    added = []
    for file in files or []:
        if not file or not getattr(file, "filename", None):
            continue
        original_name = file.filename
        base, ext = os.path.splitext(original_name)
        safe_base = safe_filename(base) or "image"
        ext = (ext or ".jpg").lower()
        item_id = uuid.uuid4().hex
        dest_name = f"{safe_base}_{item_id}{ext}"
        dest_path = os.path.join(QUEUE_UPLOADS_DIR, dest_name)
        file.save(dest_path)
        now = _now_iso()
        item = {
            "id": item_id,
            "filename": original_name,
            "status": "pending",
            "upload_path": dest_path,
            "created_at": now,
            "updated_at": now,
        }
        queue["items"].append(item)
        added.append(item)
    _save_queue(queue)
    return added


def list_queue_items() -> list:
    queue = _load_queue()
    return queue.get("items", [])


def serialize_queue_items() -> list:
    items = []
    for item in list_queue_items():
        items.append({
            "id": item.get("id"),
            "filename": item.get("filename"),
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "num_objects": item.get("num_objects"),
            "model": item.get("model"),
            "error": item.get("error"),
        })
    return items


def get_queue_item(item_id: str) -> dict | None:
    if not item_id:
        return None
    for item in list_queue_items():
        if item.get("id") == item_id:
            return item
    return None


def update_queue_item(item_id: str, **updates) -> dict | None:
    if not item_id:
        return None
    queue = _load_queue()
    updated = None
    for item in queue.get("items", []):
        if item.get("id") != item_id:
            continue
        item.update({k: v for k, v in updates.items() if v is not None})
        item["updated_at"] = _now_iso()
        updated = item
        break
    if updated is not None:
        _save_queue(queue)
    return updated


def claim_next_pending() -> dict | None:
    queue = _load_queue()
    for item in queue.get("items", []):
        if item.get("status") == "pending":
            item["status"] = "processing"
            item["updated_at"] = _now_iso()
            _save_queue(queue)
            return item
    return None


def mark_reserved(item_id: str, assigned_name: str | None = None, analysis_name: str | None = None) -> dict | None:
    return update_queue_item(
        item_id,
        status="reserved",
        assigned_name=assigned_name,
        analysis_name=analysis_name
    )


def consume_queue_item(item_id: str) -> dict | None:
    return update_queue_item(item_id, status="consumed")


def list_available_preanalysis() -> list:
    queue = _load_queue()
    available = []
    changed = False
    for item in queue.get("items", []):
        if item.get("status") != "done":
            continue
        analysis_name = item.get("analysis_name")
        if not analysis_name:
            continue
        json_path = build_json_temp_path(f"{analysis_name}.json")
        if not os.path.exists(json_path):
            item["status"] = "missing"
            item["updated_at"] = _now_iso()
            changed = True
            continue
        preview = (
            item.get("annotated_display_path")
            or item.get("annotated_image_path")
            or item.get("original_display_path")
            or item.get("original_image_path")
        )
        if preview and os.path.isabs(preview):
            preview = os.path.basename(preview)
        label = item.get("filename") or analysis_name
        available.append({
            "id": item.get("id"),
            "label": label,
            "analysis_name": analysis_name,
            "created_at": item.get("created_at"),
            "num_objects": item.get("num_objects"),
            "model": item.get("model"),
            "preview_path": preview,
        })
    if changed:
        _save_queue(queue)
    return available
