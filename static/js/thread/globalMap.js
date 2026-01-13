import {
  addChronoLinkDecorations,
  buildGeoTimeline,
  formatObjectLabel,
  getImageObjects,
  getObjectThumbPath
} from "./mapView.js";
import { openInstancePreview } from "./instancePreview.js";

const globalMapState = {
  map: null,
  lineLayer: null,
  markerLayer: null,
  controlsEl: null,
  emptyEl: null,
  threadEntries: new Map(),
  objectColors: new Map(),
  fullImagesCache: new Map(),
  objectTimelines: new Map(),
  controlsBound: false,
  previewBound: false
};

const DEFAULT_CENTER = [34.33 , 134.05];

/**
 * Create the global map if not already created. Adds tile layer and base layers.
 * @returns {boolean} True if the map is ready, false otherwise.
 */
function ensureGlobalMap() {
  if (globalMapState.map) return true;
  const mapEl = document.getElementById("global-thread-map");
  if (!mapEl || typeof L === "undefined") return false;

  globalMapState.controlsEl = document.getElementById("global-thread-controls");
  globalMapState.emptyEl = document.getElementById("global-thread-empty");

  globalMapState.map = L.map(mapEl.id, { dragging: true }).setView(DEFAULT_CENTER, 2);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OSM"
  }).addTo(globalMapState.map);

  globalMapState.lineLayer = L.layerGroup().addTo(globalMapState.map);
  globalMapState.markerLayer = L.layerGroup().addTo(globalMapState.map);
  bindGlobalPreviewHandler();
  return true;
}

export function initGlobalThreadMap() {
  ensureGlobalMap();
}

export function getGlobalMapState() {
  return globalMapState;
}

function generateRandomColor() {
  return `#${((1 << 24) * Math.random() | 0).toString(16).padStart(6, "0")}`;
}

function getObjectColor(objectId) {
  const key = Number(objectId);
  if (globalMapState.objectColors.has(key)) return globalMapState.objectColors.get(key);
  const color = generateRandomColor();
  globalMapState.objectColors.set(key, color);
  return color;
}

function formatObjectLabelWithFallback(obj = null, fallbackId = null) {
  const id = obj?.object_id ?? obj?.id ?? fallbackId ?? null;
  const label = formatObjectLabel(obj);
  if (label) return label;
  if (id) return `Object #${id}`;
  return "Object";
}

