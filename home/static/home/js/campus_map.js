/*
 * Campus-map integration staging module.
 *
 * This file is intentionally not loaded by any template yet. It makes no network
 * requests and contains no campus or tile-provider defaults. When the map feature
 * is approved, call window.SkillSwapCampusMap.initialize(...) from the home-page
 * integration described in docs/osm-leaflet-integration-notes.md.
 */
(function (window) {
  "use strict";

  function required(value, name) {
    if (value === undefined || value === null || value === "") {
      throw new Error("Campus map configuration requires " + name + ".");
    }
    return value;
  }

  function coordinatePair(value, name) {
    if (!Array.isArray(value) || value.length !== 2 ||
        !Number.isFinite(value[0]) || !Number.isFinite(value[1])) {
      throw new Error(name + " must be a [latitude, longitude] pair.");
    }
    return value;
  }

  function popupContent(event) {
    var content = document.createElement("div");
    var title = document.createElement("strong");
    title.textContent = event.title;
    content.appendChild(title);

    if (event.location_note) {
      var note = document.createElement("div");
      note.textContent = event.location_note;
      content.appendChild(note);
    }

    return content;
  }

  function initialize(config) {
    if (!window.L) {
      throw new Error("Leaflet must be loaded before the campus map module.");
    }

    config = required(config, "a configuration object");
    var element = required(config.element, "element");
    var center = coordinatePair(required(config.center, "center"), "center");
    var tileUrl = required(config.tileUrl, "tileUrl");
    var tileAttribution = required(config.tileAttribution, "tileAttribution");
    var zoom = required(config.zoom, "zoom");
    var events = required(config.events, "events");
    if (!Array.isArray(events)) {
      throw new Error("events must be an array.");
    }

    var map = window.L.map(element).setView(center, zoom);
    window.L.tileLayer(tileUrl, {
      attribution: tileAttribution,
    }).addTo(map);

    events.forEach(function (event) {
      var coordinates = coordinatePair([event.latitude, event.longitude], "event coordinates");
      window.L.marker(coordinates)
        .addTo(map)
        .bindPopup(popupContent(event));
    });

    return map;
  }

  window.SkillSwapCampusMap = { initialize: initialize };
})(window);
