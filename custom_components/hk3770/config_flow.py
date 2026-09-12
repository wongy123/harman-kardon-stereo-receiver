"""Config flow for the Harman Kardon HK 3700/3770 integration.

Two entry paths converge on one config entry keyed by the device MAC:

* user  - type an IP, we probe the DLNA dd.xml for identity.
* ssdp  - the Frontier Silicon IR-tunnel advertisement (ST
          urn:schemas-frontier-silicon-com:fs_reference:iptunnelling:1).

Both UDNs end in the device MAC, so `mac_from_udn` gives a unique id that
matches whichever path saw the device first.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.components import ssdp
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import callback

from .client import HK3770UPnPClient
from .const import (
    CONF_IR_PORT,
    CONF_UPNP_PORT,
    DEFAULT_IR_PORT,
    DEFAULT_UPNP_PORT,
    DOMAIN,
    mac_from_udn,
)

_LOGGER = logging.getLogger(__name__)


def _probe_identity(host: str) -> dict[str, Any]:
    """Fetch dd.xml from the DLNA endpoint; return identity or raise."""
    client = HK3770UPnPClient(host, DEFAULT_UPNP_PORT)
    info = client.device_info()
    if not info or not info.get("udn"):
        raise ConnectionError(f"No HK3770 DLNA identity at {host}")
    mac = mac_from_udn(info["udn"])
    if not mac:
        raise ConnectionError(f"Could not derive MAC from UDN {info['udn']}")
    return {
        "mac": mac,
        "model": info.get("model") or "HK 3770",
        "serial": info.get("serial"),
        "udn": info["udn"],
    }


class HK3770ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HK 3700/3770."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import HK3770OptionsFlowHandler

        return HK3770OptionsFlowHandler(config_entry)

    # ------------------------------------------------------------- user
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                identity = await self.hass.async_add_executor_job(
                    _probe_identity, host
                )
            except ConnectionError:
                errors[CONF_HOST] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error probing %s", host)
                errors[CONF_HOST] = "unknown"
            else:
                await self.async_set_unique_id(identity["mac"])
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host},
                    reload_on_update=True,
                )
                return self._create(identity, host)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(
                        CONF_IR_PORT, default=DEFAULT_IR_PORT
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_UPNP_PORT, default=DEFAULT_UPNP_PORT
                    ): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    # ------------------------------------------------------------- ssdp
    async def async_step_ssdp(
        self, discovery_info: ssdp.SsdpServiceInfo
    ) -> ConfigFlowResult:
        # The IR-tunnel UDN carries the MAC directly.
        mac = mac_from_udn(discovery_info.udn)
        if not mac:
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        # Host from the tunnel location URL (http://IP:7070/...).
        host = urlparse(discovery_info.location).hostname
        if not host:
            return self.async_abort(reason="cannot_connect")

        # Confirm the DLNA surface and grab model/serial for a nice title.
        try:
            identity = await self.hass.async_add_executor_job(
                _probe_identity, host
            )
        except ConnectionError:
            # Reachable on SSDP but DLNA dd.xml missing - still usable;
            # fall back to a generic identity.
            identity = {
                "mac": mac,
                "model": "HK 3770",
                "serial": None,
                "udn": discovery_info.udn,
            }

        self._identity = identity
        self._host = host
        self.context["title_placeholders"] = {"name": identity["model"]}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._create(self._identity, self._host)
        return self.async_show_form(step_id="confirm")

    def _create(self, identity: dict[str, Any], host: str) -> ConfigFlowResult:
        return self.async_create_entry(
            title=identity["model"],
            data={
                CONF_HOST: host,
                CONF_IR_PORT: DEFAULT_IR_PORT,
                CONF_UPNP_PORT: DEFAULT_UPNP_PORT,
                "mac": identity["mac"],
                "model": identity["model"],
                "serial": identity["serial"],
            },
        )

    # ------------------------------------------------------- reconfigure
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                identity = await self.hass.async_add_executor_job(
                    _probe_identity, host
                )
            except ConnectionError:
                errors[CONF_HOST] = "cannot_connect"
            else:
                await self.async_set_unique_id(identity["mac"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_IR_PORT: user_input.get(CONF_IR_PORT, DEFAULT_IR_PORT),
                        CONF_UPNP_PORT: user_input.get(
                            CONF_UPNP_PORT, DEFAULT_UPNP_PORT
                        ),
                        "model": identity["model"],
                        "serial": identity["serial"],
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=entry.data.get(CONF_HOST)
                    ): str,
                    vol.Optional(
                        CONF_IR_PORT,
                        default=entry.data.get(CONF_IR_PORT, DEFAULT_IR_PORT),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_UPNP_PORT,
                        default=entry.data.get(CONF_UPNP_PORT, DEFAULT_UPNP_PORT),
                    ): vol.Coerce(int),
                }
            ),
            errors=errors,
        )
