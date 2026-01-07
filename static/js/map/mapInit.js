import { mapState } from "./state.js";
import { enablePointAdding } from "./points.js";
import { enableZoomClustering, updateLinkOnZoom } from "./visualization.js";

const DEFAULT_CENTER = [34.33, 134.05];

export function initMap(position) {
  const userLat = position.coords.latitude || DEFAULT_CENTER[0];
  const userLon = position.coords.longitude || DEFAULT_CENTER[1];

  mapState.map = L.map("map", { dragging: true }).setView([userLat, userLon], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OSM"
  }).addTo(mapState.map);

  L.marker([userLat, userLon])
    .addTo(mapState.map)
    .bindPopup("You are here!")
    .openPopup();

  mapState.markers.addTo(mapState.map);
  mapState.clusters.addTo(mapState.map);
  mapState.pointsLayer.addTo(mapState.map);

  enableZoomClustering(mapState.map);
  updateLinkOnZoom(mapState.map);
  enablePointAdding(mapState.map);
  handleActionPropagation(L);
}

export function invalidateMapSize() {
  if (!mapState.map) return;
  clearTimeout(mapState.mapInvalidateTimer);
  mapState.mapInvalidateTimer = setTimeout(() => {
    mapState.map.invalidateSize();
  }, 200);
}

export function handleLocationError(error) {
  console.warn(`ERROR(${error.code}): ${error.message}`);
  initMap({ coords: { latitude: DEFAULT_CENTER[0], longitude: DEFAULT_CENTER[1] } });
}

function handleActionPropagation(leaflet) {
  const filterDiv = document.querySelector(".filter");
  const linkPanelDiv = document.getElementById("link-panel");
  leaflet.DomEvent.disableClickPropagation(filterDiv);
  leaflet.DomEvent.disableScrollPropagation(filterDiv);
  leaflet.DomEvent.disableClickPropagation(linkPanelDiv);
  leaflet.DomEvent.disableScrollPropagation(linkPanelDiv);
}
