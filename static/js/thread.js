/************************************************************
 * 1. IMPORTS
 ************************************************************/
import { apiPost } from './api.js';
import { normalizeValueToPostgreSQL } from './utils.js';
import { createPopupHTML } from './popup.js';

/************************************************************
 * 2. GLOBAL STATE (Threads, config)
 ************************************************************/

let threadCounter = 0;
const mapStates = {}; // Keep Leaflet instances per thread

/************************************************************
 * 3. LISTENERS AND USER INTERACTIONS
 ************************************************************/
// Merge unique values into a threads map (e.g., add places/dates)
function mergeThreadValues(threads, key, values) {
    if (!threads[key]) threads[key] = [];
    values.forEach((val) => {
        if (val === null || val === undefined || val === "") return;
        if (!threads[key].includes(val)) threads[key].push(val);
    });
}

// Pressing Enter triggers the search
function handleTyping(e) {
    if (e.key === "Enter") performSearch();
}
window.handleTyping = handleTyping;

// Updating the input type based on the selected type
function updateSearchField(select) {
    const input = document.getElementById("search-input");
    const selectedType = select.value;
    const config = searchTypeToInput[selectedType];

    if (!config) return;

    input.type = config.type;
    input.placeholder = config.placeholder;

    if (config.step) input.step = config.step;
    else input.removeAttribute("step");
}
window.updateSearchField = updateSearchField;

function toggleMetadata(btn, event) {
    event.stopPropagation();
    const block = btn.nextElementSibling;

    if (block.style.display === "none") {
        block.style.display = "block";
        btn.textContent = "Hide metadata";
    } else {
        block.style.display = "none";
        btn.textContent = "Show metadata";
    }
}
window.toggleMetadata = toggleMetadata;

function closeTab(threadId, tabClass) {
    const container = document.getElementById(threadId);
    if (!container) return;
    container.querySelectorAll(tabClass).forEach(block => block.classList.remove("selected"));
}

function enableSingleSelect(threadId, selector) {
    const container = document.getElementById(threadId);
    if (!container) return;

    container.querySelectorAll(selector).forEach(block => {
        block.addEventListener("click", (e) => {
            container.querySelectorAll(selector)
                .forEach(b => b.classList.remove("selected"));

            e.currentTarget.classList.add("selected");
        });
    });
}

function clearThreadExcept(threadId, section, singleItemHTML) {
    const container = document.getElementById(threadId);
    if (!container) return;

    // 1. Hide all sections
    const sections = container.querySelectorAll(".thread-content");
    sections.forEach(sec => sec.classList.add("hidden"));

    // 2. Disable all tabs EXCEPT the selected one AND the map tab
    const tabs = container.querySelectorAll(".tab");
    tabs.forEach(tab => {
        const isSelected = tab.dataset.tab === section;
        const isMap = tab.dataset.tab === "map";

        if (isSelected) {
            // Selected tab stays fully enabled
            tab.classList.add("selected");
            tab.style.pointerEvents = "auto";
            tab.style.opacity = "1";
        }
        else if (isMap) {
            // Map stays enabled even when collapsing the thread
            tab.classList.remove("selected");
            tab.style.pointerEvents = "auto";
            tab.style.opacity = "1";
        }
        else {
            // All other tabs get disabled
            tab.classList.remove("selected");
            tab.style.pointerEvents = "none";
            tab.style.opacity = "0.4";
        }
    });

    // 3. Show only the target section and inject the single-item content
    const targetContainer = container.querySelector(`.thread-content[data-section="${section}"]`);
    if (!targetContainer) return;
    targetContainer.classList.remove("hidden");
    targetContainer.innerHTML = singleItemHTML;

    // Disable Generate Button
    const generateBtn = container.querySelector(".thread-generate-btn");
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.classList.add("disabled-btn");
    }
}


