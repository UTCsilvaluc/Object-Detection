import { createPopupHTML } from "../popup.js";
import { getOrCreateMapState } from "./state.js";

export function buildGeoTimeline(imagesList = []) {
  return imagesList
    .map((img) => {
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

export function formatObjectLabel(obj = null) {
  if (!obj) return null;
  const id = obj.object_id ?? obj.id;
  const name = obj.name ?? obj.label ?? obj.class;
  if (id && name) return `${name} (#${id})`;
  if (id) return `Object #${id}`;
  return name || null;
}

export function getImageObjects(image = null) {
  return image?.objects || image?.object_instances || [];
}

export function getObjectThumbPath(obj = null) {
  return obj?.cropped_file_path || obj?.cropped_path || obj?.thumb || null;
}

function renderObjectBadge(obj = null) {
  if (!obj) return "";
  const label = formatObjectLabel(obj) || "Object";
  const thumb = obj.cropped_path || obj.thumb || null;
  const imgTag = thumb
    ? `<img src="${window.appConfig.URL_for_images}${thumb}" class="shared-thumb" alt="${label}">`
    : "";
  return `
    <div class="shared-obj-card">
      <div>${label}</div>
      ${imgTag}
      <a href="/objects-overview?ObjectID=${encodeURIComponent(obj.object_id || obj.id || "")}" target="_blank" rel="noopener noreferrer">See</a>
    </div>
  `;
}

function buildChronoPopup(fromItem, toItem, relation = null, objectLabel = null, linkReason = null, linkedObject = null) {
  const relationLabel =
    relation === "cooccurrence"
      ? "Co-occurrence link"
      : relation === "movement"
        ? "Movement link"
        : "Chronological link";

  const baseReason = linkReason
    ? linkReason
    : relation === "cooccurrence" && objectLabel
      ? `Images sharing ${objectLabel}`
      : objectLabel
        ? `Linked by ${objectLabel}`
        : "Linked by date order";

  const objectBadge = renderObjectBadge(linkedObject || null);
  const reason = `${baseReason}${objectBadge ? `<div style="margin-top:6px;">${objectBadge}</div>` : ""}`;
  const dateLine = `${fromItem.dateLabel} -> ${toItem.dateLabel}`;
  const locFrom = fromItem.raw.location_name || "Unknown place";
  const locTo = toItem.raw.location_name || "Unknown place";

  return `
    <div style="font-size:12px; line-height:1.4;">
      <strong>${relationLabel}</strong>
      <div>${reason}</div>
      <div>Date path: ${dateLine}</div>
      <div>From ${locFrom} to ${locTo}</div>
    </div>
  `;
}

function safeDateMs(date) {
  if (!date) return null;
  const ms = date instanceof Date ? date.getTime() : new Date(date).getTime();
  return Number.isFinite(ms) ? ms : null;
}

export function midpointLatLng(a, b) {
  const latA = Array.isArray(a) ? a[0] : a.lat;
  const lngA = Array.isArray(a) ? a[1] : a.lng;
  const latB = Array.isArray(b) ? b[0] : b.lat;
  const lngB = Array.isArray(b) ? b[1] : b.lng;
  return [(latA + latB) / 2, (lngA + lngB) / 2];
}

export function addChronoLinkDecorations(state, fromLatLng, toLatLng, color, stepLabel) {
  if (!state?.layer || !state?.map) return;

  const labelIcon = L.divIcon({
    className: "chrono-link-label-icon",
    html: `<div class="chrono-link-label" style="background:${color}; border-color:${color}; color:#fff;">${stepLabel}</div>`,
    iconSize: [1, 1]
  });
  const labelMarker = L.marker(midpointLatLng(fromLatLng, toLatLng), {
    icon: labelIcon,
    interactive: false,
    keyboard: false
  });
  labelMarker.addTo(state.layer);

  const ptA = state.map.latLngToLayerPoint(fromLatLng);
  const ptB = state.map.latLngToLayerPoint(toLatLng);
  const rotation = Math.atan2(ptB.y - ptA.y, ptB.x - ptA.x) * (180 / Math.PI);

  const arrowLatLng = [
    fromLatLng[0] + (toLatLng[0] - fromLatLng[0]) * 0.72,
    fromLatLng[1] + (toLatLng[1] - fromLatLng[1]) * 0.72
  ];
  const arrowIcon = L.divIcon({
    className: "chrono-link-arrow-icon",
    html: `<div class="chrono-link-arrow" style="--chrono-link-color:${color}; transform: translate(-50%, -50%) rotate(${rotation}deg);"></div>`,
    iconSize: [1, 1]
  });
  const arrowMarker = L.marker(arrowLatLng, {
    icon: arrowIcon,
    interactive: false,
    keyboard: false
  });
  arrowMarker.addTo(state.layer);
}

function computeChronoStepAssignments(rawLinks) {
  const links = (rawLinks || [])
    .map((l) => ({ ...l }))
    .filter((l) => l && l.key && Number.isFinite(l.fromId) && Number.isFinite(l.toId));

  links.forEach((l) => {
    const a = safeDateMs(l.fromDate);
    const b = safeDateMs(l.toDate);
    if (a !== null && b !== null && a > b) {
      const tmpId = l.fromId;
      l.fromId = l.toId;
      l.toId = tmpId;
      const tmpDate = l.fromDate;
      l.fromDate = l.toDate;
      l.toDate = tmpDate;
      l._reversed = true;
    } else {
      l._reversed = false;
    }
    l._fromMs = safeDateMs(l.fromDate) ?? 0;
    l._toMs = safeDateMs(l.toDate) ?? l._fromMs;
  });

  const parent = new Map();
  const find = (x) => {
    if (!parent.has(x)) parent.set(x, x);
    const px = parent.get(x);
    if (px !== x) parent.set(x, find(px));
    return parent.get(x);
  };
  const union = (a, b) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  };

  links.forEach((l) => union(l.fromId, l.toId));

  const byRoot = new Map();
  links.forEach((l) => {
    const root = find(l.fromId);
    if (!byRoot.has(root)) byRoot.set(root, []);
    byRoot.get(root).push(l);
  });

  const assignment = new Map();
  byRoot.forEach((compLinks) => {
    compLinks.sort(
      (a, b) =>
        a._fromMs - b._fromMs ||
        a._toMs - b._toMs ||
        String(a.key).localeCompare(String(b.key))
    );
    const total = compLinks.length;
    compLinks.forEach((l, idx) => {
      assignment.set(l.key, {
        step: idx + 1,
        total,
        fromId: l.fromId,
        toId: l.toId
      });
    });
  });

  return assignment;
}

function drawChronologicalLinks(state, timeline, relation = null, commonObject = null, links = []) {
  if (!state || !state.layer || !timeline || timeline.length < 2) return;

  const objectLabel = formatObjectLabel(commonObject);
  const byId = new Map(timeline.map((item) => [Number(item.raw.image_id), item]));
  const objectsByImage = new Map(
    timeline.map((item) => {
      const objMap = new Map();
      (item.raw.object_instances || []).forEach((o) => {
        objMap.set(Number(o.object_id), { id: Number(o.object_id), thumb: o.cropped_path || null });
      });
      return [Number(item.raw.image_id), objMap];
    })
  );
  const adjacency = new Map();

  const edges = (links || [])
    .map((l) => ({
      from: Number(l.from_image_id),
      to: Number(l.to_image_id),
      reason:
        l.metadata && l.metadata.length
          ? l.metadata
              .map(
                (md) =>
                  `${md.key}: ${md.target_value ?? md.value1 ?? "?"} ⇄ ${md.related_value ?? md.value2 ?? "?"}`
              )
              .join("<br>")
          : null
    }))
    .filter((e) => byId.has(e.from) && byId.has(e.to));

  if (edges.length === 0) {
    const ids = Array.from(byId.keys());
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = ids[i];
        const b = ids[j];
        const objsA = objectsByImage.get(a) || new Map();
        const objsB = objectsByImage.get(b) || new Map();
        const shared = Array.from(objsA.keys()).filter((id) => objsB.has(id));
        if (shared.length > 0) {
          const sharedDetails = shared.map((id) => {
            const fromObj = objsA.get(id);
            const toObj = objsB.get(id);
            return { id, thumb: fromObj?.thumb || toObj?.thumb || null };
          });
          const thumbsHTML = sharedDetails
            .map((s) => {
              const imgTag = s.thumb
                ? `<img src="${window.appConfig.URL_for_images}${s.thumb}" class="shared-thumb" alt="Object #${s.id}" />`
                : "";
              return `<div class="shared-obj-card"><div>#${s.id}</div>${imgTag}</div>`;
            })
            .join("");
          const reason = `
            <div style="font-size:12px;">
              <div>Objets communs :</div>
              <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">${thumbsHTML}</div>
              <a href="/objects-overview?ObjectID=${sharedDetails.map((s) => s.id).join(",")}" target="_blank" rel="noopener noreferrer">Voir les objets</a>
            </div>
          `;
          edges.push({ from: a, to: b, reason });
        }
      }
    }
  }

  const components = [];
  const visited = new Set();

  edges.forEach((e) => {
    if (!adjacency.has(e.from)) adjacency.set(e.from, []);
    if (!adjacency.has(e.to)) adjacency.set(e.to, []);
    adjacency.get(e.from).push(e.to);
    adjacency.get(e.to).push(e.from);
  });

  const buildComponent = (startNode) => {
    const stack = [startNode];
    const nodes = [];
    while (stack.length) {
      const node = stack.pop();
      if (visited.has(node)) continue;
      visited.add(node);
      nodes.push(node);
      (adjacency.get(node) || []).forEach((next) => {
        if (!visited.has(next)) stack.push(next);
      });
    }
    return nodes;
  };

  if (edges.length > 0) {
    edges.forEach((e) => {
      [e.from, e.to].forEach((node) => {
        if (!visited.has(node)) components.push(buildComponent(node));
      });
    });
  } else if (commonObject) {
    components.push(timeline.map((t) => Number(t.raw.image_id)));
  } else {
    return;
  }

  const edgeReasonMap = new Map();
  edges.forEach((e) => {
    const key1 = `${e.from}-${e.to}`;
    const key2 = `${e.to}-${e.from}`;
    if (e.reason) {
      edgeReasonMap.set(key1, e.reason);
      edgeReasonMap.set(key2, e.reason);
    }
  });

  components.forEach((comp) => {
    const entries = comp
      .map((id) => byId.get(id))
      .filter(Boolean)
      .sort((a, b) => (a.date?.getTime() || 0) - (b.date?.getTime() || 0));
    const total = Math.max(0, entries.length - 1);
    for (let idx = 1; idx < entries.length; idx++) {
      const prev = entries[idx - 1];
      const curr = entries[idx];
      const coords = [
        [prev.lat, prev.lng],
        [curr.lat, curr.lng]
      ];
      const reason =
        edgeReasonMap.get(`${Number(prev.raw.image_id)}-${Number(curr.raw.image_id)}`) || null;
      const stepLabel = `${idx} / ${total}`;
      const color = relation === "cooccurrence" ? "#0ea5e9" : "#2463eb";
      const popupHTML = `
        <div style="font-size:12px; line-height:1.4; margin-bottom:6px;">
          <div><strong>Step:</strong> ${stepLabel}</div>
        </div>
        ${buildChronoPopup(prev, curr, relation, objectLabel, reason, commonObject)}
      `;
      L.polyline(coords, { color, weight: 3, opacity: 0.85 }).bindPopup(popupHTML).addTo(state.layer);
      addChronoLinkDecorations(state, coords[0], coords[1], color, stepLabel);
    }
  });
}

