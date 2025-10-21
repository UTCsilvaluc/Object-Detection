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

def insert_metadata(object_id: int , image_id: int , key: str , value: str):
    """
    Insert a new metadata record into the Metadata table.
    :param object_id: int
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
        INSERT INTO Metadata (object_id, image_id, key, value)
        VALUES (%s, %s, %s, %s)
        """
        cur.execute(insert_query, (object_id, image_id, key, value))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting metadata: {e}")
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
                "source_type": row[8],
                "type": row[9],
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