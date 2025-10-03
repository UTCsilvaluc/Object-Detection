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

def insert_image(file_path, title, description=None, capture_date=None, location_name=None, latitude=None, longitude=None, source_type=None):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO Image (file_path, title, description, capture_date, location_name, latitude, longitude, source_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING image_id;
        """
        cur.execute(insert_query, (file_path, title, description, capture_date, location_name, latitude, longitude, source_type))
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
"""
CREATE TABLE ObjectInstance (
    object_id INT NOT NULL,
    version_number INT NOT NULL,
    image_id INT NOT NULL,
    coords_x REAL,
    coords_y REAL,
    width REAL,
    height REAL,
    confidence_score NUMERIC(4, 3),
    cropped_file_path TEXT,
    FOREIGN KEY (object_id) REFERENCES Object(object_id) ON DELETE CASCADE,
    FOREIGN KEY (version_number, image_id) REFERENCES VersionedImage(version_number, image_id) ON DELETE CASCADE,
    PRIMARY KEY (object_id, image_id, version_number)
);
"""
def create_instance_object(object_id: int , version_number: int , image_id: int , coords_x: float = None , coords_y: float = None , width: float = None , height: float = None , confidence_score: float = None , cropped_file_path: str = None):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        insert_query = """
        INSERT INTO ObjectInstance (object_id, version_number, image_id, coords_x, coords_y, width, height, confidence_score, cropped_file_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (object_id, version_number, image_id, coords_x, coords_y, width, height, confidence_score, cropped_file_path))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error inserting object instance: {e}")
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