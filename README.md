# Afvalscheiding met AI, MQTT, Terraform en Ansible

Dit project is een proof of concept voor een challenge rond afvalscheiding met
AI en computer vision. Het idee is om met YOLO objecten op afbeeldingen te
herkennen en de detectieresultaten via MQTT door te sturen.

De focus van dit project ligt vooral op de infrastructuur. Met Terraform wordt
een AWS omgeving aangemaakt en met Ansible worden de servers geconfigureerd. De
YOLO- en MQTT-onderdelen worden gebruikt om te testen of de omgeving werkt en om
lokale metingen te vergelijken met metingen via de cloud.

Het project is dus nog geen volledig eindproduct voor automatische
afvalscheiding. Het is een technische basis waarin infrastructuur, messaging en
AI-detectie samenkomen.

## Huidige status

Dit project is op dit moment een proof of concept.

Wat al werkt:

- AWS infrastructuur aanmaken met Terraform
- EC2 instances gebruiken voor bastion en MQTT broker
- Servers configureren met Ansible
- Mosquitto MQTT lokaal of in AWS gebruiken
- Tailscale gebruiken voor veilige toegang tot de cloud broker
- YOLO-detecties uitvoeren op testafbeeldingen
- Detectieresultaten publiceren via MQTT
- MQTT berichten ontvangen met een subscriber
- Resultaten opslaan in CSV-bestanden
- Lokale en cloudmetingen met elkaar vergelijken

Wat nog niet volledig is uitgewerkt:

- Geen compleet fysiek afvalscheidingssysteem
- Geen koppeling met een echte lopende band of robotarm
- Geen productieklare beveiliging voor MQTT
- Geen dashboard voor eindgebruikers
- Geen automatisch besluitvormingssysteem voor soorten afval

## Wat doet dit project?

Het project bestaat uit meerdere onderdelen die samen een testomgeving vormen.

Terraform maakt de cloudinfrastructuur aan in AWS. Hierbij worden onder andere
een VPC, subnetten, security groups, een bastion host, een NAT instance en een
Mosquitto server aangemaakt.

Ansible configureert de servers nadat Terraform ze heeft aangemaakt. Hiermee
worden bijvoorbeeld Tailscale, Mosquitto en andere benodigde packages op de
servers gezet.

De YOLO-container verwerkt afbeeldingen uit de map `test-images`. Per afbeelding
wordt gekeken welke objecten herkend worden. De resultaten worden daarna via
MQTT naar een broker gestuurd.

De subscriber luistert op het MQTT topic, ontvangt de berichten en schrijft de
resultaten naar CSV-bestanden. Deze bestanden kunnen daarna gebruikt worden om
metingen lokaal en via de cloud te vergelijken.

## Simpele architectuur

```text
Laptop / ontwikkelmachine
|-- Terraform
|-- Ansible
|-- Docker container met YOLO publisher
|-- Python MQTT subscriber
|
| maakt, configureert en test
v
AWS omgeving
|-- Public subnet
|   |-- Bastion host
|   |-- NAT instance
|
|-- Private subnet
|   |-- Mosquitto MQTT broker
|
v
MQTT berichten
|
v
CSV bestanden met resultaten
```

De MQTT broker kan op twee manieren gebruikt worden:

- Lokaal met Docker en Mosquitto
- In AWS via een EC2 instance en Tailscale

Hierdoor kan hetzelfde testscript gebruikt worden voor een lokale test en voor
een cloudtest.

## Relatie met afvalscheiding

Het onderwerp van de challenge is afvalscheiding met AI. In dit project wordt
dat onderzocht door afbeeldingen te analyseren met YOLO. YOLO kan objecten op
een afbeelding detecteren en daar een label en confidence score aan koppelen.

In een verder uitgewerkt systeem zouden deze detecties gebruikt kunnen worden om
afval te classificeren en daarna een actie uit te voeren, bijvoorbeeld sorteren
of doorsturen naar een bepaalde afvalstroom.

In deze proof of concept ligt de nadruk nog niet op het echte sorteren van
afval. De nadruk ligt op de technische basis:

- Kan de infrastructuur automatisch worden opgezet?
- Kan een MQTT broker lokaal en in de cloud draaien?
- Kunnen YOLO-resultaten via MQTT worden verstuurd?
- Kunnen de resultaten worden opgeslagen voor analyse?
- Is er verschil tussen lokale communicatie en communicatie via de cloud?

## Gebruikte technieken

| Techniek | Gebruik in dit project |
| --- | --- |
| Terraform | AWS infrastructuur automatisch aanmaken |
| Ansible | Servers installeren en configureren |
| AWS EC2 | Virtuele servers voor bastion, NAT en Mosquitto |
| Docker | YOLO publisher en lokale Mosquitto broker draaien |
| Python | Publisher, subscriber en benchmark scripts |
| Mosquitto MQTT | Broker voor berichten tussen publisher en subscriber |
| Tailscale | Veilige verbinding naar de cloudomgeving |
| YOLO | Objectdetectie op afbeeldingen |

## Mappenstructuur

