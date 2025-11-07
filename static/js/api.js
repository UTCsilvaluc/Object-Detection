// static/js/api.js
import { controlInputValues , getMetadataFromFields} from "./utils.js";
import { addPoint , getHTMLForSVGIcon , createPopupPoint} from "./popup.js";
export async function apiPost(url , body){
    try {
        const res = await fetch(url , {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'An error occurred');
        }
        return data;
    } catch (error) {
        console.error("API POST error:", error);
        alert("An error occurred: " + error.message);
        return null;
    }
}
window.apiPost = apiPost;

export function uploadAIImage(lat, lng) {
    const token = crypto.randomUUID();
    if (localStorage) { 
        localStorage.setItem('upload_pending', JSON.stringify({
            token: token,
            latitude: lat,
            longitude: lng
        }));
        const url = `/?token=${token}&latitude=${lat}&longitude=${lng}`;
        window.open(url, '_blank');
    } else {
        alert("Your browser does not support localStorage. Cannot proceed with AI image upload.");
    }
}   
window.uploadAIImage = uploadAIImage;

export async function saveData(map , lat , lng , tempMarker , pointsLayer) {
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
window.saveData = saveData;