"""Minimal async client for the MotionWake HTTP API."""

from __future__ import annotations

import asyncio
import json
import logging

import aiohttp

_LOGGER = logging.getLogger(__package__)

TOKEN_HEADER = "X-MotionWake-Token"

# Most endpoints return quickly. /sleep runs the tablet's own
# nap -> screensaver -> sleep pipeline, which can take well over a
# minute on some Fire builds, so allow time.
TIMEOUT_NORMAL = 30
TIMEOUT_SLEEP = 200
TIMEOUT_UPDATE = 240

# Sanity bounds for APK bytes fetched for OTA (app allows up to 64 MiB).
APK_MAX_BYTES = 60 * 1024 * 1024


class MotionWakeError(Exception):
    """Base error for MotionWake communication problems."""


class MotionWakeConnectionError(MotionWakeError):
    """Raised when the tablet cannot be reached."""


class MotionWakeAuthError(MotionWakeError):
    """Raised when the tablet rejects the token (HTTP 401)."""


class MotionWakeClient:
    """Talks to the MotionWake app on a Fire tablet over LAN HTTP.

    Endpoint reference (see the firetablet-app README, "HTTP API"):

    GET  /status           -> device + monitor state (token required)
    GET  /settings         -> idle_minutes / threshold / check_seconds / auto_start
    POST /settings         -> partial update of any of the above (applied live)
    POST /start            -> start the motion monitor
    POST /stop             -> stop the motion monitor
    POST /shutdown         -> stop the service (restarts via BootStarter)
    POST /wake             -> wake the display now
    POST /sleep            -> put the display to sleep now
    GET  /browser          -> stored dashboard URL
    POST /browser          -> set the dashboard URL ({"url": "..."}) and open it
    POST /browser/reload   -> reload the stored dashboard URL
    POST /update           -> raw APK bytes; staged install + app restart
    GET  /update/status    -> none | pending | applied + version + last result
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str):
        self._session = session
        self._base = f"http://{host}:{int(port)}"
        self._token = token

    async def _request(
        self,
        method: str,
        path: str,
        timeout: int,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> dict:
        url = f"{self._base}{path}"
        headers = {TOKEN_HEADER: self._token}
        if content_type:
            headers["Content-Type"] = content_type
        try:
            async with self._session.request(
                method,
                url,
                data=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status == 401:
                    raise MotionWakeAuthError(f"bad token for {url}")
                if resp.status < 200 or resp.status >= 300:
                    raise MotionWakeError(f"{method} {path} -> HTTP {resp.status}: {data!r}")
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise MotionWakeConnectionError(f"cannot reach {url}: {err}") from err

    # ------------------------------------------------------------- state

    async def get_status(self) -> dict:
        """GET /status — full state, used for validation and polling."""
        data = await self._request("GET", "/status", TIMEOUT_NORMAL)
        if not isinstance(data, dict) or data.get("ok") is not True:
            raise MotionWakeError(f"unexpected /status payload: {data!r}")
        return data

    # --------------------------------------------------------- settings

    async def get_settings(self) -> dict:
        """GET /settings — current settings incl. auto_start."""
        return await self._request("GET", "/settings", TIMEOUT_NORMAL)

    async def set_settings(self, settings: dict) -> dict:
        """POST /settings — partial update; applied live by the app.

        Recognized keys (any subset): idle_minutes, threshold, check_seconds.
        """
        payload = {k: v for k, v in settings.items() if v is not None}
        if not payload:
            raise MotionWakeError("set_settings: no non-null values")
        body = json.dumps(payload).encode()
        return await self._request(
            "POST", "/settings", TIMEOUT_NORMAL, body=body,
            content_type="application/json",
        )

    # ------------------------------------------------------- monitor ops

    async def start(self) -> dict:
        """POST /start — start monitoring."""
        return await self._request("POST", "/start", TIMEOUT_NORMAL)

    async def stop(self) -> dict:
        """POST /stop — stop monitoring."""
        return await self._request("POST", "/stop", TIMEOUT_NORMAL)

    async def shutdown(self) -> dict:
        """POST /shutdown — stop the app service (BootStarter restarts it)."""
        return await self._request("POST", "/shutdown", TIMEOUT_NORMAL)

    async def wake(self) -> dict:
        """POST /wake — wake the display."""
        return await self._request("POST", "/wake", TIMEOUT_NORMAL)

    async def sleep(self) -> dict:
        """POST /sleep — put the display to sleep (long-running on Fire)."""
        return await self._request("POST", "/sleep", TIMEOUT_SLEEP)

    # ---------------------------------------------------------- browser

    async def get_browser(self) -> dict:
        """GET /browser — stored dashboard URL + browser package."""
        return await self._request("GET", "/browser", TIMEOUT_NORMAL)

    async def set_browser(self, url: str) -> dict:
        """POST /browser — set the dashboard URL (and open it)."""
        body = json.dumps({"url": url.strip()}).encode()
        return await self._request(
            "POST", "/browser", TIMEOUT_NORMAL, body=body,
            content_type="application/json",
        )

    async def reload_dashboard(self) -> dict:
        """POST /browser/reload — reload the stored dashboard URL."""
        return await self._request("POST", "/browser/reload", TIMEOUT_NORMAL)

    # ------------------------------------------------------ OTA update

    async def get_update_status(self) -> dict:
        """GET /update/status — OTA state (none|pending|applied) + version."""
        return await self._request("GET", "/update/status", TIMEOUT_NORMAL)

    async def post_update(self, apk: bytes) -> dict:
        """POST /update — ship raw APK bytes; the app stages + installs."""
        return await self._request(
            "POST", "/update", TIMEOUT_UPDATE, body=apk,
            content_type="application/octet-stream",
        )

    async def fetch_apk(self, source: str) -> bytes:
        """Fetch a release APK from an http(s) URL or a local file path."""
        source = source.strip()
        if source.lower().startswith(("http://", "https://")):
            try:
                async with self._session.get(
                    source, timeout=aiohttp.ClientTimeout(total=180)
                ) as resp:
                    if not (200 <= resp.status < 300):
                        raise MotionWakeError(f"APK fetch -> HTTP {resp.status}")
                    data = await resp.read()
            except aiohttp.ClientError as err:
                raise MotionWakeConnectionError(f"cannot fetch APK: {err}") from err
        else:
            def _read() -> bytes:
                with open(source, "rb") as fh:  # noqa: SIM115
                    return fh.read()

            try:
                data = await asyncio.to_thread(_read)
            except OSError as err:
                raise MotionWakeConnectionError(f"cannot read APK file: {err}") from err
        if len(data) < 65536:
            raise MotionWakeError(f"APK too small ({len(data)} bytes) to be an APK")
        if len(data) > APK_MAX_BYTES:
            raise MotionWakeError(f"APK too large ({len(data)} bytes)")
        if (data[0] & 0xFF) != 0x50 or (data[1] & 0xFF) != 0x4B:
            raise MotionWakeError("not a ZIP/APK (missing PK header)")
        _LOGGER.debug("fetched APK %d bytes from %s", len(data), source)
        return data
