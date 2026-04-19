# Afval AI met YOLO, MQTT, Terraform en Ansible

Dit project is gemaakt voor een Infrastructure as Code opdracht. Het doel van
het project is om een simpele cloudomgeving te maken waarin een MQTT broker
draait. Daarna worden YOLO-detecties vanaf een Docker container naar deze broker
gestuurd. De resultaten worden opgeslagen in CSV-bestanden zodat lokale en cloud
metingen met elkaar vergeleken kunnen worden.

De README is geschreven op semester 3 HBO-ICT niveau. Daarom staat hier vooral
wat het project doet, hoe je het start en waar de belangrijkste bestanden staan.

## Wat doet dit project?

Het project bestaat uit drie delen:

1. Terraform maakt de AWS infrastructuur aan.
2. Ansible configureert de servers.
3. De YOLO container verwerkt afbeeldingen en stuurt resultaten via MQTT.

De MQTT broker kan lokaal draaien of in AWS via Tailscale worden gebruikt.

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
```

Bij de cloudversie draait de Mosquitto broker op een EC2 instance in AWS. De
verbinding loopt dan via Tailscale.

## Gebruikte technieken

- Terraform
- Ansible
- AWS EC2
- Docker
- Python
- Mosquitto MQTT
- Tailscale
- YOLO

## Mappenstructuur

```text
InfraAsCode/
|-- Terraform/        # Maakt de AWS infrastructuur
|-- Ansible/          # Configureert de servers
|-- yolo-container/   # Docker container, YOLO model en Python scripts
```

Belangrijke bestanden:

- `Terraform/environments/dev/main.tf`
- `Ansible/playbooks/bastion.yml`
- `Ansible/playbooks/mosquitto-broker.yml`
- `yolo-container/Dockerfile`
- `yolo-container/app/run_publish_folder.py`
- `yolo-container/app/subscriber.py`
- `yolo-container/app/mqtt_latency_benchmark.py`

## Benodigdheden

Voor dit project heb je nodig:

- Terraform
- Ansible
- Docker
- Python
- AWS CLI
- Een AWS account
- Een SSH key pair in AWS
- Een Tailscale account

## Veilig delen via GitHub

In deze repository staan geen echte secrets in de voorbeeldbestanden. Bestanden
met lokale waarden, IP-adressen of keys worden niet mee gecommit.

Maak lokaal je eigen configuratie op basis van deze voorbeelden:

```bash
cp Terraform/environments/dev/terraform.tfvars.example Terraform/environments/dev/terraform.tfvars
cp Terraform/environments/persistent/terraform.tfvars.example Terraform/environments/persistent/terraform.tfvars
cp Ansible/inventory/hosts.example.ini Ansible/inventory/hosts.ini
cp Ansible/inventory/hosts-tailscale.example.ini Ansible/inventory/hosts-tailscale.ini
cp Ansible/inventory/group_vars/bastion.example.yml Ansible/inventory/group_vars/bastion.yml
```

Vul daarna lokaal je eigen AWS profiel, IP-adressen, SSH key naam en Tailscale
auth key in. Deze echte waarden horen niet in GitHub.

## Terraform gebruiken

Ga eerst naar de Terraform dev omgeving:

```bash
cd Terraform/environments/dev
```

Start Terraform:

```bash
terraform init
```

Controleer wat Terraform gaat aanmaken:

```bash
terraform plan
```

Maak de infrastructuur aan:

```bash
terraform apply
```

Terraform maakt onder andere deze onderdelen aan:

- VPC
- Public subnet
- Private subnet
- Bastion host
- NAT instance
- Mosquitto server
- Security groups

Na het uitvoeren van Terraform wordt ook de Ansible inventory bijgewerkt.

## Ansible gebruiken

Ga naar de Ansible map:

```bash
cd Ansible
```

Draai eerst het playbook voor de bastion host:

```bash
ansible-playbook playbooks/bastion.yml
```

Draai daarna het playbook voor de Mosquitto broker:

```bash
ansible-playbook playbooks/mosquitto-broker.yml
```

De playbooks installeren onder andere:

- Tailscale
- Mosquitto
- Nginx op de bastion host

## Lokale MQTT broker starten

Voor lokaal testen kan Mosquitto met Docker gestart worden:

```powershell
cd yolo-container
docker run --rm -p 1883:1883 `
  -v ${PWD}\broker\config\mosquitto.conf:/mosquitto/config/mosquitto.conf `
  eclipse-mosquitto:2
```

## Subscriber starten

De subscriber ontvangt MQTT berichten en slaat deze op in een CSV-bestand.

```powershell
cd yolo-container
python -m pip install paho-mqtt
$env:MQTT_BROKER="localhost"
$env:OUTPUT_FILE="results_subscriber_local_steps.csv"
python app\subscriber.py
```

Voor de cloud broker kan `MQTT_BROKER` worden aangepast naar het Tailscale IP
van de Mosquitto server.

## YOLO container bouwen

Ga naar de map van de container:

```powershell
cd yolo-container
```

Build de Docker image:

```powershell
docker build -t yolo-mqtt-publisher:latest .
```

Start de publisher:

```powershell
docker run --rm `
  -e MQTT_BROKER=host.docker.internal `
  -e MQTT_PORT=1883 `
  -e OUTPUT_FILE=/app/results/results_roundtrip_local_steps.csv `
  -v ${PWD}:/app/results `
  yolo-mqtt-publisher:latest
```

De container doet het volgende:

1. Laadt het YOLO model.
2. Leest afbeeldingen uit `test-images`.
3. Voert detectie uit.
4. Stuurt het resultaat naar de MQTT broker.
5. Wacht op een antwoord van de subscriber.
6. Slaat de tijden op in een CSV-bestand.

## Benchmark

Er is ook een los script om alleen MQTT latency te meten:

```powershell
cd yolo-container
python app\mqtt_latency_benchmark.py `
  --broker-host localhost `
  --messages 100 `
  --label local `
  --output-file results_mqtt_latency_local.csv
```

Hiermee wordt gemeten hoe lang een MQTT bericht erover doet om heen en terug te
gaan.

## Resultaten

De resultaten staan in de map `yolo-container`.

Voorbeelden:

- `results_subscriber_local_steps.csv`
- `results_subscriber_cloud_tailscale_steps.csv`
- `results_roundtrip_local_steps.csv`
- `results_roundtrip_cloud_tailscale_steps.csv`

Deze bestanden zijn gebruikt om lokale metingen en cloudmetingen met elkaar te
vergelijken.

## Opruimen

Als de AWS omgeving niet meer nodig is, kan deze worden verwijderd met:

```bash
cd Terraform/environments/dev
terraform destroy
```

Controleer daarna in AWS of alle EC2 instances en andere resources echt weg
zijn. Zo voorkom je onnodige kosten.

## Korte samenvatting

Dit project laat zien hoe je met Infrastructure as Code een simpele cloudomgeving
maakt voor een MQTT broker. Daarna wordt met Docker en Python getest hoe snel
YOLO-detecties via MQTT kunnen worden verstuurd. De resultaten worden opgeslagen
in CSV-bestanden zodat ze later geanalyseerd kunnen worden.
