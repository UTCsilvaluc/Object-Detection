import { handleLinkCreationClick } from "./links.js";

/**
 * Create the HTML content for the point popup.
 * @param {Object} point - The point object containing details.
 * @returns {string} The HTML content for the popup.
 */
export function createPopupPoint(point) {
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
    return popupContent;
}

/**
 * Create the HTML content for the image popup.
 * @param {Object} image - The image object containing details.
 * @returns {string} The HTML content for the popup.
 */
export function createPopupHTML(image , URL_for_images , URL_for_view_image) {
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

/**
 * Create the HTML content for the add point popup.
 * @param {Array<Object>} icons - Array of icon objects.
 * @param {string} URL_for_icons - Base URL for icons.
 * @param {number} lat - Latitude of the point.
 * @param {number} lng - Longitude of the point.
 * @returns {string} The HTML content for the popup.
 */    
export function createPopupAddPoint(icons, URL_for_icons, lat, lng) {
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
    return popupHTML;
}        

export function addPoint(L , point, icon, layer , popupContent) {
    L.marker([point.latitude, point.longitude], { icon })
        .bindPopup(popupContent)
        .addTo(layer)
        .addEventListener('click', (event) => {
            if (window.enableLinkCreation) {
                handleLinkCreationClick(point , event.target , 'point');
            } 
        });
}

export function popupPolylineLink(link) {
    const title = link.title || "Unnamed Link";
    const desc = link.description || "No description available";
    const type = link.link_type || "Unknown type";
    const date = link.created_at ? new Date(link.created_at).toLocaleDateString() : "Unknown date";

    let metadataHTML = "";
    if (link.metadata && link.metadata.length > 0) {
        metadataHTML = `
        <h4 style="margin-top:6px;">Metadata</h4>
        <ul style="padding-left:18px; margin:3px 0;">
            ${link.metadata.map(meta => `
                <li><strong>${meta.key}:</strong> ${meta.value}</li>
            `).join("")}
        </ul>`;
    } else {
        metadataHTML = `<p><em>No metadata</em></p>`;
    }
    return `
        <div style="font-family:Arial, sans-serif; font-size:13px; line-height:1.35; max-width:220px;">
            <h3 style="margin:0 0 4px 0; font-size:16px;">${title}</h3>
            <p style="margin:2px 0;"><strong>Description:</strong><br>${desc}</p>
            <p style="margin:2px 0;"><strong>Type:</strong> ${type}</p>
            <p style="margin:2px 0;"><strong>Created:</strong> ${date}</p>
            ${metadataHTML}
        </div>
    `;
}

export function getHTMLForSVGIcon(iconURL, color) {
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

export function createPopUpForObjectLinks(objectData, URL_for_image) {
    return Object.values(objectData)
        .map(obj => `
            <div class="popup-content">
                <img src="${URL_for_image + obj.cropped_file_path}" width="100" />
                <h3>Class: ${obj.class || 'Unknown'}</h3>
                <p><strong>Confidence Score:</strong> ${obj.confidence_score ?? 'N/A'}</p>
                <p><strong>Dimensions:</strong> ${obj.width ?? 'N/A'} x ${obj.height ?? 'N/A'}</p>
                <p><strong>Coordinates in Image:</strong> (${obj.coords_x ?? 'N/A'}, ${obj.coords_y ?? 'N/A'})</p>
            </div>
        `)
        .join('');
}

