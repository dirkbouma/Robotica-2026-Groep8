#include <Arduino.h>
#include <Dynamixel2Arduino.h>

// --- ESP32 HARDWARE PINNEN ---
#define DXL_TX_PIN   17
#define DXL_RX_PIN   16

// --- 74HC125 PINNEN ---
#define TX_ENABLE_PIN 4  
#define RX_ENABLE_PIN 5  
#define DXL_DIR_PIN  RX_ENABLE_PIN

// --- DYNAMIXEL INSTELLINGEN ---
const uint8_t DXL_ID = 254;               // Zorg dat dit jouw correcte ID is!
const float DXL_PROTOCOL_VERSION = 1.0; 
const uint32_t BAUDRATE = 1000000;      

HardwareSerial DxlSerial(2);
Dynamixel2Arduino dxl(DxlSerial, DXL_DIR_PIN);

// --- TIMERS VOOR MULTITASKING ---
unsigned long vorigeBewegingTijd = 0;
const unsigned long BEWEEG_INTERVAL = 2000; // Wissel elke 2 seconden van richting

unsigned long vorigeLeesTijd = 0;
const unsigned long LEES_INTERVAL = 50;     // Lees elke 50 milliseconden (20x per seconde)

// --- POSITIE INSTELLINGEN ---
const int POSITIE_A = 300;
const int POSITIE_B = 700;
bool gaNaarB = true; // Houdt bij welke kant we op gaan

// =========================================================================
// DE SOFTWARE INVERTER (Hardware Interrupt)
// =========================================================================
void IRAM_ATTR flipDirectionPin() {
  digitalWrite(TX_ENABLE_PIN, !digitalRead(RX_ENABLE_PIN));
}
// =========================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Start Sweep & Uitlees Test ---");

  pinMode(TX_ENABLE_PIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(RX_ENABLE_PIN), flipDirectionPin, CHANGE);
  digitalWrite(TX_ENABLE_PIN, HIGH); 

  DxlSerial.begin(BAUDRATE, SERIAL_8N1, DXL_RX_PIN, DXL_TX_PIN);
  dxl.begin(BAUDRATE);
  dxl.setPortProtocolVersion(DXL_PROTOCOL_VERSION);
  
  // BELANGRIJK: Om te kunnen bewegen, moeten we Torque aanzetten!
  dxl.setOperatingMode(DXL_ID, OP_POSITION);
  dxl.torqueOn(DXL_ID);

  Serial.println("Klaar! Starten met bewegen en lezen...\n");
}

void loop() {
  unsigned long huidigeTijd = millis();

  // TAAK 1: Controleer of het tijd is om van richting te wisselen (elke 2000ms)
  if (huidigeTijd - vorigeBewegingTijd >= BEWEEG_INTERVAL) {
    vorigeBewegingTijd = huidigeTijd; // Reset de timer

    if (gaNaarB) {
      dxl.setGoalPosition(DXL_ID, POSITIE_B);
    } else {
      dxl.setGoalPosition(DXL_ID, POSITIE_A);
    }
    
    gaNaarB = !gaNaarB; // Draai de richting om voor de volgende keer
  }

  // TAAK 2: Controleer of het tijd is om de positie uit te lezen (elke 50ms)
  if (huidigeTijd - vorigeLeesTijd >= LEES_INTERVAL) {
    vorigeLeesTijd = huidigeTijd; // Reset de timer

    int positie = dxl.getPresentPosition(DXL_ID);

    // Omdat we heel snel printen, gebruiken we een nette opmaak:
    Serial.print("Doelpositie: ");
    Serial.print(gaNaarB ? POSITIE_A : POSITIE_B); // Print waar hij op dit moment naartoe probeert te gaan
    Serial.print(" | Actuele Positie: ");
    Serial.println(positie);
  }
}