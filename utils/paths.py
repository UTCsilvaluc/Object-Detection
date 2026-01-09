import os

# Directory and file path configurations
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) #Absolute path of the utils folder
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir)) #Absolute path of the project root folder

MEDIA_ROOT = os.path.abspath(os.getenv("MEDIA_ROOT" , os.path.join(ROOT_DIR, "media")))
TEMP_ROOT = os.path.abspath(os.getenv("TEMP_ROOT" , os.path.join(MEDIA_ROOT, "temp")))
MEDIA_URL = os.getenv("MEDIA_URL" , "/media")

MEDIA_IMAGES_DIR = os.path.join(MEDIA_ROOT, "img", "Images")
MEDIA_THUMBS_DIR = os.path.join(MEDIA_ROOT, "thumbs")
MEDIA_CROPS_DIR = os.path.join(MEDIA_ROOT, "crops")

TEMP_IMG_DIR = os.path.join(TEMP_ROOT, "img")
TEMP_JSON_DIR = os.path.join(TEMP_ROOT, "json")
TEMP_THUMBS_DIR = os.path.join(TEMP_ROOT, "thumbs")