"""Clients for the Harman Kardon HK 3770.

The amp exposes two independent control surfaces:

1. UPnP DLNA MediaRenderer on port 8080
   Standard SOAP services with real state readback:
     RenderingControl  - GetVolume / SetVolume / GetMute / SetMute
     AVTransport       - Play / Pause / Stop / Next / Previous /
                        SetAVTransportURI / GetTransportInfo / GetMediaInfo
   Volume here is AUTHORITATIVE and AUDIBLE: DLNA SetVolume(N) drives the
   amp's real output. Confirmed mapping (user test): N=1 -> -80 dB (min),
   N=2 -> -79 dB, ... N=91 -> +10 dB (max). So dB = N - 81, clamped.
   Mute is shared with the IR path (both reflect each other).

2. IR-to-IP tunnelling host on port 10025
   Frontier Silicon "ir-ser-FS4444". Accepts the Harman XML envelope and
   fires the equivalent IR code. Commands are accepted SILENTLY - there is
   no acknowledgement, so a successful send proves nothing. Only
   `heart-alive` ever replies (a 257-byte POST-back).
   This is the only way to select sources, power off, navigate the menu,
   drive the tuner, or dim the display.

Why volume comes from DLNA and not IR:
   IR volume-up / volume-down change the amp's loudness but are INVISIBLE to
   DLNA GetVolume (tested: DLNA stayed pinned through repeated IR steps).
   Mixing the two would desync the readback. DLNA gives absolute set + read,
   so the integration uses DLNA for volume and never fires IR volume.

Command vocabulary below is the empirically confirmed set (26 buttons).
Unconfirmed candidates live in tools/hk3770_buttons.py, not here.
"""
from __future__ import annotations

import logging
import re
import socket
import urllib.error
import urllib.request

_LOGGER = logging.getLogger(__name__)

RC_TYPE = "urn:schemas-upnp-org:service:RenderingControl:1"
AT_TYPE = "urn:schemas-upnp-org:service:AVTransport:1"

# --- Confirmed source mnemonics (source-selection <para> -> amp display) ----
# HA-friendly name -> IR para. Order mirrors the remote.
SOURCES: dict[str, str] = {
    "Cable Sat": "Cable Sat",
    "STB": "STB",
    "TV": "TV",
    "CD": "Disc",            # 'CD' itself does nothing; the command is 'Disc'
    "Phono": "Phono",
    "FM": "Radio",           # 'Radio' -> display FM
    "AM": "AM",
    "USB": "USB",            # -> display iPod
    "Bluetooth": "Bluetooth",
    "Home Network": "Home Network",
    "vTuner": "vTuner",
}

# Second-step input assignment (manual p.9), applied to the current source.
INPUT_ASSIGNMENTS: tuple[str, ...] = ("Analog", "Digital")

# Amp real volume range in dB (user-confirmed).
DB_MIN = -80
DB_MAX = 10


def dlna_to_db(level: int) -> int:
    """DLNA 0-100 -> real dB. N=1 -> -80, N=91 -> +10, clamped."""
    return max(DB_MIN, min(DB_MAX, level - 81))


def db_to_dlna(db: int) -> int:
    """Real dB -> DLNA 0-100."""
    return max(0, min(100, db + 81))


