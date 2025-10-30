import { clusterPoints, centerCluster } from './math.js';
import { createPopupHTML } from './popup.js';
window.expandedMarkers = [];
window.hiddenClusters = [];
window.isExpanding = false;
export function enableClustering(map, clusters, markers, filteredImages) {
    const zoomLevel = map.getZoom();
    const findCluster = clusterPoints(filteredImages, 0.5, zoomLevel);
    findCluster.forEach(cluster => {
        const center = centerCluster(cluster);
        const clusterMarker = L.circleMarker(
            [center.latitude, center.longitude],
            { radius: 10 + (cluster.length - 1) * 4, color: 'blue', fillOpacity: 0.5 }
        )
        .bindPopup(`Cluster of ${cluster.length} images`)
        .addTo(clusters);
        clusterMarker.on('click', () => {
            if (window.isExpanding) return;
            if (cluster.length <= 1) return;
            window.isExpanding = true;
            expandCluster(cluster, map , center , markers);
        });
    });
}

function expandCluster(cluster, map, center , markers) {
    map.setView([center.latitude, center.longitude], Math.min(map.getZoom() + 2 , 18));

    markers.eachLayer(marker => {
        const pos = marker.getLatLng();
        if (cluster.some(point => point.latitude === pos.lat && point.longitude === pos.lng)) {
            window.hiddenClusters.push(marker);
            map.removeLayer(marker);
        }
    });
    const count = cluster.length;
    const bounds = map.getBounds();
    const latDiff = bounds.getNorth() - bounds.getSouth();
    const pixelHeight = map.getSize().y;

    const latPerPixel = latDiff / pixelHeight;

    const R = latPerPixel * (40 + count * 2); // 40px + 2px par image

    cluster.forEach((point, index) => {
        const angle = (index / count) * 2 * Math.PI;
        const latOffset = R * Math.cos(angle);
        const lonOffset = R * Math.sin(angle);
        const icon = L.icon({
            iconUrl: window.appConfig.URL_for_images + point.file_path,
            iconSize: [80, 80],
            iconAnchor: [22, 94],
            popupAnchor: [-3, -76]
        });
        const marker = L.marker([point.latitude + latOffset, point.longitude + lonOffset], { icon })
            .bindPopup(createPopupHTML(point , window.appConfig.URL_for_images , window.appConfig.URL_for_view_image))
            .addTo(map);
        window.expandedMarkers.push(marker);
    });
    console.log(`Expanded cluster of ${count} points.`);
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