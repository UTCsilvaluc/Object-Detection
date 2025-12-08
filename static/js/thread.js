/************************************************************
 * 1. IMPORTS
 ************************************************************/
import { apiPost } from './api.js';
import { normalizeValueToPostgreSQL } from './utils.js';



/************************************************************
 * 2. GLOBAL STATE (Threads, config)
 ************************************************************/

let threadCounter = 0;

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

function closeObjectsTab(threadId) {
    const container = document.getElementById(threadId);
    if (!container) return;
    container.querySelectorAll(".object-block").forEach(block => block.classList.remove("selected"));
}
function closeImagesTab(threadId) {
    const container = document.getElementById(threadId);
    if (!container) return;
    container.querySelectorAll(".image-block").forEach(block => block.classList.remove("selected"));
}

function toggleSelectBlockImage(threadId) {
    const container = document.getElementById(threadId);
    if (!container) return;

    container.querySelectorAll(".image-block").forEach(block => {
        block.addEventListener("click", (e) => {

            container.querySelectorAll(".image-block")
                .forEach(b => b.classList.remove("selected"));

            e.currentTarget.classList.add("selected");
        });
    });
}


function toggleSelectBlockObject(threadId) {
    const container = document.getElementById(threadId);
    if (!container) return;

    container.querySelectorAll(".object-block").forEach(block => {
        block.addEventListener("click", (e) => {

            container.querySelectorAll(".object-block")
                .forEach(b => b.classList.remove("selected"));

            e.currentTarget.classList.add("selected");
        });
    });
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
    closeObjectsTab(threadIdFull);
    closeImagesTab(threadIdFull);
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

        // Build HTML
        let html = `
            <h2>Object #${obj.object_id} — ${obj.name ?? "Unnamed"}</h2>

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
    renderObjectsTab(threadId, threadsData.objects_same_picture);

    const threads = injectImageContextIntoThread(threadsData);

    renderThreadTab(threadId, threads);
    renderImagesTab(threadId, threadsData.images_from_object);

    toggleSelectBlockImage(threadId);
    toggleSelectBlockObject(threadId);
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

    const tab = document.querySelector(`#thread-${threadId} .tab.selected`).dataset.tab;
    let payload = {};

    if (tab === "objects") {
        const selected = document.querySelector(`#thread-${threadId} .object-block.selected`);
        if (!selected) {
            alert("Select an object first.");
            return;
        }
        payload = {
            mode: "object",
            object_id: selected.dataset.objectId
        };
    }

    else if (tab === "images") {
        const selected = document.querySelector(`#thread-${threadId} .image-block.selected`);
        if (!selected) {
            alert("Select an image first.");
            return;
        }
        payload = {
            mode: "image",
            image_id: selected.dataset.imageId
        };
    }

    else if (tab === "thread") {
        const container = document.getElementById(`thread-${threadId}`);
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
    }

    const newData = await requestThreadGeneration(payload);
    if (!newData) return;

    // Create a new thread panel
    const newThreadId = "thread-" + threadCounter;

    createThreadContainer(newThreadId);
    renderFullThread(newThreadId, newData);

    threadCounter++;
}
window.generateThread = generateThread;
