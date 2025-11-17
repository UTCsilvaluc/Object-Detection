// static/js/utils.js

export const $ = (sel) => document.querySelector(sel);
export const $$ = (sel) => document.querySelectorAll(sel);

window.$ = $;
window.$$ = $$;
let trashIcon = null;
function setTrashIcon(icon) {
    trashIcon = icon;
}
export { setTrashIcon };

if (!window.AppState) {
    window.AppState = {};
}

export function toggleAccordion(id) {
    const content = document.getElementById(id);
    if (!content) return;
    content.style.display = (content.style.display === "block") ? "none" : "block";
}
window.toggleAccordion = toggleAccordion;

export function refreshImage(img = $('.image-box img')) {
    if (!img) return;
    img.src = img.src.split('?')[0] + '?t=' + new Date().getTime();
}
window.refreshImage = refreshImage;
export function refreshCount(numObjects) {
    const counter = $('#num-objects');
    if (!counter) return;
    counter.innerText = counter.innerText.replace(/\d+/, numObjects);
}
window.refreshCount = refreshCount;
export function resetMetaForm(){
    let button = $(`button[onclick="createNewMetadata(this)"]`);
    button.innerHTML = button.innerHTML.replace('-', '+');
    $(`input[name="new_metadata_key"]`).value = "";
    $(`input[name="new_metadata_key"]`).required = false;
    $(`input[name="new_metadata_desc"]`).value = "";
    $(`input[name="new_metadata_desc"]`).required = false;
    $(`input[name="new_metadata_metric"]`).value = "";
    $(`input[name="new_metadata_metric"]`).hidden = true;
    $(`input[name="new_metadata_metric"]`).required = false;
    $(`select[name="new_metadata_type"]`).value = "short";
    $(`input[name="metric_required"]`).checked = false;
    $(`#enum_values`).style.display = "none";
    $(`input[name="enum_values"]`).value = "";
}
window.resetMetaForm = resetMetaForm;
export function addOrUpdateObjectSection(data) {
    refreshImage();
    refreshCount(data.num_objects);
    const id = data.image_id || data.new_object_id;
    const template = document.querySelector(`.accordion-section.template`).outerHTML;
    const html = template.replace(/__ID__/g, id)
        .replace('[0,0,0,0]', data.bbox || '[0,0,0,0]')
        .replace('Object template', `Object ${id}`);
    const temp = document.createElement('div');
    temp.innerHTML = html;
    const accordion_section = temp.firstElementChild;

    // Cloning and updating the accordion section
    accordion_section.style.display = "block";
    accordion_section.classList.remove("template");
    accordion_section.querySelectorAll('[disabled]').forEach(el => el.disabled = false);

    let accordion_header = accordion_section.querySelector(`.accordion-header`);
    let accordion_content = accordion_section.querySelector(`.accordion-content`);
    let obj_wrapper = accordion_content.querySelector(`.obj-wrapper`);
    let left_obj_info = obj_wrapper.querySelector(`.left-obj-info`);
    let right_obj_info = obj_wrapper.querySelector(`.right-obj-info`);
    let img = left_obj_info.querySelector(`img`);
    let hiddenInputCrop = left_obj_info.querySelector(`input`);

    // --- Dynamic return data ---
    img.src = data.image_path || data.pathObj;
    img.alt = `Object ${data.image_id || data.new_object_id}`;

    const class_id = data.class_id || data.new_object_id;
    const tmpName = data.tmpName || data.nameNewObj;
    accordion_section.id = 'obj' + id;
    hiddenInputCrop.name = `objects[${id}][crop_path]`;
    hiddenInputCrop.value = tmpName;

    writeAccordionHeader(accordion_header, id, class_id);
    accordion_section.id = `obj${id}`;
    accordion_content.id = `obj-data${id}`;


    right_obj_info.querySelector('input[name$="[class_id]"]').value = class_id;
    right_obj_info.querySelector('input[name$="[score]"]').value = 1.0;
    right_obj_info.querySelector('input[name$="[bbox]"]').value = data.bbox;

    let metadataContainer = right_obj_info.querySelector('.metadata-container');
    writeClassMetaField(metadataContainer , id , AppState.classNames);
    const similarObjectsDiv = accordion_content.querySelector('.similar-objects');
    if (data.simObj && data.simObj.length > 0) {

        data.simObj.forEach((simObj, index) => {

            const grouped = {};
            (simObj.metadata || []).forEach(meta => {
                const imgID = meta.obj_image_id || 'no_image';
                if (!grouped[imgID]) grouped[imgID] = [];
                grouped[imgID].push(meta);
            });

            const groupedHTML = Object.entries(grouped).map(([imgID, metas]) => {

                const versionText = metas[0].obj_version_number
                    ? ` — V${metas[0].obj_version_number}`
                    : "";

                const items = metas.map(m => `
                    <li class="metadata-item" data-key="${m.key}" data-value="${m.value}">
                        <span class="meta-key">${m.key}:</span>
                        <span class="meta-value">${m.value}</span>
                    </li>
                `).join("");

                return `
                    <div class="metadata-source-block">
                        <h4>From Image ${imgID}${versionText}</h4>
                        <ul class="metadata-list">
                            ${items}
                        </ul>
                    </div>
                `;
            }).join("");

            const objWrapperSimilar = document.createElement('div');
            objWrapperSimilar.className = 'obj-wrapper-similar';

            objWrapperSimilar.innerHTML = `
                <div class="left-similar">
                    <div class="similar-info">
                        <p><strong>Object ID:</strong> ${simObj.object_id}</p>
                        <p><strong>Similarity:</strong> ${((1 - simObj.distance) * 100).toFixed(2)}%</p>
                    </div>
                    <div class="similar-image-box">
                        <img src="${window.AppConfig.URL_for_images + simObj.cropped_file_path}"
                            alt="Similar Object ${simObj.object_id}"
                            class="similar-image">
                    </div>
                </div>

                <div class="right-similar">
                    <div class="obj-meta">
                        <h3>Similar object ${index + 1} — Metadata</h3>

                        ${simObj.metadata && simObj.metadata.length > 0
                            ? `<div class="metadata-grouped">${groupedHTML}</div>
                            <button type="button" class="import-btn"
                                onclick="importMetadata(this , '${id}')">
                                Import metadata from this object
                            </button>`
                            : `<p class="no-metadata">No metadata available for this object.</p>`
                        }

                        <div class="same-object-field">
                            <label title="Mark this as the same real-world object in database">
                                Same object as object ${id}?
                                <input type="checkbox" role="radio"
                                    name="selected_similar_${id}"
                                    value="${simObj.object_id}"
                                    onchange="defaultObjectSelection(this , '${id}' , '${simObj.object_id}')">
                            </label>
                        </div>
                    </div>
                </div>
            `;

            similarObjectsDiv.appendChild(objWrapperSimilar);
        });
    }


    $('.accordion-item').appendChild(accordion_section);
    $('input[name="max_object_detected"]').value =
        parseInt($('input[name="max_object_detected"]').value) + 1;
}
window.addOrUpdateObjectSection = addOrUpdateObjectSection;
export function writeClassMetaField(metadataContainer , id , classNames){
    metadataContainer.id = `meta-${id}`;
    metadataContainer.innerHTML = `
        <div class="meta-field">
            <input type="text" name="objects[${id}][type]" value="type" readonly>
            <select name="objects[${id}][value]" class="object_type" onchange="handleNewType(this)" required>
                ${classNames.map(cls => `
                    <option value="${cls}">${cls}</option>
                `).join('')}
                    <option value="__new__">+ Add new type</option>
            </select>
        </div>
    `;
}
window.writeClassMetaField = writeClassMetaField;
export function writeAccordionHeader(accordion_header, id, class_id) {
    accordion_header.innerHTML = `
        Object ID ${id} — Class ${class_id} (Confidence : 100%)
        <div class="handle-container" style="display: flex; flex-direction: row; float: right; gap: 10px;">
            <input type="checkbox" name="merge_${id}" id="merge_${id}" title="Select this object to merge it with another one">
            <img src="${trashIcon}" alt="Object ${id}" class="trash-icon" onclick="event.stopPropagation(); removeObject('${id}');">
        </div>
    `;
    accordion_header.setAttribute('onclick', `toggleAccordion('obj-data${id}')`);
}
window.writeAccordionHeader = writeAccordionHeader;
export function removeSelectOptionFromAll(metadataContainer , valueToDelete , exceptSelect = null){
    metadataContainer.querySelectorAll('.meta-field select').forEach(select => {
        if (select !== exceptSelect) {
            const foundIndex = Array.from(select.options).findIndex(option => option.value === valueToDelete);
            if (foundIndex > -1) {
                select.remove(foundIndex);
            }
        }
    });
}
window.removeSelectOptionFromAll = removeSelectOptionFromAll;
export function createOptionElement(meta){
    let option = document.createElement("option");
    option.value = meta.key;
    option.textContent = meta.key;
    option.setAttribute("data-desc", meta.description);
    option.setAttribute("data-type", meta.type);
    option.setAttribute("data-metric", meta.metric);
    option.setAttribute("data-enum", meta.enum_values);
    option.setAttribute("data-regex", returnRegexByName(meta.type , meta.enum_values));
    return option;
}
window.createOptionElement = createOptionElement;
export function addSelectOptionFromAll(metadataContainer , valueToAdd , exceptSelect = null){
    let dataOptions = AppState.metadataKeys.find(meta => meta.key === valueToAdd);
    metadataContainer.querySelectorAll('.meta-field select').forEach(select => {
        if (!(exceptSelect) || select !== exceptSelect) {
            select.add(createOptionElement(dataOptions));
            select.addEventListener('change', function() {
                changeKey(this , `objects[${metadataContainer.id.split('-')[1]}][metadata][${Array.from(metadataContainer.children).indexOf(this.parentElement)}][value]`);
            });
        }
    });
}
window.addSelectOptionFromAll = addSelectOptionFromAll;
export function showSimilar(button){
    button.innerText = button.innerText === "Show similar objects" ? "Hide similar objects" : "Show similar objects";
    const objWrapper = button.nextElementSibling;
    console.log("objWrapper : ", objWrapper);
    if (!objWrapper) return;
    if (objWrapper && button.innerText === "Hide similar objects") {
        objWrapper.style.display = "block";
    } else {
        objWrapper.style.display = "none";
    }
}
window.showSimilar = showSimilar;
export function defaultObjectSelection(checkboxElem , sourceObjID , similarObjID){
    sourceObjID = String(sourceObjID);
    similarObjID = String(similarObjID);
    document.querySelectorAll(`input[type="checkbox"][name="selected_similar_${sourceObjID}"]`).forEach(cb => {
        if (cb !== checkboxElem) {
            cb.checked = false;
        }
    });
    if (checkboxElem.checked){
        document.querySelector(`input[name="objects[${sourceObjID}][default_object]"]`).value = similarObjID;
    } else {
        document.querySelector(`input[name="objects[${sourceObjID}][default_object]"]`).value = "";
    }
}
window.defaultObjectSelection = defaultObjectSelection;

