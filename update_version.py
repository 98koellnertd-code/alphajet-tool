"""Aktualisiert version.json und CHANGELOG.md mit der aktuellen APP_VERSION aus tool.py.
Wird von BUILD.bat aufgerufen — vermeidet fragiles python -c in der Batch."""
import json
import os
import re

# APP_VERSION lesen ohne das ganze Modul zu importieren (kein tkinter beim Build noetig)
version = "0.0.0"
with open("tool.py", encoding="utf-8") as f:
    for line in f:
        if line.strip().startswith("APP_VERSION"):
            version = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

# ── CHANGELOG.md ──────────────────────────────────────────────────────────────
notes = ""
if os.path.exists("CHANGELOG.md"):
    with open("CHANGELOG.md", encoding="utf-8") as f:
        content = f.read()

    # "neuste Version" Banner-Zeile aktualisieren
    content = re.sub(
        r"(-- neuste Version )v[\d.]+( --)",
        rf"\g<1>v{version}\2",
        content
    )

    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  CHANGELOG.md aktualisiert: v{version}")

    # ###LATEST CHANGES### Abschnitt → notes für den Update-Dialog
    match = re.search(
        r"###LATEST CHANGES###\s*\n(.*?)(?=\n#{10,})",
        content, re.DOTALL
    )
    if match:
        notes = match.group(1).strip()

# ── version.json ──────────────────────────────────────────────────────────────
data = {}
if os.path.exists("version.json"):
    try:
        with open("version.json", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

data["version"] = version
data["download_url"] = f"https://github.com/98koellnertd-code/alphajet-tool/releases/download/v{version}/alphaJet-InterfaceTool.exe"
data.setdefault("name", "K & B alphaJET - Servicetechniker Tool")
data["notes"] = notes

with open("version.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"  version.json aktualisiert: v{version}")
