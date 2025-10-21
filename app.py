# app.py
from flask import Flask
from config import Config
import os

# --- blueprints imports ---
from routes import (
    analysis_bp,
    object_bp,
    metadata_bp,
    save_bp,
    main_routes_bp
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # --- blueprints registration ---
    app.register_blueprint(main_routes_bp, url_prefix="/")
    app.register_blueprint(analysis_bp, url_prefix="/analysis")
    app.register_blueprint(object_bp, url_prefix="/objects")
    app.register_blueprint(metadata_bp, url_prefix="/metadata")
    app.register_blueprint(save_bp, url_prefix="/save")

    return app

if __name__ == "__main__":
    from utils.helper import cleanup_temp_dir
    cleanup_temp_dir()
    app = create_app()
    app.run(debug=True)
