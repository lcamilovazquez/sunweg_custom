"""
The top-level initialization for the SunWEG integration.

This file sets up the integration within Home Assistant, managing the
communication with the remote API via an update coordinator and exposing
sensor entities for energy production, power and other metrics.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SunWegAPI, SunWegAPIError, SunWegAuthError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SunWEG integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    plant_id: str = entry.data[CONF_PLANT_ID]

    session = aiohttp_client.async_get_clientsession(hass)
    api = SunWegAPI(session, username, password)
    try:
        # Authenticate before starting the coordinator to ensure the token is available
        await api.async_login()
    except SunWegAuthError as err:
        _LOGGER.error("SunWEG authentication error: %s", err)
        raise ConfigEntryNotReady from err
    except SunWegAPIError as err:
        _LOGGER.error("SunWEG API communication error: %s", err)
        raise ConfigEntryNotReady from err

    async def async_update_data() -> Dict[str, Any]:
        """Fetch the latest data from SunWEG for the configured plant."""
        try:
            # Fetch plant-specific summary
            resumo = await api.async_get_resumo(plant_id)
            # Fetch aggregated totals
            totalizers = await api.async_get_totalizadores()
        except SunWegAuthError as err:
            # Authentication error implies token expiry; raise UpdateFailed to trigger a retry
            _LOGGER.warning("Authentication failure during update: %s", err)
            raise UpdateFailed("Authentication failure") from err
        except SunWegAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err
        return {
            "resumo": resumo,
            "totalizers": totalizers,
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"SunWEG Data ({plant_id})",
        update_method=async_update_data,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    # Fetch initial data to validate connection
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "plant_id": plant_id,
    }

    # Forward setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
