# DNS-Auflösung schlägt fehl / DNS resolution fails

keywords: dns, nxdomain, servfail, auflösung, resolution, domain, hostname, nameserver, resolver, zone, eintrag, record, ttl, website, webseite, nicht erreichbar, unreachable

## Symptome
Namen lassen sich nicht auflösen (NXDOMAIN, SERVFAIL), Webseite für Kunden nicht erreichbar, IP-Adresse direkt funktioniert aber.

## Prüfschritte
1. `dig name.example.com` und `dig @8.8.8.8 name.example.com` vergleichen (interner vs. externer Resolver).
2. Zone beim DNS-Anbieter prüfen: Eintrag gelöscht? Domain abgelaufen? Letzte Änderung?
3. `dig +trace` zeigt, an welcher Stelle die Auflösung abbricht.
4. TTL beachten: Korrekturen wirken erst nach Ablauf der alten TTL überall.

## Häufige Ursachen
Gelöschter oder falscher Eintrag nach einer Änderung, abgelaufene Domain, ausgefallener Nameserver.
