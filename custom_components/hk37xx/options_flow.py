"""Options flow for HK 3770 (reserved for per-entry tuning)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.core import callback


class HK37xxOptionsFlowHandler(OptionsFlow):
    """Empty options flow placeholder (keeps parity with yamaha_ynca)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=None)
