CREATE INDEX IF NOT EXISTS idx_object_embedding 
ON Object USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-----

CREATE INDEX IF NOT EXISTS idx_versionedimage_latest
ON VersionedImage(image_id, version_number DESC);

CREATE INDEX IF NOT EXISTS idx_objinst_image_version
ON ObjectInstance(image_id, version_number);
CREATE INDEX IF NOT EXISTS idx_oi_object_id ON ObjectInstance(object_id);
CREATE INDEX IF NOT EXISTS idx_objectinstance_objectid_version 
ON ObjectInstance(object_id, version_number DESC);


CREATE INDEX IF NOT EXISTS idx_metadata_image_obj_ver
ON Metadata(image_id, object_id, version_number);
CREATE INDEX IF NOT EXISTS idx_md_instance ON Metadata(object_id, image_id, version_number);
CREATE INDEX IF NOT EXISTS idx_metadata_objectid ON Metadata(object_id);

CREATE INDEX IF NOT EXISTS idx_point_icon_point_id ON Point (icon_key, point_id);

CREATE INDEX IF NOT EXISTS idx_metadatapoint_point_key ON MetaDataPoint (point_id, key);

CREATE INDEX IF NOT EXISTS idx_lep_link_order
ON LinkEndPoint(link_id, order_index);
