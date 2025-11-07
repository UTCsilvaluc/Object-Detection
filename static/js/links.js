import { degOfPente, getCenterMarker } from "./math.js";
import { getMarkerByLatLng } from "./utils.js";
export function createPolylineWithText(linesLayer , latlngs, map, link) {
    const randomColor = '#' + Math.floor(Math.random()*16777215).toString(16);
    const polyline = L.polyline(latlngs, { color: randomColor , weight: 4 , opacity: 0.7});
    latlngs.forEach((value , index) => {
        if (index === latlngs.length -1) return;
        const xCenter = latlngs[index][0] + latlngs[index + 1]?.[0];
        const yCenter = latlngs[index][1] + latlngs[index + 1]?.[1];
        const offset = 0.0005;
        const midPoint = [ (xCenter / 2) + offset , (yCenter / 2) + offset];
        const angle = degOfPente(map , latlngs[index][0], latlngs[index][1], latlngs[index + 1][0], latlngs[index + 1][1]);
        const labelHtml = `
            <div class="polyline-label" style="transform: rotate(${angle}deg)">${link.title}</div>
        `;
        const labelIcon = L.divIcon({
            className: 'polyline-label-icon',
            html: labelHtml
        });
        L.marker(midPoint, { icon: labelIcon , interactive: false}).addTo(linesLayer);
    });
    polyline.addEventListener('click', (e) => {
        polyline.openPopup();
    });
    return polyline;
}

export function addLinksToMap(linesLayer , map, links , markers , L) {
    linesLayer.clearLayers();
    links.forEach(link => {
        if (link.geometry) {
            const geo = link.geometry;
            let coordinates = [];

            if (Array.isArray(geo.coordinates) && geo.coordinates.length) {
                coordinates = geo.coordinates;
            }
            else if (geo.type === 'FeatureCollection' && Array.isArray(geo.features) && geo.features.length) {
                const feat = geo.features.find(f => f && f.geometry && Array.isArray(f.geometry.coordinates));
                if (feat) coordinates = feat.geometry.coordinates;
            }
            else if (geo.geojson && geo.geojson.type === 'FeatureCollection' && Array.isArray(geo.geojson.features)) {
                const feat = geo.geojson.features.find(f => f && f.geometry && Array.isArray(f.geometry.coordinates));
                if (feat) coordinates = feat.geometry.coordinates;
            }
            else {
                const findCoords = (obj) => {
                    if (!obj || typeof obj !== 'object') return null;
                    if (Array.isArray(obj.coordinates)) return obj.coordinates;
                    for (const k of Object.keys(obj)) {
                        const result = findCoords(obj[k]);
                        if (result) return result;
                    }
                    return null;
                };
                const found = findCoords(geo);
                if (found) coordinates = found;
            }
            if (coordinates.length && Array.isArray(coordinates[0]) && Array.isArray(coordinates[0][0])) {
                coordinates = coordinates[0];
            }
            if (!coordinates || !coordinates.length) {
                console.warn('No valid coordinates found for link.geometry:', geo);
            } else {
                const latlngs = coordinates.map(coord => [coord[1], coord[0]]);
                const polyline = createPolylineWithText(linesLayer ,latlngs, map, link);
                linesLayer.addLayer(polyline);
                linesLayer.addTo(map);
            }
        } else {
            const latlngs = link.endpoints.map(item => [item.latitude , item.longitude]);
            centerLatLngsWithAnchor(latlngs, markers, map, L);
            const polyline = createPolylineWithText(linesLayer,latlngs, map, link);
            linesLayer.addLayer(polyline);
            linesLayer.addTo(map);
        }
    });
}
/**
 * Centers the given latitude/longitude pairs based on the markers' positions.
 * @param {*} latlngs - The latitude/longitude pairs to center.
 * @param {*} markers - The markers layer.
 * @param {*} map - The map object.
 * @param {*} L - The Leaflet object.
 * @returns {Array} - The centered latitude/longitude pairs.
 */
function centerLatLngsWithAnchor(latlngs, markers , map , L) {
    latlngs.forEach((latlng , index) => {
        const marker = getMarkerByLatLng(markers, latlng[0], latlng[1]);
        if (marker) {
            const newLatLng = getCenterMarker(marker , map , L);
            latlngs[index] = [newLatLng.centerLatLng.lat , newLatLng.centerLatLng.lng];
        }
    });
    return latlngs;
}

export function removeLinkItem(id , type , iconEl) {
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

export function handleLinkCreationClick(item , marker , type='image' , URL_for_images='') {
    const iconEl = marker._icon;
    let src = '';
    let title = '';
    let id = '';
    if (iconEl) {
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

export function clearLinkCreationForm(markers , pointsLayer) {
    Array.from(document.getElementById('selected-items').children).forEach(child => {
        const id = child.dataset.id;
        const type = child.dataset.type;
        let iconEl = null;
        if (type === 'image') {
            markers.eachLayer(marker => {
                const latlng = marker.getLatLng();
                if (latlng.lat == parseFloat(child.getAttribute('latitude')) &&
                    latlng.lng == parseFloat(child.getAttribute('longitude'))) {
                    iconEl = marker._icon;
                }
            });
        } else if (type === 'point') {
            pointsLayer.eachLayer(marker => {
                const latlng = marker.getLatLng();
                if (latlng.lat == parseFloat(child.getAttribute('latitude')) &&
                    latlng.lng == parseFloat(child.getAttribute('longitude'))) {
                    iconEl = marker._icon;
                }
            });
        }
        if (iconEl) {
            if (type === 'image') {
                iconEl.style.border = 'none';
            } else {
                const divChild = iconEl.querySelector('div');
                if (divChild) {
                    divChild.style.border = '2px solid white';
                }
            }
        }
    });
    const container = document.getElementById('selected-items');
    container.innerHTML = '<div class="empty-msg">No items selected.</div>';
    document.getElementById('link-title').value = '';
    document.getElementById('link-description').value = '';
    document.getElementById('link-type').value = document.getElementById('link-type').options[0].value;
    document.getElementById('toggle-add-links').checked = false;
    window.enableLinkCreation = false;
    document.body.style.cursor = 'default';
    document.getElementById('link-panel').classList.toggle('hidden');
}