// Build ordered list of geolocated images with dates for the map tab
function buildGeoTimeline(imagesList = []) {
    return imagesList
        .map(img => {
            const lat = Number(img?.latitude);
            const lng = Number(img?.longitude);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
            const dateStr = img.event_date || img.capture_date || null;
            const date = dateStr ? new Date(dateStr) : null;
            return {
                raw: img,
                lat,
                lng,
                date,
                dateLabel: date ? date.toISOString().split("T")[0] : "Unknown date"
            };
        })
        .filter(Boolean)
        .sort((a, b) => {
            if (!a.date && !b.date) return 0;
            if (!a.date) return 1;
            if (!b.date) return -1;
            return a.date - b.date;
        });
}

function ensureThreadMap(threadId, center) {
    if (!mapStates[threadId]) {
        mapStates[threadId] = {
            map: null,
            layer: null,
            bounds: null,
            markers: new Map(),
            plottedIds: new Set(),
            drawnLinks: new Set(),
            previousIds: new Set(),
            colors: new Object(),
            images: []
        };
    }
    const state = mapStates[threadId];
    const mapContainer = document.querySelector(`#${threadId} .thread-map`);
    if (!mapContainer) return state;

    if (!state.map) {
        state.layer = L.layerGroup();
        state.map = L.map(mapContainer.id, { dragging: true }).setView(center, 6);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OSM"
        }).addTo(state.map);
        state.layer.addTo(state.map);
    } else {
        // Needed when map was initialized while hidden
        setTimeout(() => state.map.invalidateSize(), 50);
    }
    return state;
}

function refreshThreadMap(threadId) {
    const state = mapStates[threadId];
    if (!state || !state.map) return;
    state.map.invalidateSize();
    if (state.bounds) state.map.fitBounds(state.bounds, { padding: [20, 20] });
}

/************************************************************
 * 4. CONFIG : FIELD TYPE BY DATA TYPE
 ************************************************************/
const searchTypeToInput = {
    text:         { type: "text", placeholder: "Enter a text value" },
    int:          { type: "number", placeholder: "Enter an integer value" },
    float:        { type: "number", placeholder: "Enter a float value", step: "any" },
    short_float:  { type: "number", placeholder: "Enter a short float value", step: "any" },
    coordinate:   { type: "text",   placeholder: "Enter coordinates (e.g., 12.34,56.78)" },
    bool:         { type: "text",   placeholder: "Enter true or false" },
    date:         { type: "date",   placeholder: "" },
    "date-hr-sec":{ type: "datetime-local", placeholder: "" },
    string:       { type: "text",   placeholder: "Enter a string value" },
    enum:         { type: "text",   placeholder: "Enter one of the enum values" }
};

/************************************************************
 * 5. API : SEARCH VALUES
 ************************************************************/
async function performSearch() {
    const input = document.getElementById("search-input");
    const select = document.getElementById("search-type");

    const query = input.value.trim();
    const selectedType = select.value;

    if (!query) {
        alert("Please enter a value.");
        return;
    }

    const normalizedQuery = normalizeValueToPostgreSQL(selectedType, query);

    const data = await apiPost("/thread/thread_search_values", { query: normalizedQuery });

    if (data.success) {
        const container = document.getElementById("results-container");
        displayResultsIn(container, data.objects);
    } else {
        alert("Search failed. Please try again.");
    }
}
window.performSearch = performSearch;

async function selectObject(objectId) {

    const threadsData = await requestThreadGeneration({
        mode: "object",
        object_id: objectId
    });

    if (!threadsData) return;

    const threadId = "thread-" + threadCounter;
    
    createThreadContainer(threadId); 
    renderFullThread(threadId, threadsData);

    threadCounter++;
}
window.selectObject = selectObject;


async function requestThreadGeneration(payload) {
    const data = await apiPost("/thread/generate", payload);

    if (!data.success) {
        alert("Thread generation failed.");
        return null;
    }

    return data.threads;
}
window.requestThreadGeneration = requestThreadGeneration;


window.selectObject = selectObject;
/************************************************************
 * 6. UI : DISPLAYING RESULTS
 ************************************************************/
