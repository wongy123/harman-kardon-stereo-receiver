"""Button entities for the Harman Kardon HK 3700/3770.

These are the IR-only one-shot controls that have no media_player
equivalent: the IR volume steps (for non-DLNA use), the analog/digital
input cyclers, menu navigation, tuner, and display dim.

The cyclers are buttons rather than selects because the IR command CYCLES
the physical input (Analog: A1<->A2; Digital: Optical 1 -> Optical 2 ->
Coaxial) and there is no readback to reflect the current position.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HK37xxCoordinator
from .entity import HK37xxEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass(frozen=True, kw_only=True)
class HK37xxButtonDescription:
    """Describes one IR one-shot button."""

    key: str
    icon: str
    press: Callable[[HK37xxCoordinator], Awaitable[None]]
    entity_category: EntityCategory | None = None
    hk3770_only: bool = False


DESCRIPTIONS: tuple[HK37xxButtonDescription, ...] = (
    # IR volume steps - audible, but invisible to DLNA GetVolume.
    HK37xxButtonDescription(
        key="volume_up",
        icon="mdi:volume-plus",
        press=lambda c: c.async_volume_up(),
    ),
    HK37xxButtonDescription(
        key="volume_down",
        icon="mdi:volume-minus",
        press=lambda c: c.async_volume_down(),
    ),
    # Input assignment cyclers (manual p.9: select a source, then assign).
    HK37xxButtonDescription(
        key="assign_analog",
        icon="mdi:audio-input-rca",
        press=lambda c: c.async_cycle_analog(),
        entity_category=EntityCategory.CONFIG,
    ),
    HK37xxButtonDescription(
        key="assign_digital",
        icon="mdi:toslink",
        press=lambda c: c.async_cycle_digital(),
        hk3770_only=True,
        entity_category=EntityCategory.CONFIG,
    ),
    # Menu navigation (confirmed: up, down, exit).
    HK37xxButtonDescription(
        key="nav_up", icon="mdi:menu-up", press=lambda c: c.async_nav("up")
    ),
    HK37xxButtonDescription(
        key="nav_down", icon="mdi:menu-down", press=lambda c: c.async_nav("down")
    ),
    HK37xxButtonDescription(
        key="nav_exit", icon="mdi:arrow-left", press=lambda c: c.async_nav("exit")
    ),
    # Tuner.
    HK37xxButtonDescription(
        key="tune_up", icon="mdi:access-point-plus", press=lambda c: c.async_tune("up")
    ),
    HK37xxButtonDescription(
        key="tune_down", icon="mdi:access-point-minus", press=lambda c: c.async_tune("down")
    ),
    HK37xxButtonDescription(
        key="tuner_direct", icon="mdi:tune", press=lambda c: c.async_tuner_direct()
    ),
    HK37xxButtonDescription(
        key="tuner_mem", icon="mdi:content-save", press=lambda c: c.async_tuner_mem()
    ),
    # Display.
    HK37xxButtonDescription(
        key="dim_display", icon="mdi:brightness-6", press=lambda c: c.async_dim_display()
    ),
    # Confirmed via the decompiled official app.
    HK37xxButtonDescription(
        key="menu", icon="mdi:menu", press=lambda c: c.async_top_menu()
    ),
    HK37xxButtonDescription(
        key="rds", icon="mdi:radio-tower", press=lambda c: c.async_rds()
    ),
    HK37xxButtonDescription(
        key="speaker_a",
        icon="mdi:speaker",
        press=lambda c: c.async_speaker_switch("A"),
    ),
    HK37xxButtonDescription(
        key="speaker_b",
        icon="mdi:speaker-multiple",
        press=lambda c: c.async_speaker_switch("B"),
    ),
    HK37xxButtonDescription(
        key="harman_volume",
        icon="mdi:volume-equal",
        press=lambda c: c.async_harman_volume(),
        hk3770_only=True,
    ),
    HK37xxButtonDescription(
        key="auto_preset", icon="mdi:auto-fix", press=lambda c: c.async_auto_preset()
    ),
    HK37xxButtonDescription(
        key="tone", icon="mdi:equalizer", press=lambda c: c.async_tone_control()
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "ConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HK37xxCoordinator = entry.runtime_data
    is_3770 = "3770" in str(entry.data.get("model", ""))
    async_add_entities(
        HK37xxButton(coordinator, d)
        for d in DESCRIPTIONS
        if not d.hk3770_only or is_3770
    )


class HK37xxButton(HK37xxEntity, ButtonEntity):
    """One IR one-shot button on the receiver."""

    _attr_entity_registry_enabled_default = True

    def __init__(
        self, coordinator: HK37xxCoordinator, description: HK37xxButtonDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self._description = description
        self._attr_icon = description.icon
        self._attr_translation_key = description.key
        self._attr_entity_category = description.entity_category

    async def async_press(self) -> None:
        await self._description.press(self.coordinator)
