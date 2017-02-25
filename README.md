# fancontrol

Dew point ventilation controller software, written in Python.

See the project home page: http://danifold.net/fancontrol.html.

This package is not meant to be used out-of-the-box since it was coded for a unique hardware device. Nevertheless, the package is modular and flexible, hence could be useful as a basis for your own controller if you build a similar device to mine.

The heart of the controller is the message board. All information flow is directed through this module. All other components register here, subscribe to messages or directly query information from other components.

###### Message board
* [messageboard.py](blob/master/messageboard.py): Central message board, can be considered stable.

###### Main module
* [control.py](blob/master/control.py): This is the entry point to the controller. Call this script to start the software. All components are started and stopped from here. Add or remove components according to your own setup.

###### Components
* [component.py](blob/master/component.py): Contains the base class for all components. Components react to messages and may either run in the main thread (for non-blocking operations) or have their own worker thread for more computationally intensive tasks.
* [average.py](blob/master/average.py): Small component to compute the average of the last measurements over a given period.
* [dcf77_thread.py](blob/master/dcf77_thread.py): Component for receiving a DCF77 radio clock signal. Optional.
* [devices.py](blob/master/devices.py): Component to control the relays for the connected (mains voltage) devices. This needs to be adapted to the actual installation: e.g., one fan, two fans (push-pull configuration?), or one fan and a window motor as in the original setup.
* [display.py](blob/master/display.py): Component for text display on my small LCD screen. Should be adapted to your specific screen. A minimal version of the ventilation controller could also leave the display out.
* [fan.py](blob/master/fan.py): This component decides when the ventilation is switched on and off. Use the provided algorithm or adapt it to your own needs.
* [htmlwriter.py](blob/master/htmlwriter.py): Component to publish live data online. Optional. Needs to be adapted to your web server setup.
* [menu.py](blob/master/menu.py): Component for the onscreen menus and button controls. The “user interface“ is implemented here.
* [sensor.py](blob/master/sensor.py): Component for the measurements (the non hardware-specific part).
* [status.py](blob/master/status.py): This component receives information from all other components and generates status information for the built-in display and the web interface.

###### Hardware drivers
* [dcf77_reader.py](blob/master/dcf77_reader.py): Device driver for the external radio clock module. Implements the DCF77 protocol. Probably only small changes needed to adapt to different receiver hardware.
* [sht75.py](blob/master/sht75.py): Hardware-specific part of the sensor component: driver with the bus protocol and readout routines. Use this module for Sensirion sensors or replace for other types of sensors.

###### Configuration
* [fancontrol.cfg](blob/master/fancontrol.cfg): Part of the configuration is stored here. Note that some specifics are still hard-coded. If needed, the configuration feature could be made more extensive.

###### Helper modules
* [ip.py](blob/master/ip.py): Determine the computer's local and public IP addresses.
* [shutdown.py](blob/master/shutdown.py): Shut the computer down.
* [signals_handler.py](blob/master/signals_handler.py): Handler for Unix signals to allow graceful termination (e.g., close the window before the controller terminates).
* [uptime.py](blob/master/uptime.py): Determine the uptime of the computer. All time intervals in the controller software are measured by uptime diffences, except the logging timestamps. Uptime has the advantage that it is never adjusted, so the controller is not confused when the real-time clock (Unix time) is adjusted.
* [rwlock.py](blob/master/rwlock.py): Two different reader-writer locks, used by the message board.

###### Data
* [index.html](blob/master/index.html): HTML page for the web server. See http://fancontrol.selfhost.eu:8080/.
* [endscreen.bin](blob/master/endscreen.bin): End screen and splash screen for the controller. Change these to your own taste. The .bin files are raw bitmaps which are copied directly to the framebuffer device for the display.
* [endscreen.png](blob/master/endscreen.png)
* [startscreen.bin](blob/master/startscreen.bin)
* [startscreen.png](blob/master/startscreen.png)

###### External scripts
The following scripts are not used by [control.py](blob/master/control.py) and its submodules.
* [led.py](blob/master/led.py): Switch the status LED on. See http://danifold.net/fancontrol_setup.html.
* [startscreen.sh](blob/master/startscreen.sh): Turn the LED on and display the splash screen.
* [statistics.py](blob/master/statistics.py): This script generates data plots from the log files. I use it to create both live plots (every 5 minutes) and historical data plots (daily, for the previous day). See http://danifold.net/fancontrol_setup.html for instructions and http://fancontrol.selfhost.eu:8080/ for the result.
* [splash_screen_generator.py](blob/master/splash_screen_generator.py): The splash screen and end screen images were created by this script.
