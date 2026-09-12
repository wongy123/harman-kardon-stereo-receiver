"""Media player platform for the Harman Kardon HK 3700/3770.

This is the *media* facet of the receiver device. Volume / mute / transport
come from DLNA (the only surface with readback); source selection and power
go over the IR tunnel. The IR-only one-shot controls (volume steps, input
cycling, nav, tuner, dim, speakers) live in button.py / select.py, not here.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
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
    async_add_entities([HK3770MediaPlayer(coordinator)])


class HK3770MediaPlayer(HK3770Entity, MediaPlayerEntity):
    """DLNA-backed media player for the HK 3770."""

    _attr_name = None  # device name is the entity name (has_entity_name)
    _attr_translation_key = "player"

    # No TURN_ON: the amp cannot be powered on over the network (standby
    # drops the network stack). Power-off works via IR while it is on.
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, coordinator: HK3770Coordinator) -> None:
        super().__init__(coordinator, "player")

    # ------------------------------------------------------------- state
    @property
    def state(self) -> MediaPlayerState:
        data = self.coordinator.data
        if not data or not data.reachable:
            return MediaPlayerState.OFF
        transport = (data.transport or "").upper()
        if transport == "PLAYING":
            return MediaPlayerState.PLAYING
        if transport in ("PAUSED_PLAYBACK", "PAUSED"):
            return MediaPlayerState.PAUSED
        if transport == "STOPPED":
            return MediaPlayerState.IDLE
        return MediaPlayerState.ON

    @property
    def volume_level(self) -> float | None:
        if not self.coordinator.data or self.coordinator.data.volume is None:
            return None
        return self.coordinator.data.volume / 100.0

    @property
    def is_volume_muted(self) -> bool | None:
        return self.coordinator.data.mute if self.coordinator.data else None

    @property
    def source(self) -> str | None:
        return self.coordinator.source

    @property
    def source_list(self) -> list[str]:
        return list(SOURCES)

    @property
    def media_title(self) -> str | None:
        return (self.coordinator.data.media or {}).get("CurrentURI") or None

    # ---------------------------------------------------------- actions
    async def async_set_volume_level(self, volume: float) -> None:
        await self.coordinator.async_set_volume(round(volume * 100))

    async def async_volume_up(self) -> None:
        cur = self.coordinator.data.volume if self.coordinator.data else None
        if cur is not None:
            await self.coordinator.async_set_volume(min(100, cur + 1))

    async def async_volume_down(self) -> None:
        cur = self.coordinator.data.volume if self.coordinator.data else None
        if cur is not None:
            await self.coordinator.async_set_volume(max(0, cur - 1))

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.async_set_mute(mute)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_power_off()

    async def async_turn_on(self) -> None:
        # Not reachable over the network from standby; feature not advertised.
        raise NotImplementedError

    async def async_media_play(self) -> None:
        await self.coordinator.async_play()

    async def async_media_pause(self) -> None:
        await self.coordinator.async_pause()

    async def async_media_stop(self) -> None:
        await self.coordinator.async_stop()

    async def async_media_next_track(self) -> None:
        await self.coordinator.async_next()

    async def async_media_previous_track(self) -> None:
        await self.coordinator.async_previous()

    async def async_select_source(self, source: str) -> None:
        if source not in SOURCES:
            raise ValueError(f"Unknown source: {source}")
        await self.coordinator.async_select_source(source)
