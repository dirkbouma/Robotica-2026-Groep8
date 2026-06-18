# Afvinkbare Checklist TOP Elektrotechniek

Gebruik deze checklist om het elektrotechnische Technisch Ontwerp Portfolio af te ronden. Vink items af door `[ ]` te veranderen naar `[x]`.

## 1. Blokschema's

- [x] Blokschema van de robot als geheel inclusief controller is aanwezig.
  - Bestand: `01_Blokschemas/Blokschema van robot als geheel (inclusief controller)/Blokschema_Controller_Robot.drawio`
- [x] Blokschema van de interne werking van de robot is aanwezig.
  - Bestand: `01_Blokschemas/Blokschema Interne werking robot/BlokschemaInterneRobot.drawio`
- [x] Blokschema van de interne werking van de controller is aanwezig.
  - Bestand: `01_Blokschemas/Blokschema Controller/Internewerkingcontroller.drawio`
- [ ] Controleer of alle blokschema's spanningsdomeinen tonen.
- [ ] Controleer of alle blokschema's communicatieprotocollen tonen.
- [ ] Controleer of alle blokschema's commando's of berichttypes tonen.
- [ ] Controleer of alle blokschema's medium/richting van communicatie tonen.
- [ ] Controleer of alle in- en outputs grootheden en eenheden hebben.

## 2. Elektrische Schema's en PCB-layouts

- [x] Schema hoofdbord is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB hoofdbord/Schema_Hoofdbord.pdf`
- [x] Layout hoofdbord is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB hoofdbord/Layout_Hoofdbord.pdf`
- [x] Aansluitschema hoofdbord is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB hoofdbord/Aansluitschema Hoofdbord.png`
- [x] Schema controller-hoofdmodule is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB's Controller/Hoofdmodule/Schema_Hoofdmodule.pdf`
- [x] Layout controller-hoofdmodule is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB's Controller/Hoofdmodule/Layout_Hoofdmodule.pdf`
- [x] Schema joystickmodule is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB's Controller/JoystickModule/Schema_JoystickModule.pdf`
- [x] Layout joystickmodule is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/PCB's Controller/JoystickModule/Layout_JoystickModule.pdf`
- [x] Breadboard/74LS241-schema is aanwezig.
  - Bestand: `02_Schemas_PCB_Layouts/Breadboard 74LS241/Breadboard_74LS241.pdf`
- [ ] Voeg bronbestanden toe als die beschikbaar zijn, bijvoorbeeld KiCad/Altium/Fritzing-projectbestanden.
- [ ] Controleer of alle schema-exports datum, versie en definitieve status bevatten.
- [x] Maak of controleer een volledig systeem-aansluitschema: accu, hoofdbord, Raspberry Pi, servo's, encoders, controller en display.
  - Bestand: `02_Schemas_PCB_Layouts/Systeem_Aansluitschema.md`

## 3. Stuklijsten en BOM

- [x] Er is een BOM-bestand aanwezig.
  - Bestand: `03_Stuklijsten_BOM/Stuklijst BOM.xlsx`
- [ ] Controleer of de BOM het robot/hoofdbord volledig dekt.
- [ ] Voeg controller-hoofdmodule toe aan de BOM.
- [ ] Voeg joystickmodule toe aan de BOM.
- [ ] Voeg kabels en connectoren toe aan de BOM.
- [ ] Voeg accu's, voedingen, display, Raspberry Pi's, servo's en sensoren toe aan de BOM.
- [ ] Controleer aantallen, footprints, bestelcodes en opmerkingen.

## 4. Analyses en Berekeningen

- [x] Controlleranalyse en keuzeverantwoording is aanwezig.
  - Bestand: `04_Analyses_Berekeningen/Controller_analyse_ontwerp.docx`
- [x] Plan van aanpak controller is aanwezig.
  - Bestand: `04_Analyses_Berekeningen/Plan Van Aanpak Controller.docx`
