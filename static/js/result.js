import { $ , $$ , toggleAccordion , refreshImage , refreshCount , resetMetaForm , addOrUpdateObjectSection , writeClassMetaField , writeAccordionHeader , removeSelectOptionFromAll , createOptionElement , showSimilar , defaultObjectSelection, setTrashIcon } from './utils.js';
import { apiPost } from './api.js';
import { returnRegexByName , returnInputTypeByName , writeMetaDataField , addMetadataField , handleNewType , createNewMetadata , handleNewMetadataType , createNewMetadataKey , importMetadata , removeMetadataField , changeKey , changeValue , changeType } from './metadata.js';
import { removeObject , mergeObjects , addPointToAnalyse , runAnalysis } from './objects.js';

const AppState = {
    analyzing: false,
    submitting: false,
    metadataUsed: [[]],
    metadataKeys : window.AppConfig.metadata_keys,
    classNames : window.AppConfig.class_names
};
import { setCrossIcon } from './metadata.js';
setCrossIcon(window.AppConfig.crossIcon);
setTrashIcon(window.AppConfig.trashIcon);
window.AppState = AppState;

$('#data_form').addEventListener('submit', function(event) {
    if (AppState.submitting) {
        event.preventDefault();
        return;
    }
    AppState.submitting = true;
});
window.addEventListener("beforeunload", function () {
    if (AppState.submitting) return;
    fetch("/clear_temp", { method: "POST", headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ img_name: window.AppConfig.name, img_annotated_path: window.AppConfig.annotated_image_path, img_original_path: window.AppConfig.original_image_path }) });
});

