/*
  Arduino Nano joystick/button reader for Raspberry Pi over TTL UART serial.

  Important:
  - The pictured USB breakout exposes USB VBUS, D-, D+, and GND. It is not a
    UART/GPIO adapter, so do not connect D-/D+ to Raspberry Pi GPIO pins.
  - For Raspberry Pi GPIO communication, use the Pi UART pins instead:
      Nano D1 / TX -> Raspberry Pi GPIO15 / RXD0 / physical pin 10
      Nano D0 / RX <- Raspberry Pi GPIO14 / TXD0 / physical pin 8
      Nano GND     -> Raspberry Pi GND / physical pin 6
  - Arduino Nano TX is 5 V logic. Raspberry Pi GPIO is 3.3 V only. Put a logic
    level shifter or resistor divider between Nano D1/TX and Pi GPIO15/RX.
    Pi TX at 3.3 V can normally drive Nano RX directly.
  - Power the Nano separately or from the Pi 5 V pin only if your total current
    draw is safe for the Pi. Always connect GND between the Nano and Pi.

  Wiring assumed:
  - Joystick 1 X wiper -> A0
  - Joystick 1 Y wiper -> A1
  - Joystick 2 X wiper -> A2
  - Joystick 2 Y wiper -> A3
  - Switch1   -> D3
  - Switch2   -> D4
  - Switch3   -> D5
  - Switch4   -> D6
  - Switch1_2 -> D8
  - Switch2_2 -> D9
  - Switch3_2 -> D11
  - Switch4_2 -> D2
  - Passive Buzzer -> D13 (Positive terminal to D13, negative to GND)
  - Other side of each pushbutton -> GND

  The sketch enables INPUT_PULLUP for the buttons, so:
  - Pressed = LOW on the pin
  - Released = HIGH on the pin

  Serial output format, one line per sample:
  J,<x1>,<y1>,<x2>,<y2>,<buttonBits>

  Joystick values are normalized from -1.000 to 1.000.

  buttonBits is an 8-bit mask in decimal:
  - bit 0 = D3 / Switch1
  - bit 1 = D4 / Switch2
  - bit 2 = D5 / Switch3
  - bit 3 = D6 / Switch4
  - bit 4 = D8 / Switch1_2
  - bit 5 = D9 / Switch2_2
  - bit 6 = D11 / Switch3_2
  - bit 7 = D2 / Switch4_2

  A pressed button sets its bit to 1.
*/
#include <Arduino.h>

const unsigned long BAUD_RATE = 115200;
const unsigned long SAMPLE_INTERVAL_MS = 20;  // 50 samples per second
const unsigned long DEBOUNCE_MS = 8;

const int JOYSTICK_MIN = 324;
const int JOYSTICK_CENTER = 504;
const int JOYSTICK_MAX = 702;

const byte JOYSTICK_PINS[4] = {A0, A1, A2, A3};
const byte BUTTON_PINS[8] = {3, 4, 5, 6, 8, 9, 11, 2};

// Passive Buzzer Configuration
const byte BUZZER_PIN = 13;
// Unique frequencies (Hz) for each button (C5, D5, E5, F5, G5, A5, B5, C6)
const unsigned int BUTTON_TONES[8] = {523, 587, 659, 698, 784, 880, 988, 1047}; 
const unsigned long TONE_DURATION_MS = 70; // Short, snappy blip

bool buttonStablePressed[8] = {false};
bool buttonLastRawPressed[8] = {false};
unsigned long buttonLastChangeMs[8] = {0};

unsigned long lastSampleMs = 0;

void updateButtons();
void sendControllerState();
float readNormalizedJoystick(byte pin);

void setup() {
  Serial.begin(BAUD_RATE);
  
  pinMode(BUZZER_PIN, OUTPUT);

  for (byte i = 0; i < 8; i++) {
    pinMode(BUTTON_PINS[i], INPUT_PULLUP);
    bool pressed = digitalRead(BUTTON_PINS[i]) == LOW;
    buttonStablePressed[i] = pressed;
    buttonLastRawPressed[i] = pressed;
    buttonLastChangeMs[i] = millis();
  }
}

void loop() {
  updateButtons();

  unsigned long now = millis();
  if (now - lastSampleMs >= SAMPLE_INTERVAL_MS) {
    lastSampleMs = now;
    sendControllerState();
  }
}

void updateButtons() {
  unsigned long now = millis();

  for (byte i = 0; i < 8; i++) {
    bool rawPressed = digitalRead(BUTTON_PINS[i]) == LOW;

    if (rawPressed != buttonLastRawPressed[i]) {
      buttonLastRawPressed[i] = rawPressed;
      buttonLastChangeMs[i] = now;
    }

    if ((now - buttonLastChangeMs[i]) >= DEBOUNCE_MS) {
      // Check if the state actually changed to "pressed" to trigger the sound effect
      if (rawPressed && !buttonStablePressed[i]) {
        tone(BUZZER_PIN, BUTTON_TONES[i], TONE_DURATION_MS);
      }
      buttonStablePressed[i] = rawPressed;
    }
  }
}

void sendControllerState() {
  float x1 = readNormalizedJoystick(JOYSTICK_PINS[0]);
  float y1 = readNormalizedJoystick(JOYSTICK_PINS[1]);
  float x2 = readNormalizedJoystick(JOYSTICK_PINS[2]);
  float y2 = readNormalizedJoystick(JOYSTICK_PINS[3]);

  byte buttonBits = 0;
  for (byte i = 0; i < 8; i++) {
    if (buttonStablePressed[i]) {
      buttonBits |= (1 << i);
    }
  }

  Serial.print("J,");
  Serial.print(x1, 3);
  Serial.print(',');
  Serial.print(y1, 3);
  Serial.print(',');
  Serial.print(x2, 3);
  Serial.print(',');
  Serial.print(y2, 3);
  Serial.print(',');
  Serial.println(buttonBits);
}

float readNormalizedJoystick(byte pin) {
  int raw = analogRead(pin);

  if (raw >= JOYSTICK_CENTER) {
    float value = (float)(raw - JOYSTICK_CENTER) / (float)(JOYSTICK_MAX - JOYSTICK_CENTER);
    return constrain(value, 0.0, 1.0);
  }

  float value = (float)(raw - JOYSTICK_CENTER) / (float)(JOYSTICK_CENTER - JOYSTICK_MIN);
  return constrain(value, -1.0, 0.0);
}