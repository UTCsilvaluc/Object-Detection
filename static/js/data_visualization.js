import { clusterPoints, centerCluster , getMaxPixelRadius , destinationPoint , metersFromPixels} from './math.js';
import { getCenterMarker } from './math.js';
import { createPopupHTML } from './popup.js';
import { getMarkerByLatLng } from './utils.js';
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

function getSafeZoom(map, center, pixelRadius, imageSize = 80 , count , markers) {
    let bestZoom = map.getZoom();
    const boundsMap = map.getBounds();
    const screen = { w: map.getSize().x, h: map.getSize().y };
    const R = (imageSize*Math.sqrt(2)) / 2;
    const longueur = metersFromPixels(imageSize , center.latitude , bestZoom);
    for (let z = bestZoom; z <= 18; z++) {
        const R = metersFromPixels(pixelRadius, center.latitude, z);
        const teta = (longueur/R)*(180/Math.PI);
        if (360 / (teta*count) < 0.5) {
            break;
        }
        bestZoom = z;
    }
    return bestZoom;
}

function expandCluster(cluster, map, center, markers) {
    window.expandedMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    window.expandedMarkers = [];
    markers.eachLayer(marker => {
        window.hiddenClusters.push(marker);
        map.removeLayer(marker);
    });
    window.circle && map.removeLayer(window.circle);

    const count = cluster.length;
    const desiredPixelRadius = 40 + count * 6;

    const maxPixelRadius = getMaxPixelRadius(map, center);
    const pixelRadius = Math.min(desiredPixelRadius, maxPixelRadius);

    const safeZoom = getSafeZoom(map, center, pixelRadius , 80 , count , markers);

    map.setView([center.latitude, center.longitude], safeZoom);

    const R = metersFromPixels(pixelRadius, center.latitude, safeZoom);
    const circle = L.circle([center.latitude, center.longitude], {
        radius: R,
        color: 'red',
        fillOpacity: 0.1
    }).addTo(map);
    window.circle = circle;
    cluster.forEach((point, index) => {
        const angleDeg = (index / count) * 360;
        const [lat, lon] = destinationPoint(center.latitude, center.longitude, R, angleDeg);

        const icon = L.icon({
            iconUrl: window.appConfig.URL_for_images + point.file_path,
            iconSize: [80, 80],
            iconAnchor: [22, 94],
            popupAnchor: [-3, -76]
        });

        const marker = L.marker([lat, lon], { icon })
            .bindPopup(createPopupHTML(point, window.appConfig.URL_for_images, window.appConfig.URL_for_view_image))
            .addTo(map);

        window.expandedMarkers.push(marker);
    });
    window.expandedMarkers.forEach(marker => {
        const d1 = map.distance(marker.getLatLng(), circle.getLatLng());
        const p1 = map.containerPointToLayerPoint(map.latLngToContainerPoint(marker.getLatLng()));
        window.expandedMarkers.forEach(m => {
            if (m !== marker) {
                const d2 = map.distance(m.getLatLng(), circle.getLatLng());
                const p2 = map.containerPointToLayerPoint(map.latLngToContainerPoint(m.getLatLng()));
                if (d1 < d2 && p1.distanceTo(p2) < 80) {
                    map.setView([center.latitude, center.longitude], map.getZoom() + 1);
                }
            }
        });
    });
    window.isExpanding = false;
}

export function showObjectLinks(markers , L , objectLinks , map , objectLinesLayer) {
    objectLinesLayer.clearLayers();
    Object.values(objectLinks).forEach(key => {
        const latlngs = [];
        const randomColor = '#' + Math.floor(Math.random()*16777215).toString(16);
        key.forEach(point => {
            if (point.latitude && point.longitude) {
                const marker = getMarkerByLatLng(markers , point.latitude , point.longitude);
                const center = getCenterMarker(marker , map , L);
                latlngs.push([center.centerLatLng.lat, center.centerLatLng.lng]);
            }
        });
        var polyline = L.polyline(latlngs, {color: randomColor}).addTo(objectLinesLayer);
    });
    map.addLayer(objectLinesLayer);
}

export function hideObjectLinks(map , objectLinesLayer) {
    objectLinesLayer.clearLayers();
    map.removeLayer(objectLinesLayer);
}

export function disableClustering(map, clusters, markers, filteredImages) {
    window.expandedMarkers.forEach(m => map.removeLayer(m));
    window.expandedMarkers = [];
    window.hiddenClusters.forEach(c => map.addLayer(c));
    window.hiddenClusters = [];
    window.circle && map.removeLayer(window.circle);
    clusters.clearLayers();
}