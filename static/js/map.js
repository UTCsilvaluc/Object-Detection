// static/js/map.js

// Imports 
import { enableClustering, disableClustering, showHeatmap, hideHeatmap, showTimeline, hideTimeline, showObjectLinks, hideObjectLinks } from './data_visualization.js';
import { removeSelectOptionFromAll , setTrashIcon} from './utils.js';
import {addMetadataField , setCrossIcon} from './metadata.js';
import { apiPost } from './api.js';
// Main variables and map initialization

const URL_for_images = window.appConfig.URL_for_images ;
const URL_for_view_image = window.appConfig.URL_for_view_image;
const URL_for_icons = window.appConfig.icons_path ;
const images = window.appConfig.images ;
const classes = window.appConfig.classes;
const icons = window.appConfig.icons ;
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
    points.forEach(point => {
        const icon = L.divIcon({
            className: 'point-icon',
            html: getHTMLForSVGIcon(URL_for_icons + point.icon_svg_path, point.color_hex || '#000000')
        });
        const popupContent = `
            <h3>Place: ${point.name || 'Unnamed Point'}</h3>
            <p><strong>Description:</strong> ${point.description || 'No description available'}</p>
            <p><strong>Location:</strong> ${point.location || 'Unknown'}</p>
            <p><strong>Coordinates:</strong> (${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)})</p>
            ${point.metadata && point.metadata.length > 0 ? '<h4>Metadata:</h4>' : ''}
            <ul>
                ${point.metadata.map(meta => `<li><strong>${meta.key}:</strong> ${meta.value}</li>`).join('')}
            </ul>
        `;
        L.marker([point.latitude, point.longitude], { icon })
            .bindPopup(popupContent)
            .addTo(layer);
    });
}

/**
 * Create the HTML content for the image popup.
 * @param {Object} image - The image object containing details.
 * @returns {string} The HTML content for the popup.
 */
function createPopupHTML(image) {
    return `
        <div class="popup-content">
            <img src="${URL_for_images + image.file_path}" width="100" />
            <h3>${image.title || 'Untitled'}</h3>
            <p><strong>Type:</strong> ${image.type || 'Untitled'}</p>
            <p><strong>Description:</strong> ${image.description || 'No description available'}</p>
            <p><strong>Capture Date:</strong> ${image.capture_date || 'Unknown'}</p>
            <p><strong>Location:</strong> ${image.location_name || 'Unknown'}</p>
            <p><strong>Coordinates:</strong> (${image.latitude.toFixed(5)}, ${image.longitude.toFixed(5)})</p>
            <p><strong>Source:</strong> ${image.source_type || 'Unknown'}</p>
            <button onclick="window.open('${URL_for_view_image.replace('0', image.image_id)}')">
                View Details
            </button>
        </div>
    `;
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
            .bindPopup(createPopupHTML(img))
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
        const { lat, lng } = e.latlng;

        if (tempMarker) {
            map.removeLayer(tempMarker);
            document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
        }

        tempMarker = L.marker([lat, lng] , {
            // faire un div marker diaming circle with border and color picker
            icon: L.divIcon({
                className: 'temp-marker-icon',
                html: `<div style="width:24px; height:24px; background:#000000; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`,
            })
        }).addTo(map)
        const popupHTML = `
            <div class="popup-add-point">
                <h3>Add New Image</h3>
                <div class="popup-columns">
                    <div class="popup-left">
                        <label for="point-name"> Name: </label>
                        <input type="text" id="point-name" name="point-name" placeholder="Enter point name" required/><br/>

                        <label for="point-description"> Description: </label>
                        <textarea id="point-description" name="point-description" placeholder="Enter description" required></textarea><br/>

                        <label for="point-location"> Location: </label>
                        <input type="text" id="point-location" name="point-location" placeholder="Enter location name" /><br/>

                        <p for="point-icon"> Icon: </p>
                        <div class="icon-preview" id="icon-preview"> 
                            ${icons.map(icon => `<img class="icon" src="${URL_for_icons + icon.svg_path}" alt="${icon.label}" data-key="${icon.key}" width="24" height="24" style="margin-right:5px; fill:red;" />`).join('')}
                        </div>

                        <label for="point-color"> Color: </label>
                        <input type="color" id="point-color" name="point-color" value="#000000" /><br/>

                        <div class="metadata-section" id="meta-0"></div>

                        <button id="add-metadata-btn">+ Add Metadata</button>
                        <button id="save-point-btn">Save Point</button>
                    </div>
                </div>
                <br>
                <div class="popup-right">
                    <h4>AI Image import</h4>
                    <p>Import an image detected with AI object detection at this location.</p>
                    <button id="ai-upload-btn" onclick="uploadAIImage(${lat}, ${lng})">Upload AI Image</button>
                    <div id="image-preview"></div>
                </div>
            </div>
        `;        
        
        tempMarker.bindPopup(popupHTML).openPopup();
        document.getElementById('add-metadata-btn').addEventListener('click', () => {
            addMetaData();
        });
        document.getElementById('save-point-btn').addEventListener('click', async () => {
            await saveData(map, lat, lng);
        });
        document.getElementById('ai-upload-btn').addEventListener('click', () => {
            alert("Feature to upload AI image coming soon!");
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
    let iconURL = null;
    if (selectedIconElem) {
        iconURL = selectedIconElem.getAttribute('src');
    }
    let metadata = {};
    document.querySelectorAll('.meta-field').forEach(field => {
        const key = field.querySelector('select').value;
        const value = field.querySelector('input').value;
        if (key && value) {
            metadata[key] = value;
        }
    });
    const svgKey = selectedIconElem.getAttribute('data-key');
    const data = await apiPost('/save/save_point', {
        point: {
            name,
            description,
            location,
            latitude: lat,
            longitude: lng,
            svgKey,
            iconURL,
            color,
            metadata
        }
    });
    if (data.status == 'success') {
        pointsLayer.addLayer(L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'temp-marker-icon',
            html: iconURL ? getHTMLForSVGIcon(iconURL, color) : `<div style="width:24px; height:24px; background:${color}; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`,
        })
        }).bindPopup(`
            <h3>${name}</h3>
            <p>${description}</p>
            <p><strong>Location:</strong> ${location}</p>
            <p><strong>Coordinates:</strong> (${lat.toFixed(5)}, ${lng.toFixed(5)})</p>
        `));
    } else {
        alert('Failed to save point: ' + data.error);
        return;
    }
    map.removeLayer(tempMarker);
    document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
}

function getHTMLForSVGIcon(iconURL, color) {
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