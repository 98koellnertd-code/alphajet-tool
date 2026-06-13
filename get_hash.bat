@echo off
setlocal

set FILE=alphaJet-InterfaceTool.exe
set HASHFILE=alphaJet-InterfaceTool.sha256

echo Berechne SHA256 fuer: %FILE%
echo.

powershell -Command "Get-FileHash '.\%FILE%' -Algorithm SHA256 | Select-Object -ExpandProperty Hash" > "%HASHFILE%"

set /p HASH=<"%HASHFILE%"

echo Hash: %HASH%
echo.
echo Gespeichert in: %HASHFILE%
echo.
pause
