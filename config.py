import os

class Config:
    UPLOAD_FOLDER = "static/img/Images"
    JSON_FOLDER = "static/json"
    TEMP_FOLDER = "static/temp"
    DEBUG = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit (not used yet)
    # SAM model selection (options: sam_vit_h, sam_vit_l, sam_vit_b, sam_min)
    SAM_MODEL = "sam_vit_l"
