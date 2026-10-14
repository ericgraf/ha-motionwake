"""Minimal async client for the MotionWake HTTP API."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

_LOGGER = logging.getLogger(__package__)

TOKEN_HEADER = "X-MotionWake-Token"

# Most endpoints return quickly. /sleep runs the tablet's own
# nap -> screensaver -> sleep pipeline, which can take well over a
# minute on some Fire builds, so allow time.
TIMEOUT_NORMAL = 30
TIMEOUT_SLEEP = 200


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
    POST /start            -> start the motion monitor
    POST /stop             -> stop the motion monitor
    POST /wake             -> wake the display now
    POST /sleep            -> put the display to sleep now
    POST /browser/reload   -> reload the stored dashboard URL
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str):
        self._session = session
        self._base = f"http://{host}:{int(port)}"
        self._token = token

    async def _request(self, method: str, path: str, timeout: int) -> dict:
        url = f"{self._base}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers={TOKEN_HEADER: self._token},
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

    async def get_status(self) -> dict:
        """GET /status — full state, used for validation and polling."""
        data = await self._request("GET", "/status", TIMEOUT_NORMAL)
        if not isinstance(data, dict) or data.get("ok") is not True:
            raise MotionWakeError(f"unexpected /status payload: {data!r}")
        return data

    async def start(self) -> dict:
        """POST /start — start monitoring."""
        return await self._request("POST", "/start", TIMEOUT_NORMAL)

    async def stop(self) -> dict:
        """POST /stop — stop monitoring."""
        return await self._request("POST", "/stop", TIMEOUT_NORMAL)

    async def wake(self) -> dict:
        """POST /wake — wake the display."""
        return await self._request("POST", "/wake", TIMEOUT_NORMAL)

    async def sleep(self) -> dict:
        """POST /sleep — put the display to sleep (long-running on Fire)."""
        return await self._request("POST", "/sleep", TIMEOUT_SLEEP)

    async def reload_dashboard(self) -> dict:
        """POST /browser/reload — reload the stored dashboard URL."""
        return await self._request("POST", "/browser/reload", TIMEOUT_NORMAL)
