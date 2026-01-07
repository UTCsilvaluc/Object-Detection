import { mapConfig } from "./state.js";

const SIDEBAR_PAGE_SIZE = 60;
const sidebarState = {
  items: [],
  rendered: 0,
  button: null
};

function createSidebarThumbnail(img) {
  const thumbDiv = document.createElement("div");
  thumbDiv.className = "image-thumbnail";
  thumbDiv.setAttribute("data-longitude", img.longitude);
  thumbDiv.setAttribute("data-latitude", img.latitude);
  const title = img.title || "Untitled";
  const description = img.description || "No description";
  const type = img.type || "Unknown";
  const imagePath = img.thumb_path || img.file_path;
  thumbDiv.innerHTML = `
        <img src="${mapConfig.URL_for_images + imagePath}" alt="${title}" loading="lazy" decoding="async">
        <div class="image-meta">
            <span class="image-title">${title}</span>
            <span class="image-desc">${description}</span>
            <span class="image-type">${type}</span>
        </div>
    `;
  return thumbDiv;
}

function getSidebarLoadMoreButton(sidebar) {
  if (sidebarState.button && sidebarState.button.isConnected) {
    return sidebarState.button;
  }
  const list = sidebar.querySelector("#image-list");
  if (!list) return null;
  const button = document.createElement("button");
  button.type = "button";
  button.id = "sidebar-load-more";
  button.className = "sidebar-load-more";
  button.addEventListener("click", () => {
    renderNextSidebarChunk();
  });
  list.appendChild(button);
  sidebarState.button = button;
  return button;
}

export function updateSidebarLoadMoreButton() {
  const sidebar = document.getElementById("sidebar-images");
  if (!sidebar) return;
  const button = getSidebarLoadMoreButton(sidebar);
  if (!button) return;
  const remaining = Math.max(0, sidebarState.items.length - sidebarState.rendered);
  if (remaining === 0) {
    button.style.display = "none";
    return;
  }
  button.style.display = "inline-flex";
  button.textContent = `Load more (${remaining})`;
}

export function renderNextSidebarChunk() {
  const sidebar = document.getElementById("sidebar-images");
  if (!sidebar) return;
  const thumbs = sidebar.querySelector(".image-thumbnails");
  if (!thumbs) return;
  const start = sidebarState.rendered;
  const end = Math.min(start + SIDEBAR_PAGE_SIZE, sidebarState.items.length);
  if (start >= end) return;

  const fragment = document.createDocumentFragment();
  for (let i = start; i < end; i += 1) {
    fragment.appendChild(createSidebarThumbnail(sidebarState.items[i]));
  }
  thumbs.appendChild(fragment);
  sidebarState.rendered = end;
  updateSidebarLoadMoreButton();
}

export function setSidebarItems(items) {
  sidebarState.items = items || [];
  sidebarState.rendered = 0;
}
