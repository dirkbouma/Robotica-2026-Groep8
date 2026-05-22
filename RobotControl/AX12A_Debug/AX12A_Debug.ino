/*
 * AX-12A Extended Debugger
 * Does NOT use the Dynamixel library. Fully manual protocol implementation.
 * Designed for ESP32 and a 74LS241 Half-Duplex Buffer.
 *
 * =========================================================================
 * 74LS241 HARDWARE WIRING NOTES FOR HALF-DUPLEX
 * =========================================================================
 * The 74LS241 has two sets of buffers:
 * - 1G (Pin 1) is ACTIVE LOW. Enables 1A -> 1Y.
 * - 2G (Pin 19) is ACTIVE HIGH. Enables 2A -> 2Y.
 *
 * Recommended wiring:
 * ESP TX (Pin 17) -> 1A (Pin 2)
 * 1Y (Pin 18)     -> AX-12A DATA Pin
 * AX-12A DATA Pin -> 2A (Pin 17)
 * 2Y (Pin 3)      -> ESP RX (Pin 16)
 *
 * DIR Pin (Pin 4) -> Connect to both 1G (Pin 1) and 2G (Pin 19).
 *
 * Behavior with this wiring:
 * - DIR = LOW:  1G active (TX enabled), 2G inactive (RX disabled)
 * - DIR = HIGH: 1G inactive (TX disabled), 2G active (RX enabled)
 *
 * NOTE: ESP32 logic is 3.3V. 74LS241 requires VCC=5V. The ESP32 TX can
 * drive the 74LS241 input (Vih = 2.0V). However, the 74LS241 output to
 * ESP RX will be ~5V. A voltage divider or logic level converter is
 * recommended on the RX line to protect the ESP32.
 * =========================================================================
 */

#include <Arduino.h>

// --- PIN CONFIGURATION ---
#define DXL_TX_PIN 17
#define DXL_RX_PIN 16
#define DIR_PIN 15

// In our hardware notes above:
// LOW = TX (1G active), HIGH = RX (2G active).
// You can flip these if your wiring is different.
#define DIR_TX LOW
#define DIR_RX HIGH

#define BAUDRATE 1000000

HardwareSerial DxlSerial(2);

// --- AX-12A INSTRUCTIONS ---
#define INST_PING 0x01
#define INST_READ_DATA 0x02
#define INST_WRITE_DATA 0x03
#define INST_REG_WRITE 0x04
#define INST_ACTION 0x05
#define INST_RESET 0x06

// --- HELPER BUFFERS ---
uint8_t rx_buffer[128];
char serial_buf[128];
int serial_idx = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial)
    ;

  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(DIR_PIN, DIR_RX); // Start in RX mode

  DxlSerial.begin(BAUDRATE, SERIAL_8N1, DXL_RX_PIN, DXL_TX_PIN);

  Serial.println("\n\n===================================");
  Serial.println("   AX-12A Extended Debugger v1.0   ");
  Serial.println("===================================");
  Serial.println("Type 'help' for a list of commands.");
  Serial.print("> ");
}

void setTxMode() { digitalWrite(DIR_PIN, DIR_TX); }

void setRxMode() {
  DxlSerial.flush(); // Block until all TX bytes are fully shifted out
  digitalWrite(DIR_PIN, DIR_RX);
}

// Low level send function
void sendPacket(uint8_t id, uint8_t instruction, uint8_t *params,
                uint8_t param_len) {
  uint8_t length = param_len + 2;
  uint8_t checksum = id + length + instruction;

  setTxMode();

  DxlSerial.write(0xFF);
  DxlSerial.write(0xFF);
  DxlSerial.write(id);
  DxlSerial.write(length);
  DxlSerial.write(instruction);

  for (uint8_t i = 0; i < param_len; i++) {
    DxlSerial.write(params[i]);
    checksum += params[i];
  }

  DxlSerial.write(~checksum & 0xFF);

  setRxMode();
}