function escapeHtmlAttr(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function getFullImageSrc(rawImage) {
  if (!rawImage) return "";
  const path = rawImage.file_path || rawImage.thumb_path || "";
  if (!path) return "";
  return `${window.appConfig.URL_for_images}${path}`;
}
/**
 * Create an object for the timeline. Ordered by date (buildGeoTimeline).
 * Return format : {imageId, lat, lng, date, dateLabel, imageTitle, location, croppedPath, rawImage}
 * @param {number} objectId ID of the object to build the timeline for.
 * @param {Array<Object>} images Images to build the timeline from.
 * @returns {Object[]} Timeline objects for the given objectId.
 */
function buildObjectTimeline(objectId, images) {
  return buildGeoTimeline(images || [])
    .map((item) => {
      const obj = getImageObjects(item.raw).find(
        (o) => Number(o?.object_id ?? o?.id) === Number(objectId)
      );
      if (!obj) return null;
      return {
        imageId: item.raw.image_id,
        lat: item.lat,
        lng: item.lng,
        date: item.date,
        dateLabel: item.dateLabel,
        imageTitle: item.raw.title || "Image",
        location: item.raw.location_name || "Unknown location",
        croppedPath: getObjectThumbPath(obj),
        rawImage: item.raw
      };
    })
    .filter(Boolean); // Remove nulls
}
/**
 * Build the HTML content for an object popup on the map. (When clicking a marker)
 * @param {string} param0.label Label of the object.
 * @param {Object} param0.item Timeline item for the object instance.
 * @returns {string} HTML content for the popup.
 */
function buildObjectPopup({ label, item }) {
  const fullSrc = getFullImageSrc(item?.rawImage);
  const subtitle = formatInstanceSubtitle(item);
  const thumb = item.croppedPath
    ? `<img src="${window.appConfig.URL_for_images}${item.croppedPath}" class="global-object-thumb" alt="${escapeHtmlAttr(label)}" data-full-src="${escapeHtmlAttr(fullSrc)}" data-title="${escapeHtmlAttr(item.imageTitle || label)}" data-subtitle="${escapeHtmlAttr(subtitle)}">`
    : "";
  return `
    <div class="global-object-popup">
      <div class="global-object-title">${label}</div>
      ${thumb}
      <div class="global-object-meta">${item.dateLabel}</div>
      <div class="global-object-meta">${item.location}</div>
    </div>
  `;
}

function updateGlobalEmptyState() {
  if (!globalMapState.emptyEl) return;
  globalMapState.emptyEl.classList.toggle("hidden", globalMapState.threadEntries.size > 0);
}
/** 
 * Update the map bounds to fit all enabled thread entries.
 */
function updateGlobalBounds() {
  const coords = [];
  globalMapState.threadEntries.forEach((entry) => {
    if (!entry.enabled) return;
    entry.coords.forEach((c) => coords.push(c));
  });
  if (!globalMapState.map) return;
  if (coords.length === 0) {
    globalMapState.map.setView(DEFAULT_CENTER, 2);
    return;
  }
  const bounds = L.latLngBounds(coords);
  globalMapState.map.fitBounds(bounds, { padding: [30, 30] });
}

function buildSortedObjectTimelines() {
  const merged = new Map();
  // Group by objectId across all enabled thread entries. objectId => {objectId, label, color, items: [], markers: []}
  globalMapState.threadEntries.forEach((entry) => {
    if (!entry.enabled) return;
    (entry.objects || []).forEach((obj) => {
      if (!merged.has(obj.objectId)) {
        merged.set(obj.objectId, {
          objectId: obj.objectId,
          label: obj.label,
          color: obj.color,
          items: [],
          markers: []
        });
      }
      const target = merged.get(obj.objectId);
      obj.timeline.forEach((item, idx) => {
        target.items.push(item);
        target.markers.push(obj.markers[idx]);
      });
    });
  });
  // Sort each object's items by date
  merged.forEach((value) => {
    const pairs = value.items.map((item, idx) => ({
      item,
      marker: value.markers[idx]
    }));
    pairs.sort((a, b) => {
      if (!a.item.date && !b.item.date) return 0;
      if (!a.item.date) return 1;
      if (!b.item.date) return -1;
      return a.item.date - b.item.date;
    });
    value.items = pairs.map((p) => p.item);
    value.markers = pairs.map((p) => p.marker);
  });

  return merged;
}

function formatInstanceSubtitle(item) {
  if (!item) return "";
  const date = item.dateLabel || "Unknown date";
  const place = item.location || "Unknown location";
  return `${date} • ${place}`;
}

function openFullImagePreview(item) {
  if (!item) return;
  const src = getFullImageSrc(item.rawImage);
  if (!src) return;
  openInstancePreview({
    src,
    title: item.imageTitle || "Image",
    subtitle: formatInstanceSubtitle(item)
  });
}
/**
 * Object Menu List rendering
 * @returns  {void}
 */
function renderObjectList() {
  if (!globalMapState.controlsEl) return;
  const timelines = buildSortedObjectTimelines();
  globalMapState.objectTimelines = timelines;

  if (timelines.size === 0) {
    globalMapState.controlsEl.innerHTML = `<div class="global-map-empty">No objects displayed.</div>`;
    return;
  }

  globalMapState.controlsEl.innerHTML = Array.from(timelines.values())
    .map((obj) => {
      const first = obj.items[0] || null;
      const thumb = first?.croppedPath ? `${window.appConfig.URL_for_images}${first.croppedPath}` : "";
      const fullSrc = getFullImageSrc(first?.rawImage);
      const countLabel = obj.items.length ? `1 / ${obj.items.length}` : "0 / 0";
      const subtitle = formatInstanceSubtitle(first);
      const navDisabled = obj.items.length > 1 ? "" : "disabled";
      return `
        <div class="global-object-card" data-object-id="${obj.objectId}" data-instance-idx="0">
          <div class="map-object-nav">
            <button class="obj-nav-btn left" data-dir="prev" ${navDisabled}>◀</button>
            <button class="obj-nav-btn right" data-dir="next" ${navDisabled}>▶</button>
          </div>
          <div class="global-object-header">
            <span class="global-object-swatch" style="background:${obj.color};"></span>
            <span class="map-object-label">${obj.label}</span>
          </div>
          <img class="thumb map-object-thumb global-object-thumb" src="${thumb}" alt="${escapeHtmlAttr(obj.label)}" data-full-src="${escapeHtmlAttr(fullSrc)}" data-title="${escapeHtmlAttr(first?.imageTitle || obj.label)}" data-subtitle="${escapeHtmlAttr(subtitle)}">
          <div class="map-object-meta ${obj.items.length ? "" : "empty"}">
            <span class="map-object-count">${countLabel}</span>
            <span class="global-object-sub">${subtitle}</span>
          </div>
        </div>
      `;
    })
    .join("");

  bindObjectListInteractions();
}

/**
 * Focus the map view on a specific object instance.
 * @param {number} objectId - The ID of the object.
 * @param {number} instanceIdx - The index of the instance in the timeline.
 */
function focusObjectInstance(objectId, instanceIdx) {
  const timeline = globalMapState.objectTimelines.get(Number(objectId));
  if (!timeline) return;
  const idx = Math.max(0, Math.min(instanceIdx, timeline.items.length - 1));
  const item = timeline.items[idx];
  const marker = timeline.markers[idx];
  if (!item || !marker || !globalMapState.map) return;
  globalMapState.map.setView([item.lat, item.lng], 15);
  marker.openPopup();
}

function updateObjectCard(card, timeline, nextIdx) {
  const item = timeline.items[nextIdx] || null;
  const thumb = item?.croppedPath ? `${window.appConfig.URL_for_images}${item.croppedPath}` : "";
  const fullSrc = getFullImageSrc(item?.rawImage);
  const countEl = card.querySelector(".map-object-count");
  const subtitleEl = card.querySelector(".global-object-sub");
  const thumbEl = card.querySelector(".global-object-thumb");
  if (countEl) countEl.textContent = `${nextIdx + 1} / ${timeline.items.length}`;
  if (subtitleEl) subtitleEl.textContent = formatInstanceSubtitle(item);
  if (thumbEl && thumb) {
    thumbEl.src = thumb;
    thumbEl.dataset.fullSrc = fullSrc;
    thumbEl.dataset.title = item?.imageTitle || "";
    thumbEl.dataset.subtitle = formatInstanceSubtitle(item);
  }
  card.dataset.instanceIdx = String(nextIdx);
}

function bindObjectListInteractions() {
  if (globalMapState.controlsBound || !globalMapState.controlsEl) return;
  globalMapState.controlsEl.addEventListener("click", (event) => {
    const navBtn = event.target.closest(".obj-nav-btn");
    const card = event.target.closest(".global-object-card");
    if (!card) return;

    if (navBtn) {
      const objectId = Number(card.dataset.objectId);
      const timeline = globalMapState.objectTimelines.get(objectId);
      if (!timeline || timeline.items.length === 0) return;
      const currentIdx = Number(card.dataset.instanceIdx) || 0;
      const delta = navBtn.dataset.dir === "prev" ? -1 : 1;
      const nextIdx = (currentIdx + delta + timeline.items.length) % timeline.items.length;
      updateObjectCard(card, timeline, nextIdx);
      focusObjectInstance(objectId, nextIdx);
      return;
    }

    const thumb = event.target.closest(".global-object-thumb");
    if (thumb) {
      const objectId = Number(card.dataset.objectId);
      const currentIdx = Number(card.dataset.instanceIdx) || 0;
      const timeline = globalMapState.objectTimelines.get(objectId);
      const item = timeline?.items?.[currentIdx] || null;
      if (item) {
        openFullImagePreview(item);
      }
      focusObjectInstance(objectId, currentIdx);
    }
  });
  globalMapState.controlsBound = true;
}

function bindGlobalPreviewHandler() {
  if (globalMapState.previewBound) return;
  document.addEventListener("click", (event) => {
    const thumb = event.target.closest(".global-object-thumb");
    if (!thumb) return;
    if (globalMapState.controlsEl && globalMapState.controlsEl.contains(thumb)) return;
    const fullSrc = thumb.dataset.fullSrc;
    if (!fullSrc) return;
    openInstancePreview({
      src: fullSrc,
      title: thumb.dataset.title || "Image",
      subtitle: thumb.dataset.subtitle || ""
    });
  });
  globalMapState.previewBound = true;
}

function ensureThreadToggle(threadEntry) {
  const container = document.getElementById(threadEntry.threadDomId);
  if (!container) return;
  const tabs = container.querySelector(".tabs-container");
  let toggle = container.querySelector(".thread-global-toggle");
  if (!toggle) {
    toggle = document.createElement("div");
    toggle.className = "thread-global-toggle";
    toggle.innerHTML = `
      <label>
        <input type="checkbox">
        <span></span>
      </label>
    `;
    container.insertBefore(toggle, tabs || container.firstChild);
  }

  const checkbox = toggle.querySelector("input[type='checkbox']");
  const label = toggle.querySelector("span");
  checkbox.checked = threadEntry.enabled;
  label.textContent = `Show on Global Map (${threadEntry.label})`;
  checkbox.onchange = () => {
    threadEntry.enabled = checkbox.checked;
    if (threadEntry.enabled) {
      threadEntry.layer.addTo(globalMapState.map);
    } else {
      globalMapState.map.removeLayer(threadEntry.layer);
    }
    renderObjectList();
    updateGlobalBounds();
  };
  threadEntry.controlEl = toggle;
}

function computeMarkerOffset(objectId, idx) {
  const seed = Math.abs(Number(objectId) || 0) + idx * 7;
  const angle = (seed % 360) * (Math.PI / 180);
  const radius = 0.00035 + (idx % 3) * 0.00015;
  return {
    lat: Math.sin(angle) * radius,
    lng: Math.cos(angle) * radius
  };
}

/**
 * Draw the full movement timeline for a single object on the global map.
 * Places one marker per occurrence and connects them in order,
 * @param {Object} params
 * @param {L.LayerGroup} params.layer Leaflet layer group to draw into.
 * @param {L.Map} params.map Leaflet map instance.
 * @param {number|string} objectId Object identifier (used for stable marker offset).
 * @param {string} objectLabel Label displayed in tooltips/popups.
 * @param {Array} timeline Ordered occurrences of the object (lat/lng/date/crop/etc).
 * @param {string} color Stroke/fill color for markers and links.
 * @returns {{ pointCount: number, coords: Array, markers: Array }}
 */
function drawObjectTimeline({ layer, map }, objectId, objectLabel, timeline, color) {
  if (!timeline || timeline.length === 0) return { pointCount: 0, coords: [], markers: [] };
  const state = { map, layer };
  const coords = [];
  const markers = [];
  timeline.forEach((item, idx) => {
    const offset = computeMarkerOffset(objectId, idx);
    const lat = item.lat + offset.lat;
    const lng = item.lng + offset.lng;
    coords.push([lat, lng]);
    const marker = L.circleMarker([lat, lng], {
      radius: 6,
      color,
      fillColor: color,
      fillOpacity: 0.9,
      weight: 2
    }).addTo(layer);
    marker.bindPopup(buildObjectPopup({ label: objectLabel, item }));
    marker.bindTooltip(`${objectLabel} • ${idx + 1}`, { direction: "top", offset: [0, -6] });
    markers.push(marker);
  });
  const total = Math.max(0, timeline.length - 1);
  for (let idx = 1; idx < timeline.length; idx++) {
    const prev = timeline[idx - 1];
    const curr = timeline[idx];
    const stepLabel = `${idx} / ${total}`;
    const coordsPair = [
      [prev.lat, prev.lng],
      [curr.lat, curr.lng]
    ];
    L.polyline(coordsPair, { color, weight: 3, opacity: 0.75 }).addTo(layer);
    addChronoLinkDecorations(state, coordsPair[0], coordsPair[1], color, stepLabel);
  }
  return { pointCount: timeline.length, coords, markers };
}

async function fetchFullImages(imageIds) {
  if (!imageIds || imageIds.length === 0) return [];
  const { requestFullImagesByIds } = await import("./searchController.js");
  const cached = [];
  const missing = [];
  imageIds.forEach((id) => {
    const key = Number(id);
    if (!Number.isFinite(key)) return;
    if (globalMapState.fullImagesCache.has(key)) {
      cached.push(globalMapState.fullImagesCache.get(key));
    } else {
      missing.push(key);
    }
  });

  if (missing.length === 0) return cached;

  const payload = await requestFullImagesByIds(missing);
  if (!payload || !Array.isArray(payload.images)) return cached;
  payload.images.forEach((img) => {
    const key = Number(img.image_id);
    if (!Number.isFinite(key)) return;
    globalMapState.fullImagesCache.set(key, img);
    cached.push(img);
  });
  return cached;
}

async function resolveThreadImages({ mode, seedImageId, imagesFromThread }) {
  const baseImages = Array.isArray(imagesFromThread) ? imagesFromThread : [];
  if (baseImages.length > 0) return baseImages;
  if (mode !== "image") return baseImages;
  const imageId = Number(seedImageId);
  if (!Number.isFinite(imageId)) return baseImages;
  const { apiPost } = await import("../api.js");
  const data = await apiPost("/thread/show_results", { mode: "image", image_id: imageId });
  if (data && Array.isArray(data.images)) return data.images;
  return baseImages;
}
/**
 * Find all objects to be used as seeds for the map thread entry.
 * If image, fetch objects from that image.
 * @param {*} param0 
 * @returns 
 */
function collectSeedObjectsFromImage(image) {
  if (!image) return [];
  const objects = getImageObjects(image);
  if (!objects.length) return [];
  return objects.map((obj) => ({
    object_id: obj.object_id ?? obj.id,
    name: obj.name,
    label: obj.label,
    class: obj.class,
    cropped_path: getObjectThumbPath(obj)
  }));
}

async function resolveSeedObjects({ mode, seedObjects, seedImageId, imagesFromThread }) {
  if (Array.isArray(seedObjects) && seedObjects.length > 0) return seedObjects;
  if (mode === "image" && seedImageId) {
    const imageId = Number(seedImageId);
    if (!Number.isFinite(imageId)) return [];
    const merged = new Map();
    const threadImage = (imagesFromThread || []).find(
      (img) => Number(img?.image_id) === imageId
    );
    collectSeedObjectsFromImage(threadImage).forEach((obj) => {
      if (obj?.object_id) merged.set(Number(obj.object_id), obj);
    });
    const cachedImage = globalMapState.fullImagesCache.get(imageId) || null;
    const images = cachedImage ? [cachedImage] : await fetchFullImages([imageId]);
    const first = images[0] || cachedImage || null;
    collectSeedObjectsFromImage(first).forEach((obj) => {
      if (obj?.object_id) merged.set(Number(obj.object_id), obj);
    });
    return Array.from(merged.values());
  }
  return [];
}

export async function addThreadToGlobalMap({
  threadDomId,
  mode,
  seedObjects,
  seedImageId,
  imagesFromThread
}) {
  if (!ensureGlobalMap()) return;
  if (!threadDomId || !Array.isArray(imagesFromThread)) return;

  const objectSeeds = await resolveSeedObjects({ mode, seedObjects, seedImageId, imagesFromThread });
  if (!objectSeeds.length) return;

  const resolvedImages = await resolveThreadImages({ mode, seedImageId, imagesFromThread });
  const imageIds = (resolvedImages || [])
    .map((img) => Number(img.image_id))
    .filter((id) => Number.isFinite(id));
  const fullImages = await fetchFullImages(imageIds);
  if (!fullImages.length) return;

  const threadLabel = `Thread ${threadDomId.split("-")[1]}`;
  const layer = L.layerGroup().addTo(globalMapState.map);
  const entry = {
    threadDomId,
    label: threadLabel,
    layer,
    enabled: true,
    controlEl: null,
    objectCount: 0,
    pointCount: 0,
    coords: [],
    objects: []
  };

  objectSeeds.forEach((obj) => {
    const objectId = obj.object_id ?? obj.id;
    if (!objectId) return;
    const color = getObjectColor(objectId);
    const label = formatObjectLabelWithFallback(obj, objectId);
    const timeline = buildObjectTimeline(objectId, fullImages);
    if (!timeline.length) return;
    const { pointCount, coords, markers } = drawObjectTimeline(
      { layer, map: globalMapState.map },
      objectId,
      label,
      timeline,
      color
    );
    entry.objectCount += 1;
    entry.pointCount += pointCount;
    entry.coords.push(...coords);
    entry.objects.push({
      objectId: Number(objectId),
      label,
      color,
      timeline,
      markers
    });
  });

  if (entry.pointCount === 0) {
    globalMapState.map.removeLayer(layer);
    return;
  }

  globalMapState.threadEntries.set(threadDomId, entry);
  ensureThreadToggle(entry);
  updateGlobalEmptyState();
  renderObjectList();
  updateGlobalBounds();
}
