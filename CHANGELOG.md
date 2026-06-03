********************************************************************************
********************************************************************************
********        -- alphaJET Interface-Tool -- Marvin Köllner --        *********
********Steuerprogramm fuer Koenig & Bauer alphaJET Tintenstrahldrucker*********
********                 Protokoll: G-PR(INT) V3.0.0                   *********
********************************************************************************
********************************************************************************

################################################################################
####################       -- neuste Version v1.8.0 --      ####################
################################################################################




######### -- v1.8.0 -- #########

### Design
-- Forest TTK Dark Theme Unterstützung (res/themes/forest-dark.tcl)
-- Farbpalette kontrastreicher (Text heller, Buttons mit solidem Hintergrund + hellem Text)
-- Farbige Buttons (Grün/Rot/Orange/Blau/Lila/Gelb) nun auch unter Forest-Theme korrekt dargestellt

### AZ & Reisekosten (neuer Tab, neue Datei az_reisekosten.py)
-- Persönliche Daten speichern (Name, Wohnort, Personal-Nr)
-- Salesforce FSL Anbindung: Login per OAuth2 oder Session-ID (VPN)
-- Wochenansicht mit editierbaren Feldern: Status, Start/Ende/Pause, Stunden (live berechnet)
-- Detail-Panel pro Tag: Auftr.Nr, Kunde, Standort, Reiseweg, Start-/Endpunkt
-- Reisekosten-Felder: Art (Außen-/Innendienst/Ausland), Land, Übernachtung, Mahlzeiten, km, Sonstiges
-- KW-Daten werden pro Woche lokal gespeichert (res/kw_data/)
-- Stundenübersicht PDF: komplette Monatstabelle (A4 Querformat, alle KWs des Monats)
-- Excel Servicezeitenmeldung (FB_0221): befüllt Vorlage automatisch mit KW-Daten
-- Excel Reisekostenabrechnung (FB_0020): befüllt Vorlage mit Monatsdaten inkl. Pauschalen-Felder
-- Vorlagen werden beim ersten Klick einmalig eingerichtet (res/templates/)
-- Abhängigkeiten (reportlab, openpyxl) werden beim ersten Start automatisch installiert

################################################################################

######### -- v1.7.0 -- #########

### FTP Tab
-- Ordner werden jetzt immer zuerst angezeigt, dann Dateien (alphabetisch sortiert)
-- Icons je Dateityp: 📁 Ordner · 📝 Labels · ⚙ Configs · 🖨 PrintCtl · 🖼 Logos · 📄 Rest
-- Download-Button funktioniert jetzt für Dateien und Ordner
-- Datei → Speicherdialog wie bisher
-- Ordner → Zielordner wählen → rekursiver Download mit Fortschrittsanzeige
-- Backup-Button (lila, neuer Abschnitt rechts)
-- Lädt alles vom Drucker (/) rekursiv herunter
-- Packt als ZIP-Archiv
-- Speicherdialog mit Voreinstellung backup_{IP}.zip
-- Ping Test wird jetzt ebenfalls im FTB Tab automatisch alle 30sek nach Verbindung durchgeführt, wenn false -> Nicht Verbunden
-- Keine Antwort / Exception → Status -> Nicht verbunden, Baum wird geleert, Button auf "Verbinden" zurück, Log-Eintrag
-- Öffnet jetzt askopenfilenames → mehrere Dateien gleichzeitig auswählbar
-- Alle werden nacheinander in das aktuell im Baum gewählte Verzeichnis hochgeladen
-- Fortschrittsanzeige pro Datei
-- Am Ende: Upload abgeschlossen: 3/3 Dateien → /label
-- „Ordner hochladen" (neu)
-- Öffnet Ordner-Auswahldialog
-- Lädt den Ordner rekursiv hoch — Unterordner werden auf dem Drucker automatisch erstellt (MKD)
-- Existierende Ordner werden nicht als Fehler behandelt
-- Fortschrittsanzeige pro Datei, danach Baum-Refresh
-- Ziel wird immer aus dem aktuell im Baum markierten Element abgeleitet:
-- 
-- Ordner markiert → direkt dort hinein
-- Datei markiert → in deren übergeordneten Ordner
-- Nichts markiert → Root /

