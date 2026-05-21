/**
 * ESP-NOW receiver for AX-12A (Dynamixel protocol 1.0).
 * Prints WiFi MAC on boot — set that address in the SmartController.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_idf_version.h>
#include <Dynamixel2Arduino.h>

#define DXL_TX_PIN 17
#define DXL_RX_PIN 16
#define TX_ENABLE_PIN 4
#define RX_ENABLE_PIN 5
#define DXL_DIR_PIN RX_ENABLE_PIN

const float DXL_PROTOCOL_VERSION = 1.0f;
const uint32_t BAUDRATE = 1000000;

HardwareSerial DxlSerial(2);
Dynamixel2Arduino dxl(DxlSerial, DXL_DIR_PIN);

#pragma pack(push, 1)
struct Ax12Command {
  uint8_t magic;
  uint8_t cmd;
  uint8_t servoId;
  int16_t value;
} __attribute__((packed));
#pragma pack(pop)

static constexpr uint8_t kMagic = 0xA5;
static constexpr uint8_t kRspMagic = 0xA6;
enum : uint8_t { CMD_POSITION = 0, CMD_WHEEL = 1, CMD_WHEEL_STOP = 2, CMD_SCAN = 3 };
enum : uint8_t { RSP_SCAN = 1 };

#pragma pack(push, 1)
struct Ax12Response {
  uint8_t magic;
  uint8_t type;
  uint8_t foundId;
  uint8_t reserved;
} __attribute__((packed));
#pragma pack(pop)

uint8_t activeId = 0;
int activeMode = -1;
uint8_t controllerMac[6] = {};
bool hasControllerMac = false;

void applyWheelStop(uint8_t id);
void rememberController(const uint8_t *mac);
void runScanAndReply();

void IRAM_ATTR flipDirectionPin() {
  digitalWrite(TX_ENABLE_PIN, !digitalRead(RX_ENABLE_PIN));
}

void ensurePositionMode(uint8_t id) {
  if (activeId == id && activeMode == (int)OP_POSITION) return;
  dxl.setOperatingMode(id, OP_POSITION);
  dxl.torqueOn(id);
  activeId = id;
  activeMode = (int)OP_POSITION;
}

void ensureWheelMode(uint8_t id) {
  if (activeId == id && activeMode == (int)OP_VELOCITY) return;
  dxl.setOperatingMode(id, OP_VELOCITY);
  dxl.torqueOn(id);
  activeId = id;
  activeMode = (int)OP_VELOCITY;
}

void applyPosition(uint8_t id, int16_t pos) {
  pos = constrain(pos, 0, 1023);
  ensurePositionMode(id);
  dxl.setGoalPosition(id, (float)pos);
  Serial.printf("POS id=%u goal=%d\n", (unsigned)id, (int)pos);
}

void applyWheel(uint8_t id, int16_t pct) {
  pct = constrain(pct, -100, 100);
  if (pct == 0) {
    applyWheelStop(id);
    return;
  }
  ensureWheelMode(id);
  dxl.setGoalVelocity(id, (float)pct, UNIT_PERCENT);
  Serial.printf("WHEEL id=%u pct=%d\n", (unsigned)id, (int)pct);
}

void applyWheelStop(uint8_t id) {
  // Velocity 0 in wheel mode can still creep on AX-12A — lock joint at present angle.
  float present = dxl.getPresentPosition(id);
  if (isnan(present)) present = 512.0f;

  dxl.setGoalVelocity(id, 0.0f, UNIT_RAW);
  dxl.setOperatingMode(id, OP_POSITION);
  dxl.torqueOn(id);
  dxl.setGoalPosition(id, present);

  activeId = id;
  activeMode = (int)OP_POSITION;
  Serial.printf("WHEEL STOP id=%u locked@%d\n", (unsigned)id, (int)present);
}

void rememberController(const uint8_t *mac) {
  if (!mac) return;
  if (hasControllerMac && memcmp(mac, controllerMac, 6) == 0) return;

  memcpy(controllerMac, mac, 6);
  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, mac, 6);
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
  hasControllerMac = true;
}

uint8_t scanForServo() {
  for (int testId = 1; testId <= 253; testId++) {
    if (dxl.ping(testId)) {
      dxl.ledOn(testId);
      delay(80);
      dxl.ledOff(testId);
      return (uint8_t)testId;
    }
  }
  return 0;
}

void runScanAndReply() {
  uint8_t found = scanForServo();
  Serial.printf("SCAN done, found id=%u\n", (unsigned)found);

  if (!hasControllerMac) return;

  Ax12Response rsp{};
  rsp.magic = kRspMagic;
  rsp.type = RSP_SCAN;
  rsp.foundId = found;
  esp_now_send(controllerMac, reinterpret_cast<uint8_t *>(&rsp), sizeof(rsp));
}

void onEspNowRecv(const uint8_t *mac, const uint8_t *data, int len) {
  if (len < (int)sizeof(Ax12Command)) return;

  Ax12Command cmd;
  memcpy(&cmd, data, sizeof(cmd));
  if (cmd.magic != kMagic) return;

  rememberController(mac);

  if (cmd.cmd == CMD_SCAN) {
    runScanAndReply();
    return;
  }

  if (cmd.servoId == 0 || cmd.servoId > 254) return;

  switch (cmd.cmd) {
    case CMD_POSITION:
      applyPosition(cmd.servoId, cmd.value);
      break;
    case CMD_WHEEL:
      applyWheel(cmd.servoId, cmd.value);
      break;
    case CMD_WHEEL_STOP:
      applyWheelStop(cmd.servoId);
      break;
    default:
      break;
  }
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
void onEspNowRecvCompat(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  onEspNowRecv(info ? info->src_addr : nullptr, data, len);
}
#else
void onEspNowRecvCompat(const uint8_t *mac, const uint8_t *data, int len) {
  onEspNowRecv(mac, data, len);
}
#endif

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(TX_ENABLE_PIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(RX_ENABLE_PIN), flipDirectionPin, CHANGE);
  digitalWrite(TX_ENABLE_PIN, HIGH);

  DxlSerial.begin(BAUDRATE, SERIAL_8N1, DXL_RX_PIN, DXL_TX_PIN);
  dxl.begin(BAUDRATE);
  dxl.setPortProtocolVersion(DXL_PROTOCOL_VERSION);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  Serial.print("Receiver MAC (set in controller): ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(onEspNowRecvCompat);
  Serial.println("ESP-NOW listening for AX-12 commands");
}

void loop() {
  delay(10);
}
