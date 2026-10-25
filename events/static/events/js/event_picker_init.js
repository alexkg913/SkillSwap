/*
 * Event-form map picker activation.
 *
 * Mirrors home/static/home/js/campus_map_init.js: reads server-rendered
 * json_script data and starts the shared initializer, in its own file rather
 * than an inline <script> so the page needs no script-src exception under a
 * future Content-Security-Policy.
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

  function start() {
    var element = document.getElementById("campus-map-picker");
    if (!element) {
      return;
    }

    var fallback = document.querySelector(".map-picker__fallback");
    var warning = document.querySelector(".map-picker__warning");
    var config;
    var buildings;

    try {
      config = readJson("map-config");
      buildings = readJson("campus-buildings");
    } catch (error) {
      if (window.console && window.console.error) {
        window.console.error("Campus map picker could not be displayed.", error);
      }
      return;
    }

    element.removeAttribute("hidden");
    if (fallback) {
      fallback.setAttribute("hidden", "hidden");
    }

    try {
      window.SkillSwapCampusMap.initializePicker({
        element: element,
        tileUrl: config.tile_url,
        tileAttribution: config.tile_attribution,
        referrerPolicy: config.tile_referrer_policy,
        center: config.center,
        zoom: config.default_zoom,
        bbox: config.campus_bbox,
        latitudeInput: document.getElementById("id_latitude"),
        longitudeInput: document.getElementById("id_longitude"),
        buildingSelect: document.getElementById("id_campus_location"),
        buildings: buildings,
        onChange: function (insideCampus) {
          if (!warning) {
            return;
          }
          // Advisory only -- the server rejects out-of-bounds pins regardless.
          if (insideCampus) {
            warning.setAttribute("hidden", "hidden");
          } else {
            warning.removeAttribute("hidden");
          }
        },
      });
    } catch (error) {
      if (window.console && window.console.error) {
        window.console.error("Campus map picker could not be displayed.", error);
      }
      element.setAttribute("hidden", "hidden");
      if (fallback) {
        fallback.removeAttribute("hidden");
        // The dropdown and the form still work without the map.
        fallback.textContent =
          "The map is unavailable right now. Pick a building from the list instead.";
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})(window, document);
