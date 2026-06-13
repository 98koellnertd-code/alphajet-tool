
Koenig & Bauer Coding
alphaJET Interface-Tool
Benutzerhandbuch — Version 2.1.1

Produkt:	alphaJET Interface-Tool
Version:	2.1.1
Protokoll:	G-PR(INT) V3.0.0 · TCP/IP · XML 1.0
Plattform:	Windows 10 / 11 (64-bit)
Datum:	12.06.2026
Autor:	Marvin Köllner · Koenig & Bauer Coding

Nur zur internen Verwendung · Vertraulich
 
Abhängigkeiten & SBOM

Nachfolgende Tabelle listet alle Softwarekomponenten (Software Bill of Materials gemäß Annex I CRA).

Komponente	Version	Typ	Verwendung
Python	3.11.x	Laufzeit	Basisinterpreter
tkinter / ttk	(stdlib)	GUI	Basis-UI-Framework
socket	(stdlib)	Netzwerk	TCP/IP-Kommunikation
ftplib	(stdlib)	Netzwerk	FTP-Client
hashlib	(stdlib)	Sicherheit	SHA-256-Verifikation bei Updates (neu v2.x)
threading	(stdlib)	System	Nebenläufige Netzwerkoperationen
xml.etree	(stdlib)	Daten	G-PRINT XML-Verarbeitung
Pillow	11.x	Drittanbieter	Bild-Rendering im Label/Logo-Editor
openpyxl	3.1.x	Drittanbieter	Excel-Export (lazy import)
pyftpdlib	2.x	Drittanbieter	Mock FTP-Server im Monitor-Tab (neu v2.x)
forest-dark.tcl	–	Theme-Asset	Visuelles Design (Dark Mode)
forest-light.tcl	–	Theme-Asset	Visuelles Design (Light Mode, neu v2.x)

Hinweis:

reportlab und CustomTkinter wurden mit v2.0 entfernt. Grafiken werden ausschließlich über Pillow realisiert; das GUI-Framework ist jetzt tkinter/ttk.
 
Inhaltsverzeichnis
1.   Übersicht
2.   Systemvoraussetzungen & Installation
3.   Programmoberfläche
4.   Tab: Netzwerk
5.   Tab: Befehle
6.   Tab: Funktionen
7.   Tab: Labels
8.   Tab: Configs
9.   Tab: PrintControls
10.  Tab: Monitor
11.  Tab: Label Editor
12.  Tab: Logo Editor
13.  Tab: FTP
14.  Tab: AZ & Reisekosten
15.  Kommunikations-Log
16.  Tastenkürzel
17.  Farbkodierung der Buttons
18.  Ordnerstruktur
19.  Fehlerbehebung
 
1. Übersicht

Das alphaJET Interface-Tool ist ein internes Servicetechniker-Programm zur Fernsteuerung und Konfiguration von Koenig & Bauer alphaJET CIJ-Druckern über das G-PR(INT) Protokoll (TCP/IP).

Funktionsumfang
Bereich	Funktion
Netzwerk	Drucker-IP konfigurieren, Verbindung testen, Profile speichern
Befehle	G-PRINT XML-Befehle senden (Schnellbefehle + freier Editor)
Funktionen	Eigene Befehle speichern und wiederverwenden
Labels	Label-Dateien verwalten, im Editor öffnen, auf Drucker übertragen
Configs	Config-Dateien (.pcf) verwalten und auf Drucker laden
PrintControls	PrintControl-Dateien (.ctl) verwalten und laden
Monitor	TCP-Proxy, Mock-Drucker und Mock-FTP-Server für Tests
Label Editor	Visuellen Labels per Drag & Drop erstellen und bearbeiten
Logo Editor	Pixel-Logos zeichnen (MLG/BMP/PNG/JPG/SVG)
FTP	Drucker-Dateisystem browsen, Dateien hoch-/herunterladen, Backup
AZ & Reisekosten	Arbeitszeiten erfassen, Salesforce FSL synchronisieren, Excel-Export
 
