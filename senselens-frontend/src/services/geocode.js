const MELBOURNE_CBD = { lat: -37.8136, lng: 144.9631 };

// The backend requires destination coordinates for every route request, but a
// user who types an address and hits Enter without picking a dropdown
// suggestion never gets any — resolve it ourselves rather than sending a
// request the backend will reject.
export async function geocodeAddress(address) {
  try {
    const params = new URLSearchParams({
      q: address,
      access_token: import.meta.env.VITE_MAPBOX_ACCESS_TOKEN,
      proximity: `${MELBOURNE_CBD.lng},${MELBOURNE_CBD.lat}`,
      country: "au",
      limit: "1",
    });
    const res = await fetch(`https://api.mapbox.com/search/geocode/v6/forward?${params}`);
    if (!res.ok) throw new Error(`Geocode failed: ${res.status}`);
    const data = await res.json();
    const coordinates = data.features?.[0]?.geometry?.coordinates;
    if (!coordinates) throw new Error("no results");
    return { lat: coordinates[1], lng: coordinates[0] };
  } catch (err) {
    // Surfaces as one consistent, user-facing message regardless of cause
    // (no results, network error, API error) — the specifics go to the
    // console for debugging instead of showing raw API errors to the user.
    console.warn("Geocoding failed:", err);
    throw new Error(`We couldn't find "${address}". Try picking a suggestion from the search box.`);
  }
}
