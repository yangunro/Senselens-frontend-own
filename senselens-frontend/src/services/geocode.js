import { importLibrary } from "@googlemaps/js-api-loader";
import { ensureGoogleMapsConfigured } from "./googleMapsLoader";

let geocoderPromise = null;

function getGeocoder() {
  if (!geocoderPromise) {
    geocoderPromise = (async () => {
      ensureGoogleMapsConfigured();
      const { Geocoder } = await importLibrary("geocoding");
      return new Geocoder();
    })();
  }
  return geocoderPromise;
}

// The backend requires destination coordinates for every route request, but a
// user who types an address and hits Enter without picking a dropdown
// suggestion never gets any — resolve it ourselves rather than sending a
// request the backend will reject.
export async function geocodeAddress(address) {
  const geocoder = await getGeocoder();
  try {
    const { results } = await geocoder.geocode({ address, region: "au" });
    const location = results?.[0]?.geometry?.location;
    if (!location) throw new Error("no results");
    return { lat: location.lat(), lng: location.lng() };
  } catch (err) {
    // Surfaces as one consistent, user-facing message regardless of cause
    // (no results, quota, API error) — the specifics go to the console for
    // debugging instead of showing raw API error codes to the user.
    console.warn("Geocoding failed:", err);
    throw new Error(`We couldn't find "${address}". Try picking a suggestion from the search box.`);
  }
}
