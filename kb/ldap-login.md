# Anmeldung über LDAP/Verzeichnisdienst scheitert / LDAP login fails

keywords: ldap, active directory, ad, verzeichnis, directory, anmeldung, login, log in, sso, server unavailable, nicht verfügbar, bind, zertifikat, team

## Symptome
Anmeldung an einer oder mehreren Anwendungen schlägt fehl, Fehlermeldung wie "LDAP server unavailable".

## Prüfschritte
1. Ist der LDAP-Server erreichbar? `ldapsearch -H ldaps://server -x -b "" -s base`.
2. Betrifft es nur eine Anwendung: deren LDAP-Konfiguration prüfen (Server-Adresse, Bind-Benutzer, Passwort des Dienstkontos abgelaufen?).
3. LDAPS: Ist das Zertifikat des LDAP-Servers abgelaufen oder ersetzt worden?

## Häufige Ursachen
Abgelaufenes Passwort des Dienstkontos, abgelaufenes LDAPS-Zertifikat, Server nicht erreichbar.
