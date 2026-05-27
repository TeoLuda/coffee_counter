#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>

TwoWire OLED_I2C = TwoWire(0);
TwoWire NFC_I2C = TwoWire(1);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32


#include <Adafruit_PN532.h>
#include <ArduinoJson.h>
#include <WiFiClientSecure.h>

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &OLED_I2C,
  -1
);

// WIFI
const char* ssid = "IPP_Guests";
const char* password = "";

// SERVER URL
const char* serverUrl = "https://coffee-counter-292q.onrender.com/coffee";

// PN532 I2C
#define SDA_PIN 21
#define SCL_PIN 22

Adafruit_PN532 nfc(-1, -1, &NFC_I2C);

String lastUID = "";
unsigned long lastScanTime = 0;

const unsigned long scanCooldown = 10000; // 10 seconds

void setup() {

  Serial.begin(115200);

  // I2C
  NFC_I2C.begin(21, 22);
  OLED_I2C.begin(18, 19);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {

    Serial.println("OLED not found");

    while(1);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0,0);
  display.println("Coffee Counter");
  display.println("Booting...");

  display.display();

  // NFC init
  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();

  if (!versiondata) {
    Serial.println("PN532 not found");
    while (1);
  }

  nfc.SAMConfig();

  Serial.println("PN532 ready");

  // WIFI
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.println(WiFi.localIP());

  display.clearDisplay();

  display.setCursor(0,0);
  display.println("WiFi connected");
  display.println(WiFi.localIP());

  display.display();

  delay(2000);

  display.clearDisplay();

  display.setCursor(0,0);
  display.println("Ready for");
  display.println("NFC scan");

  display.display();

  Serial.println("Ready for NFC scan");
}

void loop() {

  uint8_t success;
  uint8_t uid[] = {0,0,0,0,0,0,0};
  uint8_t uidLength;

  // Try reading NFC card
  success = nfc.readPassiveTargetID(
    PN532_MIFARE_ISO14443A,
    uid,
    &uidLength,
    100  // timeout in ms
  );

  // No card detected
  if (!success) {
    delay(50);
    return;
  }

  // Build UID string
  String uidString = "";

  for (uint8_t i = 0; i < uidLength; i++) {

    if (uid[i] < 0x10) {
      uidString += "0";
    }

    uidString += String(uid[i], HEX);
  }

  uidString.toUpperCase();

  unsigned long currentTime = millis();

  // Ignore duplicate scan within cooldown
  if (uidString == lastUID &&
      currentTime - lastScanTime < scanCooldown) {

    Serial.println("Duplicate scan ignored");

    delay(200);

    return;
  }


  Serial.println();
  Serial.println("======================");
  Serial.print("UID detected: ");
  Serial.println(uidString);

  display.clearDisplay();

  display.setCursor(0,0);
  display.println("Card detected");
  display.println(uidString);

  display.display();
  delay(2000);

  // Check WiFi
  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("WiFi disconnected");
    Serial.println("Reconnecting...");

    WiFi.begin(ssid, password);

    int retries = 0;

    while (WiFi.status() != WL_CONNECTED && retries < 20) {
      delay(500);
      Serial.print(".");
      retries++;
    }

    Serial.println();

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi reconnect failed");
      return;
    }

    Serial.println("WiFi reconnected");
  }

  // HTTPS client
  WiFiClientSecure client;

  client.setInsecure();

  client.setTimeout(15000);

  HTTPClient http;

  http.setTimeout(15000);

  http.useHTTP10(true);

  Serial.println("Connecting to server...");

  display.clearDisplay();

  display.setCursor(0,0);
  display.println("Connecting...");
  display.println("Please wait");

  display.display();

  if (!http.begin(client, serverUrl)) {

    Serial.println("HTTP begin failed");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Connection", "close");

  String jsonPayload = "{\"uid\":\"" + uidString + "\"}";

  Serial.println("Sending POST...");
  Serial.println(jsonPayload);

  int httpResponseCode = http.POST(jsonPayload);

  Serial.print("HTTP Response code: ");
  Serial.println(httpResponseCode);

  if (httpResponseCode > 0) {

    String response = http.getString();

    Serial.println("Server response:");
    Serial.println(response);

    DynamicJsonDocument doc(1024);

    DeserializationError error = deserializeJson(doc, response);

    if (error) {

      Serial.println("JSON parse failed");

    } else {

      String status = doc["status"];

      if (status == "ok") {

        String name = doc["name"];
        int count = doc["coffee_count"];

        Serial.println();
        Serial.println("USER FOUND");
        Serial.print("Name: ");
        Serial.println(name);

        Serial.print("Coffee count: ");
        Serial.println(count);

        display.clearDisplay();

        display.setTextSize(2);

        display.setCursor(0,0);
        display.println(name);

        display.setTextSize(1);

        display.print("Coffees: ");
        display.println(count);

        display.display();

      }

      else if (status == "new_user") {

        display.clearDisplay();

        display.setCursor(0,0);
        display.println("Unknown user");
        display.println("Registered");

        display.display();

        Serial.println();
        Serial.println("NEW USER CREATED");
      }
    }

  } else {

    Serial.print("HTTP Error: ");
    Serial.println(httpResponseCode);

    display.clearDisplay();

    display.setCursor(0,0);
    display.println("HTTP Error");
    display.println(httpResponseCode);

    display.display();
  }

  http.end();

  client.stop();

  lastUID = uidString;
  lastScanTime = millis();

  Serial.println("Remove NFC tag...");

  // WAIT UNTIL CARD REMOVED
  while (nfc.readPassiveTargetID(
      PN532_MIFARE_ISO14443A,
      uid,
      &uidLength,
      100
    )) {

    delay(100);
  }

  Serial.println("Ready for next scan");
  Serial.println("======================");

  delay(5000);

  display.clearDisplay();

  display.setCursor(0,0);
  display.println("Ready for");
  display.println("NFC scan");

  display.display();
}