2. Systemvoraussetzungen & Installation
Voraussetzungen
•	Windows 10 oder Windows 11 (64-bit empfohlen)
•	Python 3.11+ (nur bei Verwendung der .py-Quellversion, nicht bei .exe)
•	Netzwerkverbindung zum Drucker (gleicher Subnet)

Starten
Ausführbare Datei doppelklicken:
alphaJet-InterfaceTool.exe

Auto-Update
Beim Programmstart wird automatisch nach einer neueren Version gesucht (sofern konfiguriert). Die Update-URL wird im Tab Netzwerk → Software-Update eingestellt.

Sicherheitshinweis (CRA):
Die Integrität jedes heruntergeladenen Updates wird durch SHA-256-Prüfsummenvergleich verifiziert. Ein Update wird nur installiert, wenn der Hash übereinstimmt.

Dark / Light Mode
Das Tool unterstützt Dark Mode und Light Mode. Wechsel per Klick auf das ☀/☾-Symbol in der Titelleiste. Das Programm startet danach automatisch neu.
 
3. Programmoberfläche
Header-Bereich
Element	Bedeutung
K & B	Branding (grün)
v2.1.1	Aktuelle Programmversion
IP: 192.168.x.x	Aktuell konfigurierte Drucker-IP
● Nicht verbunden / Verbunden	Verbindungsstatus (rot / grün)
Uhrzeit & Datum	Aktuelle Systemzeit (rechts)
☀ / ☾	Theme-Toggle: Dark Mode / Light Mode
[?]	Über das Programm / Tastenkürzel-Übersicht

Tab-Leiste
Die Tab-Leiste enthält alle Funktionsbereiche. Der aktive Tab wird grün hervorgehoben. Tabs werden beim ersten Aufrufen lazy initialisiert.
 
4. Tab: Netzwerk
 

4.1 Drucker-Konfiguration
Feld	Standard	Beschreibung
IP-Adresse des Druckers	192.168.1.100	IPv4-Adresse des Druckers
Port	3002	TCP-Port für G-PRINT (Standard seit v2.x: 3002)
Subnetzmaske	255.255.255.0	Netzwerkmaske
Standard-Gateway	0.0.0.0	Standard-Gateway
Drucker-Name	alphaJET	Bezeichnung für das Geräteprofil
Timeout (Sek.)	5	Verbindungs-Timeout in Sekunden
DHCP aktivieren	aus	DHCP am Drucker aktivieren/deaktivieren

Wichtig:
Nach Änderungen immer auf [Speichern] klicken. Der Standard-Port ist seit v2.x 3002 (zuvor 3000).

4.2 Verbindungstest
Button	Funktion
Verbindung prüfen	Sendet <GP><MAINSTATE/></GP> und zeigt Ergebnis an
Drucker-Status	Fragt den aktuellen Drucker-Status ab
Trennen	Beendet die aktive Verbindung

4.3 Software-Update
•	Update-URL zeigt auf eine version.json-Datei (z. B. GitHub Releases)
•	"Beim Start automatisch prüfen" aktiviert den automatischen Check
•	[URL speichern] sichert die URL dauerhaft in config.json
•	Downloads werden per SHA-256 verifiziert bevor sie installiert werden

4.4 Drucker-Profile
•	[Speichern] – Aktuelle Konfiguration unter einem Namen speichern
•	[Laden] – Ausgewähltes Profil laden (auch per Doppelklick)
•	[Löschen] – Ausgewähltes Profil entfernen

4.5 Netzwerk-Helfer
Zeigt alle IP-Adressen des PCs an und prüft ob PC und Drucker im gleichen Subnetz sind.
•	[IPs aktualisieren] – IP-Liste neu einlesen
•	[Windows-Netzwerkeinstellungen] – Öffnet ncpa.cpl direkt

Grün: OK – PC und Drucker sind im selben Subnetz.
Rot:  ACHTUNG: Nicht im gleichen Subnetz! – Mit Korrekturhinweis auf richtige PC-IP.
 
