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
3. **De YOLO-container** verwerkt afbeeldingen en stuurt detectieresultaten via MQTT.

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

Bij de cloudversie draait de Mosquitto broker op een EC2-instance in AWS. De verbinding loopt dan via Tailscale.

Relatie met afvalscheiding

Binnen de bredere challenge is het idee dat AI gebruikt wordt om afvalobjecten te herkennen, zodat afvalstromen later beter gescheiden of aangestuurd kunnen worden. In deze repository ligt de focus nog niet op de volledige scheidingsmachine of een compleet eindproduct, maar op de technische keten daarachter.

Deze repository onderzoekt dus vooral vragen als:

hoe kunnen detectieresultaten betrouwbaar worden verstuurd?
wat is het verschil tussen lokaal en cloud in latency?
hoe kan infrastructuur reproduceerbaar worden ingericht?
hoe kan de technische basis later verder worden uitgebreid?
Gebruikte technieken
Terraform
Ansible
AWS EC2
Docker
Python
Mosquitto MQTT
Tailscale
YOLO
Mappenstructuur
InfraAsCode/
|-- Terraform/        # Maakt de AWS infrastructuur
|-- Ansible/          # Configureert de servers
|-- yolo-container/   # Docker container, YOLO model en Python scripts
Belangrijke bestanden
Terraform/environments/dev/main.tf
Ansible/playbooks/bastion.yml
Ansible/playbooks/mosquitto-broker.yml
yolo-container/Dockerfile
yolo-container/app/run_publish_folder.py
yolo-container/app/subscriber.py
yolo-container/app/mqtt_latency_benchmark.py
Benodigdheden

Voor dit project heb je nodig:

Terraform
Ansible
Docker
Python
AWS CLI
een AWS account
een SSH key pair in AWS
een Tailscale account
Veilig delen via GitHub

In deze repository staan geen echte secrets in de voorbeeldbestanden. Bestanden met lokale waarden, IP-adressen of keys worden niet mee gecommit.

Maak lokaal je eigen configuratie op basis van deze voorbeelden:

cp Terraform/environments/dev/terraform.tfvars.example Terraform/environments/dev/terraform.tfvars
cp Terraform/environments/persistent/terraform.tfvars.example Terraform/environments/persistent/terraform.tfvars
cp Ansible/inventory/hosts.example.ini Ansible/inventory/hosts.ini
cp Ansible/inventory/hosts-tailscale.example.ini Ansible/inventory/hosts-tailscale.ini
cp Ansible/inventory/group_vars/bastion.example.yml Ansible/inventory/group_vars/bastion.yml

Vul daarna lokaal je eigen AWS-profiel, IP-adressen, SSH key naam en Tailscale auth key in. Deze echte waarden horen niet in GitHub.

Terraform gebruiken

Ga eerst naar de Terraform dev-omgeving:

cd Terraform/environments/dev

Start Terraform:

terraform init

Controleer wat Terraform gaat aanmaken:

terraform plan

Maak de infrastructuur aan:

terraform apply

Terraform maakt onder andere deze onderdelen aan:

VPC
public subnet
private subnet
bastion host
NAT instance
Mosquitto server
security groups

Na het uitvoeren van Terraform wordt ook de Ansible inventory bijgewerkt.

Ansible gebruiken

Ga naar de Ansible-map:

cd Ansible

Draai eerst het playbook voor de bastion host:

ansible-playbook playbooks/bastion.yml

Draai daarna het playbook voor de Mosquitto broker:

ansible-playbook playbooks/mosquitto-broker.yml

De playbooks installeren onder andere:

Tailscale
Mosquitto
Nginx op de bastion host
Lokale MQTT broker starten

Voor lokaal testen kan Mosquitto met Docker gestart worden:

cd yolo-container
docker run --rm -p 1883:1883 `
  -v ${PWD}\broker\config\mosquitto.conf:/mosquitto/config/mosquitto.conf `
  eclipse-mosquitto:2
Subscriber starten

De subscriber ontvangt MQTT-berichten en slaat deze op in een CSV-bestand.

cd yolo-container
python -m pip install paho-mqtt
$env:MQTT_BROKER="localhost"
$env:OUTPUT_FILE="results_subscriber_local_steps.csv"
python app\subscriber.py

Voor de cloud broker kan MQTT_BROKER worden aangepast naar het Tailscale-IP van de Mosquitto server.

YOLO-container bouwen

Ga naar de map van de container:

cd yolo-container

Build de Docker image:

docker build -t yolo-mqtt-publisher:latest .

Start de publisher:

docker run --rm `
  -e MQTT_BROKER=host.docker.internal `
  -e MQTT_PORT=1883 `
  -e OUTPUT_FILE=/app/results/results_roundtrip_local_steps.csv `
  -v ${PWD}:/app/results `
  yolo-mqtt-publisher:latest

De container doet het volgende:

laadt het YOLO-model
leest afbeeldingen uit test-images
voert detectie uit
stuurt het resultaat naar de MQTT broker
wacht op een antwoord van de subscriber
slaat de tijden op in een CSV-bestand
Benchmark

Er is ook een los script om alleen MQTT-latency te meten:

cd yolo-container
python app\mqtt_latency_benchmark.py `
  --broker-host localhost `
  --messages 100 `
  --label local `
  --output-file results_mqtt_latency_local.csv

Hiermee wordt gemeten hoe lang een MQTT-bericht erover doet om heen en terug te gaan.

Resultaten

De resultaten staan in de map yolo-container.

Voorbeelden:

results_subscriber_local_steps.csv
results_subscriber_cloud_tailscale_steps.csv
results_roundtrip_local_steps.csv
results_roundtrip_cloud_tailscale_steps.csv

Deze bestanden zijn gebruikt om lokale metingen en cloudmetingen met elkaar te vergelijken.

Opruimen

Als de AWS-omgeving niet meer nodig is, kan deze worden verwijderd met:

cd Terraform/environments/dev
terraform destroy

Controleer daarna in AWS of alle EC2-instances en andere resources echt weg zijn. Zo voorkom je onnodige kosten.

Samenvatting

Deze repository laat een eerste technische basis zien voor een AI-ondersteund afvalscheidingsproject. De focus ligt op infrastructuur, MQTT-communicatie en het vergelijken van lokale en cloudopstellingen. Het project is nog niet compleet en vormt vooral een proof of concept, maar laat wel zien hoe detectieresultaten uit een AI-model via een reproduceerbare infrastructuur verwerkt en gemeten kunnen worden.
