// static/js/map.js

// Imports 
import { enableClustering , showObjectLinks , hideObjectLinks} from './data_visualization.js';
import { removeSelectOptionFromAll , setTrashIcon , getMetadataFromFields , controlInputValues} from './utils.js';
import {addMetadataField , setCrossIcon} from './metadata.js';
import { apiPost , uploadAIImage} from './api.js';
import { createPopupHTML , createPopupPoint , createPopupAddPoint , addPoint} from './popup.js';
// Main variables and map initialization

const $ = window.jQuery;

const URL_for_images = window.appConfig.URL_for_images;
const URL_for_view_image = window.appConfig.URL_for_view_image;
const URL_for_icons = window.appConfig.icons_path;
const images = window.appConfig.images;
const classes = window.appConfig.classes;
const objectLinks = window.appConfig.objects_linked || [];
const icons = window.appConfig.icons;
const points = window.appConfig.points;
const crossIcon = window.appConfig.crossIcon;
const trashIcon = window.appConfig.trashIcon;

setCrossIcon(crossIcon);
setTrashIcon(trashIcon);

let map = null;
let pointsLayer = L.layerGroup();
let markers = L.layerGroup();
let clusters = L.layerGroup();
let linesLayer = L.layerGroup();
window.circle = L.layerGroup();
let checkClasses = [...classes];
let filteredImages = [...images];
let metadata_keys = window.appConfig.metadata_keys || [];
let metadata_keys_available = metadata_keys.slice();
let tempMarker = null;

window.filteredImages = filteredImages;
window.checkClasses = checkClasses;
window.enableLinkCreation = false;

// Initialize the map after getting the user's location

navigator.geolocation.getCurrentPosition(initMap , handleLocationError);

function initMap(position) {
    var userLat = position.coords.latitude || 34.33; 
    var userLon = position.coords.longitude || 134.05; 

    map = L.map('map', { dragging: true }).setView([userLat, userLon], 13);

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
    enableZoomClustering(map);
    enableClustering(map, clusters, markers, filteredImages);
    enableMapStorageListener(map);
    enablePointAdding(map);
    buildTimelineFromFilteredImages(filteredImages , URL_for_images);
}

function handleLocationError(error) {
    console.warn(`ERROR(${error.code}): ${error.message}`);
    initMap({ coords: { latitude: 34.33, longitude: 134.05 } });
}

function handleActionPropagation(L) {
    // Prevent event propagation for filter actions
    const filterDiv = document.querySelector('.filter');
    const linkPanelDiv = document.getElementById('link-panel');
    L.DomEvent.disableClickPropagation(filterDiv);
    L.DomEvent.disableScrollPropagation(filterDiv);
    L.DomEvent.disableClickPropagation(linkPanelDiv);
    L.DomEvent.disableScrollPropagation(linkPanelDiv);
}

function addPoints(layer, points) {
    let iconURL = URL_for_icons ;
    points.forEach(point => {
        iconURL = point.icon_svg_path ? (URL_for_icons + point.icon_svg_path) : null;
        const icon = L.divIcon({
            className: 'point-icon',
            html: getHTMLForSVGIcon(iconURL, point.color_hex || '#000000')
        });
        point.iconURL = iconURL;
        const popupContent = createPopupPoint(point);
        addPoint(L, point, icon, layer , popupContent);
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
    const sidebar = document.getElementById('sidebar-images');
    markers.clearLayers();
    const thumbs = sidebar.querySelector('.image-thumbnails');
    if (thumbs) {
            thumbs.innerHTML = '';
        }
    filteredImages.forEach(img => {
        let thumbDiv = document.createElement('div');
        thumbDiv.className = 'image-thumbnail';
        thumbDiv.setAttribute('data-longitude', img.longitude);
        thumbDiv.setAttribute('data-latitude', img.latitude);
        thumbDiv.innerHTML = `
            <img src="${URL_for_images + img.file_path}" alt="${img.title}">
            <div class="data-image">
                <span class="image-title"><strong>Title:</strong> ${img.title}</span>
                <span class="image-class"><strong>Description:</strong> ${img.description}</span>
                <span class="image-date"><strong>Class:</strong> ${img.type}</span>
            </div>
        `;
        if (thumbs) {
            thumbs.appendChild(thumbDiv);
            thumbDiv.addEventListener('click', () => {
                map.setView([img.latitude, img.longitude], 15);
            });
        }
        if (!img.latitude || !img.longitude) return;
        const icon = L.icon({
            iconUrl: URL_for_images + img.file_path,
            iconSize: [80, 80],
            iconAnchor: [22, 94],
            popupAnchor: [-3, -76]
        });
        L.marker([img.latitude, img.longitude], { icon })
            .bindPopup(createPopupHTML(img , URL_for_images , URL_for_view_image))
            .addTo(markers)
            .addEventListener('click', (e) => {
                if (window.enableLinkCreation) {
                    handleLinkCreationClick(img , e.target);
                }   
            });
    });
    buildTimelineFromFilteredImages(filteredImages , URL_for_images);
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

    if (!isNaN(imgDate)){
        if (startDate && imgDate < new Date(startDate)) return false;
        if (endDate && imgDate > new Date(endDate)) return false;
    }
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

function addMetaData(id) {
    if (metadata_keys_available.length === 0) {
        alert("No more metadata keys available to add.");
        return;
    }
    addMetadataField(id);

}

function enableZoomClustering(map) {
    map.on('zoomend', () => {
        if (!document.getElementById('toggle-cluster').checked) return;
        clusters.clearLayers();
        enableClustering(map, clusters, markers, filteredImages);
    });
}

function enableMapStorageListener(map) {
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
                if (tempMarker) {
                    map.removeLayer(tempMarker);
                    document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
                    document.getElementById('sidebar').classList.add('visible');
                    tempMarker = null;
                }
            }
        }
    });
}

