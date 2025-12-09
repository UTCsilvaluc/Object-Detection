from utils.database import get_db_connection , close_db_connection , get_objectsID_in_image
from psycopg2.extras import RealDictCursor
import re

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
        "objects_same_metadata": [],
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
    incoming_threads = new.get("threads") or {}
    for category in thread_def.keys():
        if category not in base["threads"]:
            base["threads"][category] = []
        for value in incoming_threads.get(category, []) or []:
            if value not in base["threads"][category]:
                base["threads"][category].append(value)

    # --- Merge objects_same_picture ---
    seen_obj_ids = {obj["object_id"] for obj in base["objects_same_picture"]}
    for obj in new.get("objects_same_picture") or []:
        oid = obj.get("object_id")
        if oid and oid not in seen_obj_ids:
            base["objects_same_picture"].append(obj)
            seen_obj_ids.add(oid)

    # --- Merge objects_same_metadata ---
    seen_obj_md_ids = {obj["object_id"] for obj in base.get("objects_same_metadata", [])}
    for obj in new.get("objects_same_metadata") or []:
        oid = obj.get("object_id")
        if oid and oid not in seen_obj_md_ids:
            base.setdefault("objects_same_metadata", []).append(obj)
            seen_obj_md_ids.add(oid)

    # --- Merge images_from_object ---
    seen_img_ids = {img["image_id"] for img in base["images_from_object"]}
    for img in new.get("images_from_object") or []:
        iid = img.get("image_id")
        if iid and iid not in seen_img_ids:
            base["images_from_object"].append(img)
            seen_img_ids.add(iid)

    return base

