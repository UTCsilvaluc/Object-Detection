import { wireInstancePreviews } from "./instancePreview.js";
import { enableSingleSelect } from "./ui.js";
import { injectImageContextIntoThread, orderObjectsByRelevance } from "./shared.js";
import { renderMapTab } from "./mapView.js";

export function createThreadContainer(threadDomId) {
  const template = document.getElementById("thread-__ID__");
  if (!template) return;

  const newThread = template.cloneNode(true);
  newThread.classList.remove("hidden");

  newThread.innerHTML = newThread.innerHTML.replace(/__ID__/g, threadDomId.split("-")[1]);
  newThread.id = threadDomId;

  document.getElementById("wrapper-threads")?.appendChild(newThread);
}

export function renderObjectsTab(threadDomId, objectsList) {
  const container = document.querySelector(`#${threadDomId} .thread-content[data-section="objects"]`);
  if (!container) return;

  container.innerHTML = "";

  if (!objectsList || objectsList.length === 0) {
    container.innerHTML = `<p>No related objects found.</p>`;
    return;
  }

  const withMetadata = [];
  const withoutMetadata = [];

  objectsList.forEach((obj) => {
    const hasMetadata = obj.metadata && Object.keys(obj.metadata).length > 0;
    if (hasMetadata) withMetadata.push(obj);
    else withoutMetadata.push(obj);
  });

  const renderBlock = (obj, targetContainer) => {
    const block = document.createElement("div");
    block.className = "object-block";
    block.dataset.objectId = obj.object_id;
    block.dataset.relation = obj.relation || "cooccurrence";
    block.dataset.co_occurrence_images = obj.co_occurrence_images ? obj.co_occurrence_images.join(",") : "";

    let html = `
      <h2>Object #${obj.object_id} — ${obj.name ?? "Unnamed"}</h2>
      <p class="object-relation">Relation: ${
        block.dataset.relation + (obj.co_occurrence_images ? " (" + obj.co_occurrence_images.length + " images)" : "")
      }</p>
      <div class="instance-row">
    `;

    obj.instances.forEach((inst) => {
      html += `
        <img src="${window.appConfig.URL_for_images}${inst.cropped_path}"
             class="obj-instance"
             title="Image ${inst.image_id}">
      `;
    });

    html += `</div>`;

    html += `
      <div class="metadata-block">
        <h3>Metadata</h3>
        <table>
    `;

    const metaKeys = Object.keys(obj.metadata || {});
    if (metaKeys.length === 0) {
      html += `
        <tr>
          <td class="meta-key">Metadata</td>
          <td class="meta-value">None</td>
        </tr>
      `;
    } else {
      metaKeys.forEach((key) => {
        html += `
          <tr>
            <td class="meta-key">${key}</td>
            <td class="meta-value">${obj.metadata[key].join(", ")}</td>
          </tr>
        `;
      });
    }

    html += `
        </table>
      </div>
    `;

    block.innerHTML = html;
    targetContainer.appendChild(block);
  };

  withMetadata.forEach((obj) => renderBlock(obj, container));

  if (withoutMetadata.length > 0) {
    const collapsible = document.createElement("details");
    collapsible.className = "no-metadata-section";
    collapsible.innerHTML = `<summary>Objects without metadata (${withoutMetadata.length})</summary>`;

    const noMetaContainer = document.createElement("div");
    noMetaContainer.className = "no-metadata-list";
    withoutMetadata.forEach((obj) => renderBlock(obj, noMetaContainer));

    collapsible.appendChild(noMetaContainer);
    container.appendChild(collapsible);
  }

  wireInstancePreviews(container);
}

export function renderThreadTab(threadDomId, threads) {
  const container = document.querySelector(`#${threadDomId} .thread-content[data-section="thread"]`);
  if (!container) return;

  const selectors = container.querySelectorAll(".thread-select");
  const fillSelect = (select, values) => {
    values.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      select.appendChild(opt);
    });
  };

  selectors.forEach((sel) => fillSelect(sel, threads[sel.dataset.key] || []));

  container.querySelectorAll(".thread-row input[type='checkbox']").forEach((checkbox) => {
    checkbox.addEventListener("change", (e) => {
      const select = e.target.previousElementSibling;
      if (!select) return;
      if (select.options.length === 0) {
        e.target.checked = false;
        alert("No options available for this category.");
        return;
      }
      if (e.target.checked) select.removeAttribute("disabled");
      else select.setAttribute("disabled", "disabled");
    });
  });
}

export function renderImagesTab(threadDomId, imagesList) {
  const container = document.querySelector(`#${threadDomId} .thread-content[data-section="images"]`);
  if (!container) return;

  container.innerHTML = "";

  if (!imagesList || imagesList.length === 0) {
    container.innerHTML = `<p>No images found for this object.</p>`;
    return;
  }

  imagesList.forEach((img) => {
    const block = document.createElement("div");
    block.className = "image-block";
    block.dataset.imageId = img.image_id;

    let html = `
      <h2>Image #${img.image_id} — ${img.title ?? "No title"}</h2>
      <div class="image-header-row">
        <img src="${window.appConfig.URL_for_images}${img.thumb_path || img.file_path}" class="thread-image-thumb">
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

    const groups = {};
    (img.metadata || []).forEach((m) => {
      if (!groups[m.object_id]) groups[m.object_id] = [];
      groups[m.object_id].push(m);
    });

    Object.keys(groups).forEach((objId) => {
      html += `
        <div class="object-meta-group">
          <h4>Object #${objId}</h4>
          <table>
      `;

      groups[objId].forEach((m) => {
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

    html += `</div>`;

    block.innerHTML = html;
    container.appendChild(block);
  });
}
/**
 * Renders the full thread including objects, thread details, images, and map.
 * @param {*} threadDomId 
 * @param {*} threadsData 
 * @param {*} context 
 */
export function renderFullThread(threadDomId, threadsData, context = {}) {
  const allObjects = [
    ...(threadsData.objects_same_picture || []).map((obj) => ({ ...obj, relation: "cooccurrence" })),
    ...(threadsData.objects_same_metadata || []).map((obj) => ({ ...obj, relation: "metadata" }))
  ];

  orderObjectsByRelevance(allObjects);
  renderObjectsTab(threadDomId, allObjects);

  const threads = injectImageContextIntoThread(threadsData);
  renderThreadTab(threadDomId, threads);
  renderImagesTab(threadDomId, threadsData.images_from_object);
  renderMapTab(threadDomId, threadsData.images_from_object, null, null, false, [], context);

  enableSingleSelect(threadDomId, ".object-block");
  enableSingleSelect(threadDomId, ".image-block");
}
