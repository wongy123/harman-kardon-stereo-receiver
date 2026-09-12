"""Data coordinator for the Harman Kardon HK 3700/3770.

One coordinator owns both control surfaces and the single source of truth:

* DLNA (port 8080) is polled for the *readable* state - volume, mute,
  transport. This is the only surface with real readback.
* The IR tunnel (port 10025) is fire-and-forget. Its effects (source,
  input assignment, Harman Volume, display) have NO readback, so the
  coordinator *tracks* the last value it commanded and exposes it as
  best-effort state.

Entities read from the coordinator; they never touch the clients directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import HK3770IRClient, HK3770UPnPClient
from .const import (
    CONF_IR_PORT,
    CONF_UPNP_PORT,
    DEFAULT_IR_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPNP_PORT,
    DOMAIN,
    SOURCES,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass
class HKDlnaState:
    """Snapshot of the DLNA-readable state."""

    reachable: bool = False
    volume: int | None = None          # DLNA 0-100
    mute: bool | None = None
    transport: str | None = None       # PLAYING / PAUSED_PLAYBACK / STOPPED / ...
    media: dict[str, Any] = field(default_factory=dict)


class HK3770Coordinator(DataUpdateCoordinator[HKDlnaState]):
    """Poll DLNA, track IR state, own both clients."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        host = entry.data["host"]
        self.ir = HK3770IRClient(
            host, entry.data.get(CONF_IR_PORT, DEFAULT_IR_PORT)
        )
        self.upnp = HK3770UPnPClient(
            host, entry.data.get(CONF_UPNP_PORT, DEFAULT_UPNP_PORT)
        )
        # IR-tracked (no readback). Seeded from persisted options.
        self.source: str | None = entry.options.get("last_source")

    # ------------------------------------------------------------------ poll
    async def _async_update_data(self) -> HKDlnaState:
        return await self.hass.async_add_executor_job(self._poll)

    def _poll(self) -> HKDlnaState:
        volume = self.upnp.get_volume()
        if volume is None:
            # Amp unreachable (off / standby / network down). Not an error:
            # entities go unavailable, we keep retrying on the interval.
            return HKDlnaState(reachable=False)
        return HKDlnaState(
            reachable=True,
            volume=volume,
            mute=self.upnp.get_mute(),
            transport=self.upnp.transport_info().get("CurrentTransportState"),
            media=self.upnp.media_info(),
        )

    # ------------------------------------------------------- IR commands
    async def async_select_source(self, name: str) -> None:
        para = SOURCES[name]
        await self.hass.async_add_executor_job(self.ir.select_source, para)
        self.source = name
        self._persist_source()
        self.async_set_updated_data(self.data)

    async def async_cycle_analog(self) -> None:
        await self.hass.async_add_executor_job(self.ir.assign_input, "Analog")
        self.async_set_updated_data(self.data)

    async def async_cycle_digital(self) -> None:
        await self.hass.async_add_executor_job(self.ir.assign_input, "Digital")
        self.async_set_updated_data(self.data)

    async def async_volume_up(self) -> None:
        await self.hass.async_add_executor_job(self.ir.volume_up)

    async def async_volume_down(self) -> None:
        await self.hass.async_add_executor_job(self.ir.volume_down)

    async def async_nav(self, direction: str) -> None:
        await self.hass.async_add_executor_job(self.ir.nav, direction)

    async def async_tune(self, direction: str) -> None:
        await self.hass.async_add_executor_job(self.ir.tune, direction)

    async def async_tuner_direct(self) -> None:
        await self.hass.async_add_executor_job(self.ir.tuner_direct)

    async def async_tuner_mem(self) -> None:
        await self.hass.async_add_executor_job(self.ir.tuner_mem)

    async def async_dim_display(self) -> None:
        await self.hass.async_add_executor_job(self.ir.dim_display)

    async def async_power_off(self) -> None:
        await self.hass.async_add_executor_job(self.ir.power_off)

    async def async_top_menu(self) -> None:
        await self.hass.async_add_executor_job(self.ir.top_menu)

    async def async_rds(self) -> None:
        await self.hass.async_add_executor_job(self.ir.rds)

    async def async_speaker_switch(self, which: str) -> None:
        await self.hass.async_add_executor_job(self.ir.speaker_switch, which)

    async def async_harman_volume(self) -> None:
        await self.hass.async_add_executor_job(self.ir.harman_volume)

    async def async_auto_preset(self) -> None:
        await self.hass.async_add_executor_job(self.ir.auto_preset)

    async def async_tone_control(self) -> None:
        await self.hass.async_add_executor_job(self.ir.tone_control)

    async def async_clear_entry(self) -> None:
        await self.hass.async_add_executor_job(self.ir.clear)

    async def async_tune_direct(self, digits: str) -> None:
        await self.hass.async_add_executor_job(self.ir.tune_direct, digits)

    # ------------------------------------------------------- DLNA commands
    async def async_set_volume(self, level: int) -> None:
        await self.hass.async_add_executor_job(self.upnp.set_volume, level)
        await self.async_request_refresh()

    async def async_set_mute(self, mute: bool) -> None:
        await self.hass.async_add_executor_job(self.upnp.set_mute, mute)
        await self.async_request_refresh()

    async def async_play(self) -> None:
        await self.hass.async_add_executor_job(self.upnp.play)
        await self.async_request_refresh()

    async def async_pause(self) -> None:
        await self.hass.async_add_executor_job(self.upnp.pause)
        await self.async_request_refresh()

    async def async_stop(self) -> None:
        await self.hass.async_add_executor_job(self.upnp.stop)
        await self.async_request_refresh()

    async def async_next(self) -> None:
        await self.hass.async_add_executor_job(self.upnp.next_track)
        await self.async_request_refresh()

    async def async_previous(self) -> None:
        await self.hass.async_add_executor_job(self.upnp.previous_track)
        await self.async_request_refresh()

    # ------------------------------------------------------- persistence
    def _persist_source(self) -> None:
        """Remember the last selected source across restarts (no reload)."""
        if self.entry.options.get("last_source") == self.source:
            return
        # async_update_entry is synchronous; safe to call from the loop.
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, "last_source": self.source}
        )
