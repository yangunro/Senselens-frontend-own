// Hands off to the user's own maps app for real turn-by-turn voice
// navigation — building that ourselves is out of scope, and every phone
// already has a better version of it installed. Works cross-platform
// (opens the native Google Maps app on iOS/Android if installed, falls
// back to Google Maps in the browser) without needing an API key.
export function openExternalNavigation(destination) {
  if (!destination?.lat || !destination?.lng) return;

  const url = new URL("https://www.google.com/maps/dir/");
  url.searchParams.set("api", "1");
  url.searchParams.set("destination", `${destination.lat},${destination.lng}`);
  url.searchParams.set("travelmode", "walking");

  window.open(url.toString(), "_blank", "noopener");
}
