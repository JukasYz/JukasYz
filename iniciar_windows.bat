@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Cyber Snake Royale - Servidor
if exist ".venv\Scripts\python.exe" goto dependencies
python -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 goto use_python
py -3 -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 goto use_py
echo Python 3.10 ou superior nao encontrado.
echo Instale em https://www.python.org/downloads/ e marque Add Python to PATH.
echo Feche e abra o terminal depois da instalacao.
goto failure
:use_python
python -m venv .venv
if errorlevel 1 goto failure
goto dependencies
:use_py
py -3 -m venv .venv
if errorlevel 1 goto failure
:dependencies
".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3,10))"
if errorlevel 1 goto failure
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failure
echo Abra o painel do apresentador informado abaixo. Nao compartilhe sua chave.
".venv\Scripts\python.exe" server.py
if errorlevel 1 goto failure
pause
exit /b 0
:failure
echo.
echo Nao foi possivel iniciar. Leia a mensagem acima.
echo Se a pasta .venv veio de outro computador, remova somente essa pasta e tente novamente.
pause
exit /b 1