function ensureThreadMap(threadDomId, center) {
  const state = getOrCreateMapState(threadDomId);
  const mapContainer = document.querySelector(`#${threadDomId} .thread-map`);
  if (!mapContainer) return state;

  if (!state.map) {
    state.layer = L.layerGroup();
    state.map = L.map(mapContainer.id, { dragging: true }).setView(center, 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OSM"
    }).addTo(state.map);
    state.layer.addTo(state.map);
  } else {
    setTimeout(() => state.map.invalidateSize(), 50);
  }

  return state;
}

export function refreshThreadMap(threadDomId) {
  const state = getOrCreateMapState(threadDomId);
  if (!state || !state.map) return;
  state.map.invalidateSize();
  if (state.bounds) state.map.fitBounds(state.bounds, { padding: [20, 20] });
}

function ensureMapPanel(container, threadDomId) {
  if (!container.querySelector(".map-panel")) {
    container.innerHTML = `
      <div class="map-panel">
        <div class="thread-map" id="map-${threadDomId.split("-")[1]}"></div>
        <div class="map-side">
          <h3>Moves over time</h3>
          <div class="map-image-list"></div>
        </div>
      </div>
    `;
  }

  const listEl = container.querySelector(".map-image-list");
  const mapEl = container.querySelector(".thread-map");
  return { listEl, mapEl };
}

