async function removeObject(objID) {
    if (!confirm('Are you sure you want to delete this object?')) return;
    const data = await apiPost('/objects/remove_object', { id: objID , img_name: window.AppConfig.name , img_original_path: window.AppConfig.original_image_path, img_annotated_path: window.AppConfig.annotated_image_path });
    if (!data) return;
    if (data.success) {
        const objElement = $(`#obj${objID}`);
        if (objElement) objElement.remove();
        refreshImage();
        refreshCount(data.num_objects);
    } else {
        alert('Failed to delete the object.');
    }
}
window.removeObject = removeObject;
async function mergeObjects(button) {
    const selectedObjects = Array.from($$('input[type="checkbox"][name^="merge_"]:checked'))
        .map(cb => cb.name.split('_')[1]);

    if (selectedObjects.length < 2) {
        alert("Please select at least two objects to merge.");
        return;
    }
    if (!confirm(`Are you sure you want to merge the selected objects: ${selectedObjects.join(', ')}?`)) return;
    const data = await apiPost('/objects/merge_objects', {
        obj_ids: selectedObjects,
        img_name: window.AppConfig.name,
        img_original_path: window.AppConfig.original_image_path,
        img_annotated_path: window.AppConfig.annotated_image_path
    });
    if (data.success) {
        selectedObjects.forEach(id => document.getElementById(`obj${id}`)?.remove());
        addOrUpdateObjectSection(data);
    } else {
        alert('Failed to merge objects: ' + data.error);
    }
}
window.mergeObjects = mergeObjects;
async function addPointToAnalyse(img) {
    if (AppState.analyzing) {
        alert("Analysis is already in progress. Please wait.");
        return;
    }
    AppState.analyzing = true;
    const rect = img.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const xReal = Math.round(x * (img.naturalWidth / img.width));
    const yReal = Math.round(y * (img.naturalHeight / img.height));
    alert(`Point added for analysis at coordinates: (${xReal}, ${yReal})`);
    const data = await apiPost('/analysis/analyse_point', {
        img_name: window.AppConfig.name,
        x: xReal,
        y: yReal,
        img_original_path: window.AppConfig.original_image_path,
        img_annotated_path: window.AppConfig.annotated_image_path
    });
    if (data.success) {
        alert("Object detected and added successfully.");
        addOrUpdateObjectSection(data);
    } else {
        alert('Failed to add point: ' + data.error);
    }
    AppState.analyzing = false;
}
window.addPointToAnalyse = addPointToAnalyse;
async function runAnalysis(button) {
    AppState.analyzing = true;
    button.disabled = true;
    button.innerText = "Running analysis...";
    const points_per_side = document.getElementById("points_per_side").value;
    const pred_iou_thresh = document.getElementById("pred_iou_thresh").value;
    const stability_score_thresh = document.getElementById("stability_score_thresh").value;
    const min_mask_region_area = document.getElementById("min_mask_region_area").value;
    const data = await apiPost('/analysis/re_run_analysis', {
        img_name: window.AppConfig.name,
        points_per_side: points_per_side,
        pred_iou_thresh: pred_iou_thresh,
        stability_score_thresh: stability_score_thresh,
        min_mask_region_area: min_mask_region_area,
        img_original_path: window.AppConfig.original_image_path,
        img_annotated_path: window.AppConfig.annotated_image_path
    });
    if (!data) {
        button.disabled = false;
        button.innerText = "Run new analysis";
        AppState.analyzing = false;
        return;
    }
    if (data.success) {
        document.open();
        document.write(data.html);
        document.close();
    } else {
        alert("Failed to re-analyze the image: " + data.error);
        button.disabled = false;
        button.innerText = "Run new analysis";
    }
    AppState.analyzing = false;
}
window.runAnalysis = runAnalysis;
export { removeObject, mergeObjects, addPointToAnalyse , runAnalysis };