5. Tab: Befehle
5.1 Schnell-Befehle
Button	G-PRINT Befehl	Funktion
Verbindungstest	<GP><MAINSTATE/></GP>	Drucker erreichbar?
Status abfragen	<GP><SYS><STATE/></SYS></GP>	System-Status
Firmware-Version	<GP><VERSION/></GP>	Versionsinfo abfragen
Board-Info	<GP><BOARDINFO/></GP>	Hardware-Info
Board-Info (ext.)	<GP><BOARDINFO_EXT/></GP>	Erweiterte Hardware-Info
Datum / Uhrzeit	<GP><SYS><DATETIME/></SYS></GP>	Datum/Uhrzeit abfragen
GUI sperren	<GP><GUICONTROL aMode="1">...</GP>	Drucker-GUI sperren
GUI schliessen	<GP><GUICONTROL aMode="2">...</GP>	Drucker-GUI schließen
GUI neu starten	<GP><GUICONTROL aMode="3">...</GP>	Drucker-GUI neu starten
Drucken START	<GP><START/></GP>	Druck starten
Drucken STOP	<GP><STOP/></GP>	Druck stoppen

5.2 Befehlsverlauf
•	Die letzten 20 gesendeten Befehle werden gespeichert
•	Doppelklick auf einen Eintrag = Befehl erneut senden
•	Auto-Ping: Sendet alle 30 Sekunden automatisch einen Verbindungstest

5.3 Freier G-PRINT Befehl
•	[Senden] – Befehl an den Drucker schicken
•	[Formatieren] – XML automatisch einrücken und lesbar machen
•	[Als Funktion speichern] – Befehl in den Funktionen-Tab übernehmen
 
6. Tab: Funktionen
Eigene, häufig benötigte G-PRINT Befehle speichern und verwalten.

Workflow
•	Links eine Funktion auswählen oder [+ Neu] klicken
•	Im Editor den Titel und XML-Befehl eingeben
•	[Speichern] – Funktion dauerhaft speichern (functions.json)
•	[Ausführen] – Gespeicherten Befehl direkt an den Drucker senden
•	[Formatieren] – XML-Einrückung automatisch korrigieren

Beispiel: Global-Zähler auf 0 setzen
<?xml version="1.0" ?>
<GP>
  <GLOBALCOUNTER aResetable="1">0</PRODCOUNTER>
</GP>
 
7. Tab: Labels
Verwaltung lokaler Label-Dateien (.txt / .gp / .lab) und direktes Übertragen auf den Drucker.

Button	Funktion
+ Neu	Neue leere Label-Datei anlegen
Importieren	Externe Datei in das lokale Labels-Verzeichnis kopieren
Aktualisieren	Dateiliste neu laden
Löschen	Ausgewählte Datei löschen
Lokal speichern	Inhalt in der lokalen Datei speichern
Label speichern (im Drucker)	Label direkt in den Drucker-Speicher übertragen (G-PRINT)
Label laden (im Drucker-Puffer)	Label aus dem Drucker-Puffer laden
Formatieren	XML automatisch einrücken
 
8. Tab: Configs
Verwaltung lokaler Konfigurations-Dateien (.pcf).

Button	Funktion
Config lokal speichern	Geänderten Inhalt lokal sichern
Config laden (in Tool)	Config-Datei vom Drucker in den Editor laden
Config laden (im Drucker)	Config direkt in den Drucker laden (G-PRINT)
Formatieren	XML-Formatierung korrigieren
 
9. Tab: PrintControls
Verwaltung lokaler PrintControl-Dateien (.ctl).

Button	Funktion
PrintControl lokal speichern	Geänderten Inhalt lokal sichern
PrintControl laden (in Tool)	PrintControl vom Drucker laden
PrintControl laden (im Drucker)	PrintControl direkt in den Drucker laden
Formatieren	XML-Formatierung korrigieren
 
10. Tab: Monitor
Der Monitor-Tab bietet drei unabhängige Test- und Debugging-Werkzeuge.

10.1 TCP-Proxy
Leitet den Datenverkehr zwischen einem externen Steuerungssystem und dem Drucker durch das Tool und protokolliert alle G-PRINT Nachrichten mit.

Verwendung:
1. Im Netzwerk-Tab: Drucker-Port auf 3002, Drucker-IP auf tatsächliche Drucker-IP setzen.
2. Lausch-Port und Weiterleitungs-IP:Port konfigurieren.
3. [Proxy starten] klicken. Alle Nachrichten erscheinen im Log.

