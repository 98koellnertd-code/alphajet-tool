********************************************************************************
********************************************************************************
-- alphaJET Interface-Tool -- Marvin Köllner -- 
Steuerprogramm fuer Koenig & Bauer alphaJET Tintenstrahldrucker
Protokoll: G-PR(INT) V3.0.0                   
********************************************************************************
********************************************************************************


################################################################################
################################################################################
################################################################################
####################       -- neuste Version v2.1.2 --      ####################
################################################################################
################################################################################
################################################################################

###LATEST CHANGES###

######### -- v2.1.2 -- #########

### CRA-Anpassungen
###utils.py
-- TEST-FTP-Eintrag entfernt (Drittanbieter-Server mit öffentlichen Credentials)
-- FTP-Credentials werden jetzt aus res/ftp_credentials.json geladen wenn vorhanden → Werksvorgaben überschreibbar ohne Code-Änderung
-- Neue Helfer: validate_ip(), validate_port(), validate_gprint_xml(), validate_local_path()
### tool.py
-- import hashlib ergänzt; _verify_sha256() hinzugefügt; Update-Download prüft SHA-256 aus version.json vor dem Ausführen – Abort bei Mismatch
-- _save_network(): IP-Format, Port 1–65535, Timeout 1–120 werden vor dem Speichern geprüft
-- _run_cmd(): G-PRINT-XML-Struktur (<GP>…</GP>) wird validiert bevor gesendet wird
### ftp.py
-- Sichtbare Warnung im FTP-Header: "FTP überträgt Daten unverschlüsselt – nur in gesichertem Netzwerk verwenden (CRA Art. 13)"
-- _ftp_connect(): IP-Adresse und Port werden vor dem Verbindungsaufbau validiert
-- _ftp_download_recursive(): Path-Traversal-Schutz — Dateinamen mit / oder \ werden blockiert; lokale Pfade werden auf Verbleib im Zielverzeichnis geprüft
-- _ftp_upload_recursive(): Versteckte Dateien (.) und Einträge mit Pfadzeichen werden übersprungen
###requirements.txt	
reportlab (nie benutzt) entfernt; pyftpdlib ergänzt
###BUILD.bat	
reportlab-Check und --collect-all "reportlab" entfernt
###SECURITY.md	
-- Vulnerability Disclosure Policy (CRA Art. 13/14): Meldeweg, Reaktionszeiten, bekannte Risiken (FTP), implementierte Maßnahmen
### sbom.json	
Software Bill of Materials im CycloneDX 1.4 Format (CRA Annex I, Part II)
###version.json
--SHA 256 
### OP-01 – Security Audit Log (utils.py, ftp.py, tool.py)
-- utils.security_log(event, detail, result) schreibt JSON-Lines nach res/logs/security_audit.jsonl (thread-safe)
-- ftp.py: Log-Eintrag bei FTP-Connect (ok/error)
-- tool.py: Log-Einträge in do_download() (start/ok/hash_error/error) und _save_network() (CONFIG_CHANGE)
### OP-02 – Pfad-Leak in Exception-Meldungen (utils.py, tool.py, az_reisekosten.py)
-- utils.sanitize_error(e) — kürzt absolute Windows/POSIX-Pfade auf Dateinamen
-- Verwendet in _file_import(), do_download() (tool.py) und Excel-Fehlerdialogen (az_reisekosten.py)
### OP-03 – pip-audit in BUILD.bat
-- Auto-install von pip-audit falls fehlend, dann pip_audit --requirement requirements.txt vor PyInstaller
### OP-04 – SECURITY.md
Abschnitt "Geräte-Standardpasswörter" um Schritt-für-Schritt-Anleitung und vollständige ftp_credentials.json-Struktur erweitert

######### -- v2.1.1 -- #########

### UPDATER
-- App muss einmalig aktualisiert werden
-- Updater neu gebaut, ohne Fehler und Errors, beim Theme Wechsel

### MLG 
-- Mlg Logos werden jetzt korrekt decodiert und  beim speichern korrekt codiert (kba (cgrafic) style)

