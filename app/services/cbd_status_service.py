from app.services.pedestrian_service import get_current_cbd_status


def get_cbd_status():
    status = get_current_cbd_status()

    if status is None:
        return {
            "level": "unknown",
            "label": "CBD activity unavailable",
            "note": "No recent pedestrian data is available."
        }

    return status