function displayResultsIn(container, objects) {
    container.innerHTML = "";

    if (!objects || objects.length === 0) {
        container.innerHTML = "<p>No matching objects found.</p>";
        return;
    }

    objects.forEach(obj => {
        const div = document.createElement("div");
        div.className = "object-block";
        div.dataset.objectId = obj.object_id;

        // Unique ID
        div.id = `object-${obj.object_id}-${Math.random().toString(36).slice(2)}`;

        // Header + instances
        let html = `
            <h2>Object ${obj.object_id}</h2>
            <div class="instance-row">
                ${obj.instances.map(inst => `
                    <img src="${window.appConfig.URL_for_images}${inst.cropped_path}"
                         class="obj-instance"
                         title="Image ${inst.image_id}">
                `).join("")}
            </div>
        `;

        // Metadata
        html += `
            <div class="metadata-block">
                <h3>Metadata</h3>
                <table>
                    ${Object.keys(obj.metadata).map(key => `
                        <tr>
                            <td class="meta-key">${key}</td>
                            <td class="meta-value">${obj.metadata[key].join(", ")}</td>
                        </tr>
                    `).join("")}
                </table>
            </div>
        `;

        // Bouton
        html += `
            <button class="select-btn" onclick="selectObject(${obj.object_id})">
                Select Object
            </button>
        `;

        div.innerHTML = html;
        container.appendChild(div);
    });
}
window.displayResultsIn = displayResultsIn;

/**
 * Change active tab inside a thread container
 * @param {string} threadId - ex: "thread-42"
 * @param {string} targetTab - "objects" | "images" | "thread"
 */
function selectTab(threadId, targetTab) {
    // Get the thread container
    const threadIdFull = `thread-${threadId}`;
    const container = document.getElementById(threadIdFull);
    if (!container) return;

    // Get all tabs
    const tabs = container.querySelectorAll(".tab");

    // Get all sections
    const sections = container.querySelectorAll(".thread-content");

    // 4) Switch visual state of tabs
    tabs.forEach(tab => {
        if (tab.dataset.tab === targetTab) {
            tab.classList.add("selected");
        } else {
            tab.classList.remove("selected");
        }
    });

    // 5) Show the correct section
    sections.forEach(section => {
        if (section.dataset.section === targetTab) {
            section.classList.remove("hidden");
        } else {
            section.classList.add("hidden");
        }
    });
    closeTab(threadIdFull, ".object-block");
    closeTab(threadIdFull, ".image-block");
    if (targetTab === "map") {
        refreshThreadMap(threadIdFull);
    }
}
window.selectTab = selectTab;

function renderObjectsTab(threadId, objectsList) {
    const container = document.querySelector(`#${threadId} .thread-content[data-section="objects"]`);
    if (!container) return;

    container.innerHTML = ""; // reset

    if (!objectsList || objectsList.length === 0) {
        container.innerHTML = `<p>No related objects found.</p>`;
        return;
    }

    objectsList.forEach(obj => {
        const block = document.createElement("div");
        block.className = "object-block";
        block.dataset.objectId = obj.object_id;
        block.dataset.relation = obj.relation || "cooccurrence";
        block.dataset.co_occurrence_images = obj.co_occurrence_images ? obj.co_occurrence_images.join(",") : "";

        // Build HTML
        let html = `
            <h2>Object #${obj.object_id} — ${obj.name ?? "Unnamed"}</h2>
            <p class="object-relation">Relation: ${block.dataset.relation}</p>

            <div class="instance-row">
        `;

        // INSTANCES
        obj.instances.forEach(inst => {
            html += `
                <img src="${window.appConfig.URL_for_images}${inst.cropped_path}"
                     class="obj-instance"
                     title="Image ${inst.image_id}">
            `;
        });

        html += `</div>`;

        // METADATA
        html += `
            <div class="metadata-block">
                <h3>Metadata</h3>
                <table>
        `;

        Object.keys(obj.metadata).forEach(key => {
            html += `
                <tr>
                    <td class="meta-key">${key}</td>
                    <td class="meta-value">${obj.metadata[key].join(", ")}</td>
                </tr>
            `;
        });

        html += `
                </table>
            </div>
        `;

        block.innerHTML = html;
        container.appendChild(block);
    });
}
/**
 * Renders the "thread" tab content , fullfiling the select options
 * @param {*} threadId 
 * @param {*} threads : Object (identity, place, date, ...)
 * @returns 
 */