```text
InfraAsCode/
|-- Terraform/
|   |-- environments/
|   |   |-- persistent/
|   |   |-- dev/
|   |-- modules/
|
|-- Ansible/
|   |-- inventory/
|   |-- playbooks/
|
|-- yolo-container/
|   |-- app/
|   |-- broker/
|   |-- models/
|   |-- test-images/
|   |-- Dockerfile
|
|-- README.md
```

Belangrijke bestanden:

- `Terraform/environments/dev/main.tf`
- `Terraform/environments/dev/terraform.tfvars.example`
- `Terraform/environments/persistent/main.tf`
- `Ansible/playbooks/bastion.yml`
- `Ansible/playbooks/mosquitto-broker.yml`
- `yolo-container/Dockerfile`
- `yolo-container/app/run_publish_folder.py`
- `yolo-container/app/subscriber.py`
- `yolo-container/app/mqtt_latency_benchmark.py`

## Benodigdheden

Voor dit project zijn de volgende onderdelen nodig:

- Terraform
- Ansible
- Docker
- Python 3
- AWS CLI
- Een AWS account
- Een AWS key pair voor SSH
- Een Tailscale account
- Een YOLO modelbestand in `yolo-container/models/`

Daarnaast moet de AWS CLI lokaal ingesteld zijn met een profiel dat resources
mag aanmaken in AWS.

## Veilig delen via GitHub

In dit project kunnen gevoelige gegevens voorkomen, zoals:

- AWS profielnamen
- Publieke IP-adressen
- Tailscale auth keys
- SSH key namen
- Terraform state bestanden
- Lokale inventory bestanden

Deze gegevens horen niet in GitHub te staan.

Daarom staan er voorbeeldbestanden in de repository. Maak lokaal je eigen
bestanden op basis van deze voorbeelden:

```bash
cp Terraform/environments/dev/terraform.tfvars.example Terraform/environments/dev/terraform.tfvars
cp Terraform/environments/persistent/terraform.tfvars.example Terraform/environments/persistent/terraform.tfvars
cp Ansible/inventory/hosts.example.ini Ansible/inventory/hosts.ini
cp Ansible/inventory/hosts-tailscale.example.ini Ansible/inventory/hosts-tailscale.ini
cp Ansible/inventory/group_vars/bastion.example.yml Ansible/inventory/group_vars/bastion.yml
```

Vul daarna lokaal je eigen waarden in. Controleer altijd met `git status` voordat
je iets commit.

## Terraform gebruiken

Terraform wordt gebruikt om de AWS infrastructuur aan te maken.

### 1. Persistente Elastic IP aanmaken

De map `persistent` wordt gebruikt voor resources die langer mogen blijven
bestaan, zoals een Elastic IP voor de bastion host.

```bash
cd Terraform/environments/persistent
terraform init
terraform plan
terraform apply
terraform output
```

Neem de output `bastion_eip_allocation_id` over in:

```text
Terraform/environments/dev/terraform.tfvars
```

### 2. Dev omgeving aanmaken

Ga daarna naar de dev omgeving:

```bash
cd ../dev
terraform init
terraform plan
terraform apply
```

Terraform maakt onder andere aan:

- VPC
- Public subnet
- Private subnet
- Internet gateway
- Route tables
- Security groups
- Bastion host
- NAT instance
- Mosquitto EC2 instance

Na het uitvoeren van Terraform worden ook de Ansible inventory bestanden
bijgewerkt.

## Ansible gebruiken

Ansible wordt gebruikt om de servers verder in te richten.

Ga naar de Ansible map:

```bash
cd Ansible
```

Maak lokaal de benodigde group vars aan. De Tailscale auth key moet lokaal
worden ingevuld en mag niet in GitHub komen.

Voor de bastion host:

```yaml
tailscale_auth_key: "replace-with-your-tailscale-auth-key"
tailscale_hostname: "bastion-trash-ai"
```

Voor de Mosquitto server kan lokaal een bestand worden gemaakt zoals:

```yaml
tailscale_auth_key: "replace-with-your-tailscale-auth-key"
tailscale_hostname: "mosquitto-trash-ai"
mosquitto_config_dir: "/etc/mosquitto/conf.d"
mosquitto_data_dir: "/var/lib/mosquitto"
mosquitto_log_dir: "/var/log/mosquitto"
mosquitto_port: 1883
mosquitto_protocol: "mqtt"
mosquitto_persistence: true
mosquitto_allow_anonymous: true
mosquitto_user: "mosquitto"
mosquitto_group: "mosquitto"
```

Draai daarna de playbooks:

```bash
ansible-playbook playbooks/bastion.yml
ansible-playbook playbooks/mosquitto-broker.yml
```

Het bastion-playbook installeert onder andere Tailscale en Nginx. Het
Mosquitto-playbook installeert en configureert de MQTT broker.

## Lokale MQTT broker starten

Voor lokale tests kan Mosquitto met Docker worden gestart.

