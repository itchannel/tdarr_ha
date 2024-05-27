## **Changelog**
### Version 1.17
- Added disable schedules toggle
- Add icons for certain switches
### Version 1.16
- Added Health and Transcode failed sensors
- Added icons
- Added support for long term statistics
- Refactored some code
### Version 1.15
- Fix staged count not showing
### Version 1.14
- Added more debugging
- Added handling for null sensor values
### Version 1.13
- Added Total FPS sensor
- Add Staged files sensor
- Add Health count sensor
### Version 1.12
- Add translations for services.yaml
### Version 1.11
- Fix versioning
### Version 1.10
- Added Pause All switch
### Version 1.09
- Fix node naming in latest Tdarr version (Now uses NodeName, this will create a new sensor for each node as it uses a unique ID for entity ID but uses the original name for the sensor, preventing duplicate names)
### Version 1.08
- Fix error when loading with 0 nodes active
- Fix version error on initial load
- Add auto reload when new nodes are added to tdarr
### Version 1.07
- Add refresh library service
### Version 1.06
- Fix options unloading
### Version 1.05
- Auto reload on options change
### Version 1.04
- Add library support (Show details for individual libraries)
### Version 1.03
- Improved error handling
### Version 1.02
- Add unit_of_measurement to sensors
- Add 3 general statistic sensors
### Version 1.01
- Fix update bug
- Add option to set poll interval
### Version 1.00
- Initial commit