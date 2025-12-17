export function toggleMetadata(btn, event) {
  event.stopPropagation();
  const block = btn.nextElementSibling;
  if (!block) return;

  if (block.style.display === "none") {
    block.style.display = "block";
    btn.textContent = "Hide metadata";
  } else {
    block.style.display = "none";
    btn.textContent = "Show metadata";
  }
}

export function closeTab(threadDomId, tabClass) {
  const container = document.getElementById(threadDomId);
  if (!container) return;
  container.querySelectorAll(tabClass).forEach((block) => block.classList.remove("selected"));
}

export function enableSingleSelect(threadDomId, selector) {
  const container = document.getElementById(threadDomId);
  if (!container) return;

  container.querySelectorAll(selector).forEach((block) => {
    block.addEventListener("click", (e) => {
      container.querySelectorAll(selector).forEach((b) => b.classList.remove("selected"));
      e.currentTarget.classList.add("selected");
    });
  });
}

export function clearThreadExcept(threadDomId, section, singleItemHTML) {
  const container = document.getElementById(threadDomId);
  if (!container) return;

  const sections = container.querySelectorAll(".thread-content");
  sections.forEach((sec) => sec.classList.add("hidden"));

  const tabs = container.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    const isSelected = tab.dataset.tab === section;
    const isMap = tab.dataset.tab === "map";

    if (isSelected) {
      tab.classList.add("selected");
      tab.style.pointerEvents = "auto";
      tab.style.opacity = "1";
    } else if (isMap) {
      tab.classList.remove("selected");
      tab.style.pointerEvents = "auto";
      tab.style.opacity = "1";
    } else {
      tab.classList.remove("selected");
      tab.style.pointerEvents = "none";
      tab.style.opacity = "0.4";
    }
  });

  const targetContainer = container.querySelector(`.thread-content[data-section="${section}"]`);
  if (!targetContainer) return;
  targetContainer.classList.remove("hidden");
  targetContainer.innerHTML = singleItemHTML;

  const generateBtn = container.querySelector(".thread-generate-btn");
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.classList.add("disabled-btn");
  }
}

