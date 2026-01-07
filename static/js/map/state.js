const appConfig = window.appConfig || {};

export const mapConfig = {
  URL_for_images: appConfig.URL_for_images,
  URL_for_view_image: appConfig.URL_for_view_image,
  URL_for_icons: appConfig.icons_path,
  crossIcon: appConfig.crossIcon,
  trashIcon: appConfig.trashIcon
};

export const mapState = {
  map: null,
  pointsLayer: L.layerGroup(),
  markers: L.layerGroup(),
  clusters: L.layerGroup(),
  linesLayer: L.layerGroup(),
  objectLinesLayer: L.layerGroup(),
  sharedObjectsLayer: L.layerGroup(),
  images: [],
  filteredImages: [],
  classes: appConfig.classes || [],
  checkClasses: [...(appConfig.classes || [])],
  links: appConfig.links || [],
  linkTypes: appConfig.link_types || [],
  objectsData: {},
  sharedObjects: [],
  icons: [],
  points: [],
  metadataKeys: appConfig.metadata_keys || [],
  metadataKeysAvailable: (appConfig.metadata_keys || []).slice(),
  tempMarker: null,
  mapInvalidateTimer: null,
  lastTimelineImageId: null
};

export function initMapStateGlobals() {
  window.filteredImages = mapState.filteredImages;
  window.checkClasses = mapState.checkClasses;
  window.enableLinkCreation = false;
  window.ClusterExpandActive = false;
  if (typeof L !== "undefined" && !window.circle) {
    window.circle = L.layerGroup();
  }
}

export function setFilteredImages(next) {
  mapState.filteredImages = next;
  window.filteredImages = next;
}

export function setCheckClasses(next) {
  mapState.checkClasses = next;
  window.checkClasses = next;
}

export function setTempMarker(marker) {
  mapState.tempMarker = marker;
}

export function setLastTimelineImageId(imageId) {
  mapState.lastTimelineImageId = imageId;
}
