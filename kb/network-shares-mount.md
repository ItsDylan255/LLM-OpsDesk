# Netzlaufwerk nicht eingehängt / network share not mounted

keywords: mount, eingehängt, gemountet, share, freigabe, nfs, smb, cifs, nas, fstab, neustart, reboot, laufwerk, dateien, files, autofs

## Symptome
Nach einem Neustart fehlt ein Netzlaufwerk, Nutzer kommen nicht an ihre Dateien.

## Prüfschritte
1. `mount | grep share` bzw. `findmnt` prüfen.
2. Eintrag in `/etc/fstab` prüfen; bei Netzlaufwerken Option `_netdev` bzw. `x-systemd.automount` setzen.
3. Manuell einhängen (`mount /mnt/share`) und Fehlermeldung lesen.
4. Ist der NAS-Dienst nach dem Neustart gestartet (NFS/SMB-Dienst)?

## Häufige Ursachen
Mount wird beim Start versucht, bevor das Netzwerk bereit ist; Dienst auf dem NAS nicht gestartet.
