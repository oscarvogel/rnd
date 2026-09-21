APP_ID = "rnd"
BUILD_VERSION = "2026.8.11.1"
MANIFEST_URL = "https://raw.githubusercontent.com/oscarvogel/vogel-releases/main/apps/rnd/latest.json"


def manifest_url_for(app_id=APP_ID):
    if app_id != APP_ID:
        raise ValueError("app_id desconocido: {!r}".format(app_id))
    return MANIFEST_URL