export function getMetadataFromFields(metaFields) {
    let metadata = {};
    metaFields.forEach(field => {
        const key = field.querySelector('select').value;
        const value = field.querySelector('input').value;
        if (key && value) {
            metadata[key] = value;
        }
    });
    return metadata;
}
export function controlInputValues(name, description , ...args) {
    if (name && name.trim() === '') {
        alert("Point name is required.");
        return false;
    }
    if (description && description.trim() === '') {
        alert("Point description is required.");
        return false;
    }
    for (const arg of args) {
        if (arg && arg.trim() === '') {
            alert("All fields are required.");
            return false;
        }
    }
    return true;
}

export function showGeoStatus(msg, type) {
    const box = document.getElementById('geojson-status');
    box.className = `geojson-status ${type}`;
    box.textContent = msg;
    box.style.display = 'block';
}

export async function getGeoJSONFileInput() {
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
        return {geojson , polyline , latlngs};
    }
    catch (error) {
        statusBox.innerText = "Failed to load GeoJSON: " + error.message;
        return null;
    }
}

export function getMarkerByLatLng(markers, lat, lng) {
    let foundMarker = null;
    markers.eachLayer(marker => {
        const markerLatLng = marker.getLatLng();
        if (markerLatLng.lat == lat && markerLatLng.lng == lng) {
            foundMarker = marker;
        }
    });
    return foundMarker;
}