@echo off
setlocal enabledelayedexpansion
title Bambi Express - Instalador

echo.
echo ============================================================
echo              BAMBI EXPRESS - VIDEO GENERATOR
echo ============================================================
echo.

echo [1/7] Verificando Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python encontrado

echo.
echo [2/7] Verificando Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Node.js nao encontrado!
    echo Baixe em: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js encontrado

echo.
echo [3/7] Verificando FFMPEG...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] FFMPEG nao encontrado - instale depois
) else (
    echo [OK] FFMPEG encontrado
)

echo.
echo [4/7] Configurando Python...
cd /d "%~dp0backend"
if not exist "venv" python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo [OK] Python configurado

echo.
echo [5/7] Criando pastas...
if not exist "storage" mkdir storage
if not exist "storage\temp" mkdir storage\temp
if not exist "storage\outputs" mkdir storage\outputs
if not exist "storage\music" mkdir storage\music
echo [OK] Pastas criadas

cd /d "%~dp0"

echo.
echo [6/7] Instalando Frontend...
cd /d "%~dp0frontend"
call npm install
echo [OK] Frontend instalado

cd /d "%~dp0"

echo.
echo [7/7] Criando scripts...
echo @echo off > start.bat
echo start cmd /k "cd backend && call venv\Scripts\activate.bat && python -m uvicorn src.main:app --reload --port 8000" >> start.bat
echo timeout /t 3 /nobreak ^>nul >> start.bat
echo start cmd /k "cd frontend && npm run dev" >> start.bat
echo timeout /t 5 /nobreak ^>nul >> start.bat
echo start http://localhost:3000 >> start.bat
echo [OK] Scripts criados

echo.
echo ============================================================
echo              INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo Execute: start.bat
echo.
pause
