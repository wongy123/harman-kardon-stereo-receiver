"""The Harman Kardon HK 3700/3770 integration.

Configured via the UI (config flow) - either by IP or by SSDP discovery of
the Frontier Silicon IR-tunnel device. YAML setup is not supported; the
old `media_player: - platform: hk37xx` block must be removed.

One config entry = one receiver device. The device carries:

* media_player   - IR receiver controls with DLNA state readback
* select         - source selector
* button         - IR one-shots (volume steps, analog/digital cycler,
                   nav, tuner, dim)
* sensor         - transport + source readouts

Entities are grouped in the UI: day-to-day controls sit under Controls;
the input-assignment cyclers and the diagnostic transport sensor are
flagged as Configuration.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import HK37xxCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.NUMBER,
]

type HK37xxConfigEntry = ConfigEntry[HK37xxCoordinator]


async def async_setup(_hass: HomeAssistant, _config: "ConfigType") -> bool:
    """Set up the integration (config entries only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HK37xxConfigEntry) -> bool:
    """Set up an HK 3700/3770 from a config entry."""
    coordinator = HK37xxCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(
            f"Could not reach HK 3700/3770 at {entry.data['host']}"
        ) from err

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HK37xxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
