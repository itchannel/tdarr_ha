# Tdarr Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/itchannel)

## Install
Use HACS and add as a custom repo. Once the integration is installed go to your integrations and follow the configuration options below:
- Tdarr Server IP
- Tdarr Port (Prefilled to Tdarr default port 8265)

## Currently Supported
- Server status
- Node information
- Node FPS
- Library information and Statistics
- Switches to pause/unpause a node

## Screenshots
![Paused Sensor](https://github.com/itchannel/screenshots/raw/main/tdarr_node_paused.jpg)

![Library Sensor](https://github.com/itchannel/screenshots/raw/main/tdarr_library_sensor.jpg)

## Additional Information

The integration will automatically add new nodes as they come online. Old nodes that are no longer used will need to be manually deleted from HA if no longer used.

All sensors display any available additional info in the sensor attributes section. This information can be used by you to create more verbose sensors using Home Assistant templates. 


This is a custom integration I have created to allow me to use HA to control my nodes such as pausing/unpausing transcoding depending on how much excess solar electricity I have. 