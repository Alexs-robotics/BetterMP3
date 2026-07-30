@echo off
REM ============================================================
REM build_exe.bat
REM Genera l'eseguibile Windows (.exe) dell'MP3 Player.
REM Esegui questo script da un Prompt dei comandi di Windows,
REM dentro la cartella del progetto, DOPO aver installato le
REM dipendenze con: pip install -r requirements.txt
REM
REM Prerequisiti:
REM   - VLC media player installato (per le DLL di libvlc), oppure
REM     copia manualmente libvlc.dll, libvlccore.dll e la cartella
REM     "plugins" di VLC nella cartella di questo progetto prima
REM     di lanciare lo script.
REM   - ffmpeg.exe raggiungibile nel PATH (richiesto da yt-dlp per
REM     estrarre/convertire l'audio in mp3).
REM ============================================================

pyinstaller --noconfirm --windowed --onefile ^
    --name "MP3Player" ^
    --add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;." ^
    --add-binary "C:\Program Files\VideoLAN\VLC\libvlccore.dll;." ^
    --add-data "C:\Program Files\VideoLAN\VLC\plugins;plugins" ^
    main.py

echo.
echo Eseguibile creato in dist\MP3Player.exe
pause
