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

    async def _async_update_data(self) -> dict[str, Any]:
        headers = {"If-None-Match": self._etag} if self._etag else {}

        try:
            async with (
                asyncio.timeout(REQUEST_TIMEOUT),
                self._session.get(FEED_URL, headers=headers) as response,
            ):
                if response.status == HTTPStatus.NOT_MODIFIED:
                    return self.data
                response.raise_for_status()
                etag = response.headers.get("ETag")
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise UpdateFailed(f"Cannot read {FEED_URL}: {err}") from err

        payload = _require_sections(payload)
        self._etag = etag
        return payload