function enablePointAdding(map) {
    map.on('click', function(e) {
        if (window.enableLinkCreation) return;
        if (tempMarker) {
            map.removeLayer(tempMarker);
            document.querySelectorAll('.popup-add-point').forEach(el => el.remove());
            if (document.getElementById('toggle-filters').checked) {
                document.getElementById('sidebar').classList.add('visible');
            }
            tempMarker = null;
            return;
        }   
        if (window.expandedMarkers.length > 0) {
            disableClustering();
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
            addMetaData(0);
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
    const metaDataContainer = document.getElementById('meta-0');
    let metadata = getMetadataFromFields(metaDataContainer.querySelectorAll('.meta-field'));
    const point = {
        name,
        description,
        location,
        latitude: lat,
        longitude: lng,
        svgKey,
        color,
        metadata, 
        iconURL
    };
    const data = await apiPost('/save/save_point', {
        point: point
    });
    point.metadata = Object.entries(metadata).map(([key, value]) => ({ key, value }));
    if (data.status == 'success') {
        addPoint(L , point, L.divIcon({
            className: 'point-icon',
            html: getHTMLForSVGIcon(iconURL, color)
        }) , pointsLayer , createPopupPoint(point) , iconURL);
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
function disableClustering() {
    window.expandedMarkers.forEach(m => map.removeLayer(m));
    window.expandedMarkers = [];
    window.hiddenClusters.forEach(c => map.addLayer(c));
    window.hiddenClusters = [];
    window.circle && map.removeLayer(window.circle);
    clusters.clearLayers();
    enableClustering(map, clusters, markers, filteredImages);
}
/* Map feature toggles  event listener */
document.getElementById('toggle-cluster').addEventListener('change', (e) => {
    if (e.target.checked) enableClustering(map, clusters, markers, filteredImages);
    else {
        disableClustering();
    }
});

document.getElementById('toggle-timeline').addEventListener('change', (e) => {
    if (e.target.checked) {
        document.getElementById('sidebar-timeline').classList.add('visible');
        document.getElementById('sidebar-timeline').style.width = '50%';
    } else {
        document.getElementById('sidebar-timeline').classList.remove('visible');
    }
});

document.getElementById('toggle-links').addEventListener('change', (e) => {
    if (e.target.checked) showObjectLinks(objectLinks , map , linesLayer);
    else hideObjectLinks(map , linesLayer);
});

document.getElementById('import-geojson').addEventListener('click', () => {
    alert("Feature to import GeoJSON coming soon!");
});

document.getElementById('import-other').addEventListener('click', () => {
    alert("Feature to import custom datasets coming soon!");
});

document.getElementById('toggle-sidebar').addEventListener('click', () => {
    const sidebar = document.querySelector('.map-controller .sidebar');
    sidebar.classList.toggle('visible');
});

document.querySelectorAll('.image-thumbnail').forEach(div => {
    div.addEventListener('click', (e) => {
        const longitude = parseFloat(div.getAttribute('data-longitude'));
        const latitude = parseFloat(div.getAttribute('data-latitude'));
        map.setView([latitude, longitude], 15);
    });
});

document.getElementById('add-metadata-link').addEventListener('click', () => {
    addMetaData(1);
});

document.getElementById("sidebar-timeline").addEventListener("scroll", (e) => {
    const activeItem = document.querySelector(".timeline-item--active");
    if (activeItem) {
        const lat = parseFloat(activeItem.getAttribute("data-latitude"));
        const lon = parseFloat(activeItem.getAttribute("data-longitude"));
        if (!isNaN(lat) && !isNaN(lon)) {
            map.setView([lat, lon], map.getZoom());
        }
    }
});

document.getElementById('toggle-filters').addEventListener('change', (e) => {
    const filterDiv = document.querySelector('.filter');
    if (e.target.checked) {
        filterDiv.classList.add('visible');
    } else {
        filterDiv.classList.remove('visible');
    }
});

document.getElementById('toggle-add-links').addEventListener('change', (e) => {
    if (e.target.checked) {
        window.enableLinkCreation = true;
        document.body.style.cursor = 'crosshair';
        document.getElementById('toggle-filters').checked = false;
        document.querySelector('.filter').classList.remove('visible');
        document.getElementById('link-panel').classList.toggle('hidden');
        //alert("Link creation enabled. Click on two points or more to create a link between them.");
    } else {
        window.enableLinkCreation = false;
        document.body.style.cursor = 'default';
        //alert("Link creation disabled.");
    }
});
    
document.getElementById('link-type').addEventListener('change', async (e) => {
    if (e.target.value === '__new__') {
        const key = prompt("Enter the key of the new link type:");
        const label = prompt("Enter the label of the new link type:");
        if (key && label) {
            const data = await apiPost('/save/save_link_type', {
                key: key,
                label: label
            });
            if (data.success) {
                const option = document.createElement('option');
                option.value = key;
                option.text = label;
                e.target.add(option, e.target.options[e.target.options.length - 1]);
                e.target.value = key;
            } else {
                alert("Failed to add new link type: " + data.message);
                e.target.value = e.target.options[0].value;
            }
        } else {
            e.target.value = e.target.options[0].value;
        }
    }
});

document.getElementById('save-link').addEventListener('click', async () => {
    const title = document.getElementById('link-title').value;
    const description = document.getElementById('link-description').value;
    const linkType = document.getElementById('link-type').value;
    const linkTitleInput = document.getElementById('link-title').value;
    controlInputValues(title, description , linkType , linkTitleInput);
    const container = document.getElementById('selected-items');
    if (container.childElementCount < 2) {
        alert("Please select at least two items to create a link.");
        return;
    }
    const items = Array.from(container.children);
    const metaDataContainer = document.getElementById('meta-1');
    let metadata = getMetadataFromFields(metaDataContainer.querySelectorAll('.meta-field'));
    const GeoJSON = await getGeoJSONFileInput();
    const linkData = {
        title,
        description,
        link_type: linkType,
        items: items.map(item => ({
            id: item.dataset.id,
            entity_type: item.dataset.type,
            latitude: parseFloat(item.getAttribute('latitude')),
            longitude: parseFloat(item.getAttribute('longitude'))
        })),
        metadata,
        geojson: GeoJSON ? GeoJSON.geojson : null
    };
    const data = await apiPost('/save/save_link', {
        link: linkData
    });
    if (data.status == 'success') {
        alert("Link saved successfully.");
        container.innerHTML = '<div class="empty-msg">No items selected.</div>';
        document.getElementById('link-title').value = '';
        document.getElementById('link-description').value = '';
        document.getElementById('link-type').value = document.getElementById('link-type').options[0].value;
        disableClustering();
        document.getElementById('toggle-add-links').checked = false;
        window.enableLinkCreation = false;
        document.body.style.cursor = 'default';
        document.getElementById('link-panel').classList.toggle('hidden');
    } else {
        alert('Failed to save link: ' + data.error);
        return;
    }
});

async function getGeoJSONFileInput() {
    const input = document.getElementById('geojson-input');
    const file = input.files[0];
    const statusBox = document.getElementById('geojson-status');
    if (!file) return;
    try {
        const text = await file.text();
        const geojson = JSON.parse(text);
        if (geojson.type !== 'FeatureCollection' || !geojson.features || geojson.features.length === 0) {
            statusBox.innerText = "Invalid GeoJSON format.";
            return;
        } 
        const lineFeature = geojson.features.find(f => f.geometry && f.geometry.type === 'LineString');
        if (!lineFeature) {
            statusBox.innerText = "No LineString feature found in GeoJSON.";
            return;
        }
        const coordinates = lineFeature.geometry.coordinates;
        const latlngs = coordinates.map(coord => [coord[1], coord[0]]);
        const polyline = L.polyline(latlngs, { color: 'blue' , weight: 4 , opacity: 0.7});
        showGeoStatus("GeoJSON LineString path loaded successfully!" , "success");
        return {geojson , polyline};
    }
    catch (error) {
        statusBox.innerText = "Failed to load GeoJSON: " + error.message;
        showGeoStatus("Failed to load GeoJSON: " + error.message , "error");
        return null;
    }
}

document.getElementById('geojson-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const statusBox = document.getElementById('geojson-status');
    if (!file) return;
    try {
        const text = await file.text();
        const geojson = JSON.parse(text);
        if (geojson.type !== 'FeatureCollection' || !geojson.features || geojson.features.length === 0) {
            statusBox.innerText = "Invalid GeoJSON format.";
            return;
        } 
        const lineFeature = geojson.features.find(f => f.geometry && f.geometry.type === 'LineString');
        if (!lineFeature) {
            statusBox.innerText = "No LineString feature found in GeoJSON.";
            return;
        }
        const coordinates = lineFeature.geometry.coordinates;
        const latlngs = coordinates.map(coord => [coord[1], coord[0]]);
        const polyline = L.polyline(latlngs, { color: 'blue' , weight: 4 , opacity: 0.7}).addTo(map);
        map.fitBounds(polyline.getBounds());
        showGeoStatus("GeoJSON LineString path loaded successfully!" , "success");
    }
    catch (error) {
        statusBox.innerText = "Failed to load GeoJSON: " + error.message;
        showGeoStatus("Failed to load GeoJSON: " + error.message , "error");
        return;
    }
    statusBox.innerText = "GeoJSON loaded successfully!";
});
function showGeoStatus(msg, type) {
    const box = document.getElementById('geojson-status');
    box.className = `geojson-status ${type}`;
    box.textContent = msg;
    box.style.display = 'block';
}
/* Link creation functionality */

function handleLinkCreationClick(item , marker , type='image') {
    const iconEl = marker._icon;
    let src = '';
    let title = '';
    let id = '';
    if (iconEl) {
        //si img ou si div
        if (type === 'image') {
            src = (URL_for_images + item.file_path);
            title = item.title;
            id = item.image_id;
            iconEl.style.border = '3px solid red';
        } else {
            const divChild = iconEl.querySelector('div');
            src = item.iconURL;
            title = item.name;
            id = item.point_id;
            type = 'point';
            if (divChild) {
                divChild.style.border = '7px solid black';
            }
        }        
    }
    const container = document.getElementById('selected-items');
    if (Array.from(container.children).some(child => child.dataset.id == id)) {
        if (confirm("This item is already selected for linking. Do you want to remove it? (yes/no)")) {
            removeLinkItem(id , type , iconEl);
        }
        return;
    }
    document.querySelector(".empty-msg")?.remove();
    const div = document.createElement('div');
    div.className = 'item';
    div.draggable = true;
    div.setAttribute('latitude', item.latitude);
    div.setAttribute('longitude', item.longitude);
    div.innerHTML = `
        <img src="${src}" alt="${title}" width="50" height="50"/>
        <span class="title">${title}</span>
        <span class="remove-item">&times;</span>
    `; 
    div.dataset.id = id;
    div.dataset.type = type;
    container.appendChild(div);
    div.querySelector('.remove-item').addEventListener('click', () => {
        removeLinkItem(id , type , iconEl);
    });
    enableDragSort();
}
window.handleLinkCreationClick = handleLinkCreationClick;

function enableDragSort() {
    const items = document.querySelectorAll('.selected-items .item');

    items.forEach(item => {
        item.addEventListener('dragstart', () => item.classList.add("dragging"));
        item.addEventListener('dragend', () => item.classList.remove("dragging"));
    });

    const zone = document.querySelector('.selected-items');
    zone.addEventListener('dragover', e => {
        e.preventDefault();
        const dragging = document.querySelector(".dragging");
        const after = [...zone.querySelectorAll(".item:not(.dragging)")].find(i => {
            const box = i.getBoundingClientRect();
            return e.clientY < box.top + box.height / 2;
        });
        after ? zone.insertBefore(dragging, after) : zone.appendChild(dragging);
    });
}

function removeLinkItem(id , type , iconEl) {
    const container = document.getElementById('selected-items');
    Array.from(container.children).find(child => parseInt(child.dataset.id) == parseInt(id)).remove();
    if (type === 'image') {
        iconEl.style.border = 'none';
    } else {
        const divChild = iconEl.querySelector('div');
        if (divChild) {
            divChild.style.border = '2px solid white';
        }
    }
}

//TODO: timeline, object links functionalities
/* 
Link between picture depending on detected objects
2)
Use other data or metadatas like objects etc for filtering or clustering...
view by metadata , by objects , historical period...

3) Outil de sélection de points / images pour faire des tracés entre les points sauvegardés sur le serveur ou base de donnée.

Timeline : Outil de sélection d'objet parmi le temps ? Reconstruire l'historique d'un objet au travers du temps, déplacements etc ?
Par exemple apparait en 1940 à telle endroit, puis en 1950 à un autre endroit etc...
OU
Timeline globale des images sur la carte ? Filtrer les images visibles sur la carte en fonction d'une timeline ? avec auto play 

Option qui permettrait de lier des images / points entre eux avec metadatas , permettrait de tracer des chemins, itinéraires etc...

*/