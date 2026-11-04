# Cronjob läuft nicht / cron job not running

keywords: cron, cronjob, crontab, zeitplan, schedule, nächtlich, nightly, export, job, timer, systemd timer, lief nicht, did not run

## Prüfschritte
1. Ist der Job eingetragen? `crontab -l -u benutzer`, `/etc/cron.d/`.
2. Läuft der Cron-Dienst? `systemctl status cron`.
3. Logs: `journalctl -u cron` bzw. `/var/log/syslog | grep CRON`.
4. Skript manuell als derselbe Benutzer ausführen; in Cron fehlen oft Umgebungsvariablen und PATH.
5. Ausgabe des Jobs in eine Logdatei umleiten, damit Fehler sichtbar werden.

## Häufige Ursachen
Abweichende Umgebung (PATH), geänderte Rechte, Skript nach Update verschoben.
