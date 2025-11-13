import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def get_db_connection():
    """
    Establish and return a new database connection using environment variables.
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    
def close_db_connection(conn):
    """
    Close the database connection.
    :param conn: psycopg2 connection object
    :return: None
    """
    try:
        if conn:
            conn.close()
    except Exception as e:
        print(f"Error closing database connection: {e}")    

def insert_image(file_path, title, description=None, capture_date=None, location_name=None, latitude:float=None, longitude:float=None, source_type=None, type=None):
    """
    Insert a new image record into the Image table.
    :param file_path: str , only the name of the file, not the full path , it is managed by the system.
    :param title: str
    :param description: str
    :param capture_date: date
    :param location_name: str
    :param latitude: float
    :param longitude: float
    :param source_type: str
    :param type: str
    :return: image_id (int) or False on failure
    """
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO Image (file_path, title, description, capture_date, location_name, latitude, longitude, source_type, type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING image_id;
        """
        cur.execute(insert_query, (file_path, title, description, capture_date, location_name, latitude, longitude, source_type, type))
        image_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return image_id
    except Exception as e:
        print(f"Error inserting image: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_annoted_image(image_id, file_path, model=None):
    """
    version_number is handled by a trigger in the database with auto increment.
    Insert a new versioned image record into the VersionedImage table.
    :param image_id: int
    :param file_path: str , only the name of the file, not the full path , it is managed by the system.
    :param model: str
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO VersionedImage (image_id, file_path, model)
        VALUES (%s, %s, %s)
        RETURNING version_number;
        """
        cur.execute(insert_query, (image_id, file_path, model))
        version_number = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return version_number
    except Exception as e:
        print(f"Error inserting annoted image: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_metadata(object_id: int , version_number: int , image_id: int , key: str , value: str):
    """
    Insert a new metadata record into the Metadata table.
    (object_id , version_number , image_id) are foreign keys referencing ObjectInstance table.
    :param object_id: int
    :param version_number: int
    :param image_id: int
    :param key: str , must exist in MetadataDefinition table
    :param value: str
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO Metadata (object_id, version_number, image_id, key, value)
        VALUES (%s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (object_id, version_number, image_id, key, value))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting metadata: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_point(name: str , description: str = None , location_name: str = None , latitude: float = None , longitude: float = None , icon_key: str = None , color_hex: str = "#000000"):
    """
    Insert a new point record into the Point table.
    :param name: str
    :param description: str
    :param location_name: str
    :param latitude: float
    :param longitude: float
    :param icon_key: str , must exist in Icon table
    :param color_hex: str , hex color code
    :return: point_id (int) or False on failure
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO Point (name, description, location_name, latitude, longitude, icon_key, color_hex)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING point_id;
        """
        cur.execute(insert_query, (name, description, location_name, latitude, longitude, icon_key, color_hex))
        point_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return point_id
    except Exception as e:
        print(f"Error inserting point: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_metadata_point(point_id: int , key: str , value: str):
    """
    Insert a new metadata record into the MetaDataPoint table.
    :param point_id: int
    :param key: str , must exist in MetadataDefinition table
    :param value: str
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO MetaDataPoint (point_id, key, value)
        VALUES (%s, %s, %s)
        """
        cur.execute(insert_query, (point_id, key, value))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting metadata for point: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_link_type(key: str , label: str):
    """
    Insert a new link type record into the LinkType table.
    :param key: str
    :param label: str
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO LinkType (key, label)
        VALUES (%s, %s);
        """
        cur.execute(insert_query, (key, label))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting link type: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_link(title: str , description: str , link_type: str):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        query = """
        INSERT INTO Link (title, description, link_type)
        VALUES (%s, %s, %s)
        RETURNING link_id;
        """
        cur.execute(query, (title, description, link_type))
        link_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return link_id
    except Exception as e:
        print(f"Error inserting link: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_link_endpoint(link_id: int , entity_type: str , image_id: int = None , point_id: int = None , role: str = None , order_index: int = None):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO LinkEndPoint (link_id, entity_type, image_id, point_id, role, order_index)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cur.execute(insert_query, (link_id, entity_type, image_id, point_id, role, order_index))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting link endpoint: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_link_metadata(link_id: int , key: str , value: str):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO LinkMetadata (link_id, key, value)
        VALUES (%s, %s, %s);
        """
        cur.execute(insert_query, (link_id, key, value))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting link metadata: {e}")
        return False
    finally:
        close_db_connection(conn)

def insert_link_geometry(link_id: int , geojson: str , source: str = None):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO LinkGeometry (link_id, geojson, source)
        VALUES (%s, %s, %s);
        """
        cur.execute(insert_query, (link_id, geojson, source))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting link geometry: {e}")
        return False
    finally:
        close_db_connection(conn)

def create_object(name: str , description: str = None , type: str = None , embedding: list = None):
    """
    Create a new object record in the Object table.
    :param name: str
    :param description: str
    :param type: str
    :param embedding: list of floats (optional) (currently not available)
    :return: object_id (int) or False on failure
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO Object (name, description, type, embedding)
        VALUES (%s, %s, %s, %s) RETURNING object_id;
        """
        cur.execute(insert_query, (name, description, type, embedding))
        object_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return object_id
    except Exception as e:
        print(f"Error inserting object: {e}")
        return False
    finally:
        close_db_connection(conn)

def create_instance_object(object_id: int , version_number: int , image_id: int , coords_x: float = None , coords_y: float = None , width: float = None , height: float = None , confidence_score: float = None , cropped_file_path: str = None, instance_value: str = None):
    """
    Create a new object instance record in the ObjectInstance table.
    :param object_id: int
    :param version_number: int
    :param image_id: int
    :param coords_x: float
    :param coords_y: float
    :param width: float
    :param height: float
    :param confidence_score: float
    :param cropped_file_path: str (only the name of the file, not the full path)
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO ObjectInstance (object_id, version_number, image_id, coords_x, coords_y, width, height, confidence_score, cropped_file_path , class)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s , %s);
        """
        cur.execute(insert_query, (object_id, version_number, image_id, coords_x, coords_y, width, height, confidence_score, cropped_file_path, instance_value))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting object instance: {e}")
        return False
    finally:
        close_db_connection(conn)

def create_new_class(name, desc):
    """
    Create a new class record in the Class table.
    :param name: str
    :param desc: str
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        query = "INSERT INTO Class VALUES(%s , %s);"
        cur.execute(query , (name , desc))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error creating a new class : {e}")
        return False
    finally:
        close_db_connection(conn)

def create_new_metadata_key(key, desc, metric=None, type=None, enum_values=None , format_pattern=None):
    """
    Create a new metadata key record in the MetadataDefinition table.
    :param key: str
    :param desc: str
    :param metric: str (optional) if the metadata is metric_required
    :param type: str
    :param enum_values: str (comma-separated values for enum type)
    :param format_pattern: str (regex pattern for validation)
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO MetadataDefinition (key, description, type, format_pattern, enum_values, metric)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cur.execute(insert_query, (key, desc, type, format_pattern, enum_values, metric))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error creating a new metadata key: {e}")
        return False
    finally:
        close_db_connection(conn)

def update_class_instance_object(object_id: int, version_number: int, image_id: int, new_class: str):
    """
    Update the class of an object instance in the ObjectInstance table.
    As Primary Key is (object_id, version_number, image_id)
    :param object_id: int
    :param version_number: int
    :param image_id: int
    :param new_class: str
    :return: bool
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        query = "UPDATE ObjectInstance SET class = %s WHERE object_id = %s AND version_number = %s AND image_id = %s;"
        cur.execute(query, (new_class, object_id, version_number, image_id))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error updating class in ObjectInstance: {e}")
        return False
    finally:
        close_db_connection(conn)

def check_if_class_exist(name):
    """
    Check if a class with the given name exists in the Class table.
    :param name: str
    :return: bool ; True if exists, False otherwise
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM Class WHERE name = %s;", (name,))
        exists = cur.fetchone() is not None
        return exists
    except Exception as e:
        print(f"Error checking class existence: {e}")
        return False
    finally:
        close_db_connection(conn)

def check_if_title_exist(title):
    """
    Check if an image title with the given title exists in the Image table.
    :param title: str
    :return: bool ; True if exists, False otherwise
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM Image WHERE title = %s;", (title,))
        exists = cur.fetchone() is not None
        return exists
    except Exception as e:
        print(f"Error checking title existence: {e}")
        return False
    finally:
        close_db_connection(conn)

def check_if_metadata_key_exist(key):
    """
    Check if a metadata key with the given key exists in the MetadataDefinition table.
    :param key: str
    :return: bool ; True if exists, False otherwise
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM MetadataDefinition WHERE key = %s;", (key,))
        exists = cur.fetchone() is not None
        return exists
    except Exception as e:
        print(f"Error checking metadata key existence: {e}")
        return False
    finally:
        close_db_connection(conn)

def get_image_by_id(image_id):
    """
    Get an image by its ID.
    :param image_id: int ; must be a valid image_id in the Image table
    :return: dict or None
    """
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        select_query = """
        SELECT * FROM Image WHERE image_id = %s;
        """
        cur.execute(select_query, (image_id,))
        row = cur.fetchone()
        if row:
            image_data = {
                "image_id": row[0],
                "file_path": row[1],
                "title": row[2],
                "description": row[3],
                "capture_date": row[4],
                "location_name": row[5],
                "latitude": row[6],
                "longitude": row[7],
                "upload_date": row[8],
                "source_type": row[9],
                "type": row[10]
            }
            return image_data
        cur.close()
        return None
    except Exception as e:
        print(f"Error fetching image by ID: {e}")
        return None
    finally:
        close_db_connection(conn)

def get_versions_by_image_id(image_id):
    """
    Get all versions of an image by its ID.
    :param image_id: int ; must be a valid image_id in the VersionedImage table
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = """
        SELECT version_number, file_path, model FROM VersionedImage WHERE image_id = %s ORDER BY version_number DESC;
        """
        cur.execute(select_query, (image_id,))
        rows = cur.fetchall()
        versions = []
        for row in rows:
            versions.append({
                "version_number": row[0],
                "file_path": row[1],
                "model": row[2]
            })
        cur.close()
        return versions
    except Exception as e:
        print(f"Error fetching versions by image ID: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_objects_by_image_version(image_id, version_number):
    """
    Get all objects for a specific image and version.
    :param image_id: int ; must be a valid image_id in the ObjectInstance table
    :param version_number: int ; must be a valid version_number in the ObjectInstance table
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT OBJ.object_id , OBJ.width , OBJ.height , OBJ.cropped_file_path , OBJ.class , OBJ.confidence_score
        FROM ObjectInstance AS OBJ
        WHERE OBJ.image_id = %s AND OBJ.version_number = %s;
        """
        cur.execute(query, (image_id, version_number))
        rows = cur.fetchall()
        objects = []
        for row in rows:
            objects.append({
                "object_id": row[0],
                "width": row[1],
                "height": row[2],
                "cropped_file_path": row[3],
                "class": row[4],
                "confidence": row[5]
            })
        cur.close()
        return objects
    except Exception as e:
        print(f"Error fetching objects by image version: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_metadata_by_object_id(image_id, object_id):
    """
    Get all metadata for a specific object in an image.
    ! General not specific to a version of the image. !
    :param image_id: int ; must be a valid image_id in the Metadata table
    :param object_id: int ; must be a valid object_id in the Metadata table
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT key, value FROM Metadata WHERE image_id = %s AND object_id = %s;
        """
        cur.execute(query, (image_id, object_id))
        rows = cur.fetchall()
        metadata = []
        for row in rows:
            metadata.append({
                "key": row[0],
                "value": row[1]
            })
        cur.close()
        return metadata
    except Exception as e:
        print(f"Error fetching metadata by object ID: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_images():
    """
    Get all images from the Image table.
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = """
        SELECT * FROM Image ORDER BY image_id DESC;
        """
        cur.execute(select_query)
        rows = cur.fetchall()
        images = []
        for row in rows:
            images.append({
                "image_id": row[0],
                "file_path": row[1],
                "title": row[2],
                "description": row[3],
                "capture_date": row[4],
                "location_name": row[5],
                "latitude": row[6],
                "longitude": row[7],
                "upload_date": row[8],
                "source_type": row[9],
                "type": row[10],
            })
        cur.close()
        return images
    except Exception as e:
        print(f"Error fetching images: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_classes():
    """
    Get all class names from the Class table.
    :return: list of strings or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = "SELECT name FROM Class;"
        cur.execute(select_query)
        rows = cur.fetchall()
        class_names = [row[0] for row in rows]
        return class_names
    except Exception as e:
        print(f"Error fetching classes: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_metadata_keys():
    """
    Get all metadata keys from the MetadataDefinition table.
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = """
        SELECT key, description, type, format_pattern, enum_values, metric FROM MetadataDefinition ORDER BY key;
        """
        cur.execute(select_query)
        rows = cur.fetchall()
        keys = []
        for row in rows:
            keys.append({
                "key": row[0],
                "description": row[1],
                "type": row[2],
                "format_pattern": row[3],
                "enum_values": row[4],
                "metric": row[5]
            })
        cur.close()
        return keys
    except Exception as e:
        print(f"Error fetching metadata keys: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_image_title():
    """
    Get all image titles from the Image table.
    :return: list of strings or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = "SELECT title FROM Image;"
        cur.execute(select_query)
        rows = cur.fetchall()
        titles = [row[0] for row in rows]
        return titles
    except Exception as e:
        print(f"Error fetching image titles: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_icons():
    """
    Get all icons from the Icon table.
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = "SELECT key, label, svg_path FROM Icon;"
        cur.execute(select_query)
        rows = cur.fetchall()
        icons = []
        for row in rows:
            icons.append({
                "key": row[0],
                "label": row[1],
                "svg_path": row[2]
            })
        cur.close()
        return icons
    except Exception as e:
        print(f"Error fetching icons: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_points():
    """
    Get all points from the Point table.
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        select_query = "SELECT point_id, name, description, location_name, latitude, longitude, icon_key, color_hex , ICON.svg_path FROM Point LEFT JOIN Icon ON Point.icon_key = Icon.key;"
        cur.execute(select_query)
        rows = cur.fetchall()
        points = []
        for row in rows:
            points.append({
                "point_id": row[0],
                "name": row[1],
                "description": row[2],
                "location_name": row[3],
                "latitude": row[4],
                "longitude": row[5],
                "icon_key": row[6],
                "color_hex": row[7],
                "icon_svg_path": row[8]
            })
        cur.close()
        return points
    except Exception as e:
        print(f"Error fetching points: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_metadata_by_point_id(point_id: int):
    """
    Get all metadata for a specific point.
    :param point_id: int ; must be a valid point_id in the MetaDataPoint table
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT key, value FROM MetaDataPoint WHERE point_id = %s;
        """
        cur.execute(query, (point_id,))
        rows = cur.fetchall()
        metadata = []
        for row in rows:
            metadata.append({
                "key": row[0],
                "value": row[1]
            })
        cur.close()
        return metadata
    except Exception as e:
        print(f"Error fetching metadata by point ID: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_instance_object_by_object_id(object_id: int):
    """
    Get all object instances for a specific object ID.
    :param object_id: int ; must be a valid object_id in the ObjectInstance table
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT OBJ.image_id, OBJ.version_number, OBJ.coords_x, OBJ.coords_y, OBJ.width, OBJ.height, OBJ.confidence_score, OBJ.cropped_file_path, OBJ.class, MD.key, MD.value
        FROM ObjectInstance OBJ
        LEFT JOIN Metadata MD ON OBJ.object_id = MD.object_id and OBJ.version_number = MD.version_number AND OBJ.image_id = MD.image_id
        WHERE OBJ.object_id = %s;
        """
        cur.execute(query, (object_id,))
        rows = cur.fetchall()
        instances = []
        for row in rows:
            instances.append({
                "image_id": row[0],
                "version_number": row[1],
                "coords_x": row[2],
                "coords_y": row[3],
                "width": row[4],
                "height": row[5],
                "confidence_score": row[6],
                "cropped_file_path": row[7],
                "class": row[8],
                "metadata_key": row[9],
                "metadata_value": row[10],
            })
        cur.close()
        return instances
    except Exception as e:
        print(f"Error fetching object instances by object ID: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_link_between_objects():
    """
    Allows to find images where the same object appears multiple times.
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT I.image_id , I.latitude , I.longitude  , OBI.object_id 
        FROM Image AS I
        JOIN ObjectInstance AS OBI ON I.image_id = OBI.image_id
        WHERE (
            OBI.object_id IN (
                SELECT OBJ.object_id 
                FROM Object AS OBJ
                JOIN ObjectInstance AS OBI ON OBJ.object_id = OBI.object_id
                GROUP BY OBJ.object_id
                HAVING COUNT(DISTINCT OBI.image_id) > 1
            )
        );
        """
        cur.execute(query)
        rows = cur.fetchall()
        links = []
        for row in rows:
            links.append({
                "image_id": row[0],
                "latitude": row[1],
                "longitude": row[2],
                "object_id": row[3]
            })
        cur.close()
        print(links)
        return links
    except Exception as e:
        print(f"Error fetching link between objects: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_link_types():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = "SELECT key, label FROM LinkType;"
        cur.execute(query)
        rows = cur.fetchall()
        link_types = []
        for row in rows:
            link_types.append({
                "key": row[0],
                "label": row[1]
            })  
        cur.close()
        return link_types
    except Exception as e:
        print(f"Error fetching link types: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_links():
    """
    Get all links from the Link table.
    :return: list of dicts or empty list
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = "SELECT link_id, title, description, link_type, created_at FROM Link;"
        cur.execute(query)
        rows = cur.fetchall()
        links = []
        for row in rows:
            links.append({
                "link_id": row[0],
                "title": row[1],
                "description": row[2],
                "link_type": row[3],
                "created_at": row[4]
            })  
        cur.close()
        return links
    except Exception as e:
        print(f"Error fetching links: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_link_endpoints(link_id: int):
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT LEP.entity_type, LEP.image_id, LEP.point_id, LEP.role, LEP.order_index , img.latitude, img.longitude, pt.latitude, pt.longitude
        FROM LinkEndPoint LEP
        LEFT JOIN Image img ON LEP.image_id = img.image_id
        LEFT JOIN Point pt ON LEP.point_id = pt.point_id
        WHERE link_id = %s
        ORDER BY order_index ASC;
        """
        cur.execute(query, (link_id,))
        rows = cur.fetchall()
        endpoints = []
        for row in rows:
            latitude = row[5] if row[5] is not None else row[7]
            longitude = row[6] if row[6] is not None else row[8]
            endpoints.append({
                "entity_type": row[0],
                "image_id": row[1],
                "point_id": row[2],
                "role": row[3],
                "order_index": row[4],
                "latitude": latitude,
                "longitude": longitude
            })  
        cur.close()
        return endpoints
    except Exception as e:
        print(f"Error fetching link endpoints: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_link_metadata(link_id: int):
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = """
        SELECT key , value FROM LinkMetadata WHERE link_id = %s;
        """
        cur.execute(query, (link_id,))
        rows = cur.fetchall()
        metadata = []
        for row in rows:
            metadata.append({
                "key": row[0],
                "value": row[1]
            })
        cur.close()
        return metadata
    except Exception as e:
        print(f"Error fetching link metadata: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_link_geometry(link_id: int):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        query = """
        SELECT geojson, source FROM LinkGeometry WHERE link_id = %s;
        """
        cur.execute(query, (link_id,))
        row = cur.fetchone()
        if row:
            geometry = {
                "geojson": row[0],
                "source": row[1]
            }
            return geometry
        cur.close()
        return None
    except Exception as e:
        print(f"Error fetching link geometry: {e}")
        return None
    finally:
        close_db_connection(conn)

def get_all_metadatas_values():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        query = "SELECT DISTINCT key , value FROM Metadata;"
        cur.execute(query)
        rows = cur.fetchall()
        metadatas = []
        for row in rows:
            metadatas.append({
                "key": row[0],
                "value": row[1]
            })
        cur.close()
        return metadatas
    except Exception as e:
        print(f"Error fetching all metadata values: {e}")
        return []
    finally:        
        close_db_connection(conn)
        
def find_similar_objects(embedding: list, top_k: int = 5):
    """
    Find similar objects based on the provided embedding using cosine similarity.
    """
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()

        # Convert the embedding list to PostgreSQL vector format
        vector_str = "[" + ",".join(map(str, embedding)) + "]"
        query = """
        SELECT object_id, name, embedding <-> %s::vector AS distance
        FROM Object
        WHERE embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT %s;
        """
        cur.execute(query, (vector_str, top_k))
        rows = cur.fetchall()
        similar_objects = [
            {"object_id": row[0], "name": row[1], "distance": row[2]}
            for row in rows
        ]
        cur.close()
        return similar_objects
    except Exception as e:
        print(f"Error finding similar objects: {e}")
        return []
    finally:
        close_db_connection(conn)

from dateutil import parser

def normalize_value(value: str):
    if not value:
        return value
    value = value.strip()
    try:
        # Essaye de convertir en date normalisée
        return parser.parse(value).date().isoformat()
    except:
        return value.lower()

def find_similar_objects_by_metadatas(metadatas: list[dict[str, str]]):
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        where_clauses = []
        params = []

        for m in metadatas:
            key = m.get("key")
            value = normalize_value(m.get("value"))
            where_clauses.append("(LOWER(MD.key) = LOWER(%s) AND LOWER(MD.value) = LOWER(%s))")
            params.extend([key, value])

        if not where_clauses:
            return []

        WHERE = " OR ".join(where_clauses)

        query = f"""
        SELECT OBJ.object_id, OBJ.name, COUNT(MD.key) AS match_count
        FROM Object OBJ 
        JOIN ObjectInstance OBI ON OBJ.object_id = OBI.object_id
        JOIN Metadata MD ON OBI.object_id = MD.object_id 
        WHERE {WHERE}
        GROUP BY OBJ.object_id 
        ORDER BY match_count DESC;
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        similar_objects = [
            {"object_id": row[0], "name": row[1], "match_count": row[2]}
            for row in rows
        ]

        cur.close()
        return similar_objects

    except Exception as e:
        print(f"Error finding similar objects by metadatas: {e}")
        return []
    finally:
        close_db_connection(conn)

def find_similar_objects_by_value(value: str):
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        normalized_value = normalize_value(value)
        query = """
        SELECT OBJ.object_id , OBJ.name , COUNT(MD.key) AS match_count
        FROM Object OBJ 
        JOIN ObjectInstance OBI ON OBJ.object_id = OBI.object_id
        JOIN Metadata MD ON OBI.object_id = MD.object_id 
        WHERE LOWER(MD.value) ILIKE LOWER(%s)
        GROUP BY OBJ.object_id 
        ORDER BY match_count DESC;
        """
        cur.execute(query, (f"%{normalized_value}%",))
        rows = cur.fetchall()
        similar_objects = [ 
            {"object_id": row[0], "name": row[1], "match_count": row[2]}
            for row in rows
        ]
        cur.close()
        return similar_objects

    except Exception as e:
        print(f"Error finding similar objects by value: {e}")
        return []
    finally:
        close_db_connection(conn)