10.2 Mock-Drucker
Simuliert einen alphaJET-Drucker auf dem lokalen PC. Ermöglicht vollständiges Testen ohne physischen Drucker.

Einrichtung:
Im Netzwerk-Tab: IP = 127.0.0.1, Port = 3002. Mock-Port im Monitor-Tab einstellen → [Mock starten].

10.3 Mock FTP-Server
Simulierter alphaJET FTP-Server mit Testdateien. Standard-Zugangsdaten: IP 127.0.0.1, Port 2121, User: test, PW: test.
•	[FTP-Server starten] – Server starten
•	[Testordner öffnen] – Öffnet res/mock_ftp/ im Explorer
 
11. Tab: Label Editor
Visueller Editor zum Erstellen und Bearbeiten von alphaJET-Labels per Drag & Drop. Alle Änderungen werden sofort als G-PRINT XML dargestellt.

11.1 Objekt-Typen
Typ	Beschreibung
T Text	Statischer oder dynamischer Texteintrag
Datum / Zeit	Automatisches Datum/Uhrzeit-Feld mit konfigurierbarem Format
# Zähler	Produktions- oder Stückzähler
DMC (Matrix)	Data-Matrix-Code (2D) in verschiedenen Größen (10×10 bis 64×64)
Barcode / QR	1D-Barcodes (EAN-128, Code39, Code93) und QR-Code
Logo	Pixel-Logo (.mlg / .svg) aus dem Logos-Ordner
— Linie	Horizontale oder vertikale Trennlinie
[ ] Rechteck	Rechteck-Element

11.2 Eigenschaften-Panel
•	Position X / Y (Pixel / Strokes)
•	Strichbreite (SW), Strichstärke (SS), Magnifikation (1×–3×)
•	Feld-Typ: Statisch, Eingabe (prompted), Datafield
•	Negativ / Rückwärts / Winkel
•	Schriftart und -größe (inkl. Drucker-Fonts aus fonts/-Ordner)

Drucker-Fonts:
TTF-Druckerfonts aus dem fonts/-Ordner (neben der .exe) werden beim Start automatisch geladen und ermöglichen eine exaktere Druckervorschau.

11.3 Objekt-Operationen
Funktion	Beschreibung
Duplizieren	Ausgewähltes Objekt kopieren
Spiegeln	Objekt horizontal spiegeln
Breite 1×–4×	Magnifikation der Breite setzen
Ausrichten	Links, rechts, oben, unten ausrichten
H/V-Zentrieren	Horizontal oder vertikal zentrieren
Drehen	Um 90° links/rechts oder 180° drehen
Löschen	Ausgewähltes Objekt entfernen

11.4 G-PRINT XML Live-Ansicht
Am unteren Rand des Editors wird das aktuelle G-PRINT XML in Echtzeit angezeigt. [Kopieren] überträgt den Inhalt in die Zwischenablage.
 
12. Tab: Logo Editor
Pixel-Editor zum Erstellen und Bearbeiten von Logos für den alphaJET-Drucker.

Button	Funktion
Größe setzen	Canvas-Größe auf Breite/Höhe anpassen
Alles löschen	Alle Pixel löschen (Canvas leeren)
Invertieren	Alle Pixel invertieren (schwarz ↔ weiß)
Logo laden	MLG-Datei aus dem Logos-Ordner laden
Als MLG speichern	Als alphaJET-Logo-Datei (.mlg) exportieren
Als BMP speichern	Als BMP-Bitmap exportieren
Als PNG speichern	Als PNG-Bild exportieren
Als JPG speichern	Als JPEG-Bild exportieren
 
13. Tab: FTP
Direkter Zugriff auf das Dateisystem des Druckers über FTP.

13.1 Standardzugangsdaten
Gerätetyp	User	Passwort	Port
AJD	User	user$ftp	21
AJ5	User	c0d1n9b	21
Mock	test	test	2121

Hinweis:
Zugangsdaten können durch res/ftp_credentials.json überschrieben werden (gleiche Schlüsselstruktur wie die Standardwerte).

