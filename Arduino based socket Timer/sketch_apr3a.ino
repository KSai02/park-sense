#include <WiFi.h>
#include <ESPAsyncWebServer.h>

#define RELAY_PIN 5

const char* ssid = "realme gt2 d";
const char* password = "90149341";

AsyncWebServer server(80);

// Timer configuration (defaults)
int onHour = 6, onMinute = 0;
int offHour = 18, offMinute = 0;
bool relayState = false;
int mode = 0; // 0 = Auto, 1 = ON, 2 = OFF

struct Schedule {
  int onHour;
  int onMinute;
  int offHour;
  int offMinute;
};

Schedule schedules[10];

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ESP32 Programmable Timer</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      text-align: center;
      background-color: #f4f4f4;
    }
    h1 {
      margin-top: 20px;
      color: #333;
    }
    .time-block, .controls, .status {
      margin: 20px auto;
      padding: 15px;
      width: 300px;
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    label {
      display: block;
      margin: 10px 0 5px;
      font-weight: bold;
    }
    select, button, input[type="time"] {
      width: 100%;
      padding: 8px;
      margin-bottom: 10px;
      border-radius: 5px;
      border: 1px solid #ccc;
    }
    .relay-on {
      color: green;
      font-weight: bold;
    }
    .relay-off {
      color: red;
      font-weight: bold;
    }
  </style>
</head>
<body>

<h1>ESP32 Timer Control</h1>

<div class="status">
  <p>Current Time: <span id="currentTime">--:--</span></p>
  <p>Relay: <span id="relayState" class="relay-off">OFF</span></p>
</div>

<div class="time-block">
  <label for="schedule">Schedule Slot</label>
  <select id="schedule">
    <option value="0">Schedule 1</option>
    <option value="1">Schedule 2</option>
    <option value="2">Schedule 3</option>
    <option value="3">Schedule 4</option>
    <option value="4">Schedule 5</option>
    <option value="5">Schedule 6</option>
    <option value="6">Schedule 7</option>
    <option value="7">Schedule 8</option>
    <option value="8">Schedule 9</option>
    <option value="9">Schedule 10</option>
  </select>

  <label for="onTime">On Time</label>
  <input type="time" id="onTime">

  <label for="offTime">Off Time</label>
  <input type="time" id="offTime">
</div>

<div class="controls">
  <label for="modeSelect">Mode</label>
  <select id="modeSelect" onchange="setMode()">
    <option value="0">Auto</option>
    <option value="1">ON</option>
    <option value="2">OFF</option>
  </select>

  <button onclick="sendUpdate()">Update Schedule</button>
  <button onclick="resetAll()">Reset All</button>
</div>

<script>
  function fetchStatus() {
    fetch('/status')
      .then(response => response.json())
      .then(data => {
        document.getElementById('currentTime').textContent = data.currentTime;
        document.getElementById('relayState').textContent = data.relayState ? "ON" : "OFF";
        document.getElementById('relayState').className = data.relayState ? "relay-on" : "relay-off";
        document.getElementById('onTime').value = pad(data.onHour) + ':' + pad(data.onMinute);
        document.getElementById('offTime').value = pad(data.offHour) + ':' + pad(data.offMinute);
        document.getElementById('modeSelect').value = data.mode;
      });
  }

  function pad(num) {
    return num.toString().padStart(2, '0');
  }

  function sendUpdate() {
    const [onHour, onMinute] = document.getElementById('onTime').value.split(':');
    const [offHour, offMinute] = document.getElementById('offTime').value.split(':');
    const schedule = document.getElementById('schedule').value;

    const params = new URLSearchParams();
    params.append("onHour", onHour);
    params.append("onMinute", onMinute);
    params.append("offHour", offHour);
    params.append("offMinute", offMinute);
    params.append("schedule", schedule);

    fetch('/set-time', {
      method: 'POST',
      body: params
    }).then(() => {
      alert("Timer Updated!");
      fetchStatus();
    });
  }

  function setMode() {
    const mode = document.getElementById('modeSelect').value;
    const params = new URLSearchParams();
    params.append("mode", mode);
    fetch('/set-mode', {
      method: 'POST',
      body: params
    }).then(() => {
      alert("Mode updated!");
      fetchStatus();
    });
  }

  function resetAll() {
    fetch('/reset', {
      method: 'POST'
    }).then(() => {
      alert("All schedules reset.");
      fetchStatus();
    });
  }

  setInterval(fetchStatus, 5000);
  window.onload = fetchStatus;
</script>

</body>
</html>
)rawliteral";


void updateRelayState() {
  time_t now = millis() / 1000;
  int hours = (now / 3600) % 24;
  int minutes = (now / 60) % 60;
  int currentMinutes = hours * 60 + minutes;

  bool active = false;

  if (mode == 0) {
    for (int i = 0; i < 10; i++) {
      int start = schedules[i].onHour * 60 + schedules[i].onMinute;
      int end = schedules[i].offHour * 60 + schedules[i].offMinute;
      if (currentMinutes >= start && currentMinutes < end) {
        active = true;
        break;
      }
    }
    relayState = active;
  } else if (mode == 1) {
    relayState = true;
  } else {
    relayState = false;
  }

  digitalWrite(RELAY_PIN, relayState);
} 


void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected. IP: " + WiFi.localIP().toString());

  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send_P(200, "text/html", index_html);
  });

  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
    time_t now = millis() / 1000;
    int hours = (now / 3600) % 24;
    int minutes = (now / 60) % 60;

    String json = "{";
    json += "\"currentTime\":\"" + String(hours) + ":" + (minutes < 10 ? "0" : "") + String(minutes) + "\",";
    json += "\"onHour\":" + String(onHour) + ",";
    json += "\"onMinute\":" + String(onMinute) + ",";
    json += "\"offHour\":" + String(offHour) + ",";
    json += "\"offMinute\":" + String(offMinute) + ",";
    json += "\"relayState\":" + String(relayState ? "true" : "false") + ",";
    json += "\"mode\":" + String(mode);
    json += "}";

    request->send(200, "application/json", json);
  });

  server.on("/set-time", HTTP_POST, [](AsyncWebServerRequest *request) {
    if (request->hasParam("onHour", true) && request->hasParam("onMinute", true) &&
        request->hasParam("offHour", true) && request->hasParam("offMinute", true)) {
      onHour = request->getParam("onHour", true)->value().toInt();
      onMinute = request->getParam("onMinute", true)->value().toInt();
      offHour = request->getParam("offHour", true)->value().toInt();
      offMinute = request->getParam("offMinute", true)->value().toInt();
      request->send(200, "text/plain", "Timer updated");
    } else {
      request->send(400, "text/plain", "Missing parameters");
    }
  });

  server.on("/set-mode", HTTP_POST, [](AsyncWebServerRequest *request) {
    if (request->hasParam("mode", true)) {
      mode = request->getParam("mode", true)->value().toInt();
      request->send(200, "text/plain", "Mode updated");
    } else {
      request->send(400, "text/plain", "Missing mode parameter");
    }
  });

  server.on("/reset", HTTP_POST, [](AsyncWebServerRequest *request) {
    onHour = 0; onMinute = 0;
    offHour = 0; offMinute = 0;
    mode = 0;
    request->send(200, "text/plain", "Schedule reset");
  });

  server.begin();
}

void loop() {
  updateRelayState();
  delay(1000);
}
