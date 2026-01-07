import { enableClustering } from "../data_visualization.js";
import { addLinksToMap, addSharedLinksToMap } from "../links.js";
import { mapState } from "./state.js";

export function refreshVisualization() {
  if (window.ClusterExpandActive) return;
  if (document.getElementById("toggle-cluster").checked) {
    enableClustering(
      mapState.map,
      mapState.clusters,
      mapState.markers,
      mapState.filteredImages,
      mapState.objectLinesLayer,
      mapState.linesLayer
    );
  }
  if (document.getElementById("toggle-show-links").checked) {
    addLinksToMap(
      mapState.linesLayer,
      mapState.pointsLayer,
      mapState.map,
      mapState.links,
      mapState.markers,
      L
    );
  }
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

export function enableZoomClustering(map) {
  map.on("zoomend", () => {
    if (!document.getElementById("toggle-cluster").checked) return;
    if (window.ClusterExpandActive) return;
    mapState.clusters.clearLayers();
    enableClustering(
      map,
      mapState.clusters,
      mapState.markers,
      mapState.filteredImages,
      mapState.objectLinesLayer,
      mapState.linesLayer
    );
  });
}

export function updateLinkOnZoom(map) {
  map.on("zoomend", () => {
    if (window.ClusterExpandActive) return;
    if (document.getElementById("toggle-show-links").checked) {
      addLinksToMap(
        mapState.linesLayer,
        mapState.pointsLayer,
        map,
        mapState.links,
        mapState.markers,
        L
      );
    }
    if (document.getElementById("toggle-shared-objects").checked) {
      addSharedLinksToMap(
        mapState.sharedObjectsLayer,
        map,
        mapState.sharedObjects,
        mapState.markers,
        L,
        mapState.objectsData
      );
    }
  });
}
