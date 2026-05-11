#include <Arduino.h>
#include <SPI.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

// --- Pincofiguraties ---
const int JOY_POWER_PIN = 32;
const int JOY_X_PIN = 34; 
const int JOY_Y_PIN = 35; 

// --- Kleuren Thema ---
#define ST_DARK   0x0841 
#define ST_LIME   0xDEFB 
#define ST_MINT   0xDAFF 
#define ST_RED    0xF800 

// --- UI Toestanden ---
enum Scherm { AUTO, MANUAL, DEBUG };
Scherm huidigScherm = MANUAL;

// --- Data Variabelen ---
int gepluktAantal = 0;
int joyX_raw, joyY_raw;
int joyX_mapped, joyY_mapped; // Waarden van -100 tot +100

// --- Smoothing Variabelen (Maakt de beweging vloeiend) ---
float joyX_smooth = 0.0;
float joyY_smooth = 0.0;

// --- Instellingen Joystick ---
const int deadzone = 200;    // Kleiner gemaakt (was 350) voor snellere reactie
const int adc_center = 2048; // Theoretisch midden

// --- UI Variabelen ---
unsigned long vorigeMillis = 0;
const int menuBreedte = 100;

// --- Prototypes ---
void tekenMenu();
void tekenSchermAuto();
void tekenSchermManual();
void tekenSchermDebug();
void checkTouch();
int berekenJoystick(int raw);

void setup() {
  Serial.begin(115200);
  
  // Zorgt ervoor dat de ESP32 de volledige 3.3V kan aflezen
  analogSetAttenuation(ADC_11db);

  // Joystick stroom
  pinMode(JOY_POWER_PIN, OUTPUT);
  digitalWrite(JOY_POWER_PIN, HIGH);

  tft.init();
  tft.setRotation(1); 
  tft.fillScreen(ST_DARK);

  uint16_t calData[5] = { 275, 3620, 264, 3532, 1 }; 
  tft.setTouch(calData);

  tekenMenu();
}

void loop() {
  // Lees ruwe data
  joyX_raw = analogRead(JOY_X_PIN);
  joyY_raw = analogRead(JOY_Y_PIN);

  // Bereken nieuwe gewenste posities (met deadzone en EXPO curve)
  int doel_x = berekenJoystick(joyX_raw);
  int doel_y = berekenJoystick(joyY_raw);

  // --- LOW-PASS FILTER (SMOOTHING) ---
  // Dit mengt 60% van de oude positie met 40% van de nieuwe input. 
  // Dit voorkomt harde schokken en trillingen.
  joyX_smooth = (joyX_smooth * 0.6) + (doel_x * 0.4);
  joyY_smooth = (joyY_smooth * 0.6) + (doel_y * 0.4);

  // Sla op als integers voor het scherm
  joyX_mapped = (int)joyX_smooth;
  joyY_mapped = (int)joyY_smooth;

  checkTouch();

  if (millis() - vorigeMillis > 100) {
    vorigeMillis = millis();
    
    switch(huidigScherm) {
      case AUTO: tekenSchermAuto(); break;
      case MANUAL: tekenSchermManual(); break;
      case DEBUG: tekenSchermDebug(); break;
    }
  }
}

// Functie met Deadzone én Exponentiële curve voor meer precisie
int berekenJoystick(int raw) {
  raw = constrain(raw, 0, 4095);
  int lineair = 0;

  // Zit hij in de deadzone? Dan 0.
  if (abs(raw - adc_center) < deadzone) {
    return 0;
  }
  
  // Bereken lineaire waarde (0 tot 100 of -100 tot 0)
  if (raw >= adc_center + deadzone) {
    lineair = map(raw, adc_center + deadzone, 4095, 0, 100);
  } else if (raw <= adc_center - deadzone) {
    lineair = map(raw, 0, adc_center - deadzone, -100, 0);
  }

  lineair = constrain(lineair, -100, 100);

  // --- EXPO CURVE ---
  // We delen door 100 (zodat we een factor tussen -1.0 en 1.0 hebben), 
  // doen dat tot de 3e macht (behoudt negatieve/positieve kant) en vermenigvuldigen weer met 100.
  // Hierdoor voelt de besturing rond het midden HEEL zacht aan!
  float factor = (float)lineair / 100.0;
  float expo = (factor * factor * factor) * 100.0;

  return (int)expo;
}