function renderThreadTab(threadId, threads) {
    const container = document.querySelector(`#${threadId} .thread-content[data-section="thread"]`);
    if (!container) return;
    
    const selectors = container.querySelectorAll(".thread-select");
    const fillSelect = (select, values) => {
        values.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v;
            opt.textContent = v;
            select.appendChild(opt);
        });
    };
    selectors.forEach(sel => {
        fillSelect(sel, threads[sel.dataset.key] || []);
    });    
    container.querySelectorAll(".thread-row input[type='checkbox']").forEach(checkbox => {
        checkbox.addEventListener("change", (e) => {
            const select = e.target.previousElementSibling;
            if (select.options.length === 0) {
                e.target.checked = false;
                alert("No options available for this category.");
                return;
            }
            if (e.target.checked) {
                select.removeAttribute("disabled");
            } else {
                select.setAttribute("disabled", "disabled");
            }
        });
    });
}
function renderImagesTab(threadId, imagesList) {
    const container = document.querySelector(
        `#${threadId} .thread-content[data-section="images"]`
    );
    if (!container) return;

    container.innerHTML = "";

    if (!imagesList || imagesList.length === 0) {
        container.innerHTML = `<p>No images found for this object.</p>`;
        return;
    }

    imagesList.forEach(img => {
        const block = document.createElement("div");
        block.className = "image-block";
        block.dataset.imageId = img.image_id;

        let html = `
            <h2>Image #${img.image_id} — ${img.title ?? "No title"}</h2>

            <div class="image-header-row">
                <img src="${window.appConfig.URL_for_images}${img.file_path}" 
                     class="thread-image-thumb">

                <div class="image-info">
                    <p><strong>Description:</strong> ${img.description ?? "None"}</p>
                    <p><strong>Capture date:</strong> ${img.capture_date ?? "?"}</p>
                    <p><strong>Event date:</strong> ${img.event_date ?? "?"}</p>
                    <p><strong>Location:</strong> ${img.location_name ?? "?"}</p>
                    <p><strong>Coordinates:</strong> ${img.latitude}, ${img.longitude}</p>
                    <p><strong>Type:</strong> ${img.type}</p>
                </div>
            </div>

            <button class="metadata-toggle-btn" onclick="toggleMetadata(this, event)">
                Hide metadata
            </button>

            <div class="metadata-block">
                <h3>All Objects Metadata in Image</h3>
        `;

        // GROUP BY OBJECT
        const groups = {};
        img.metadata.forEach(m => {
            if (!groups[m.object_id]) groups[m.object_id] = [];
            groups[m.object_id].push(m);
        });

        Object.keys(groups).forEach(objId => {
            html += `
                <div class="object-meta-group">
                    <h4>Object #${objId}</h4>
                    <table>
            `;

            groups[objId].forEach(m => {
                html += `
                    <tr>
                        <td class="meta-key">${m.key}</td>
                        <td class="meta-value">${m.value}</td>
                    </tr>
                `;
            });

            html += `
                    </table>
                </div>
            `;
        });

        html += `</div>`; // close metadata-block

        block.innerHTML = html;
        container.appendChild(block);
    });
}
window.renderImagesTab = renderImagesTab;

