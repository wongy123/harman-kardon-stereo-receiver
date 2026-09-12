"""Base entity for the Harman Kardon HK 3700/3770 integration.

All entities attach to ONE device (the receiver) via the shared MAC
identifier, following the yamaha_ynca pattern: the media_player is just
one facet of the device; selects/buttons/numbers are the others.
"""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HK3770Coordinator


class HK3770Entity(CoordinatorEntity[HK3770Coordinator]):
    """Common base: one device, has-entity-name, availability from DLNA poll."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HK3770Coordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.data['mac']}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["mac"])},
            manufacturer="Harman Kardon",
            model=entry.data.get("model", "HK 3770"),
            name=entry.title,
            serial_number=entry.data.get("serial"),
            configuration_url=(
                f"http://{entry.data['host']}:"
                f"{entry.data.get('upnp_port', 8080)}"
            ),
        )

    @property
    def available(self) -> bool:
        """IR-only controls need the amp reachable (network dies in standby)."""
        return bool(self.coordinator.data and self.coordinator.data.reachable)