void checkTouch() {
  uint16_t t_x = 0, t_y = 0;
  
  if (tft.getTouch(&t_x, &t_y)) {
    t_y = tft.height() - t_y; 

    if (t_x < menuBreedte) {
      if (t_y < 106) huidigScherm = AUTO;
      else if (t_y < 212) huidigScherm = MANUAL;
      else huidigScherm = DEBUG;
      
      tft.fillRect(menuBreedte, 0, 480 - menuBreedte, 320, ST_DARK); 
      tekenMenu();
    }
  }
}

void tekenMenu() {
  tft.fillRect(0, 0, menuBreedte, 320, 0x1082); 
  tft.drawFastVLine(menuBreedte - 1, 0, 320, ST_LIME);

  tft.setTextSize(2);
  tft.setTextColor(huidigScherm == AUTO ? ST_LIME : TFT_WHITE);
  tft.setCursor(15, 45); tft.print("AUTO");

  tft.setTextColor(huidigScherm == MANUAL ? ST_LIME : TFT_WHITE);
  tft.setCursor(15, 151); tft.print("HAND");

  tft.setTextColor(huidigScherm == DEBUG ? ST_LIME : TFT_WHITE);
  tft.setCursor(15, 257); tft.print("DEBUG");
}

void tekenSchermAuto() {
  tft.setTextColor(ST_LIME, ST_DARK);
  tft.setTextSize(2);
  tft.setCursor(menuBreedte + 20, 30);
  tft.print("WEDSTRIJD MONITOR");

  tft.setTextSize(3);
  tft.setCursor(menuBreedte + 50, 100);
  tft.print("OOGST: "); tft.print(gepluktAantal);
  
  tft.setTextSize(2);
  tft.setCursor(menuBreedte + 50, 160);
  tft.print("STATUS: ");
  tft.setTextColor(TFT_YELLOW, ST_DARK);
  tft.print("SCANNING...");

  tft.fillRoundRect(menuBreedte + 50, 230, 120, 50, 10, 0x03E0); 
  tft.setTextColor(TFT_WHITE);
  tft.setCursor(menuBreedte + 75, 245); tft.print("START");
}

void tekenSchermManual() {
  int boxX = menuBreedte + 70; 
  int boxY = 20;               
  int boxW = 240;              
  int boxH = 240;              

  int vizierX = map(joyX_mapped, -100, 100, boxX, boxX + boxW);
  int vizierY = map(joyY_mapped, -100, 100, boxY, boxY + boxH);

  tft.drawRect(boxX, boxY, boxW, boxH, TFT_WHITE);
  tft.fillRect(boxX + 1, boxY + 1, boxW - 2, boxH - 2, ST_DARK);
  
  tft.drawFastHLine(boxX, vizierY, boxW, ST_LIME); 
  tft.drawFastVLine(vizierX, boxY, boxH, ST_LIME); 
  
  tft.setTextColor(TFT_WHITE, ST_DARK);
  tft.setTextSize(3);
  
  tft.setCursor(boxX + 10, boxY + boxH + 20); 
  tft.print("X: "); 
  if(joyX_mapped >= 0) tft.print(" "); // Ruimte compenseren voor min-teken
  tft.print(joyX_mapped); 
  tft.print("   "); 
  
  tft.setCursor(boxX + 130, boxY + boxH + 20); 
  tft.print("Y: "); 
  if(joyY_mapped >= 0) tft.print(" ");
  tft.print(joyY_mapped); 
  tft.print("   "); 
}

void tekenSchermDebug() {
  tft.setTextColor(TFT_WHITE, ST_DARK);
  tft.setTextSize(2);
  tft.setCursor(menuBreedte + 20, 20);
  tft.print("RAW SENSOR DATA");

  tft.setTextColor(ST_LIME, ST_DARK);
  tft.setCursor(menuBreedte + 20, 70);
  tft.print("RAW X: "); tft.print(joyX_raw); tft.print("    "); 
  
  tft.setCursor(menuBreedte + 20, 100);
  tft.print("RAW Y: "); tft.print(joyY_raw); tft.print("    ");

  tft.setCursor(menuBreedte + 20, 160);
  tft.print("ESP-NOW: DISCONNECTED");
  
  tft.fillRoundRect(menuBreedte + 20, 240, 200, 50, 10, ST_RED);
  tft.setTextColor(TFT_WHITE);
  tft.setCursor(menuBreedte + 45, 255); tft.print("KALIBREER XYZ");
}