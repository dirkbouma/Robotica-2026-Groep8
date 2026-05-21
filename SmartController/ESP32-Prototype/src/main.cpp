/**
 * Minimal AX-12A touchscreen remote over ESP-NOW.
 * Set robotAddress[] to your receiver ESP32 MAC (Serial prints it on boot).
 */
#include <Arduino.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_idf_version.h>

TFT_eSPI tft = TFT_eSPI();

uint8_t robotAddress[] = {0xCC, 0xDB, 0xA7, 0x98, 0x82, 0x84};

#pragma pack(push, 1)
struct Ax12Command {
  uint8_t magic;
  uint8_t cmd;
  uint8_t servoId;
  int16_t value;
} __attribute__((packed));

struct Ax12Response {
  uint8_t magic;
  uint8_t type;
  uint8_t foundId;
  uint8_t reserved;
} __attribute__((packed));
#pragma pack(pop)

static constexpr uint8_t kMagic = 0xA5;
static constexpr uint8_t kRspMagic = 0xA6;
static constexpr uint8_t kBroadcastId = 254;
enum : uint8_t { CMD_POSITION = 0, CMD_WHEEL = 1, CMD_WHEEL_STOP = 2, CMD_SCAN = 3 };
enum : uint8_t { RSP_SCAN = 1 };

esp_now_peer_info_t peerInfo;
String espNowStatus = "...";

const int JOY_POWER_PIN = 32;
const int JOY_X_PIN = 34;
const int JOY_Y_PIN = 35;

#define C_BG 0x0000
#define C_PANEL 0x2104
#define C_TEXT TFT_WHITE
#define C_DIM 0xBDF7
#define C_AC 0xFFE0
#define C_BORDER 0xFFFF
#define C_BTN 0x3186
#define C_BTN_DARK 0x2124
#define C_BTN_APPLY 0x03E0
#define C_ERR 0xF800

enum Screen { SCR_ID, SCR_POS, SCR_WHEEL, SCR_JOY };
Screen screen = SCR_ID;

const int MENU_W = 72;
const int CONTENT_X = MENU_W + 8;
const int CONTENT_PAD = 10;

uint8_t targetId = 1;
int16_t goalPos = 512;
int16_t wheelPct = 0;

int joyRawX, joyRawY;
int joyMapX, joyMapY;

unsigned long tWheelSend = 0;

static constexpr unsigned long kIdHoldDelayMs = 500;
static constexpr unsigned long kIdRepeatMs = 120;
int idHoldBtn = -1;
unsigned long idHoldStart = 0;
unsigned long idLastStep = 0;
bool idBcastWasDown = false;
bool idIdentifyWasDown = false;
bool posApplyWasDown = false;
bool scanPending = false;
unsigned long scanStartMs = 0;

Screen drawnScreen = (Screen)-1;
uint8_t drawnId = 0;
int16_t drawnPos = -1;
int16_t drawnWheel = -999;
String drawnEnow;
int drawnJoyRawX = -1, drawnJoyRawY = -1;
int drawnJoyMapX = -999, drawnJoyMapY = -999;
int joyCrossVx = -1, joyCrossVy = -1;

struct Rect {
  int x, y, w, h;
};

struct UiLayout {
  int contentW;
  int cx;
  int idValueY;
  Rect idMinus;
  Rect idPlus;
  Rect idBroadcast;
  Rect idIdentify;
  int posValueY;
  Rect posM50;
  Rect posM10;
  Rect posP10;
  Rect posP50;
  Rect posApply;
  Rect wheelStop;
  Rect wheelSlider;
  int wheelValueY;
  Rect joyBox;
};

UiLayout ui{};

void calcLayout();
void drawMenu();
void drawScreenStatic();
void updateScreenDynamic();
void switchScreen(Screen next);
void handleTouch();
void updateIdButtons();
void updateIdScreenButtons();
void updatePosButtons();
void stepId(int dir);
void sendCmd(uint8_t cmd, int16_t value);
void sendScan();
void pollScanTimeout();
int mapJoystick(int raw);
void printFixed(int x, int y, int w, int h, uint16_t fg, uint16_t bg, const char *text);
void drawButton(const Rect &r, const char *label, uint16_t fill, uint16_t textColor, uint8_t font);
bool hitRect(const Rect &r, int tx, int ty);
void drawCenteredValue(int cx, int cy, int clearW, int clearH, const char *text, uint8_t textSize);
void onScanResponse(const uint8_t *data, int len);

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  (void)mac_addr;
  if (!scanPending) {
    espNowStatus = (status == ESP_NOW_SEND_SUCCESS) ? "OK" : "FAIL";
  }
}

