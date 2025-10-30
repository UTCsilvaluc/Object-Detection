function orderFilteredImagesByDate(filteredImages) {
    filteredImages.sort((a, b) => {
        const dateA = new Date(a.capture_date);
        const dateB = new Date(b.capture_date);
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
    orderFilteredImagesByDate(filteredImages);
    const timelineContainer = sidebar.querySelector(".timeline");

    if (filteredImages.length === 0) {
        timelineContainer.innerHTML = `<p style="color:white; padding:20px;">No images found for this filter.</p>`;
        return;
    }

    filteredImages.forEach(img => {
        const item = document.createElement("div");
        item.className = "timeline-item";
        item.setAttribute("data-text", img.type || "Unknown");
        item.setAttribute("data-longitude", img.longitude);
        item.setAttribute("data-latitude", img.latitude);

        item.innerHTML = `
            <div class="timeline__content">
                <img class="timeline__img" src="${URL_for_images + img.file_path}" alt="${img.title}">
                <h2 class="timeline__content-title">${img.capture_date ? new Date(img.capture_date).getFullYear() : "N/A"}</h2>
                <p class="timeline__content-desc">${img.description || "No description available."}</p>
            </div>
        `;
        timelineContainer.appendChild(item);
    });

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

    selectors.item.eq(0).addClass(selectors.activeClass);
    selectors.id.css(
      "background-image",
      "url(" + selectors.item.first().find(selectors.img).attr("src") + ")"
    );

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const item = $(entry.target);
          selectors.item.removeClass(selectors.activeClass);
          item.addClass(selectors.activeClass);

          selectors.id.css(
            "background-image",
            "url(" + item.find(selectors.img).attr("src") + ")"
          );
        }
      });
    }, {
      root: document.getElementById("sidebar-timeline"),
      threshold: 0.6 
    });
    selectors.item.each(function () {
      observer.observe(this);
    });
  };
})(jQuery);

$("#timeline-1").timeline();
