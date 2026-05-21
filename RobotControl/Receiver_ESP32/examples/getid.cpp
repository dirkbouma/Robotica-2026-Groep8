#include <Arduino.h>
#include <Dynamixel2Arduino.h>
#include "ESP32SerialPortHandler.cpp"

// --- ESP32 HARDWARE PINNEN ---
#define DXL_TX_PIN   17
#define DXL_RX_PIN   16
#define DXL_DIR_PIN  15  // 1 dir pin voor beide richtingen

// --- DYNAMIXEL INSTELLINGEN ---
const float DXL_PROTOCOL_VERSION = 1.0; 
const uint32_t BAUDRATE = 1000000;      

Dynamixel2Arduino dxl;
ESP32SerialPortHandler esp_dxl_port(Serial2, DXL_RX_PIN, DXL_TX_PIN, DXL_DIR_PIN);

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n=================================================");
  Serial.println("   Dynamixel ID Scanner");
  Serial.println("=================================================");
  Serial.println("Zorg dat de 12V voeding AAN staat.");
  Serial.println("Sluit slechts 1 servo tegelijk aan op de datalijn.\n");

  dxl.setPort(esp_dxl_port);
  dxl.begin(BAUDRATE);
  dxl.setPortProtocolVersion(DXL_PROTOCOL_VERSION);
  
  Serial.println("Start scannen van ID 0 t/m 252...\n");

  int gevondenCount = 0;

  for (int testId = 0; testId < 253; testId++) {
    if (dxl.ping(testId)) {
      Serial.print("✅ BINGO! Servo gevonden met ID: ");
      Serial.println(testId);
      gevondenCount++;
      
      dxl.ledOn(testId);
      delay(500);
      dxl.ledOff(testId);
    }
  }

  Serial.println("\n-------------------------------------------------");
  if (gevondenCount == 0) {
    Serial.println("❌ Geen enkele servo gevonden.");
    Serial.println("Checklist:");
    Serial.println("- Heeft de servo 12V stroom?");
    Serial.println("- Zijn TX/RX niet per ongeluk omgedraaid?");
  } else {
    Serial.print(gevondenCount);
    Serial.println(" servo(s) gevonden!");
  }
}

void loop() {}
