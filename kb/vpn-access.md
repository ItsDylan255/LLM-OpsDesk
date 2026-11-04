# VPN-Zugriff auf interne Systeme / VPN access to internal systems

keywords: vpn, tunnel, standort, office, büro, remote, homeoffice, wireguard, ipsec, openvpn, route, routing, fileserver, nicht erreichbar, unreachable, wartung, maintenance

## Symptome
Interne Systeme sind über VPN nicht erreichbar, direkt im Netz aber schon. Oft nach Wartungsarbeiten oder Änderungen an Firewall/Routing.

## Prüfschritte
1. Steht der Tunnel? Status am VPN-Gateway prüfen (Handshake, Uptime).
2. Routen prüfen: Wird das Zielnetz über den Tunnel geroutet (`ip route`, Gateway-Konfiguration)?
3. Firewall-Regeln am Gateway: Wurde bei der Wartung eine Regel entfernt oder geändert?
4. Betrifft es einen Standort oder alle? Einzelner Standort deutet auf dessen Tunnel hin.

## Häufige Ursachen
Fehlende Route nach Wartung, geänderte Firewall-Regel, abgelaufenes Zertifikat oder geänderter Schlüssel am Gateway.
