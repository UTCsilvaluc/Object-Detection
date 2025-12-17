let root = null;
let img = null;
let titleEl = null;
let subtitleEl = null;

function init() {
  if (root) return true;
  root = document.getElementById("instance-preview");
  if (!root) return false;

  img = root.querySelector(".instance-preview__img");
  titleEl = root.querySelector(".instance-preview__title");
  subtitleEl = root.querySelector(".instance-preview__subtitle");

  root.addEventListener("click", (e) => {
    if (e.target === root) closeInstancePreview();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeInstancePreview();
  });

  return true;
}

export function openInstancePreview({ src, title, subtitle }) {
  if (!init()) return;
  if (!root || !img || !titleEl || !subtitleEl) return;

  img.src = src;
  img.alt = title || subtitle || "Object instance";
  titleEl.textContent = title || "Instance preview";
  subtitleEl.textContent = subtitle || "";

  root.classList.remove("hidden");
  document.body.classList.add("preview-open");
}

export function closeInstancePreview() {
  if (!root || !img) return;
  root.classList.add("hidden");
  img.src = "";
  document.body.classList.remove("preview-open");
}

export function wireInstancePreviews(scope) {
  const domRoot = scope || document;
  if (!domRoot) return;

  domRoot.querySelectorAll(".obj-instance").forEach((imgEl) => {
    if (imgEl.dataset.previewBound === "1") return;

    const src = imgEl.getAttribute("src");
    const block = imgEl.closest(".object-block");
    const objectId = block?.dataset.objectId || "";
    const relation = block?.dataset.relation || "";
    const imageLabel = imgEl.getAttribute("title") || "";

    const subtitleParts = [];
    if (imageLabel) subtitleParts.push(`Image ${imageLabel}`);
    if (relation) subtitleParts.push(`Relation: ${relation}`);

    imgEl.dataset.previewBound = "1";
    imgEl.addEventListener("click", () => {
      openInstancePreview({
        src,
        title: objectId ? `Object #${objectId}` : "Object instance",
        subtitle: subtitleParts.join(" · ")
      });
    });
  });
}

