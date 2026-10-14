@echo off
rem Vigia de video: cria a tarefa no Agendador do Windows, rodando a cada 5 minutos.
rem 1) Troque a linha RAIZ pela sua pasta (a que tem entrada, revisao e saida).
rem 2) Rode este arquivo uma vez (duplo clique). Nao precisa ser administrador.
rem Para remover a tarefa:  schtasks /Delete /TN "Vigia de video" /F
rem Para ver a ultima rodada:  schtasks /Query /TN "Vigia de video" /V /FO LIST
setlocal
set "RAIZ=D:\Fred\video"
set "AQUI=%~dp0"
for /f "delims=" %%P in ('where pythonw 2^>nul') do (set "PYW=%%P" & goto :achou)
echo Nao achei o pythonw.exe no PATH. Reinstale o Python marcando "Add python.exe to PATH".
pause
exit /b 1
:achou
schtasks /Create /F /SC MINUTE /MO 5 /TN "Vigia de video" /TR "\"%PYW%\" \"%AQUI%vigia.py\" --raiz \"%RAIZ%\" --uma-vez"
if errorlevel 1 (
  echo A tarefa nao foi criada. Se o erro fala do tamanho do comando, mova esta pasta para um caminho mais curto.
) else (
  echo Pronto. O log fica em %RAIZ%\.vigia\vigia.log
)
pause
