# Paketverlust und hohe Latenz / packet loss and high latency

keywords: paketverlust, packet loss, latenz, latency, ping, mtr, langsam, slow, netzwerk, network, switch, interface, fehler, errors, duplex

## Symptome
Anwendungen sind langsam, Ping zeigt Verluste oder stark schwankende Antwortzeiten zwischen zwei Systemen.

## Prüfschritte
1. `mtr host` zwischen den betroffenen Systemen: an welchem Hop beginnt der Verlust?
2. Interface-Fehler prüfen: `ip -s link`, Zähler für Errors/Drops.
3. Switch-Port prüfen: Duplex/Speed-Fehlanpassung, CRC-Fehler, ausgelastete Uplinks.

## Häufige Ursachen
Defektes Kabel oder Port, Duplex-Fehlanpassung, überlasteter Uplink.
