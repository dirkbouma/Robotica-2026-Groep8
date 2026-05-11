#include <Arduino.h>
#include <Dynamixel2Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

// --- Hardware ---
#define DXL_TX_PIN   17
#define DXL_RX_PIN   16
#define TX_ENABLE_PIN 32  
#define RX_ENABLE_PIN 33  
#define DXL_DIR_PIN  RX_ENABLE_PIN
HardwareSerial DxlSerial(2);
Dynamixel2Arduino dxl(DxlSerial, DXL_DIR_PIN);

// --- ESP-NOW ---
typedef struct struct_message {
  int x;
  int y;
  float maxSpeed;
} struct_message;

struct_message inkomendeData;
unsigned long laatsteBerichtTijd = 0;
float virtueleDoelPositie = 512.0; // Float voor super-vloeiende kleine stapjes

// --- Limieten ---
const uint8_t DXL_ID = 5;
const int SERVO_MIN = 100;
const int SERVO_MAX = 900;

void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  memcpy(&inkomendeData, incomingData, sizeof(inkomendeData));
  laatsteBerichtTijd = millis();
}

void IRAM_ATTR flipDirectionPin() {
  digitalWrite(TX_ENABLE_PIN, !digitalRead(RX_ENABLE_PIN));
}

void setup() {
  Serial.begin(115200);
  pinMode(TX_ENABLE_PIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(RX_ENABLE_PIN), flipDirectionPin, CHANGE);
  
  DxlSerial.begin(1000000, SERIAL_8N1, DXL_RX_PIN, DXL_TX_PIN);
  dxl.begin(1000000);
  dxl.setPortProtocolVersion(1.0);
  dxl.setOperatingMode(DXL_ID, OP_POSITION);
  dxl.torqueOn(DXL_ID);

  WiFi.mode(WIFI_STA);
  esp_now_init();
  esp_now_register_recv_cb(OnDataRecv);
  
  // Begin op huidige fysieke positie om schokken te voorkomen
  virtueleDoelPositie = dxl.getPresentPosition(DXL_ID);
}

void loop() {
  if (millis() - laatsteBerichtTijd < 1000) {
    // SNELHEIDS LOGICA:
    // inkomendeData.x is -100 tot 100.
    // We delen door 100.0 om een factor (-1.0 tot 1.0) te krijgen.
    // Vermenigvuldig met maxSpeed voor de stapgrootte per loop.
    
    float stap = (float)inkomendeData.x / 100.0 * inkomendeData.maxSpeed;
    
    // Update de positie
    virtueleDoelPositie += stap;
    
    // Blijf binnen de hardware limieten
    virtueleDoelPositie = constrain(virtueleDoelPositie, SERVO_MIN, SERVO_MAX);
    
    // Stuur naar de servo
    dxl.setGoalPosition(DXL_ID, (int)virtueleDoelPositie);
  }
  
  delay(10); // 100Hz verversing voor zeer soepele beweging
}