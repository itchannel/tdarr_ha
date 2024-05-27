DOMAIN = "tdarr"
SERVERIP = "serverip"
MANUFACTURER = "Tdarr"
SERVERPORT = "serverport"
UPDATE_INTERVAL = "update_interval"
UPDATE_INTERVAL_DEFAULT = 60
COORDINATOR = "coordinator"

SENSORS = {
    "server": {"icon": "mdi:server", "type": "single", "entry": "server"},
    "stats_spacesaved": {"icon": "mdi:harddisk","type": "single", "entry": "stats", "unit_of_measurement": "GB", "device_class": "data_size"},
    "stats_transcodefilesremaining": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats"},
    "stats_transcodedcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats"},
    "stats_stagedcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "staged"},
    "stats_healthcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats"},
    "stats_transcodeerrorcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats"},
    "stats_healtherrorcount": {"icon": "mdi:medication-outline", "unit_of_measurement": "Files", "type": "single", "entry": "stats"},
    "node": {"icon": "mdi:server-network-outline"},
    "nodefps": {"icon": "mdi:video", "unit_of_measurement": "FPS"},
    "stats_totalfps": {"icon": "mdi:video", "unit_of_measurement": "FPS", "type": "single", "entry": "nodes"},
    "library": {"icon": "mdi:folder-multiple", "unit_of_measurement": "Files"},
}

SWITCHES = {
    "pauseAll": {"icon": "mdi:pause-circle", "name": "pauseAll", "data": "globalsettings"},
    "ignoreSchedules": {"icon": "mdi:calendar-remove", "name": "ignoreSchedules", "data": "globalsettings"},
}