function renderMapTab(threadId, imagesList, focusImageId = null, relation = null, append = false, links = []) {
    const container = document.querySelector(
        `#${threadId} .thread-content[data-section="map"]`
    );
    if (!container) return;

    // Ensure map-side structure exists (for safety if HTML changes)
    if (!container.querySelector(".map-panel")) {
        container.innerHTML = `
            <div class="map-panel">
                <div class="thread-map" id="map-${threadId.split("-")[1]}"></div>
                <div class="map-side">
                    <h3>Moves over time</h3>
                    <div class="map-image-list"></div>
                </div>
            </div>
        `;
    }

    const listEl = container.querySelector(".map-image-list");
    const mapEl = container.querySelector(".thread-map");
    if (!listEl || !mapEl) return;

    const defaultCenter = [34.33, 134.05];
    const state = ensureThreadMap(threadId, defaultCenter);
    if (!state.map) return;
    // Reset map content when not appending
    if (!append) {
        state.layer.clearLayers();
        state.markers = new Map();
        state.plottedIds = new Set();
        state.drawnLinks = new Set();
        state.images = [];
        state.previousIds = new Set();
        state.colors = new Object();
    }

    const newImages = imagesList || [];
    const merged = new Map();
    state.images.forEach(img => merged.set(img.image_id, img));
    newImages.forEach(img => merged.set(img.image_id, img));
    state.images = Array.from(merged.values());

    const timeline = buildGeoTimeline(state.images);
    const newTimeline = buildGeoTimeline(newImages);

    if (timeline.length === 0) {
        listEl.innerHTML = `<p>No geolocated images for this selection.</p>`;
    } else {
        listEl.innerHTML = `
            <p><strong>${timeline.length} result(s)</strong></p>
            ${timeline.map(({ raw, dateLabel }) => `
                <div class="map-image-card ${raw.image_id == focusImageId ? "primary" : ""}">
                    <img class="thumb" src="${window.appConfig.URL_for_images + raw.file_path}" alt="${raw.title ?? "Image"}">
                    <strong>${raw.title ?? "Untitled image"}</strong>
                    <small>${dateLabel}</small>
                    <div>${raw.location_name ?? "Unknown location"}</div>
                </div>
            `).join("")}
        `;
    }

    // Add markers for new items only
    const coordsAll = [];
    state.markers.forEach(marker => {
        coordsAll.push([marker.getLatLng().lat, marker.getLatLng().lng]);
    });

    let focusMarker = state.markers.get(Number(focusImageId)) || null;
    let focusLatLng = focusMarker ? focusMarker.getLatLng() : null;

    newTimeline.forEach(item => {
        if (state.plottedIds.has(item.raw.image_id)) return;
        const popupImage = { ...item.raw, latitude: item.lat, longitude: item.lng };
        const popupHTML = createPopupHTML(popupImage, window.appConfig.URL_for_images, window.appConfig.URL_for_view_image);
        const marker = L.marker([item.lat, item.lng]).bindPopup(popupHTML).addTo(state.layer);
        state.markers.set(item.raw.image_id, marker);
        state.plottedIds.add(item.raw.image_id);
        coordsAll.push([item.lat, item.lng]);
        if (item.raw.image_id == focusImageId) {
            focusMarker = marker;
            focusLatLng = marker.getLatLng();
        }
    });

    // Polyline for this batch (maintain prior lines)
    //Filter newTimeline to keep only items that are the main object of the thread.
    const filteredTimeline = newTimeline.filter(item => {
        return state.previousIds.has(item.raw.image_id);
    });
    const newCoords = filteredTimeline.map(item => [item.lat, item.lng]);
    if (newCoords.length > 1) {
        L.polyline(newCoords, { color: "#2463eb", weight: 3, opacity: 0.8 }).addTo(state.layer);
    }

    // Metadata links: only between focus and newly related images, with reasons
    const drawMetadataLink = relation === "metadata" || relation === "thread";
    if (drawMetadataLink && links && links.length > 0) {
        links.forEach(link => {
            const fromMarker = state.markers.get(Number(link.from_image_id));
            const toMarker = state.markers.get(Number(link.to_image_id));
            if (!fromMarker || !toMarker) return;
            const key = `${link.from_image_id}->${link.to_image_id}`;
            if (state.drawnLinks && state.drawnLinks.has(key)) return;
            const reasons = (link.metadata || []).map(md => {
                const tgt = md.target_value ?? "N/A";
                const rel = md.related_value ?? "N/A";
                return `<li><strong>${md.key}:</strong> ${tgt} ⇄ ${rel}</li>`;
            }).join("");
            const popupHtml = `
                <div style="font-size:12px;">
                    <strong>${relation === "thread" ? "Link by thread filters" : "Link by metadata"}</strong>
                    <ul style="padding-left:16px; margin:6px 0;">
                        ${reasons || "<li>No details</li>"}
                    </ul>
                </div>
            `;
            L.polyline([fromMarker.getLatLng(), toMarker.getLatLng()], { color: "#e3342f", weight: 3, opacity: 0.9 })
                .bindPopup(popupHtml)
                .addTo(state.layer);
            if (state.drawnLinks) state.drawnLinks.add(key);
        });
    }

    if (coordsAll.length > 0) {
        state.bounds = L.latLngBounds(coordsAll);
        state.map.fitBounds(state.bounds, { padding: [20, 20] });
    } else {
        state.bounds = null;
        state.map.setView(defaultCenter, 2);
    }
    if (state.previousIds && state.previousIds.size === 0) {
        state.previousIds = new Set(state.plottedIds);
    }

    if (focusMarker) {
        setTimeout(() => {
            state.map.setView(focusLatLng, 15);
            focusMarker.openPopup();
        }, 300);
    } 
}

