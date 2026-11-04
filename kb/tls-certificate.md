# TLS-Zertifikat abgelaufen / TLS certificate expired

keywords: tls, ssl, zertifikat, certificate, abgelaufen, expired, https, browser, warnung, warning, login, portal, renew, erneuern, lets encrypt, certbot

## Symptome
Browser zeigt Zertifikatswarnung, Clients brechen die Verbindung ab, Anmeldung über HTTPS nicht möglich.

## Prüfschritte
1. `openssl s_client -connect host:443 -servername host | openssl x509 -noout -dates`.
2. Zertifikat erneuern (z. B. `certbot renew`) und Webserver neu laden.
3. Prüfen, warum die automatische Erneuerung nicht lief (Timer/Cronjob, Log).
4. Ablaufüberwachung einrichten (Warnung 14 Tage vorher).

## Häufige Ursachen
Automatische Erneuerung ausgefallen, Zertifikat manuell ausgestellt und vergessen.
