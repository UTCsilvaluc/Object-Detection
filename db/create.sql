CREATE EXTENSION IF NOT EXISTS vector;
-- ==============================================
-- 1. Drop existing tables (for dev convenience)
-- ==============================================
DROP TABLE IF EXISTS Metadata CASCADE;
DROP TABLE IF EXISTS ObjectInstance CASCADE;
DROP TABLE IF EXISTS Object CASCADE;
DROP TABLE IF EXISTS VersionedImage CASCADE;
DROP TABLE IF EXISTS Image CASCADE;
DROP TABLE IF EXISTS Class CASCADE;
DROP TABLE IF EXISTS MetadataDefinition CASCADE;
DROP TYPE IF EXISTS metaType;

-- ==============================================
-- 2. Tables
-- ==============================================
CREATE TABLE Class(
    name VARCHAR(255) PRIMARY KEY,
    description TEXT
);

CREATE TABLE Image (
    image_id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    title TEXT,
    description TEXT,
    capture_date TIMESTAMP,
    location_name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT,
    type VARCHAR(255) REFERENCES Class(name) ON DELETE CASCADE
);

CREATE TABLE VersionedImage (
    image_id INT NOT NULL,
    version_number INT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model TEXT,
    FOREIGN KEY (image_id) REFERENCES Image(image_id) ON DELETE CASCADE,
    PRIMARY KEY (image_id, version_number)
);

CREATE TABLE Object (
    object_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    type VARCHAR(100),
    embedding vector(512) -- requires pgvector extension
);

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
    class VARCHAR(255) REFERENCES Class(name) ON DELETE SET NULL,
    FOREIGN KEY (object_id) REFERENCES Object(object_id) ON DELETE CASCADE,
    FOREIGN KEY (version_number, image_id) REFERENCES VersionedImage(version_number, image_id) ON DELETE CASCADE,
    PRIMARY KEY (object_id, image_id, version_number)
);
CREATE TYPE metaType AS ENUM(
    'short', 
    'text', 
    'int', 
    'float', 
    'short_float', 
    'coordinate', 
    'bool', 
    'date', 
    'date-hr-sec', 
    'string', 
    'enum'
);

CREATE TABLE MetadataDefinition(
    key TEXT PRIMARY KEY,
    description TEXT,
    type metaType NOT NULL,
    format_pattern TEXT, -- regex pattern for validation 
    enum_values TEXT, -- semicolon-separated values for enum type
    metric VARCHAR(100), -- unit of measurement if applicable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Metadata (
    object_id INT NOT NULL,
    image_id INT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES Object(object_id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES Image(image_id) ON DELETE CASCADE,
    FOREIGN KEY (key) REFERENCES MetadataDefinition(key) ON DELETE CASCADE,
    PRIMARY KEY (object_id, image_id, key)
);

INSERT INTO Class (name, description) VALUES
('Person', 'Human individual detected in the image'),
('Building', 'Architectural structures such as houses, temples, or towers'),
('Artifact', 'Historical or cultural objects, tools, or art pieces'),
('Animal', 'Domestic or wild animals'),
('Plant', 'Vegetation including trees, flowers, and crops'),
('Landscape', 'Natural scenery, including mountains, rivers, and terrain'),
('Historical Map', 'Old maps representing geographical information'),
('Historical Document', 'Documents of historical value or manuscripts'),
('Inscription', 'Text or carvings engraved on surfaces or objects');

-- ==============================================
-- Insert default Metadata Definitions
-- ==============================================
INSERT INTO MetadataDefinition (key, description, type, format_pattern, enum_values, metric) VALUES
-- ===== Textual / String =====
('title', 'Short title or name of the object', 'short', '^[\\p{L}\\p{N}\\s\\-_,.()]{1,100}$', NULL, NULL),
('description', 'Detailed textual description', 'text', NULL, NULL, NULL),
('creator', 'Author, artist or maker of the object', 'string', '^[\\p{L}\\s\\-]{1,100}$', NULL, NULL),
('language', 'Primary language of the text or inscription', 'enum', NULL, 'Japanese;English;French;Chinese;Korean;Other', NULL),

-- ===== Numeric =====
('height', 'Height of the object', 'float', '^[0-9]+(\\.[0-9]+)?$', NULL, 'cm'),
('width', 'Width of the object', 'float', '^[0-9]+(\\.[0-9]+)?$', NULL, 'cm'),
('length', 'Length or depth of the object', 'float', '^[0-9]+(\\.[0-9]+)?$', NULL, 'cm'),
('weight', 'Weight of the object', 'float', '^[0-9]+(\\.[0-9]+)?$', NULL, 'kg'),

-- ===== Coordinates =====
('latitude', 'Geographical latitude', 'coordinate', '^[-+]?([1-8]?\\d(\\.\\d+)?|90(\\.0+)?)$', NULL, '°'),
('longitude', 'Geographical longitude', 'coordinate', '^[-+]?(180(\\.0+)?|((1[0-7]\\d)|([1-9]?\\d))(\\.\\d+)?)$', NULL, '°'),

-- ===== Boolean =====
('is_original', 'Indicates whether this object is an original or a reproduction', 'bool', '^(true|false|0|1)$', NULL, NULL),
('is_historical', 'Specifies if the object has historical significance', 'bool', '^(true|false|0|1)$', NULL, NULL),

-- ===== Date =====
('date_of_birth', 'Date of birth (for a person or creation date)', 'date', '^\\d{4}-\\d{2}-\\d{2}$', NULL, NULL),
('capture_date', 'Date of image capture', 'date-hr-sec', '^\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}$', NULL, NULL),

-- ===== Enumerations =====
('material', 'Material composition of the object', 'enum', NULL, 'Wood;Stone;Metal;Paper;Ceramic;Glass;Fabric;Plastic;Other', NULL),
('condition', 'Preservation condition of the object', 'enum', NULL, 'Excellent;Good;Fair;Poor;Restored', NULL),
('orientation', 'Orientation of the object or photo', 'enum', NULL, 'Portrait;Landscape;Square;Unknown', NULL),

-- ===== Specialized formats =====
('confidence_score', 'Confidence level of detection (0-1)', 'short_float', '^(0(\\.\\d+)?|1(\\.0+)?)$', NULL, NULL),
('person_age', 'Approximate age of person', 'int', '^[0-9]{1,3}$', NULL, 'years'),
('temperature', 'Temperature at capture time', 'float', '^-?[0-9]+(\\.[0-9]+)?$', NULL, '°C'),
('file_format', 'File format type', 'enum', NULL, 'JPEG;PNG;TIFF;BMP;WEBP;Other', NULL),
('cultural_period', 'Cultural or historical period of the object', 'string', '^[\\p{L}\\s\\-_,.()]{1,50}$', NULL, NULL);


CREATE OR REPLACE FUNCTION auto_increment_version()
RETURNS TRIGGER AS $$
BEGIN 
    NEW.version_number := COALESCE(
        (SELECT MAX(version_number) 
         FROM VersionedImage 
         WHERE image_id = NEW.image_id), 0
    ) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_increment_version ON VersionedImage;

CREATE TRIGGER trg_auto_increment_version
BEFORE INSERT ON VersionedImage
FOR EACH ROW
EXECUTE FUNCTION auto_increment_version();

-- ==============================================
-- Auto create the database and run this script with:
-- createdb -U postgres object_detection
-- psql -U postgres -d object_detection -f ~/Desktop/object-detection/db/create.sql

-- Please check the database with the following command:
-- \d+ Image : Show table details
-- \dt : List all tables
-- ==============================================
