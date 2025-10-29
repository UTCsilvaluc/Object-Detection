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