class HK3770IRClient:
    """Harman XML -> IR tunnelling client (port 10025)."""

    _TEMPLATE = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<harman><avr><common><control>"
        "<name>{name}</name><zone>{zone}</zone><para>{para}</para>"
        "</control></common></avr></harman>"
    )

    def __init__(self, host: str, port: int = 10025, zone: str = "Main Zone") -> None:
        self.host = host
        self.port = port
        self.zone = zone

    def send(self, name: str, para: str = "", timeout: float = 2.0) -> dict:
        """Fire one IR command.

        Returns dict(ok, raw, error). NOTE: ok=False does NOT mean the
        command was rejected - IR commands are accepted silently. Only
        `heart-alive` ever replies.
        """
        xml = self._TEMPLATE.format(name=name, zone=self.zone, para=para)
        req = (
            "POST AVR HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "User-Agent: Harman Kardon AVR Remote Controller /2.0\r\n"
            f"Content-Length: {len(xml)}\r\n"
            f"\r\n{xml}"
        )
        chunks: list[bytes] = []
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout) as s:
                s.settimeout(timeout)
                s.sendall(req.encode())
                try:
                    while True:
                        c = s.recv(4096)
                        if not c:
                            break
                        chunks.append(c)
                        # Amp holds the socket open after replying; stopping at
                        # the closing tag is ~10x faster than waiting it out.
                        if b"</harman>" in b"".join(chunks) or sum(map(len, chunks)) > 8192:
                            break
                except socket.timeout:
                    pass
        except OSError as err:
            _LOGGER.debug("IR %s failed: %s", name, err)
            return {"ok": False, "raw": "", "error": type(err).__name__}
        raw = b"".join(chunks).decode("utf-8", "replace")
        return {"ok": bool(raw), "raw": raw, "error": None}

    # --- confirmed command helpers ----------------------------------------

    def select_source(self, para: str) -> None:
        """Select an input source by its IR mnemonic."""
        self.send("source-selection", para)

    def assign_input(self, para: str) -> None:
        """Assign a physical input (Analog / Digital) to the current source.

        Per the owner's manual this is a second step after selecting a source:
        'press the CD source button, and then press the AUX button to assign
        ANA 1 input to the CD source.'
        """
        self.send("source-selection", para)

    def power_off(self) -> None:
        """Standby. Network stack goes down; cannot be reversed over the network."""
        self.send("power-off")

    def nav(self, direction: str) -> None:
        """Menu navigation. Confirmed: up, down, exit. (left/right untested.)"""
        self.send(direction)

    def tune(self, direction: str) -> None:
        """Tuner seek. Confirmed: tune-up, tune-down (no display feedback)."""
        self.send(f"tune-{direction}")

    def tuner_direct(self) -> None:
        """Enter direct frequency-entry mode. Confirmed: 'Direct In'."""
        self.send("direct")

    def tuner_mem(self) -> None:
        """Store current station as preset. Confirmed: 'Set Preset'."""
        self.send("mem")

    def dim_display(self) -> None:
        """Toggle the VFD display. Confirmed: toggles VFD."""
        self.send("dim")

    def volume_up(self) -> None:
        """IR volume step up. Confirmed audible; INVISIBLE to DLNA GetVolume."""
        self.send("volume-up")

    def volume_down(self) -> None:
        """IR volume step down. Confirmed audible; INVISIBLE to DLNA GetVolume."""
        self.send("volume-down")

    def alive(self, attempts: int = 2) -> bool:
        """heart-alive answers only when the amp is powered.

        Retries because the amp drops ~17% of keepalives while running.
        """
        for _ in range(attempts):
            if self.send("heart-alive")["ok"]:
                return True
        return False

    # --- confirmed via decompiled official app (com.harman.hkremote) -----

    def key(self, digit: str) -> None:
        """One digit of a direct-entry frequency: name 'Key', para=digit."""
        self.send("Key", str(digit))

    def tune_direct(self, digits: str) -> None:
        """Enter direct mode then type a frequency digit string (no decimal).

        The amp's display carries a fixed decimal point, so 101.5 MHz is
        entered as the digits "1015". Confirmed sequence: direct -> Key x N.
        """
        self.send("direct")
        for d in digits:
            self.send("Key", d)

    def top_menu(self) -> None:
        """Open the on-screen menu (HK3700_MENU -> 'top-menu')."""
        self.send("top-menu")

    def rds(self) -> None:
        """Toggle RDS information."""
        self.send("rds")

    def speaker_switch(self, which: str) -> None:
        """Toggle speaker group 'A' or 'B'."""
        self.send("speaker_switch", which)

    def harman_volume(self) -> None:
        """Cycle Harman Volume High -> Low -> Off (HK 3770)."""
        self.send("harman_volume")

    def auto_preset(self) -> None:
        """Auto-program the tuner presets."""
        self.send("auto_preset")

    def tone_control(self) -> None:
        """Open the tone (bass/treble) control."""
        self.send("tone_control")

    def clear(self) -> None:
        """Clear the direct-entry buffer."""
        self.send("clear")


