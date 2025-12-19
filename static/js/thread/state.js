// Centralized state for the thread page (kept minimal and explicit).

export const threadState = {
  threadCounter: 0,
  searchLocked: false,
  mapStates: Object.create(null) // threadDomId -> Leaflet state
};

export function allocateThreadDomId() {
  const id = `thread-${threadState.threadCounter}`;
  threadState.threadCounter += 1;
  return id;
}

export function isSearchLocked() {
  return Boolean(threadState.searchLocked);
}

export function lockSearch() {
  threadState.searchLocked = true;
}

export function getOrCreateMapState(threadDomId) {
  if (!threadState.mapStates[threadDomId]) {
    threadState.mapStates[threadDomId] = {
      map: null,
      layer: null,
      bounds: null,
      markers: new Map(),
      plottedIds: new Set(),
      drawnLinks: new Set(),
      previousIds: new Set(),
      colors: {},
      images: [],
      objectIndexByImage: new Map(),
      context: {}
    };
  }
  return threadState.mapStates[threadDomId];
}
