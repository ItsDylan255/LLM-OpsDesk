# SSH-Verbindung hängt oder ist langsam / SSH connection hangs or is slow

keywords: ssh, sshd, port 22, verbindung, connection, connecting, timeout, hängt, hangs, langsam, slow, passwort, password prompt, reverse dns, usedns, gssapi, server

## Symptome
`ssh` bleibt bei "Connecting" hängen oder braucht lange bis zur Passwortabfrage.

## Prüfschritte
1. `ssh -vvv host` zeigt, in welcher Phase es hängt.
2. Hängt der Verbindungsaufbau komplett: Ist Port 22 offen (`nc -zv host 22`)? Firewall oder Security Group geändert? Läuft `sshd` (`systemctl status sshd`)?
3. Dauert es nur bis zur Passwortabfrage lange (10-30 s): meist Reverse-DNS-Lookup des Servers. `UseDNS no` und `GSSAPIAuthentication no` in `/etc/ssh/sshd_config` prüfen.

## Häufige Ursachen
Firewall-Regel, gestoppter sshd, langsamer oder kaputter DNS auf dem Server.
