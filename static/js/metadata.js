import { apiPost } from "./api.js";

let crossIcon = null;
function setCrossIcon(icon) {
    crossIcon = icon;
}
export { setCrossIcon };

if (!window.AppState) {
    window.AppState = {};
}

function returnRegexByName(name, enum_values = null) {
    if (enum_values && enum_values !== "null" && enum_values.trim() !== "") {
        const enumPattern = enum_values
            .split(";")
            .map(v => v.trim())
            .filter(v => v.length > 0)
            .join("|");
        return `^(?:${enumPattern})$`;
    }

    const patterns = {
        "short": "^.{1,40}$",                         
        "text": "^.{1,}$",                           
        "int": "^-?\\d+$",                           
        "float": "^-?\\d+(?:[.,]\\d+)?$",            
        "short_float": "^-?\\d+(?:[.,]\\d{1,2})?$",   
        "coordinate": "^-?\\d{1,3}(?:[.,]\\d+)?$",    
        "bool": "^(true|false)$",                     
        "date": "^\\d{4}-\\d{2}-\\d{2}$",            
        "date-hr-sec": "^\\d{4}-\\d{2}-\\d{2}\\T\\d{2}:\\d{2}$",
        "string": "^.*$"                              
    };
    return patterns[name] || patterns["string"];
}
window.returnRegexByName = returnRegexByName;
function returnInputTypeByName(name) {
    const types = {
        "short": "text",
        "text": "text",
        "int": "number",
        "float": "text",
        "short_float": "text",
        "coordinate": "text",
        "bool": "text",
        "date": "date",
        "date-hr-sec": "datetime-local",
        "string": "text"
    };
    return types[name] || types["text"];
}
window.returnInputTypeByName = returnInputTypeByName;
function writeMetaDataField(metaField, objID , metaIndex , key=null , value=null) {
    let mapClientMetadataKeys = [];
    AppState.metadataKeys.forEach(meta => {
        if (!AppState.metadataUsed[objID]) AppState.metadataUsed[objID] = [];
        if (!AppState.metadataUsed[objID].includes(meta.key) && meta.key !== "type") {
            mapClientMetadataKeys.push(meta);
        }
    });
    if (key && !mapClientMetadataKeys.some(m => m.key === key)) {
        const forcedMeta = AppState.metadataKeys.find(m => m.key === key);
        if (forcedMeta) mapClientMetadataKeys.unshift(forcedMeta);
    }
    if (mapClientMetadataKeys.length === 0) {
        alert("No more metadata keys available to add. Please create a new metadata key.");
        return;
    }
    metaField.innerHTML = `
        <select name="objects[${objID}][metadata][${metaIndex}][key]" 
                class="object_type" 
                onchange="changeKey(this)" 
                required>
            ${mapClientMetadataKeys.map(meta => `
                <option value="${meta.key}"
                        data-desc="${meta.description}"
                        data-type="${meta.type}"
                        data-metric="${meta.metric}"
                        data-regex="${meta.format_pattern}"
                        data-enum="${meta.enum_values}"
                        ${meta.key === key ? 'selected' : ''}>
                        ${meta.key}
                </option>
            `).join('')}
        </select>
        <input type="text" 
            name="objects[${objID}][metadata][${metaIndex}][value]" 
            placeholder="Value" 
            onchange="changeValue(this)" 
            required>
        <img src=${crossIcon} 
            alt="" 
            class="remove-icon" 
            onclick="removeMetadataField(this)" 
            data-index="${metaIndex}">
    `;
}
window.writeMetaDataField = writeMetaDataField;
function addMetadataField(objID, key = null, value = null , search = false) {
    console.log(search);
    objID = parseInt(objID);
    const container = search ? document.getElementById(`metasearch-${objID}`) : document.getElementById(`meta-${objID}`);
    const metaIndex = container.children.length - 1; 
    let div = document.createElement('div');
    div.className = 'meta-field';


    writeMetaDataField(div, objID, metaIndex, key, value);

    container.appendChild(div);

    const elemKey = div.querySelector('select');
    const selectedOption = elemKey.options[elemKey.selectedIndex];
    const desc = selectedOption.getAttribute("data-desc");
    const type = selectedOption.getAttribute("data-type");
    const metric = selectedOption.getAttribute("data-metric");
    const enumVals = selectedOption.getAttribute("data-enum");
    const regex = returnRegexByName(type, enumVals);

    const inputValue = div.querySelector('input');
    inputValue.placeholder = desc ? desc : "Value";
    inputValue.pattern = regex ? regex : "";
    inputValue.type = returnInputTypeByName(type);
    inputValue.title = 
        "Description: " + (desc ? desc : "Value") + 
        (metric != "null" ? " | Metric: " + metric : "") + 
        (regex ? " | Format: " + regex : "");
    if (value){
        inputValue.value = value;
    }
    elemKey.setAttribute("data-old-value", elemKey.value);
    AppState.metadataUsed[objID].push(elemKey.value);
    removeSelectOptionFromAll(container, elemKey.value, elemKey);
}
window.addMetadataField = addMetadataField;
async function handleNewType(selectedItem){
    if (selectedItem.value === "__new__") {
        const typeName = prompt("Enter the new type name or nothing to cancel the action:")
        if (!typeName) {
            selectedItem.selectedIndex = 0;
            return;
        }
        const typeDesc = prompt("Enter a description for this type:");
        if (!typeDesc) {
            selectedItem.selectedIndex = 0;
            return;
        }
        const data = await apiPost('/metadata/add_class', { name: typeName, description: typeDesc });
        if (!data) return;
        if (data.success) {
            $$(".object_type").forEach(sel => {
                const newOption = document.createElement("option");
                newOption.value = typeName;
                newOption.textContent = typeName;
                sel.insertBefore(newOption, sel.querySelector('option[value="__new__"]'));
            })
            const newOption = document.createElement("option");
            newOption.value = typeName;
            newOption.textContent = typeName;
            let selecteurImage = document.getElementById("imgType");
            selecteurImage.insertBefore(newOption , selecteurImage.querySelector('option[value="__new__"]'));
            selectedItem.value = typeName;
            AppState.classNames.push(typeName);
        } else {
            alert("Failed to add new type: " + data.error);
            selectElem.selectedIndex = 0;
        }
    }
}
window.handleNewType = handleNewType;
function createNewMetadata(button){
    $(`.hid-maker`).classList.toggle('visible');
    if (button.innerHTML.includes('-')) {
        button.innerHTML = button.innerHTML.replace('-', '+');
        resetMetaForm();
    } else {
        button.innerHTML = button.innerHTML.replace('+', '-');
        $(`input[name="new_metadata_key"]`).required = true;
        $(`input[name="new_metadata_desc"]`).required = true;
    }
}
window.createNewMetadata = createNewMetadata;
function handleNewMetadataType(selectedItem){
    if (selectedItem.value === "enum"){
        $(`#enum_values`).style.display = "block";
    } else {
        $(`#enum_values`).style.display = "none";
    }
}
window.handleNewMetadataType = handleNewMetadataType;
async function createNewMetadataKey(button){
    const makerDiv = button.closest('.maker_metadata');
    const key = makerDiv.querySelector('input[name="new_metadata_key"]').value.trim();
    const desc = makerDiv.querySelector('input[name="new_metadata_desc"]').value.trim();
    const metric = makerDiv.querySelector('input[name="new_metadata_metric"]').value.trim();
    const type = makerDiv.querySelector('select[name="new_metadata_type"]').value;
    const metric_required = makerDiv.querySelector('input[name="metric_required"]').checked;
    const enum_values = (type === "enum") ? makerDiv.querySelector('input[name="enum_values"]').value.trim() : "";
    if (!key || !desc || (metric_required && !metric) || (type === "enum" && !enum_values)) {
        alert("Please fill in all required fields.");
        return;
    }
    const data = await apiPost('/metadata/add_metadata_key', { key: key, description: desc, metric: metric, type: type, metric_required: metric_required, enum_values: enum_values });
    if (!data.success) {
        alert("Failed to create metadata key: " + data.error);
        return;
    }
    $$(".meta-field select[name$='[key]']").forEach(input => {
        const newOption = createOptionElement({
            key: key,
            description: desc,
            type: type,
            metric: metric,
            enum_values: enum_values
        });
        input.insertBefore(newOption, input.querySelector('option[value="type"]'));
    });
    $(`#enum_values`).style.display = "none";
    $(`.hid-maker`).classList.remove('visible');
    $(`button[onclick="createNewMetadata(this)"]`).innerHTML = $(`button[onclick="createNewMetadata(this)"]`).innerHTML.replace('-', '+');
    AppState.metadataKeys.push({
        key: key,
        "description": desc,
        "type": type,
        "metric": metric,
        "format_pattern": data.regex, // ou génère le regex côté client si nécessaire
        "enum_values": enum_values
    });
    resetMetaForm();
}
window.createNewMetadataKey = createNewMetadataKey;
function importMetadata(button, targetObjID){
    targetObjID = String(targetObjID);

    const similarMetaContainer = button.closest('.obj-meta');
    if (!similarMetaContainer) return;
    const metadataElems = similarMetaContainer.querySelectorAll('ul.metadata-list li.metadata-item');
    const accordionSection = button.closest('.accordion-section');
    if (!accordionSection) return;

    //CSS allows to escape special characters in IDs ; but not supported in all browsers yet : fallback to normal ID selector if not supported
    const targetMetaContainer =
        accordionSection.querySelector(`#meta-${CSS && CSS.escape ? CSS.escape(targetObjID) : targetObjID}`) ||
        accordionSection.querySelector('.metadata-container');
    if (targetMetaContainer.children.length > 1) {
        const confirm = window.confirm("Do you want do remove old metadata fields before importing the new ones ?");
        if (confirm) {
            targetMetaContainer.querySelectorAll('.meta-field').forEach((elem, index) => {
                if (index === 0) return; 
                elem.remove();
            });
            AppState.metadataUsed[targetObjID] = [];
        }
    }
    if (!targetMetaContainer) return;
    // If AppState.metadataUsed[targetObjID] is not defined yet, initialize it
    if (!AppState.metadataUsed[targetObjID]) AppState.metadataUsed[targetObjID] = [];
    const selects = Array.from(targetMetaContainer.querySelectorAll('.meta-field select'));
    let keyAppended = [];
    metadataElems.forEach(metaElem => {
        const key = metaElem.getAttribute('data-key');
        const value = metaElem.getAttribute('data-value') ?? '';
        if (!key) return;
        if (keyAppended.includes(key)) return;
        keyAppended.push(key);
        const existingField = selects.find(sel => sel.value === key);

        if (existingField) {
            const input = existingField.closest('.meta-field')?.querySelector('input');
            if (input) {
                input.value = value;
                changeValue(input);
            }
            if (!AppState.metadataUsed[targetObjID].includes(key)) {
                AppState.metadataUsed[targetObjID].push(key);
            }
            return; 
        }
        const metaDef = (AppState.metadataKeys || []).find(m => m.key === key);
        if (!metaDef) {
            return;
        }
        addMetadataField(targetObjID , key , value); 
    });
}
window.importMetadata = importMetadata;
function removeMetadataField(img){
    event.stopPropagation();
    if (!confirm('Are you sure you want to delete this metadata field?')) return;
    const parent = img.closest('.meta-field');
    const container = parent.parentNode;
    const id = container.id.split('-')[1];
    let startIndex = parseInt(img.getAttribute("data-index"));
    let index = AppState.metadataUsed[id].indexOf( parent.querySelector('select').value );
    if (index > -1) { 
        AppState.metadataUsed[id].splice(index, 1); 
    }
    const removedValue = parent.querySelector('select').value;
    parent.remove();
    for (let i = startIndex + 1; i < container.children.length; i++) {
        let child = container.children[i];
        let selectElem = child.querySelector('select');
        let inputElem = child.querySelector('input');
        let trashIcon = child.querySelector('.remove-icon');
        trashIcon.setAttribute("data-index", i - 1);
        selectElem.name = `objects[${id}][metadata][${i-1}][key]`;
        selectElem.setAttribute("onchange", `changeKey(this)`);
        inputElem.name = `objects[${id}][metadata][${i-1}][value]`;
    }
    addSelectOptionFromAll(container , removedValue);
}    
window.removeMetadataField = removeMetadataField;
/**
 * This function is called when the metadata key select element is changed. Available for /upload and /map pages.
 * @param {*} selectElem 
 */
