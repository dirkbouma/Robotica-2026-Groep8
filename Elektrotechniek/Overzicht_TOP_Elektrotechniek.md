# Overzicht Technisch Ontwerp Portfolio - Elektrotechniek

Gebaseerd op de projecthandleiding Robotica 2025-2026, Bijlage 2 Elektrotechniek, en de bestanden die nu in de map `Elektrotechniek` staan.

## Samenvatting

Er is al veel gemaakt voor het elektrotechnische deel: drie blokschema's, schema's en PCB-layouts voor hoofdbord en controller, een BOM, controlleranalyse, stroomverbruiksanalyse, communicatie/OSI-documentatie en een hardwarevalidatierapport.

De mapindeling is toegepast. Gebruik `00_Index_README.md` als ingang tot het portfolio en `TOP_Checklist_Elektrotechniek.md` als afvinkbare werkchecklist.

De grootste open punten zijn:

1. Embedded softwaredocumentatie van de remote controller aanvullen.
2. Complete stuklijsten maken voor alle E-onderdelen, niet alleen het robot/hoofdbord.
3. Aansluitschema's uitbreiden naar het volledige systeem.
4. Blokschema's nalopen op alle gevraagde details: spanningsdomeinen, protocollen, commando's, medium en I/O met grootheden en eenheden.
5. Meetresultaten/testbewijs aanvullen met concrete screenshots, meetwaarden en verwijzing naar testpunten.
6. Controleren of de officiele TOP-map of gedeelde link naar deze elektrotechniek-structuur verwijst.

## Checklist Per Eis

| Eis uit handleiding | Status | Wat is er al | Nog maken / aanvullen |
|---|---:|---|---|
| Blokschema robot als geheel inclusief controller | Bijna klaar | `01_Blokschemas/Blokschema van robot als geheel (inclusief controller)/Blokschema_Controller_Robot.drawio` | Controleren of alle verbindingen medium, protocol, spanning, richting en eenheden hebben. Voeg commando's/berichttypes toe waar nodig. |
| Blokschema interne werking robot | Bijna klaar | `01_Blokschemas/Blokschema Interne werking robot/BlokschemaInterneRobot.drawio` | I/O-signalen vollediger labelen: UART, I2C, voeding, logicaniveaus, stromen en spanningen. |
| Blokschema interne werking controller | Bijna klaar | `01_Blokschemas/Blokschema Controller/Internewerkingcontroller.drawio` | Controleren op spanningsdomeinen, accuvoeding/regelaar, joystick-signalen, display-interface en Wi-Fi/protocol. |
| Alle elektrische schema's | Aanwezig | Schema hoofdbord, hoofdmodule, joystickmodule en breadboard 74LS241 als PDF | Bronbestanden toevoegen indien beschikbaar, bijvoorbeeld KiCad/Altium/Fritzing. PDF alleen is minder sterk als ontwerpportfolio. |
| Alle PCB-layouts | Aanwezig | Layout hoofdbord, controller-hoofdmodule en joystickmodule als PDF | Ook bronbestanden toevoegen indien beschikbaar. Controleer of versienummers/datum/finale status op de exports staan. |
| Complete stuklijsten | Deels klaar | `03_Stuklijsten_BOM/Stuklijst BOM.xlsx` met sheet `Robotica-8-Robotpcb` | BOM's toevoegen voor controller-hoofdmodule, joystickmodule, kabels/connectoren, accu, voedingen, display, Raspberry Pi's, servo's/sensoren en overige koopdelen. |
| Aansluitschema's | Aanwezig | `02_Schemas_PCB_Layouts/PCB hoofdbord/Aansluitschema Hoofdbord.png` en `02_Schemas_PCB_Layouts/Systeem_Aansluitschema.md` | Connectornamen en exacte pinnummers nog vergelijken met definitieve PCB-schema's/layouts. |
| Stroomverbruik robot | Aanwezig | `04_Analyses_Berekeningen/Stroomverbruik Robot.docx` | Controleer of aannames en bronnen van componentstromen duidelijk zijn. Voeg worst-case en normale gebruiksduur toe als dat nog niet concreet genoeg is. |
| Accucapaciteit | Aanwezig voor robot, onduidelijk voor controller | `04_Analyses_Berekeningen/Stroomverbruik Robot.docx`, controlleranalyse noemt accucapaciteit | Controller-accuberekening apart concretiseren: belasting Raspberry Pi/display/joysticks, gekozen batterij, verwachte gebruiksduur. |
| Keuzeverantwoording componenten/protocollen | Aanwezig | `04_Analyses_Berekeningen/Controller_analyse_ontwerp.docx` en `04_Analyses_Berekeningen/Plan Van Aanpak Controller.docx` | Zorg dat definitieve keuzes terugkomen: gekozen Pi, Wi-Fi/ROS2/DDS, joystick/display, accu, AX-12A, AS5600, 74LS241, buck converter. |
| Embedded software remote controller | Deels aanwezig | `05_Controller_Software/Smartcontroller V1 - ESP+ESPNOW/main.cpp`, `05_Controller_Software/Smartcontroller V2 - PI4+Arduino nano/main.cpp` en `05_Controller_Software/README.md` | README aanvullen met starten/installeren, dependency's, bestandsstructuur, communicatie-topics/commando's en automatisch gegenereerde documentatie of duidelijke comments. |
| Werkende draadloze remote controller met eigen PCB | Deels aantoonbaar | Controller-PCB schema/layout, controllerfoto's, plan/analyse | Voeg foto's/video of korte testbeschrijving toe waarin draadloze besturing werkt. Verwijs naar de eigen PCB's en testresultaten. |
| Design for testability | Aanwezig | `06_Testen_Verificatie_Validatie/Hardware Validatie en Testrapport.docx` noemt testpunten | Voeg schema/layout-markering van testpunten toe en koppel elk testpunt aan wat daar gemeten moet worden. |
| Meetresultaten en validatie | Deels klaar | Hardwarevalidatierapport met meetapparatuur en meetresultatenhoofdstuk | Aanvullen met echte meettabellen, oscilloscoopbeelden/foto's, pass/fail per test en conclusie per eis. |
| Communicatieprotocol/commando's/OSI | Aanwezig | `04_Analyses_Berekeningen/Comunicatie en OSI laag.docx` | Controleer of dit de definitieve versie is en of commando's/topics overeenkomen met de controllercode. |
| TOP toegankelijk en navolgbaar | Geordend | `00_Index_README.md`, `TOP_Checklist_Elektrotechniek.md` en genummerde mappen | Plaats deze map in de officiele TOP of voeg in `General/TOP` een duidelijke verwijzing/index toe. Maak versiebeheer/naamgeving consistent. |

