# ESP32 Programmable Timer Web Server

This project lets you configure a programmable timer using an ESP32 and a web interface. You can set up to 10 schedules to automatically control a relay, toggle between Auto/ON/OFF modes, and reset all schedules remotely.

---

## Features

- Web UI hosted on ESP32 to control relay timer
- 10 customizable On/Off schedules
- Auto, ON, and OFF modes
- Real-time system clock using millis()
- Reset all schedules with a button
- No external RTC module required

---

## Hardware Components & Connections

| Component      | ESP32 Pin   | Description          |
|----------------|-------------|----------------------|
| Relay IN       | GPIO 5      | Relay control pin    |
| Relay VCC      | VIN (5V)    | Power supply         |
| Relay GND      | GND         | Ground               |

> *Important*: Ensure your relay module is compatible with 3.3V logic or use a level shifter if needed.

---

## Web Interface Preview

Here's how the webpage looks when you access the ESP32 IP in your browser:

### Web Page Features:
- *Current Time* (HH:MM from ESP32 millis())
- *Relay State* (ON/OFF display)
- *10 Schedule Slots*: Select and set On/Off times
- *Modes*:
  - Auto: Relay switches based on time
  - ON: Relay always on
  - OFF: Relay always off
- *Reset All*: Clear all saved times

---

## Getting Started

1. *Install Libraries*:
   - [ESPAsyncWebServer](https://github.com/me-no-dev/ESPAsyncWebServer)
   - [AsyncTCP](https://github.com/me-no-dev/AsyncTCP)

2. *WiFi Setup*:  
   Open the Arduino sketch and edit:
   ```cpp
   const char* ssid = "your_SSID";
   const char* password = "your_PASSWORD";