function changeKey(selectElem){
    const selectedOption = selectElem.options[selectElem.selectedIndex];
    let metadataContainer = selectElem.closest('.metadata-container') || selectElem.closest('.metadata-section');
    const oldKey = selectElem.getAttribute("data-old-value");
    const type = selectedOption.getAttribute("data-type");
    const desc = selectedOption.getAttribute("data-desc");
    const metric = selectedOption.getAttribute("data-metric");
    const enumValues = selectedOption.getAttribute("data-enum");
    const regex = returnRegexByName(type, enumValues);
    let metaField = selectElem.closest('.meta-field');
    let inputValue = metaField.querySelector('input');
    inputValue.placeholder = desc ? desc : "Value";
    inputValue.value = "";
    inputValue.pattern = regex ? regex : "";  
    inputValue.type = returnInputTypeByName(type);
    let title = "Description: " + (desc ? desc : "Value") + (metric != "null" ? " | Metric: " + metric : "") + (regex ? " | Format: " + regex : "");
    inputValue.title = title;
    if (type === "bool") {
        inputValue.value = "false";
    }
    selectElem.setAttribute("data-old-value", selectElem.value);
    let objIndex = metadataContainer.id.split('-')[1];
    let key = selectElem.value;
    if (!AppState.metadataUsed[objIndex]) AppState.metadataUsed[objIndex] = [];
    if (AppState.metadataUsed[objIndex].includes(oldKey)) {
        let index = AppState.metadataUsed[objIndex].indexOf(oldKey);
        if (index > -1) { 
            AppState.metadataUsed[objIndex].splice(index, 1); 
        }
        addSelectOptionFromAll(metadataContainer , oldKey , selectElem);
    }
    if (!AppState.metadataUsed[objIndex].includes(key)) {
        AppState.metadataUsed[objIndex].push(key);
        removeSelectOptionFromAll(metadataContainer , selectElem.value , selectElem);
    }
}
window.changeKey = changeKey;
function changeValue(inputElem) {
    const pattern = inputElem.getAttribute("pattern");
    if (pattern) {
        const regex = new RegExp(pattern);
        if (!regex.test(inputElem.value)) {
            alert("The value you entered does not match the required format. Please hover over the input field to see the expected format.");
            inputElem.setCustomValidity("Invalid value format");
        } else {
            inputElem.setCustomValidity("");
        }
    }
}
window.changeValue = changeValue;
function changeType(selectedItem){
    handleNewType(selectedItem);
    let selecteur = document.getElementById("imgType");
    const hidden = document.getElementById("hiddenType");
    hidden.value = selecteur.value;
}
window.changeType = changeType;