// Low level read function
// Returns: Number of parameters read, or negative on error
int readPacket(uint8_t *out_buffer, uint8_t max_len, uint8_t *out_error,
               uint32_t timeout_ms = 100) {
  uint32_t start = millis();
  uint8_t state = 0;
  uint8_t id = 0, length = 0, error = 0, checksum = 0;
  uint8_t param_idx = 0;
  uint8_t calc_checksum = 0;

  while (millis() - start < timeout_ms) {
    if (DxlSerial.available()) {
      uint8_t b = DxlSerial.read();
      switch (state) {
      case 0:
        if (b == 0xFF)
          state = 1;
        break;
      case 1:
        if (b == 0xFF)
          state = 2;
        else
          state = 0;
        break;
      case 2:
        id = b;
        calc_checksum += b;
        state = 3;
        break;
      case 3:
        length = b;
        calc_checksum += b;
        state = 4;
        break;
      case 4:
        error = b;
        if (out_error)
          *out_error = error;
        calc_checksum += b;
        if (length == 2)
          state = 6; // No parameters
        else
          state = 5;
        break;
      case 5:
        if (param_idx < max_len)
          out_buffer[param_idx] = b;
        param_idx++;
        calc_checksum += b;
        if (param_idx >= length - 2)
          state = 6;
        break;
      case 6:
        checksum = b;
        calc_checksum = ~calc_checksum & 0xFF;
        if (checksum == calc_checksum) {
          return param_idx; // Success
        } else {
          return -2; // Checksum error
        }
      }
    }
  }
  return -1; // Timeout
}

void printErrorStatus(uint8_t error) {
  if (error == 0)
    return;
  Serial.print("  [ERRORS]: ");
  if (error & 0x01)
    Serial.print("InputVoltage ");
  if (error & 0x02)
    Serial.print("AngleLimit ");
  if (error & 0x04)
    Serial.print("Overheating ");
  if (error & 0x08)
    Serial.print("Range ");
  if (error & 0x10)
    Serial.print("Checksum ");
  if (error & 0x20)
    Serial.print("Overload ");
  if (error & 0x40)
    Serial.print("Instruction ");
  Serial.println();
}

// --- COMMAND IMPLEMENTATIONS ---

void cmd_ping(uint8_t id) {
  sendPacket(id, INST_PING, NULL, 0);
  uint8_t err;
  int res = readPacket(rx_buffer, sizeof(rx_buffer), &err);
  if (res >= 0) {
    Serial.printf("Pong from ID: %d\n", id);
    printErrorStatus(err);
  } else if (res == -2) {
    Serial.println("Checksum Error!");
  } else {
    Serial.println("Timeout.");
  }
}

void cmd_scan() {
  Serial.println("Scanning IDs 0-253...");
  for (int id = 0; id <= 253; id++) {
    sendPacket(id, INST_PING, NULL, 0);
    uint8_t err;
    int res = readPacket(rx_buffer, sizeof(rx_buffer), &err, 15);
    if (res >= 0) {
      Serial.printf("Found servo at ID: %d\n", id);
    }
  }
  Serial.println("Scan complete.");
}

void cmd_read(uint8_t id, uint8_t addr, uint8_t len) {
  uint8_t params[2] = {addr, len};
  sendPacket(id, INST_READ_DATA, params, 2);

  uint8_t err;
  int res = readPacket(rx_buffer, sizeof(rx_buffer), &err);
  if (res >= 0) {
    Serial.printf("Read %d bytes from addr %d:\n", res, addr);
    for (int i = 0; i < res; i++) {
      Serial.printf("  [%02d] 0x%02X (%d)\n", addr + i, rx_buffer[i],
                    rx_buffer[i]);
    }
    printErrorStatus(err);
  } else {
    Serial.println("Failed to read (timeout or err).");
  }
}

void cmd_write(uint8_t id, uint8_t addr, uint8_t val) {
  uint8_t params[2] = {addr, val};
  sendPacket(id, INST_WRITE_DATA, params, 2);

  uint8_t err;
  int res = readPacket(rx_buffer, sizeof(rx_buffer), &err);
  if (res >= 0) {
    Serial.println("Write successful.");
    printErrorStatus(err);
  } else {
    Serial.println("Write failed (timeout or err).");
  }
}

void cmd_write16(uint8_t id, uint8_t addr, uint16_t val) {
  uint8_t params[3] = {addr, (uint8_t)(val & 0xFF),
                       (uint8_t)((val >> 8) & 0xFF)};
  sendPacket(id, INST_WRITE_DATA, params, 3);

  uint8_t err;
  int res = readPacket(rx_buffer, sizeof(rx_buffer), &err);
  if (res >= 0) {
    Serial.println("Write 16-bit successful.");
    printErrorStatus(err);
  } else {
    Serial.println("Write failed.");
  }
}

void cmd_move(uint8_t id, uint16_t pos, uint16_t speed) {
  uint8_t params[5];
  params[0] = 30; // Goal position register
  params[1] = pos & 0xFF;
  params[2] = (pos >> 8) & 0xFF;
  params[3] = speed & 0xFF;
  params[4] = (speed >> 8) & 0xFF;

  sendPacket(id, INST_WRITE_DATA, params, 5);
  uint8_t err;
  readPacket(rx_buffer, sizeof(rx_buffer), &err);
  Serial.println("Move command sent.");
}

