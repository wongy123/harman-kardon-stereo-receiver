"""Constants for the Harman Kardon HK 3700/3770 integration."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT  # noqa: F401  (re-exported)

DOMAIN = "hk37xx"
MANUFACTURER = "Harman Kardon"

# Control surfaces (see client.py for the measured behaviour of each).
DEFAULT_IR_PORT = 10025      # Frontier Silicon "ir-ser-FS4444" IR-to-IP tunnel
DEFAULT_UPNP_PORT = 8080     # DLNA MediaRenderer SOAP endpoint

CONF_IR_PORT = "ir_port"
CONF_UPNP_PORT = "upnp_port"

# SSDP search-target of the Frontier Silicon IR-tunnel device. Unique to this
# chip family, so it is the discovery matcher. (The DLNA MediaRenderer ST is
# shared by every DLNA renderer on the LAN and would over-match.)
SSDP_ST_IPTUNNELLING = (
    "urn:schemas-frontier-silicon-com:fs_reference:iptunnelling:1"
)

# Poll interval for the DLNA readback surface (volume / mute / transport).
DEFAULT_SCAN_INTERVAL = 10

# Friendly source name -> IR <para> for `source-selection`.
# Confirmed against the amp display during probing.
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
# Each press CYCLES the underlying physical input:
#   Analog  -> A1 <-> A2
#   Digital -> Optical 1 -> Optical 2 -> Coaxial   (HK 3770 only)
INPUT_ASSIGNMENTS: tuple[str, ...] = ("Analog", "Digital")

# Harman Volume cycles High -> Low -> Off (HK 3770 only).
HARMAN_VOLUME_LEVELS: tuple[str, ...] = ("High", "Low", "Off")

# Amp real volume range in dB (user-confirmed): DLNA 1 -> -80 dB, 91 -> +10 dB.
DB_MIN = -80
DB_MAX = 10


def dlna_to_db(level: int) -> int:
    """DLNA 0-100 -> real dB. N=1 -> -80, N=91 -> +10, clamped."""
    return max(DB_MIN, min(DB_MAX, level - 81))


def db_to_dlna(db: int) -> int:
    """Real dB -> DLNA 0-100."""
    return max(0, min(100, db + 81))


def mac_from_udn(udn: str | None) -> str | None:
    """Extract the 12-hex MAC suffix shared by both of the amp's UDNs.

    Both the DLNA MediaRenderer UDN (uuid:3dcc7100-...-9c645e16dd90) and the
    Frontier Silicon IR-tunnel UDN (uuid:46c19e4a-...-9c645e16dd90) end in the
    device MAC. Using it as the unique id lets the user-IP flow and the SSDP
    flow converge on one config entry regardless of which UDN they saw.
    """
    if not udn:
        return None
    tail = udn.rsplit("-", 1)[-1]
    if len(tail) == 12 and all(c in "0123456789abcdefABCDEF" for c in tail):
        return tail.lower()
    return None
