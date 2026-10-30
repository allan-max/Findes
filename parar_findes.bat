@echo off
title Parar FINDES
chcp 65001 >nul

echo ==============================================
echo           PARANDO O ROBO FINDES...
echo ==============================================
echo.

powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*findes.py*' -and $_.CommandLine -notlike '*powershell*' -and $_.CommandLine -notlike '*cmd.exe*' }; if ($procs) { foreach ($p in $procs) { Write-Host ('Encerrando processo PID: ' + $p.ProcessId); Stop-Process -Id $p.ProcessId -Force } Write-Host 'Robo FINDES parado com sucesso!' -ForegroundColor Green } else { Write-Host 'O FINDES nao esta em execucao no momento.' -ForegroundColor Yellow }"

echo.
ping 127.0.0.1 -n 3 >nul
