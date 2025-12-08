from utils.database import get_db_connection , close_db_connection , get_objectsID_in_image

def get_existing_threads():
    conn = get_db_connection()
    if conn is None:
        return []
    try:   
        cur = conn.cursor()
        QUERY = """
        SELECT T.key , COALESCE(
            JSON_AGG(DISTINCT MD.key) FILTER (WHERE MD.key IS NOT NULL), '[]'::json
        )
        FROM ThreadCategory T
        LEFT JOIN MetadataDefinition MD ON MD.thread_category = T.key
        GROUP BY T.key
        ORDER BY T.key;
        """
        cur.execute(QUERY)
        rows = cur.fetchall()
        threads = {row[0]: row[1] for row in rows}
        cur.close()
        return threads
    except Exception as e:
        print("Error while retrieving existing threads:", e)
        return {}
    finally:
        close_db_connection(conn)

def build_thread_from_object_list(object_ids: list[int]):
    """
    Builds threads from a list of object IDs by extracting their respective threads.
    Aims to create three primary tabs: (Objects , Images , Threads)
    Objects tab: all objects related to the objects in the list. (Appear in same pictures OR sharing metadata)
    Images tab: all images where the objects appear.
    Threads tab: three threads based on identity, place, and date.
    Returns a dictionary with threads categorized by identity, place, and date.
    """
    thread_def = get_existing_threads()
    dynamic_threads = {category: [] for category in thread_def}
    result = {
        "threads": dynamic_threads,
        "objects_same_picture": [],
        "images_from_object": []
    }
    for obj_id in object_ids:
        t = build_thread_from_objectID(obj_id)
        if not t:
            continue
        result = merge_thread_result(result, t, thread_def)
    return result

def merge_thread_result(base: dict, new: dict, thread_def: dict):
    """
    Merge the result of build_thread_from_objectID into an accumulated structure.

    base structure expected:
    {
        "threads": { category: [values...] },
        "objects_same_picture": [...],
        "images_from_object": [...]
    }

    new is the output of build_thread_from_objectID_sql(object_id).

    thread_def is { category: [metadata keys] }
    """
    # --- Merge threads ---
    for category in thread_def.keys():
        if category not in base["threads"]:
            base["threads"][category] = []
        for value in new.get("threads", {}).get(category, []):
            if value not in base["threads"][category]:
                base["threads"][category].append(value)

    # --- Merge objects_same_picture ---
    seen_obj_ids = {obj["object_id"] for obj in base["objects_same_picture"]}
    for obj in new.get("objects_same_picture", []):
        oid = obj.get("object_id")
        if oid and oid not in seen_obj_ids:
            base["objects_same_picture"].append(obj)
            seen_obj_ids.add(oid)

    # --- Merge images_from_object ---
    seen_img_ids = {img["image_id"] for img in base["images_from_object"]}
    for img in new.get("images_from_object", []):
        iid = img.get("image_id")
        if iid and iid not in seen_img_ids:
            base["images_from_object"].append(img)
            seen_img_ids.add(iid)

    return base

def build_thread_from_objectID(object_id: int):
    """
    Version optimisée et corrigée : 1 seule requête SQL pour tout récupérer.
    """
    conn = get_db_connection()
    if conn is None:
        return {}
    
    try:
        cur = conn.cursor()
        
        QUERY = """
        WITH 
        -- Identify target images containing the object 
        target_images AS (
            SELECT DISTINCT image_id 
            FROM ObjectInstance 
            WHERE object_id = %s
        ),

        -- Thread data extraction : { "identity": [...], "place": [...], "date": [...] , ...}
        thread_data_source AS (
            SELECT 
                md_def.thread_category,
                json_agg(DISTINCT md.value) as values
            FROM Metadata md
            JOIN MetadataDefinition md_def ON md.key = md_def.key
            WHERE md.object_id = %s
            GROUP BY md_def.thread_category
        ),
        -- Aggregate thread data into a single JSON object : 
        thread_data AS (
            SELECT 
                json_object_agg(thread_category, values) as data
            FROM thread_data_source where thread_category IS NOT NULL
        ),

        -- Objects appearing in the same pictures as the target object
        related_objects_list AS (
            SELECT DISTINCT oi.object_id
            FROM ObjectInstance oi
            JOIN target_images ti ON ti.image_id = oi.image_id
            WHERE oi.object_id != %s
        ),
        
        -- Objects built with instances and metadata
        related_objects_built AS (
            SELECT 
                robj.object_id,
                obj_table.name,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'image_id', li.image_id, 
                            'version_number', li.version_number, 
                            'cropped_path', li.cropped_file_path
                        )
                    ) FILTER (WHERE li.image_id IS NOT NULL), 
                '[]'::json) AS instances,

                COALESCE(
                    json_object_agg(
                        md.key, md.values_arr
                    ) FILTER (WHERE md.key IS NOT NULL), 
                '{}'::json) AS metadata
                

            FROM related_objects_list robj
            JOIN Object obj_table ON obj_table.object_id = robj.object_id

            LEFT JOIN LATERAL (
                SELECT DISTINCT ON (oi_sub.image_id) 
                    oi_sub.image_id, oi_sub.version_number, oi_sub.cropped_file_path
                FROM ObjectInstance oi_sub
                WHERE oi_sub.object_id = robj.object_id 
                ORDER BY oi_sub.image_id, oi_sub.version_number DESC
            ) li ON TRUE 

            LEFT JOIN LATERAL (
                SELECT m.key, json_agg(DISTINCT m.value) AS values_arr
                FROM Metadata m
                WHERE m.object_id = robj.object_id 
                GROUP BY m.key
            ) md ON TRUE 
            GROUP BY robj.object_id, obj_table.name
        ),

        -- Image from the target object, with ALL metadata from ALL objects in the image
        images_built AS (
            SELECT 
                img.image_id,
                img.file_path,
                img.title,
                img.description,
                img.capture_date,
                img.event_date,
                img.location_name,
                img.latitude,
                img.longitude,
                img.upload_date,
                img.source_type,
                img.type,
                
                -- Metadata flatten (Format: [{ "object_id": 1, "key": "K", "value": "V" }])
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'object_id', md.object_id,
                                'key', md.key,
                                'value', md.value
                            )
                        )
                        FROM ObjectInstance oi
                        JOIN Metadata md 
                            ON md.object_id = oi.object_id 
                            AND md.image_id = oi.image_id 
                            AND md.version_number = oi.version_number
                        WHERE oi.image_id = img.image_id
                    ), '[]'::json
                ) as metadata

            FROM target_images ti
            JOIN Image img ON img.image_id = ti.image_id
            ORDER BY img.image_id DESC
        )
        SELECT json_build_object(
            'threads', COALESCE((SELECT data FROM thread_data), '{}'::json),
            'objects_same_picture', COALESCE((SELECT json_agg(row_to_json(rob)) FROM related_objects_built rob), '[]'::json),
            'images_from_object', COALESCE((SELECT json_agg(row_to_json(imb)) FROM images_built imb), '[]'::json)
        );
        """

        cur.execute(QUERY, (object_id, object_id, object_id))
        row = cur.fetchone()
        
        if row and row[0]:
            return row[0]
        else:
            return {
                "threads": {},
                "objects_same_picture": [],
                "images_from_object": []
            }

    except Exception as e:
        print(f"Error in optimized build_thread_from_objectID: {e}")
        return {
            "threads": {},
            "objects_same_picture": [],
            "images_from_object": []
        }
    finally:
        close_db_connection(conn)

