// static/js/map.js

// Imports 
import { enableClustering, disableClustering, showHeatmap, hideHeatmap, showTimeline, hideTimeline, showObjectLinks, hideObjectLinks } from './data_visualization.js';
import { removeSelectOptionFromAll , setTrashIcon , getMetadataFromFields , controlInputValues} from './utils.js';
import {addMetadataField , setCrossIcon} from './metadata.js';
import { apiPost , uploadAIImage} from './api.js';
import { createPopupHTML , createPopupPoint , createPopupAddPoint } from './popup.js';
// Main variables and map initialization

const URL_for_images = window.appConfig.URL_for_images;
const URL_for_view_image = window.appConfig.URL_for_view_image;
const URL_for_icons = window.appConfig.icons_path;
const images = window.appConfig.images;
const classes = window.appConfig.classes;
const icons = window.appConfig.icons;
const points = window.appConfig.points;
const crossIcon = window.appConfig.crossIcon;
const trashIcon = window.appConfig.trashIcon;

setCrossIcon(crossIcon);
setTrashIcon(trashIcon);

let pointsLayer = L.layerGroup();
let markers = L.layerGroup();
let clusters = L.layerGroup();
let checkClasses = [...classes];
let filteredImages = [...images];
let metadata_keys = window.appConfig.metadata_keys || [];
let metadata_keys_available = metadata_keys.slice();
let tempMarker = null;

window.filteredImages = filteredImages;
window.checkClasses = checkClasses;

// Initialize the map after getting the user's location

navigator.geolocation.getCurrentPosition(initMap , handleLocationError);

function initMap(position) {
    var userLat = position.coords.latitude || 34.33; 
    var userLon = position.coords.longitude || 134.05; 

    const map = L.map('map', { dragging: true }).setView([userLat, userLon], 13);

    // Set up the OpenStreetMap layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    handleActionPropagation(L);

    // Add a marker at the user's location
    L.marker([userLat, userLon])
        .addTo(map)
        .bindPopup('You are here!')
        .openPopup();

    markers.addTo(map);
    clusters.addTo(map);
    pointsLayer.addTo(map);

    // Add points to the map based on filtered images
    applyFilters();
    addPoints(pointsLayer, points);
    enableClustering(map, clusters, markers, filteredImages);
    enablePointAdding(map);
}

function handleLocationError(error) {
    console.warn(`ERROR(${error.code}): ${error.message}`);
    initMap({ coords: { latitude: 34.33, longitude: 134.05 } });
}

function handleActionPropagation(L) {
    // Prevent event propagation for filter actions
    const filterDiv = document.querySelector('.filter');
    L.DomEvent.disableClickPropagation(filterDiv);
    L.DomEvent.disableScrollPropagation(filterDiv);
}

function addPoints(layer, points) {
    let iconURL = URL_for_icons ;
    points.forEach(point => {
        iconURL = point.icon_svg_path ? (URL_for_icons + point.icon_svg_path) : null;
        const icon = L.divIcon({
            className: 'point-icon',
            html: getHTMLForSVGIcon(iconURL, point.color_hex || '#000000')
        });
        const popupContent = createPopupPoint(point);
        L.marker([point.latitude, point.longitude], { icon })
            .bindPopup(popupContent)
            .addTo(layer);
    });
}

/* Filter part control */
function toggleFilter(filterId) {
    const filterDiv = document.getElementById(filterId);
    if (filterDiv){
        filterDiv.classList.toggle('visible');
    }
}
window.toggleFilter = toggleFilter;
function applyFilters() {
    markers.clearLayers();
    filteredImages.forEach(img => {
        if (!img.latitude || !img.longitude) return;
        const icon = L.icon({
            iconUrl: URL_for_images + img.file_path,
            iconSize: [80, 80],
            iconAnchor: [22, 94],
            popupAnchor: [-3, -76]
        });
        L.marker([img.latitude, img.longitude], { icon })
            .bindPopup(createPopupHTML(img , URL_for_images , URL_for_view_image))
            .addTo(markers);
    });
}   
window.applyFilters = applyFilters;
function clearFilters() {
    checkClasses = [...classes];
    filteredImages = [...images];
    document.querySelectorAll('.class-list input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = true;
    });
    document.getElementById('start-date').value = '';
    document.getElementById('end-date').value = '';
    applyFilters();
}
window.clearFilters = clearFilters;
function checkAllFilters(image) {
    if (image.type && !checkClasses.includes(image.type)) {
        return false;
    }

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const imgDate = new Date(image.capture_date);

    if (isNaN(imgDate)) return false; 

    if (startDate && imgDate < new Date(startDate)) return false;
    if (endDate && imgDate > new Date(endDate)) return false;

    return true;
}

