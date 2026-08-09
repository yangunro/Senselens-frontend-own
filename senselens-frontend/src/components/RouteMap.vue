<template>
  <div class="google-map-wrapper">
    <div
      v-if="errorMessage"
      class="map-message"
    >
      {{ errorMessage }}
    </div>

    <div
      ref="mapElement"
      class="google-map"
    ></div>
  </div>
</template>

<script setup>
import {
  onMounted,
  onBeforeUnmount,
  ref,
  watch,
} from "vue";

import { loadGoogleMapsLibrary } from "../services/googleMaps";

const props = defineProps({
  polyline: {
    type: String,
    default: null,
  },

  quietSpaces: {
    type: Array,
    default: () => [],
  },

  pedestrianSensors: {
    type: Array,
    default: () => [],
  },

  currentLocation: {
    type: Object,
    default: null,
  },
});

const mapElement = ref(null);

const errorMessage = ref("");

let map = null;

let routePolyline = null;

let quietSpaceMarkers = [];

let pedestrianMarkers = [];

let currentLocationMarker = null;

let geometryEncoding = null;

let advancedMarkerElement = null;

async function initialiseMap() {
  try {
    const [
      { Map },
      { encoding },
      { AdvancedMarkerElement },
    ] = await Promise.all([
      loadGoogleMapsLibrary("maps"),
      loadGoogleMapsLibrary("geometry"),
      loadGoogleMapsLibrary("marker"),
    ]);

    // Melbourne CBD
    const defaultCenter = {
      lat: -37.8136,
      lng: 144.9631,
    };

    map = new Map(
      mapElement.value,
      {
        center: defaultCenter,

        zoom: 14,

        mapId: "DEMO_MAP_ID",

        mapTypeControl: false,

        streetViewControl: false,
      },
    );

    geometryEncoding = encoding;
    advancedMarkerElement =
      AdvancedMarkerElement;

    drawRoute(encoding);

    drawQuietSpaces(
      AdvancedMarkerElement,
    );

    drawPedestrianSensors(
      AdvancedMarkerElement,
    );

    drawCurrentLocation(
      AdvancedMarkerElement,
    );
  } catch (error) {
    console.error(
      "Google Map error:",
      error,
    );

    errorMessage.value =
      "Unable to load Google Map.";
  }
}

function pedestrianMarkerColour(
  minuteCount,
) {
  if (minuteCount < 10) {
    return "#317c70";
  }

  if (minuteCount < 25) {
    return "#c7852d";
  }

  return "#b94a48";
}

function createPedestrianMarkerContent(
  sensor,
) {
  const marker =
    document.createElement("div");

  marker.textContent = String(
    sensor.minuteCount,
  );

  marker.setAttribute(
    "aria-label",
    `${sensor.name}: ${sensor.minuteCount} pedestrians`,
  );

  Object.assign(marker.style, {
    display: "grid",
    placeItems: "center",
    minWidth: "28px",
    height: "28px",
    padding: "0 6px",
    background:
      pedestrianMarkerColour(
        sensor.minuteCount,
      ),
    border: "2px solid white",
    borderRadius: "999px",
    boxShadow:
      "0 2px 7px rgba(0, 0, 0, 0.28)",
    color: "white",
    fontSize: "11px",
    fontWeight: "800",
  });

  return marker;
}

function drawPedestrianSensors(
  AdvancedMarkerElement,
) {
  pedestrianMarkers.forEach(
    (marker) => {
      marker.map = null;
    },
  );

  pedestrianMarkers = [];

  props.pedestrianSensors
    .filter(
      (sensor) =>
        Number.isFinite(sensor.lat) &&
        Number.isFinite(sensor.lng) &&
        Number.isFinite(
          sensor.minuteCount,
        ),
    )
    .forEach((sensor) => {
      const marker =
        new AdvancedMarkerElement({
          map,
          position: {
            lat: sensor.lat,
            lng: sensor.lng,
          },
          title:
            `${sensor.name}: ` +
            `${sensor.minuteCount} pedestrians`,
          content:
            createPedestrianMarkerContent(
              sensor,
            ),
        });

      pedestrianMarkers.push(
        marker,
      );
    });
}