class HK3770UPnPClient:
    """DLNA MediaRenderer SOAP client (port 8080)."""

    def __init__(self, host: str, port: int = 8080) -> None:
        self.host = host
        self.port = port

    def _soap(self, svc_type: str, path: str, action: str, args: dict,
              timeout: float = 4.0):
        body = "".join(f"<u:{k}>{v}</u:{k}>" for k, v in args.items())
        env = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
            ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{svc_type}">{body}</u:{action}>'
            "</s:Body></s:Envelope>"
        )
        req = urllib.request.Request(
            f"http://{self.host}:{self.port}/{path}",
            data=env.encode(),
            headers={
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction": f'"{svc_type}#{action}"',
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            return None, f"ERR {type(e).__name__}"

    @staticmethod
    def _fields(raw: str) -> dict:
        return dict(re.findall(r"<(?!s:|u:)([A-Za-z0-9_]+)>([^<]*)</\1>", raw))

    # ---- RenderingControl -------------------------------------------------

    def get_volume(self) -> int | None:
        code, raw = self._soap(RC_TYPE, "RenderingControl/control", "GetVolume",
                              {"InstanceID": 0, "Channel": "Master"})
        if code != 200:
            return None
        try:
            return int(self._fields(raw).get("CurrentVolume"))
        except (TypeError, ValueError):
            return None

    def set_volume(self, level: int) -> bool:
        code, _ = self._soap(RC_TYPE, "RenderingControl/control", "SetVolume",
                            {"InstanceID": 0, "Channel": "Master",
                             "DesiredVolume": int(level)})
        return code == 200

    def get_mute(self) -> bool | None:
        code, raw = self._soap(RC_TYPE, "RenderingControl/control", "GetMute",
                              {"InstanceID": 0, "Channel": "Master"})
        if code != 200:
            return None
        return self._fields(raw).get("CurrentMute") == "1"

    def set_mute(self, mute: bool) -> bool:
        code, _ = self._soap(RC_TYPE, "RenderingControl/control", "SetMute",
                            {"InstanceID": 0, "Channel": "Master",
                             "DesiredMute": 1 if mute else 0})
        return code == 200

    # ---- AVTransport ----------------------------------------------------

    def transport_info(self) -> dict:
        code, raw = self._soap(AT_TYPE, "AVTransport/control", "GetTransportInfo",
                              {"InstanceID": 0})
        if code != 200:
            return {}
        return self._fields(raw)

    def media_info(self) -> dict:
        code, raw = self._soap(AT_TYPE, "AVTransport/control", "GetMediaInfo",
                              {"InstanceID": 0})
        if code != 200:
            return {}
        return self._fields(raw)

    def position_info(self) -> dict:
        code, raw = self._soap(AT_TYPE, "AVTransport/control", "GetPositionInfo",
                              {"InstanceID": 0})
        if code != 200:
            return {}
        return self._fields(raw)

    def play(self) -> bool:
        code, _ = self._soap(AT_TYPE, "AVTransport/control", "Play",
                            {"InstanceID": 0, "Speed": "1"})
        return code == 200

    def pause(self) -> bool:
        code, _ = self._soap(AT_TYPE, "AVTransport/control", "Pause",
                            {"InstanceID": 0})
        return code == 200

    def stop(self) -> bool:
        code, _ = self._soap(AT_TYPE, "AVTransport/control", "Stop",
                            {"InstanceID": 0})
        return code == 200

    def next_track(self) -> bool:
        code, _ = self._soap(AT_TYPE, "AVTransport/control", "Next",
                            {"InstanceID": 0})
        return code == 200

    def previous_track(self) -> bool:
        code, _ = self._soap(AT_TYPE, "AVTransport/control", "Previous",
                            {"InstanceID": 0})
        return code == 200

    def set_uri(self, uri: str, metadata: str = "") -> bool:
        code, _ = self._soap(AT_TYPE, "AVTransport/control", "SetAVTransportURI",
                            {"InstanceID": 0, "CurrentURI": uri,
                             "CurrentURIMetaData": metadata})
        return code == 200

    # ---- identity -------------------------------------------------------

    def device_info(self) -> dict:
        """Parse the root device description (dd.xml) for identity."""
        try:
            with urllib.request.urlopen(
                f"http://{self.host}:{self.port}/dd.xml", timeout=4
            ) as r:
                body = r.read().decode("utf-8", "replace")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("dd.xml unavailable: %s", err)
            return {}

        def tag(name: str) -> str | None:
            m = re.search(rf"<{name}>(.*?)</{name}>", body)
            return m.group(1).strip() if m else None

        return {
            "udn": tag("UDN"),
            "friendly_name": tag("friendlyName"),
            "model": tag("modelName"),
            "serial": tag("serialNumber"),
            "manufacturer": tag("manufacturer"),
        }
