# Tdarr Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/itchannel)

## Install
Use HACS and add as a custom repo. Once the integration is installed go to your integrations and follow the configuration options below:
- Tdarr Server IP or full URL (e.g. `192.168.1.10` or `https://tdarr.example.com` for a reverse proxy)
- Tdarr Port (Prefilled to Tdarr default port 8265, leave blank when using a URL without a port)
- Tdarr API Key (only needed if authentication is enabled on the server)

Requires Home Assistant 2024.11 or newer.

## Currently Supported
- Server status
- Node information
- Node FPS
- Library information and Statistics
- Switches to pause/unpause a node
- Switches to pause all nodes and ignore schedules
- `tdarr.refresh_library` service to rescan a library
- `tdarr.cancel_workers_by_node_name` service to cancel all transcodes/workers on a node
- Re-authentication flow when the API key is changed/revoked
- Diagnostics download (API key redacted) for easier issue reports
- Long-term statistics on numeric sensors (FPS, file counts, space saved)
- HTTPS/reverse proxy support with optional SSL verification
- `current_files` attribute on node sensors showing what each node is processing (file, progress, ETA)
- Separate (slower) polling interval for library statistics as these queries are heavy on the Tdarr server

## Screenshots
![Paused Sensor](https://github.com/itchannel/screenshots/raw/main/tdarr_node_paused.jpg)

![Library Sensor](https://github.com/itchannel/screenshots/raw/main/tdarr_library_sensor.jpg)

## Additional Information

The integration will automatically add new nodes and libraries as they appear, without reloading the integration. Node sensors show "Offline" (and node pause switches become unavailable) when a node disconnects. Old nodes that are no longer used will need to be manually deleted from HA.

All sensors display any available additional info in the sensor attributes section. This information can be used by you to create more verbose sensors using Home Assistant templates. 


This is a custom integration I have created to allow me to use HA to control my nodes such as pausing/unpausing transcoding depending on how much excess solar electricity I have. 