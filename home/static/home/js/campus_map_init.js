/*
 * Home-page campus-map activation.
 *
 * Reads the server-provided configuration and event pins from the json_script
 * elements rendered by home/templates/home/index.html, then starts the shared
 * initializer in campus_map.js. This lives in its own file rather than in an
 * inline <script> so the page needs no script-src exception under a future
 * Content-Security-Policy.
 *
 */
(function (window, document) {
  "use strict";

  function readJson(id) {
    var element = document.getElementById(id);
    if (!element) {
      throw new Error("Missing campus map data element #" + id + ".");
    }
    return JSON.parse(element.textContent);
  }

  function report(error) {
    if (window.console && window.console.error) {
      window.console.error("Campus map could not be displayed.", error);
    }
  }

  function start() {
    var element = document.getElementById("campus-map");
    if (!element) {
      return;
    }

    var panel = element.closest(".map") || element.parentNode;
    var fallback = panel && panel.querySelector(".map__fallback");

    var config;
    var events;
    try {
      config = readJson("map-config");
      events = readJson("map-events");
    } catch (error) {
      report(error);
      return;
    }

    // Leaflet measures the container on initialize, so reveal it first.
    element.removeAttribute("hidden");
    if (fallback) {
      fallback.setAttribute("hidden", "hidden");
    }

    try {
      window.SkillSwapCampusMap.initialize({
        element: element,
        tileUrl: config.tile_url,
        tileAttribution: config.tile_attribution,
        referrerPolicy: config.tile_referrer_policy,
        center: config.center,
        zoom: config.default_zoom,
        events: events,
      });
    } catch (error) {
      report(error);
      element.setAttribute("hidden", "hidden");
      if (fallback) {
        fallback.removeAttribute("hidden");
        fallback.textContent = "The campus map is unavailable right now.";
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})(window, document);
