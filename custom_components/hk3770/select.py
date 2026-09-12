"""Select entities for the Harman Kardon HK 3700/3770.

`source` mirrors the IR-tracked current source (selecting fires the IR
source-selection command). The analog/digital input *cycler* is exposed as
buttons in button.py because those commands cycle the physical input rather
than set a known value - there is no readback to reflect in a select.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SOURCES
from .coordinator import HK3770Coordinator
from .entity import HK3770Entity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "ConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HK3770Coordinator = entry.runtime_data
    async_add_entities([HK3770SourceSelect(coordinator)])


class HK3770SourceSelect(HK3770Entity, SelectEntity):
    """Current input source; selecting sends the IR source-selection."""

    _attr_translation_key = "source"
    _attr_options = list(SOURCES)
    _attr_icon = "mdi:import"

    def __init__(self, coordinator: HK3770Coordinator) -> None:
        super().__init__(coordinator, "source")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.source

    async def async_select_option(self, option: str) -> None:
        if option not in SOURCES:
            raise ValueError(f"Unknown source: {option}")
        await self.coordinator.async_select_source(option)
