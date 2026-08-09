import {
  importLibrary,
  setOptions,
} from "@googlemaps/js-api-loader";


const apiKey =
  import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

let configured = false;


function configureGoogleMaps() {
  if (!apiKey) {
    throw new Error(
      "VITE_GOOGLE_MAPS_API_KEY is missing.",
    );
  }

  if (!configured) {
    setOptions({
      key: apiKey,
      v: "weekly",
    });

    configured = true;
  }
}


export async function loadGoogleMapsLibrary(
  library,
) {
  configureGoogleMaps();
  return importLibrary(library);
}