void onScanResponse(const uint8_t *data, int len) {
  if (len < (int)sizeof(Ax12Response)) return;

  Ax12Response rsp;
  memcpy(&rsp, data, sizeof(rsp));
  if (rsp.magic != kRspMagic || rsp.type != RSP_SCAN) return;

  scanPending = false;
  if (rsp.foundId >= 1 && rsp.foundId <= 253) {
    targetId = rsp.foundId;
    drawnId = 0;
    espNowStatus = "FOUND";
  } else {
    espNowStatus = "NO SERVO";
  }
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
  onScanResponse(data, len);
}
#else
void OnDataRecv(const uint8_t *mac, const uint8_t *data, int len) {
  (void)mac;
  onScanResponse(data, len);
}
#endif

void calcLayout() {
  ui.contentW = tft.width() - CONTENT_X - CONTENT_PAD;
  ui.cx = (MENU_W + tft.width()) / 2;

  const int btnH = 48;
  const int gap = 10;
  const int halfW = (ui.contentW - gap) / 2;

  ui.idValueY = 88;
  ui.idMinus = {CONTENT_X, 120, halfW, btnH};
  ui.idPlus = {CONTENT_X + halfW + gap, 120, halfW, btnH};
  ui.idBroadcast = {CONTENT_X, 176, ui.contentW, 40};
  ui.idIdentify = {CONTENT_X, 222, ui.contentW, 40};

  ui.posValueY = 92;
  const int stepW = (ui.contentW - 3 * gap) / 4;
  const int stepY = 138;
  ui.posM50 = {CONTENT_X, stepY, stepW, btnH};
  ui.posM10 = {CONTENT_X + stepW + gap, stepY, stepW, btnH};
  ui.posP10 = {CONTENT_X + 2 * (stepW + gap), stepY, stepW, btnH};
  ui.posP50 = {CONTENT_X + 3 * (stepW + gap), stepY, stepW, btnH};
  ui.posApply = {CONTENT_X, 220, ui.contentW, btnH};

  ui.wheelValueY = 78;
  ui.wheelSlider = {CONTENT_X + 36, 128, ui.contentW - 72, 32};
  ui.wheelStop = {CONTENT_X, 220, ui.contentW, btnH};

  ui.joyBox = {CONTENT_X + 16, 52, ui.contentW - 80, 200};
}

