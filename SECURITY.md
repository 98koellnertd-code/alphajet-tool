# Security Policy — alphaJET Interface Tool

> **Internes Servicetechniker-Tool** zur Fernsteuerung und Konfiguration von Koenig & Bauer alphaJET CIJ-Druckern über das G-PR(INT)-Protokoll (TCP/IP).

![Version](https://img.shields.io/badge/Version-2.1.3-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Protocol](https://img.shields.io/badge/Protokoll-G--PR(INT)%20V3.0.0-orange)
![Python](https://img.shields.io/badge/Python-3.11%2B-yellow)
![Internal](https://img.shields.io/badge/Verwendung-Intern%20%2F%20Vertraulich-red)

---

Dieses Dokument beschreibt den Umgang mit Sicherheitsschwachstellen im Rahmen der
Anforderungen des EU Cyber Resilience Act (CRA, Verordnung 2024/2847).

## Unterstützte Versionen

| Version | Sicherheits-Updates |
|---------|---------------------|
| aktuell (main) | ✅ Ja |
| ältere Builds   | ❌ Nein – bitte aktualisieren |

## Schwachstellen melden (Coordinated Disclosure)

Sicherheitslücken bitte **nicht** als öffentliches GitHub-Issue melden, sondern direkt:

**E-Mail:** marvin_koellner@outlook.de  
**Betreff:** `[SECURITY] alphaJET-InterfaceTool – <Kurzbeschreibung>`

Bitte folgende Informationen mitschicken:
- Beschreibung der Schwachstelle
- Reproduktionsschritte / Proof-of-Concept (falls vorhanden)
- Betroffene Versionen / Betriebssysteme
- Schweregrad-Einschätzung (niedrig / mittel / hoch / kritisch)

### Reaktionszeiten
| Schweregrad | Erste Rückmeldung | Patch-Ziel |
|------------|-------------------|------------|
| Kritisch   | 24 h              | 7 Tage     |
| Hoch       | 48 h              | 14 Tage    |
| Mittel     | 5 Werktage        | 30 Tage    |
| Niedrig    | 10 Werktage       | nächste Release |

Aktiv ausgenutzte Schwachstellen werden gemäß CRA Art. 14 innerhalb von 24 h an
die zuständige nationale Behörde (BSI) und ENISA gemeldet.

## Bekannte Einschränkungen / akzeptierte Risiken

### Unverschlüsselte FTP-Verbindung (CRA Annex I, Part I, Abs. 3d)
Die Kommunikation mit den alphaJET-Druckern erfolgt über Plain-FTP (Port 21).
Die Drucker-Firmware von K&B unterstützt ausschließlich unverschlüsseltes FTP
(FTPS/SFTP nicht verfügbar). Dieses Risiko ist bewusst akzeptiert und dokumentiert.

**Empfehlung:** Das Tool ausschließlich in isolierten, gesicherten Industrie-Netzwerken
verwenden. Keine Verwendung in öffentlichen oder ungesicherten WLANs.

### Geräte-Standardpasswörter
Die Drucker werden mit Herstellerpasswörtern ausgeliefert. Diese sind im Tool
als Vorgabewerte hinterlegt, damit Servicetechniker schnell verbinden können.
**Empfehlung:** Passwort am Gerät ändern und in `res/ftp_credentials.json` hinterlegen.

**Passwort am Gerät ändern (alphaJET)**
siehe Dokumentation - Passwort ändern FTP AJD UND AJ5 (intern)

**Angepasste Zugangsdaten in `res/ftp_credentials.json` hinterlegen:**

Die Datei `res/ftp_credentials.json` wird **nicht** ins Repository eingecheckt und
überschreibt die eingebauten Standardwerte. Struktur (Schlüssel = Gerätetyp-Name):

```json
{
  "AJD": {
    "user": "User",
    "pass": "IhrNeuesPasswort",
    "port": 21,
    "host": ""
  },
  "AJ5": {
    "user": "User",
    "pass": "IhrNeuesPasswort",
    "port": 21,
    "host": ""
  }
}
```

Felder:
- `user` – FTP-Benutzername (Groß-/Kleinschreibung beachten)
- `pass` – neues Passwort
- `port` – FTP-Port (Standard: 21)
- `host` – leer lassen für AJD/AJ5 (IP wird aus der App-Konfiguration gelesen)

## Sicherheitsmaßnahmen (implementiert)

- **Update-Integrität:** Downloads werden per SHA-256 geprüft (sofern in `version.json` hinterlegt)
- **HTTPS-Pflicht:** Update-Downloads werden nur über HTTPS akzeptiert
- **Input-Validierung:** IP-Adressen, Ports, XML-Struktur werden vor Verwendung geprüft
- **Path-Traversal-Schutz:** FTP-Download-Pfade werden gegen das Zielverzeichnis validiert
- **Keine externen Telemetrie-Aufrufe:** Das Tool kommuniziert ausschließlich mit konfigurierten Druckern und der optionalen Update-URL

## Software Bill of Materials (SBOM)

Siehe [`sbom.json`](sbom.json) (CycloneDX 1.4).
