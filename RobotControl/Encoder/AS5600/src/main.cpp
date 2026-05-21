#include <Arduino.h>
#include <Wire.h>

// --- ESP32 DYNAMIXEL PINNEN ---
#define DXL_TX_PIN   17
#define DXL_RX_PIN   16
#define DXL_DIR_PIN  15  // Verbonden met Pin 1 en 19 van de 74LS241

// --- ESP32 I2C PINNEN (AS5600) ---
#define I2C_SDA      21
#define I2C_SCL      22
#define AS5600_ADDR  0x36
#define AS5600_REG_ANGLE 0x0E

// --- DYNAMIXEL INSTELLINGEN ---
const uint8_t DXL_ID = 5; 
const uint32_t DXL_BAUDRATE = 1000000;

// --- ENCODER VARIABELEN ---
uint16_t raw_angle = 0;
float angle_degrees = 0.0;
int32_t rotation_count = 0;
uint16_t prev_angle = 0;
float SCREW_PITCH_MM = 5.0;

// --- FUNCTIE DEKLARATIES ---
void setWheelMode(uint8_t id);
void setSpeed(uint8_t id, int16_t speed);
void stuurPakket(uint8_t* pakket, uint8_t lengte);
void readAS5600();
void printData();

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== Gecombineerde Dynamixel + AS5600 Systeem ===");
  Serial.println("Typ '+' voor omhoog (CW), '-' voor omlaag (CCW), 's' voor STOP\n");

  // --- 1. SETUP DYNAMIXEL ---
  pinMode(DXL_DIR_PIN, OUTPUT);
  digitalWrite(DXL_DIR_PIN, LOW); // Ruststand: Luisteren
  Serial2.begin(DXL_BAUDRATE, SERIAL_8N1, DXL_RX_PIN, DXL_TX_PIN);
  delay(100);

  Serial.println("Dynamixel instellen op Wheel Mode...");
  setWheelMode(DXL_ID);
  delay(100);

  // --- 2. SETUP I2C (AS5600) ---
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);
  
  Wire.beginTransmission(AS5600_ADDR);
  if (Wire.endTransmission() == 0) {
    Serial.println("✓ AS5600 encoder gevonden!\n");
  } else {
    Serial.println("ERROR: AS5600 encoder NIET gevonden!\n");
  }

  // Eerste meting doen om de startpositie te bepalen
  readAS5600();
  prev_angle = raw_angle;
}

void loop() {
  // 1. Controleer Serial Monitor voor besturing van de AX-12A
  if (Serial.available() > 0) {
    char commando = Serial.read();

    if (commando == '+') {
      Serial.println("\n>>> Commando ontvangen: Omhoog / CW");
      setSpeed(DXL_ID, 400); 
    } 
    else if (commando == '-') {
      Serial.println("\n>>> Commando ontvangen: Omlaag / CCW");
      setSpeed(DXL_ID, 400 + 1024); 
    } 
    else if (commando == 's' || commando == 'S') {
      Serial.println("\n>>> Commando ontvangen: STOP");
      setSpeed(DXL_ID, 0); 
    }
  }

  // 2. Lees constant de beweging uit via de encoder
  readAS5600();

  // 3. Print de actuele positie naar de monitor
  printData();

  delay(50); // 20 metingen per seconde
}

// =========================================================================
// AS5600 ENCODER FUNCTIES
// =========================================================================
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
    
    // Omwentelingen tellen (rekening houdend met de sprong 0 <-> 4095)
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
  Serial.println(" mm");
}

// =========================================================================
// INTERNE FUNCTIES VOOR DYNAMIXEL PROTOCOL 1.0
// =========================================================================
void setWheelMode(uint8_t id) {
  uint8_t pakket[11] = { 0xFF, 0xFF, id, 7, 0x03, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00 };
  uint32_t checksum = 0;
  for(int i = 2; i < 10; i++) checksum += pakket[i];
  pakket[10] = ~(checksum) & 0xFF;
  stuurPakket(pakket, 11);
}

void setSpeed(uint8_t id, int16_t speed) {
  uint8_t speedL = speed & 0xFF;
  uint8_t speedH = (speed >> 8) & 0xFF;
  uint8_t pakket[9] = { 0xFF, 0xFF, id, 5, 0x03, 0x20, speedL, speedH, 0x00 };
  uint32_t checksum = 0;
  for(int i = 2; i < 8; i++) checksum += pakket[i];
  pakket[8] = ~(checksum) & 0xFF;
  stuurPakket(pakket, 9);
}

void stuurPakket(uint8_t* pakket, uint8_t lengte) {
  digitalWrite(DXL_DIR_PIN, HIGH);  // HIGH = Zenden via 74LS241
  Serial2.write(pakket, lengte);    
  Serial2.flush();                  
  digitalWrite(DXL_DIR_PIN, LOW);   // LOW = Ontvangen / Vrijgeven
}