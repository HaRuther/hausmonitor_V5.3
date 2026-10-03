# Hausmonitor V5.3 LTS

Konsolidierte Version mit vollständigem Nivellement, Rissmonitoring und robuster Migration älterer Datenbanken.

## Funktionsumfang

- Nivellement: Rohdaten SW, SO, ANB, TSW, TSO; Statistik; Fehlerband; SD-Diagramm; Fotos; Bearbeitung; CSV
- Rissmonitoring: Messstellen, Messungen, Fotos, Bearbeitung, Grenzwerte, Rohdaten, CSV
- Fotovergleich erstes/aktuelles Rissfoto
- QR-Code pro Rissmessstelle direkt zur neuen Messung
- automatische textliche Lagebeurteilung auf dem Dashboard
- Einstellungen: Referenzkampagne, Grenzwerte, QR-Basis-URL und Rissstandardwerte
- Geräte- und Kalibrierverwaltung
- Gesamt-PDF und Jahres-PDF mit Nivellement, Rissmessungen und Rissfotos
- modernes PWA-App-Icon und Offline-App-Shell
- Backup-Skript

## Sichere Aktualisierung

```bash
cd /root/hausmonitor
cp -a data /root/hausmonitor-data-backup-v53
cp .env /root/hausmonitor-env-backup-v53
docker-compose down
```

Neue Projektdateien übernehmen, aber den vorhandenen Ordner `data/` und `.env` behalten. Danach:

```bash
docker-compose up -d --build
docker ps
docker logs --tail=100 hausmonitor-v5
```

## Datenbankmigration

V5.3 verwendet `app_settings` und liest bei der ersten Initialisierung automatisch bekannte Werte aus einer alten Tabelle `settings(key,value)`. Die bestehende alte Tabelle wird nicht gelöscht. Fehlende Spalten in `campaigns` und `crack_points` werden additiv ergänzt.

## Backups

```bash
./scripts/backup.sh
```

Zusätzlich sollte der gesamte LXC regelmäßig durch Proxmox gesichert werden.
