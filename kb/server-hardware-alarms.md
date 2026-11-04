# Hardware-Alarme am Server (Netzteil, Lüfter) / server hardware alarms

keywords: hardware, server, netzteil, psu, power supply, lüfter, fan, idrac, ilo, ipmi, bmc, alarm, failure, redundanz, redundancy, temperatur

## Symptome
Das Management-Interface (iDRAC, iLO, IPMI) meldet einen Ausfall, z. B. "PSU failure" oder Lüfterfehler.

## Prüfschritte
1. Ereignisprotokoll im Management-Interface lesen (`ipmitool sel list`).
2. Netzteil: Stromkabel und Steckdosenleiste prüfen, bevor man von einem Defekt ausgeht.
3. Läuft der Server auf einem Netzteil weiter, ist die Redundanz weg: Ersatzteil bestellen, Ausfall des zweiten Netzteils würde den Server stoppen.
4. Garantie/Wartungsvertrag prüfen.

## Häufige Ursachen
Defektes Netzteil, gezogenes Kabel, ausgefallener Stromkreis.
