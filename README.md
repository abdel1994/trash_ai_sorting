# Afvalscheiding met AI, MQTT, Terraform en Ansible

Dit project is onderdeel van een challenge rond afvalscheiding met behulp van AI en computer vision. Het doel van dit project is nog niet om een volledig werkend eindproduct voor automatische afvalscheiding op te leveren, maar om een eerste technische basis neer te zetten waarmee onderdelen van zo’n systeem onderzocht, getest en vergeleken kunnen worden.

Binnen deze uitwerking ligt de nadruk vooral op de infrastructuurkant. Ik onderzoek hoe AI-detecties van afvalobjecten verstuurd, ontvangen en verwerkt kunnen worden binnen een eenvoudige maar reproduceerbare opstelling. Daarbij kijk ik zowel naar een lokale opstelling als naar een cloudopstelling in AWS.

De kern van dit project is als volgt:

- een YOLO-container detecteert objecten op afbeeldingen
- detectieresultaten worden via MQTT verstuurd
- een subscriber ontvangt deze berichten en schrijft resultaten weg naar CSV
- lokale en cloudmetingen kunnen daarna met elkaar vergeleken worden

Deze opzet ondersteunt het grotere projectdoel: onderzoeken hoe AI en infrastructuur samen kunnen bijdragen aan het herkennen van afval en het technisch ondersteunen van afvalscheiding.

## Huidige status van het project

Dit project is een proof of concept en nog niet compleet. De focus ligt op het testen van een technische keten, niet op een volledig productieklare oplossing.

Op dit moment is vooral gewerkt aan:

- het opzetten van infrastructuur met Terraform
- het configureren van servers met Ansible
- het testen van MQTT-communicatie tussen componenten
- het uitvoeren van metingen tussen lokale en cloudopstellingen
- het vastleggen van resultaten in CSV-bestanden

Nog niet alles van een volledig afvalscheidingssysteem zit hierin. Denk bijvoorbeeld aan een complete beslislaag, integratie met fysieke actuatoren of een volledig uitgewerkte end-to-end productieketen. Deze repository laat dus vooral de infrastructuurbasis en technische experimenten zien.

## Wat doet dit project?

Het project bestaat uit drie hoofdonderdelen:

1. **Terraform** maakt de AWS infrastructuur aan.
2. **Ansible** configureert de servers en services.
3. **De YOLO container** verwerkt afbeeldingen en stuurt detectieresultaten via MQTT.

De MQTT broker kan lokaal draaien of in AWS via Tailscale worden gebruikt. Daardoor kunnen lokale tests en cloudtests met elkaar worden vergeleken.

## Simpele architectuur

```text
Laptop
|-- Docker container met YOLO
|-- Subscriber script
|
| stuurt MQTT berichten
v
Mosquitto MQTT broker
|
v
CSV bestanden met meetresultaten
