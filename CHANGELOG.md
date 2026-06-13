# alphaJET Interface-Tool — Changelog

> Versionshistorie des internen Servicetechniker-Tools für Koenig & Bauer alphaJET CIJ-Drucker.

![Version](https://img.shields.io/badge/Version-2.1.2-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Protocol](https://img.shields.io/badge/Protokoll-G--PR(INT)%20V3.0.0-orange)
![Python](https://img.shields.io/badge/Python-3.11%2B-yellow)
![Internal](https://img.shields.io/badge/Verwendung-Intern%20%2F%20Vertraulich-red)

---

Dieses Dokument enthält alle Anpassungen seit Version v.1.0.0

<!--
################################################################################
  ACHTUNG: Der Block ###LATEST CHANGES### wird vom Updater automatisch ausgelesen.
  Alles unterhalb wird im Update-Dialog angezeigt. Nicht entfernen oder umbenennen.
################################################################################
-->

###LATEST CHANGES###

######### -- v2.1.2 -- #########

### CRA-Anpassungen
#### `utils.py`
- TEST-FTP-Eintrag entfernt (Drittanbieter-Server mit öffentlichen Credentials)
- FTP-Credentials werden jetzt aus `res/ftp_credentials.json` geladen, wenn vorhanden → Werksvorgaben überschreibbar ohne Code-Änderung
- Neue Helfer: `validate_ip()`, `validate_port()`, `validate_gprint_xml()`, `validate_local_path()`

#### `tool.py`
- `import hashlib` ergänzt; `_verify_sha256()` hinzugefügt
- Update-Download prüft SHA-256 aus `version.json` vor dem Ausführen – Abort bei Mismatch
- `_save_network()`: IP-Format, Port 1–65535, Timeout 1–120 werden vor dem Speichern geprüft
- `_run_cmd()`: G-PRINT-XML-Struktur (`<GP>…</GP>`) wird validiert bevor gesendet wird

#### `ftp.py`
- Sichtbare Warnung im FTP-Header: *„FTP überträgt Daten unverschlüsselt – nur in gesichertem Netzwerk verwenden (CRA Art. 13)"*
- `_ftp_connect()`: IP-Adresse und Port werden vor dem Verbindungsaufbau validiert
- `_ftp_download_recursive()`: Path-Traversal-Schutz — Dateinamen mit `/` oder `\` werden blockiert; lokale Pfade werden auf Verbleib im Zielverzeichnis geprüft
- `_ftp_upload_recursive()`: Versteckte Dateien (`.`) und Einträge mit Pfadzeichen werden übersprungen

#### Sonstige Dateien
| Datei | Änderung |
|---|---|
| `requirements.txt` | `reportlab` entfernt; `pyftpdlib` ergänzt |
| `BUILD.bat` | `reportlab`-Check und `--collect-all "reportlab"` entfernt |
| `SECURITY.md` | Vulnerability Disclosure Policy (CRA Art. 13/14): Meldeweg, Reaktionszeiten, bekannte Risiken (FTP), implementierte Maßnahmen |
| `sbom.json` | Software Bill of Materials im CycloneDX 1.4 Format (CRA Annex I, Part II) |
| `version.json` | SHA-256-Feld ergänzt |

### Security Audit (OP-01 bis OP-04)

| Ticket | Bereich | Maßnahme |
|---|---|---|
| OP-01 | `utils.py`, `ftp.py`, `tool.py` | `utils.security_log(event, detail, result)` schreibt JSON-Lines nach `res/logs/security_audit.jsonl` (thread-safe); Log-Einträge bei FTP-Connect, Download (start/ok/hash_error/error) und `_save_network()` (CONFIG_CHANGE) |
| OP-02 | `utils.py`, `tool.py`, `az_reisekosten.py` | `utils.sanitize_error(e)` kürzt absolute Windows/POSIX-Pfade auf Dateinamen; verwendet in `_file_import()`, `do_download()` und Excel-Fehlerdialogen |
| OP-03 | `BUILD.bat` | Auto-install von `pip-audit` falls fehlend, dann `pip_audit --requirement requirements.txt` vor PyInstaller |
| OP-04 | `SECURITY.md` | Abschnitt „Geräte-Standardpasswörter" um Schritt-für-Schritt-Anleitung und vollständige `ftp_credentials.json`-Struktur erweitert |

---

<details>
<summary><b>v2.1.1</b> — Updater-Fix · MLG-Fixes · FTP-Verbesserungen · Local Cancel</summary>

### Updater
- App muss einmalig aktualisiert werden
- Updater neu gebaut, ohne Fehler und Errors beim Theme-Wechsel

### MLG
- MLG-Logos werden jetzt korrekt decodiert und beim Speichern korrekt codiert (KBA cgrafic-Style)

### FTP
- Drucker unterstützen weder `nlst` noch `mlsd` FTP-List-Formate
- Wenn kein Standardformat erkannt wird: Datei wird analysiert (Typ, Größe, Name) und in Spalten visualisiert
- Speichern als SVG entfernt (unnötig)

### Local
- Cancel wird nun korrekt ausgeführt, auch beim Theme-Wechsel (löscht alle temporären Dateien)

### Labels / Configs
- Neue G-PRINT Befehle hinzugefügt

</details>

---

<details>
<summary><b>v2.0.0</b> — Dark/Light-Mode · Design-Overhaul · Code-Qualität · Performance</summary>

### Design
- Hell/Dunkel-Modus wählbar (`forest-dark` & `forest-light`)
- Eigenes Stylesheet erstellt
- Button- und Schriftanpassungen; alles größer und kontrastreicher
- Kompletter Design-Quellcode in `utils.py` ausgelagert

### Updates
- Update über Git eingebunden; `version.json` als Versionsquelle

### Performance & Code-Qualität

| Bereich | Änderung |
|---|---|
| `_build_props_area` | Nur noch Header-Label + `_props_built = False`; Canvas/Scrollbar/Inner-Frame werden lazy gebaut |
| Auto-Ping | Toggle entfernt; startet automatisch 3 s nach App-Start, läuft dauerhaft |
| FTP-Keepalive | Intervall 10 s (statt 30 s); `_ftp_keepalive_id` gespeichert → kein Loop-Akkumulieren |
| Salesforce-Ping | `_sf_ping_loop()` startet 5 s nach Tab-Öffnung; 401/403 → Token gecleart; Netzwerkfehler → Dot gelb |
| HTTPS-Enforcement | `_update_check` und `_update_prompt` prüfen `url.startswith("https://")` |
| `shell=True` → `os.startfile` | Kein Subprozess mehr für `ncpa.cpl` |
| FTP-Tab Fehlerbehandlung | Jeder Sub-Build einzeln in `try/except`; Fehlermeldung im Tab statt leerem Frame |
| Thread-Safety | `threading.Lock()` schützt alle Schreibzugriffe auf `self._ftp` |
| Tiefenbegrenzung FTP | `_ftp_download_recursive(_depth=0)` – Abbruch bei `_depth > 20` |
| `save_json` | Exception-Handling ergänzt (Dateisystem voll → kein unkontrollierter Crash) |
| `label_editor.py` | `tag_bind` in `_redraw` akkumulierte Bindings → Memory Leak behoben |
| `label_editor.py` | `Image.NEAREST` deprecated → `Image.Resampling.NEAREST` |
| `az_reisekosten.py` | Timezone-Berechnung robuster: `datetime.now().astimezone().utcoffset()` |
| Allgemein | `WM_DELETE_WINDOW`-Handler ergänzt → FTP/Logs werden sauber beendet |

</details>

---

<details>
<summary><b>v1.9.0</b> — AZ & Reisekosten · Salesforce · Label Editor Fixes</summary>

### AZ & Reisekosten
- Salesforce Login hinzugefügt (Session-ID-basiert)
- Salesforce Load: SOQL-Abfrage aus TimeSheet → aktuelle KW befüllen
- Bug-Fix (Hauptursache für `#NV`): Enddatum geht jetzt auf H7 statt I7
- Innendienst-Filter: Einträge mit Dienstart Innendienst/Homeoffice werden in der Reisekosten-Excel übersprungen
- Gemischte Tage (z. B. Materialmanagement + Außendienst) werden nur mit dem AD-Anteil geladen
- Neue Zeile „Sonstiges Kosten €" direkt unter der Stundenleiste (gilt für die gesamte KW)
- Weitere Anpassungen beim Extrahieren der Reisekosten

### Salesforce-Auth / Login
- Nummerierte Schritt-für-Schritt-Anleitung direkt im Panel
- Button „🌐 Salesforce in Chrome öffnen"
- Tooltips auf allen Buttons (erscheinen nach ~0,6 s Hover)

### Salesforce-Laden
- Pause-Einträge (`Type = "Pause"`) → Dauer als Pausenzeit übernehmen
- Reisezeit-Einträge → zählen für Tag-Start/Ende
- Tag-Start = frühester Eintrag; Tag-Ende = spätester Eintrag
- Pause wird neu berechnet: `sum(..)` über alle SF-Einträge mit `Type="Pause"`

### Label Editor
- Weißer Rand unter bestimmten Labels entfernt (`CANVAS_PAD = 0`)
- Arial-Font-Rahmen korrigiert: dynamische Breitenberechnung via `char_height`

</details>

---

<details>
<summary><b>v1.8.0</b> — Mock FTP-Server · Forest-Dark-Theme · AZ & Reisekosten (Basis)</summary>

### Mock Server
- Mock-Server kann jetzt auch für FTP-Tests und Monitoring mit einem 2. PC genutzt werden
- Testdateien werden beim ersten Start automatisch in `res/mock_ftp/` angelegt

| Ordner | Datei | Inhalt |
|---|---|---|
| `labels/` | `sample_label.gp` | G-PRINT Label mit Text + Barcode |
| `logos/` | `kb_logo.svg` | K&B-Buchstaben als Pixel-SVG (32×16) |
| `logos/` | `checkerboard.mlg` | Schachbrett-Muster im MLG-Binärformat |
| `configs/` | `printer_test.pcf` | Drucker-Netzwerkkonfiguration |
| `printctl/` | `default.ctl` | PrintControl mit Trigger/Speed |

### Design
- Forest TTK Dark Theme (`res/themes/forest-dark.tcl`)
- Farbpalette kontrastreicher; farbige Buttons (Grün/Rot/Orange/Blau/Lila/Gelb) korrekt unter Forest-Theme

### AZ & Reisekosten *(neuer Tab, neue Datei `az_reisekosten.py`)*
- Persönliche Daten speichern (Name, Wohnort, Personal-Nr.)
- Wochenansicht mit editierbaren Feldern: Status, Start/Ende/Pause, Stunden (live berechnet)
- Detail-Panel pro Tag: Auftragsnummer, Kunde, Standort, Reiseweg, Start-/Endpunkt
- Reisekosten-Felder: Art, Land, Übernachtung, Mahlzeiten, km, Sonstiges
- KW-Daten werden lokal gespeichert (`res/kw_data/`)
- Stundenübersicht PDF: komplette Monatstabelle (A4 Querformat)
- Excel Reisekostenabrechnung (FB_0020): befüllt Vorlage inkl. Pauschalen-Felder

</details>

---

<details>
<summary><b>v1.7.0</b> — FTP-Verbesserungen · Upload-Funktionen · Tooltips · Button-Cleanup</summary>

### FTP Tab
- Ordner werden immer zuerst angezeigt, dann Dateien (alphabetisch)
- Icons je Dateityp: 📁 Ordner · 📝 Labels · ⚙ Configs · 🖨 PrintCtl · 🖼 Logos · 📄 Rest
- Download-Button funktioniert für Dateien und Ordner (rekursiv mit Fortschrittsanzeige)
- Backup-Button (lila): lädt alles rekursiv herunter und packt als ZIP
- Schriftgröße Tab-Leiste: 9 → 11 pt
- `askopenfilenames` → mehrere Dateien gleichzeitig hochladbar
- Neuer Button „Ordner hochladen": rekursiver Upload mit automatischer MKD-Ordnererstellung
- Ziel wird aus dem aktuell markierten Baum-Element abgeleitet

### Buttons
- Alle nicht-funktionierenden G-PRINT Befehle entfernt
- Einheitliche Farbzuordnung auf allen Tabs

### Hilfsfunktionen
- Maus-Hover-Tooltips mit detaillierter Beschreibung bei ausgewählten Funktionen

</details>

---

<details>
<summary><b>v1.6.0</b> — Label Editor Fixes · Logo Editor Verbesserungen</summary>

### Label Editor
- Linespace-Skalierung entfernt (hatte `px_size` auf bis zu −6 reduziert)
- Textposition: `anchor="sw"` + `cy_b` — Text an Unterkante ausgerichtet (Druckerlogik: Y=0 = unterste Zeile)
- MLG-Rendering: eigene 1-Bit-Darstellung (Pillow Fonts Library entfernt)
- Alle Bildformate werden jetzt selbst gerendert

### Logo Editor
- Schachbrett-Hintergrund für transparente (nicht gedruckte) Pixel
- Schwarze Pixel: `(20, 20, 20)` statt reines Schwarz
- Vorschau-Pixel beim Zeichnen von Linien/Rechtecken (grau mit sauberem Fill)
- Info-Zeile zeigt Anzahl gesetzter Pixel: z. B. *„32 × 10 px · 87 Pixel gesetzt"*
- Schneller bei großen Logos: PIL rendert alles auf einmal

</details>

---

<details>
<summary><b>v1.5.0</b> — Neues Design · FTP-Fixes · Label/Logo Editor Erweiterungen</summary>

### Design — Elegant Charcoal
- Hintergrund `#1a1a1a`, Text `#e0e0e0`, Akzent `#5a9fd4` (Steel Blue)
- Buttons: dunkler Hintergrund + Akzentfarbe als Text
- Header: 2 px Akzentlinie (statt 3 px), 52 px kompakt
- Treeview: Zeilenhöhe 24 px, flache Spaltenköpfe

### FTP
- Dateibaum-Fix: Umstellung von `ftp.dir()` auf `ftp.mlsd()` (RFC 3659), Fallback auf `ftp.nlst()`
- Standardpasswort AJD korrigiert (`User` mit großem U)
- FTP Timeout auf 120 s erhöht

### Label Editor
- Zähler-XML komplett auf Geräte-Format umgestellt (Child-Elemente: FORMAT, AUTOSTOP, RESETABLE, …)
- Zähler-Properties erweitert: Format-Dropdown, Autostop, Rückstellbar, Alpha-Code, Timed Reset, …
- Objektrahmen-Badge zeigt jetzt X Y H L
- Dots/Pixel-Modus: neuer Toggle (Dots = Tintenpunkte als Kreise; Pixel = klassisches Rechteck)
- Linke Seitenleiste: 185 → 215 px

### Logo Editor
- PNG speichern (transparenter Hintergrund)
- JPG speichern (weißer Hintergrund)

</details>

---

<details>
<summary><b>v1.4.0</b> — FTP-Tab · Monitor-Tab · Auto-Update · Drucker-Profile · Befehlshistorie</summary>

### FTP und Monitor Tab
- Monitor: TCP-Proxy (Steuerung → PC → Drucker) + Mock-Drucker für Tests
- FTP: Verbindung, Verzeichnis-Browser, Upload/Download, direkt im Editor öffnen
- Geräteprofil-Auswahl (AJD / AJ5II / Test) mit vorausgefüllten FTP-Zugangsdaten

### App & Build
- Fenster startet maximiert (Titelleiste sichtbar)
- `BUILD.bat` überarbeitet — beendet laufende Instanz automatisch
- `update_version.py` als separates Build-Hilfsskript

### Allgemein
- Auto-Update beim Start (konfigurierbar, An/Aus, URL einstellbar)
- Drucker-Profile: mehrere IP/Port-Konfigurationen speichern und laden
- Befehlshistorie: letzte 20 Befehle, per Doppelklick erneut senden
- Auto-Ping: optionaler Hintergrund-Ping alle 30 Sekunden
- Session-Log: automatisch in `res/logs/` gespeichert
- Tab PrintControls hinzugefügt (`.ctl`-Dateien)
- Neue Schnellbefehle: `BOARDINFO`, `BOARDINFO_EXT`

### PrintModes
- `pm05` (5 px), `pm07` (7 px), `pm48` (48 px) hinzugefügt

### Label Editor — Fixes
- Objektbreite korrigiert (Bounding Box passt zur tatsächlichen Textbreite)
- MAG 2×/3×/4×: Text wird nur noch horizontal gestreckt
- Linie / Rechteck / Ellipse: Koordinaten und Bounding Box korrigiert
- NEG=1 Objekte aus Kollisionserkennung ausgeschlossen
- Proportionale Schriften: Rahmen mit echter tkinter-Rendering-Breite gemessen

### Label Editor — Neue Features
- Undo / Redo (50 Schritte) — `Strg+Z` / `Strg+Y`
- Tastenkürzel: `Entf`, Pfeiltasten, `Strg+Mausrad`
- Zoom bis 32×
- Kollisionserkennung (überlappende Objekte → orange markiert)
- Resize-Handle (oranges Quadrat oben rechts)
- Drehung, Duplizieren, Spiegeln, Ausrichten, Zentrieren
- Logo-Objekt als neuer Objekttyp
- Zähler: Eigener Zähler (NUMB), Produktzähler (#PCNT), Globaler Zähler (#GCNT)

### Logo Editor
- PNG und WebP speichern (transparenter Hintergrund)
- `res/logos/` wird automatisch angelegt

</details>

---

<details>
<summary><b>v1.3.0</b> — Dark-Theme · Label Editor Basis · About-Dialog</summary>

### App & Build
- Dark-Theme mit Catppuccin-Farbpalette
- Uhr + IP-Anzeige im Header
- About-Dialog mit Tastenkürzel-Übersicht

### Label Editor
- Pixel-genaue Font-Darstellung mit geladenen TTF-Druckerfonts
- Y=0 = Unterkante (Drucker-Koordinatensystem)
- Zoom 1×–8×, Hintergrund-Raster wählbar
- Objekt-Typen: Text, Datum/Zeit, Zähler, DMC, Barcode/QR, Linie, Rechteck, Logo
- Drag & Drop zum Verschieben
- Properties-Panel mit allen Objekt-Eigenschaften
- XML-Vorschau live (ein-/ausklappbar)

</details>

---

<details>
<summary><b>v1.2.0</b> — Label Editor & Logo Editor (erste Versionen)</summary>

### Label Editor
- Visueller Label-Editor als eigener Tab
- Objekte per Klick hinzufügen: Text, Datum/Zeit, Zähler, DMC, Barcode/QR, Linie, Rechteck
- Label direkt aus dem Editor an Drucker senden

### Logo Editor
- Paint-ähnlicher Pixel-Editor als eigener Tab
- Größe frei wählbar (B × H in Pixeln)
- Werkzeuge: Stift, Radierer, Füllen, Linie, Rechteck
- Speichern als SVG; Laden von SVG / MLG / PNG / BMP

</details>

---

<details>
<summary><b>v1.1.0</b> — Labels · Configs · PrintControls · Funktionen-Tab</summary>

### Neue Tabs
- **Labels** — lokale Label-Dateien verwalten, auf Drucker laden/speichern (`SAVELAB`, `LOADLAB`)
- **Configs** — Konfigurations-Dateien verwalten und übertragen (`LOADCONFIG`)
- **PrintControls** — `.ctl`-Dateien, Pfad `user/config/PrintControl/`
- **Funktionen** — eigene G-PRINT XML-Befehle speichern und wiederverwenden

### Netzwerk
- Subnetz-Prüfung (PC und Drucker im gleichen Netz?)

</details>

---

<details>
<summary><b>v1.0.0</b> — Erstveröffentlichung</summary>

### Grundfunktionen
- Verbindung zum alphaJET per TCP/IP (G-PRINT Protokoll)
- Netzwerk-Tab: IP, Port, Subnetz, Gateway, Name, Timeout konfigurieren
- Befehle-Tab: Schnellbefehle + freier XML-Befehl-Editor
- Kommunikations-Log mit Zeitstempel (ein-/ausklappbar)
- Konfiguration wird lokal gespeichert (`res/config.json`)
- `START.bat` prüft Python-Installation

</details>

---

<div align="center">

**alphaJET Interface-Tool**  
Marvin Köllner · Koenig & Bauer Coding  
*Nur zur internen Verwendung · Vertraulich*

</div>
