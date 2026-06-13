[![Benutzerhandbuch](https://img.shields.io/badge/📋_Benutzerhandbuch-1a3a5c?style=flat-square)](README.md) [![Security](https://img.shields.io/badge/🔒_Security-1a3a5c?style=flat-square)](SECURITY.md) [![Changelog](https://img.shields.io/badge/📝_Changelog-1a3a5c?style=flat-square)](CHANGELOG.md) [![Requirements](https://img.shields.io/badge/📦_Requirements-1a3a5c?style=flat-square)](requirements.txt)

# alphaJET Interface-Tool — Requirements

> Abhängigkeiten, Systemvoraussetzungen und Laufzeitumgebung für das interne Servicetechniker-Tool.

![Version](https://img.shields.io/badge/Version-2.1.3-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-yellow)
![Architecture](https://img.shields.io/badge/Architektur-x86__64-lightgrey)
![Internal](https://img.shields.io/badge/Verwendung-Intern%20%2F%20Vertraulich-red)

---

## 🖥️ Systemvoraussetzungen

### Betriebssystem

| Anforderung       | Minimum                        | Empfohlen                      |
|-------------------|--------------------------------|--------------------------------|
| **OS**            | Windows 10 (Build 1903)        | Windows 11 (aktuell gepacht)   |
| **Architektur**   | x86\_64 (64-Bit)               | x86\_64 (64-Bit)               |
| **RAM**           | 2 GB                           | 4 GB                           |
| **Speicher**      | 200 MB freier Speicherplatz    | 500 MB                         |
| **Netzwerk**      | LAN / TCP-IP-Zugang zum Drucker | Dediziertes Servicenetzwerk   |
| **Auflösung**     | 1280 × 720                     | 1920 × 1080                    |

> ⚠️ **Hinweis:** Linux und macOS werden **nicht** unterstützt. Das Tool verwendet Windows-spezifische APIs (z. B. `ctypes` für Fenster-Handling, `winreg` für Registry-Zugriff).

---

## 🐍 Python-Laufzeitumgebung

| Komponente   | Version     | Hinweis                                      |
|--------------|-------------|----------------------------------------------|
| **Python**   | ≥ 3.11      | 3.12 empfohlen; 3.10 und älter nicht getestet |
| **pip**      | ≥ 23.0      | `python -m pip install --upgrade pip`        |
| **Bitness**  | 64-Bit      | 32-Bit-Python wird nicht unterstützt         |

---

## 📦 Python-Abhängigkeiten

```
pillow
openpyxl
pyftpdlib
pyinstaller
```

> Installationsbefehl:
> ```bash
> pip install -r requirements.txt
> ```

### Paketbeschreibungen

| Paket          | Version (getestet) | Verwendung                                                                 |
|----------------|--------------------|----------------------------------------------------------------------------|
| **Pillow**     | ≥ 10.0             | Bildverarbeitung: Icons, Vorschaubilder, Bildmanipulation in der GUI       |
| **openpyxl**   | ≥ 3.1              | Export und Import von Druckdaten / Etiketten im `.xlsx`-Format             |
| **pyftpdlib**  | ≥ 1.5              | Integrierter FTP-Server für Dateiübertragung zum/vom alphaJET-Controller   |
| **PyInstaller**| ≥ 6.0              | Build-Werkzeug zum Paketieren der Anwendung als portable `.exe`-Datei      |

---

## 🔌 Netzwerkvoraussetzungen

| Parameter            | Wert / Anforderung                                    |
|----------------------|-------------------------------------------------------|
| **Protokoll**        | TCP/IP (G-PRINT V3.0.0)                               |
| **Verbindungstyp**   | Ethernet (LAN), direkter oder Switch-Anschluss        |
| **Ports (FTP)**      | 21 (Control), passiv konfigurierbar                   |
| **Ports (G-PRINT)**  | konfigurierbar (Standard: siehe Netzwerkeinstellungen)|
| **Firewall**         | Ausgehende Verbindungen zum Drucker müssen erlaubt sein|

> 🔒 **Sicherheitshinweis:** FTP überträgt Daten **unverschlüsselt**. Ausschließlich in gesicherten, isolierten Servicenetzwerken verwenden (CRA Art. 13).

---

## 🏗️ Build-Voraussetzungen (nur für Entwickler)

Für das Kompilieren der `.exe` via `BUILD.bat`:

| Werkzeug          | Anforderung                              |
|-------------------|------------------------------------------|
| **PyInstaller**   | ≥ 6.0 (in `requirements.txt` enthalten) |
| **icon.ico**      | Im Projektroot vorhanden                 |
| **BUILD.bat**     | Im Projektroot ausführen                 |

```bat
:: Beispielaufruf
BUILD.bat
```

> Das Build-Script bündelt automatisch `icon.ico`, `forest-dark.tcl` und `forest-light.tcl` in die `.exe`.  
> Keine externen Ressourcen-Dateien nach dem Build notwendig.

---

## ✅ Kompatibilitätsmatrix

| Umgebung                        | Status         |
|---------------------------------|----------------|
| Windows 11 + Python 3.12        | ✅ Getestet     |
| Windows 10 + Python 3.11        | ✅ Getestet     |
| Windows 10 + Python 3.10        | ⚠️ Nicht getestet |
| Windows 10 (32-Bit)             | ❌ Nicht unterstützt |
| Linux / macOS                   | ❌ Nicht unterstützt |
| Als `.exe` (PyInstaller-Bundle) | ✅ Empfohlen für den Feldeinsatz |

---

*Letzte Aktualisierung: v2.1.3 · Intern / Vertraulich · König & Bauer*
