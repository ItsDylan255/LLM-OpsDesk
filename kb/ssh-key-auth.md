# SSH-Key wird abgelehnt / SSH key rejected

keywords: ssh, key, schlüssel, publickey, permission denied, authorized_keys, rechte, permissions, git, anmeldung, authentication

## Symptome
"Permission denied (publickey)", obwohl der Key auf anderen Servern funktioniert.

## Prüfschritte
1. `ssh -v` zeigt, welche Keys angeboten werden.
2. Auf dem Server: Ist der öffentliche Key in `~/.ssh/authorized_keys` des richtigen Benutzers?
3. Rechte prüfen: `~/.ssh` 700, `authorized_keys` 600, Home-Verzeichnis nicht für andere schreibbar.
4. Server-Log: `journalctl -u sshd` nennt meist den Grund.
5. Neuere Server lehnen alte Key-Typen (z. B. ssh-rsa mit SHA-1) ab.

## Häufige Ursachen
Falsche Dateirechte, Key fehlt, veralteter Key-Typ.