function injectImageContextIntoThread(threadsData) {
    const threads = Object.fromEntries(
        Object.entries(threadsData.threads || {}).map(([k, v]) => [k, Array.isArray(v) ? [...v] : []])
    );
    const images = threadsData.images_from_object || [];
    images.forEach((img) => {
        mergeThreadValues(threads, "place", [img.location_name]);
        mergeThreadValues(threads, "date", [img.event_date]);
    });
    return threads;
}
window.injectImageContextIntoThread = injectImageContextIntoThread;

function renderFullThread(threadId, threadsData) {

    const allObjects = [
        ...(threadsData.objects_same_picture || []).map(obj => ({ ...obj, relation: "cooccurrence" })),
        ...(threadsData.objects_same_metadata || []).map(obj => ({ ...obj, relation: "metadata" }))
    ];

    renderObjectsTab(threadId, allObjects);

    const threads = injectImageContextIntoThread(threadsData);

    renderThreadTab(threadId, threads);
    renderImagesTab(threadId, threadsData.images_from_object);
    renderMapTab(threadId, threadsData.images_from_object);
    enableSingleSelect(threadId, ".object-block");
    enableSingleSelect(threadId, ".image-block");
}

window.renderFullThread = renderFullThread;

function createThreadContainer(threadId) {
    const template = document.getElementById("thread-__ID__");
    const newThread = template.cloneNode(true);
    newThread.classList.remove("hidden");

    newThread.innerHTML = newThread.innerHTML.replace(/__ID__/g, threadId.split("-")[1]);
    newThread.id = threadId;

    document.getElementById("wrapper-threads").appendChild(newThread);
}
window.createThreadContainer = createThreadContainer;


/************************************************************
 * 7. LOADING THREADS
 ************************************************************/
function loadInitialThreads(threads) {
    const container = document.getElementById("thread-0");
    if (!container) return;
    const selectors = container.querySelectorAll(".thread-select");
    const fillSelect = (select, values) => {
        values.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v;
            opt.textContent = v;
            select.appendChild(opt);
        });
    };

    selectors.forEach(sel => {
        fillSelect(sel, threads[sel.dataset.key] || []);
    });
}
window.loadInitialThreads = loadInitialThreads;

