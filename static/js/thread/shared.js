// Small pure helpers used across controllers/renderers.

export function mergeThreadValues(threads, key, values) {
  if (!threads[key]) threads[key] = [];
  values.forEach((val) => {
    if (val === null || val === undefined || val === "") return;
    if (!threads[key].includes(val)) threads[key].push(val);
  });
}

export function injectImageContextIntoThread(threadsData) {
  const threads = Object.fromEntries(
    Object.entries(threadsData.threads || {}).map(([k, v]) => [k, Array.isArray(v) ? [...v] : []])
  );

  const images = threadsData.images_from_object || [];
  images.forEach((img) => {
    mergeThreadValues(threads, "place", [img.location_name]);
    mergeThreadValues(threads, "date", [img.event_date]);
  });

  return threads;
}

export function orderObjectsByRelevance(objectsList) {
  if (!objectsList || objectsList.length === 0) return [];
  objectsList.sort((a, b) => {
    const aMetaCount = a.metadata ? Object.keys(a.metadata).length : 0;
    const bMetaCount = b.metadata ? Object.keys(b.metadata).length : 0;
    if (bMetaCount !== aMetaCount) return bMetaCount - aMetaCount;

    const aOcc = a.co_occurrence_images ? a.co_occurrence_images.length : 0;
    const bOcc = b.co_occurrence_images ? b.co_occurrence_images.length : 0;
    return bOcc - aOcc;
  });
  return objectsList;
}

