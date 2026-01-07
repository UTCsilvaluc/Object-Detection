import { createPopupHTML } from "../popup.js";
import { handleLinkCreationClick } from "../links.js";
import { mapConfig, mapState, setCheckClasses, setFilteredImages } from "./state.js";
import { renderNextSidebarChunk, setSidebarItems, updateSidebarLoadMoreButton } from "./sidebar.js";
import { refreshVisualization } from "./visualization.js";

function rebuildTimeline() {
  if (typeof window.buildTimelineFromFilteredImages === "function") {
    window.buildTimelineFromFilteredImages(mapState.filteredImages, mapConfig.URL_for_images);
  }
}

export function toggleFilter(filterId) {
  const filterDiv = document.getElementById(filterId);
  if (filterDiv) {
    filterDiv.classList.toggle("visible");
  }
}

export function applyFilters() {
  const sidebar = document.getElementById("sidebar-images");
  mapState.markers.clearLayers();
  if (sidebar) {
    const thumbs = sidebar.querySelector(".image-thumbnails");
    if (thumbs) {
      thumbs.innerHTML = "";
    }
  }

  setSidebarItems(mapState.filteredImages);
  renderNextSidebarChunk();
  updateSidebarLoadMoreButton();

  mapState.filteredImages.forEach((img) => {
    if (!img.latitude || !img.longitude) return;
    const icon = L.icon({
      iconUrl: mapConfig.URL_for_images + img.file_path,
      iconSize: [80, 80],
      iconAnchor: [22, 94],
      popupAnchor: [-3, -76]
    });
    L.marker([img.latitude, img.longitude], { icon })
      .bindPopup(createPopupHTML(img, mapConfig.URL_for_images, mapConfig.URL_for_view_image))
      .addTo(mapState.markers)
      .addEventListener("click", (e) => {
        if (window.enableLinkCreation) {
          handleLinkCreationClick(img, e.target, "image", mapConfig.URL_for_images);
        }
      });
  });

  refreshVisualization();
  rebuildTimeline();
}

export function clearFilters() {
  setCheckClasses([...mapState.classes]);
  setFilteredImages([...mapState.images]);
  document.querySelectorAll('.class-list input[type="checkbox"]').forEach((checkbox) => {
    checkbox.checked = true;
  });
  document.getElementById("start-date").value = "";
  document.getElementById("end-date").value = "";
  applyFilters();
}

export function checkAllFilters(image) {
  if (image.type && !mapState.checkClasses.includes(image.type)) {
    return false;
  }
  const startDate = document.getElementById("start-date").value;
  const endDate = document.getElementById("end-date").value;
  const rawDate = image.capture_date || image.event_date || null;
  const imgDate = rawDate ? new Date(rawDate) : null;

  if (startDate || endDate) {
    if (!imgDate || isNaN(imgDate)) return false;
    if (startDate && imgDate < new Date(startDate)) return false;
    if (endDate && imgDate > new Date(endDate)) return false;
  }

  if (!filterByMetadata(image)) {
    return false;
  }
  return true;
}

export function filterByMetadata(image) {
  const metadatasRequired = Array.from(
    document.querySelectorAll('#metadata-filter input[type="checkbox"]:checked')
  ).map((cb) => cb.value);
  const metadatasContainingInImages = {};
  if (image.objects === undefined || image.objects.length === 0) {
    return metadatasRequired.length === 0;
  }
  image.objects.forEach((obj) => {
    metadatasContainingInImages[image.image_id] = metadatasContainingInImages[image.image_id] || new Set();
    Object.keys(obj.metadatas).forEach((key) => {
      if (obj.metadatas[key].key && !(metadatasContainingInImages[image.image_id].has(obj.metadatas[key].key))) {
        metadatasContainingInImages[image.image_id].add(obj.metadatas[key].key);
      }
    });
  });
  for (let i = 0; i < metadatasRequired.length; i += 1) {
    const key = metadatasRequired[i];
    if (
      !(metadatasContainingInImages[image.image_id] && metadatasContainingInImages[image.image_id].has(key))
    ) {
      return false;
    }
  }
  return true;
}

export function refreshFilteredImages() {
  setFilteredImages(mapState.images.filter(checkAllFilters));
  applyFilters();
}

export function bindFilterInputs() {
  document.querySelectorAll('.class-list input[type="checkbox"]').forEach((checkbox) => {
    checkbox.addEventListener("change", (event) => {
      const className = event.target.value;
      let next = mapState.checkClasses;
      if (event.target.checked) {
        next = next.includes(className) ? next : [...next, className];
      } else {
        next = next.filter((c) => c !== className);
      }
      setCheckClasses(next);
      refreshFilteredImages();
    });
  });

  document.querySelectorAll('.filter-class input[type="date"]').forEach((input) => {
    input.addEventListener("change", () => {
      const startDate = document.getElementById("start-date");
      const endDate = document.getElementById("end-date");
      if (startDate && endDate && new Date(startDate.value) > new Date(endDate.value)) {
        alert("Start date cannot be after end date.");
        startDate.value = "";
        return;
      }
      refreshFilteredImages();
    });
  });
}
