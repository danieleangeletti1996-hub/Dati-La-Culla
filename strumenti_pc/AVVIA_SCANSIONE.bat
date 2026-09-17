@echo off
setlocal EnableExtensions
title Scansione PC La Culla
cd /d "%~dp0"
set "SCRIPT=%~dp0scan_pc_laculla.py"
echo ==========================================================
echo  SCANSIONE PC LA CULLA - ricerca documenti per lo Studio
echo  Solo lettura e copie: nessun file viene spostato,
echo  rinominato o cancellato.
echo ==========================================================
echo.
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY python3 --version >nul 2>&1 && set "PY=python3"
if not defined PY goto :nopython
echo Uso l'interprete: %PY%
echo.
%PY% "%SCRIPT%" %*
set "ESITO=%ERRORLEVEL%"
echo.
if "%ESITO%"=="0" (
  echo Finito. Il riepilogo si chiama RIEPILOGO.md nella cartella 00_scan dell'archivio.
) else (
  echo Terminato con codice %ESITO%. Leggi i messaggi qui sopra.
)
echo.
pause
exit /b %ESITO%

:nopython
echo Python non risulta installato su questo PC.
echo.
echo Per installarlo (una volta sola):
echo   1. apri https://www.python.org/downloads/windows/ e scarica "Windows installer (64-bit)"
echo      oppure, da un prompt dei comandi:  winget install -e --id Python.Python.3.12
echo   2. durante l'installazione spunta "Add python.exe to PATH"
echo   3. rilancia questo file.
echo.
pause
exit /b 1
