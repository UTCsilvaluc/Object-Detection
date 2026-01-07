import { apiPost } from "../api.js";
import { addLinksToMap } from "../links.js";
import { mapState, setFilteredImages } from "./state.js";
import { applyFilters } from "./filters.js";
import { addPoints } from "./points.js";

export async function loadMapData() {
  const datas = await apiPost("/api/map-data", {});

  if (!datas || !datas.status) {
    alert("Failed to load map data");
    return;
  }

  mapState.images.push(...datas.images);
  setFilteredImages([...mapState.images]);

  mapState.icons.push(...datas.icons);
  mapState.points.push(...datas.points);

  mapState.objectsData = datas.object_datas || {};
  mapState.sharedObjects = datas.shared_objects || {};

  addPoints(mapState.pointsLayer, mapState.points);
  applyFilters();

  addLinksToMap(
    mapState.linesLayer,
    mapState.pointsLayer,
    mapState.map,
    mapState.links,
    mapState.markers,
    L
  );
}
