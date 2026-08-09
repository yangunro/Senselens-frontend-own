<template>
  <div class="address-autocomplete">
    <div
      v-show="ready && !initialisationError"
      ref="autocompleteHost"
      class="places-host"
    ></div>

    <input
      v-if="initialisationError"
      :value="modelValue"
      type="text"
      autocomplete="off"
      placeholder="Enter your destination"
      aria-label="Destination address"
      @input="handleFallbackInput"
      @keyup.enter="emit('submit')"
    />

    <input
      v-else-if="!ready"
      type="text"
      disabled
      placeholder="Loading address search…"
      aria-label="Loading address search"
    />
  </div>
</template>

<script setup>
import {
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import { loadGoogleMapsLibrary } from "../services/googleMaps";


const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
});

const emit = defineEmits([
  "update:modelValue",
  "place-selected",
  "submit",
  "error",
]);

const autocompleteHost = ref(null);
const ready = ref(false);
const initialisationError = ref(null);

let autocompleteElement = null;


function coordinateValue(location, key) {
  const value = location?.[key];

  return typeof value === "function"
    ? value.call(location)
    : value;
}


function handleInput(event) {
  const value =
    event.target?.value ??
    autocompleteElement?.value ??
    "";

  emit("update:modelValue", value);
}


async function handlePlaceSelect(event) {
  try {
    const prediction =
      event.placePrediction;

    if (!prediction) {
      return;
    }

    const place = prediction.toPlace();

    await place.fetchFields({
      fields: [
        "displayName",
        "formattedAddress",
        "location",
      ],
    });

    const address =
      place.formattedAddress ||
      place.displayName ||
      autocompleteElement?.value ||
      "";
    const selectedPlace = {
      address,
      displayName:
        place.displayName || address,
      lat: coordinateValue(
        place.location,
        "lat",
      ),
      lng: coordinateValue(
        place.location,
        "lng",
      ),
    };

    emit("update:modelValue", address);
    emit("place-selected", selectedPlace);
  } catch (error) {
    emit("error", error);
  }
}


function handleFallbackInput(event) {
  emit(
    "update:modelValue",
    event.target.value,
  );
}


async function initialiseAutocomplete() {
  try {
    const { PlaceAutocompleteElement } =
      await loadGoogleMapsLibrary(
        "places",
      );

    autocompleteElement =
      new PlaceAutocompleteElement();

    autocompleteElement.includedRegionCodes = [
      "au",
    ];
    autocompleteElement.locationBias = {
      center: {
        lat: -37.8136,
        lng: 144.9631,
      },
      radius: 50000,
    };
    autocompleteElement.placeholder =
      "Enter your destination";
    autocompleteElement.value =
      props.modelValue;
    autocompleteElement.setAttribute(
      "aria-label",
      "Destination address",
    );

    autocompleteElement.addEventListener(
      "input",
      handleInput,
    );
    autocompleteElement.addEventListener(
      "gmp-select",
      handlePlaceSelect,
    );

    autocompleteHost.value.appendChild(
      autocompleteElement,
    );
    ready.value = true;
  } catch (error) {
    initialisationError.value = error;
    emit("error", error);
  }
}


watch(
  () => props.modelValue,
  (value) => {
    if (
      autocompleteElement &&
      autocompleteElement.value !== value
    ) {
      autocompleteElement.value = value;
    }
  },
);


onMounted(initialiseAutocomplete);

onBeforeUnmount(() => {
  if (!autocompleteElement) {
    return;
  }

  autocompleteElement.removeEventListener(
    "input",
    handleInput,
  );
  autocompleteElement.removeEventListener(
    "gmp-select",
    handlePlaceSelect,
  );
  autocompleteElement.remove();
});
</script>

<style scoped>
.address-autocomplete,
.places-host,
input {
  width: 100%;
}

.places-host {
  display: flex;
  align-items: center;
}

input {
  height: 56px;

  padding: 0;

  background: transparent;
  border: none;
  outline: none;

  color: var(--color-text);
  font: inherit;
  font-size: 14.5px;
}

input::placeholder {
  color: var(--color-text-faint);
}

:deep(gmp-place-autocomplete) {
  width: 100%;
  min-height: 54px;

  background: transparent;
  border: none;
  border-radius: 0;

  color: var(--color-text);
  font-family: inherit;
}

@media (min-width: 768px) {
  input,
  :deep(gmp-place-autocomplete) {
    min-height: 58px;
    font-size: 16px;
  }
}
</style>
