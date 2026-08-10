const EARTH_RADIUS_M = 6_371_000;

export function haversineMetres(a, b) {
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

// Progress and "next instruction" are both estimated from straight-line
// distance to the destination, not from matching your live position back
// onto the route polyline — much simpler, and close enough for a walking
// route where you're broadly heading toward the destination the whole way.
// It'll read a little rough if you detour, but never says something
// confidently wrong, just a slightly off percentage/step.
export function estimateRouteProgress(position, activeRoute) {
  const path = activeRoute?.path ?? [];
  const steps = activeRoute?.steps ?? [];
  const destination = path[path.length - 1];

  if (!position || !destination || path.length < 2) return null;

  const totalRouteMetres = path.reduce(
    (total, point, i) => (i === 0 ? 0 : total + haversineMetres(path[i - 1], point)),
    0
  );
  if (totalRouteMetres === 0) return null;

  const remainingMetres = haversineMetres(position, destination);
  const coveredMetres = Math.max(0, Math.min(totalRouteMetres, totalRouteMetres - remainingMetres));
  const progress = Math.round((coveredMetres / totalRouteMetres) * 100);

  let cumulative = 0;
  let currentStep = null;
  for (const step of steps) {
    const stepStart = cumulative;
    cumulative += step.distanceMeters ?? 0;
    if (coveredMetres < cumulative || step === steps[steps.length - 1]) {
      currentStep = { ...step, remainingInStepM: Math.max(0, Math.round(cumulative - coveredMetres)), stepStart };
      break;
    }
  }

  return { progress, coveredMetres, remainingMetres, currentStep };
}
