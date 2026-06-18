# Korte Analyse Missende Bestanden en Aanpassingen

## Conclusie

De basis van het elektrotechnische TOP staat er goed in: blokschema's, schema's, PCB-layouts, BOM, analyses, communicatie/OSI, softwarebestanden, validatierapport en foto-/videobewijs zijn aanwezig. Wat nog mist zit vooral in compleetheid, definitieve bewijsvoering en koppeling tussen documenten.

## Bestanden Die Nog Missen

1. **PCB-bronbestanden**
   - Er zijn PDF-exports van schema's en layouts, maar geen ontwerpbronbestanden gevonden.
   - Toevoegen als beschikbaar: KiCad, Altium, EasyEDA, Fritzing of andere projectbestanden.

2. **Complete BOM's**
   - Er is een BOM voor het robot/hoofdbord, maar nog geen aantoonbaar complete BOM voor:
     - controller-hoofdmodule;
     - joystickmodule;
     - kabels en connectoren;
     - accu's, voedingen, display, Raspberry Pi's, servo's en sensoren.

3. **Controller-softwaredocumentatie**
   - Er staan `main.cpp` bestanden voor Smartcontroller V1 en V2.
   - Nog missen: installatie-instructies, startinstructies, dependencies, gebruikte libraries, uploadmethode en uitleg hoe de controllerdata naar de Raspberry Pi/ROS-kant gaat.

4. **Raspberry Pi / ROS-controllercode**
   - De Arduino/Nano-code is aanwezig, maar de software die de seriele controllerdata verwerkt op de Raspberry Pi en omzet naar robotcommando's/ROS-topics is niet zichtbaar.
   - Als die code bestaat, toevoegen aan `05_Controller_Software`.

5. **Meetresultaten als bewijs**
   - Het validatierapport is aanwezig, maar er moeten nog concrete meettabellen en bewijsbestanden bij:
     - gemeten 11,1 V, 5 V en 3,3 V;
     - stroomverbruik in rust en onder belasting;
     - UART/I2C/servo-bus signalen;
     - oscilloscoopbeelden of foto's van metingen;
     - pass/fail per testpunt.

6. **Controller-accuberekening**
   - Robotstroomverbruik is aanwezig.
   - Een aparte berekening voor controllerverbruik en accuduur moet nog worden toegevoegd of expliciet worden uitgewerkt.

## Wat Sowieso Moet Worden Aangepast

1. **Blokschema's nalopen**
   - Voeg per verbinding toe: spanning, signaalrichting, protocol, medium, grootheid en eenheid.
   - Vooral belangrijk voor Wi-Fi/ROS 2, UART, I2C, servo-bus en voedingslijnen.

2. **BOM uitbreiden**
   - Maak de BOM beoordelaar-proof: niet alleen PCB-componenten, maar ook modules, kabels, connectoren, voedingen, display, Pi's, sensoren en servo's.

3. **Validatierapport concreter maken**
   - Voeg echte meetwaarden toe in plaats van alleen beschrijvingen.
   - Koppel testpunten aan: doel, verwacht, gemeten, resultaat en bewijsfoto.

4. **Softwaremap aanvullen**
   - `05_Controller_Software/README.md` moet concreet worden:
     - hoe compileer/upload je de code;
     - welke hardware hoort erbij;
     - welke seriele output wordt gebruikt;
     - hoe dit wordt omgezet naar robotcommando's.

5. **Communicatieprotocol controleren met echte code**
   - Het OSI/communicatiedocument is aanwezig, maar moet worden vergeleken met de uiteindelijke software.
   - Controleer of topicnamen, joystickmapping, heartbeat/failsafe en berichtfrequenties overeenkomen met de implementatie.

6. **Bewijsbestanden beter labelen**
   - Er zijn foto's en video's aanwezig, maar geef ze waar nodig duidelijke namen of voeg een korte toelichting toe.
   - Vooral bij meetopstellingen, UART-collision, videostream en hoofdbordfoto's.

7. **Definitieve versies markeren**
   - Controleer of schema's, layouts en documenten datum, versie en status bevatten.
   - Markeer concepten duidelijk of zet alleen definitieve exports in de TOP.

## Hoogste Prioriteit

1. BOM compleet maken.
2. Meetresultaten en testbewijs toevoegen.
3. Controller-softwaredocumentatie en Raspberry Pi/ROS-code toevoegen.
4. Blokschema's technisch volledig labelen.
5. Communicatieprotocol afstemmen met de werkende software.