function createCurrentLocationContent() {
  const marker =
    document.createElement("div");

  Object.assign(marker.style, {
    width: "18px",
    height: "18px",
    background: "#2878d0",
    border: "4px solid white",
    borderRadius: "50%",
    boxShadow:
      "0 2px 9px rgba(40, 120, 208, 0.5)",
  });

  return marker;
}

function drawCurrentLocation(
  AdvancedMarkerElement,
) {
  if (currentLocationMarker) {
    currentLocationMarker.map = null;
    currentLocationMarker = null;
  }

  const location = props.currentLocation;

  if (
    !location ||
    !Number.isFinite(location.lat) ||
    !Number.isFinite(location.lng)
  ) {
    return;
  }

  currentLocationMarker =
    new AdvancedMarkerElement({
      map,
      position: {
        lat: location.lat,
        lng: location.lng,
      },
      title:
        `Your location (±${Math.round(
          location.accuracy,
        )} m)`,
      content:
        createCurrentLocationContent(),
      zIndex: 1000,
    });
}

watch(
  () => props.polyline,
  () => {
    if (geometryEncoding) {
      drawRoute(geometryEncoding);
    }
  },
);

watch(
  () => props.quietSpaces,
  () => {
    if (advancedMarkerElement) {
      drawQuietSpaces(
        advancedMarkerElement,
      );
    }
  },
  { deep: true },
);

watch(
  () => props.pedestrianSensors,
  () => {
    if (advancedMarkerElement) {
      drawPedestrianSensors(
        advancedMarkerElement,
      );
    }
  },
  { deep: true },
);

watch(
  () => props.currentLocation,
  () => {
    if (advancedMarkerElement) {
      drawCurrentLocation(
        advancedMarkerElement,
      );
    }
  },
  { deep: true },
);

function drawRoute(encoding) {
  if (
    !map ||
    !props.polyline
  ) {
    return;
  }

  if (routePolyline) {
    routePolyline.setMap(null);
  }

  const path =
    encoding.decodePath(
      props.polyline,
    );

  routePolyline =
    new google.maps.Polyline({
      path,

      geodesic: true,

      strokeColor: "#317c70",

      strokeOpacity: 0.95,

      strokeWeight: 6,
    });

  routePolyline.setMap(map);

  const bounds =
    new google.maps.LatLngBounds();

  path.forEach((point) => {
    bounds.extend(point);
  });

  map.fitBounds(bounds);
}

function drawQuietSpaces(
  AdvancedMarkerElement,
) {
  quietSpaceMarkers.forEach(
    (marker) => {
      marker.map = null;
    },
  );

  quietSpaceMarkers = [];

  props.quietSpaces
    .filter(
      (space) =>
        Number.isFinite(space.lat) &&
        Number.isFinite(space.lng),
    )
    .forEach((space) => {
      const marker =
        new AdvancedMarkerElement({
          map,

          position: {
            lat: space.lat,
            lng: space.lng,
          },

          title:
            space.name ||
            space.label ||
            "Quiet space",
        });

      quietSpaceMarkers.push(
        marker,
      );
    });
}

onMounted(() => {
  initialiseMap();
});

onBeforeUnmount(() => {
  if (routePolyline) {
    routePolyline.setMap(null);
  }

  quietSpaceMarkers.forEach(
    (marker) => {
      marker.map = null;
    },
  );

  pedestrianMarkers.forEach(
    (marker) => {
      marker.map = null;
    },
  );

  if (currentLocationMarker) {
    currentLocationMarker.map = null;
  }
});
</script>

<style scoped>
.google-map-wrapper {
  width: 100%;
  height: 100%;
}

.google-map {
  width: 100%;
  height: 100%;
  min-height: 340px;
}

.map-message {
  position: absolute;
  z-index: 10;

  margin: 12px;
  padding: 10px 14px;

  background: white;
  border-radius: 8px;

  font-size: 12px;
}
</style>
