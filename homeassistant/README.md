# Jacuzzi Spa — Home Assistant custom integration

Native Home Assistant integration for Jacuzzi / Sundance spas connected through an RS485-to-TCP bridge (encrypted controllers supported). No MQTT required.

## What you get

| Entity | Type | Notes |
|--------|------|--------|
| Temperature | Climate | Current + setpoint; set temperature remotely |
| Pump 1 | Switch | On / off |
| Pump 2 | Switch | On / off |
| Lights | Switch | On (color cycle) / off |
| Current temperature | Sensor | Read-only |
| Setpoint temperature | Sensor | Read-only |
| Connection state | Sensor | Connected / disconnected |
| Heat state | Sensor | Idle / heating |

Not exposed (not supported over RS485 on encrypted boards): heat mode, filters, locks, absolute brightness, date/time.

## Requirements

- Home Assistant OS, Supervised, Container, or Core (tested path: HA OS at `http://homeassistant.local/`)
- Spa bridge reachable from the HA host (example: `192.168.0.8:8899`)
- This integration folder: `custom_components/jacuzzi_spa/`

## Install on Home Assistant OS

1. Copy the entire `jacuzzi_spa` folder into your HA config:

   ```text
   /config/custom_components/jacuzzi_spa/
   ```

   Ways to copy:
   - **Samba share** add-on: mount the `config` share and copy the folder
   - **Studio Code Server** / **File editor** add-on: upload or create the files under `custom_components/`
   - **SSH** add-on: `scp -r custom_components/jacuzzi_spa root@homeassistant.local:/config/custom_components/`

2. Restart Home Assistant (**Settings → System → Restart**).

3. Go to **Settings → Devices & Services → Add Integration**.

4. Search for **Jacuzzi Spa**.

5. Enter:
   - **Host:** `192.168.0.8` (your bridge IP)
   - **Port:** `8899`

6. Submit. You should see a Jacuzzi Spa device with climate, switches, and sensors.

## Update

Replace `/config/custom_components/jacuzzi_spa/` with a newer copy from this repo, then restart Home Assistant.

## Troubleshooting

- **Cannot connect during setup** — Confirm the bridge IP/port from a machine on the same LAN. HA must be able to reach that IP (same network / no client isolation on Wi‑Fi).
- **Entities unavailable** — Check the Connection state sensor. The integration reconnects automatically if the bridge drops.
- **Temperature set seems slow** — Encrypted controllers step the setpoint with Temp Up/Down button presses; large changes can take several seconds.
- **Logs** — **Settings → System → Logs**, filter for `jacuzzi_spa`.

## Source

Integration code lives in this repository at:

```text
custom_components/jacuzzi_spa/
```

The spa protocol client is vendored under `custom_components/jacuzzi_spa/lib/` (based on `src/jacuzzi.py` / `src/balboa.py`).
