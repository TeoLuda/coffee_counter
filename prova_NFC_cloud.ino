#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_PN532.h>
#include <ArduinoJson.h>

// WIFI
const char* ssid = "IPP_Guests";
const char* password = "";

// SERVER URL
const char* serverUrl = "https://coffee-counter-292q.onrender.com/coffee";

// PN532 I2C
#define SDA_PIN 21
#define SCL_PIN 22

Adafruit_PN532 nfc(-1, -1);

void setup() {

  Serial.begin(115200);

  // I2C
  Wire.begin(SDA_PIN, SCL_PIN);

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

  Serial.println("Ready for NFC scan");
}

void loop() {

  uint8_t success;
  uint8_t uid[] = {0,0,0,0,0,0,0};
  uint8_t uidLength;

  success = nfc.readPassiveTargetID(
    PN532_MIFARE_ISO14443A,
    uid,
    &uidLength
  );

  if (success) {

    // Build UID string
    String uidString = "";

    for (uint8_t i = 0; i < uidLength; i++) {

      if (uid[i] < 0x10) {
        uidString += "0";
      }

      uidString += String(uid[i], HEX);
    }

    uidString.toUpperCase();

    Serial.print("UID detected: ");
    Serial.println(uidString);

    // Send HTTP POST
    if (WiFi.status() == WL_CONNECTED) {

      HTTPClient http;

      http.begin(serverUrl);

      http.addHeader("Content-Type", "application/json");

      // JSON payload
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

        // Parse JSON
        DynamicJsonDocument doc(1024);

        deserializeJson(doc, response);

        String status = doc["status"];

        if (status == "ok") {

          String name = doc["name"];
          int count = doc["coffee_count"];

          Serial.println("USER FOUND");
          Serial.println(name);
          Serial.println(count);
        }

        else if (status == "new_user") {

          Serial.println("NEW USER CREATED");
        }
      }

      else {

        Serial.print("HTTP Error: ");
        Serial.println(httpResponseCode);
      }

      http.end();
    }

    delay(3000);
  }
}