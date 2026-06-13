[![Benutzerhandbuch](https://img.shields.io/badge/📋_Benutzerhandbuch-1a3a5c?style=flat-square)](README.md) [![Security](https://img.shields.io/badge/🔒_Security-1a3a5c?style=flat-square)](SECURITY.md) [![Changelog](https://img.shields.io/badge/📝_Changelog-1a3a5c?style=flat-square)](CHANGELOG.md) [![Requirements](https://img.shields.io/badge/📦_Requirements-1a3a5c?style=flat-square)](requirements.txt)
# alphaJET Interface-Tool — Benutzerhandbuch

> **Internes Servicetechniker-Tool** zur Fernsteuerung und Konfiguration von Koenig & Bauer alphaJET CIJ-Druckern über das G-PR(INT)-Protokoll (TCP/IP).

![Version](https://img.shields.io/badge/Version-2.1.3-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Protocol](https://img.shields.io/badge/Protokoll-G--PR(INT)%20V3.0.0-orange)
![Python](https://img.shields.io/badge/Python-3.11%2B-yellow)
![Internal](https://img.shields.io/badge/Verwendung-Intern%20%2F%20Vertraulich-red)

---
Dieses Dokument erklärt den Aufbau und die Funktionen des alphaJet Interface-Tool.

## Inhaltsverzeichnis

- [Übersicht](#übersicht)
- [Systemvoraussetzungen & Installation](#systemvoraussetzungen--installation)
- [Programmoberfläche](#programmoberfläche)
- [Tabs im Überblick](#tabs-im-überblick)
  - [Netzwerk](#netzwerk)
  - [Befehle](#befehle)
  - [Funktionen](#funktionen)
  - [Labels](#labels)
  - [Configs](#configs)
  - [PrintControls](#printcontrols)
  - [Monitor](#monitor)
  - [Label Editor](#label-editor)
  - [Logo Editor](#logo-editor)
  - [FTP](#ftp)
  - [AZ & Reisekosten](#az--reisekosten)
- [Kommunikations-Log](#kommunikations-log)
- [Tastenkürzel](#tastenkürzel)
- [Farbkodierung](#farbkodierung-der-buttons)
- [Ordnerstruktur](#ordnerstruktur)
- [Fehlerbehebung](#fehlerbehebung)
- [Abhängigkeiten (SBOM)](#abhängigkeiten--sbom)
- [Versionshistorie](#versionshistorie)

---

## Übersicht

Das **alphaJET Interface-Tool** ermöglicht Servicetechnikern die vollständige Fernsteuerung und Diagnose von alphaJET CIJ-Druckern. Es kommuniziert über G-PRINT XML-Befehle via TCP/IP und bietet darüber hinaus lokale Editoren, FTP-Zugriff und Zeiterfassung.

| Bereich         | Funktion                                                                 |
|-----------------|--------------------------------------------------------------------------|
| Netzwerk        | Drucker-IP konfigurieren, Verbindung testen, Profile speichern           |
| Befehle         | G-PRINT XML-Befehle senden (Schnellbefehle + freier Editor)              |
| Funktionen      | Eigene Befehle speichern und wiederverwenden                              |
| Labels          | Label-Dateien verwalten, bearbeiten, auf Drucker übertragen              |
| Configs         | Config-Dateien (`.pcf`) verwalten und auf Drucker laden                  |
| PrintControls   | PrintControl-Dateien (`.ctl`) verwalten und laden                        |
| Monitor         | TCP-Proxy, Mock-Drucker und Mock-FTP-Server für Tests                    |
| Label Editor    | Visuelle Labels per Drag & Drop erstellen und bearbeiten                 |
| Logo Editor     | Pixel-Logos zeichnen (MLG / BMP / PNG / JPG / SVG)                      |
| FTP             | Drucker-Dateisystem browsen, Dateien hoch-/herunterladen, Backup         |
| AZ & Reisekosten| Arbeitszeiten erfassen, Salesforce FSL synchronisieren, Excel-Export     |

---

## Systemvoraussetzungen & Installation

| Anforderung       | Details                                         |
|-------------------|-------------------------------------------------|
| Betriebssystem    | Windows 10 / 11 (64-bit empfohlen)              |
| Python            | 3.11+ *(nur bei .py-Quellversion, nicht .exe)*  |
| Netzwerk          | Gleicher Subnet wie der Drucker                 |

### Starten

```
alphaJet-InterfaceTool.exe
```

Einfach die ausführbare Datei per Doppelklick starten – keine Installation erforderlich.

### Auto-Update

Beim Programmstart wird automatisch nach einer neueren Version gesucht (sofern konfiguriert). Die Update-URL wird im Tab **Netzwerk → Software-Update** eingestellt.

> 🔒 **Sicherheitshinweis (CRA):** Jedes heruntergeladene Update wird per SHA-256-Prüfsummenvergleich verifiziert. Ein Update wird nur installiert, wenn der Hash übereinstimmt.

### Dark / Light Mode

Wechsel per Klick auf das **☀ / ☾**-Symbol in der Titelleiste. Das Programm startet danach automatisch neu.

---

## Programmoberfläche

| Element                        | Bedeutung                                          |
|--------------------------------|----------------------------------------------------|
| `K & B`                        | Branding (grün)                                    |
| `v2.1.1`                       | Aktuelle Programmversion                           |
| `IP: 192.168.x.x`              | Aktuell konfigurierte Drucker-IP                   |
| `● Nicht verbunden / Verbunden`| Verbindungsstatus (rot / grün)                     |
| Uhrzeit & Datum                | Aktuelle Systemzeit (rechts)                       |
| `☀ / ☾`                        | Theme-Toggle: Dark / Light Mode                    |
| `[?]`                          | Über das Programm / Tastenkürzel-Übersicht         |

Tabs werden beim ersten Aufrufen **lazy initialisiert** (kein unnötiger Speicherverbrauch beim Start).

---

## Tabs im Überblick

### Netzwerk

Drucker-Verbindung konfigurieren, testen und Profile verwalten.

| Feld               | Standard        | Beschreibung                         |
|--------------------|-----------------|--------------------------------------|
| IP-Adresse         | `192.168.1.100` | IPv4-Adresse des Druckers            |
| Port               | `3002`          | TCP-Port für G-PRINT (Standard v2.x) |
| Subnetzmaske       | `255.255.255.0` | Netzwerkmaske                        |
| Standard-Gateway   | `0.0.0.0`       | Standard-Gateway                     |
| Drucker-Name       | `alphaJET`      | Bezeichnung für das Geräteprofil     |
| Timeout            | `5` Sek.        | Verbindungs-Timeout                  |
| DHCP               | aus             | DHCP am Drucker aktivieren           |

> ⚠️ **Hinweis:** Standard-Port ist seit v2.x **3002** (zuvor 3000). Nach Änderungen immer **[Speichern]** klicken.

**Verbindungstest-Buttons:**

| Button              | Funktion                                                |
|---------------------|---------------------------------------------------------|
| Verbindung prüfen   | Sendet `<GP><MAINSTATE/></GP>` und zeigt Ergebnis an    |
| Drucker-Status      | Fragt den aktuellen Drucker-Status ab                   |
| Trennen             | Beendet die aktive Verbindung                           |

**Netzwerk-Helfer:** Zeigt alle IP-Adressen des PCs und prüft, ob PC und Drucker im gleichen Subnetz sind.
- 🟢 **Grün:** OK – PC und Drucker sind im selben Subnetz
- 🔴 **Rot:** ACHTUNG: Nicht im gleichen Subnetz! – Mit Korrekturhinweis

---

### Befehle

G-PRINT Befehle senden – per Schnellzugriff oder freiem Editor.

**Schnell-Befehle:**

| Button             | G-PRINT Befehl                                | Funktion               |
|--------------------|-----------------------------------------------|------------------------|
| Verbindungstest    | `<GP><MAINSTATE/></GP>`                       | Drucker erreichbar?    |
| Status abfragen    | `<GP><SYS><STATE/></SYS></GP>`                | System-Status          |
| Firmware-Version   | `<GP><VERSION/></GP>`                         | Versionsinfo abfragen  |
| Board-Info         | `<GP><BOARDINFO/></GP>`                       | Hardware-Info          |
| Board-Info (ext.)  | `<GP><BOARDINFO_EXT/></GP>`                   | Erweiterte Hardware-Info|
| Datum / Uhrzeit    | `<GP><SYS><DATETIME/></SYS></GP>`             | Datum/Uhrzeit abfragen |
| GUI sperren        | `<GP><GUICONTROL aMode="1">...</GP>`          | Drucker-GUI sperren    |
| GUI schließen      | `<GP><GUICONTROL aMode="2">...</GP>`          | Drucker-GUI schließen  |
| GUI neu starten    | `<GP><GUICONTROL aMode="3">...</GP>`          | Drucker-GUI neu starten|
| Drucken START      | `<GP><START/></GP>`                           | Druck starten          |
| Drucken STOP       | `<GP><STOP/></GP>`                            | Druck stoppen          |

**Befehlsverlauf:** Die letzten 20 gesendeten Befehle werden gespeichert. Doppelklick = erneut senden.  
**Auto-Ping:** Sendet alle 30 Sekunden automatisch einen Verbindungstest.

---

### Funktionen

Eigene, häufig benötigte G-PRINT Befehle speichern und verwalten (gespeichert in `functions.json`).

```xml
<!-- Beispiel: Global-Zähler auf 0 setzen -->
<?xml version="1.0" ?>
<GP>
  <GLOBALCOUNTER aResetable="1">0</GLOBALCOUNTER>
</GP>
```

---

### Labels

Verwaltung lokaler Label-Dateien (`.txt` / `.gp` / `.lab`) und direktes Übertragen auf den Drucker.

| Button                         | Funktion                                              |
|--------------------------------|-------------------------------------------------------|
| + Neu                          | Neue leere Label-Datei anlegen                        |
| Importieren                    | Externe Datei ins lokale Labels-Verzeichnis kopieren  |
| Aktualisieren                  | Dateiliste neu laden                                  |
| Löschen                        | Ausgewählte Datei löschen                             |
| Lokal speichern                | Inhalt in der lokalen Datei speichern                 |
| Label speichern (im Drucker)   | Label direkt in den Drucker-Speicher übertragen       |
| Label laden (im Drucker-Puffer)| Label aus dem Drucker-Puffer laden                    |
| Formatieren                    | XML automatisch einrücken                             |

---

### Configs

Verwaltung lokaler Konfigurations-Dateien (`.pcf`).

| Button                    | Funktion                                         |
|---------------------------|--------------------------------------------------|
| Config lokal speichern    | Geänderten Inhalt lokal sichern                  |
| Config laden (in Tool)    | Config-Datei vom Drucker in den Editor laden     |
| Config laden (im Drucker) | Config direkt in den Drucker laden (G-PRINT)     |
| Formatieren               | XML-Formatierung korrigieren                     |

---

### PrintControls

Verwaltung lokaler PrintControl-Dateien (`.ctl`).

| Button                          | Funktion                                     |
|---------------------------------|----------------------------------------------|
| PrintControl lokal speichern    | Geänderten Inhalt lokal sichern              |
| PrintControl laden (in Tool)    | PrintControl vom Drucker laden               |
| PrintControl laden (im Drucker) | PrintControl direkt in den Drucker laden     |
| Formatieren                     | XML-Formatierung korrigieren                 |

---

### Monitor

Drei unabhängige Test- und Debugging-Werkzeuge.

#### TCP-Proxy
Leitet Datenverkehr zwischen einem externen Steuerungssystem und dem Drucker durch und protokolliert alle G-PRINT Nachrichten mit.

**Verwendung:**
1. Im Netzwerk-Tab: Drucker-Port auf `3002`, Drucker-IP auf tatsächliche Drucker-IP setzen
2. Lausch-Port und Weiterleitungs-IP:Port konfigurieren
3. **[Proxy starten]** klicken → Alle Nachrichten erscheinen im Log

#### Mock-Drucker
Simuliert einen alphaJET-Drucker auf dem lokalen PC. Vollständiges Testen ohne physischen Drucker möglich.

**Einrichtung:** Im Netzwerk-Tab IP = `127.0.0.1`, Port = `3002` → Mock-Port im Monitor-Tab einstellen → **[Mock starten]**

#### Mock FTP-Server
Simulierter alphaJET FTP-Server mit Testdateien.

| Parameter | Wert      |
|-----------|-----------|
| IP        | 127.0.0.1 |
| Port      | 2121      |
| User      | test      |
| Passwort  | test      |

---

### Label Editor

Visueller Editor zum Erstellen und Bearbeiten von alphaJET-Labels per Drag & Drop. Alle Änderungen werden sofort als G-PRINT XML dargestellt.

**Unterstützte Objekt-Typen:**

| Typ            | Beschreibung                                              |
|----------------|-----------------------------------------------------------|
| `T` Text       | Statischer oder dynamischer Texteintrag                   |
| Datum / Zeit   | Automatisches Datum/Uhrzeit-Feld mit konfigurierbarem Format |
| `#` Zähler     | Produktions- oder Stückzähler                             |
| DMC (Matrix)   | Data-Matrix-Code (2D), 10×10 bis 64×64                    |
| Barcode / QR   | EAN-128, Code39, Code93 und QR-Code                       |
| Logo           | Pixel-Logo (`.mlg` / `.svg`) aus dem Logos-Ordner        |
| `—` Linie      | Horizontale oder vertikale Trennlinie                     |
| `[ ]` Rechteck | Rechteck-Element                                          |

> 💡 **Tipp:** TTF-Druckerfonts aus dem `fonts/`-Ordner (neben der `.exe`) werden beim Start automatisch geladen für eine exaktere Druckervorschau.

---

### Logo Editor

Pixel-Editor zum Erstellen und Bearbeiten von Drucker-Logos.

| Button           | Funktion                                    |
|------------------|---------------------------------------------|
| Größe setzen     | Canvas-Größe auf Breite/Höhe anpassen       |
| Alles löschen    | Alle Pixel löschen (Canvas leeren)          |
| Invertieren      | Alle Pixel invertieren (schwarz ↔ weiß)    |
| Logo laden       | MLG-Datei aus dem Logos-Ordner laden        |
| Als MLG speichern| Als alphaJET-Logo-Datei (`.mlg`) exportieren|
| Als BMP speichern| Als BMP-Bitmap exportieren                  |
| Als PNG speichern| Als PNG-Bild exportieren                    |
| Als JPG speichern| Als JPEG-Bild exportieren                   |

---

### FTP

Direkter Zugriff auf das Dateisystem des Druckers über FTP.

**Standard-Zugangsdaten:**

| Gerätetyp | User   | Passwort    | Port |
|-----------|--------|-------------|------|
| AJD       | `User` | `user$ftp`  | 21   |
| AJ5       | `User` | `c0d1n9b`   | 21   |
| Mock      | `test` | `test`      | 2121 |

> Zugangsdaten können durch `res/ftp_credentials.json` überschrieben werden.

**Dateioperationen:**

| Button            | Funktion                                              |
|-------------------|-------------------------------------------------------|
| Download → lokal  | Ausgewählte Datei/Ordner herunterladen                |
| Dateien hochladen | Lokale Dateien auf den Drucker hochladen              |
| Ordner hochladen  | Lokalen Ordner rekursiv hochladen                     |
| Datei löschen     | Ausgewählte Datei/Ordner löschen                      |
| Alles als ZIP     | Gesamtes Drucker-Dateisystem als ZIP sichern          |

---

### AZ & Reisekosten

Arbeitszeiten erfassen, mit Salesforce FSL synchronisieren und Excel-Reports exportieren.

#### Salesforce-Verbindung (Session-ID)

1. VPN verbinden (GlobalProtect)
2. Im Tool: **[Salesforce in Chrome öffnen]** klicken
3. Mit K&B-SSO-Account einloggen
4. `F12` → Developer Tools → Application → Cookies → `koenig-bauer.lightning.force.com`
5. Zeile `sid` suchen → Wert kopieren (`Strg+C`)
6. Feld „Session ID" im Tool einfügen → **[Verbinden (Session ID)]** klicken

> ⏱️ Die Session-ID ist ca. **8 Stunden** gültig. Sie wird mit **[Daten speichern]** dauerhaft gespeichert.

#### Allgemeinkosten-Codes (Innendienst)

| Code | Beschreibung                        |
|------|-------------------------------------|
| 0010 | Customer Preparation                |
| 0020 | Service Hotline                     |
| 0060 | Internal Meetings / Trainings       |
| 0080 | Materials Management Activities     |
| 0090 | Documentation Activities            |
| 0140 | Automotive Workshop / Inspection    |
| 0190 | Dealer & Subsidiary Support         |
| 2100 | Activities Service Cloud            |

---

## Kommunikations-Log

| Farbe  | Bedeutung                      |
|--------|--------------------------------|
| 🔵 Blau | Gesendete Befehle (`→`)        |
| 🟢 Grün | Empfangene Antworten (`←`)     |
| 🔴 Rot  | Fehlermeldungen                |
| 🟣 Lila | Info-Meldungen                 |
| 🟡 Gelb | Warnungen                      |

Logs werden automatisch in `res/logs/` gespeichert. Größe per `[S]` / `[M]` / `[L]` anpassbar.

---

## Tastenkürzel

### Allgemein

| Kürzel   | Funktion                   |
|----------|----------------------------|
| `Strg+S` | Speichern (aktiver Tab)    |
| `Strg+Z` | Rückgängig                 |
| `Strg+Y` | Wiederholen                |

### Label Editor

| Kürzel              | Funktion                       |
|---------------------|--------------------------------|
| `Strg+Z`            | Rückgängig (bis 50 Schritte)   |
| `Strg+Y`            | Wiederholen                    |
| `Entf`              | Ausgewähltes Objekt löschen    |
| `↑ ↓ ← →`           | Objekt pixelweise verschieben  |
| `Strg + Mausrad`    | Zoom ein-/auszoomen            |
| `Mausrad`           | Vertikal scrollen              |
| `Shift + Mausrad`   | Horizontal scrollen            |

---

## Farbkodierung der Buttons

| Farbe   | Bedeutung              | Beispiele                                      |
|---------|------------------------|------------------------------------------------|
| 🟢 Grün  | Speichern / Bestätigen | Speichern, Verbinden, Lokal speichern          |
| 🔵 Blau  | Laden / Abrufen        | Laden, IPs aktualisieren, Erneut senden        |
| 🔴 Rot   | Löschen / Stoppen      | Löschen, Proxy stoppen, Trennen                |
| 🟠 Orange| Hochladen / Übertragen | Dateien hochladen, Ordner hochladen            |
| 🟣 Lila  | Sonderfunktionen       | Formatieren, Backup                            |
| 🟡 Gelb  | Test-Funktionen        | Mock starten, FTP-Server starten               |

---

## Ordnerstruktur

```
alphaJet-InterfaceTool.exe
fonts/                        ← Drucker-TTF-Fonts (optional)
res/
├── config.json               ← Drucker-Konfiguration (IP, Port, Theme)
├── functions.json            ← Gespeicherte Funktionen
├── profiles.json             ← Drucker-Profile
├── user_profile.json         ← Persönliche Daten (AZ-Tab)
├── sf_config.json            ← Salesforce-Konfiguration & Session-ID
├── kunden_vorlagen.json      ← Kunden-Vorlagen (AZ-Tab)
├── ftp_credentials.json      ← Eigene FTP-Zugangsdaten (optional)
├── labels/                   ← Lokale Label-Dateien
├── configs/                  ← Lokale Config-Dateien (.pcf)
├── printcontrol/             ← Lokale PrintControl-Dateien (.ctl)
├── logos/                    ← Lokale Logo-Dateien (.mlg, .svg, .png)
├── logs/                     ← Sitzungs-Logs (automatisch)
├── kw_data/                  ← Arbeitszeit-Daten pro KW (AZ-Tab)
├── templates/                ← Excel-Vorlagen (FB_0020, FB_0221)
├── mock_ftp/                 ← Testdateien für Mock FTP-Server
└── themes/
    ├── forest-dark.tcl       ← Dark-Mode Theme
    └── forest-light.tcl      ← Light-Mode Theme
```

---

## Fehlerbehebung

<details>
<summary>🔴 Verbindung schlägt fehl – <code>WinError 10060 timeout</code></summary>

PC und Drucker nicht im gleichen Subnetz oder falsche IP/Port.

1. Netzwerk-Tab → **Netzwerk-Helfer** prüfen
2. PC-IP anpassen (Windows-Netzwerkeinstellungen)
3. Port prüfen (Standard seit v2.x: **3002**)
4. Firewall prüfen

</details>

<details>
<summary>🔴 FTP-Verbindung schlägt fehl – <code>530 Login incorrect</code></summary>

- AJD → `User` / `user$ftp`
- AJ5 → `User` / `c0d1n9b`
- Eigene Zugangsdaten in `res/ftp_credentials.json` hinterlegen

</details>

<details>
<summary>🔴 Salesforce Login schlägt fehl – <code>HTTP Error 403 Forbidden</code></summary>

- Beide SID-Werte nacheinander probieren (manchmal werden 2 angezeigt)
- In Salesforce prüfen ob noch eingeloggt
- SID evtl. abgelaufen → erneuter Login nötig

</details>

<details>
<summary>⚠️ Label-Editor zeigt Schrift falsch an</summary>

TTF-Druckerfonts in den `fonts/`-Ordner (neben der `.exe`) ablegen. Das Tool lädt sie automatisch beim Start.

</details>

<details>
<summary>⚠️ Auto-Update funktioniert nicht</summary>

1. Netzwerk-Tab → **Software-Update**: Update-URL eintragen
2. „Beim Start automatisch prüfen" aktivieren
3. **[URL speichern]** klicken

</details>

---

## Abhängigkeiten / SBOM

*Software Bill of Materials gemäß Annex I CRA*

| Komponente        | Version     | Typ            | Verwendung                                    |
|-------------------|-------------|----------------|-----------------------------------------------|
| Python            | 3.11.x      | Laufzeit       | Basisinterpreter                              |
| tkinter / ttk     | (stdlib)    | GUI            | Basis-UI-Framework                            |
| socket            | (stdlib)    | Netzwerk       | TCP/IP-Kommunikation                          |
| ftplib            | (stdlib)    | Netzwerk       | FTP-Client                                    |
| hashlib           | (stdlib)    | Sicherheit     | SHA-256-Verifikation bei Updates              |
| threading         | (stdlib)    | System         | Nebenläufige Netzwerkoperationen              |
| xml.etree         | (stdlib)    | Daten          | G-PRINT XML-Verarbeitung                      |
| Pillow            | 11.x        | Drittanbieter  | Bild-Rendering im Label/Logo-Editor           |
| openpyxl          | 3.1.x       | Drittanbieter  | Excel-Export (lazy import)                    |
| pyftpdlib         | 2.x         | Drittanbieter  | Mock FTP-Server im Monitor-Tab                |
| forest-dark.tcl   | –           | Theme-Asset    | Visuelles Design (Dark Mode)                  |
| forest-light.tcl  | –           | Theme-Asset    | Visuelles Design (Light Mode)                 |

> `reportlab` und `CustomTkinter` wurden mit v2.0 entfernt. GUI-Framework ist jetzt **tkinter/ttk**, Grafiken über **Pillow**.

---

## Versionshistorie

| Version | Datum      | Änderungen                                                                                                                                                          |
|---------|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 2.1.1   | 12.06.2026 | Light/Dark-Mode-Toggle, SHA-256 Update-Verifikation, Port-Standard 3002, `ftp_credentials.json`, `fonts/`-Ordner, Mock-FTP im Monitor-Tab, Logo-Editor-Exportformate (BMP/PNG/JPG), CRA-Compliance, CustomTkinter/reportlab entfernt → tkinter/ttk + Pillow |
| 1.9.0   | –          | Initiale veröffentlichte Version                                                                                                                                    |

---

<div align="center">

**alphaJET Interface-Tool v2.1.1**  
Marvin Köllner · Koenig & Bauer Coding · 12.06.2026  
*Nur zur internen Verwendung · Vertraulich*

</div>
