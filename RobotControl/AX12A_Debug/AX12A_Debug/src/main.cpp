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

void setup() {
  Serial.begin(115200); // To your computer monitor
  Serial2.begin(1000000); // Listening to the Raspberry Pi
  Serial.println("ESP32 Sniffer Ready...");
}

void loop() {
  if (Serial2.available()) {
    byte incomingByte = Serial2.read();
    // Print the raw byte as a HEX value (e.g., FF)
    Serial.print(incomingByte, HEX); 
    Serial.print(" ");
  }
}