void setup() {
  Serial.begin(115200);
  analogSetAttenuation(ADC_11db);
  pinMode(JOY_POWER_PIN, OUTPUT);
  digitalWrite(JOY_POWER_PIN, HIGH);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  delay(20);

  uint16_t calData[5] = {275, 3620, 264, 3532, 1};
  tft.setTouch(calData);
  calcLayout();

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  if (esp_now_init() == ESP_OK) {
    esp_now_register_send_cb(OnDataSent);
    esp_now_register_recv_cb(OnDataRecv);
    memcpy(peerInfo.peer_addr, robotAddress, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    esp_now_add_peer(&peerInfo);
    espNowStatus = "PEER OK";
  } else {
    espNowStatus = "ENOW FAIL";
  }

  Serial.print("Controller MAC: ");
  Serial.println(WiFi.macAddress());

  tft.fillScreen(TFT_BLACK);
  drawMenu();
  switchScreen(SCR_ID);
}

void loop() {
  joyRawX = analogRead(JOY_X_PIN);
  joyRawY = analogRead(JOY_Y_PIN);
  joyMapX = mapJoystick(joyRawX);
  joyMapY = mapJoystick(joyRawY);

  updateIdButtons();
  updateIdScreenButtons();
  updatePosButtons();
  handleTouch();
  pollScanTimeout();

  unsigned long now = millis();
  if (screen == SCR_WHEEL && now - tWheelSend >= 50) {
    tWheelSend = now;
    if (wheelPct == 0) sendCmd(CMD_WHEEL_STOP, 0);
    else sendCmd(CMD_WHEEL, wheelPct);
  }

  updateScreenDynamic();
}

bool hitRect(const Rect &r, int tx, int ty) {
  return tx >= r.x && tx < r.x + r.w && ty >= r.y && ty < r.y + r.h;
}

void drawButton(const Rect &r, const char *label, uint16_t fill, uint16_t textColor, uint8_t font) {
  tft.fillRect(r.x, r.y, r.w, r.h, fill);
  tft.drawRect(r.x, r.y, r.w, r.h, C_BORDER);
  tft.drawRect(r.x + 1, r.y + 1, r.w - 2, r.h - 2, C_DIM);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(textColor, fill);
  tft.drawString(label, r.x + r.w / 2, r.y + r.h / 2 + 1, font);
  tft.setTextDatum(TL_DATUM);
}

void drawCenteredValue(int cx, int cy, int clearW, int clearH, const char *text, uint8_t textSize) {
  tft.fillRect(cx - clearW / 2, cy - clearH / 2, clearW, clearH, C_BG);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(C_AC, C_BG);
  tft.setTextSize(textSize);
  tft.drawString(text, cx, cy);
  tft.setTextSize(1);
  tft.setTextDatum(TL_DATUM);
}

void printFixed(int x, int y, int w, int h, uint16_t fg, uint16_t bg, const char *text) {
  tft.fillRect(x, y, w, h, bg);
  tft.setTextColor(fg, bg);
  tft.setTextDatum(TL_DATUM);
  tft.setCursor(x, y);
  tft.print(text);
}

void switchScreen(Screen next) {
  if (screen == SCR_WHEEL && next != SCR_WHEEL) {
    wheelPct = 0;
    sendCmd(CMD_WHEEL_STOP, 0);
  }
  screen = next;
  idHoldBtn = -1;
  idBcastWasDown = false;
  idIdentifyWasDown = false;
  posApplyWasDown = false;
  drawnScreen = (Screen)-1;
  joyCrossVx = joyCrossVy = -1;
  drawnJoyRawX = drawnJoyRawY = -1;
  drawnJoyMapX = drawnJoyMapY = -999;
  tft.fillScreen(TFT_BLACK);
  drawMenu();
  drawScreenStatic();
  updateScreenDynamic();
}

void sendCmd(uint8_t cmd, int16_t value) {
  Ax12Command p{};
  p.magic = kMagic;
  p.cmd = cmd;
  p.servoId = targetId;
  p.value = value;
  esp_now_send(robotAddress, reinterpret_cast<uint8_t *>(&p), sizeof(p));
}

void sendScan() {
  Ax12Command p{};
  p.magic = kMagic;
  p.cmd = CMD_SCAN;
  p.servoId = 0;
  p.value = 0;
  esp_now_send(robotAddress, reinterpret_cast<uint8_t *>(&p), sizeof(p));
  scanPending = true;
  scanStartMs = millis();
  espNowStatus = "SCANNING";
}

void pollScanTimeout() {
  if (scanPending && millis() - scanStartMs > 10000) {
    scanPending = false;
    espNowStatus = "SCAN TIMEOUT";
  }
}

int mapJoystick(int raw) {
  const int center = 2048;
  const int dz = 200;
  if (abs(raw - center) < dz) return 0;
  int lin = (raw >= center + dz) ? map(raw, center + dz, 4095, 0, 100)
                                 : map(raw, 0, center - dz, -100, 0);
  float f = lin / 100.0f;
  return (int)((f * f * f) * 100.0f);
}

void stepId(int dir) {
  if (dir < 0) {
    if (targetId == kBroadcastId) targetId = 253;
    else if (targetId > 1) targetId--;
  } else {
    if (targetId == 253) targetId = kBroadcastId;
    else if (targetId < 253) targetId++;
  }
}

void updateIdButtons() {
  if (screen != SCR_ID) {
    idHoldBtn = -1;
    return;
  }

  uint16_t tx, ty;
  bool touch = tft.getTouch(&tx, &ty);
  if (touch) ty = tft.height() - ty;

  int btn = -1;
  if (touch) {
    if (hitRect(ui.idMinus, tx, ty)) btn = 0;
    else if (hitRect(ui.idPlus, tx, ty)) btn = 1;
  }

  unsigned long now = millis();
  if (btn != idHoldBtn) {
    if (btn >= 0) {
      stepId(btn == 0 ? -1 : 1);
      idHoldBtn = btn;
      idHoldStart = now;
      idLastStep = now;
    } else {
      idHoldBtn = -1;
    }
    return;
  }

  if (idHoldBtn >= 0 && now - idHoldStart >= kIdHoldDelayMs &&
      now - idLastStep >= kIdRepeatMs) {
    stepId(idHoldBtn == 0 ? -1 : 1);
    idLastStep = now;
  }
}

void updateIdScreenButtons() {
  if (screen != SCR_ID) {
    idBcastWasDown = false;
    idIdentifyWasDown = false;
    return;
  }

  uint16_t tx, ty;
  bool touch = tft.getTouch(&tx, &ty);
  if (touch) ty = tft.height() - ty;

  bool bcastDown = touch && hitRect(ui.idBroadcast, tx, ty);
  if (bcastDown && !idBcastWasDown) targetId = kBroadcastId;
  idBcastWasDown = bcastDown;

  bool identifyDown = touch && hitRect(ui.idIdentify, tx, ty);
  if (identifyDown && !idIdentifyWasDown && !scanPending) sendScan();
  idIdentifyWasDown = identifyDown;
}

void updatePosButtons() {
  if (screen != SCR_POS) {
    posApplyWasDown = false;
    return;
  }

  uint16_t tx, ty;
  bool touch = tft.getTouch(&tx, &ty);
  if (touch) ty = tft.height() - ty;

  bool applyDown = touch && hitRect(ui.posApply, tx, ty);
  if (applyDown && !posApplyWasDown) sendCmd(CMD_POSITION, goalPos);
  posApplyWasDown = applyDown;
}

void handleTouch() {
  uint16_t tx, ty;
  if (!tft.getTouch(&tx, &ty)) return;
  ty = tft.height() - ty;

  if (tx < MENU_W) {
    int h = tft.height() / 4;
    Screen next = SCR_ID;
    if (ty < h) next = SCR_ID;
    else if (ty < 2 * h) next = SCR_POS;
    else if (ty < 3 * h) next = SCR_WHEEL;
    else next = SCR_JOY;
    if (next != screen) switchScreen(next);
    return;
  }

  if (screen == SCR_POS) {
    if (hitRect(ui.posM50, tx, ty)) goalPos -= 50;
    else if (hitRect(ui.posM10, tx, ty)) goalPos -= 10;
    else if (hitRect(ui.posP10, tx, ty)) goalPos += 10;
    else if (hitRect(ui.posP50, tx, ty)) goalPos += 50;
    goalPos = constrain(goalPos, 0, 1023);
  } else if (screen == SCR_WHEEL) {
    if (hitRect(ui.wheelStop, tx, ty)) {
      wheelPct = 0;
      sendCmd(CMD_WHEEL_STOP, 0);
      return;
    }
    Rect sl = {ui.wheelSlider.x - 12, ui.wheelSlider.y - 20, ui.wheelSlider.w + 24,
               ui.wheelSlider.h + 40};
    if (hitRect(sl, tx, ty)) {
      wheelPct = (int16_t)map(tx, ui.wheelSlider.x, ui.wheelSlider.x + ui.wheelSlider.w,
                              -100, 100);
      wheelPct = constrain(wheelPct, -100, 100);
      if (abs(wheelPct) <= 5) wheelPct = 0;
    }
  }
}

void drawMenu() {
  tft.fillRect(0, 0, MENU_W, tft.height(), C_PANEL);
  tft.drawFastVLine(MENU_W - 1, 0, tft.height(), C_BORDER);
  int h = tft.height() / 4;
  const char *labels[] = {"ID", "POS", "SPN", "JOY"};
  for (int i = 0; i < 4; i++) {
    int y = i * h;
    if (screen == (Screen)i) {
      tft.fillRect(4, y + 8, MENU_W - 8, h - 16, C_BTN);
      tft.drawRect(4, y + 8, MENU_W - 8, h - 16, C_AC);
      tft.setTextColor(C_AC, C_BTN);
    } else {
      tft.setTextColor(C_TEXT, C_PANEL);
    }
    tft.setTextSize(2);
    tft.setTextDatum(MC_DATUM);
    tft.drawString(labels[i], MENU_W / 2, y + h / 2, 1);
  }
  tft.setTextDatum(TL_DATUM);
}

void drawHeaderStatic() {
  if (screen == SCR_JOY) return;
  tft.fillRect(CONTENT_X, 0, tft.width() - CONTENT_X, 30, C_PANEL);
  tft.drawFastHLine(CONTENT_X, 29, tft.width() - CONTENT_X, C_DIM);
}

void drawHeaderDynamic() {
  if (screen == SCR_JOY) return;
  char buf[32];
  snprintf(buf, sizeof(buf), "ID:%u   ENOW:%s", (unsigned)targetId, espNowStatus.c_str());
  printFixed(CONTENT_X + 4, 8, ui.contentW, 14, C_TEXT, C_PANEL, buf);
  drawnEnow = espNowStatus;
}

void drawScreenStatic() {
  if (drawnScreen == screen) return;
  drawnScreen = screen;

  drawHeaderStatic();

  if (screen == SCR_ID) {
    tft.fillRect(CONTENT_X, 30, tft.width() - CONTENT_X, tft.height() - 30, C_BG);
    tft.setTextDatum(MC_DATUM);
    tft.setTextColor(C_TEXT, C_BG);
    tft.drawString("SERVO ID", ui.cx, 52, 2);
    drawButton(ui.idMinus, "-", C_BTN, C_TEXT, 4);
    drawButton(ui.idPlus, "+", C_BTN, C_TEXT, 4);
    drawButton(ui.idBroadcast, "BCAST 254", C_BTN_DARK, C_AC, 2);
    drawButton(ui.idIdentify, "FIND ID", C_BTN_APPLY, C_BG, 2);
    tft.setTextDatum(TL_DATUM);
  } else if (screen == SCR_POS) {
    tft.fillRect(CONTENT_X, 30, tft.width() - CONTENT_X, tft.height() - 30, C_BG);
    tft.setTextDatum(MC_DATUM);
    tft.setTextColor(C_TEXT, C_BG);
    tft.drawString("GOAL POSITION", ui.cx, 52, 2);
    tft.setTextColor(C_DIM, C_BG);
    tft.drawString("0 - 1023", ui.cx, 72, 1);
    drawButton(ui.posM50, "-50", C_BTN, C_TEXT, 2);
    drawButton(ui.posM10, "-10", C_BTN, C_TEXT, 2);
    drawButton(ui.posP10, "+10", C_BTN, C_TEXT, 2);
    drawButton(ui.posP50, "+50", C_BTN, C_TEXT, 2);
    drawButton(ui.posApply, "APPLY", C_BTN_APPLY, C_BG, 2);
    tft.setTextDatum(TL_DATUM);
  } else if (screen == SCR_WHEEL) {
    tft.fillRect(CONTENT_X, 30, tft.width() - CONTENT_X, tft.height() - 30, C_BG);
    const Rect &sl = ui.wheelSlider;
    const int midY = sl.y + sl.h / 2;
    tft.setTextDatum(MC_DATUM);
    tft.setTextColor(C_TEXT, C_BG);
    tft.drawString("CONTINUOUS SPIN", ui.cx, 52, 2);
    tft.setTextColor(C_DIM, C_BG);
    tft.drawString("-100", sl.x - 14, midY, 2);
    tft.drawString("+100", sl.x + sl.w + 14, midY, 2);
    tft.drawString("0", ui.cx, sl.y + sl.h + 14, 1);
    tft.fillRect(sl.x, sl.y, sl.w, sl.h, C_BTN_DARK);
    tft.drawRect(sl.x, sl.y, sl.w, sl.h, C_BORDER);
    tft.drawFastVLine(sl.x, sl.y - 6, sl.h + 12, C_DIM);
    tft.drawFastVLine(sl.x + sl.w, sl.y - 6, sl.h + 12, C_DIM);
    tft.drawFastVLine(sl.x + sl.w / 2, sl.y - 4, sl.h + 8, C_DIM);
    drawButton(ui.wheelStop, "STOP", C_ERR, C_TEXT, 2);
    tft.setTextDatum(TL_DATUM);
  } else if (screen == SCR_JOY) {
    tft.fillRect(CONTENT_X, 0, tft.width() - CONTENT_X, tft.height(), C_BG);
    tft.drawRect(ui.joyBox.x, ui.joyBox.y, ui.joyBox.w, ui.joyBox.h, C_BORDER);
    tft.fillRect(ui.joyBox.x + 1, ui.joyBox.y + 1, ui.joyBox.w - 2, ui.joyBox.h - 2, C_BG);
  }

  drawnId = 0;
  drawnPos = -1;
  drawnWheel = -999;
}

void updateJoyCrosshair(int vx, int vy) {
  const Rect &j = ui.joyBox;
  if (joyCrossVx >= 0) tft.drawFastVLine(joyCrossVx, j.y + 1, j.h - 2, C_BG);
  if (joyCrossVy >= 0) tft.drawFastHLine(j.x + 1, joyCrossVy, j.w - 2, C_BG);
  tft.drawFastVLine(vx, j.y + 1, j.h - 2, C_AC);
  tft.drawFastHLine(j.x + 1, vy, j.w - 2, C_AC);
  joyCrossVx = vx;
  joyCrossVy = vy;
}

void updateScreenDynamic() {
  drawScreenStatic();

  if (screen != SCR_JOY && (drawnEnow != espNowStatus || drawnId != targetId)) {
    drawHeaderDynamic();
  }

  if (screen == SCR_ID) {
    if (drawnId != targetId) {
      char buf[12];
      if (targetId == kBroadcastId) snprintf(buf, sizeof(buf), "254");
      else snprintf(buf, sizeof(buf), "%u", (unsigned)targetId);
      drawCenteredValue(ui.cx, ui.idValueY, 220, 56, buf, 6);
      drawnId = targetId;
    }
  } else if (screen == SCR_POS) {
    if (drawnPos != goalPos) {
      char buf[16];
      snprintf(buf, sizeof(buf), "%d", (int)goalPos);
      drawCenteredValue(ui.cx, ui.posValueY, 240, 48, buf, 5);
      drawnPos = goalPos;
    }
  } else if (screen == SCR_WHEEL) {
    if (drawnWheel != wheelPct) {
      char buf[16];
      snprintf(buf, sizeof(buf), "%d%%", (int)wheelPct);
      drawCenteredValue(ui.cx, ui.wheelValueY, 160, 40, buf, 4);

      const Rect &sl = ui.wheelSlider;
      int knobX = map(wheelPct, -100, 100, sl.x, sl.x + sl.w);
      if (drawnWheel != -999) {
        int oldKnobX = map(drawnWheel, -100, 100, sl.x, sl.x + sl.w);
        tft.fillRect(oldKnobX - 12, sl.y - 10, 24, sl.h + 20, C_BG);
        tft.fillRect(sl.x, sl.y, sl.w, sl.h, C_BTN_DARK);
        tft.drawRect(sl.x, sl.y, sl.w, sl.h, C_BORDER);
        tft.drawFastVLine(sl.x, sl.y - 6, sl.h + 12, C_DIM);
        tft.drawFastVLine(sl.x + sl.w, sl.y - 6, sl.h + 12, C_DIM);
        tft.drawFastVLine(sl.x + sl.w / 2, sl.y - 4, sl.h + 8, C_DIM);
      }
      tft.fillRect(knobX - 12, sl.y - 10, 24, sl.h + 20, C_AC);
      tft.drawRect(knobX - 12, sl.y - 10, 24, sl.h + 20, C_BORDER);
      drawnWheel = wheelPct;
    }
  } else if (screen == SCR_JOY) {
    if (drawnJoyRawX != joyRawX || drawnJoyRawY != joyRawY) {
      char buf[32];
      snprintf(buf, sizeof(buf), "raw X:%4d Y:%4d", joyRawX, joyRawY);
      printFixed(CONTENT_X, 8, 240, 14, C_TEXT, C_BG, buf);
      drawnJoyRawX = joyRawX;
      drawnJoyRawY = joyRawY;
    }
    if (drawnJoyMapX != joyMapX || drawnJoyMapY != joyMapY) {
      char buf[32];
      snprintf(buf, sizeof(buf), "map X:%4d Y:%4d", joyMapX, joyMapY);
      printFixed(CONTENT_X, 26, 240, 14, C_AC, C_BG, buf);
      drawnJoyMapX = joyMapX;
      drawnJoyMapY = joyMapY;
      int vx = map(joyMapX, -100, 100, ui.joyBox.x, ui.joyBox.x + ui.joyBox.w);
      int vy = map(joyMapY, -100, 100, ui.joyBox.y, ui.joyBox.y + ui.joyBox.h);
      updateJoyCrosshair(vx, vy);
    }
  }
}
