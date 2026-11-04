# Container startet nach Neustart nicht / container does not start after reboot

keywords: docker, container, neustart, reboot, autostart, restart policy, unless-stopped, compose, startet nicht, host

## Prüfschritte
1. `docker inspect -f '{{ .HostConfig.RestartPolicy.Name }}' container`.
2. Restart-Policy setzen: `docker update --restart unless-stopped container` bzw. `restart: unless-stopped` in compose.
3. Ist der Docker-Dienst selbst beim Systemstart aktiviert? `systemctl is-enabled docker`.

## Häufige Ursachen
Container ohne Restart-Policy gestartet.
