import { getOrCreateMapState } from "./state.js";
import { renderMapTab } from "./mapView.js";
import {requestFullImagesByIds} from "./searchController.js";

export function toggleMetadata(btn, event) {
  event.stopPropagation();
  const block = btn.nextElementSibling;
  if (!block) return;

  if (block.style.display === "none") {
    block.style.display = "block";
    btn.textContent = "Hide metadata";
  } else {
    block.style.display = "none";
    btn.textContent = "Show metadata";
  }
}

export function closeTab(threadDomId, tabClass) {
  const container = document.getElementById(threadDomId);
  if (!container) return;
  container.querySelectorAll(tabClass).forEach((block) => block.classList.remove("selected"));
}

export function enableSingleSelect(threadDomId, selector) {
  const container = document.getElementById(threadDomId);
  if (!container) return;

  container.querySelectorAll(selector).forEach((block) => {
    block.addEventListener("click", (e) => {
      container.querySelectorAll(selector).forEach((b) => b.classList.remove("selected"));
      e.currentTarget.classList.add("selected");
    });
  });
}

export function clearThreadExcept(threadDomId, section, singleItemHTML) {
  const container = document.getElementById(threadDomId);
  if (!container) return;

  const sections = container.querySelectorAll(".thread-content");
  sections.forEach((sec) => sec.classList.add("hidden"));

  const tabs = container.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    const isSelected = tab.dataset.tab === section;
    const isMap = tab.dataset.tab === "map";

    if (isSelected) {
      tab.classList.add("selected");
      tab.style.pointerEvents = "auto";
      tab.style.opacity = "1";
    } else if (isMap) {
      tab.classList.remove("selected");
      tab.style.pointerEvents = "auto";
      tab.style.opacity = "1";
    } else {
      tab.classList.remove("selected");
      tab.style.pointerEvents = "none";
      tab.style.opacity = "0.4";
    }
  });

  const targetContainer = container.querySelector(`.thread-content[data-section="${section}"]`);
  if (!targetContainer) return;
  targetContainer.classList.remove("hidden");
  targetContainer.innerHTML = singleItemHTML;

  const generateBtn = container.querySelector(".thread-generate-btn");
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.classList.add("disabled-btn");
  }
}

export async function switchMode(button, threadID) {
  const threadDomId = threadID.startsWith("thread-") ? threadID : `thread-${threadID}`;
  const state = getOrCreateMapState(threadDomId);

  const currentMode = state?.context?.viewMode === "objects" ? "objects" : "images";
  const nextMode = currentMode === "images" ? "objects" : "images";
  const buttonLabel = nextMode === "objects" ? "Switch to images display" : "Switch to objects display";

  if (state && state.context) state.context.viewMode = nextMode;
  button.textContent = buttonLabel;

  if (!state?.images || state.images.length === 0) return;

  const fullImages = await requestFullImagesByIds(state?.plottedIds || []);

  if (fullImages && Array.isArray(fullImages.images)) {
    state.fullImages = fullImages.images;
  }

  renderMapTab(
    threadDomId,
    state.fullImages || [],
    null,
    state.context?.relation || null,
    false,
    state.context?.links || [],
    state.context,
    nextMode
  );
}

export function navigateObject(button , idx , direction , threadDomId) {
  const state = getOrCreateMapState(threadDomId);
  if (!state || !state.images || state.images.length === 0) return null;

  const card = button.closest(".map-image-card");
  const imageId = card?.dataset?.imageId ? Number(card.dataset.imageId) : null;
  const currentImage =
    (imageId && state.images.find((img) => Number(img.image_id) === imageId)) ||
    state.fullImages?.find((img) => Number(img.image_id) === imageId) ||
    state.images[idx] ||
    null;

  const objects = currentImage?.objects || currentImage?.object_instances || [];
  if (!objects.length) return null;

  const currentIdxObject = Number.isInteger(parseInt(button.dataset.currentObjectIdx, 10))
    ? parseInt(button.dataset.currentObjectIdx, 10)
    : 0;
  const delta = direction === "prev" ? -1 : 1;
  const newIndex = (currentIdxObject + delta + objects.length) % objects.length;

  const thumb = card?.querySelector(".thumb");
  const newThumbPath = objects[newIndex]?.cropped_file_path || objects[newIndex]?.cropped_path || null;
  if (thumb) {
    const fallbackPath = currentImage?.file_path || "";
    const nextPath = newThumbPath || fallbackPath;
    if (nextPath) thumb.src = `${window.appConfig.URL_for_images}${nextPath}`;
  }

  const labelEl = card?.querySelector(".map-object-label");
  const countEl = card?.querySelector(".map-object-count");
  const objectLabel = objects[newIndex]?.name || objects[newIndex]?.label || objects[newIndex]?.class || null;
  const objectId = objects[newIndex]?.object_id ?? objects[newIndex]?.id ?? null;
  if (labelEl) {
    labelEl.textContent = objectLabel || (objectId ? `Object #${objectId}` : "Object");
  }
  if (countEl) {
    countEl.textContent = `${newIndex + 1} / ${objects.length}`;
  }

  if (card) {
    card.querySelectorAll(".obj-nav-btn").forEach((btn) => {
      btn.dataset.currentObjectIdx = String(newIndex);
    });
    card.dataset.currentObjectIdx = String(newIndex);
  } else {
    button.dataset.currentObjectIdx = String(newIndex);
  }

  const imageKey = imageId || currentImage?.image_id || null;
  if (state.objectIndexByImage && imageKey) {
    state.objectIndexByImage.set(Number(imageKey), newIndex);
  }

  return newIndex;
}
