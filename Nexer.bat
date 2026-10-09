@echo off
setlocal

rem =====================================================
rem Pasta do projeto
rem =====================================================

cd /d "%~dp0"

rem =====================================================
rem Configurações
rem =====================================================

set "NOME_EXE=Nexer.exe"
set "NOME_ATALHO=Nexer"

rem =====================================================
rem Cria atalho (uma única vez)
rem =====================================================

if not exist "%~dp0.atalho_criado" (

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ws = New-Object -ComObject WScript.Shell;" ^
        "$lnk = $ws.CreateShortcut('%USERPROFILE%\Desktop\%NOME_ATALHO%.lnk');" ^
        "$lnk.TargetPath = '%~dp0%NOME_EXE%';" ^
        "$lnk.WorkingDirectory = '%~dp0';" ^
        "$lnk.IconLocation = '%~dp0%NOME_EXE%';" ^
        "$lnk.Save()"

    if not errorlevel 1 (
        echo.>"%~dp0.atalho_criado"
    )
)

rem =====================================================
rem Verifica Python
rem =====================================================

where python >nul 2>nul

if errorlevel 1 (

    call :instalar_python

    for /f "skip=2 tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SysPath=%%B"
    for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "UserPath=%%B"

    set "PATH=%SysPath%;%UserPath%;%PATH%"

    where python >nul 2>nul

    if errorlevel 1 (
        exit /b 1
    )
)

rem =====================================================
rem Ambiente virtual
rem =====================================================

if not exist "venv\" (

    echo Criando ambiente virtual...

    python -m venv venv

)

rem =====================================================
rem Ativa venv
rem =====================================================

call venv\Scripts\activate.bat

rem =====================================================
rem Dependências
rem =====================================================

echo Verificando dependências...

pip install -r requisitos.txt --disable-pip-version-check --quiet

rem =====================================================
rem Edge Playwright
rem =====================================================

python -m playwright install msedge >nul 2>nul

rem =====================================================
rem Logs
rem =====================================================

if not exist "logs" (
    mkdir logs
)

rem =====================================================
rem Inicia Launcher
rem =====================================================

start "" venv\Scripts\pythonw.exe launcher.py

exit /b 0


rem =====================================================
rem Instala Python
rem =====================================================

:instalar_python

where winget >nul 2>nul

if errorlevel 1 (
    exit /b 1
)

winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements

goto :eof