function resetMapState(state) {
  state.layer.clearLayers();
  state.markers = new Map();
  state.plottedIds = new Set();
  state.drawnLinks = new Set();
  state.images = [];
  state.previousIds = new Set();
  state.colors = {};
}

function mergeImagesIntoState(state, newImages) {
  const merged = new Map();
  state.images.forEach((img) => merged.set(img.image_id, img));
  newImages.forEach((img) => merged.set(img.image_id, img));
  state.images = Array.from(merged.values());
}

function syncObjectIndex(state) {
  if (!state.objectIndexByImage) state.objectIndexByImage = new Map();
  const nextObjectIndexByImage = new Map();
  state.images.forEach((img) => {
    const imgId = Number(img.image_id);
    if (Number.isFinite(imgId) && state.objectIndexByImage.has(imgId)) {
      nextObjectIndexByImage.set(imgId, state.objectIndexByImage.get(imgId));
    }
  });
  state.objectIndexByImage = nextObjectIndexByImage;
}

function buildListLinkHint(relation, objectLabel) {
  if (relation === "thread") {
    return "Red: metadata • Purple: object presence • Green: movement (ordered by date)";
  }
  if (objectLabel) {
    return `Links explained by ${objectLabel} (ordered by date)`;
  }
  return "Links ordered by date";
}

