# Project Robotica 2026 - Autonoom aardbeien plukken

Welkom bij de centrale software-repository voor de autonome aardbeienpluk-robot van **groep 8**. In deze repository staat alle broncode voor het project zoals de AI-aardbeiherkenning tot de hardware-aansturing en de zelfgebouwde afstandsbediening.

## Mappenstructuur

Het project is opgedeeld in drie hoofdmappen om de code overzichtelijk te houden:

* **`/SmartController`**
  * Bevat de C++ code voor de zelfontworpen ESP32 remote controller.
  * *Techniek:* PlatformIO, ESP-NOW protocol, OLED I2C, Encoder input.
* **`/Robot_Control`**
  * De hoofdlogica van de robotarm en de aansturing van de AX12A servomotoren.
  * *Techniek:* Raspberry Pi / ESP32, Kinematica, State Machine.
* **`/Vision_AI`**
  * De software voor de DEBO CAM om (rijpe) aardbeien te herkennen en coördinaten te berekenen.
  * *Techniek:* Python, OpenCV.

## Getting Started

### 1. Smart Controller (ESP32)
We gebruiken **PlatformIO** om gedoe met libraries te voorkomen. 
1. Installeer [Visual Studio Code](https://code.visualstudio.com/) en de [PlatformIO extensie](https://platformio.org/).
2. Clone deze repository
3. Ga in VS Code naar *PIO Home* -> *Open Project* en selecteer de map `SmartController`.
4. PlatformIO downloadt nu automatisch alle benodigde libraries en board-instellingen.
5. Klik op Build in de onderste balk om de code te compileren.

### 2. Vision / AI


## Team
* **TBD ** - AI & Vision (ICT)
* **TBD** - Robot Logica & Servo's (ICT / ET)
* **Dirk Bouma** - Smart Controller & Communicatie (ET)
* **Daan Smit** - Smart Controller & Communicatie (ET)
---
*Dit project is onderdeel van de NHL Stenden / WUR module: Interdisciplinair Project Robotica 2026.*
