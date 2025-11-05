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
DROP TYPE IF EXISTS link_entity;
DROP TABLE IF EXISTS Icon CASCADE;
DROP TABLE IF EXISTS MetaDataPoint CASCADE;
DROP TABLE IF EXISTS Point CASCADE;
DROP TABLE IF EXISTS LinkEndPoint CASCADE;
DROP TABLE IF EXISTS LinkGeometry CASCADE;
DROP TABLE IF EXISTS LinkMetadata CASCADE;
DROP TABLE IF EXISTS Link CASCADE;
DROP TABLE IF EXISTS LinkType CASCADE;


-- ==============================================
-- 2. Enum Types
-- ==============================================
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

CREATE TYPE link_entity AS ENUM(
    'image',
    'point'
);

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
    version_number INT NOT NULL,
    image_id INT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id, version_number, image_id) REFERENCES ObjectInstance(object_id, version_number, image_id) ON DELETE CASCADE,
    FOREIGN KEY (key) REFERENCES MetadataDefinition(key) ON DELETE CASCADE,
    PRIMARY KEY (object_id, version_number, image_id, key)
);

-- ==============================================
-- Map system tables
-- ==============================================

CREATE TABLE Icon(
    key TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    svg_path TEXT NOT NULL
);
CREATE TABLE Point (
    point_id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    location_name TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    icon_key TEXT REFERENCES Icon(key) ON DELETE SET NULL,
    color_hex VARCHAR(7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE MetaDataPoint (
    point_id INT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (point_id) REFERENCES Point(point_id) ON DELETE CASCADE,
    FOREIGN KEY (key) REFERENCES MetadataDefinition(key) ON DELETE CASCADE,
    PRIMARY KEY (point_id, key)
);

CREATE TABLE LinkType (
    key TEXT PRIMARY KEY,       -- ex: 'pilgrimage', '100-days', 'war-1980'
    label TEXT NOT NULL         
);

-- Allow to give a title to the link, e.g. "Pèlerinage Seg. A" , "First step of 100-days..."
CREATE TABLE Link (
    link_id SERIAL PRIMARY KEY,
    title TEXT,  
    description TEXT, 
    link_type TEXT NOT NULL REFERENCES LinkType(key) ON DELETE RESTRICT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE LinkEndPoint(
    link_id INT NOT NULL,
    entity_type link_entity NOT NULL,
    image_id INT,
    point_id INT,
    role TEXT,               -- e.g. 'start', 'end', 'waypoint'
    order_index INT,        -- order of the endpoint in the link
    PRIMARY KEY (link_id, entity_type, order_index),
    UNIQUE (link_id , image_id),
    UNIQUE (link_id , point_id),
    FOREIGN KEY (link_id) REFERENCES Link(link_id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES Image(image_id) ON DELETE CASCADE,
    FOREIGN KEY (point_id) REFERENCES Point(point_id) ON DELETE CASCADE,
    CHECK ((entity_type = 'image' AND image_id IS NOT NULL AND point_id IS NULL) OR
           (entity_type = 'point' AND point_id IS NOT NULL AND image_id IS NULL))
);

CREATE TABLE LinkGeometry(
    link_id INT NOT NULL,
    geojson JSONB NOT NULL,
    source TEXT,
    PRIMARY KEY (link_id),
    FOREIGN KEY (link_id) REFERENCES Link(link_id) ON DELETE CASCADE
);

CREATE TABLE LinkMetadata (
    link_id INT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (link_id) REFERENCES Link(link_id) ON DELETE CASCADE,
    FOREIGN KEY (key) REFERENCES MetadataDefinition(key) ON DELETE CASCADE,
    PRIMARY KEY (link_id, key)
);

-- ==============================================
-- 3. Triggers
-- ==============================================
-- Trigger to auto-increment version_number in VersionedImage

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