### Buttons
-- Alle Buttons / G-PRINT Befehle die nicht funktionierten gelöscht
-- Einheitliche Farbzuordnung auf allen Tabs (grün=speichern, blau=laden, rot=löschen..)

### Hilfsfunktionen
-- Maus-Hover-Tooltips bei ausgewählten Funktionen mit detaillierter Beschreibung


################################################################################

######### -- v1.6.0 -- #########

### Label Editor
-- Linespace-Skalierung entfernt — hat px_size auf bis zu -6 reduziert, Font war fast unsichtbar
-- Textposition: anchor="sw" + cy_b — Text an Unterkante ausgerichtet (Druckerlogik: Y=0 = unterste Zeile)
-- MLG-Rendering — zuvor nur SVG, PNG, BMP & JPG; MLG ist nicht in Pillow → eigene 1-Bit-Darstellung
-- Alle Bildformate werden jetzt selbst gerendert (Pillow Fonts Library entfernt)
-- Leerzeichen = 1 leerer Pixel
-- Teilweise Padding der Frames erhöht (Buttons waren in bestimmten Zuständen nicht sichtbar)

### Logo Editor
-- Schachbrett-Hintergrund — zeigt transparente (weiße = nicht gedruckte) Pixel an
-- Schwarze Pixel — (20, 20, 20) statt reines Schwarz
-- Vorschau-Pixel beim Zeichnen von Linien/Rechtecken — grau mit sauberem Fill
-- Info-Zeile zeigt jetzt auch Anzahl gesetzter Pixel: z.B. "32 × 10 px · 87 Pixel gesetzt"
-- Schneller bei großen Logos — PIL rendert alles auf einmal, kein tausendfaches create_rectangle
-- Fallback ohne PIL — funktioniert weiterhin (alte Methode)

################################################################################

######### -- v1.5.0 -- #########

### Design
-- Neue Farbpalette — Elegant Charcoal
-- Hintergrund: #1a1a1a → neutrales Dunkelgrau, kein Blau-Stich
-- Text: #e0e0e0 → warm-weiß, gut lesbar
-- Akzent: #5a9fd4 → Steel Blue, gedämpfter als vorher
-- Header: #141414 → fast schwarz, klarer Kontrast
-- Buttons — dunkler Hintergrund + Akzentfarbe als Text
-- Grün: dunkelgrüner Hintergrund #1c3528, mintgrüner Text #52a06e
-- Blau: dunkelblauer Hintergrund #1a2e40, Steel-Blue Text #5a9fd4
-- Rot: dunkelroter Hintergrund #3a1e1e, gedämpftes Rot #c05858
-- Orange: dunkel-amber Hintergrund, Bronze-Text
-- Header: 2px statt 3px Akzentlinie, kompakter (52px)
-- Tabs: neutrale Farbtrennung, kein blaues Underline
-- Checkboxen: Haken in Steel Blue bei Auswahl
-- Entries: Focus-Rahmen in Akzentfarbe
-- Treeview: saubere Zeilenhöhe 24px, flache Spaltenköpfe

### FTP
-- Dateibaum war nach erfolgreicher Verbindung leer — Fix: Umstellung von ftp.dir() auf ftp.mlsd() (RFC 3659), Fallback auf ftp.nlst()
-- Standardpasswort AJD korrigiert + U von user musste groß! (noch beim aj5 prüfen)
-- FTP Timeout-Fehler gefixt (settimeout 120s)
-- Anpassung Design — FTP UI Header, Background, Fonts