def build_thread_from_objectID(object_id: int):
    """
    Builds threads from a given object ID by extracting related metadata and objects.
    Aims to create three primary tabs: (Objects , Images , Threads)
    Objects tab: all objects related to the target object (appear in same pictures).
    Images tab: all images where the target object appears.
    Threads tab: three threads based on identity, place, and date.
    Returns a dictionary with threads categorized by identity, place, and date.
    """
    conn = get_db_connection()
    if conn is None:
        return {}
    
    try:
        cur = conn.cursor()
        
        QUERY = """
        WITH 

            -- 1. Target images containing selected object
            target_images AS (
                SELECT DISTINCT image_id
                FROM ObjectInstance
                WHERE object_id = %s
            ),

            -- 2. Thread data
            thread_data_source AS (
                SELECT 
                    md_def.thread_category,
                    json_agg(DISTINCT md.value) AS values
                FROM Metadata md
                JOIN MetadataDefinition md_def ON md.key = md_def.key
                WHERE md.object_id = %s
                GROUP BY md_def.thread_category
            ),
            thread_data AS (
                SELECT COALESCE(json_object_agg(thread_category, values), '{}'::json) AS data
                FROM thread_data_source
                WHERE thread_category IS NOT NULL
            ),

            -- 3. Objects appearing on same images
            related_objects_list AS (
                SELECT DISTINCT oi.object_id
                FROM ObjectInstance oi
                JOIN target_images ti ON ti.image_id = oi.image_id
                WHERE oi.object_id != %s
            ),

            -- 4. IMAGE CO-OCCURRENCE: list images where both objects appear
            co_occurrence_images AS (
                SELECT 
                    oi2.object_id,
                    json_agg(DISTINCT oi1.image_id) AS images
                FROM ObjectInstance oi1
                JOIN ObjectInstance oi2 
                    ON oi1.image_id = oi2.image_id
                WHERE oi1.object_id = %s
                AND oi2.object_id != %s
                GROUP BY oi2.object_id
            ),

            -- 5. METADATA COMPARISON (raw) between target object and each other object
            related_metadata_raw AS (
                SELECT 
                    md2.object_id AS related_id,
                    md1.key AS key,
                    md1.value AS value1,
                    md2.value AS value2,
                    md1.image_id AS image1,
                    md2.image_id AS image2
                FROM Metadata md1
                JOIN Metadata md2 ON md1.key = md2.key
                WHERE md1.object_id = %s
                AND md2.object_id != %s
                AND (
                        -- Check if target value is inside related value (e.g. Paris in Paris, France)
                        unaccent(LOWER(md2.value::text)) LIKE ('%%' || unaccent(LOWER(md1.value::text)) || '%%')
                        OR
                        -- Check if related value is inside target value (e.g. Saku in Sakura)
                        unaccent(LOWER(md1.value::text)) LIKE ('%%' || unaccent(LOWER(md2.value::text)) || '%%')
                  )
                AND md2.version_number = (
                        SELECT MAX(md3.version_number)
                        FROM Metadata md3
                        WHERE md3.object_id = md2.object_id
                        AND md3.image_id = md2.image_id
                )
            ),

            -- 6. Aggregate metadata similarities per related object
            related_metadata_objects AS (
                SELECT 
                    related_id AS object_id,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'key', key,
                                'value1', value1,
                                'value2', value2,
                                'image1', image1,
                                'image2', image2
                            )
                        ), '[]'::json
                    ) AS shared_metadata
                FROM related_metadata_raw
                GROUP BY related_id
            ),

            -- 7. Build object blocks for objects related by metadata
            related_objects_from_metadata AS (
                SELECT 
                    rmo.object_id,
                    obj.name,

                    -- Instances (latest version per image)
                    
                    COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'image_id', oi.image_id,
                                'version_number', oi.version_number,
                                'cropped_path', oi.cropped_file_path
                            )
                        )
                        FROM (
                            SELECT DISTINCT ON (oi_sub.image_id)
                                oi_sub.image_id,
                                oi_sub.version_number,
                                oi_sub.cropped_file_path
                            FROM ObjectInstance oi_sub
                            WHERE oi_sub.object_id = rmo.object_id
                            ORDER BY oi_sub.image_id, oi_sub.version_number DESC
                        ) oi
                    ), '[]'::json) AS instances,

                    -- Metadata full
                    COALESCE(
                    (
                        SELECT json_object_agg(md.key, md.values_arr)
                        FROM (
                            SELECT m.key, json_agg(DISTINCT m.value) AS values_arr
                            FROM Metadata m
                            WHERE m.object_id = rmo.object_id
                            GROUP BY m.key
                        ) md
                    ), '[]'::json) AS metadata,

                    -- Shared metadata with target
                    COALESCE(rmo2.shared_metadata, '[]'::json) AS shared_metadata

                FROM related_metadata_objects rmo
                JOIN Object obj ON obj.object_id = rmo.object_id
                LEFT JOIN related_metadata_objects rmo2 ON rmo2.object_id = rmo.object_id
            ),

            -- 8. Build object blocks for co-occurrence objects
            related_objects_built AS (
                SELECT 
                    robj.object_id,
                    obj_table.name,
                    -- Instances (latest version per image)
                    COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'image_id', oi.image_id,
                                'version_number', oi.version_number,
                                'cropped_path', oi.cropped_file_path
                            )
                        )
                        FROM (
                            SELECT DISTINCT ON (oi_sub.image_id)
                                oi_sub.image_id,
                                oi_sub.version_number,
                                oi_sub.cropped_file_path
                            FROM ObjectInstance oi_sub
                            WHERE oi_sub.object_id = robj.object_id
                            ORDER BY oi_sub.image_id, oi_sub.version_number DESC
                        ) oi
                    ), '[]'::json) AS instances,

                    -- Metadata full
                    COALESCE (
                    (
                        SELECT json_object_agg(md.key, md.values_arr)
                        FROM (
                            SELECT m.key, json_agg(DISTINCT m.value) AS values_arr
                            FROM Metadata m
                            WHERE m.object_id = robj.object_id
                            GROUP BY m.key
                        ) md
                    ), '[]'::json) AS metadata,

                    -- NEW: images of co-occurrence
                    COALESCE(coi.images, '[]'::json) AS co_occurrence_images

                FROM related_objects_list robj
                JOIN Object obj_table ON obj_table.object_id = robj.object_id
                LEFT JOIN co_occurrence_images coi ON coi.object_id = robj.object_id
            ),

            -- 9. Build images tab
            images_built AS (
                SELECT 
                    img.*,
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
                    ), '[]'::json) AS metadata
                FROM target_images ti
                JOIN Image img ON img.image_id = ti.image_id
            )

            -- FINAL
            SELECT json_build_object(
                'threads', (SELECT data FROM thread_data),
                'objects_same_picture', (SELECT json_agg(row_to_json(rob)) FROM related_objects_built rob),
                'objects_same_metadata', (SELECT json_agg(row_to_json(rom)) FROM related_objects_from_metadata rom),
                'images_from_object', (SELECT json_agg(row_to_json(imb)) FROM images_built imb)
            );

        """
        cur.execute(QUERY, (object_id, object_id, object_id, object_id, object_id, object_id, object_id))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        else:
            return {
                "threads": {},
                "objects_same_picture": [],
                "objects_same_metadata": [],
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
    result = build_thread_from_object_list(object_ids)

    # In thread mode, keep only objects that themselves match the selectors (avoid co-occurrence noise)
    allowed_ids = set(object_ids)
    result["objects_same_picture"] = [
        obj for obj in result.get("objects_same_picture", [])
        if obj.get("object_id") in allowed_ids
    ]
    result["objects_same_metadata"] = [
        obj for obj in result.get("objects_same_metadata", [])
        if obj.get("object_id") in allowed_ids
    ]
    return result

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
                tokens = re.split(r"[,\s]+", val)
                tokens = [t.strip() for t in tokens if t.strip()]

                if not tokens:
                    continue

                md_subconds = []
                im_subconds = []

                for _ in tokens:
                    md_subconds.append(
                        "unaccent(LOWER(md.value::text)) LIKE ('%%' || unaccent(LOWER(%s)) || '%%')"
                    )
                    im_subconds.append(
                        "unaccent(LOWER(im.location_name::text)) LIKE ('%%' || unaccent(LOWER(%s)) || '%%')"
                    )

                md_cond = " AND ".join(md_subconds)
                im_cond = " AND ".join(im_subconds)

                conditions.append(f"""
                (
                    (
                        md.key IN (
                            SELECT key FROM MetadataDefinition
                            WHERE thread_category = %s
                        )
                        AND ({md_cond})
                    )
                    OR
                    (
                        im.location_name IS NOT NULL
                        AND ({im_cond})
                    )
                )
                """)

                params.append(category)
                for token in tokens:
                    params.extend([token, token])
            elif category == "date":
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


# ---------- MAP RESULTS HELPERS ----------

def _fetch_images_by_ids(conn, image_ids):
    if not image_ids:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT 
                image_id, file_path, title, description, capture_date, event_date,
                location_name, latitude, longitude, type
            FROM Image
            WHERE image_id = ANY(%s)
            """,
            (list(set(image_ids)),)
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        print("Error fetching images by ids:", e)
        return []

def _fetch_images_for_objects(conn, object_ids):
    if not object_ids:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT DISTINCT 
                im.image_id, im.file_path, im.title, im.description,
                im.capture_date, im.event_date, im.location_name,
                im.latitude, im.longitude, im.type
            FROM ObjectInstance oi
            JOIN Image im ON im.image_id = oi.image_id
            WHERE oi.object_id = ANY(%s)
            """,
            (list(set(object_ids)),)
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        print("Error fetching images for objects:", e)
        return []


def get_map_results_for_object(object_id: int, relation: str = "cooccurrence" , co_occurrence_images: list[int] = []):
    """
    Returns map-ready images for a given object depending on the relation type.
    - cooccurrence: images where the object appears with at least one other object.
    - metadata: images for objects sharing metadata with the given object (substring matching included).
    """
    conn = get_db_connection()
    if conn is None:
        return {"images": [], "links": []}
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if relation == "metadata":
            # Images where the target object appears
            cur.execute(
                "SELECT DISTINCT image_id FROM ObjectInstance WHERE object_id = %s",
                (object_id,)
            )
            target_image_ids = [row["image_id"] for row in cur.fetchall()]
            
            # Related images with metadata matches 
            # NOTE: ('%%') are used for psycopg2 , to differentiate from variables.
            cur.execute(
                """
                SELECT 
                    m2.image_id AS related_image_id, tm.image_id AS target_image_id,
                    json_agg(DISTINCT jsonb_build_object('key', m2.key, 'target_value', tm.value, 'related_value', m2.value)) AS metadata
                FROM Metadata m2
                JOIN Metadata tm
                  ON tm.key = m2.key
                 AND tm.object_id = %s
                WHERE m2.object_id <> %s
                  AND (
                        -- Check if target value is inside related value (e.g. Paris in Paris, France)
                        unaccent(LOWER(m2.value::text)) LIKE ('%%' || unaccent(LOWER(tm.value::text)) || '%%')
                        OR
                        -- Check if related value is inside target value (e.g. Saku in Sakura)
                        unaccent(LOWER(tm.value::text)) LIKE ('%%' || unaccent(LOWER(m2.value::text)) || '%%')
                  )
                GROUP BY m2.image_id, tm.image_id;
                """,
                (object_id, object_id)
            )
            
            related_rows = cur.fetchall()
            related_image_ids = [row["related_image_id"] for row in related_rows]
            
            # 4. Build links target_image -> related_image with metadata reasons
            links = []
            for row in related_rows:
                links.append({
                    "from_image_id": row["target_image_id"],
                    "to_image_id": row["related_image_id"],
                    "metadata": row["metadata"]
                })
            
            image_ids = target_image_ids + related_image_ids
            images = _fetch_images_by_ids(conn, image_ids)
            cur.close()
            return {"images": images, "links": links}
            
        # Default: cooccurrence images
        co_occurrence_images = [int(img_id) for img_id in co_occurrence_images]
        images = _fetch_images_by_ids(conn, co_occurrence_images)
        return {"images": images, "links": []}
    except Exception as e:
        print("Error in get_map_results_for_object:", e)
        return {"images": [], "links": []}
    finally:
        close_db_connection(conn)      
def get_map_results_for_image(image_id: int):
    """
    Returns images for all objects that appear in the given image.
    This pulls every image where those objects appear (including the source image).
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        object_ids = get_objectsID_in_image(image_id)
        return _fetch_images_for_objects(conn, object_ids)
    finally:
        close_db_connection(conn)


def get_map_results_for_thread(selectersValue: list[dict]):
    """
    Returns all images corresponding to objects that match the provided thread selectors.
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        object_ids = get_objects_from_thread(selectersValue)
        images = _fetch_images_for_objects(conn, object_ids)

        # No matches, early return
        if not images:
            return {"images": [], "links": [], "focus_image_id": None}

        # Build a map of image_id -> list of matched selectors to later create links
        matches_by_image = {}

        def add_match(image_id, key, value, source):
            if value is None:
                return
            matches_by_image.setdefault(image_id, []).append({
                "key": key,
                "value": value,
                "source": source
            })

        enabled_selectors = [
            sel for sel in selectersValue
            if sel.get("enabled") and sel.get("value") and sel.get("key")
        ]

        if not enabled_selectors:
            return {"images": images, "links": [], "focus_image_id": images[0].get("image_id")}

        def _place_tokens(value: str):
            tokens = re.split(r"[,\s]+", value)
            return [t.strip() for t in tokens if t.strip()]

        cur = conn.cursor(cursor_factory=RealDictCursor)

        for sel in enabled_selectors:
            category = sel.get("key")
            val = sel.get("value")

            if category == "place":
                tokens = _place_tokens(str(val))
                if not tokens:
                    continue

                md_cond = " AND ".join(
                    ["unaccent(LOWER(md.value::text)) LIKE ('%%' || unaccent(LOWER(%s)) || '%%')" for _ in tokens]
                )
                im_cond = " AND ".join(
                    ["unaccent(LOWER(im.location_name::text)) LIKE ('%%' || unaccent(LOWER(%s)) || '%%')" for _ in tokens]
                )

                query = f"""
                SELECT DISTINCT 
                    im.image_id,
                    CASE 
                        WHEN im.location_name IS NOT NULL AND ({im_cond}) THEN im.location_name::text 
                        ELSE NULL
                    END AS location_match,
                    CASE 
                        WHEN def.thread_category = %s AND ({md_cond}) THEN md.value::text 
                        ELSE NULL
                    END AS metadata_match
                FROM ObjectInstance oi
                JOIN Image im ON im.image_id = oi.image_id
                LEFT JOIN Metadata md 
                  ON md.object_id = oi.object_id
                 AND md.image_id = oi.image_id
                 AND md.version_number = oi.version_number
                LEFT JOIN MetadataDefinition def ON def.key = md.key
                WHERE oi.object_id = ANY(%s)
                  AND (
                        (im.location_name IS NOT NULL AND ({im_cond}))
                     OR (def.thread_category = %s AND ({md_cond}))
                  );
                """
                params = []
                params.extend(tokens)                 # im_cond (select)
                params.append(category)               # def.thread_category (select)
                params.extend(tokens)                 # md_cond (select)
                params.append(list(set(object_ids)))  # ANY(%s)
                params.extend(tokens)                 # im_cond (where)
                params.append(category)               # def.thread_category (where)
                params.extend(tokens)                 # md_cond (where)

                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                for row in rows:
                    add_match(row["image_id"], category, row.get("location_match"), "location")
                    add_match(row["image_id"], category, row.get("metadata_match"), "metadata")

            elif category == "date":
                query = """
                SELECT DISTINCT 
                    im.image_id,
                    md.value::text AS metadata_match,
                    im.event_date::text AS event_match,
                    im.capture_date::text AS capture_match
                FROM ObjectInstance oi
                JOIN Image im ON im.image_id = oi.image_id
                LEFT JOIN Metadata md 
                  ON md.object_id = oi.object_id
                 AND md.image_id = oi.image_id
                 AND md.version_number = oi.version_number
                LEFT JOIN MetadataDefinition def ON def.key = md.key
                WHERE oi.object_id = ANY(%s)
                  AND (
                        (def.thread_category = %s AND md.value::date = %s::date)
                     OR (im.event_date IS NOT NULL AND im.event_date::date = %s::date)
                     OR (im.capture_date IS NOT NULL AND im.capture_date::date = %s::date)
                  );
                """
                params = (list(set(object_ids)), category, val, val, val)
                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    add_match(row["image_id"], category, row.get("metadata_match"), "metadata")
                    add_match(row["image_id"], category, row.get("event_match"), "event_date")
                    add_match(row["image_id"], category, row.get("capture_match"), "capture_date")

            else:
                query = """
                SELECT DISTINCT 
                    im.image_id,
                    md.value::text AS metadata_match
                FROM ObjectInstance oi
                JOIN Image im ON im.image_id = oi.image_id
                JOIN Metadata md 
                  ON md.object_id = oi.object_id
                 AND md.image_id = oi.image_id
                 AND md.version_number = oi.version_number
                JOIN MetadataDefinition def ON def.key = md.key
                WHERE oi.object_id = ANY(%s)
                  AND def.thread_category = %s
                  AND md.value = %s;
                """
                params = (list(set(object_ids)), category, val)
                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    add_match(row["image_id"], category, row.get("metadata_match"), "metadata")

        cur.close()

        focus_id = images[0].get("image_id")
        focus_matches = matches_by_image.get(focus_id, [])
        if not focus_matches:
            # If the first image does not carry the matches, pick the first image that does.
            for img_id, match_list in matches_by_image.items():
                if match_list:
                    focus_id = img_id
                    focus_matches = match_list
                    break

        links = []
        for img in images:
            img_id = img.get("image_id")
            if img_id is None or img_id == focus_id:
                continue
            other_matches = matches_by_image.get(img_id, [])
            if not other_matches or not focus_matches:
                continue

            shared_metadata = []
            seen_keys = set()
            for fm in focus_matches:
                for om in other_matches:
                    if fm["key"] != om["key"] or fm["key"] in seen_keys:
                        continue
                    shared_metadata.append({
                        "key": fm["key"],
                        "target_value": fm["value"],
                        "related_value": om["value"]
                    })
                    seen_keys.add(fm["key"])
            if shared_metadata:
                links.append({
                    "from_image_id": focus_id,
                    "to_image_id": img_id,
                    "metadata": shared_metadata
                })

        return {"images": images, "links": links, "focus_image_id": focus_id}
    finally:
        close_db_connection(conn)
