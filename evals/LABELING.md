# Label-Richtlinie für den Testsatz

Damit die Auswertung etwas bedeutet, müssen die "richtigen Antworten" (Labels) nach festen
Regeln vergeben werden, nicht nach Bauchgefühl. Diese Regeln gelten für `tickets.jsonl`.

## Kategorie (`category`)

| Wert | Wann |
|---|---|
| `network` | Verbindungen: DNS, VPN, SSH-Verbindungsaufbau, Firewall, Routing, Paketverlust, WLAN |
| `storage` | Speicher: Platte voll, Dateisystem, Mounts, Backups wegen Speicher, Quotas, RAID/Disk-Fehler aus Sicht des Speichers |
| `auth` | Anmeldung und Rechte: Passwörter, gesperrte Konten, SSH-Keys, Zertifikate für Login, LDAP, Berechtigungen |
| `service` | Ein Dienst/eine Anwendung läuft nicht richtig: Absturz, startet nicht, Fehlermeldungen, langsam, Cronjobs |
| `hardware` | Physische Geräte: Lüfter, Netzteil, RAM-Fehler, Drucker, Monitor, Laptop-Defekt |
| `other` | Passt nirgends sicher hinein, oder Anfrage statt Störung (z. B. Software-Wunsch) |

**Bei Überschneidung zählt die Ursache, die man zuerst prüfen würde.** Beispiel: "Backup schlägt
fehl, No space left on device" ist `storage`, nicht `service`.

## Priorität (`priority`)

| Wert | Regel |
|---|---|
| `critical` | Produktivsystem ausgefallen ODER viele Nutzer betroffen ODER Datenverlust/Sicherheitsvorfall droht, kein Workaround |
| `high` | Wichtiger Dienst stark beeinträchtigt oder ein Team blockiert, Workaround schwierig |
| `medium` | Einzelne Person oder unkritisches System betroffen, Workaround vorhanden |
| `low` | Schönheitsfehler, Frage, Wunsch, kein Zeitdruck |

## Mehr Informationen nötig (`needs_more_info`)

`true`, wenn das Ticket **weder ein System noch ein konkretes Symptom** nennt
(z. B. "Geht nicht, bitte schnell fixen"). Solche Tickets bekommen `category: other`
und die Priorität, die der Text nahelegt (meist `medium`).

## Prüfung durch einen Menschen

Die Tickets und Labels wurden mit KI-Hilfe erstellt. Jedes Ticket hat das Feld `reviewed`.
Es wird erst auf `true` gesetzt, wenn ein Mensch das Label nach dieser Richtlinie geprüft
(und ggf. korrigiert) hat. Die Auswertung zeigt an, wie viele Tickets geprüft sind.
