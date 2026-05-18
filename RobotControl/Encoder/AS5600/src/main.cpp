#include <Arduino.h>
#include <Wire.h>

#define I2C_SDA 21
#define I2C_SCL 22
#define AS5600_ADDR 0x36
#define AS5600_REG_ANGLE 0x0E

uint16_t raw_angle = 0;
float angle_degrees = 0.0;
int32_t rotation_count = 0;
uint16_t prev_angle = 0;
float SCREW_PITCH_MM = 5.0;

void readAS5600();
void printData();

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n=== AS5600 Test ===\n");
  
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);
  
  Wire.beginTransmission(AS5600_ADDR);
  if (Wire.endTransmission() == 0) {
    Serial.println("✓ AS5600 found\n");
  } else {
    Serial.println("ERROR: AS5600 not found\n");
  }
}

void loop() {
  readAS5600();
  printData();
  delay(50);
}

void readAS5600() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(AS5600_REG_ANGLE);
  Wire.endTransmission();
  
  Wire.requestFrom(AS5600_ADDR, 2);
  if (Wire.available() >= 2) {
    uint8_t msb = Wire.read();
    uint8_t lsb = Wire.read();
    raw_angle = ((msb << 8) | lsb) & 0x0FFF;
    angle_degrees = (raw_angle / 4096.0) * 360.0;
    
    if (raw_angle < 1000 && prev_angle > 3000) {
      rotation_count++;
    } else if (raw_angle > 3000 && prev_angle < 1000) {
      rotation_count--;
    }
    prev_angle = raw_angle;
  }
}

void printData() {
  Serial.print("Angle: ");
  Serial.print(angle_degrees, 1);
  Serial.print("°  |  Rotations: ");
  Serial.print(rotation_count);
  Serial.print("  |  Z: ");
  float z = (rotation_count * SCREW_PITCH_MM) + ((raw_angle / 4096.0) * SCREW_PITCH_MM);
  Serial.print(z, 2);
  Serial.println("mm");
}