### FTP 
-- Drucker haben weder nlst noch mlds ftp-list-formate.. 
-- normalerweise gibt es standardformate für ftp. also erhält man einfach eine stumpfe Liste.
-- wenn kein format erkannt wird, man die datei sich anguckt, welcher type, größe, name.. und das in spalten anzeigt und natürlich verarbeiten/visualisiert.
-- Speichern als SVG entfernt. unnötig.

### LOCAL
-- cancel wird nun richtig ausgeführt, auch beim theme wechsel (löschen aller temp. files)

### LABELS / Configs
-- neue Befehle hinzugefügt

################################################################################

######### -- v2.0.0 -- #########

### Updates
-- Update über GIT eingebunden und version.json

### Design 
-- Es kann nun zwischen Hell und Dunkel gewählt werden (forest-dark & forest-light)
-- eigenes Stylesheet erstellt 
-- Button Anpassungen
-- Schriftanpassungen
-- insgesamt alles etwas größer &  kontrastreicher und damit übersichtlicher gestaltet
-- kompletter Design-Quellcode in utils.py ausgelagert 

#### Code Änderungen, Ineffizienzen, Exceptions und Performance + 
-- _build_props_area → nur noch Header-Label + _props_built = False. Canvas, Scrollbar, Inner-Frame werden nicht mehr beim Start gebaut.
-- _ensure_props_built() → neuer Helfer, baut das Panel beim ersten Aufruf, danach no-op.
-- _show_props(obj) → ruft _ensure_props_built() als erstes — das ist der einzige Trigger.
-- _show_empty_props() → if not self._props_built: return — solange kein Objekt je angeklickt wurde, gibt es nichts zu leeren.
-- Toggle-Button Auto-Ping: AUS/AN vollständig entfernt
-- Startet automatisch 3s nach App-Start, läuft für immer
-- _printer_ping_id wird gespeichert → after_cancel beim Schließen der App via neuem _on_close-Handler (löst gleichzeitig den fehlenden WM_DELETE_WINDOW-Bug aus dem Code-Review)
-- Status: Verbunden (grün) / Offline (rot)
-- FTP-Keepalive (ftp.py)
-- 10s Intervall statt 30s
-- _ftp_keepalive_id gespeichert → bei "Trennen" und bei _ftp_on_kicked sofort gecancelt
-- Verhindert damit die doppelte-Loop-Akkumulation beim schnellen Trennen/Verbinden
-- Status bei Verbindungsverlust jetzt: ● Offline statt ● Nicht verbunden
-- Salesforce-Ping (az_reisekosten.py)
-- Neuer _sf_ping_loop() startet 5s nach Tab-Öffnung, läuft dann dauerhaft
-- Solange kein Token: idled (1 µs Check + reschedule)
-- Nach Login: GET /services/data/ – leichtester möglicher Endpoint (nur API-Versionsliste, ~200 Bytes)
-- 401/403 → Token wird gecleart, Dot rot, Text "Session abgelaufen"
-- Netzwerkfehler / 5xx → Dot gelb, Text "Verbindungsproblem" (Token bleibt erhalten, evtl. nur kurze Störung)
-- _sf_display_name wird nach Login gespeichert und vom Ping-Loop wiederverwendet
-- HTTPS-Enforcement	_update_check prüft url.startswith("https://") → Warnung + Abbruch; _update_prompt prüft dl_url ebenfalls
-- shell=True → os.startfile	Kein Subprozess mehr für ncpa.cpl
-- FTP-Tab Fehlerbehandlung	Jeder Sub-Build (Monitor, LabelEditor, LogoEditor) einzeln in try/except; bei FTPTab-Fehler: Fehlermeldung im Tab statt leerem Frame
-- MockFTPServer.start() bindet den Socket synchron – kein Warten nötig. Externer Server wird direkt als verfügbar markiert (ohne falsches _running=True)
-- Kein gefaktes MockFTPServer-Objekt mehr wenn Port schon belegt – nur Status-Update und return True
-- Doppeltes socket.close()	relay() schließt nur src; signalisiert dst via shutdown(SHUT_WR) → jeder Socket wird exakt einmal geschlossen
-- _calc_hours Duplikation	Delegiert jetzt an _calc_entry_hours – eine Implementierung, kein kopierter Code
-- 53× JSON im Main-Thread	File-I/O komplett in _do_stundenblatt (Hintergrundthread) verschoben; Main-Thread übergibt nur dict(self._day_data) als Snapshot
-- kw_data.pop()	→ kw_data.get() – kein Seiteneffekt auf übergebenes Dict
-- StringVar GC-anfällig	sv wird in self._day_rows[ds]["sv"] gespeichert → starke Referenz, sicher gegen Garbage Collector
-- Thread-Safety self._ftp	threading.Lock() schützt alle Schreibzugriffe (connect/disconnect); Keepalive liest atomisch in lokale Variable ftp
-- Tiefenbegrenzung	_ftp_download_recursive(_depth=0) – Abbruch bei _depth > 20
-- _ftp_mkd_safe	Prüft jetzt Codes 550, 521, 553 + "exists" im Text → kompatibel mit vsftpd, PureFTPd, ProFTPd
-- utils.py	save_json hat kein Exception-Handling – Dateisystem voll → unkontrollierter Crash
-- utils.py	LABEL_EXTS enthält .TXT, .Txt etc. redundant – has_ext normiert schon alles
-- label_editor.py	BASE_DIR wird lokal neu berechnet statt from utils import BASE_DIR
-- label_editor.py	tag_bind in _redraw akkumuliert Bindings auch nach delete("all") – Memory Leak
-- label_editor.py	Image.NEAREST deprecated seit Pillow 10 → Image.Resampling.NEAREST
-- label_editor.py	_photo_refs-hasattr-Guards sind redundant nach _redraw-Initialisierung
-- service_db.py	BASE_DIR wird lokal als _BASE_DIR neu berechnet
-- az_reisekosten.py	Timezone-Berechnung mit time.timezone/altzone – robuster: datetime.now().astimezone().utcoffset()
-- Gesamt	Kein WM_DELETE_WINDOW-Handler → offene FTP-Verbindungen / Logs beim Schließen nicht sauber beendet
-- Gesamt	Session-Logs wachsen unbegrenzt in res/logs/ – kein automatisches Cleanup alter Dateien
-- e_bg	surface2 bzw. row_stripe (je nach Parität)	bg (= gleich wie Tag-Header) → einheitlicher Block
-- Entry-Feld-Hintergrund	bg_=e_bg	bg_=C["surface2"] fix – Eingabefelder sehen immer wie Felder aus
-- _day_rows	nur row gespeichert	row + e_rows: [...] – alle Unterzeilen werden getrackt
-- _select_day / _select_entry	nur info["row"].config(bg=...)	_recolor_block() → färbt Header-Frame + alle Eintrags-Frames + ihre Labels gemeinsam um


