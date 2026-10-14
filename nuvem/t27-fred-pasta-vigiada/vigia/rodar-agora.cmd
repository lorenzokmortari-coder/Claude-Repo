@echo off
rem Vigia de video: uma rodada agora, e depois mostra em que pe esta cada video.
rem Troque a linha RAIZ pela sua pasta.
setlocal
set "RAIZ=D:\Fred\video"
python "%~dp0vigia.py" --raiz "%RAIZ%" --uma-vez
echo.
python "%~dp0vigia.py" --raiz "%RAIZ%" --status
pause
