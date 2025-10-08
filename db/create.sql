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
    FOREIGN KEY (object_id) REFERENCES Object(object_id) ON DELETE CASCADE,
    FOREIGN KEY (version_number, image_id) REFERENCES VersionedImage(version_number, image_id) ON DELETE CASCADE,
    PRIMARY KEY (object_id, image_id, version_number)
);

CREATE TABLE Metadata (
    object_id INT NOT NULL,
    image_id INT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES Object(object_id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES Image(image_id) ON DELETE CASCADE,
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
