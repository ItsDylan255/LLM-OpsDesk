# Festplattenzustand, SMART und RAID / disk health, SMART and RAID

keywords: smart, smartctl, reallocated, sektoren, sectors, raid, raid1, mdadm, array, degraded, festplatte, disk, defekt, failing, tausch, replace

## Symptome
SMART-Werte verschlechtern sich (z. B. steigende Reallocated Sectors), RAID meldet "degraded".

## Prüfschritte
1. `smartctl -a /dev/sdX`: Reallocated, Pending und Uncorrectable Sectors beobachten.
2. RAID-Status: `cat /proc/mdstat` bzw. `mdadm --detail /dev/mdX`.
3. Steigende Werte: Platte zeitnah tauschen, solange das RAID noch redundant ist.
4. Backup prüfen, bevor am RAID gearbeitet wird.

## Häufige Ursachen
Alternde Festplatte. Ein RAID ersetzt kein Backup.
