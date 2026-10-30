@echo off
title Iniciar FINDES (Segundo Plano)
chcp 65001 >nul
cd /d "%~dp0"

echo Verificando se o FINDES ja esta rodando...
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*findes.py*' -and $_.CommandLine -notlike '*powershell*' -and $_.CommandLine -notlike '*cmd.exe*' }; if ($procs) { Write-Host 'O FINDES ja esta em execucao!' -ForegroundColor Yellow; exit 1 } else { exit 0 }"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo O FINDES ja esta em execucao!
    ping 127.0.0.1 -n 2 >nul
    exit /b 1
)

echo Iniciando FINDES em segundo plano (sem janela CMD)...

powershell -NoProfile -WindowStyle Hidden -Command "Start-Process python -ArgumentList 'findes.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden"

echo.
echo ==============================================
echo       FINDES INICIADO COM SUCESSO!
echo  (Rodando em segundo plano e gravando logs)
echo ==============================================
echo.
ping 127.0.0.1 -n 3 >nul
