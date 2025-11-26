from utils.database import get_db_connection , close_db_connection

IDENTITY_KEYS  = ["name", "full_name", "alias", "creator", "person_name", "identity" , "Name"]
PLACE_KEYS = ["place", "location", "location_name", "birth_place", "death_place", "event_place", "birth place", "death place", "place_name"]
DATE_KEYS  = ["date", "event_date", "date_of_birth", "creation_date", "capture_date"]

def build_thread_from_objectID(object_id: int):
    """
    Builds threads from a given object ID by extracting relevant metadata.
    Aims to create three primary tabs: (Objects , Images , Threads)
    Objects tab: all objects related to the same object. (Appear in same pictures OR sharing metadata)
    Images tab: all images where the object appears.
    Threads tab: three threads based on identity, place, and date.
    Returns a dictionary with threads categorized by identity, place, and date.
    """
    threads = {}
    threads_obj = get_threads_from_object(object_id)
    if threads_obj:
        threads["threads"] = threads_obj
    objects_same_picture = get_objects_same_picture(object_id)
    if objects_same_picture:
        threads["objects_same_picture"] = objects_same_picture
    images_from_object = get_images_from_object(object_id)
    if images_from_object:
        threads["images_from_object"] = images_from_object
    return threads

def get_threads_from_object(object_id: int):
    """
    Extracts initial thread seeds from a given object:
    - NAME thread: all metadata identifying the person/object
    - PLACE thread: metadata or image location information
    - DATE thread: all temporal metadata
    """

    conn = get_db_connection()
    if conn is None:
        return {}

    try:
        cur = conn.cursor()
        QUERY = """
        SELECT key, value   
        FROM Metadata 
        WHERE object_id = %s
        """
        cur.execute(QUERY, (object_id,))
        metadata_rows = cur.fetchall()

        threads = {
            "identity": [],
            "place": [],
            "date": []
        }
        for key, value in metadata_rows:

            key_l = key.lower()
            if key_l in IDENTITY_KEYS:
                if (value not in threads["identity"]):
                    threads["identity"].append(value)

            if key_l in PLACE_KEYS:
                if (value not in threads["place"]):
                    threads["place"].append(value)

            if key_l in DATE_KEYS or "date" in key_l:
                if (value not in threads["date"]):
                    threads["date"].append(value)
        return threads
    except Exception as e:
        print("Error while creating threads:", e)
        return {}
    finally:
        close_db_connection(conn)

def get_objects_same_picture(object_id: int):
    """
    Retrieves all objects (including instances) that appear in the same pictures as the given object ID.
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        QUERY = """
        WITH images_with_obj1 AS (
            SELECT DISTINCT image_id
            FROM ObjectInstance
            WHERE object_id = %s
        ),
        latest_instances AS (
            SELECT DISTINCT ON (OI.object_id, OI.image_id)
                OI.object_id,
                OI.image_id,
                OI.version_number,
                OI.cropped_file_path
            FROM ObjectInstance OI
            ORDER BY OI.object_id, OI.image_id, OI.version_number DESC
        )
        SELECT
            OBJ.object_id,
            OBJ.name,
            COALESCE(
                JSON_AGG(
                    JSON_BUILD_OBJECT(
                        'image_id', LI.image_id,
                        'version_number', LI.version_number,
                        'cropped_path', LI.cropped_file_path
                    ) ORDER BY LI.image_id
                ) FILTER (WHERE LI.image_id IS NOT NULL),
                '[]'
            ) AS instances,
            COALESCE(
                JSON_OBJECT_AGG(MD.key, MD.values)
                FILTER (WHERE MD.key IS NOT NULL),
                '{}'::json
            ) AS metadata
        FROM Object OBJ
        JOIN latest_instances LI ON LI.object_id = OBJ.object_id
        JOIN images_with_obj1 IW ON IW.image_id = LI.image_id
        LEFT JOIN LATERAL (
            SELECT md.key, JSON_AGG(DISTINCT md.value) AS values
            FROM Metadata md
            WHERE md.object_id = OBJ.object_id
            GROUP BY md.key
        ) MD ON TRUE
        WHERE OBJ.object_id <> %s
        GROUP BY OBJ.object_id, OBJ.name;
        """
        cur.execute(QUERY, (object_id, object_id))
        rows = cur.fetchall()
        objects = []
        for row in rows:
            objects.append({
                "object_id": row[0],
                "name": row[1],
                "instances": row[2],
                "metadata": row[3] 
            })
        cur.close()
        return objects
    except Exception as e:
        print("Error while retrieving objects from same picture:", e)
        return []
    finally:
        close_db_connection(conn)

def get_images_from_object(object_id: int):
    """
    Returns ALL images in which the object appears,
    with ALL metadata from ALL objects present in the image.
    """
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        QUERY = """
        WITH target_images AS (
            SELECT DISTINCT image_id
            FROM ObjectInstance
            WHERE object_id = %s
        ),
        latest_versions AS (
            SELECT DISTINCT ON (image_id)
                image_id,
                version_number
            FROM VersionedImage
            ORDER BY image_id, version_number DESC
        ),
        image_objects AS (
            SELECT 
                OI.image_id,
                OI.object_id,
                OI.version_number
            FROM ObjectInstance OI
            JOIN target_images TI ON TI.image_id = OI.image_id
        ),
        all_metadata AS (
            SELECT 
                io.image_id,
                io.object_id,
                md.key,
                md.value
            FROM image_objects io
            LEFT JOIN Metadata md 
                ON md.object_id = io.object_id
                AND md.image_id = io.image_id
                AND md.version_number = io.version_number
        )
        SELECT
            IMG.image_id,
            IMG.file_path,
            IMG.title,
            IMG.description,
            IMG.capture_date,
            IMG.event_date,
            IMG.location_name,
            IMG.latitude,
            IMG.longitude,
            IMG.upload_date,
            IMG.source_type,
            IMG.type,

            COALESCE(
                JSON_AGG(
                    JSON_BUILD_OBJECT(
                        'object_id', AM.object_id,
                        'key', AM.key,
                        'value', AM.value
                    )
                ) FILTER (WHERE AM.key IS NOT NULL),
                '[]'
            ) AS metadata
        FROM target_images TI
        JOIN Image IMG ON IMG.image_id = TI.image_id
        LEFT JOIN all_metadata AM ON AM.image_id = IMG.image_id
        GROUP BY IMG.image_id
        ORDER BY IMG.image_id DESC;
        """

        cur = conn.cursor()
        cur.execute(QUERY, (object_id,))
        rows = cur.fetchall()

        images = []
        for row in rows:
            images.append({
                "image_id": row[0],
                "file_path": row[1],
                "title": row[2],
                "description": row[3],
                "capture_date": row[4],
                "event_date": row[5],
                "location_name": row[6],
                "latitude": row[7],
                "longitude": row[8],
                "upload_date": row[9],
                "source_type": row[10],
                "type": row[11],
                "metadata": row[12] 
            })

        cur.close()
        return images

    except Exception as e:
        print(f"Error fetching images with full metadata: {e}")
        return []

    finally:
        close_db_connection(conn)