function getObjectSelection(rawImage, state) {
  const objects = getImageObjects(rawImage);
  const objectCount = objects.length;
  const storedIdx = state.objectIndexByImage?.get(Number(rawImage.image_id));
  let objectIdx = Number.isInteger(storedIdx) ? storedIdx : 0;
  if (objectCount === 0) objectIdx = 0;
  if (objectIdx >= objectCount) objectIdx = 0;
  if (objectCount > 0) state.objectIndexByImage.set(Number(rawImage.image_id), objectIdx);
  return { objects, objectCount, objectIdx };
}

function buildMapCardHTML({
  raw,
  dateLabel,
  idx,
  focusImageId,
  mode,
  threadDomId,
  objectSelection
}) {
  const { objects, objectCount, objectIdx } = objectSelection;
  const selectedObject = objectCount > 0 ? objects[objectIdx] : null;
  const objectThumb = selectedObject ? getObjectThumbPath(selectedObject) : null;
  const imageThumb = raw.thumb_path || raw.file_path || "";
  const displayThumb =
    mode === "objects"
      ? objectThumb || imageThumb
      : imageThumb;
  const objectLabelText =
    selectedObject ? formatObjectLabel(selectedObject) || "Object" : "No objects detected";
  const objectCountText = objectCount > 0 ? `${objectIdx + 1} / ${objectCount}` : "0 / 0";
  const navDisabled = objectCount > 1 ? "" : "disabled";

  return `
    <div class="map-image-card ${raw.image_id == focusImageId ? "primary" : ""}" data-image-id="${raw.image_id}" data-timeline-idx="${idx}" data-current-object-idx="${objectIdx}">
      ${
        mode === "objects"
          ? `
            <div class="map-object-nav">
              <button class="obj-nav-btn left" data-currentObjectIdx="${objectIdx}" data-dir="prev" onclick="navigateObject(this , ${idx}, 'prev' , '${threadDomId}')" ${navDisabled}>◀</button>
              <button class="obj-nav-btn right" data-currentObjectIdx="${objectIdx}" data-dir="next" onclick="navigateObject(this , ${idx}, 'next', '${threadDomId}')" ${navDisabled}>▶</button>
            </div>
          `
          : ""
      }

      <img class="thumb map-object-thumb" src="${window.appConfig.URL_for_images + displayThumb}" alt="${raw.title ?? "Image"}">
      ${
        mode === "objects"
          ? `
            <div class="map-object-meta ${objectCount > 0 ? "" : "empty"}">
              <span class="map-object-count">${objectCountText}</span>
              <span class="map-object-label">${objectLabelText}</span>
            </div>
          `
          : ""
      }
      <strong>${raw.title ?? "Untitled image"}</strong>
      <small>${dateLabel}</small>
      <div>${raw.location_name ?? "Unknown location"}</div>
    </div>
  `;
}