void cmd_led(uint8_t id, uint8_t state) { cmd_write(id, 25, state ? 1 : 0); }

void cmd_reset(uint8_t id) {
  Serial.printf("Factory resetting ID %d... (This will reset ID to 1 and baud "
                "to 1000000)\n",
                id);
  sendPacket(id, INST_RESET, NULL, 0);
  uint8_t err;
  readPacket(rx_buffer, sizeof(rx_buffer), &err);
  Serial.println("Reset command sent.");
}

void cmd_status(uint8_t id) {
  // Read Temperature (43), Voltage (42), Load (40)
  Serial.printf("--- Status ID %d ---\n", id);

  // Volt
  uint8_t p_volt[2] = {42, 1};
  sendPacket(id, INST_READ_DATA, p_volt, 2);
  uint8_t err;
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) >= 0) {
    Serial.printf("Voltage: %.1f V\n", (float)rx_buffer[0] / 10.0f);
  }

  // Temp
  uint8_t p_temp[2] = {43, 1};
  sendPacket(id, INST_READ_DATA, p_temp, 2);
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) >= 0) {
    Serial.printf("Temperature: %d C\n", rx_buffer[0]);
  }

  // Load
  uint8_t p_load[2] = {40, 2};
  sendPacket(id, INST_READ_DATA, p_load, 2);
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) == 2) {
    uint16_t load = rx_buffer[0] | (rx_buffer[1] << 8);
    bool ccw = (load & 0x400) > 0;
    load = load & 0x3FF;
    Serial.printf("Load: %d (%s)\n", load, ccw ? "CCW" : "CW");
  }

  // Pos
  uint8_t p_pos[2] = {36, 2};
  sendPacket(id, INST_READ_DATA, p_pos, 2);
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) == 2) {
    uint16_t pos = rx_buffer[0] | (rx_buffer[1] << 8);
    Serial.printf("Present Position: %d\n", pos);
  }
}

void cmd_json_scan() {
  Serial.print("{\"type\":\"scan\",\"found\":[");
  bool first = true;
  for (int id = 0; id <= 253; id++) {
    sendPacket(id, INST_PING, NULL, 0);
    uint8_t err;
    int res = readPacket(rx_buffer, sizeof(rx_buffer), &err, 15);
    if (res >= 0) {
      if (!first) Serial.print(",");
      Serial.print(id);
      first = false;
    }
  }
  Serial.println("]}");
}

void cmd_json_status(uint8_t id) {
  // Volt
  float volt = 0;
  uint8_t p_volt[2] = {42, 1};
  sendPacket(id, INST_READ_DATA, p_volt, 2);
  uint8_t err;
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) >= 0) {
    volt = (float)rx_buffer[0] / 10.0f;
  }

  // Temp
  int temp = 0;
  uint8_t p_temp[2] = {43, 1};
  sendPacket(id, INST_READ_DATA, p_temp, 2);
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) >= 0) {
    temp = rx_buffer[0];
  }

  // Load
  int load_val = 0;
  bool ccw = false;
  uint8_t p_load[2] = {40, 2};
  sendPacket(id, INST_READ_DATA, p_load, 2);
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) == 2) {
    uint16_t load = rx_buffer[0] | (rx_buffer[1] << 8);
    ccw = (load & 0x400) > 0;
    load_val = load & 0x3FF;
  }

  // Pos
  int pos_val = 0;
  uint8_t p_pos[2] = {36, 2};
  sendPacket(id, INST_READ_DATA, p_pos, 2);
  if (readPacket(rx_buffer, sizeof(rx_buffer), &err) == 2) {
    pos_val = rx_buffer[0] | (rx_buffer[1] << 8);
  }

  Serial.printf("{\"type\":\"status\",\"id\":%d,\"voltage\":%.1f,\"temp\":%d,\"load\":%d,\"load_dir\":\"%s\",\"pos\":%d}\n",
                id, volt, temp, load_val, ccw ? "CCW" : "CW", pos_val);
}

