DOMAIN = "tdarr"
SERVERIP = "serverip"
MANUFACTURER = "Tdarr"
SERVERPORT = "serverport"
UPDATE_INTERVAL = "update_interval"
UPDATE_INTERVAL_DEFAULT = 60
LIBRARY_SCAN_INTERVAL = "library_scan_interval"
LIBRARY_SCAN_INTERVAL_DEFAULT = 600
COORDINATOR = "coordinator"
APIKEY = "apikey"
VERIFY_SSL = "verify_ssl"

SENSORS = {
    "server": {"icon": "mdi:server", "type": "single", "entry": "server"},
    "stats_spacesaved": {"icon": "mdi:harddisk", "type": "single", "entry": "stats", "unit_of_measurement": "GB", "device_class": "data_size", "state_class": "measurement"},
    "stats_transcodefilesremaining": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats", "state_class": "measurement"},
    "stats_transcodedcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats", "state_class": "measurement"},
    "stats_stagedcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "staged", "state_class": "measurement"},
    "stats_healthcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats", "state_class": "measurement"},
    "stats_transcodeerrorcount": {"icon": "mdi:file-multiple", "unit_of_measurement": "Files", "type": "single", "entry": "stats", "state_class": "measurement"},
    "stats_healtherrorcount": {"icon": "mdi:medication-outline", "unit_of_measurement": "Files", "type": "single", "entry": "stats", "state_class": "measurement"},
    "node": {"icon": "mdi:server-network-outline"},
    "nodefps": {"icon": "mdi:video", "unit_of_measurement": "FPS", "state_class": "measurement"},
    "stats_totalfps": {"icon": "mdi:video", "unit_of_measurement": "FPS", "type": "single", "entry": "nodes", "state_class": "measurement"},
    "library": {"icon": "mdi:folder-multiple", "unit_of_measurement": "Files", "state_class": "measurement"},
}

SWITCHES = {
    "pauseAll": {"icon": "mdi:pause-circle", "name": "pauseAll", "data": "globalsettings"},
    "ignoreSchedules": {"icon": "mdi:calendar-remove", "name": "ignoreSchedules", "data": "globalsettings"},
}
