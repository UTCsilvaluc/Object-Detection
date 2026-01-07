import { apiPost } from "../api.js";
import { addSharedLinksToMap } from "../links.js";
import { mapState } from "./state.js";
import { applyFilters } from "./filters.js";
import { clearTempMarker } from "./points.js";

export function enableMapStorageListener() {
  window.addEventListener("storage", async (event) => {
    if (event.key === "upload_done") {
      const data = JSON.parse(event.newValue);
      const pending = localStorage.getItem("upload_pending");
      if (pending && pending.token === data.token) {
        const image = data.image;
        localStorage.removeItem("upload_pending");
        localStorage.removeItem("upload_done");
        mapState.images.push(image);
        mapState.filteredImages.push(image);
        applyFilters();
        alert("AI Image uploaded and added to the map successfully.");
        const dataReq = await apiPost("objects/link_between_objects", {});
        if (dataReq.status === "success") {
          mapState.objectsData = dataReq.object_datas;
          mapState.sharedObjects = dataReq.shared_objects;
          if (document.getElementById("toggle-shared-objects").checked) {
            addSharedLinksToMap(
              mapState.sharedObjectsLayer,
              mapState.map,
              mapState.sharedObjects,
              mapState.markers,
              L,
              mapState.objectsData
            );
          }
        }
        if (mapState.tempMarker) {
          clearTempMarker();
          document.getElementById("sidebar").classList.add("visible");
        }
      }
    }
  });
}
