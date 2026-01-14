import { apiPost } from "../api.js";
import { normalizeValueToPostgreSQL } from "../utils.js";
import { searchTypeToInput } from "./searchConfig.js";
import { allocateThreadDomId, isSearchLocked, lockSearch } from "./state.js";
import { createThreadContainer, renderFullThread } from "./render.js";
import { wireInstancePreviews } from "./instancePreview.js";
import { addThreadToGlobalMap } from "./globalMap.js";

export function handleTyping(e) {
  if (isSearchLocked()) return;
  if (e.key === "Enter") performSearch();
}

export function updateSearchField(select) {
  const input = document.getElementById("search-input");
  const selectedType = select.value;
  const config = searchTypeToInput[selectedType];
  if (!input || !config) return;

  input.type = config.type;
  input.placeholder = config.placeholder;

  if (config.step) input.step = config.step;
  else input.removeAttribute("step");
}

async function requestThreadGeneration(payload) {
  const data = await apiPost("/thread/generate", payload);
  if (!data) return null;
  return data.threads;
}

function lockSearchUI(objectId, triggerEl) {
  if (isSearchLocked()) return;
  lockSearch();

  const searchInput = document.getElementById("search-input");
  const searchSelect = document.getElementById("search-type");
  const searchBtn = document.querySelector(".search-box button");
  [searchInput, searchSelect, searchBtn].forEach((el) => {
    if (!el) return;
    el.setAttribute("disabled", "disabled");
    el.classList.add("disabled");
  });

  const container = document.getElementById("results-container");
  if (!container) return;

  let selectedBlock = container.querySelector(`.object-block[data-object-id="${objectId}"]`);
  if (!selectedBlock && triggerEl) selectedBlock = triggerEl.closest(".object-block");

  if (selectedBlock) {
    const clone = selectedBlock.cloneNode(true);
    const btn = clone.querySelector(".select-btn");
    if (btn) {
      btn.textContent = "Selected";
      btn.setAttribute("disabled", "disabled");
      btn.classList.add("disabled-btn");
    }
    container.innerHTML = `<p class="locked-label">Search locked: Object #${objectId} selected.</p>`;
    container.appendChild(clone);
  }
}

export async function performSearch() {
  if (isSearchLocked()) {
    alert("Search is locked. You already started a thread with a selected object.");
    return;
  }

  const input = document.getElementById("search-input");
  const select = document.getElementById("search-type");
  if (!input || !select) return;

  const query = input.value.trim();
  const selectedType = select.value;
  if (!query) {
    alert("Please enter a value.");
    return;
  }

  const normalizedQuery = normalizeValueToPostgreSQL(selectedType, query);
  const data = await apiPost("/thread/thread_search_values", { query: normalizedQuery });
  if (!data) return;

  const container = document.getElementById("results-container");
  if (!container) return;
  displayResultsIn(container, data.objects);
}
/**
 * Function called by the "Select Object" button in search results.
 * @param {*} objectId 
 * @param {*} triggerEl 
 */
export async function selectObject(objectId, triggerEl = null) {
  const threadsData = await requestThreadGeneration({ mode: "object", object_id: objectId });
  if (!threadsData) return;

  lockSearchUI(objectId, triggerEl);

  const threadDomId = allocateThreadDomId();
  createThreadContainer(threadDomId);

  const context = { commonObject: threadsData.main_object || { object_id: objectId } };
  renderFullThread(threadDomId, threadsData, context);

  addThreadToGlobalMap({
    threadDomId,
    mode: "object",
    seedObjects: threadsData.main_object ? [threadsData.main_object] : [{ object_id: objectId }],
    seedImageId: null,
    imagesFromThread: threadsData.images_from_object || []
  });
}

export function displayResultsIn(container, objects) {
  container.innerHTML = "";

  if (!objects || objects.length === 0) {
    container.innerHTML = "<p>No matching objects found.</p>";
    return;
  }

  objects.forEach((obj) => {
    const div = document.createElement("div");
    div.className = "object-block";
    div.dataset.objectId = obj.object_id;

    div.id = `object-${obj.object_id}-${Math.random().toString(36).slice(2)}`;

    let html = `
      <h2>Object ${obj.object_id}</h2>
      <div class="instance-row">
        ${obj.instances
          .map(
            (inst) => `
              <img src="${window.appConfig.URL_for_images}${inst.cropped_path}"
                   class="obj-instance"
                   title="Image ${inst.image_id}">
            `
          )
          .join("")}
      </div>
    `;

    html += `
      <div class="metadata-block">
        <h3>Metadata</h3>
        <table>
          ${Object.keys(obj.metadata || {})
            .map(
              (key) => `
                <tr>
                  <td class="meta-key">${key}</td>
                  <td class="meta-value">${(obj.metadata[key] || []).join(", ")}</td>
                </tr>
              `
            )
            .join("")}
        </table>
      </div>
    `;

    html += `
      <button class="select-btn" onclick="selectObject(${obj.object_id}, this)">
        Select Object
      </button>
    `;

    div.innerHTML = html;
    container.appendChild(div);
  });

  wireInstancePreviews(container);
}

/**
 * If requested by switchMode, request full images by their IDs.
 * Allows to fetch only the images currently plotted on the map. Only if needed.
 * @param {*} imageIds 
 */
export async function requestFullImagesByIds(imageIds) {
  if (!imageIds || imageIds.length === 0) return [];
  const idsArray = Array.from(imageIds);
  return await apiPost("/thread/request_full_images",{ image_ids: idsArray });
}
