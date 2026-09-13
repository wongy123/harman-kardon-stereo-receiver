"""Sensor entities for the Harman Kardon HK 3700/3770.

Diagnostic readouts from the DLNA surface. The IR-tracked source is
mirrored here as a read-only sensor so dashboards can show it without
exposing the select control.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HK37xxCoordinator
from .entity import HK37xxEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "ConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HK37xxCoordinator = entry.runtime_data
    async_add_entities(
        [
            HK37xxTransportSensor(coordinator),
            HK37xxSourceSensor(coordinator),
        ]
    )


class HK37xxTransportSensor(HK37xxEntity, SensorEntity):
    """Raw DLNA transport state."""

    _attr_translation_key = "transport"
    _attr_icon = "mdi:play-circle-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: HK37xxCoordinator) -> None:
        super().__init__(coordinator, "transport")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.transport if self.coordinator.data else None


class HK37xxSourceSensor(HK37xxEntity, SensorEntity):
    """IR-tracked current source (read-only mirror)."""

    _attr_translation_key = "source_sensor"
    _attr_icon = "mdi:input-source"

    def __init__(self, coordinator: HK37xxCoordinator) -> None:
        super().__init__(coordinator, "source_sensor")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.source