```powershell
cd yolo-container
docker run --rm -p 1883:1883 `
  -v ${PWD}\broker\config\mosquitto.conf:/mosquitto/config/mosquitto.conf `
  eclipse-mosquitto:2
```

De broker luistert dan lokaal op poort `1883`.

## Subscriber starten

De subscriber ontvangt berichten van de MQTT broker en schrijft deze weg naar
een CSV-bestand.

Voor een lokale broker:

```powershell
cd yolo-container
python -m pip install paho-mqtt
$env:MQTT_BROKER="localhost"
$env:MQTT_PORT="1883"
$env:OUTPUT_FILE="results_subscriber_local_steps.csv"
python app\subscriber.py
```

Voor de broker in AWS via Tailscale:

```powershell
cd yolo-container
$env:MQTT_BROKER="<tailscale-ip-of-hostname-van-broker>"
$env:MQTT_PORT="1883"
$env:OUTPUT_FILE="results_subscriber_cloud_tailscale_steps.csv"
python app\subscriber.py
```

De subscriber luistert standaard op:

```text
waste/detections
```

En stuurt acknowledgements terug via:

```text
waste/acks
```

## YOLO-container bouwen en draaien

De YOLO publisher draait in een Docker container. Deze container leest
afbeeldingen uit `test-images`, voert detectie uit en publiceert de resultaten
naar MQTT.

Build de Docker image:

```powershell
cd yolo-container
docker build -t yolo-mqtt-publisher:latest .
```

Publisher draaien tegen een lokale MQTT broker:

```powershell
docker run --rm `
  -e MQTT_BROKER=host.docker.internal `
  -e MQTT_PORT=1883 `
  -e OUTPUT_FILE=/app/results/results_roundtrip_local_steps.csv `
  -v ${PWD}:/app/results `
  yolo-mqtt-publisher:latest
```

Publisher draaien tegen de cloud broker via Tailscale:

```powershell
docker run --rm `
  -e MQTT_BROKER=<tailscale-ip-of-hostname-van-broker> `
  -e MQTT_PORT=1883 `
  -e OUTPUT_FILE=/app/results/results_roundtrip_cloud_tailscale_steps.csv `
  -v ${PWD}:/app/results `
  yolo-mqtt-publisher:latest
```

De container doet in grote lijnen dit:

1. YOLO model laden
2. Afbeeldingen inlezen
3. Objectdetectie uitvoeren
4. Detectieresultaten publiceren via MQTT
5. Wachten op acknowledgement van de subscriber
6. Resultaten opslaan in CSV

## Benchmark

De benchmark is niet het hoofdonderdeel van het project. De benchmark is gebruikt
om te testen of de MQTT verbinding goed werkt en om lokale metingen te
vergelijken met cloudmetingen.

Er is een los benchmarkscript voor MQTT latency:

```powershell
cd yolo-container
python -m pip install paho-mqtt
python app\mqtt_latency_benchmark.py `
  --broker-host localhost `
  --broker-port 1883 `
  --messages 100 `
  --warmup 5 `
  --payload-bytes 512 `
  --label local `
  --output-file results_mqtt_latency_local.csv
```

Voor een test via Tailscale kan `--broker-host localhost` vervangen worden door
het Tailscale IP of de Tailscale hostname van de broker.

## Resultaten

De resultaten worden opgeslagen als CSV-bestanden in `yolo-container`.

Voorbeelden van resultaatbestanden:

- `results_subscriber_local_steps.csv`
- `results_subscriber_cloud_tailscale_steps.csv`
- `results_roundtrip_local_steps.csv`
- `results_roundtrip_cloud_tailscale_steps.csv`

De subscriberbestanden laten zien welke MQTT berichten zijn ontvangen. De
roundtripbestanden bevatten informatie over de tijd tussen publiceren en
bevestigen.

Deze resultaten zijn gebruikt om te controleren:

- Of berichten goed worden verstuurd
- Of berichten goed worden ontvangen
- Hoe groot het verschil is tussen lokaal testen en testen via AWS/Tailscale
- Of de infrastructuur bruikbaar is voor de proof of concept

## Opruimen

Als de AWS omgeving niet meer nodig is, kan deze worden verwijderd met
Terraform.

Verwijder eerst de dev omgeving:

```bash
cd Terraform/environments/dev
terraform destroy
```

Als de Elastic IP ook niet meer nodig is, kan daarna de persistent omgeving
worden verwijderd:

```bash
cd ../persistent
terraform destroy
```

Controleer daarna in de AWS Console of alle resources echt verwijderd zijn. Dit
voorkomt onnodige kosten.

## Samenvatting

Dit project is een proof of concept voor afvalscheiding met AI. YOLO wordt
gebruikt om objecten op afbeeldingen te detecteren en MQTT wordt gebruikt om de
resultaten door te sturen.

De belangrijkste focus ligt op de infrastructuur. Terraform bouwt de AWS
omgeving, Ansible configureert de servers en Docker/Python worden gebruikt om de
werking te testen. De benchmark en CSV-resultaten zijn bedoeld als controle en
vergelijking tussen lokaal draaien en draaien via AWS met Tailscale.
