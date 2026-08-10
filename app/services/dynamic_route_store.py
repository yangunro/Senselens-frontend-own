from collections import OrderedDict
from threading import Lock


MAX_CACHED_ROUTES = 100

_routes = OrderedDict()
_lock = Lock()


def save_dynamic_routes(routes):
    """Keep recent Mapbox route details available to follow-up API calls."""
    with _lock:
        for route in routes:
            route_id = str(route["id"])
            _routes[route_id] = route
            _routes.move_to_end(route_id)

        while len(_routes) > MAX_CACHED_ROUTES:
            _routes.popitem(last=False)


def get_dynamic_route(route_id):
    with _lock:
        route = _routes.get(str(route_id))

        if route is not None:
            _routes.move_to_end(str(route_id))

        return route
