@echo off
setlocal
cd /d "%~dp0"
echo.
echo ===== NEXER - PREPARAR INTERFACE =====
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\prepare_frontend.ps1" %*
set "NEXER_EXIT=%ERRORLEVEL%"
echo.
if not "%NEXER_EXIT%"=="0" (
  echo [ERRO] A interface nao foi preparada. Confira os detalhes acima.
) else (
  echo [OK] Agora abra Nexer.bat ou Abrir-Nexer.cmd.
)
echo.
pause
exit /b %NEXER_EXIT%
