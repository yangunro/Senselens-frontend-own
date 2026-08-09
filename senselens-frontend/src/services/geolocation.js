const TARGET_ACCURACY_METRES = 50;
const MAXIMUM_ACCURACY_METRES = 200;
const LOCATION_TIMEOUT_MS = 12000;

const positionOptions = {
  enableHighAccuracy: true,
  maximumAge: 0,
  timeout: LOCATION_TIMEOUT_MS,
};

function ensureGeolocationAvailable() {
  if (!window.isSecureContext) {
    throw new Error(
      "Location requires HTTPS or localhost.",
    );
  }

  if (!navigator.geolocation) {
    throw new Error(
      "Location is not supported by this browser.",
    );
  }
}

function normalisePosition(position) {
  return {
    lat: position.coords.latitude,
    lng: position.coords.longitude,
    accuracy: position.coords.accuracy,
    observedAt: new Date(
      position.timestamp,
    ).toISOString(),
  };
}

function locationErrorMessage(error) {
  if (error?.code === 1) {
    return (
      "Location permission was denied. " +
      "Allow location access and try again."
    );
  }

  if (error?.code === 2) {
    return (
      "Your location is currently unavailable. " +
      "Move near a window or enable device location services."
    );
  }

  if (error?.code === 3) {
    return "Location request timed out. Please try again.";
  }

  return "Unable to determine your current location.";
}

export function getAccurateCurrentLocation() {
  return new Promise((resolve, reject) => {
    try {
      ensureGeolocationAvailable();
    } catch (error) {
      reject(error);
      return;
    }

    let bestPosition = null;
    let watchId = null;
    let settled = false;

    function finish(callback, value) {
      if (settled) {
        return;
      }

      settled = true;
      window.clearTimeout(timeoutId);

      if (watchId !== null) {
        navigator.geolocation.clearWatch(
          watchId,
        );
      }

      callback(value);
    }

    const timeoutId = window.setTimeout(
      () => {
        if (
          bestPosition &&
          bestPosition.accuracy <=
            MAXIMUM_ACCURACY_METRES
        ) {
          finish(resolve, bestPosition);
          return;
        }

        finish(
          reject,
          new Error(
            "Location accuracy is too low to calculate a reliable route. Try again outdoors or near a window.",
          ),
        );
      },
      LOCATION_TIMEOUT_MS,
    );

    watchId =
      navigator.geolocation.watchPosition(
        (position) => {
          const current =
            normalisePosition(position);

          if (
            !bestPosition ||
            current.accuracy <
              bestPosition.accuracy
          ) {
            bestPosition = current;
          }

          if (
            current.accuracy <=
            TARGET_ACCURACY_METRES
          ) {
            finish(resolve, current);
          }
        },
        (error) => {
          if (error?.code === 1) {
            finish(
              reject,
              new Error(
                locationErrorMessage(error),
              ),
            );
          }
        },
        positionOptions,
      );
  });
}

export function watchCurrentLocation(
  onPosition,
  onError,
) {
  try {
    ensureGeolocationAvailable();
  } catch (error) {
    onError?.(error);
    return () => {};
  }

  const watchId =
    navigator.geolocation.watchPosition(
      (position) => {
        const current =
          normalisePosition(position);

        if (
          current.accuracy <=
          MAXIMUM_ACCURACY_METRES
        ) {
          onPosition(current);
        }
      },
      (error) => {
        onError?.(
          new Error(
            locationErrorMessage(error),
          ),
        );
      },
      positionOptions,
    );

  return () => {
    navigator.geolocation.clearWatch(
      watchId,
    );
  };
}