def build_thread_from_imageID(image_id: int):
    """
    Builds threads from a given image ID by extracting each object in the image
    and compiling their respective threads.
    Aims to create three primary tabs: (Objects , Images , Threads)
    Objects tab: all objects related to the objects in the image. (Appear in same pictures OR sharing metadata)
    Images tab: all images where the objects appear.
    Threads tab: three threads based on identity, place, and date.
    Returns a dictionary with threads categorized by identity, place, and date.
    """
    object_ids = get_objectsID_in_image(image_id)
    return build_thread_from_object_list(object_ids)
        
def build_thread_from_metadata(selectersValue: list[dict]):
    """
    Builds threads based on provided metadata selecters.
    Each entry in selectersValue must be:
        { key: 'identity', value: 'Sakura', enabled: True }
    Returns a dictionary with threads categorized by identity, place, and date.
    """
    object_ids = get_objects_from_thread(selectersValue)
    return build_thread_from_object_list(object_ids)

def get_objects_from_thread(selectersValue: list[dict]):
    """
    Retrieves object IDs that match the provided thread metadata selectors.
    Special cases:
    - place: matches either object metadata or image.location_name (case-insensitive)
    - date: matches object metadata or image.event_date/capture_date (date-only comparison)
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        conditions = []
        params = []
        for thread in selectersValue:
            if not thread.get("enabled"):
                continue
            val = thread.get("value")
            category = thread.get("key")
            if not val or not category:
                continue
            if category == "place":
                # Match place via object metadata OR image location_name
                conditions.append("""
                (
                   (md.key IN (SELECT key FROM MetadataDefinition WHERE thread_category = %s)
                    AND md.value = %s)
                   OR
                   (im.location_name IS NOT NULL AND 
                        unaccent(LOWER(im.location_name)) LIKE unaccent(LOWER(%s)) 
                                  OR
                        unaccent(LOWER(%s)) LIKE unaccent(LOWER(im.location_name))
                        )
                )
                """)
                params.extend([category, val, val, val])
            elif category == "date":
                # Match date via object metadata OR image event/capture dates (date-only)
                conditions.append("""
                (
                   (md.key IN (SELECT key FROM MetadataDefinition WHERE thread_category = %s)
                    AND md.value::date = %s::date)
                   OR
                   (im.event_date IS NOT NULL AND im.event_date::date = %s::date)
                   OR
                   (im.capture_date IS NOT NULL AND im.capture_date::date = %s::date)
                )
                """)
                params.extend([category, val, val, val])

            else:
                conditions.append("""
                (
                   md.key IN (SELECT key FROM MetadataDefinition WHERE thread_category = %s)
                   AND md.value = %s
                )
                """)
                params.extend([category, val])

        if not conditions:
            return []

        where_clause = " OR ".join(conditions)

        QUERY = f"""
        SELECT DISTINCT oi.object_id
        FROM ObjectInstance oi
        JOIN Image im
          ON im.image_id = oi.image_id
        LEFT JOIN Metadata md
          ON md.object_id = oi.object_id
         AND md.version_number = oi.version_number
         AND md.image_id = oi.image_id
        WHERE {where_clause}
        """
        cur.execute(QUERY, tuple(params))
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print("Error while retrieving objects from thread metadata:", e)
        return []
    finally:
        close_db_connection(conn)
