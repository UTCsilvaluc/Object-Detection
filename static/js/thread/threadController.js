import { apiPost } from "../api.js";
import { allocateThreadDomId } from "./state.js";
import { closeTab, clearThreadExcept } from "./ui.js";
import { createThreadContainer, renderFullThread } from "./render.js";
import { refreshThreadMap, renderMapTab } from "./mapView.js";

async function requestThreadGeneration(payload) {
  const data = await apiPost("/thread/generate", payload);
  if (!data) return null;
  return data.threads;
}

export function selectTab(threadId, targetTab) {
  const threadDomId = `thread-${threadId}`;
  const container = document.getElementById(threadDomId);
  if (!container) return;

  const tabs = container.querySelectorAll(".tab");
  const sections = container.querySelectorAll(".thread-content");

  tabs.forEach((tab) => {
    tab.classList.toggle("selected", tab.dataset.tab === targetTab);
  });

  sections.forEach((section) => {
    section.classList.toggle("hidden", section.dataset.section !== targetTab);
  });

  closeTab(threadDomId, ".object-block");
  closeTab(threadDomId, ".image-block");

  if (targetTab === "map") refreshThreadMap(threadDomId);
}

export async function generateThread(threadId) {
  const threadDomId = `thread-${threadId}`;
  const selectedTabEl = document.querySelector(`#${threadDomId} .tab.selected`);
  const tab = selectedTabEl?.dataset.tab;
  if (!tab) return;

  let cleanupSelectedView = null;
  let payload = {};

  if (tab === "objects") {
    const selected = document.querySelector(`#${threadDomId} .object-block.selected`);
    if (!selected) {
      alert("Select an object first.");
      return;
    }
    payload = { mode: "object", object_id: selected.dataset.objectId };
    const singleObjectHTML = selected.outerHTML;
    cleanupSelectedView = () => clearThreadExcept(threadDomId, "objects", singleObjectHTML);
  } else if (tab === "images") {
    const selected = document.querySelector(`#${threadDomId} .image-block.selected`);
    if (!selected) {
      alert("Select an image first.");
      return;
    }
    payload = { mode: "image", image_id: selected.dataset.imageId };
    const singleImageHTML = selected.outerHTML;
    cleanupSelectedView = () => clearThreadExcept(threadDomId, "images", singleImageHTML);
  } else if (tab === "map") {
    alert("Select an Object, Image, or configure Threads to generate a new thread.");
    return;
  } else if (tab === "thread") {
    const container = document.getElementById(threadDomId);
    if (!container) return;

    const selectors = container.querySelectorAll(".thread-select");
    const summarySelections = [];
    const selectorsValue = Array.from(selectors).map((sel) => ({
      key: sel.dataset.key,
      value: sel.value || null,
      enabled: !sel.disabled
    }));

    selectors.forEach((sel) => {
      const row = sel.closest(".thread-row");
      const checkbox = row ? row.querySelector("input[type='checkbox']") : null;
      const label = row ? row.querySelector(".thread-row-label")?.textContent.trim() : null;
      const enabled = checkbox ? checkbox.checked && !sel.disabled : !sel.disabled;
      if (enabled && sel.value) {
        summarySelections.push({ label: label || sel.dataset.key, value: sel.value });
      }
    });

    const summaryHTML = summarySelections.length
      ? summarySelections
          .map(
            ({ label, value }) =>
              `<div class="thread-row"><span class="meta-key">${label}</span>: <span class="meta-value">${value}</span></div>`
          )
          .join("")
      : "<p>No thread filters selected.</p>";

    payload = { mode: "thread", threads: selectorsValue };
    cleanupSelectedView = () => clearThreadExcept(threadDomId, "thread", summaryHTML);
  }

  const newData = await requestThreadGeneration(payload);
  if (!newData) return;

  if (cleanupSelectedView) cleanupSelectedView();

  const newThreadDomId = allocateThreadDomId();
  createThreadContainer(newThreadDomId);

  const context = {
    commonObject: newData.main_object || (payload.object_id ? { object_id: payload.object_id } : null)
  };
  renderFullThread(newThreadDomId, newData, context);
}

export async function showResults(threadId) {
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
      co_occurrence_images: selected.dataset.co_occurrence_images
        ? selected.dataset.co_occurrence_images.split(",")
        : [],
      relation: selected.dataset.relation || "cooccurrence"
    };
  } else if (tab === "images") {
    const selected = document.querySelector(`#${threadDomId} .image-block.selected`);
    if (!selected) {
      alert("Select an image first.");
      return;
    }
    payload = { mode: "image", image_id: selected.dataset.imageId };
  } else if (tab === "thread") {
    const container = document.getElementById(threadDomId);
    if (!container) return;
    const selectors = container.querySelectorAll(".thread-select");
    const selectorsValue = Array.from(selectors).map((sel) => ({
      key: sel.dataset.key,
      value: sel.value || null,
      enabled: !sel.disabled
    }));
    payload = { mode: "thread", threads: selectorsValue };
  } else if (tab === "map") {
    alert("Switch to Objects, Images, or Threads to fetch results.");
    return;
  }

  const data = await apiPost("/thread/show_results", payload);
  if (!data) return;

  renderMapTab(
    threadDomId,
    data.images || [],
    data.focus_image_id || null,
    data.relation || payload.relation || null,
    false,
    data.links || [],
    { commonObject: data.common_object || (payload.object_id ? { object_id: payload.object_id } : null) }
  );

  selectTab(threadId, "map");
}

// Legacy helper kept for compatibility (may not be used).
export function loadInitialThreads(threads) {
  const container = document.getElementById("thread-0");
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
}

