import os

class Config:
    UPLOAD_FOLDER = "static/img/Images"
    JSON_FOLDER = "static/json"
    TEMP_FOLDER = "static/temp"
    DEBUG = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit (not used yet)
