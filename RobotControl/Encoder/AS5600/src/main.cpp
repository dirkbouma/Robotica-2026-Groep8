#include <Arduino.h>
#include <Wire.h>

#define TCA_ADDR   0x70
#define AS5600_ADDR 0x36

// TCA9548A channel select
void selectChannel(uint8_t ch) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);   // enable bit for channel 0-7
  Wire.endTransmission();
}

// Disable all channels
void disableAllChannels() {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(0x00);
  Wire.endTransmission();
}

// Read 12-bit raw angle from AS5600 (registers 0x0C–0x0D)
int readRawAngle() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(0x0C);
  if (Wire.endTransmission(false) != 0) return -1;  // NACK = not present
  Wire.requestFrom(AS5600_ADDR, 2);
  if (Wire.available() < 2) return -1;
  uint16_t high = Wire.read();
  uint16_t low  = Wire.read();
  return ((high & 0x0F) << 8) | low;
}

// Read signal magnitude (0x1B–0x1C) — 0..4095, higher = stronger magnet
int readMagnitude() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(0x1B);
  if (Wire.endTransmission(false) != 0) return -1;
  Wire.requestFrom(AS5600_ADDR, 2);
  if (Wire.available() < 2) return -1;
  uint16_t high = Wire.read();
  uint16_t low  = Wire.read();
  return ((high & 0x0F) << 8) | low;
}

// Read AGC byte (0x1A) — lower = stronger magnet (ideal ~60–100 out of 255)
int readAGC() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(0x1A);
  if (Wire.endTransmission(false) != 0) return -1;
  Wire.requestFrom(AS5600_ADDR, 1);
  if (Wire.available() < 1) return -1;
  return Wire.read();
}

// Read status byte (0x0B) — bit 5 = MH (magnet high), bit 4 = ML (low), bit 3 = MD (detected)
String readStatus() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(0x0B);
  if (Wire.endTransmission(false) != 0) return "NO_RESPONSE";
  Wire.requestFrom(AS5600_ADDR, 1);
  if (!Wire.available()) return "NO_DATA";
  uint8_t s = Wire.read();
  String out = "";
  out += (s & 0x20) ? "MH " : "";   // magnet too strong
  out += (s & 0x10) ? "ML " : "";   // magnet too weak
  out += (s & 0x08) ? "MD"  : "NO_MAGNET";  // magnet detected
  return out;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);   // SDA=21, SCL=22 for ESP32 DevKit
  Wire.setClock(400000);
  delay(500);
  Serial.println("\n=== AS5600 Encoder Test ===\n");
}

void loop() {
  for (uint8_t ch = 0; ch < 3; ch++) {
    selectChannel(ch);
    delay(5);  // short settle time

    int angle = readRawAngle();
    int magnitude = readMagnitude();
    int agc = readAGC();
    String status = readStatus();
    float degrees = (angle >= 0) ? (angle / 4095.0f) * 360.0f : -1.0f;

    Serial.print("Ch");
    Serial.print(ch);
    Serial.print(" | ");

    if (angle < 0) {
      Serial.println("NOT FOUND — check wiring or channel");
    } else {
      Serial.print("Angle: ");
      Serial.print(angle);
      Serial.print(" raw (");
      Serial.print(degrees, 1);
      Serial.print(" deg) | Magnitude: ");
      Serial.print(magnitude);
      Serial.print(" | AGC: ");
      Serial.print(agc);
      Serial.print(" | Status: ");
      Serial.println(status);
    }
  }

  disableAllChannels();
  Serial.println("---");
  delay(500);
}