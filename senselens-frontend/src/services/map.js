const API_BASE =
  import.meta.env.VITE_API_BASE ||
  "http://localhost:3000";

async function request(path) {
  console.log(
    "[SenseLens API] requesting:",
    `${API_BASE}${path}`,
  );

  const response = await fetch(
    `${API_BASE}${path}`,
  );

  if (!response.ok) {
    const text = await response.text();

    throw new Error(
      `Backend request failed: ${response.status} ${text}`,
    );
  }

  return response.json();
}

/**
 * 获取多条路线
 */
export async function getRoutes(
  destination,
  origin = null,
) {
  const params = new URLSearchParams();

  params.set("destination", destination);

  if (origin) {
    params.set(
      "originLat",
      origin.lat,
    );

    params.set(
      "originLng",
      origin.lng,
    );
  }

  return request(
    `/routes?${params.toString()}`,
  );
}

/**
 * 获取当前路线详情
 */
export async function getRouteDetail(
  routeId,
) {
  if (!routeId) {
    throw new Error(
      "routeId is required",
    );
  }

  return request(
    `/routes/${encodeURIComponent(
      routeId,
    )}`,
  );
}

/**
 * 获取 quiet spaces
 */
export async function getQuietSpaces(
  routeId,
) {
  if (!routeId) {
    throw new Error(
      "routeId is required",
    );
  }

  return request(
    `/routes/${encodeURIComponent(
      routeId,
    )}/quiet-spaces`,
  );
}

/**
 * 获取当前 sensory alert
 */
export async function getSensoryAlert(
  routeId,
) {
  if (!routeId) {
    throw new Error(
      "routeId is required",
    );
  }

  return request(
    `/routes/${encodeURIComponent(
      routeId,
    )}/alerts`,
  );
}

/**
 * 获取 forecast
 */
export async function getRouteForecast(
  routeId,
) {
  if (!routeId) {
    throw new Error(
      "routeId is required",
    );
  }

  return request(
    `/routes/${encodeURIComponent(
      routeId,
    )}/forecast`,
  );
}