function researchSimilar(button){
    const researchDiv = button.nextElementSibling;
    if (researchDiv.classList.contains('visible')){
        researchDiv.classList.remove('visible');
        return;
    }
    researchDiv.classList.add('visible');
}
window.researchSimilar = researchSimilar;

async function searchByMetadata(objID){
    const section = document.querySelector(`#obj${objID} .search-metadata-container`);
    const container = document.getElementById(`metasearch-${objID}`);
    const selectedRadio = section.querySelector('input[name="search_mode"]:checked');
    let flaskData = {};
    if (selectedRadio && selectedRadio.value === "value_only"){
        const valueInput = section.querySelector('#value-search');
        const searchValue = valueInput.value.trim();
        if (searchValue.length === 0){
            alert("Please enter a value to search for.");
            return;
        }
        flaskData = { searchValue : searchValue };
    } else {
        let metadata = [];
        Array.from(container.querySelectorAll('.meta-field')).forEach(field => {
            const keySelect = field.querySelector('select');
            const valueInput = field.querySelector('input');
            if (keySelect && valueInput) {
                metadata.push({
                    key: keySelect.value,
                    value: valueInput.value
                });
            }
        });
        flaskData = { metadata: metadata };
    }
    console.log(flaskData);
    const data = await apiPost('/metadata/search_by_metadata', flaskData);
    if (!data) return;
    if (data.success) {
        const resultDiv = document.querySelector(`#obj${objID} .search-results`);
        resultDiv.innerHTML = "";
        data.similar_objects.forEach((simObj , index) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'obj-wrapper-similar';
            wrapper.innerHTML = `
                <div class="left-similar">
                    <div class="similar-info">
                        <p> <strong>Object ID:</strong> ${simObj.object_id}</p>
                    </div>
                    <div class="similar-image-box">
                        <img src="${window.AppConfig.URL_for_images + simObj.cropped_file_path}" alt="Similar Object Image" class="similar-image">
                    </div>
                </div>
            `;

            const right = document.createElement('div');
            right.className = 'right-similar';

            const metaDiv = document.createElement('div');
            metaDiv.className = 'obj-meta';
            metaDiv.innerHTML = `<h3> Similar Object Index ${index} - Metadata </h3>`;

            if (simObj.metadata && Object.keys(simObj.metadata).length > 0) {
                const grouped = {};
                simObj.metadata.forEach(meta => {
                    const imgID = meta.obj_image_id || 'no_image';
                    if (!grouped[imgID]) {
                        grouped[imgID] = [];
                    }
                    grouped[imgID].push(meta);
                });

                const metadataGrouped = document.createElement('div');
                metadataGrouped.className = 'metadata-grouped';

                Object.entries(grouped).forEach(([imgID, metas]) => {
                    const block = document.createElement('div');
                    block.className = 'metadata-source-block';
                    const versionText = metas[0].obj_version_number ? ` - V${metas[0].obj_version_number})` : '';
                    block.innerHTML = `
                        <h4> From Image ID: ${imgID}${imgID !== 'no_image' ? versionText : ''} </h4>
                        <ul class="metadata-list">
                            ${metas.map(meta => `
                                <li class="metadata-item" data-key="${meta.key}" data-value="${meta.value}">
                                    <span class="meta-key">${meta.key}:</span> 
                                    <span class="meta-value">${meta.value}</span>
                                </li>
                            `).join('')}
                        </ul>
                    `;
                    metadataGrouped.appendChild(block);
                });

                metaDiv.appendChild(metadataGrouped);

                const importBtn = document.createElement('button');
                importBtn.type = 'button';
                importBtn.className = 'import-btn';
                importBtn.textContent = 'Import Metadata from this Object';
                importBtn.onclick = () => importMetadata(importBtn, objID);
                metaDiv.appendChild(importBtn);
            } else {
                metaDiv.innerHTML += `<p class="no-metadata">No metadata available for this object.</p>`;
            }
            const sameDiv = document.createElement('div');
            sameDiv.className = 'same-object-field';
            sameDiv.innerHTML = `
                <label title="Mark this as the same real-world object in database">
                    Same object as object ID ${simObj.object_id} ?
                    <input type="checkbox" role="radio" name="selected_similar_${objID}" value="${simObj.object_id}" onchange="defaultObjectSelection(this , '${objID}' , '${simObj.object_id}')">
                </label>
            `;
            metaDiv.appendChild(sameDiv);
            right.appendChild(metaDiv);
            wrapper.appendChild(right);
            resultDiv.appendChild(wrapper);
        });         
    } else {
        alert("Failed to search by metadata: " + data.error);
    }
}
window.searchByMetadata = searchByMetadata;

function updateSimilarSearch(radio){
    const search_row = radio.closest('.research-similar').querySelector('.search-row');
    const value_search = radio.closest('.research-similar').querySelector('#value-search');
    if (radio.checked && radio.value === "value_only"){
        search_row.style.display = "none";
        value_search.style.display = "block";
    } else {
        search_row.style.display = "flex";
        value_search.style.display = "none";
    }
}
window.updateSimilarSearch = updateSimilarSearch;

export { returnRegexByName , returnInputTypeByName , addMetadataField, createNewMetadata, createNewMetadataKey, handleNewMetadataType, importMetadata, changeKey, changeValue , changeType , removeMetadataField , handleNewType , writeMetaDataField};