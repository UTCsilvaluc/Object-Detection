from utils.paths import MEDIA_IMAGES_DIR, TEMP_JSON_DIR, TEMP_ROOT

class Config:
    UPLOAD_FOLDER = MEDIA_IMAGES_DIR
    JSON_FOLDER = TEMP_JSON_DIR
    TEMP_FOLDER = TEMP_ROOT
    DEBUG = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit (not used yet)
    # SAM model selection (options: sam_vit_h, sam_vit_l, sam_vit_b, sam_min)
    SAM_MODEL = "sam_vit_l"
