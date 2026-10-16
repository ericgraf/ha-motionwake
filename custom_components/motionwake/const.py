"""Constants for the MotionWake integration."""

DOMAIN = "motionwake"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_ENTRY_ID = "entry_id"
# Optional OTA source for the "Update app" button:
#   - http(s):// URL to the release APK, or
#   - filesystem path visible from the HA container (e.g. /config/motionwake-update.apk)
CONF_UPDATE_SOURCE = "update_source"

DEFAULT_PORT = 8587
DEFAULT_TIMEOUT = 20

# How often to poll the tablet's state endpoints.
SCAN_INTERVAL_SECONDS = 15
