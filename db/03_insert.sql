-- ==============================================
-- DISCLAIMER: All datas have been generated for testing purposes only and by AI.
-- They do not represent real historical data.
-- ==============================================
INSERT INTO ThreadCategory (key, label) VALUES
('identity', 'Identity Thread'),
('place', 'Place Thread'),
('date', 'Date Thread'),
('event', 'Event Thread'),
('custom', 'No thread');

INSERT INTO Icon (key, label, svg_path) VALUES
('bike', 'Bike', 'bike.svg'),
('break', 'Break', 'break.svg'),
('bus', 'Bus', 'bus.svg'),
('coffin', 'Coffin', 'coffin.svg'),
('house', 'House', 'house.svg'),
('information', 'Information', 'information.svg'),
('rest', 'Rest', 'rest.svg'),
('restaurant', 'Restaurant', 'restaurant.svg'),
('temple', 'Temple', 'temple.svg'),
('toilets', 'Toilets', 'toilets.svg'),
('train', 'Train', 'train.svg');
-- ==============================================

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
INSERT INTO MetadataDefinition
(key, description, type, thread_category, format_pattern, enum_values, metric)
VALUES
-- ===== Textual / String =====
('title', 'Short title or name of the object', 'short', NULL, '^[\\p{L}\\p{N}\\s\\-_,.()]{1,100}$', NULL, NULL),
('description', 'Detailed textual description', 'text', NULL, NULL, NULL, NULL),
('creator', 'Author, artist or maker of the object', 'string', NULL, '^[\\p{L}\\s\\-]{1,100}$', NULL, NULL),
('language', 'Primary language of the text or inscription', 'enum', NULL, NULL, 'Japanese;English;French;Chinese;Korean;Other', NULL),

-- ===== Numeric =====
('height', 'Height of the object', 'float', NULL, '^[0-9]+(\\.[0-9]+)?$', NULL, 'cm'),
('width', 'Width of the object', 'float', NULL, '^[0-9]+(\\.[0-9]+)?$', NULL, 'cm'),
('length', 'Length or depth of the object', 'float', NULL, '^[0-9]+(\\.[0-9]+)?$', NULL, 'cm'),
('weight', 'Weight of the object', 'float', NULL, '^[0-9]+(\\.[0-9]+)?$', NULL, 'kg'),

-- ===== Coordinates =====
('latitude', 'Geographical latitude', 'coordinate', NULL, '^[-+]?([1-8]?\\d(\\.\\d+)?|90(\\.0+)?)$', NULL, '°'),
('longitude', 'Geographical longitude', 'coordinate', NULL, '^[-+]?(180(\\.0+)?|((1[0-7]\\d)|([1-9]?\\d))(\\.\\d+)?)$', NULL, '°'),

-- ===== Boolean =====
('is_original', 'Indicates whether this object is an original or a reproduction', 'bool', NULL, '^(true|false|0|1)$', NULL, NULL),
('is_historical', 'Specifies if the object has historical significance', 'bool', NULL, '^(true|false|0|1)$', NULL, NULL),

-- ===== Date =====
('date_of_birth', 'Date of birth (for a person or creation date)', 'date', NULL, '^\\d{4}-\\d{2}-\\d{2}$', NULL, NULL),
('capture_date', 'Date of image capture', 'date-hr-sec', NULL, '^\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}$', NULL, NULL),

-- ===== Enumerations =====
('material', 'Material composition of the object', 'enum', NULL, 'Wood;Stone;Metal;Paper;Ceramic;Glass;Fabric;Plastic;Other', NULL , NULL),
('condition', 'Preservation condition of the object', 'enum', NULL, 'Excellent;Good;Fair;Poor;Restored', NULL, NULL),
('orientation', 'Orientation of the object or photo', 'enum', NULL, 'Portrait;Landscape;Square;Unknown', NULL, NULL),

-- ===== Specialized formats =====
('confidence_score', 'Confidence level of detection (0-1)', 'short_float', NULL, '^(0(\\.\\d+)?|1(\\.0+)?)$', NULL, NULL),
('person_age', 'Approximate age of person', 'int', NULL, '^[0-9]{1,3}$', NULL, 'years'),
('temperature', 'Temperature at capture time', 'float', NULL, '^-?[0-9]+(\\.[0-9]+)?$', NULL, '°C'),
('file_format', 'File format type', 'enum', NULL, 'JPEG;PNG;TIFF;BMP;WEBP;Other', NULL , NULL),
('cultural_period', 'Cultural or historical period of the object', 'string', NULL, '^[\\p{L}\\s\\-_,.()]{1,50}$', NULL, NULL),

-- ===== Thread Research =====
('place_name', 'Name of the place where the image has taken place', 'string', 'place', '^[\\p{L}\\s\\-_,.()]{1,100}$', NULL, NULL),
('event_name', 'Name of the event depicted in the image', 'string', 'event', '^[\\p{L}\\s\\-_,.()]{1,100}$', NULL, NULL),
('event_date', 'Date of the event depicted in the image', 'date', 'date', '^\\d{4}-\\d{2}-\\d{2}$', NULL, NULL),
('identity', 'Identity of the person or object depicted in the image', 'string', 'identity', '^[\\p{L}\\s\\-_,.()]{1,100}$', NULL, NULL);