13.2 Dateioperationen
Button	Funktion
Download → lokal	Ausgewählte Datei/Ordner herunterladen
Dateien hochladen	Lokale Dateien auf den Drucker hochladen
Ordner hochladen	Lokalen Ordner rekursiv hochladen
Datei löschen	Ausgewählte Datei/Ordner löschen
Alles als ZIP	Gesamtes Drucker-Dateisystem als ZIP sichern

13.3 Schnellzugriff (rechte Seitenleiste)
Für Labels, Logos, Configs und PrintControls gibt es Schnellzugriff-Buttons zum lokalen Speichern und direkten Öffnen im jeweiligen Editor.
 
14. Tab: AZ & Reisekosten
Erfassung von Arbeitszeiten und Reisekosten mit direkter Salesforce FSL Synchronisation und Excel-Export.

14.1 Persönliche Daten
•	Vorname, Nachname, Wohnort, Personal-Nr. eintragen
•	[Daten speichern] – dauerhaft in res/user_profile.json speichern

14.2 Salesforce-Verbindung (Session-ID)
•	1. VPN verbinden (GlobalProtect)
•	2. Im Tool: [Salesforce in Chrome öffnen] klicken
•	3. Mit K&B-SSO-Account einloggen
•	4. F12 → Developer Tools → Application → Cookies → koenig-bauer.lightning.force.com
•	5. Zeile "sid" suchen → Wert kopieren (Strg+C)
•	6. Feld "Session ID" im Tool einfügen → [Verbinden (Session ID)] klicken

Gültigkeit:
Die Session-ID ist ca. 8 Stunden gültig. Sie wird mit [Daten speichern] dauerhaft gespeichert und beim nächsten Start automatisch geladen.

14.3 Wochenansicht
Spalte	Bedeutung
WT	Wochentag (Mo–So)
Datum	Datum des Tages
Status	Arbeit / Krank / Urlaub / Kurzarbeit / GLZ / Feiertag / Sonstiges
Start/Ende	Arbeitszeiten des Tages
Pause	Pausenzeit in Minuten
Std	Netto-Arbeitsstunden (automatisch berechnet)
Auftrag	Auftragsnummer des ersten Eintrags
Kundenname	Kundenname / Kürzel
Details	Route oder Allgemeinkosten-Code

14.4 Allgemeinkosten (Innendienst)
Code	Beschreibung
0010	Customer Preparation
0020	Service Hotline
0060	Internal Meetings / Trainings
0080	Materials Management Activities
0090	Documentation Activities
0140	Automotive Workshop / Inspection
0190	Dealer & Subsidiary Support
2100	Activities Service Cloud

14.5 Export
Button	Erzeugte Datei
Servicezeitenmeldung Excel	Monatliche Stundenmeldung als Excel-Datei
Reisekosten Excel (FB_0020)	Ausgefüllte Reisekostenabrechnung (Vorlage: res/templates/FB_0020_Reisekostenabrechnung.xlsm)
 
15. Kommunikations-Log
Farbe	Bedeutung
Blau	Gesendete Befehle (→)
Grün	Empfangene Antworten (←)
Rot	Fehlermeldungen
Lila	Info-Meldungen
Gelb	Warnungen

Element	Funktion
[▼/▲]	Log ein- oder ausklappen
[S]	Klein (4 Zeilen)
[M]	Mittel (7 Zeilen)
[L]	Groß (12 Zeilen)
[Leeren]	Log-Inhalt löschen

Jede Sitzung wird automatisch als Datei in res/logs/ gespeichert.
 
16. Tastenkürzel
Allgemein
Kürzel	Funktion
Strg+S	Speichern (im aktiven Tab)
Strg+Z	Rückgängig
Strg+Y	Wiederholen

Label Editor
Kürzel	Funktion
Strg+Z	Rückgängig (bis 50 Schritte)
Strg+Y	Wiederholen
Entf	Ausgewähltes Objekt löschen
↑ ↓ ← →	Objekt pixelweise verschieben
Strg + Mausrad	Zoom ein-/auszoomen
Mausrad	Vertikal scrollen
Shift + Mausrad	Horizontal scrollen
 
