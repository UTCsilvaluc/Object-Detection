# utils/data_objects.py

from utils.database import (
    get_link_between_objects,
    get_instance_object_by_object_id,
    get_metadata_by_point_id,
    get_metadata_by_object_id,
    get_versions_by_image_id,
    get_objects_by_image_version,
    get_link_endpoints,
    get_link_metadata,
    get_link_geometry,
    find_shared_objects_between_images
)

def build_object_links():
    """
    Return:
        grouped: dict {object_id: [ {lat, lon, image_id}, ... ]}
        object_datas: dict {object_id: {...instance data...}}
    """
    object_links = get_link_between_objects()
    shared_objects = find_shared_objects_between_images()
    grouped = {}
    object_datas = {}

    if not object_links:
        return grouped, object_datas

    for link in object_links:
        oid = link['object_id']
        if oid not in grouped:
            grouped[oid] = []
            object_datas[oid] = get_instance_object_by_object_id(oid)

        grouped[oid].append({
            'latitude': link['latitude'],
            'longitude': link['longitude'],
            'image_id': link['image_id']
        })

    return grouped, object_datas , shared_objects



def enrich_points_with_metadata(points):
    """Attach metadata to each point."""
    for p in points:
        p['metadata'] = get_metadata_by_point_id(p['point_id'])
    return points



def enrich_images_with_objects(images):
    """
    For each image:
        - Find version
        - Find objects
        - Attach metadata to each object
    """
    for image in images:
        versions = get_versions_by_image_id(image['image_id'])
        if not versions:
            image['objects'] = []
            continue

        current_version = versions[0]['version_number']
        objects = get_objects_by_image_version(image['image_id'], current_version)

        for obj in objects:
            obj['metadatas'] = get_metadata_by_object_id(
                image_id=image['image_id'],
                object_id=obj['object_id']
            )

        image['objects'] = objects

    return images



def enrich_links(links):
    """
    For each link:
        - Add endpoints
        - Add metadata
        - Add geometry
    """
    for link in links:
        lid = link['link_id']
        link['endpoints'] = get_link_endpoints(lid)
        link['metadata'] = get_link_metadata(lid)
        link['geometry'] = get_link_geometry(lid)
    return links
