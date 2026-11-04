"""LLM OpsDesk: Texte (zuerst IT-Tickets) mit einem Sprachmodell analysieren.

Aufbau in drei Schichten:
- providers: WIE wir ein Sprachmodell aufrufen (Claude, Mock)
- tasks:     WAS das Modell tun soll (Prompt + Antwortformat), z. B. Tickets analysieren
- runner:    verbindet beides, prüft die Antwort und repariert sie notfalls
"""