async function generateThread(threadId) {

    const threadDomId = `thread-${threadId}`;
    const tab = document.querySelector(`#${threadDomId} .tab.selected`).dataset.tab;
    let cleanupSelectedView = null;
    let payload = {};

    if (tab === "objects") {
        const selected = document.querySelector(`#${threadDomId} .object-block.selected`);
        if (!selected) {
            alert("Select an object first.");
            return;
        }
        payload = {
            mode: "object",
            object_id: selected.dataset.objectId
        };
        const singleObjectHTML = selected.outerHTML;
        cleanupSelectedView = () => clearThreadExcept(threadDomId, "objects", singleObjectHTML);
    }

    else if (tab === "images") {
        const selected = document.querySelector(`#${threadDomId} .image-block.selected`);
        if (!selected) {
            alert("Select an image first.");
            return;
        }
        payload = {
            mode: "image",
            image_id: selected.dataset.imageId
        };
        const singleImageHTML = selected.outerHTML;
        cleanupSelectedView = () => clearThreadExcept(threadDomId, "images", singleImageHTML);
    }

    else if (tab === "map") {
        alert("Select an Object, Image, or configure Threads to generate a new thread.");
        return;
    }

    else if (tab === "thread") {
        const container = document.getElementById(threadDomId);
        const selecters = container.querySelectorAll(".thread-select");
        const summarySelections = [];
        const selectersValue = Array.from(selecters).map(sel => ({
            key: sel.dataset.key,
            value: sel.value || null,
            enabled: !sel.disabled 
        }));

        // Build a compact summary to keep only the chosen thread values visible
        selecters.forEach(sel => {
            const row = sel.closest(".thread-row");
            const checkbox = row ? row.querySelector("input[type='checkbox']") : null;
            const label = row ? row.querySelector(".thread-row-label")?.textContent.trim() : null;
            const enabled = checkbox ? checkbox.checked && !sel.disabled : !sel.disabled;
            if (enabled && sel.value) {
                summarySelections.push({
                    label: label || sel.dataset.key,
                    value: sel.value
                });
            }
        });

        const summaryHTML = summarySelections.length
            ? summarySelections.map(
                ({ label, value }) =>
                    `<div class="thread-row"><span class="meta-key">${label}</span>: <span class="meta-value">${value}</span></div>`
            ).join("")
            : "<p>No thread filters selected.</p>";

        payload = {
            mode: "thread",
            threads: selectersValue
        };
        cleanupSelectedView = () => clearThreadExcept(threadDomId, "thread", summaryHTML);
    }

    const newData = await requestThreadGeneration(payload);
    if (!newData) return;

    if (cleanupSelectedView) cleanupSelectedView();

    // Create a new thread panel
    const newThreadId = "thread-" + threadCounter;

    createThreadContainer(newThreadId);
    renderFullThread(newThreadId, newData);

    threadCounter++;
}
window.generateThread = generateThread;

async function showResults(threadId) {
    const threadDomId = `thread-${threadId}`;
    const tabEl = document.querySelector(`#${threadDomId} .tab.selected`);
    const tab = tabEl ? tabEl.dataset.tab : null;
    if (!tab) {
        alert("Select a tab first.");
        return;
    }

    let payload = null;

    if (tab === "objects") {
        const selected = document.querySelector(`#${threadDomId} .object-block.selected`);
        if (!selected) {
            alert("Select an object first.");
            return;
        }
        payload = {
            mode: "object",
            object_id: selected.dataset.objectId,
            co_occurrence_images: selected.dataset.co_occurrence_images ? selected.dataset.co_occurrence_images.split(",") : [],
            relation: selected.dataset.relation || "cooccurrence"
        };
    } else if (tab === "images") {
        const selected = document.querySelector(`#${threadDomId} .image-block.selected`);
        if (!selected) {
            alert("Select an image first.");
            return;
        }
        payload = {
            mode: "image",
            image_id: selected.dataset.imageId
        };
    } else if (tab === "thread") {
        const container = document.getElementById(threadDomId);
        const selecters = container.querySelectorAll(".thread-select");
        const selectersValue = Array.from(selecters).map(sel => ({
            key: sel.dataset.key,
            value: sel.value || null,
            enabled: !sel.disabled
        }));
        payload = {
            mode: "thread",
            threads: selectersValue
        };
    } else if (tab === "map") {
        alert("Switch to Objects, Images, or Threads to fetch results.");
        return;
    }

    if (!payload) return;

    const data = await apiPost("/thread/show_results", payload);
    if (!data.success) {
        alert("Failed to fetch map results.");
        return;
    }
    renderMapTab(
        threadDomId,
        data.images || [],
        data.focus_image_id || null,
        data.relation || payload.relation || null,
        true,
        data.links || []
    );
    selectTab(threadId, "map");
}
window.showResults = showResults;
