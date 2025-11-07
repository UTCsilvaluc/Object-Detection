// static/js/math.js

/**
 * Clusters points based on a simple distance threshold.
 * @param {Array} points - Array of point objects with latitude and longitude.
 * @param {number} tolerance - Distance threshold for clustering.
 * @returns {Array} - Array of clusters, each cluster is an array of points.
 */
export function clusterPoints(points, tolerance = 0.01 , zoomLevel=10) {
    const clusters = [];
    const visited = new Set();
    
    points.forEach((point, index) => {
        if (visited.has(index)) return;
        const cluster = [point];
        visited.add(index);
        points.forEach((otherPoint, otherIndex) => {
            if (index !== otherIndex && !visited.has(otherIndex)) {
                const distance = dist(point.latitude - otherPoint.latitude, point.longitude - otherPoint.longitude);
                if (distance < getTolerance(zoomLevel)) {
                    cluster.push(otherPoint);
                    visited.add(otherIndex);
                }
            }
        });
        
        clusters.push(cluster);
    });
    return clusters;
}

function getTolerance(zoom)
{
    return 0.5 / Math.pow(1.5, zoom - 5);
}
export function dist(latDiff, lonDiff) {
    return Math.sqrt(latDiff * latDiff + lonDiff * lonDiff);
}
/**
 * Centers a cluster of points by calculating the average latitude and longitude.
 * @param {Array} cluster - Array of point objects with latitude and longitude.
 * @returns {Object} - Object containing the center latitude and longitude.
 */
export function centerCluster(cluster) {
    const latSum = cluster.reduce((sum, point) => sum + point.latitude, 0);
    const lonSum = cluster.reduce((sum, point) => sum + point.longitude, 0);
    return {
        latitude: latSum / cluster.length,
        longitude: lonSum / cluster.length
    };
}

export function destinationPoint(lat, lon, distance, bearingDeg) {
    const R = 6378137; // Earth radius in meters
    const bearing = bearingDeg * Math.PI / 180;
    lat = lat * Math.PI / 180;
    lon = lon * Math.PI / 180;

    const lat2 = Math.asin(
        Math.sin(lat) * Math.cos(distance / R) +
        Math.cos(lat) * Math.sin(distance / R) * Math.cos(bearing)
    );

    const lon2 = lon + Math.atan2(
        Math.sin(bearing) * Math.sin(distance / R) * Math.cos(lat),
        Math.cos(distance / R) - Math.sin(lat) * Math.sin(lat2)
    );

    return [
        lat2 * 180 / Math.PI,
        lon2 * 180 / Math.PI
    ];
}

export function metersFromPixels(pixels, lat, zoom) {
    const earthCircumference = 40075016.686; 
    return pixels * earthCircumference * Math.cos(lat * Math.PI / 180) / Math.pow(2, zoom + 8);
}

export function getMaxPixelRadius(map, center) {
    const mapSize = map.getSize(); // width/height in pixels

    const centerPx = map.latLngToContainerPoint([center.latitude, center.longitude]);

    // distance au bord gauche, droit, haut, bas
    const distLeft = centerPx.x;
    const distRight = mapSize.x - centerPx.x;
    const distTop = centerPx.y;
    const distBottom = mapSize.y - centerPx.y;

    return Math.min(distLeft, distRight, distTop, distBottom);
}

export function degOfPente(map, lat1, lon1, lat2, lon2) {
    const point1 = map.latLngToContainerPoint([lat1, lon1]);
    const point2 = map.latLngToContainerPoint([lat2, lon2]);
    const latDiff = point2.y - point1.y;
    const lonDiff = point2.x - point1.x;
    return Math.atan2(latDiff, lonDiff) * (180 / Math.PI);
}
