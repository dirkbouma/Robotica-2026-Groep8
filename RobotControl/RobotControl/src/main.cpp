#include <Arduino.h>

#define ID      1
#define RX_PIN  16
#define TX_PIN  17

HardwareSerial dxl(1);

void sendPacket(uint8_t id, uint8_t inst, uint8_t* params, uint8_t nparams) {
    uint8_t len = nparams + 2;
    uint16_t cs = id + len + inst;
    for (int i = 0; i < nparams; i++) cs += params[i];
    cs = ~cs & 0xFF;

    dxl.write(0xFF); dxl.write(0xFF);
    dxl.write(id);   dxl.write(len);
    dxl.write(inst);
    for (int i = 0; i < nparams; i++) dxl.write(params[i]);
    dxl.write((uint8_t)cs);
    dxl.flush();
}

int32_t readResponse(uint8_t nparams) {
    uint8_t buf[16];
    uint8_t expected = 6 + nparams;
    uint32_t t = millis();
    uint8_t i = 0;
    while (i < expected && millis() - t < 20)
        if (dxl.available()) buf[i++] = dxl.read();

    if (i < expected || buf[4] != 0) return -1;
    if (nparams == 1) return buf[5];
    if (nparams == 2) return buf[5] | (buf[6] << 8);
    return 0;
}

void writeReg(uint8_t reg, uint16_t val, bool two) {
    uint8_t p[3] = { reg, (uint8_t)(val & 0xFF), (uint8_t)(val >> 8) };
    sendPacket(ID, 0x03, p, two ? 3 : 2);
    readResponse(0);  // flush echo
}

int32_t readReg(uint8_t reg, uint8_t bytes) {
    uint8_t p[2] = { reg, bytes };
    sendPacket(ID, 0x02, p, 2);
    return readResponse(bytes);
}

void setup() {
    Serial.begin(115200);
    dxl.begin(1000000, SERIAL_8N1, RX_PIN, TX_PIN);
    delay(300);

    writeReg(0x18, 1, false);   // torque on
    writeReg(0x20, 200, true);  // speed
    Serial.println("AX-12A ready");
}

void loop() {
    // Move left
    Serial.println("Moving left...");
    writeReg(0x1E, 200, true);
    delay(1500);

    int32_t load = readReg(0x28, 2);
    if (load >= 0) {
        uint16_t magnitude = (load & 0x3FF) * 100 / 1023;
        String dir = (load >> 10) & 1 ? "CW" : "CCW";
        Serial.printf("Load: %d%% (%s)\n", magnitude, dir.c_str());
    } else {
        Serial.println("Load read failed");
    }

    // Move right
    Serial.println("Moving right...");
    writeReg(0x1E, 800, true);
    delay(1500);

    load = readReg(0x28, 2);
    if (load >= 0) {
        uint16_t magnitude = (load & 0x3FF) * 100 / 1023;
        String dir = (load >> 10) & 1 ? "CW" : "CCW";
        Serial.printf("Load: %d%% (%s)\n", magnitude, dir.c_str());
    } else {
        Serial.println("Load read failed");
    }
}