"""Number entities for the Harman Kardon HK 3700/3770.

One entity: direct FM tuner frequency entry. Setting the value fires the
`direct` command followed by the frequency's digits as `Key` commands.
The amp's display carries a fixed decimal point, so 101.5 MHz is typed as
the digits "1015" (no dot key exists on the remote). There is no readback
of the tuned frequency, so the entity reflects the last value commanded
through Home Assistant.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    async_add_entities([HK3770TunerFrequencyNumber(coordinator)])


class HK3770TunerFrequencyNumber(HK3770Entity, NumberEntity):
    """Direct FM frequency entry: `direct` then the digit keys."""

    _attr_translation_key = "tuner_frequency"
    _attr_icon = "mdi:numeric"
    _attr_native_min_value = 87.5
    _attr_native_max_value = 108.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "MHz"
    _attr_native_value: float | None = None

    def __init__(self, coordinator: HK3770Coordinator) -> None:
        super().__init__(coordinator, "tuner_frequency")

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        digits = f"{value:.1f}".replace(".", "")
        await self.coordinator.async_tune_direct(digits)
