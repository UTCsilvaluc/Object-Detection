import { addMetadataField } from "../metadata.js";
import { saveData, uploadAIImage } from "../api.js";
import { addPoint, createPopupAddPoint, createPopupPoint, getHTMLForSVGIcon } from "../popup.js";
import { disableClustering } from "../data_visualization.js";
import { mapConfig, mapState, setTempMarker } from "./state.js";

export function addPoints(layer, points) {
  let iconURL = mapConfig.URL_for_icons;
  points.forEach((point) => {
    iconURL = point.icon_svg_path ? mapConfig.URL_for_icons + point.icon_svg_path : null;
    const icon = L.divIcon({
      className: "point-icon",
      html: getHTMLForSVGIcon(iconURL, point.color_hex || "#000000")
    });
    point.iconURL = iconURL;
    const popupContent = createPopupPoint(point);
    addPoint(L, point, icon, layer, popupContent);
  });
}

export function addMetaData(id) {
  if (mapState.metadataKeysAvailable.length === 0) {
    alert("No more metadata keys available to add.");
    return;
  }
  addMetadataField(id);
}

export function clearTempMarker() {
  if (!mapState.tempMarker || !mapState.map) return;
  mapState.map.removeLayer(mapState.tempMarker);
  document.querySelectorAll(".popup-add-point").forEach((el) => el.remove());
  setTempMarker(null);
}

export function enablePointAdding(map) {
  map.on("click", (e) => {
    if (window.enableLinkCreation) return;
    if (mapState.tempMarker) {
      clearTempMarker();
      if (document.getElementById("toggle-filters").checked) {
        document.getElementById("sidebar").classList.add("visible");
      }
      return;
    }
    if (window.expandedMarkers.length > 0) {
      window.ClusterExpandActive = false;
      disableClustering(map, mapState.clusters, mapState.markers, mapState.filteredImages);
      return;
    }
    document.getElementById("sidebar").classList.remove("visible");
    const { lat, lng } = e.latlng;

    if (mapState.tempMarker) {
      clearTempMarker();
    }

    const tempMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: "temp-marker-icon",
        html: `<div style="width:24px; height:24px; background:#000000; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`
      })
    }).addTo(map);
    setTempMarker(tempMarker);
    const popupHTML = createPopupAddPoint(mapState.icons, mapConfig.URL_for_icons, lat, lng);

    tempMarker.bindPopup(popupHTML).openPopup();
    document.getElementById("add-metadata-btn").addEventListener("click", () => {
      addMetaData(0);
    });
    document.getElementById("save-point-btn").addEventListener("click", async () => {
      await saveData(map, lat, lng, tempMarker, mapState.pointsLayer);
    });
    document.getElementById("ai-upload-btn").addEventListener("click", () => {
      uploadAIImage(lat, lng);
    });
    document.querySelectorAll(".icon-preview .icon").forEach((img) => {
      img.addEventListener("click", (event) => {
        document.querySelectorAll(".icon-preview .icon").forEach((i) => i.classList.remove("selected"));
        const color = document.getElementById("point-color").value;
        event.target.classList.add("selected");
        const selectedIcon = event.target.getAttribute("src");
        const selectedIconElem = document.querySelector(".icon-preview .icon.selected");
        if (selectedIconElem) {
          tempMarker.setIcon(
            L.divIcon({
              className: "temp-marker-icon",
              html: getHTMLForSVGIcon(selectedIcon, color)
            })
          );
        } else {
          tempMarker.setIcon(
            L.divIcon({
              className: "temp-marker-icon",
              html: `<div style="width:24px; height:24px; background:${color}; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`
            })
          );
        }
      });
    });
    document.getElementById("point-color").addEventListener("change", (event) => {
      const color = event.target.value;
      const selectedIconElem = document.querySelector(".icon-preview .icon.selected");
      if (!selectedIconElem) {
        tempMarker.setIcon(
          L.divIcon({
            className: "temp-marker-icon",
            html: `<div style="width:24px; height:24px; background:${color}; transform:rotate(45deg); border-radius:4px; border:2px solid white; box-shadow:0 1px 2px rgba(0,0,0,.35);"></div>`
          })
        );
      } else {
        const iconUrl = selectedIconElem.getAttribute("src");
        tempMarker.setIcon(
          L.divIcon({
            className: "temp-marker-icon",
            html: getHTMLForSVGIcon(iconUrl, color)
          })
        );
      }
    });
  });
}
