# Harman Kardon HK 3700 / 3770 — Home Assistant integration

Control a Harman Kardon HK 3700 / 3770 stereo receiver from Home Assistant over the
network. No remote, no cloud — the integration talks directly to the receiver's
Frontier Silicon **IR-over-IP tunnel** (port `10025`) for one-shot commands and its
**DLNA MediaRenderer** endpoint (port `8080`) for state readback.

Discovered automatically via SSDP (`urn:schemas-frontier-silicon-com:fs_reference:iptunnelling:1`),
or added manually by IP.

## Install (HACS)

1. Open **HACS → Integrations → ⋮ → Add custom repository**.
2. Repository: `wongy123/harman-kardon-stereo-receiver`, category **Integration**.
3. Install, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Harman Kardon HK 3700/3770**.
   The receiver is usually already discovered — confirm and finish.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wongy123&repository=harman-kardon-stereo-receiver&category=integration)

### Manual install

Copy `custom_components/hk3770/` into your `config/custom_components/` directory and
restart Home Assistant.

## What you get

### Media player

`media_player.<name>` — power off, volume, mute, play/pause/stop, input/source
select. Volume and mute are read back from DLNA so they stay in sync with the amp.
(Power **on** is not reachable over the network — see the caveat below.)

### Sensors

Transport state and source readout from the DLNA readback surface.

### Buttons (one-shot IR)

| Entity | Function |
|---|---|
| `button.*_volume_up` / `volume_down` | Volume step (IR; audible, not read by DLNA) |
| `button.*_assign_analog` / `assign_digital` | Cycle analog / digital input assignment |
| `button.*_nav_up` / `nav_down` / `nav_exit` | On-screen menu navigation |
| `button.*_tune_up` / `tune_down` | Tune |
| `button.*_tuner_direct_entry` | Enter direct-frequency mode |
| `button.*_tuner_store_preset` | Store tuner preset |
| `button.*_dim_display` | Dim display |
| `button.*_menu` | Open top menu |
| `button.*_rds` | Toggle RDS |
| `button.*_speaker_a` / `speaker_b` | Toggle speaker group A / B |
| `button.*_harman_volume` | Cycle Harman Volume (HK 3770) |
| `button.*_auto_preset` | Auto-program tuner presets |
| `button.*_tone_control` | Open tone (bass/treble) control |

### Number — direct tuner entry

`number.*_tuner_frequency` — set an FM frequency (87.5–108.0 MHz, step 0.1).
Setting the value fires `direct` then the digit keys. The display carries a fixed
decimal point, so `101.5` is entered as the digits `1015` (no dot key exists on
the remote). There is no frequency readback, so the entity reflects the last value
commanded through Home Assistant.

## Power / Wake-on-LAN caveat

**This receiver cannot be powered on over the network.** The device's own UPnP
descriptor declares `magicPacketWakeSupported = 0`, so Wake-on-LAN magic packets
are ignored. The IR-over-IP tunnel (port `10025`) is only served while the amp is
already powered on — when it is in standby the port is closed and there is nothing
to wake.

Practically:

- **Power OFF** works over the network (IR `standby`).
- **Power ON** must be done with the physical remote / front-panel button. Once the
  amp is on, everything else — including power-off — works from Home Assistant.

If you need remote power-on, put the receiver behind a device that can drive its
IR blaster (e.g. a Broadlink / Home Assistant Connect ZBT-1 with an IR blaster) or
a smart plug with a "soft-standby + power-cycle boots on" behaviour — neither is a
property of the receiver itself.

## Requirements

- Home Assistant **2024.8** or newer.
- Receiver on the same LAN as Home Assistant (the IR tunnel is not routed across
  subnets/VLANs by default).
- No third-party Python packages required.

## How it works

- **IR tunnel (port 10025):** the receiver exposes a Frontier Silicon
  `ir-ser-FS4444` service that accepts Harman XML commands and replays them as IR.
  Used for all one-shot controls. Fire-and-forget — no readback.
- **DLNA MediaRenderer (port 8080):** standard UPnP `AVTransport` /
  `RenderingControl` / `ConnectionManager`. Used for volume, mute, transport, and
  source readback, polled on an interval.
- **SSDP discovery:** the IR-tunnel search target is unique to this chip family, so
  discovery does not over-match other DLNA renderers on the LAN.

## License

MIT
