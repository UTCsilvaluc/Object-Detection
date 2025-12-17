# Thread page (front-end)

This folder contains the refactored front-end logic for `templates/thread.html`.

## Entry point

- `static/js/thread.js` loads `static/js/thread/index.js`.
- `static/js/thread/index.js` exposes a small set of functions on `window.*` because the template uses inline `onclick` / `onchange` attributes.

## Main modules

- `searchController.js`: search input → `/thread/thread_search_values` → results list → `selectObject()` starts the first thread.
- `threadController.js`: tab switching, `Generate Thread`, and `Show Results` actions.
- `render.js`: renders the four tabs (Objects / Images / Map / Threads).
- `mapView.js`: Leaflet map rendering + link drawing logic for results.
- `instancePreview.js`: click on object instance thumbnails → fullscreen preview overlay.
- `ui.js`: small UI helpers (single-select, metadata toggle, etc.).
- `state.js`: minimal shared state (`threadCounter`, `searchLocked`, `mapStates`).

## Data flow (high level)

1. User searches → list of objects.
2. User selects an object → `/thread/generate` (`mode: "object"`) returns a thread payload.
3. The payload is rendered in a new thread panel (tabs).
4. User can:
   - generate another thread from the current selection (`/thread/generate`), or
   - show map results for a selection (`/thread/show_results`).

