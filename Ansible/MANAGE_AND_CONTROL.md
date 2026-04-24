# Manage And Control

Deze handleiding beschrijft hoe de Tailscale-toegang en de Ansible-configuratie
voor deze omgeving beheerd worden. Het doel is dat een volgende beheerder de
omgeving opnieuw kan uitrollen zonder afhankelijk te zijn van mondelinge
kennis.

## Doel

De omgeving gebruikt Tailscale voor veilige toegang tot projectservers zonder
de services publiek open te zetten. Toegang wordt geregeld via:

- `groups` voor gebruikers
- `tags` voor servers
- `grants` voor netwerktoegang
- Ansible playbooks die Tailscale opnieuw kunnen installeren en taggen

## Gebruikte Tags

De volgende tags worden gebruikt:

- `tag:project-bastion`
- `tag:project-api`
- `tag:project-db`
- `tag:project-mqtt`
- `tag:project-dashboard`

Alle tags hebben als owner:

- `group:project-admins`

## Gebruikte Groepen

De policy gebruikt minimaal deze groepen:

- `group:project-admins`
- `group:students`

Ontwerpkeuze:

- project-admins hebben beheer op alle projectservers
- studenten hebben alleen toegang tot de benodigde projectservices
- gebruikers houden toegang tot hun eigen devices via `autogroup:self`
- gebruikers hebben geen toegang tot elkaars devices

## Huidige Toegangsmodel

Huidige functionele afspraken:

- admins mogen naar alle projectservers
- studenten mogen naar:
  - API op `tcp:80` en `tcp:443`
  - dashboard op `tcp:80` en `tcp:443`
  - PostgreSQL op `tcp:5432`
  - Mosquitto op `tcp:1883`
- API mag naar PostgreSQL op `tcp:5432`
- dashboard mag naar API op `tcp:80` en `tcp:443`
- Mosquitto mag naar API op `tcp:80` en `tcp:443`
- bastion is niet toegankelijk voor studenten

Let op:

- als de ASP.NET API later op andere poorten draait, moet de Tailscale policy
  daarop aangepast worden

## Ansible Bestanden

De Tailscale-configuratie is opgenomen in:

- `playbooks/bastion.yml`
- `playbooks/api.yml`
- `playbooks/dashboard.yml`
- `playbooks/mosquitto-broker.yml`
- `playbooks/postgresql-primary.yml`

Bijbehorende voorbeeldvariabelen staan in:

- `inventory/group_vars/bastion.example.yml`
- `inventory/group_vars/api.example.yml`
- `inventory/group_vars/dashboard.example.yml`
- `inventory/group_vars/postgres_primary.example.yml`

Belangrijke variabelen:

- `tailscale_auth_key`
- `tailscale_hostname`
- `tailscale_advertise_tags`

## Heruitrol

Volgorde voor een heruitrol in de testomgeving:

```bash
cd Ansible
ansible-playbook -i inventory/hosts-test_omgeving.ini playbooks/bastion.yml
ansible-playbook -i inventory/hosts-test_omgeving.ini playbooks/api.yml
ansible-playbook -i inventory/hosts-test_omgeving.ini playbooks/dashboard.yml
ansible-playbook -i inventory/hosts-test_omgeving.ini playbooks/mosquitto-broker.yml
ansible-playbook -i inventory/hosts-test_omgeving.ini playbooks/postgresql-primary.yml
```

## Controle Na Uitrol

Controleer na een run:

- of de machine zichtbaar is in Tailscale admin
- of de juiste tag op de machine staat
- of de hostname klopt
- of de policy de tag ook echt toestaat

Praktische checks:

```bash
tailscale status
tailscale ip -4
```

Voor PostgreSQL:

- controleer dat de host zowel via het private AWS-netwerk als via Tailscale
  bereikbaar is
- controleer dat de users kunnen inloggen en dat de databases bestaan

## Beheerafspraken

- gebruik bij voorkeur tagged auth keys voor servers
- houd gebruikers in `group:students` actueel
- voeg nieuwe projectservers altijd eerst toe als `tag`
- pas daarna pas Ansible-vars en Tailscale `grants` aan
- laat geen algemene `allow all` regel actief staan

## Overdrachtsnotitie

Deze opzet is bedoeld om overdraagbaar te zijn:

- de access policy staat centraal in Tailscale
- de serverconfiguratie staat centraal in Ansible
- tags en playbooks zijn op elkaar afgestemd
- een beheerder kan servers opnieuw uitrollen zonder handmatig Tailscale-werk
