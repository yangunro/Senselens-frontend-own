from sqlalchemy import text

from app.database import engine


DEMO_USER_EMAIL = "abdullah@example.com"


def get_preferences():
    query = text("""
        SELECT
            up."NoiseSensitivity",
            up."CrowdThreshold",
            up."LightSensitivity",
            up."AvoidConstruction",
            up."ShowRefuges",
            up."HighContrastMode",
            up."ReducedMotion"
        FROM "UserPreference" up
        JOIN "User" u
            ON u."UserID" = up."UserID"
        WHERE u."Email" = :email
        LIMIT 1;
    """)

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {"email": DEMO_USER_EMAIL}
        ).mappings().first()

    if row is None:
        return {
            "sliders": [
                {
                    "key": "crowd",
                    "label": "Crowd sensitivity",
                    "value": 1
                },
                {
                    "key": "noise",
                    "label": "Noise sensitivity",
                    "value": 1
                },
                {
                    "key": "light",
                    "label": "Light sensitivity",
                    "value": 1
                }
            ],
            "toggles": [
                {
                    "key": "construction",
                    "label": "Avoid construction zones",
                    "note": "Prefer routes away from active development sites.",
                    "value": False
                },
                {
                    "key": "refuges",
                    "label": "Show refuge spaces",
                    "note": "Display quiet spaces along routes.",
                    "value": True
                },
                {
                    "key": "contrast",
                    "label": "High contrast mode",
                    "note": "Use higher contrast in the interface.",
                    "value": False
                }
            ]
        }

    sensitivity_map = {
        "Low": 0,
        "Medium": 1,
        "High": 2,
    }

    return {
        "sliders": [
            {
                "key": "crowd",
                "label": "Crowd sensitivity",
                "value": row["CrowdThreshold"] if row["CrowdThreshold"] is not None else 1
            },
            {
                "key": "noise",
                "label": "Noise sensitivity",
                "value": sensitivity_map.get(
                    row["NoiseSensitivity"],
                    1
                )
            },
            {
                "key": "light",
                "label": "Light sensitivity",
                "value": sensitivity_map.get(
                    row["LightSensitivity"],
                    1
                )
            }
        ],
        "toggles": [
            {
                "key": "construction",
                "label": "Avoid construction zones",
                "note": "Prefer routes away from active development sites.",
                "value": row["AvoidConstruction"]
            },
            {
                "key": "refuges",
                "label": "Show refuge spaces",
                "note": "Display quiet spaces along routes.",
                "value": row["ShowRefuges"]
            },
            {
                "key": "contrast",
                "label": "High contrast mode",
                "note": "Use higher contrast in the interface.",
                "value": row["HighContrastMode"]
            }
        ]
    }


def save_preferences(payload):
    slider_values = {
        item.key: item.value
        for item in payload.sliders
    }

    toggle_values = {
        item.key: item.value
        for item in payload.toggles
    }

    enum_map = {
        0: "Low",
        1: "Medium",
        2: "High",
    }

    crowd_value = slider_values.get("crowd", 1)

    noise_value = enum_map.get(
        slider_values.get("noise", 1),
        "Medium"
    )

    light_value = enum_map.get(
        slider_values.get("light", 1),
        "Medium"
    )

    query = text("""
        INSERT INTO "UserPreference"
        (
            "UserID",
            "NoiseSensitivity",
            "CrowdThreshold",
            "LightSensitivity",
            "AvoidConstruction",
            "ShowRefuges",
            "HighContrastMode",
            "ReducedMotion"
        )

        SELECT
            "UserID",
            :noise,
            :crowd,
            :light,
            :construction,
            :refuges,
            :contrast,
            FALSE
        FROM "User"
        WHERE "Email" = :email

        ON CONFLICT ("UserID")

        DO UPDATE SET
            "NoiseSensitivity" = EXCLUDED."NoiseSensitivity",
            "CrowdThreshold" = EXCLUDED."CrowdThreshold",
            "LightSensitivity" = EXCLUDED."LightSensitivity",
            "AvoidConstruction" = EXCLUDED."AvoidConstruction",
            "ShowRefuges" = EXCLUDED."ShowRefuges",
            "HighContrastMode" = EXCLUDED."HighContrastMode",
            "ReducedMotion" = EXCLUDED."ReducedMotion";
    """)

    with engine.begin() as conn:
        result = conn.execute(
            query,
            {
                "email": DEMO_USER_EMAIL,
                "noise": noise_value,
                "crowd": crowd_value,
                "light": light_value,
                "construction": toggle_values.get(
                    "construction",
                    False,
                ),
                "refuges": toggle_values.get(
                    "refuges",
                    True,
                ),
                "contrast": toggle_values.get(
                    "contrast",
                    False,
                ),
            },
        )

    if result.rowcount == 0:
        return {
            "success": False,
            "message": "Development user was not found.",
        }

    return {
        "success": True,
        "message": "Preferences saved successfully.",
        "preferences": get_preferences(),
    }