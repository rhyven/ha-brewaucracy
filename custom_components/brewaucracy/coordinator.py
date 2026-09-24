from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from http import HTTPStatus
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "brewaucracy"
FEED_URL = "https://brewaucracy.ericlight.com:23377/v1/taproom.json"
SCAN_INTERVAL = timedelta(seconds=60)
REQUEST_TIMEOUT = 30
SECTIONS = ("taps", "food_trucks", "news")
CONSECUTIVE_FETCH_FAILURES_TOLERATED_BEFORE_UNAVAILABLE = 3


def _require_sections(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise UpdateFailed("Feed did not contain a JSON object")
    for name in SECTIONS:
        section = payload.get(name)
        items = section.get("items") if isinstance(section, dict) else None
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise UpdateFailed(f"Feed section '{name}' is malformed")
    return payload


class BrewaucracyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self._session = session
        self._etag: str | None = None
        self._consecutive_failures = 0

    async def _async_update_data(self) -> dict[str, Any]:
        headers = {"If-None-Match": self._etag} if self._etag else {}

        try:
            async with (
                asyncio.timeout(REQUEST_TIMEOUT),
                self._session.get(FEED_URL, headers=headers) as response,
            ):
                if response.status == HTTPStatus.NOT_MODIFIED:
                    self._consecutive_failures = 0
                    return self.data
                response.raise_for_status()
                etag = response.headers.get("ETag")
                payload = await response.json(content_type=None)
            payload = _require_sections(payload)
        except (TimeoutError, aiohttp.ClientError, ValueError, UpdateFailed) as err:
            if self.data is not None and (
                self._consecutive_failures
                < CONSECUTIVE_FETCH_FAILURES_TOLERATED_BEFORE_UNAVAILABLE
            ):
                self._consecutive_failures += 1
                _LOGGER.warning(
                    "Cannot read %s (%s); using last known data (failure %d/%d)",
                    FEED_URL,
                    err,
                    self._consecutive_failures,
                    CONSECUTIVE_FETCH_FAILURES_TOLERATED_BEFORE_UNAVAILABLE,
                )
                return self.data
            raise UpdateFailed(f"Cannot read {FEED_URL}: {err}") from err

        self._consecutive_failures = 0
        self._etag = etag
        return payload