17. Farbkodierung der Buttons
Farbe	Bedeutung	Beispiele
Grün	Speichern / Bestätigen	Speichern, Verbinden, Lokal speichern
Blau	Laden / Abrufen	Laden, IPs aktualisieren, Erneut senden
Rot	Löschen / Stoppen	Löschen, Proxy stoppen, Trennen
Orange	Hochladen / Übertragen	Dateien hochladen, Ordner hochladen
Lila	Sonderfunktionen	Formatieren, Backup
Gelb	Test-Funktionen	Mock starten, FTP-Server starten
 
18. Ordnerstruktur
alphaJet-InterfaceTool.exe
fonts/                    ← Drucker-TTF-Fonts (optional)
res/
├── config.json           ← Drucker-Konfiguration (IP, Port, Theme)
├── functions.json        ← Gespeicherte Funktionen
├── profiles.json         ← Drucker-Profile
├── user_profile.json     ← Persönliche Daten (AZ-Tab)
├── sf_config.json        ← Salesforce-Konfiguration & Session-ID
├── kunden_vorlagen.json  ← Kunden-Vorlagen (AZ-Tab)
├── ftp_credentials.json  ← Eigene FTP-Zugangsdaten (optional)
├── labels/               ← Lokale Label-Dateien
├── configs/              ← Lokale Config-Dateien (.pcf)
├── printcontrol/         ← Lokale PrintControl-Dateien (.ctl)
├── logos/                ← Lokale Logo-Dateien (.mlg, .svg, .png)
├── logs/                 ← Sitzungs-Logs (automatisch)
├── kw_data/              ← Arbeitszeit-Daten pro KW (AZ-Tab)
├── templates/            ← Excel-Vorlagen (FB_0020, FB_0221)
├── mock_ftp/             ← Testdateien für Mock FTP-Server
└── themes/
    ├── forest-dark.tcl   ← Dark-Mode Theme
    └── forest-light.tcl  ← Light-Mode Theme
 
19. Fehlerbehebung
Verbindung schlägt fehl
Problem: "Verbindungsfehler: [WinError 10060] timeout"
PC und Drucker nicht im gleichen Subnetz oder falsche IP/Port
1. Netzwerk-Tab → Netzwerk-Helfer prüfen
2. PC-IP anpassen (Windows-Netzwerkeinstellungen)
3. Port prüfen (Standard seit v2.x: 3002)
4. Firewall prüfen

FTP-Verbindung schlägt fehl
Problem: "FTP-Fehler: 530 Login incorrect"
AJD → User / user$ftp
AJ5 → User / c0d1n9b
Eigene Zugangsdaten in res/ftp_credentials.json hinterlegen

Salesforce Login schlägt fehl
Problem: "HTTP Error 403 – Forbidden"
Beide SID-Werte nacheinander probieren (manchmal werden 2 angezeigt)
In Salesforce prüfen ob noch eingeloggt
SID evtl. abgelaufen → erneuter Login

Label-Editor zeigt Schrift falsch an
Problem: Schrift weicht von Druckerausgabe ab
TTF-Druckerfonts in fonts/-Ordner (neben der .exe) ablegen
Das Tool lädt sie automatisch beim Start

Auto-Update funktioniert nicht
Problem: Kein Update-Check beim Start
Netzwerk-Tab → Software-Update: Update-URL eintragen
"Beim Start automatisch prüfen" aktivieren
[URL speichern] klicken

 
Versionshistorie
Version	Datum	Änderungen
2.1.1	12.06.2026	Light/Dark-Mode-Toggle, SHA-256 Update-Verifikation, Port-Standard 3002, ftp_credentials.json, fonts/-Ordner, Mock-FTP im Monitor-Tab, Logo-Editor-Exportformate (BMP/PNG/JPG), CRA-Compliance, CustomTkinter/reportlab entfernt → tkinter/ttk + Pillow
1.9.0	–	Initiale veröffentlichte Version

Dokumentation erstellt für alphaJET Interface-Tool v2.1.1  ·  Marvin Köllner  ·  König & Bauer AG  ·  12.06.2026