### Label Editor
-- Zähler-XML komplett auf Geräte-Format umgestellt
-- Neues Format mit Child-Elementen: FORMAT, AUTOSTOP, RESETABLE, REPRESETABLE, START, END, STEP, REP, COUNT, AC, TIMEDRESET
-- Rückwärtskompatibilität mit altem Attribut-Format bleibt erhalten
-- Zähler-Properties erweitert: Format-Dropdown, Autostop, Rückstellbar, Wiederh. rückstellbar, Wiederholung, Zählerstand, Alpha-Code, Start=PC, Globalen Zähler verw., Timed Reset, Prompted-Zähler
-- Objektrahmen-Badge zeigt jetzt X Y H L (Höhe und Länge in Strokes/px)
-- Dots/Pixel-Modus — neuer Toggle in der Toolbar
-- Dots: Tinte-Punkte als Kreise (benötigt Pillow + TTF-Font); Pixel: klassisches Rechteck
-- Linke Seitenleiste breiter (185 → 215 px)
-- Objektrahmen — Bounding-Box richtet sich jetzt exakt nach Drucker-Koordinaten

### Logo Editor
-- PNG speichern — neuer Button, transparenter Hintergrund (Pillow erforderlich)
-- JPG speichern — neuer Button, weißer Hintergrund (Pillow erforderlich)

################################################################################

######### -- v1.4.0 -- #########

###FTP und Monitor Tab 
-- Monitor — TCP-Proxy (Steuerung → PC → Drucker) + Mock-Drucker für Tests ohne echtes Gerät
-- FTP — Verbindung zum Drucker, Verzeichnis-Browser, Datei-Upload/Download, direkt im Editor öffnen
-- Geräteprofil-Auswahl (AJD / AJ5II / Test) mit vorausgefüllten FTP-Zugangsdaten

### App & Build
-- Fenster startet maximiert (Titelleiste bleibt sichtbar)
-- BUILD.bat überarbeitet — beendet laufende Instanz automatisch vor dem Build
-- update_version.py als separates Build-Hilfsskript

### Allgemein
-- Auto-Update beim Start (konfigurierbar, an/aus, URL einstellbar)
-- Drucker-Profile — mehrere IP/Port-Konfigurationen speichern und laden
-- Befehlshistorie — letzte 20 Befehle, per Doppelklick erneut senden
-- Auto-Ping — optionaler Hintergrund-Ping alle 30 Sekunden
-- Session-Log — jede Sitzung wird automatisch in res/logs/ gespeichert
-- Tab PrintControls hinzugefügt (.ctl-Dateien, Pfad user/config/PrintControl/)
-- Neue Schnellbefehle: BOARDINFO, BOARDINFO_EXT

### PrintModes
-- pm05 (5 px) hinzugefügt
-- pm07 (7 px) hinzugefügt
-- pm48 (48 px) hinzugefügt

### Label Editor — Fixes
-- Objektbreite korrigiert — Bounding Box passt nun zur tatsächlichen Textbreite
-- MAG 2×/3×/4× — Text wird nur noch horizontal gestreckt, Höhe bleibt korrekt
-- Linie / Rechteck / Ellipse — Koordinaten und Bounding Box korrigiert, schwarz eingefärbt
-- Properties-Panel — Mausrad funktioniert überall, nicht nur auf der Scrollleiste
-- Y-Koordinate — unterster Pixel wird nicht mehr von der Rahmenlinie verdeckt
-- DMC-Hintergrund — transparent (weiße Pixel werden nicht gedruckt)
-- Beim Laden bereits erstellter Labels wurde der Objektrahmen falsch angezeigt
-- NEG=1 Objekte (schwarze Hintergrundboxen) werden aus der Kollisionserkennung ausgeschlossen
-- Proportionale Schriften (Arial, Tunga, Latha) — Rahmen wird mit echter tkinter-Rendering-Breite gemessen

### Label Editor — Neue Features
-- Undo / Redo (50 Schritte) — Strg+Z / Strg+Y / Buttons ↶ ↷ in der Toolbar
-- Tastenkürzel: Entf = Objekt löschen, Backspace = Undo, Pfeiltasten = verschieben
-- Zoom bis 32× (war max 8×)
-- Mausrad im Canvas: scrollen, Shift = horizontal, Strg = Zoom
-- Kollisions-Erkennung — überlappende Objekte werden orange markiert
-- Resize-Handle — oranges Quadrat oben rechts am Objekt, ziehen = Breite ändern
-- Drehung — Winkel-Eingabe + Buttons ↺ ↷ 0° im Panel und in Operationen
-- Duplizieren, Spiegeln, Ausrichten, Zentrieren als Operationen-Buttons
-- Logo-Objekt — neuer Objekttyp im Label Editor (Dateiname, Breite, Höhe)
-- Zähler — neue Quelle-Auswahl im Properties-Panel
-- Eigener Zähler → NUMB (Start, Ende, Schritt, Stellen)
-- Produktzähler → TEXT #PCNT
-- Globaler Zähler → TEXT #GCNT
-- Vorschau-Wert für Editor-Anzeige einstellbar

