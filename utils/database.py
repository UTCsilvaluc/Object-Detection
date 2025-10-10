import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def get_db_connection():
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
    try:
        if conn:
            conn.close()
    except Exception as e:
        print(f"Error closing database connection: {e}")    

def insert_image(file_path, title, description=None, capture_date=None, location_name=None, latitude:float=None, longitude:float=None, source_type=None, type=None):
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

    :param image_id: int
    :param file_path: str
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

def create_object(name: str , description: str = None , type: str = None , embedding: list = None):
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

def update_class_instance_object(object_id: int, version_number: int, image_id: int, new_class: str):
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


def insert_metadata(object_id: int , image_id: int , key: str , value: str):
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

def get_all_images():
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
        print(images)
        cur.close()
        return images
    except Exception as e:
        print(f"Error fetching images: {e}")
        return []
    finally:
        close_db_connection(conn)

def get_all_classes():
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

def check_if_class_exist(name):
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

def create_new_class(name, desc):
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

def get_all_metadata_keys():
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

def check_if_metadata_key_exist(key):
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

def create_new_metadata_key(key, desc, metric=None, type=None, enum_values=None , format_pattern=None):
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