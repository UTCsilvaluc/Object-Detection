import { clusterPoints, centerCluster } from './math.js';

export function enableClustering(map, clusters, markers, filteredImages) {
    const findCluster = clusterPoints(filteredImages);
    findCluster.forEach(cluster => {
        L.circleMarker(
            [centerCluster(cluster).latitude, centerCluster(cluster).longitude],
            { radius: 10 + (cluster.length - 1) * 2, color: 'blue', fillOpacity: 0.5 }
        )
        .bindPopup(`Cluster of ${cluster.length} images`)
        .addTo(clusters);
    });
}

export function disableClustering() {
    alert("Clustering disabled (feature coming soon)!");
}

export function showHeatmap() {
    alert("Heatmap shown (feature coming soon)!");
}

export function hideHeatmap() {
    alert("Heatmap hidden (feature coming soon)!");
}

export function showTimeline() {
    alert("Timeline shown (feature coming soon)!");
}

export function hideTimeline() {
    alert("Timeline hidden (feature coming soon)!");
}

export function showObjectLinks() {
    alert("Object links shown (feature coming soon)!");
}

export function hideObjectLinks() {
    alert("Object links hidden (feature coming soon)!");
}