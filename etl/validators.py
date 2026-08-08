def valid_melbourne_coordinates(lat, lng):
    if lat is None or lng is None:
        return False

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return False

    return (
        -38.5 <= lat <= -37.0
        and 144.0 <= lng <= 146.0
    )


def valid_non_negative_count(value):
    if value is None:
        return False

    try:
        return int(value) >= 0
    except (TypeError, ValueError):
        return False


def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def normalize_status(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    mapping = {
        "PROPOSED": "Proposed",
        "APPROVED": "Approved",
        "PERMIT ISSUED": "Permit Issued",
        "UNDER CONSTRUCTION": "Under Construction",
        "COMPLETED": "Completed",
    }

    return mapping.get(value)