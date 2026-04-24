# YOLO MQTT benchmark samenvatting

## Kernconclusie

- Over 100 gelijke images is de mediane roundtrip lokaal 4.29 ms en via cloud/Tailscale 24.55 ms.
- Cloud/Tailscale voegt ongeveer 20.26 ms toe en is circa 5.73x langzamer dan lokaal.
- De mediane inferentie blijft vrijwel gelijk: 54.48 ms lokaal versus 54.25 ms via cloud/Tailscale.
- Het verschil zit dus vooral in netwerktransport: publisher naar subscriber stijgt van 1.60 ms naar 11.77 ms.

## Methode

- Ja, er is met gemiddelden gewerkt, maar niet alleen met gemiddelden.
- Omdat lokaal elke image 2 keer voorkomt en cloud/Tailscale 4 keer, berekent dit rapport eerst per image een gemiddelde.
- Daarna vergelijkt het rapport de mediaan van die per-image gemiddelden. Dat maakt de vergelijking eerlijker.
- In de JSON staan daarnaast ook gewone gemiddelden en medianen over alle losse berichten.

## Meetopzet

- Lokale dataset: 200 berichten over 100 unieke images.
- Cloud/Tailscale dataset: 400 berichten over 100 unieke images.
- Hoofdvergelijking gebruikt per-image gemiddelden op de overlap van dezelfde images, zodat het verschil in herhalingen de uitkomst niet scheeftrekt.

## Hoofdvergelijking

| Metric | Lokaal mediaan | Cloud/Tailscale mediaan | Verschil | Verhouding |
| --- | ---: | ---: | ---: | ---: |
| Inferentie | 54.48 ms | 54.25 ms | -0.23 ms | 1.00x |
| Publisher naar subscriber | 1.60 ms | 11.77 ms | 10.17 ms | 7.36x |
| Ack terug naar publisher | 2.63 ms | 12.72 ms | 10.09 ms | 4.84x |
| Totale roundtrip | 4.29 ms | 24.55 ms | 20.26 ms | 5.72x |

## Gemiddelden over alle berichten

| Metric | Lokaal gemiddelde | Cloud/Tailscale gemiddelde |
| --- | ---: | ---: |
| Inferentie | 76.93 ms | 81.71 ms |
| Publisher naar subscriber | 1.62 ms | 11.78 ms |
| Ack terug naar publisher | 2.65 ms | 12.71 ms |
| Totale roundtrip | 4.30 ms | 24.53 ms |

## Bewijszin voor presentatie

Bij een vergelijking over 100 dezelfde testimages blijft de YOLO-inferentie nagenoeg gelijk, maar de MQTT-communicatie via cloud/Tailscale verhoogt de mediane roundtrip van 4.29 ms naar 24.55 ms. Dat is een extra netwerkvertraging van ongeveer 20.26 ms.
