# Dienst stürzt ab oder startet nicht / service crashes or fails to start

keywords: dienst, service, systemd, systemctl, absturz, crash, crashes, startet nicht, failed, journalctl, update, nginx, apache, restart, neustart, webserver, website down

## Symptome
Ein Dienst stürzt wiederholt ab oder startet nicht, oft direkt nach einem Update.

## Prüfschritte
1. `systemctl status dienst` und `journalctl -u dienst --since "1 hour ago"`.
2. Konfiguration testen (z. B. `nginx -t`).
3. Was wurde zuletzt aktualisiert? Paket-Historie (`/var/log/apt/history.log` bzw. `dnf history`).
4. Ist der Fehler sicher auf das Update zurückzuführen: Rollback auf die vorherige Version erwägen.
5. Speicher prüfen: Wird der Prozess vom OOM-Killer beendet (`dmesg | grep -i oom`)?

## Häufige Ursachen
Inkompatible Konfiguration nach Update, fehlender Speicher, kaputte Abhängigkeit.