## Prioriteiten

### Moet Eerst

- Vul de embedded controller-softwaredocumentatie aan.
- Maak de BOM compleet voor robot, controller, kabels, connectoren en koopdelen.
- Werk het validatierapport af met concrete meetwaarden en bewijs.
- Controleer het communicatieprotocol-document met de uiteindelijke software en testresultaten.

### Daarna Netjes Maken

- Exporteer definitieve schema's en layouts met datum, versie en status.
- Voeg bronbestanden van schema's en PCB's toe als die beschikbaar zijn.
- Gebruik `00_Index_README.md` en `TOP_Checklist_Elektrotechniek.md` als ingang voor de beoordelaar.
- Controleer of de blokschema's overal eenheden, spanningen, richtingen en protocollen tonen.

## Toegepaste Mapindeling Voor TOP

```text
Elektrotechniek/
  00_Index_README.md
  TOP_Checklist_Elektrotechniek.md
  Overzicht_TOP_Elektrotechniek.md
  01_Blokschemas/
  02_Schemas_PCB_Layouts/
  03_Stuklijsten_BOM/
  04_Analyses_Berekeningen/
  05_Controller_Software/
  06_Testen_Verificatie_Validatie/
  07_Fotos_Videos_Bewijs/
```

## Korte Beoordelaarscheck

Een expertbeoordelaar moet in maximaal enkele minuten kunnen zien:

- welke E-onderdelen ontworpen zijn;
- waarom componenten en protocollen gekozen zijn;
- hoe voeding, communicatie en signalen lopen;
- welke PCB's en aansluitingen gebouwd zijn;
- welke code de controller draait;
- welke metingen aantonen dat het werkt;
- waar de definitieve bestanden staan.