function refreshFilteredImages() {
    filteredImages = images.filter(checkAllFilters);
    applyFilters();
}

/* Event listeners */

document.querySelectorAll('.class-list input[type="checkbox"]').forEach(checkbox => {
    checkbox.addEventListener('change', (event) => {
        const className = event.target.value;
        if (event.target.checked) {
            checkClasses.push(className);
        } else {
            checkClasses = checkClasses.filter(c => c !== className);
        }
        refreshFilteredImages();
    });
});

document.querySelectorAll('.filter-class input[type="date"]').forEach(input => {
    input.addEventListener('change', () => {
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    if (startDate && endDate && new Date(startDate.value) > new Date(endDate.value)) {
        alert("Start date cannot be after end date.");
        startDate.value = '';
        return;
    }
        refreshFilteredImages();
    });
});

function addMetaData() {
    if (metadata_keys_available.length === 0) {
        alert("No more metadata keys available to add.");
        return;
    }
    addMetadataField(0);
}

function enablePointAdding(map) {
    map.on('click', function(e) {
        if (tempMarker) {
            map.removeLayer(tempMarker);
            document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
            document.getElementById('sidebar').classList.add('visible');
            tempMarker = null;
            return;
        }
        document.getElementById('sidebar').classList.remove('visible');
        const { lat, lng } = e.latlng;

        if (tempMarker) {
            map.removeLayer(tempMarker);
            document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
        }

        tempMarker = L.marker([lat, lng] , {
            icon: L.divIcon({
                className: 'temp-marker-icon',
                html: `<div style="width:24px; height:24px; background:#000000; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`,
            })
        }).addTo(map)
        const popupHTML = createPopupAddPoint(icons, URL_for_icons, lat, lng); 
            
        tempMarker.bindPopup(popupHTML).openPopup();
        document.getElementById('add-metadata-btn').addEventListener('click', () => {
            addMetaData();
        });
        document.getElementById('save-point-btn').addEventListener('click', async () => {
            await saveData(map, lat, lng);
        });
        document.getElementById('ai-upload-btn').addEventListener('click', () => {
            uploadAIImage(lat, lng);
        });
        document.querySelectorAll('.icon-preview .icon').forEach(img => {
            img.addEventListener('click', (e) => {
                document.querySelectorAll('.icon-preview .icon').forEach(i => i.classList.remove('selected'));
                const color = document.getElementById('point-color').value;
                e.target.classList.add('selected');
                const selectedIcon = e.target.getAttribute('src');
                const selectedIconElem = document.querySelector('.icon-preview .icon.selected');
                if (selectedIconElem) {
                    const color = document.getElementById('point-color').value;
                    tempMarker.setIcon(L.divIcon({
                        className: 'temp-marker-icon',
                        html: getHTMLForSVGIcon(selectedIcon, color)
                    }));
                } else {
                    tempMarker.setIcon(L.divIcon({
                        className: 'temp-marker-icon',
                        html: `<div style="width:24px; height:24px; background:${color}; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`,
                    }));
                }
            });
        });
        document.getElementById('point-color').addEventListener('change', (e) => {
            const color = e.target.value;
            const selectedIconElem = document.querySelector('.icon-preview .icon.selected');
            if (!selectedIconElem) {
                tempMarker.setIcon(L.divIcon({
                    className: 'temp-marker-icon',
                    html: `<div style="width:24px; height:24px; background:${color}; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`,
                }));
            } else {
                const iconUrl = selectedIconElem.getAttribute('src');
                tempMarker.setIcon(L.divIcon({
                    className: 'temp-marker-icon',
                    html: getHTMLForSVGIcon(iconUrl, color)
                }));
            }
        });
    });
}

