@echo off
cd /d "%~dp0"
title alphaJet Servicetechniker Tool - Build
echo.
echo  ==========================================
echo    Servicetechniker Tool
echo    Build-Prozess
echo  ==========================================
echo.

:: Abhaengigkeiten pruefen und ggf. installieren
echo  [PRE] Pruefe Abhaengigkeiten...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo  [INFO] PyInstaller nicht gefunden. Wird installiert...
    pip install pyinstaller -q
)
python -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] openpyxl nicht gefunden. Wird installiert...
    pip install openpyxl -q
)
python -c "import pyftpdlib" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] pyftpdlib nicht gefunden. Wird installiert...
    pip install pyftpdlib -q
)
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Pillow nicht gefunden. Wird installiert...
    pip install pillow -q
)

:: Laufende Instanz beenden (falls Tool noch offen)
echo  [0/3] Laufende Instanz beenden (falls noetig)...
taskkill /f /im "alphaJet-InterfaceTool.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Alten Build aufraeumen
echo  [1/3] Alte Build-Dateien loeschen...
if exist "dist\alphaJet-InterfaceTool.exe" (
    del /f /q "dist\alphaJet-InterfaceTool.exe"
    if exist "dist\alphaJet-InterfaceTool.exe" (
        echo  [FEHLER] Datei gesperrt - bitte Tool manuell schliessen und nochmal starten.
        pause & exit /b 1
    )
)

:: CVE-Pruefung der Abhaengigkeiten
echo  [PRE] CVE-Pruefung der Abhaengigkeiten...
python -m pip_audit --version >nul 2>&1
if errorlevel 1 (
    echo  [INFO] pip-audit nicht gefunden. Wird installiert...
    pip install pip-audit
)
python -m pip_audit --requirement requirements.txt
if errorlevel 1 (
    echo  [WARNUNG] Bekannte CVEs gefunden - bitte pruefen!
    pause
)

:: Kompilieren
echo  [2/3] Kompiliere...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --icon "icon.ico" ^
    --name "alphaJet-InterfaceTool" ^
    --add-data "icon.ico;." ^
    --add-data "fonts;fonts" ^
    --add-data "res;res" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL.Image" ^
    --hidden-import "PIL.ImageDraw" ^
    --hidden-import "PIL.ImageFont" ^
    --hidden-import "PIL.ImageTk" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "tkinter.filedialog" ^
    --hidden-import "tkinter.simpledialog" ^
    --hidden-import "tkinter.scrolledtext" ^
    --collect-all "openpyxl" ^
    --collect-all "pyftpdlib" ^
    tool.py
if errorlevel 1 (
    echo.
    echo  [FEHLER] Build fehlgeschlagen. Siehe Ausgabe oben.
    pause & exit /b 1
)

:: version.json aktualisieren
echo  [3/3] version.json aktualisieren...
python update_version.py
echo.
echo  ==========================================
echo  BUILD ERFOLGREICH
echo  Datei: dist\alphaJet-InterfaceTool.exe
echo  ==========================================
echo.
pause
