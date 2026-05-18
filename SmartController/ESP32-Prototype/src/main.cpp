#include <Arduino.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <esp_now.h>

TFT_eSPI tft = TFT_eSPI();

// --- ESP-NOW ---
uint8_t robotAddress[] = {0xCC, 0xDB, 0xA7, 0x98, 0x82, 0x84}; // VUL JE EIGEN MAC ADRES IN

typedef struct struct_message {
  int x;
  int y;
  float maxSpeed; // Nieuw: De ingestelde snelheid van de slider
} struct_message;

struct_message actueleData;
esp_now_peer_info_t peerInfo;
String espNowStatus = "STARTING...";

// --- Pinnen ---
const int JOY_POWER_PIN = 32;
const int JOY_X_PIN = 34; 
const int JOY_Y_PIN = 35; 

// --- Kleuren & UI ---
#define ST_DARK   0x0841 
#define ST_LIME   0xDEFB 
#define ST_RED    0xF800 
enum Scherm { AUTO, MANUAL, DEBUG };
Scherm huidigScherm = MANUAL;

int joyX_mapped, joyY_mapped;
float speedSetting = 5.0; // Standaard snelheidswaarde
unsigned long vorigeMillis = 0;
const int menuBreedte = 100;

// --- Prototypes ---
void tekenMenu();
void tekenSchermManual();
void checkTouch();
int berekenJoystick(int raw);

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  espNowStatus = (status == ESP_NOW_SEND_SUCCESS) ? "OK" : "FAIL";
}

void setup() {
  Serial.begin(115200);
  analogSetAttenuation(ADC_11db);
  pinMode(JOY_POWER_PIN, OUTPUT);
  digitalWrite(JOY_POWER_PIN, HIGH);

  tft.init();
  tft.setRotation(1); 
  tft.fillScreen(ST_DARK);
  uint16_t calData[5] = { 275, 3620, 264, 3532, 1 }; 
  tft.setTouch(calData);

  WiFi.mode(WIFI_STA);
  if (esp_now_init() == ESP_OK) {
    esp_now_register_send_cb(OnDataSent);
    memcpy(peerInfo.peer_addr, robotAddress, 6);
    peerInfo.channel = 0;  
    peerInfo.encrypt = false;
    esp_now_add_peer(&peerInfo);
  }
  tekenMenu();
}

void loop() {
  joyX_mapped = berekenJoystick(analogRead(JOY_X_PIN));
  joyY_mapped = berekenJoystick(analogRead(JOY_Y_PIN));

  checkTouch();

  if (millis() - vorigeMillis > 50) { // Iets snellere update voor snelheid (20Hz)
    vorigeMillis = millis();
    
    if (huidigScherm == MANUAL) {
      actueleData.x = joyX_mapped;
      actueleData.y = joyY_mapped;
      actueleData.maxSpeed = speedSetting;
      esp_now_send(robotAddress, (uint8_t *) &actueleData, sizeof(actueleData));
      tekenSchermManual();
    }
  }
}

int berekenJoystick(int raw) {
  int center = 2048;
  int deadzone = 200;
  if (abs(raw - center) < deadzone) return 0;
  int lineair = (raw >= center + deadzone) ? map(raw, center+deadzone, 4095, 0, 100) : map(raw, 0, center-deadzone, -100, 0);
  float f = (float)lineair / 100.0;
  return (int)((f * f * f) * 100.0); // Expo curve behouden voor precisie
}

void checkTouch() {
  uint16_t t_x, t_y;
  if (tft.getTouch(&t_x, &t_y)) {
    t_y = tft.height() - t_y; // Flip Y-as
    if (t_x < menuBreedte) {
      if (t_y < 106) huidigScherm = AUTO;
      else if (t_y < 212) huidigScherm = MANUAL;
      else huidigScherm = DEBUG;
      tft.fillRect(menuBreedte, 0, 380, 320, ST_DARK); 
      tekenMenu();
    } else if (huidigScherm == MANUAL && t_x > 410) {
      // Slider logica: bepaal de snelheidswaarde (0.5 tot 15.0)
      speedSetting = (float)map(t_y, 260, 20, 5, 150) / 10.0;
      speedSetting = constrain(speedSetting, 0.5, 15.0);
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

void tekenSchermManual() {
  int boxX = menuBreedte + 40, boxY = 40, boxW = 220, boxH = 220;
  int vX = map(joyX_mapped, -100, 100, boxX, boxX + boxW);
  int vY = map(joyY_mapped, -100, 100, boxY, boxY + boxH);

  tft.drawRect(boxX, boxY, boxW, boxH, TFT_WHITE);
  tft.fillRect(boxX+1, boxY+1, boxW-2, boxH-2, ST_DARK);
  tft.drawFastHLine(boxX, vY, boxW, ST_LIME); 
  tft.drawFastVLine(vX, boxY, boxH, ST_LIME); 

  // Slider visualisatie
  int slX = 420, slY = 40, slH = 220;
  tft.fillRect(slX, 0, 60, 320, ST_DARK); // Wis kolom
  tft.fillRect(slX+15, slY, 10, slH, TFT_DARKGREY);
  int knobY = map(speedSetting * 10, 5, 150, slY + slH, slY);
  tft.fillRect(slX, knobY-10, 40, 20, ST_LIME);
  tft.setTextColor(TFT_WHITE); tft.setTextSize(1);
  tft.setCursor(slX-5, slY+slH+15); tft.print("SPEED:");
  tft.setCursor(slX+5, slY+slH+30); tft.print(speedSetting, 1);
}