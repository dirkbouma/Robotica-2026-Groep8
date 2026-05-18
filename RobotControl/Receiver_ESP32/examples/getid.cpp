#include <Arduino.h>
#include <Dynamixel2Arduino.h>

// --- ESP32 HARDWARE PINNEN ---
#define DXL_TX_PIN   17
#define DXL_RX_PIN   16

// --- 74HC125 PINNEN ---
#define TX_ENABLE_PIN 4  // Active-Low (Zend-poort, pin 1 op de chip)
#define RX_ENABLE_PIN 5  // Active-Low (Ontvang-poort, pin 4 op de chip)

// We geven de RX pin aan de library voor de automatische timing
#define DXL_DIR_PIN  RX_ENABLE_PIN

// --- DYNAMIXEL INSTELLINGEN ---
const float DXL_PROTOCOL_VERSION = 1.0; 
const uint32_t BAUDRATE = 1000000;      

HardwareSerial DxlSerial(2);
Dynamixel2Arduino dxl(DxlSerial, DXL_DIR_PIN);


// =========================================================================
// DE SOFTWARE INVERTER (Hardware Interrupt)
// Zorgt dat zenden en ontvangen nooit tegelijk gebeurt op de 74HC125.
// =========================================================================
void IRAM_ATTR flipDirectionPin() {
  digitalWrite(TX_ENABLE_PIN, !digitalRead(RX_ENABLE_PIN));
}
// =========================================================================


void setup() {
  Serial.begin(115200);
  delay(2000); // Geef de Serial Monitor even tijd om op te starten
  
  Serial.println("\n=================================================");
  Serial.println("   Dynamixel ID Scanner (74HC125 Editie)");
  Serial.println("=================================================");
  Serial.println("Zorg dat de 12V voeding AAN staat.");
  Serial.println("Sluit slechts 1 servo tegelijk aan op de datalijn.\n");

  // 1. Stel pin 4 in als output en zet veilig uit
  pinMode(TX_ENABLE_PIN, OUTPUT);
  digitalWrite(TX_ENABLE_PIN, HIGH); 
  
  // 2. Koppel de interrupt hack aan pin 5
  attachInterrupt(digitalPinToInterrupt(RX_ENABLE_PIN), flipDirectionPin, CHANGE);

  // 3. Start communicatie
  DxlSerial.begin(BAUDRATE, SERIAL_8N1, DXL_RX_PIN, DXL_TX_PIN);
  dxl.begin(BAUDRATE);
  dxl.setPortProtocolVersion(DXL_PROTOCOL_VERSION);
  
  Serial.println("Start scannen van ID 0 t/m 252...\n");

  int gevondenCount = 0;

  // 4. De For-loop die alle ID's langsgaat
  for (int testId = 0; testId < 253; testId++) {
    
    // dxl.ping() stuurt een bericht en wacht op antwoord.
    // Dankzij de interrupt hack werkt dit nu razendsnel!
    if (dxl.ping(testId)) {
      Serial.print("✅ BINGO! Servo gevonden met ID: ");
      Serial.println(testId);
      gevondenCount++;
      
      // Laat het lampje op de servo knipperen ter bevestiging
      dxl.ledOn(testId);
      delay(500);
      dxl.ledOff(testId);
    }
  }

  // 5. Resultaat printen
  Serial.println("\n-------------------------------------------------");
  if (gevondenCount == 0) {
    Serial.println("❌ Geen enkele servo gevonden.");
    Serial.println("Checklist:");
    Serial.println("- Heeft de servo 12V stroom?");
    Serial.println("- Zijn TX/RX niet per ongeluk omgedraaid?");
    Serial.println("- Heb je een spanningsdeler op de RX pin gezet ter bescherming?");
  } else {
    Serial.println("Scannen succesvol voltooid!");
    Serial.println("Vul dit ID in bij je hoofdprogramma.");
  }
}

void loop() {
  // De scanner draait eenmalig in de setup(), dus de loop blijft leeg.
}