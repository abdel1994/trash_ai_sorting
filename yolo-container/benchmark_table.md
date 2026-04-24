# Benchmark Tabel

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