function renderTimelineList({
  listEl,
  timeline,
  focusImageId,
  relation,
  objectLabel,
  mode,
  threadDomId,
  state
}) {
  if (timeline.length === 0) {
    listEl.innerHTML = `<p>No geolocated images for this selection.</p>`;
    return;
  }

  const linkHint = buildListLinkHint(relation, objectLabel);
  listEl.innerHTML = `
    <p><strong>${timeline.length} result(s)</strong></p>
    <p class="map-link-hint">${linkHint}</p>
    ${timeline
      .map(({ raw, dateLabel }, idx) =>
        buildMapCardHTML({
          raw,
          dateLabel,
          idx,
          focusImageId,
          mode,
          threadDomId,
          objectSelection: getObjectSelection(raw, state)
        })
      )
      .join("")}
  `;
}

function selectCardInList(listEl, imageId) {
  const id = Number(imageId);
  if (!Number.isFinite(id)) return;
  listEl.querySelectorAll(".map-image-card").forEach((card) => card.classList.remove("selected"));
  const card = listEl.querySelector(`.map-image-card[data-image-id="${id}"]`);
  if (card) {
    card.classList.add("selected");
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function focusMarkerOnMap(state, imageId, opts = {}) {
  const marker = state.markers.get(Number(imageId));
  if (!marker || !state.map) return;
  const zoom = Number.isFinite(opts.zoom) ? opts.zoom : 15;
  state.map.setView(marker.getLatLng(), zoom);
  if (opts.openPopup !== false) marker.openPopup();
}

function bindThumbZoom(listEl, onThumbClick) {
  if (listEl.dataset.thumbZoomBound) return;
  listEl.addEventListener("click", (event) => {
    const thumb = event.target.closest(".map-object-thumb");
    if (!thumb) return;
    const card = thumb.closest(".map-image-card");
    if (!card) return;
    const imageId = Number(card.dataset.imageId);
    if (!Number.isFinite(imageId)) return;
    onThumbClick(imageId);
  });
  listEl.dataset.thumbZoomBound = "true";
}

function collectMarkerCoords(state) {
  const coordsAll = [];
  state.markers.forEach((marker) => coordsAll.push([marker.getLatLng().lat, marker.getLatLng().lng]));
  return coordsAll;
}

function upsertMarkers({
  state,
  newTimeline,
  focusImageId,
  onMarkerClick
}) {
  let focusMarker = state.markers.get(Number(focusImageId)) || null;
  let focusLatLng = focusMarker ? focusMarker.getLatLng() : null;
  const coordsAll = collectMarkerCoords(state);

  newTimeline.forEach((item) => {
    if (state.plottedIds.has(item.raw.image_id)) return;
    const popupImage = { ...item.raw, latitude: item.lat, longitude: item.lng };
    const popupHTML = createPopupHTML(
      popupImage,
      window.appConfig.URL_for_images,
      window.appConfig.URL_for_view_image
    );
    const marker = L.marker([item.lat, item.lng]).bindPopup(popupHTML).addTo(state.layer);
    if (onMarkerClick) marker.on("click", () => onMarkerClick(item.raw.image_id));
    state.markers.set(item.raw.image_id, marker);
    state.plottedIds.add(item.raw.image_id);
    coordsAll.push([item.lat, item.lng]);
    if (item.raw.image_id == focusImageId) {
      focusMarker = marker;
      focusLatLng = marker.getLatLng();
    }
  });

  return { coordsAll, focusMarker, focusLatLng };
}

function splitLinksByType(links) {
  const allLinks = Array.isArray(links) ? links : [];
  return {
    allLinks,
    metadataLinks: allLinks.filter(
      (l) => l?.type === "metadata" || (Array.isArray(l?.metadata) && l.metadata.length > 0)
    ),
    presenceLinks: allLinks.filter((l) => l?.type === "object_presence"),
    movementLinks: allLinks.filter((l) => l?.type === "movement")
  };
}

function buildSharedObjectsHTML(imagesById, fromId, toId, objectIds = []) {
  const imgA = imagesById.get(Number(fromId));
  const imgB = imagesById.get(Number(toId));
  if (!imgA || !imgB) return "";
  const objsA = new Map((imgA.object_instances || []).map((o) => [Number(o.object_id), o]));
  const objsB = new Map((imgB.object_instances || []).map((o) => [Number(o.object_id), o]));
  const ids = (objectIds || []).length
    ? (objectIds || []).map(Number).filter((id) => objsA.has(id) && objsB.has(id))
    : Array.from(objsA.keys()).filter((id) => objsB.has(id));
  if (ids.length === 0) return "";
  const cards = ids
    .map((id) => {
      const thumb = objsA.get(id)?.cropped_path || objsB.get(id)?.cropped_path || null;
      const imgTag = thumb
        ? `<img src="${window.appConfig.URL_for_images}${thumb}" class="shared-thumb" alt="Object #${id}" />`
        : "";
      return `<div class="shared-obj-card"><div>#${id}</div>${imgTag}</div>`;
    })
    .join("");
  const link = `/objects-overview?ObjectID=${encodeURIComponent(ids.join(","))}`;
  return `
    <div style="font-size:12px;">
      <div>Objets communs :</div>
      <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">${cards}</div>
      <a href="${link}" target="_blank" rel="noopener noreferrer">Voir les objets</a>
    </div>
  `;
}

function computeThreadStepAssignments({ relation, presenceLinks, movementLinks, metadataLinks, timelineById }) {
  if (relation !== "thread") return null;
  return {
    presence: computeChronoStepAssignments(
      (presenceLinks || []).map((link) => ({
        key: `presence:${link.from_image_id}->${link.to_image_id}`,
        fromId: Number(link.from_image_id),
        toId: Number(link.to_image_id),
        fromDate: timelineById.get(Number(link.from_image_id))?.date || null,
        toDate: timelineById.get(Number(link.to_image_id))?.date || null
      }))
    ),
    movement: computeChronoStepAssignments(
      (movementLinks || []).map((link) => ({
        key: `movement:${link.from_image_id}->${link.to_image_id}:${(link.object_ids || []).join(",")}`,
        fromId: Number(link.from_image_id),
        toId: Number(link.to_image_id),
        fromDate: timelineById.get(Number(link.from_image_id))?.date || null,
        toDate: timelineById.get(Number(link.to_image_id))?.date || null
      }))
    ),
    metadata: computeChronoStepAssignments(
      (metadataLinks || []).map((link) => ({
        key: `${link.from_image_id}->${link.to_image_id}`,
        fromId: Number(link.from_image_id),
        toId: Number(link.to_image_id),
        fromDate: timelineById.get(Number(link.from_image_id))?.date || null,
        toDate: timelineById.get(Number(link.to_image_id))?.date || null
      }))
    )
  };
}

function drawThreadPresenceLinks({
  state,
  presenceLinks,
  stepAssignments,
  imagesById
}) {
  if (presenceLinks.length === 0) return;
  presenceLinks.forEach((link) => {
    const key = `presence:${link.from_image_id}->${link.to_image_id}`;
    if (state.drawnLinks?.has(key)) return;
    const step = stepAssignments?.presence?.get(key) || null;
    const fromId = step ? step.fromId : Number(link.from_image_id);
    const toId = step ? step.toId : Number(link.to_image_id);
    const fromMarker = state.markers.get(fromId);
    const toMarker = state.markers.get(toId);
    if (!fromMarker || !toMarker) return;

    const reason = buildSharedObjectsHTML(imagesById, link.from_image_id, link.to_image_id, link.object_ids || []);
    const stepLabel = step ? `${step.step} / ${step.total}` : null;
    const popupHtml = `
      <div style="font-size:12px;">
        <strong>Link by object presence</strong>
        ${stepLabel ? `<div style="margin-top:6px;"><strong>Step:</strong> ${stepLabel}</div>` : ""}
        <div style="margin-top:6px;">${reason || "Shared objects detected."}</div>
      </div>
    `;

    const color = "#7c3aed";
    const fromLatLng = fromMarker.getLatLng();
    const toLatLng = toMarker.getLatLng();
    L.polyline([fromLatLng, toLatLng], { color, weight: 3, opacity: 0.9 }).bindPopup(popupHtml).addTo(state.layer);
    if (stepLabel) addChronoLinkDecorations(state, [fromLatLng.lat, fromLatLng.lng], [toLatLng.lat, toLatLng.lng], color, stepLabel);
    state.drawnLinks.add(key);
  });
}

function drawThreadMovementLinks({
  state,
  movementLinks,
  stepAssignments,
  imagesById,
  timelineById
}) {
  if (movementLinks.length === 0) return;
  movementLinks.forEach((link) => {
    const key = `movement:${link.from_image_id}->${link.to_image_id}:${(link.object_ids || []).join(",")}`;
    if (state.drawnLinks?.has(key)) return;
    const step = stepAssignments?.movement?.get(key) || null;
    const fromId = step ? step.fromId : Number(link.from_image_id);
    const toId = step ? step.toId : Number(link.to_image_id);
    const fromMarker = state.markers.get(fromId);
    const toMarker = state.markers.get(toId);
    if (!fromMarker || !toMarker) return;

    const fromItem = timelineById.get(fromId);
    const toItem = timelineById.get(toId);
    const reason = buildSharedObjectsHTML(imagesById, link.from_image_id, link.to_image_id, link.object_ids || []);
    const stepLabel = step ? `${step.step} / ${step.total}` : null;

    const popupHtml =
      fromItem && toItem
        ? `
            <div style="font-size:12px; line-height:1.4; margin-bottom:6px;">
              ${stepLabel ? `<div><strong>Step:</strong> ${stepLabel}</div>` : ""}
            </div>
            ${buildChronoPopup(fromItem, toItem, "movement", null, reason || null, null)}
          `
        : `
            <div style="font-size:12px;">
              <strong>Movement link</strong>
              ${stepLabel ? `<div style="margin-top:6px;"><strong>Step:</strong> ${stepLabel}</div>` : ""}
              <div style="margin-top:6px;">${reason || "Chronological link."}</div>
            </div>
          `;

    const color = "#16a34a";
    const fromLatLng = fromMarker.getLatLng();
    const toLatLng = toMarker.getLatLng();
    L.polyline([fromLatLng, toLatLng], { color, weight: 3, opacity: 0.9 }).bindPopup(popupHtml).addTo(state.layer);
    if (stepLabel) addChronoLinkDecorations(state, [fromLatLng.lat, fromLatLng.lng], [toLatLng.lat, toLatLng.lng], color, stepLabel);
    state.drawnLinks.add(key);
  });
}

function drawThreadMetadataLinks({
  state,
  metadataLinks,
  stepAssignments,
  relation
}) {
  if (metadataLinks.length === 0) return;
  metadataLinks.forEach((link) => {
    const key = `${link.from_image_id}->${link.to_image_id}`;
    if (state.drawnLinks?.has(key)) return;
    const step = stepAssignments?.metadata?.get(key) || null;
    const fromId = step ? step.fromId : Number(link.from_image_id);
    const toId = step ? step.toId : Number(link.to_image_id);
    const fromMarker = state.markers.get(fromId);
    const toMarker = state.markers.get(toId);
    if (!fromMarker || !toMarker) return;

    const reasons = (link.metadata || [])
      .map((md) => {
        const tgt = md.target_value ?? "N/A";
        const rel = md.related_value ?? "N/A";
        return `<li><strong>${md.key}:</strong> ${tgt} ⇄ ${rel}</li>`;
      })
      .join("");

    const stepLabel = step ? `${step.step} / ${step.total}` : null;
    const popupHtml = `
      <div style="font-size:12px;">
        <strong>${relation === "thread" ? "Link by thread filters" : "Link by metadata"}</strong>
        ${stepLabel ? `<div style="margin-top:6px;"><strong>Step:</strong> ${stepLabel}</div>` : ""}
        <ul style="padding-left:16px; margin:6px 0;">${reasons || "<li>No details</li>"}</ul>
      </div>
    `;
    const color = "#e3342f";
    const fromLatLng = fromMarker.getLatLng();
    const toLatLng = toMarker.getLatLng();
    L.polyline([fromLatLng, toLatLng], { color, weight: 3, opacity: 0.9 }).bindPopup(popupHtml).addTo(state.layer);
    if (stepLabel) addChronoLinkDecorations(state, [fromLatLng.lat, fromLatLng.lng], [toLatLng.lat, toLatLng.lng], color, stepLabel);
    state.drawnLinks.add(key);
  });
}

function updateMapBounds(state, coordsAll, defaultCenter) {
  if (coordsAll.length > 0) {
    state.bounds = L.latLngBounds(coordsAll);
    state.map.fitBounds(state.bounds, { padding: [20, 20] });
  } else {
    state.bounds = null;
    state.map.setView(defaultCenter, 2);
  }
}

function focusInitialMarker(state, focusMarker, focusLatLng) {
  if (!focusMarker) return;
  setTimeout(() => {
    state.map.setView(focusLatLng, 15);
    focusMarker.openPopup();
  }, 300);
}

export function renderMapTab(
  threadDomId,
  imagesList,
  focusImageId = null,
  relation = null,
  append = false,
  links = [],
  context = {},
  mode = "images"
) {
  const container = document.querySelector(`#${threadDomId} .thread-content[data-section="map"]`);
  if (!container) return;

  const { listEl, mapEl } = ensureMapPanel(container, threadDomId);
  if (!listEl || !mapEl) return;

  const defaultCenter = [34.33, 134.05];
  const state = ensureThreadMap(threadDomId, defaultCenter);
  state.context = Object.assign({}, state.context || {}, context || {});
  state.context.viewMode = mode;
  const commonObject = state.context.commonObject || null;
  if (!state.map) return;

  if (!append) {
    resetMapState(state);
  }

  const newImages = imagesList || [];
  mergeImagesIntoState(state, newImages);
  syncObjectIndex(state);
  const timeline = buildGeoTimeline(state.images);
  const newTimeline = buildGeoTimeline(newImages);
  const objectLabel = formatObjectLabel(commonObject);

  renderTimelineList({
    listEl,
    timeline,
    focusImageId,
    relation,
    objectLabel,
    mode,
    threadDomId,
    state
  });

  bindThumbZoom(listEl, (imageId) => {
    selectCardInList(listEl, imageId);
    focusMarkerOnMap(state, imageId, { zoom: 15, openPopup: true });
  });

  const { coordsAll, focusMarker, focusLatLng } = upsertMarkers({
    state,
    newTimeline,
    focusImageId,
    onMarkerClick: (imageId) => selectCardInList(listEl, imageId)
  });

  const { allLinks, metadataLinks, presenceLinks, movementLinks } = splitLinksByType(links);

  if (relation !== "thread") {
    drawChronologicalLinks(state, timeline, relation, commonObject, allLinks);
  } else if (movementLinks.length === 0) {
    drawChronologicalLinks(state, timeline, relation, commonObject, metadataLinks.concat(presenceLinks));
  }

  const imagesById = new Map(state.images.map((img) => [Number(img.image_id), img]));
  const timelineById = new Map(timeline.map((item) => [Number(item.raw.image_id), item]));
  const stepAssignments = computeThreadStepAssignments({
    relation,
    presenceLinks,
    movementLinks,
    metadataLinks,
    timelineById
  });

  if (relation === "thread") {
    drawThreadPresenceLinks({ state, presenceLinks, stepAssignments, imagesById });
    drawThreadMovementLinks({ state, movementLinks, stepAssignments, imagesById, timelineById });
  }

  const drawMetadataLink = relation === "metadata" || relation === "thread";
  if (drawMetadataLink) {
    drawThreadMetadataLinks({ state, metadataLinks, stepAssignments, relation });
  }

  updateMapBounds(state, coordsAll, defaultCenter);

  if (state.previousIds && state.previousIds.size === 0) {
    state.previousIds = new Set(state.plottedIds);
  }

  focusInitialMarker(state, focusMarker, focusLatLng);
}