void cmd_dump(uint8_t id) {
  Serial.printf("{\"type\":\"dump\",\"id\":%d,\"eeprom\":[", id);
  // Read EEPROM 0-23
  uint8_t p_eeprom[2] = {0, 24};
  sendPacket(id, INST_READ_DATA, p_eeprom, 2);
  uint8_t err;
  int res = readPacket(rx_buffer, sizeof(rx_buffer), &err);
  if (res == 24) {
    for (int i=0; i<24; i++) {
      Serial.print(rx_buffer[i]);
      if (i < 23) Serial.print(",");
    }
  }
  Serial.print("],\"ram\":[");
  // Read RAM 24-49 (26 bytes)
  uint8_t p_ram[2] = {24, 26};
  sendPacket(id, INST_READ_DATA, p_ram, 2);
  res = readPacket(rx_buffer, sizeof(rx_buffer), &err);
  if (res == 26) {
    for (int i=0; i<26; i++) {
      Serial.print(rx_buffer[i]);
      if (i < 25) Serial.print(",");
    }
  }
  Serial.println("]}");
}

// --- PARSER ---
void parseCommand(char *cmdLine) {
  char *cmd = strtok(cmdLine, " ");
  if (!cmd)
    return;

  if (strcmp(cmd, "help") == 0) {
    Serial.println("Available commands:");
    Serial.println("  ping <id>                  - Ping servo");
    Serial.println("  scan                       - Scan all IDs 0-253");
    Serial.println("  read <id> <addr> <len>     - Read registers");
    Serial.println("  write <id> <addr> <val>    - Write 8-bit register");
    Serial.println("  write16 <id> <addr> <val>  - Write 16-bit register");
    Serial.println("  move <id> <pos> <speed>    - Move servo");
    Serial.println("  led <id> <1/0>             - Toggle LED");
    Serial.println("  status <id>                - Read volt, temp, load, pos");
    Serial.println("  reset <id>                 - Factory reset servo");
    Serial.println("  jscan                      - Scan returning JSON");
    Serial.println("  jstatus <id>               - Status returning JSON");
    Serial.println("  dump <id>                  - Read EEPROM/RAM as JSON");
  } else if (strcmp(cmd, "ping") == 0) {
    int id = atoi(strtok(NULL, " "));
    cmd_ping((uint8_t)id);
  } else if (strcmp(cmd, "scan") == 0) {
    cmd_scan();
  } else if (strcmp(cmd, "read") == 0) {
    int id = atoi(strtok(NULL, " "));
    int addr = atoi(strtok(NULL, " "));
    int len = atoi(strtok(NULL, " "));
    cmd_read((uint8_t)id, (uint8_t)addr, (uint8_t)len);
  } else if (strcmp(cmd, "write") == 0) {
    int id = atoi(strtok(NULL, " "));
    int addr = atoi(strtok(NULL, " "));
    int val = atoi(strtok(NULL, " "));
    cmd_write((uint8_t)id, (uint8_t)addr, (uint8_t)val);
  } else if (strcmp(cmd, "write16") == 0) {
    int id = atoi(strtok(NULL, " "));
    int addr = atoi(strtok(NULL, " "));
    int val = atoi(strtok(NULL, " "));
    cmd_write16((uint8_t)id, (uint8_t)addr, (uint16_t)val);
  } else if (strcmp(cmd, "move") == 0) {
    int id = atoi(strtok(NULL, " "));
    int pos = atoi(strtok(NULL, " "));
    int speed = atoi(strtok(NULL, " "));
    cmd_move((uint8_t)id, (uint16_t)pos, (uint16_t)speed);
  } else if (strcmp(cmd, "led") == 0) {
    int id = atoi(strtok(NULL, " "));
    int val = atoi(strtok(NULL, " "));
    cmd_led((uint8_t)id, (uint8_t)val);
  } else if (strcmp(cmd, "status") == 0) {
    int id = atoi(strtok(NULL, " "));
    cmd_status((uint8_t)id);
  } else if (strcmp(cmd, "reset") == 0) {
    int id = atoi(strtok(NULL, " "));
    cmd_reset((uint8_t)id);
  } else if (strcmp(cmd, "jscan") == 0) {
    cmd_json_scan();
  } else if (strcmp(cmd, "jstatus") == 0) {
    int id = atoi(strtok(NULL, " "));
    cmd_json_status((uint8_t)id);
  } else if (strcmp(cmd, "dump") == 0) {
    int id = atoi(strtok(NULL, " "));
    cmd_dump((uint8_t)id);
  } else {
    Serial.println("Unknown command. Type 'help'.");
  }
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (serial_idx > 0) {
        serial_buf[serial_idx] = '\0';
        Serial.println();
        parseCommand(serial_buf);
        serial_idx = 0;
        Serial.print("> ");
      }
    } else {
      if (serial_idx < (int)sizeof(serial_buf) - 1) {
        serial_buf[serial_idx++] = c;
        Serial.print(c); // Echo
      }
    }
  }
}
