@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Nexer-Atualizado.exe" (
    echo Nexer-Atualizado.exe nao encontrado. Execute o build do launcher.
    pause
    exit /b 1
)
start "" "%~dp0Nexer-Atualizado.exe"
exit /b 0
