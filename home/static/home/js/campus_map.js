/*
 * Reusable Leaflet initializer for the campus map.
 *
 * This module holds no campus, tile-provider, or event defaults on purpose:
 * every value is supplied by the caller from server-rendered configuration, so
 * the tile provider can change without editing static JavaScript. The home page
 * calls initialize() through campus_map_init.js; the event form calls
 * initializePicker() through event_picker_init.js.
 *
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

  // Every field goes in as textContent, never innerHTML: an event title is
  // user-supplied and must stay inert text inside the popup.
  function line(text, className) {
    var element = document.createElement("div");
    element.className = className;
    element.textContent = text;
    return element;
  }

  function popupContent(event) {
    var content = document.createElement("div");

    var title = document.createElement("strong");
    title.className = "campus-map-popup__title";
    title.textContent = event.title;
    content.appendChild(title);

    if (event.starts_at_display) {
      content.appendChild(line(event.starts_at_display, "campus-map-popup__meta"));
    }
    if (event.subject) {
      content.appendChild(line(event.subject, "campus-map-popup__meta"));
    }

    var place = [event.building, event.location_note].filter(Boolean).join(" · ");
    if (place) {
      content.appendChild(line(place, "campus-map-popup__meta"));
    }

    if (event.tutor) {
      content.appendChild(line("Tutor: " + event.tutor, "campus-map-popup__meta"));
    }

    return content;
  }

  function baseMap(config) {
    if (!window.L) {
      throw new Error("Leaflet must be loaded before the campus map module.");
    }

    config = required(config, "a configuration object");
    var element = required(config.element, "element");
    var center = coordinatePair(required(config.center, "center"), "center");
    var tileUrl = required(config.tileUrl, "tileUrl");
    var tileAttribution = required(config.tileAttribution, "tileAttribution");
    var zoom = required(config.zoom, "zoom");

    var map = window.L.map(element).setView(center, zoom);

    var tileOptions = { attribution: tileAttribution };
    if (config.referrerPolicy) {
      tileOptions.referrerPolicy = config.referrerPolicy;
    }
    window.L.tileLayer(tileUrl, tileOptions).addTo(map);

    return map;
  }

  /* Read-only mode: render event pins on the home page. */
  function initialize(config) {
    var events = required(config && config.events, "events");
    if (!Array.isArray(events)) {
      throw new Error("events must be an array.");
    }

    var map = baseMap(config);

    events.forEach(function (event) {
      var coordinates = coordinatePair([event.latitude, event.longitude], "event coordinates");
      window.L.marker(coordinates)
        .addTo(map)
        .bindPopup(popupContent(event));
    });

    return map;
  }

  /*
   * Picker mode: one draggable marker whose position is mirrored into hidden
   * latitude / longitude inputs. The server re-validates those values against
   * the campus bounding box -- clamping here is a convenience, not a control.
   */
  function initializePicker(config) {
    var latitudeInput = required(config && config.latitudeInput, "latitudeInput");
    var longitudeInput = required(config && config.longitudeInput, "longitudeInput");
    var bounds = config.bbox;

    var map = baseMap(config);

    // Start from the event's saved pin when editing, otherwise the centre.
    var start = [
      parseFloat(latitudeInput.value),
      parseFloat(longitudeInput.value),
    ];
    if (!Number.isFinite(start[0]) || !Number.isFinite(start[1])) {
      start = config.center;
    }

    var marker = window.L.marker(start, { draggable: true }).addTo(map);

    function withinCampus(latitude, longitude) {
      if (!Array.isArray(bounds) || bounds.length !== 4) {
        return true;
      }
      return latitude >= bounds[0] && latitude <= bounds[2] &&
        longitude >= bounds[1] && longitude <= bounds[3];
    }

    function publish(latitude, longitude) {
      // 6 decimal places matches the DecimalField the values are stored in.
      latitudeInput.value = latitude.toFixed(6);
      longitudeInput.value = longitude.toFixed(6);
      if (config.onChange) {
        config.onChange(withinCampus(latitude, longitude));
      }
    }

    function moveTo(latitude, longitude) {
      marker.setLatLng([latitude, longitude]);
      publish(latitude, longitude);
    }

    marker.on("dragend", function () {
      var position = marker.getLatLng();
      publish(position.lat, position.lng);
    });

    map.on("click", function (clickEvent) {
      moveTo(clickEvent.latlng.lat, clickEvent.latlng.lng);
    });

    // Choosing a building jumps the pin to it; dragging afterwards still works,
    // which is how "Roux Library, but the 2nd floor" gets expressed.
    if (config.buildingSelect && config.buildings) {
      config.buildingSelect.addEventListener("change", function () {
        var building = config.buildings[config.buildingSelect.value];
        if (building) {
          moveTo(building.latitude, building.longitude);
          map.setView([building.latitude, building.longitude], map.getZoom());
        }
      });
    }

    publish(start[0], start[1]);

    return map;
  }

  window.SkillSwapCampusMap = {
    initialize: initialize,
    initializePicker: initializePicker,
  };
})(window);