- [x] Stroomverbruik robot is aanwezig.
  - Bestand: `04_Analyses_Berekeningen/Stroomverbruik Robot.docx`
- [x] Communicatieprotocol/commando's/OSI-document is aanwezig.
  - Bestand: `04_Analyses_Berekeningen/Comunicatie en OSI laag.docx`
- [ ] Controleer of de accucapaciteit van de robot concreet berekend is.
- [ ] Voeg of controleer een aparte controller-accuberekening.
- [ ] Controleer of definitieve keuzes voor Wi-Fi/ROS 2/DDS, Raspberry Pi, joysticks, display, AX-12A, AS5600, 74LS241 en voeding duidelijk terugkomen.
- [ ] Controleer of bronnen/aannames voor stroomverbruik en datasnelheden genoemd zijn.

## 5. Embedded Software Remote Controller

- [x] Voeg broncode van de remote controller toe aan `05_Controller_Software`.
  - Bestand: `05_Controller_Software/Smartcontroller V1 - ESP+ESPNOW/main.cpp`
  - Bestand: `05_Controller_Software/Smartcontroller V2 - PI4+Arduino nano/main.cpp`
- [x] README-bestand voor controller-software is aanwezig.
  - Bestand: `05_Controller_Software/README.md`
- [ ] Vul de README aan met installatie- en startinstructies.
- [ ] Beschrijf dependencies, bijvoorbeeld ROS 2, Python-packages, PyQt/PySide of rosbridge.
- [ ] Documenteer de topicnamen, commando's en joystickmapping bij de code.
- [ ] Voeg automatisch gegenereerde documentatie toe of zorg voor passend commentaar in de code.
- [ ] Voeg bewijs toe dat de controller draadloos met de robot communiceert.

## 6. Testen, Verificatie en Validatie

- [x] Hardwarevalidatie- en testrapport is aanwezig.
  - Bestand: `06_Testen_Verificatie_Validatie/Hardware Validatie en Testrapport.docx`
- [ ] Voeg concrete meetwaarden toe voor voedingsspanningen.
- [ ] Voeg concrete meetwaarden toe voor stroomverbruik.
- [ ] Voeg concrete meetwaarden of screenshots toe voor communicatie-/datasignalen.
- [ ] Voeg foto's of oscilloscoopbeelden van testpunten toe.
- [ ] Koppel elk testpunt aan doel, verwachte waarde, gemeten waarde en pass/fail.
- [ ] Test en documenteer heartbeat/failsafe bij verbindingsverlies.
- [ ] Test en documenteer videostream/telemetrie/joystickdata via ROS 2.

## 7. Foto's, Video's en Bewijs

- [x] Foto's van controller V1 zijn aanwezig.
  - Map: `07_Fotos_Videos_Bewijs/Controller V1 Fotos`
- [x] Foto's van controller V2 zijn aanwezig.
  - Map: `07_Fotos_Videos_Bewijs/Controller V2 Fotos`
- [ ] Voeg foto's toe van het hoofdbord in de robot.
- [ ] Voeg foto's toe van meetopstellingen.
- [ ] Voeg eventueel korte testvideo's toe van draadloze besturing en failsafe.
- [ ] Geef foto's duidelijke namen of voeg een korte toelichting toe.

## 8. Eindcontrole Voor Beoordelaar

- [x] TOP-map heeft een duidelijke genummerde structuur.
- [x] Er is een indexbestand aanwezig.
  - Bestand: `README.md`
- [x] Er is een afvinkbare checklist aanwezig.
  - Bestand: `TOP_Checklist_Elektrotechniek.md`
- [ ] Controleer of alle links/paden in documenten nog kloppen na de herindeling.
- [ ] Zet definitieve versies in de mappen en verwijder concepten of markeer ze duidelijk als concept.
- [ ] Controleer of de officiële TOP-map of gedeelde link naar deze structuur verwijst.
