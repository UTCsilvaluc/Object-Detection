function getImageDateMs(img) {
    const rawDate = img?.event_date || img?.capture_date || null;
    if (!rawDate) return null;
    const ms = new Date(rawDate).getTime();
    return Number.isFinite(ms) ? ms : null;
}

function orderFilteredImagesByDate(filteredImages) {
    filteredImages.sort((a, b) => {
        const dateA = getImageDateMs(a);
        const dateB = getImageDateMs(b);
        if (dateA === null && dateB === null) return 0;
        if (dateA === null) return 1;
        if (dateB === null) return -1;
        return dateA - dateB;
    });
}
const $ = window.jQuery;
function buildTimelineFromFilteredImages(filteredImages , URL_for_images) {
    const sidebar = document.getElementById("sidebar-timeline");
    if (!sidebar) return;

    // Réinitialise tout le contenu
    sidebar.innerHTML = `
        <div class="timeline-container" id="timeline-1">
            <div class="timeline-header">
                <h2 class="timeline-header__title">Timeline</h2>
                <h3 class="timeline-header__subtitle">${filteredImages.length} images</h3>
            </div>
            <div class="timeline"></div>
        </div>
    `;
    const orderedImages = [...filteredImages];
    orderFilteredImagesByDate(orderedImages);
    const timelineContainer = sidebar.querySelector(".timeline");

    if (orderedImages.length === 0) {
        timelineContainer.innerHTML = `<p style="color:white; padding:20px;">No images found for this filter.</p>`;
        return;
    }

    const fragment = document.createDocumentFragment();
    orderedImages.forEach(img => {
        const item = document.createElement("div");
        item.className = "timeline-item";
        item.setAttribute("data-text", img.type || "Unknown");
        item.setAttribute("data-longitude", img.longitude);
        item.setAttribute("data-latitude", img.latitude);
        item.setAttribute("data-image-id", img.image_id);

        const yearLabel = (() => {
            const ms = getImageDateMs(img);
            return ms === null ? "N/A" : new Date(ms).getFullYear();
        })();

        item.innerHTML = `
            <div class="timeline__content">
                <img class="timeline__img" src="${URL_for_images + img.file_path}" alt="${img.title}" loading="lazy" decoding="async">
                <h2 class="timeline__content-title">${yearLabel}</h2>
                <p class="timeline__content-desc">${img.description || "No description available."}</p>
            </div>
        `;
        fragment.appendChild(item);
    });
    timelineContainer.appendChild(fragment);

    // Réactive l’effet animation/scroll du plugin timeline
    $("#timeline-1").timeline();
}
window.buildTimelineFromFilteredImages = buildTimelineFromFilteredImages;

(function ($) {
  $.fn.timeline = function () {
    const selectors = {
      id: $(this),
      item: $(this).find(".timeline-item"),
      activeClass: "timeline-item--active",
      img: ".timeline__img"
    };
    const rootEl = selectors.id[0];
    if (!rootEl) return;

    if (rootEl.__timelineObserver) {
      rootEl.__timelineObserver.disconnect();
      rootEl.__timelineObserver = null;
    }

    selectors.item.eq(0).addClass(selectors.activeClass);
    selectors.id.css(
      "background-image",
      "url(" + selectors.item.first().find(selectors.img).attr("src") + ")"
    );
    rootEl.__timelineActiveId = selectors.item.first().attr("data-image-id") || null;
    const sidebar = document.getElementById("sidebar-timeline");
    if (sidebar) {
      const firstItem = selectors.item.get(0);
      if (firstItem) {
        sidebar.dispatchEvent(
          new CustomEvent("timeline:active-change", {
            detail: {
              imageId: firstItem.dataset.imageId || null,
              latitude: firstItem.dataset.latitude || null,
              longitude: firstItem.dataset.longitude || null
            }
          })
        );
      }
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const item = $(entry.target);
          const nextId = entry.target.dataset.imageId || null;
          if (rootEl.__timelineActiveId && rootEl.__timelineActiveId === nextId) return;
          selectors.item.removeClass(selectors.activeClass);
          item.addClass(selectors.activeClass);
          rootEl.__timelineActiveId = nextId;

          selectors.id.css(
            "background-image",
            "url(" + item.find(selectors.img).attr("src") + ")"
          );
          if (sidebar) {
            sidebar.dispatchEvent(
              new CustomEvent("timeline:active-change", {
                detail: {
                  imageId: entry.target.dataset.imageId || null,
                  latitude: entry.target.dataset.latitude || null,
                  longitude: entry.target.dataset.longitude || null
                }
              })
            );
          }
        }
      });
    }, {
      root: document.getElementById("sidebar-timeline"),
      threshold: 0.6 
    });
    selectors.item.each(function () {
      observer.observe(this);
    });
    rootEl.__timelineObserver = observer;
  };
})(jQuery);

$("#timeline-1").timeline();
