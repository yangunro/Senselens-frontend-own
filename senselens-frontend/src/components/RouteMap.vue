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
} from "vue";

import {
  importLibrary,
  setOptions,
} from "@googlemaps/js-api-loader";

const props = defineProps({
  polyline: {
    type: String,
    default: null,
  },

  quietSpaces: {
    type: Array,
    default: () => [],
  },
});

const mapElement = ref(null);

const errorMessage = ref("");

const apiKey =
  import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

let map = null;

let routePolyline = null;

let quietSpaceMarkers = [];

setOptions({
  key: apiKey,
  v: "weekly",
});

async function initialiseMap() {
  try {
    if (!apiKey) {
      errorMessage.value =
        "Google Maps Demo Key is missing.";

      return;
    }

    const [
      { Map },
      { encoding },
      { AdvancedMarkerElement },
    ] = await Promise.all([
      importLibrary("maps"),
      importLibrary("geometry"),
      importLibrary("marker"),
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

    drawRoute(encoding);

    drawQuietSpaces(
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