async function saveData(map , lat , lng) {
    const name = document.getElementById('point-name').value;
    const description = document.getElementById('point-description').value;
    const location = document.getElementById('point-location').value;
    const color = document.getElementById('point-color').value;
    const selectedIconElem = document.querySelector('.icon-preview .icon.selected');
    let svgKey = null;
    let iconURL = null;
    controlInputValues(name, description, location);
    if (selectedIconElem) {
        svgKey = selectedIconElem.getAttribute('data-key');
        iconURL = selectedIconElem.getAttribute('src');
    }
    let metadata = getMetadataFromFields(document.querySelectorAll('.meta-field'));
    const point = {
        name,
        description,
        location,
        latitude: lat,
        longitude: lng,
        svgKey,
        color,
        metadata
    };
    const data = await apiPost('/save/save_point', {
        point: point
    });
    point.metadata = Object.entries(metadata).map(([key, value]) => ({ key, value }));
    if (data.status == 'success') {
        pointsLayer.addLayer(L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'temp-marker-icon',
            html: getHTMLForSVGIcon(iconURL, color)
        })
    }).bindPopup( createPopupPoint(point) ));
    } else {
        alert('Failed to save point: ' + data.error);
        return;
    }
    map.removeLayer(tempMarker);
    document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
}

function getHTMLForSVGIcon(iconURL, color) {
    if (!iconURL) return `<div style="width:24px; height:24px; background:${color}; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`
    const html = `
                    <div style=" 
                        width:24px;
                        height:24px;
                        background-color:${color};
                        -webkit-mask-image:url('${iconURL}');
                        mask-image:url('${iconURL}');
                        -webkit-mask-size:contain;
                        mask-size:contain;
                        -webkit-mask-repeat:no-repeat;
                        mask-repeat:no-repeat;
                        border: 2px solid white;
                        box-shadow:0 1px 2px rgba(0,0,0,.35);
                    ">
                    </div>
                `;
    return html;
}

/* Map feature toggles  event listener */
document.getElementById('toggle-cluster').addEventListener('change', (e) => {
    if (e.target.checked) enableClustering(map, clusters, markers, filteredImages);
    else disableClustering();
});

document.getElementById('toggle-heatmap').addEventListener('change', (e) => {
    if (e.target.checked) showHeatmap();
    else hideHeatmap();
});

document.getElementById('toggle-timeline').addEventListener('change', (e) => {
    if (e.target.checked) showTimeline();
    else hideTimeline();
});

document.getElementById('toggle-links').addEventListener('change', (e) => {
    if (e.target.checked) showObjectLinks();
    else hideObjectLinks();
});

document.getElementById('import-geojson').addEventListener('click', () => {
    alert("Feature to import GeoJSON coming soon!");
});

document.getElementById('import-other').addEventListener('click', () => {
    alert("Feature to import custom datasets coming soon!");
});

window.addEventListener("storage", async (event) => {
    if (event.key === 'upload_done') {
        const data = JSON.parse(event.newValue);
        const pending = localStorage.getItem('upload_pending');
        if (pending && pending.token === data.token) {
            const image = data.image;
            localStorage.removeItem('upload_pending');
            localStorage.removeItem('upload_done');
            images.push(image);
            filteredImages.push(image);
            applyFilters();
            alert("AI Image uploaded and added to the map successfully.");
        }
    }
});

/**
 * Cluster points based on proximity.
 * @param {Array<Object>} points - Array of points with {latitude, longitude}
 * @param {number} tolerance - Distance tolerance for clustering
 * @returns {Array<Array<Object>>} - Array of clusters
 */


//TODO: add heatmap, timeline, object links functionalities
/* 
Ranger le javascript dans des modules (leaflet, filters, map features, etc.)
Link between picture depending on detected objects
Cliquer sur la carte pour ajouter un point en base de donnée ou une image via upload 1) avec get auto des coord 2) avec formulaire manuel
Ajouter une sidebar avec la liste des images visibles sur la carte ? 
Image browser -> dynamic sidebar and zoom on map
Ajouter des SVG de choix à l'ajout des points sur la carte (restaurant, hotel, monument, repos etc.)

2)
Use other data or metadatas like objects etc for filtering or clustering...
view by metadata , by objects , historical period...

3) Outil de sélection de points / images pour faire des tracés entre les points sauvegardés sur le serveur ou base de donnée.
*/