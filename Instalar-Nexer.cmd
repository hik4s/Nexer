@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_nexer.ps1" %*
set "NEXER_EXIT=%ERRORLEVEL%"
if not "%NEXER_EXIT%"=="0" (
  echo.
  echo A instalacao nao foi concluida. Confira a mensagem acima.
  pause
)
exit /b %NEXER_EXIT%
