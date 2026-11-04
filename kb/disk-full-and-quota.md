# Festplatte voll oder Quota überschritten / disk full or quota exceeded

keywords: festplatte, platte, voll, disk full, no space left on device, speicher, speicherplatz, df, du, quota, kontingent, home, backup, logs, datenbank, database, postgresql, schreiben, write

## Symptome
"No space left on device", Datenbank nimmt keine Schreibzugriffe an, Backups schlagen fehl, Nutzer kann keine Dateien speichern (Quota).

## Prüfschritte
1. `df -h` (Speicher) und `df -i` (Inodes) prüfen.
2. Größte Verzeichnisse finden: `du -xh / --max-depth=2 | sort -h | tail`.
3. Typische Platzfresser: alte Logs, rotierte Logs ohne Komprimierung, alte Backups, Core Dumps, Docker-Images.
4. Quota eines Nutzers: `quota -u name` bzw. `repquota`.
5. Bei Datenbanken nicht einfach Dateien löschen; zuerst Platz an anderer Stelle schaffen oder Volume vergrößern.

## Häufige Ursachen
Fehlende Log-Rotation, gewachsene Backups, unerwartet große Datenmengen.
