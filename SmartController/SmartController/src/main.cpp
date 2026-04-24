#include "Arduino.h"
#include "ax12a.h"

#define RX_PIN      16 
#define TX_PIN      17
#define BaudRate    57600ul
#define ID          254 // 254 = iedereen, maar probeer ook '1' als je weet dat dat het ID is

void setup() {
  Serial.begin(115200); // Voor je computer
  Serial2.begin(BaudRate, SERIAL_8N1, RX_PIN, TX_PIN);
  ax12a.begin(BaudRate, RX_PIN, &Serial2);
  Serial.println("Systeem gestart. Proberen LED te schakelen...");
}

void loop() {
  Serial.println("LED AAN");
  ax12a.ledStatus(ID, 1);
  // Als setLedStatus niet werkt, probeer: ax12a.ledStatus(ID, 1);
  delay(500);

  Serial.println("LED UIT");
  ax12a.ledStatus(ID, 1);
  delay(500);
}