### Logo Editor
-- Hintergrund transparent (weiße Pixel = nicht gedruckt)
-- PNG speichern — neu, transparenter Hintergrund
-- WebP speichern — neu, transparenter Hintergrund
-- Ordner res/logos/ wird automatisch angelegt
-- Laden und Speichern öffnen standardmäßig res/logos/

################################################################################

######### -- v1.3.0 -- #########

### App & Build
-- Dark-Theme mit Catppuccin-Farbpalette
-- Uhr + IP-Anzeige im Header
-- About-Dialog mit Tastenkürzel-Übersicht
-- Automatische Combobox-Styles (dunkler Hintergrund)

### Label Editor
-- Pixel-genaue Font-Darstellung mit geladenen TTF-Druckerfonts
-- Y=0 = Unterkante (Drucker-Koordinatensystem)
-- Zoom 1×–8×, Hintergrund-Raster wählbar
-- Objekt-Typen: Text, Datum/Zeit, Zähler, DMC, Barcode/QR, Linie, Rechteck, Logo
-- Drag & Drop zum Verschieben
-- Feld-Typ: Statisch / Datenfeld / Prompted
-- Datenfeld ohne Platzhalter → rot hervorgehoben
-- Properties-Panel mit allen Objekt-Eigenschaften
-- XML-Vorschau live (ein-/ausklappbar)
-- Speichern / Laden / An Drucker senden

### Sonstige Tabs
-- Labels — Dateiverwaltung
-- Configs — .pcf-Dateien

################################################################################

######### -- v1.2.0 -- #########

### Label Editor (erste Version)
-- Visueller Label-Editor als eigener Tab
-- Objekte per Klick hinzufügen: Text, Datum/Zeit, Zähler, DMC, Barcode/QR, Linie, Rechteck
-- Koordinaten-System: Y=0 = Unterkante (Drucker-Standard)
-- Label direkt aus dem Editor an Drucker senden

### Logo Editor (erste Version)
-- Paint-ähnlicher Pixel-Editor als eigener Tab
-- Größe frei wählbar (B × H in Pixeln)
-- Werkzeuge: Stift, Radierer, Füllen, Linie, Rechteck
-- Speichern als SVG, Laden von SVG/MLG/PNG/BMP

################################################################################

######### -- v1.1.0 -- #########

### Neue Tabs
-- Labels — lokale Label-Dateien (.txt, .xml, .gp) verwalten, auf Drucker laden/speichern (SAVELAB, LOADLAB)
-- Configs — Konfigurations-Dateien (.pcf) verwalten, auf Drucker übertragen (LOADCONFIG)
-- PrintControls — .ctl-Dateien, Pfad user/config/PrintControl/ auf dem Drucker
-- Funktionen — eigene G-PRINT XML-Befehle speichern und wiederverwenden

### Netzwerk
-- Subnetz-Prüfung (PC und Drucker im gleichen Netz?)

################################################################################

######### -- v1.0.0 -- #########

### Grundfunktionen
-- Verbindung zum alphaJET per TCP/IP (G-PRINT Protokoll)
-- Netzwerk-Tab — IP, Port, Subnetz, Gateway, Name, Timeout konfigurieren
-- Befehle-Tab — Schnellbefehle + freier XML-Befehl-Editor
-- Kommunikations-Log mit Zeitstempel (ein-/ausklappbar, Größe wählbar)
-- Konfiguration wird lokal gespeichert (res/config.json)
-- START.bat prüft Python-Installation und zeigt Fehlermeldungen

################################################################################
