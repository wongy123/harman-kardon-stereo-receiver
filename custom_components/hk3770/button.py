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

from .coordinator import HK3770Coordinator
from .entity import HK3770Entity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass(frozen=True, kw_only=True)
class HK3770ButtonDescription:
    """Describes one IR one-shot button."""

    key: str
    icon: str
    press: Callable[[HK3770Coordinator], Awaitable[None]]
    entity_category: EntityCategory | None = None
    hk3770_only: bool = False


DESCRIPTIONS: tuple[HK3770ButtonDescription, ...] = (
    # IR volume steps - audible, but invisible to DLNA GetVolume.
    HK3770ButtonDescription(
        key="volume_up",
        icon="mdi:volume-plus",
        press=lambda c: c.async_volume_up(),
    ),
    HK3770ButtonDescription(
        key="volume_down",
        icon="mdi:volume-minus",
        press=lambda c: c.async_volume_down(),
    ),
    # Input assignment cyclers (manual p.9: select a source, then assign).
    HK3770ButtonDescription(
        key="assign_analog",
        icon="mdi:audio-input-rca",
        press=lambda c: c.async_cycle_analog(),
        entity_category=EntityCategory.CONFIG,
    ),
    HK3770ButtonDescription(
        key="assign_digital",
        icon="mdi:toslink",
        press=lambda c: c.async_cycle_digital(),
        hk3770_only=True,
        entity_category=EntityCategory.CONFIG,
    ),
    # Menu navigation (confirmed: up, down, exit).
    HK3770ButtonDescription(
        key="nav_up", icon="mdi:menu-up", press=lambda c: c.async_nav("up")
    ),
    HK3770ButtonDescription(
        key="nav_down", icon="mdi:menu-down", press=lambda c: c.async_nav("down")
    ),
    HK3770ButtonDescription(
        key="nav_exit", icon="mdi:arrow-left", press=lambda c: c.async_nav("exit")
    ),
    # Tuner.
    HK3770ButtonDescription(
        key="tune_up", icon="mdi:access-point-plus", press=lambda c: c.async_tune("up")
    ),
    HK3770ButtonDescription(
        key="tune_down", icon="mdi:access-point-minus", press=lambda c: c.async_tune("down")
    ),
    HK3770ButtonDescription(
        key="tuner_direct", icon="mdi:tune", press=lambda c: c.async_tuner_direct()
    ),
    HK3770ButtonDescription(
        key="tuner_mem", icon="mdi:content-save", press=lambda c: c.async_tuner_mem()
    ),
    # Display.
    HK3770ButtonDescription(
        key="dim_display", icon="mdi:brightness-6", press=lambda c: c.async_dim_display()
    ),
    # Confirmed via the decompiled official app.
    HK3770ButtonDescription(
        key="menu", icon="mdi:menu", press=lambda c: c.async_top_menu()
    ),
    HK3770ButtonDescription(
        key="rds", icon="mdi:radio-tower", press=lambda c: c.async_rds()
    ),
    HK3770ButtonDescription(
        key="speaker_a",
        icon="mdi:speaker",
        press=lambda c: c.async_speaker_switch("A"),
    ),
    HK3770ButtonDescription(
        key="speaker_b",
        icon="mdi:speaker-multiple",
        press=lambda c: c.async_speaker_switch("B"),
    ),
    HK3770ButtonDescription(
        key="harman_volume",
        icon="mdi:volume-equal",
        press=lambda c: c.async_harman_volume(),
        hk3770_only=True,
    ),
    HK3770ButtonDescription(
        key="auto_preset", icon="mdi:auto-fix", press=lambda c: c.async_auto_preset()
    ),
    HK3770ButtonDescription(
        key="tone", icon="mdi:equalizer", press=lambda c: c.async_tone_control()
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "ConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HK3770Coordinator = entry.runtime_data
    is_3770 = "3770" in str(entry.data.get("model", ""))
    async_add_entities(
        HK3770Button(coordinator, d)
        for d in DESCRIPTIONS
        if not d.hk3770_only or is_3770
    )


class HK3770Button(HK3770Entity, ButtonEntity):
    """One IR one-shot button on the receiver."""

    _attr_entity_registry_enabled_default = True

    def __init__(
        self, coordinator: HK3770Coordinator, description: HK3770ButtonDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self._description = description
        self._attr_icon = description.icon
        self._attr_translation_key = description.key
        self._attr_entity_category = description.entity_category

    async def async_press(self) -> None:
        await self._description.press(self.coordinator)
