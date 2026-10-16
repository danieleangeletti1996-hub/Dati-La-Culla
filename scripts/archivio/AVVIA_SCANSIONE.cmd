@echo off
rem AVVIA_SCANSIONE.cmd - La Culla: scansione del PC a un clic (solo lettura e copie, nessuna modifica).
rem Cerca da solo la cartella Google Drive "LA CULLA - ARCHIVIO", inventaria il PC e copia i documenti fiscali trovati.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ==========================================================
echo  LA CULLA - scansione del PC per l'archivio (solo lettura)
echo  Non chiudere questa finestra: puo' durare 10-60 minuti.
echo ==========================================================
echo.
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 -X utf8 "%~dp0avvia_scansione.py" %*
    goto :fine
)
where python >nul 2>&1
if %errorlevel%==0 (
    python -X utf8 "%~dp0avvia_scansione.py" %*
    goto :fine
)
echo Python non e' installato su questo PC.
echo Installalo dal Microsoft Store (cerca "Python 3.12") oppure da https://www.python.org/downloads/windows/
echo (durante l'installazione spunta "Add python.exe to PATH"), poi riavvia questo file.
:fine
echo.
echo Finito. I risultati sono nella cartella 00_scan dell'ARCHIVIO (vedi righe sopra).
pause
