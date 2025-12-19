import { handleTyping, updateSearchField, performSearch, selectObject } from "./searchController.js";
import { toggleMetadata , switchMode , navigateObject } from "./ui.js";
import { closeInstancePreview } from "./instancePreview.js";
import { generateThread, showResults, selectTab, loadInitialThreads } from "./threadController.js";

export function initThreadPageGlobals() {
  // Functions called from inline HTML attributes in templates/thread.html
  window.handleTyping = handleTyping;
  window.updateSearchField = updateSearchField;
  window.performSearch = performSearch;
  window.selectObject = selectObject;

  window.selectTab = selectTab;
  window.generateThread = generateThread;
  window.showResults = showResults;

  window.toggleMetadata = toggleMetadata;
  window.closeInstancePreview = closeInstancePreview;

  // Legacy compatibility (if some other template calls it)
  window.loadInitialThreads = loadInitialThreads;

  window.switchMode = switchMode;
  window.navigateObject = navigateObject;
}

