# MotionWake for Home Assistant

Control a **MotionWake** Fire tablet from Home Assistant over the tablet's local
HTTP API.

MotionWake is a sideloaded app (see the
[`firetablet-app`](https://github.com/ericgraf/firetablet-screen) project) that
sleeps the tablet's screen after a period with no camera-detected motion and
wakes it when motion is seen again — turning a spare Fire tablet into a low-power
wall display. This custom integration exposes that app's control surface as
native HA entities.

## What you get

- **Switch — Motion monitoring**: start/stop the idle-sleep + motion-wake
  monitor.
- **Buttons**:
  - **Wake display** — light the screen now.
  - **Sleep display** — put the screen to sleep now.
  - **Reload dashboard** — re-open the stored dashboard URL (e.g. a Lovelace
    wall view) in the tablet's kiosk browser.
- **Sensors**:
  - **Screen state** — `awake` / `dreaming` / `asleep`.
  - **Last motion (s)** — seconds since the camera last detected motion.

The integration polls the tablet's `GET /status` endpoint (default every 15 s)
for state and calls the relevant endpoint for actions.

## Requirements

- HA 2024.1 or newer.
- The **MotionWake app** installed and running on your Fire tablet, with its
  service started and the API token known (shown in the app UI).
- The tablet and HA on the same LAN (plain HTTP, default port **8587**).

## Install

1. In HA: **Settings → Devices & services → Add integration → HACS →
   `ericgraf/ha-motionwake`** (or add this repository in HACS), then add the
   integration.
2. When prompted, enter:
   - **Host** — the tablet's LAN IP (or a hostname).
   - **Port** — `8587` (default).
   - **API token** — the token from the MotionWake app UI.

The integration validates the connection with a live `GET /status` before it
saves.

## Using it

- Turn **Motion monitoring** on to let the tablet idle-sleep and motion-wake.
- Use **Wake display** / **Sleep display** to control the screen immediately.
- Point the tablet at your wall dashboard once (in the app, or via
  `POST /browser {"url": "..."}`), then use **Reload dashboard** to refresh it
  on demand.

## Notes

- State is read from `GET /status`; actions POST to `/start`, `/stop`, `/wake`,
  `/sleep`, and `/browser/reload`. See the app README's **HTTP API** section for
  the full endpoint list and `curl` examples.
- Screen state can be `dreaming` (Fire's on-screen clock/screensaver) before it
  reaches a full `asleep`; the app treats both as "screen off".

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `cannot_connect` | Wrong IP/port, or the MotionWake service isn't running. Start it in the app or via `POST /start`. |
| `invalid_auth` | Token mistyped — copy it again from the app UI. |
| Entities exist but show `unavailable` | The tablet went offline; the config entry will re-sync on the next successful poll. |

## Repository layout

```
manifest.json                       HACS manifest
custom_components/motionwake/
  __init__.py                       entry setup/unload, session + client wiring
  config_flow.py                    host/port/token step + options, live validation
  const.py                          defaults and constants
  client.py                         aiohttp client for the MotionWake API
  coordinator.py                    DataUpdateCoordinator polling GET /status
  entity.py                         shared entity base + device info
  switch.py                         Motion monitoring (start/stop)
  button.py                         wake / sleep / reload dashboard
  sensor.py                         screen state + last-motion age
  manifest.json                     integration manifest
  strings.json                      translations (UI strings)
  translations/
    en.json                         English translations
```