################################################################################

######### -- v1.9.0 -- #########

###Allgemein, Doku
-- Alle Buttons mit Tooltip Klassen versehen (Hilfsfunktionen)
-- Dokumentation erstellt 

### AZ & Reisekosten 
-- Salesforce Login hinzugefügt (SF Token von Benni muss noch hinzugefügt werden)
-- Salesforce Load, über SOSQL Daten aus TimeSheet abfragen und in aktuelle KW einfügen (muss noch getestet werden, wenn API Zugang gegeben)
-- Bug-Fix (Hauptursache für #NV):
-- Enddatum geht jetzt auf H7 (col 8) statt I7 (col 9) → die Excel-Berechnung sollte jetzt stimmen
-- Innendienst-Filter:
-- Einträge mit Dienstart Innendienst / Homeoffice werden in der Reisekosten-Excel übersprungen
-- Gemischte Tage (z.B. Do: erst Materialmanagement, dann Außendienst) werden nur mit dem AD-Anteil geladen
-- Neue Zeile direkt unter der Stundenleiste (rechts): Sonstiges Kosten € — gilt für die ganze KW
-- Wird beim KW-Speichern mitgespeichert und beim Wechsel der KW geladen
-- Weitere kleine Anpassungen beim Extracten der Reisekosten

### Salesforce-Auth/Login
-- Nummerierte Schritt-für-Schritt-Anleitung direkt im Panel (immer sichtbar)
-- Button "🌐 Salesforce in Chrome öffnen" → öffnet direkt die richtige URL
-- Tooltip auf dem Session-ID-Feld erklärt wie lang sie gültig ist
-- Tooltip auf "Verbinden" erklärt was passiert
-- Tooltips auf allen Buttons (erscheinen nach ~0,6s Hover):
-- 💾 Daten speichern — was wird gespeichert
-- ⚡ Standardwoche füllen — welche Zeiten werden gesetzt
-- ☁ Von Salesforce laden — Hinweis auf Überschreibung + Verbindungspflicht
-- 💾 KW-Daten speichern — lokale Speicherung
-- 📊 Servicezeitenmeldung — Innendienst inklusive
-- 📊 Reisekosten FB_0020 — Innendienst übersprungen, Sonstiges-Zellen
-- ◀ ▶ + 🗑 — Navigation + Löschen im Detail-Panel
-- ✓ Übernehmen — Erinnerung ans KW-Speichern

### Salesforce-Laden 
Pause-Einträge (Type = "Pause") → Dauer in Minuten berechnen, als Pausenzeit für den Tag übernehmen
Reisezeit-Einträge → zählen für Tag-Start/Ende, werden aber nach SA gruppiert wie Arbeitszeit
Tag-Start = frühester Eintrag des Tages (07:00 Reisezeit)
Tag-Ende = spätester Eintrag (16:00 Reisezeit-Rückfahrt)
Pause wird nun neu berechnet sum(..) summiert jetzt alle SF-Einträge mit Type="Pause" 

### Label Editor
-- bei manchen Labels, die geladen wurde, wurde unten ein kleiner weißer Rand angezeigt (Label war kleiner als Canvas Widget, dadurch hat man das mid-frame gesehen)
-- CANVAS_PAD = 0 
-- Objejtrahmen von Arial Fonts wurde teilweise nicht richtig angezeigt 
-- Arial Fonts bekommen jetzt dynamische Breitenberechnung (char:width wird jetzt nicht aus font_size generiert sondern liest char_height direkt aus und rendert dann)

################################################################################

######### -- v1.8.0 -- #########

### Mock Server
-- Mock Server kann nun auch zum FTP Test genutzt werden, ebenfals zum Monitoring mit 2. PC 
-- Testdateien werden beim ersten Start automatisch in res/mock_ftp/ angelegt:
-- Ordner	Datei	Inhalt
-- labels/	sample_label.gp	G-PRINT Label mit Text + Barcode
-- logos/	kb_logo.svg	K&B-Buchstaben als Pixel-SVG (32×16)
-- logos/	checkerboard.mlg	Schachbrett-Muster im MLG-Binärformat
-- configs/	printer_test.pcf	Drucker-Netzwerkkonfiguration
-- printctl/	default.ctl	PrintControl mit Trigger/Speed

### Design
-- Forest TTK Dark Theme Unterstützung (res/themes/forest-dark.tcl)
-- Farbpalette kontrastreicher (Text heller, Buttons mit solidem Hintergrund + hellem Text)
-- Farbige Buttons (Grün/Rot/Orange/Blau/Lila/Gelb) nun auch unter Forest-Theme korrekt dargestellt

### AZ & Reisekosten (neuer Tab, neue Datei az_reisekosten.py)
-- Persönliche Daten speichern (Name, Wohnort, Personal-Nr)
-- Wochenansicht mit editierbaren Feldern: Status, Start/Ende/Pause, Stunden (live berechnet)
-- Detail-Panel pro Tag: Auftr.Nr, Kunde, Standort, Reiseweg, Start-/Endpunkt
-- Reisekosten-Felder: Art (Außen-/Innendienst/Ausland), Land, Übernachtung, Mahlzeiten, km, Sonstiges
-- KW-Daten werden pro Woche lokal gespeichert (res/kw_data/)
-- Stundenübersicht PDF: komplette Monatstabelle (A4 Querformat, alle KWs des Monats)
-- Excel Reisekostenabrechnung (FB_0020): befüllt Vorlage mit Monatsdaten inkl. Pauschalen-Felder

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
-- Schriftgröße der Tab-Leiste: 9 → 11 pt (Icons und Text deutlich größer)
-- Padding leicht angepasst für bessere Proportionen
-- FTP hat jetzt ein Icon: 📂
-- Alle Tab-Namen aufgeräumt — einheitliches Format 🔣 Name ohne unnötige Leerzeichen-Füller
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
