import { setTrashIcon } from "../utils.js";
import { setCrossIcon } from "../metadata.js";
import { loadMapData } from "./data.js";
import { bindMapUiEvents } from "./events.js";
import { applyFilters, bindFilterInputs, clearFilters, filterByMetadata, refreshFilteredImages, toggleFilter } from "./filters.js";
import { handleLocationError, initMap } from "./mapInit.js";
import { initMapStateGlobals, mapConfig } from "./state.js";
import { enableMapStorageListener } from "./storage.js";

function exposeGlobals() {
  window.toggleFilter = toggleFilter;
  window.applyFilters = applyFilters;
  window.clearFilters = clearFilters;
  window.refreshFilteredImages = refreshFilteredImages;
  window.filterByMetadata = filterByMetadata;
}

function bootstrap() {
  initMapStateGlobals();
  setCrossIcon(mapConfig.crossIcon);
  setTrashIcon(mapConfig.trashIcon);
  exposeGlobals();
  bindFilterInputs();
  bindMapUiEvents();

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      initMap(position);
      await loadMapData();
      enableMapStorageListener();
    },
    async (error) => {
      handleLocationError(error);
      await loadMapData();
      enableMapStorageListener();
    }
  );
}

export function initMapPage() {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
}
