import { apiPost } from "../api.js";
import { disableClustering, enableClustering } from "../data_visualization.js";
import { addLinksToMap, addSharedLinksToMap, clearLinkCreationForm } from "../links.js";
import { controlInputValues, getGeoJSONFileInput, getMetadataFromFields, showGeoStatus } from "../utils.js";
import { addMetaData } from "./points.js";
import { applyFilters, checkAllFilters } from "./filters.js";
import { invalidateMapSize } from "./mapInit.js";
import { mapState, setFilteredImages, setLastTimelineImageId } from "./state.js";

export function bindMapUiEvents() {
  const toggleCluster = document.getElementById("toggle-cluster");
  if (toggleCluster) {
    toggleCluster.addEventListener("change", (event) => {
      if (event.target.checked) {
        enableClustering(
          mapState.map,
          mapState.clusters,
          mapState.markers,
          mapState.filteredImages,
          mapState.objectLinesLayer,
          mapState.linesLayer
        );
      } else {
        disableClustering(mapState.map, mapState.clusters, mapState.markers, mapState.filteredImages);
      }
    });
  }

  const toggleTimeline = document.getElementById("toggle-timeline");
  if (toggleTimeline) {
    toggleTimeline.addEventListener("change", (event) => {
      if (event.target.checked) {
        document.getElementById("sidebar-timeline").classList.add("visible");
      } else {
        document.getElementById("sidebar-timeline").classList.remove("visible");
      }
      invalidateMapSize();
    });
  }

  const importGeojson = document.getElementById("import-geojson");
  if (importGeojson) {
    importGeojson.addEventListener("click", () => {
      alert("Feature to import GeoJSON coming soon!");
    });
  }

  const importOther = document.getElementById("import-other");
  if (importOther) {
    importOther.addEventListener("click", () => {
      alert("Feature to import custom datasets coming soon!");
    });
  }

  const toggleSidebar = document.getElementById("toggle-sidebar");
  if (toggleSidebar) {
    toggleSidebar.addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar-images");
      sidebar.classList.toggle("visible");
      invalidateMapSize();
    });
  }

  const sidebarImages = document.getElementById("sidebar-images");
  if (sidebarImages) {
    sidebarImages.addEventListener("click", (event) => {
      const thumb = event.target.closest(".image-thumbnail");
      if (!thumb) return;
      const longitude = parseFloat(thumb.getAttribute("data-longitude"));
      const latitude = parseFloat(thumb.getAttribute("data-latitude"));
      if (!isNaN(latitude) && !isNaN(longitude)) {
        mapState.map.setView([latitude, longitude], 15);
      }
    });
  }

  const addMetadataLink = document.getElementById("add-metadata-link");
  if (addMetadataLink) {
    addMetadataLink.addEventListener("click", () => {
      addMetaData(1);
    });
  }

  const sidebarTimeline = document.getElementById("sidebar-timeline");
  if (sidebarTimeline) {
    sidebarTimeline.addEventListener("timeline:active-change", (event) => {
      const detail = event.detail || {};
      const imageId = Number(detail.imageId);
      if (Number.isFinite(imageId) && imageId === mapState.lastTimelineImageId) return;
      const lat = parseFloat(detail.latitude);
      const lon = parseFloat(detail.longitude);
      if (!isNaN(lat) && !isNaN(lon)) {
        mapState.map.panTo([lat, lon], { animate: false });
        if (Number.isFinite(imageId)) setLastTimelineImageId(imageId);
      }
    });
  }

  const toggleFilters = document.getElementById("toggle-filters");
  if (toggleFilters) {
    toggleFilters.addEventListener("change", (event) => {
      const filterDiv = document.querySelector(".filter");
      if (event.target.checked) {
        filterDiv.classList.add("visible");
      } else {
        filterDiv.classList.remove("visible");
      }
    });
  }

  const toggleAddLinks = document.getElementById("toggle-add-links");
  if (toggleAddLinks) {
    toggleAddLinks.addEventListener("change", (event) => {
      if (event.target.checked) {
        window.enableLinkCreation = true;
        document.body.style.cursor = "crosshair";
        document.getElementById("toggle-filters").checked = false;
        document.querySelector(".filter").classList.remove("visible");
        document.getElementById("link-panel").classList.toggle("hidden");
      } else {
        clearLinkCreationForm(mapState.markers, mapState.pointsLayer);
      }
    });
  }

  const linkTypeSelect = document.getElementById("link-type");
  if (linkTypeSelect) {
    linkTypeSelect.addEventListener("change", async (event) => {
      if (event.target.value === "__new__") {
        const key = prompt("Enter the key of the new link type:");
        const label = prompt("Enter the label of the new link type:");
        if (key && label) {
          const data = await apiPost("/save/save_link_type", {
            key: key,
            label: label
          });
          if (data.success) {
            const option = document.createElement("option");
            option.value = key;
            option.text = label;
            event.target.add(option, event.target.options[event.target.options.length - 1]);
            event.target.value = key;
          } else {
            alert("Failed to add new link type: " + data.message);
            event.target.value = event.target.options[0].value;
          }
        } else {
          event.target.value = event.target.options[0].value;
        }
      } else {
        const currentValue = event.target.value;
        const linkTitles = mapState.links
          .filter((link) => link.link_type == currentValue)
          .map((link) => link.title);
        const dataList = document.getElementById("existingLinkTitles");
        dataList.innerHTML = "";
        dataList.innerHTML = linkTitles
          .map(
            (title) => `
            <option value="${title}">
            <h2>Type : ${currentValue}</h2>
            </option>
       `
          )
          .join("");
      }
    });
  }

  const saveLink = document.getElementById("save-link");
  if (saveLink) {
    saveLink.addEventListener("click", async () => {
      const title = document.getElementById("link-title").value;
      const description = document.getElementById("link-description").value;
      const linkType = document.getElementById("link-type").value;
      const linkTitleInput = document.getElementById("link-title").value;
      controlInputValues(title, description, linkType, linkTitleInput);
      const container = document.getElementById("selected-items");
      if (container.childElementCount < 2) {
        alert("Please select at least two items to create a link.");
        return;
      }
      const items = Array.from(container.children);
      const metaDataContainer = document.getElementById("meta-1");
      const metadata = getMetadataFromFields(metaDataContainer.querySelectorAll(".meta-field"));
      const GeoJSON = await getGeoJSONFileInput();
      const linkData = {
        title,
        description,
        metadata: metadata,
        link_type: linkType,
        endpoints: items.map((item, index) => ({
          entity_type: item.getAttribute("type"),
          image_id: item.getAttribute("type") === "image" ? item.getAttribute("itemID") : null,
          point_id: item.getAttribute("type") === "point" ? item.getAttribute("itemID") : null,
          order_index: index,
          latitude: parseFloat(item.getAttribute("latitude")),
          longitude: parseFloat(item.getAttribute("longitude")),
          role: "waypoint"
        })),
        metadata,
        geometry: GeoJSON ? GeoJSON.geojson : null
      };
      const data = await apiPost("/save/save_link", {
        link: linkData
      });
      if (data.status == "success") {
        linkData.id = data.link_id;
        mapState.links.push(linkData);
        addLinksToMap(mapState.linesLayer, mapState.pointsLayer, mapState.map, mapState.links, mapState.markers, L);
        clearLinkCreationForm(mapState.markers, mapState.pointsLayer);
      } else {
        alert("Failed to save link: " + data.error);
      }
    });
  }

  const geoJsonInput = document.getElementById("geojson-input");
  if (geoJsonInput) {
    geoJsonInput.addEventListener("change", async (event) => {
      const file = event.target.files[0];
      const statusBox = document.getElementById("geojson-status");
      if (!file) return;
      try {
        const text = await file.text();
        const geojson = JSON.parse(text);
        if (geojson.type !== "FeatureCollection" || !geojson.features || geojson.features.length === 0) {
          statusBox.innerText = "Invalid GeoJSON format.";
          return;
        }
        const lineFeature = geojson.features.find((f) => f.geometry && f.geometry.type === "LineString");
        if (!lineFeature) {
          statusBox.innerText = "No LineString feature found in GeoJSON.";
          return;
        }
        showGeoStatus("GeoJSON LineString path loaded successfully!", "success");
      } catch (error) {
        statusBox.innerText = "Failed to load GeoJSON: " + error.message;
        showGeoStatus("Failed to load GeoJSON: " + error.message, "error");
        return;
      }
      statusBox.innerText = "GeoJSON loaded successfully!";
    });
  }

  const toggleShowLinks = document.getElementById("toggle-show-links");
  if (toggleShowLinks) {
    toggleShowLinks.addEventListener("change", (event) => {
      if (event.target.checked) {
        addLinksToMap(mapState.linesLayer, mapState.pointsLayer, mapState.map, mapState.links, mapState.markers, L);
        mapState.linesLayer.addTo(mapState.map);
      } else {
        mapState.map.removeLayer(mapState.linesLayer);
      }
    });
  }

  const toggleOnlyImagesWithLinks = document.getElementById("toggle-only-images-with-links");
  if (toggleOnlyImagesWithLinks) {
    toggleOnlyImagesWithLinks.addEventListener("change", (event) => {
      if (event.target.checked) {
        const keepImagesIDs = new Set();
        mapState.links.forEach((link) => {
          link.endpoints.forEach((endpoint) => {
            if (endpoint.entity_type === "image" && endpoint.image_id) {
              keepImagesIDs.add(endpoint.image_id);
            }
          });
        });
        Object.values(mapState.sharedObjects).forEach((arrayOfLinks) => {
          keepImagesIDs.add(arrayOfLinks.image1);
          keepImagesIDs.add(arrayOfLinks.image2);
        });
        setFilteredImages(mapState.images.filter((img) => keepImagesIDs.has(img.image_id)));
        enableClustering(
          mapState.map,
          mapState.clusters,
          mapState.markers,
          mapState.filteredImages,
          mapState.objectLinesLayer,
          mapState.linesLayer
        );
      } else {
        setFilteredImages(mapState.images.filter(checkAllFilters));
        if (document.getElementById("toggle-shared-objects").checked) {
          const keep = new Set(mapState.filteredImages.map((img) => img.image_id));
          Object.values(mapState.sharedObjects).forEach((shared) => {
            keep.add(shared.image1);
            keep.add(shared.image2);
          });
          setFilteredImages(mapState.images.filter((img) => keep.has(img.image_id)));
        }
      }
      applyFilters();
    });
  }

  const toggleSharedObjects = document.getElementById("toggle-shared-objects");
  if (toggleSharedObjects) {
    toggleSharedObjects.addEventListener("change", (event) => {
      if (event.target.checked) {
        addSharedLinksToMap(
          mapState.sharedObjectsLayer,
          mapState.map,
          mapState.sharedObjects,
          mapState.markers,
          L,
          mapState.objectsData
        );
      } else {
        mapState.map.removeLayer(mapState.sharedObjectsLayer);
      }
    });
  }
}
