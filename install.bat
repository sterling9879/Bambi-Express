@echo off
setlocal enabledelayedexpansion

title Bambi Express - Instalador

echo.
echo ============================================================
echo.
echo              BAMBI EXPRESS - VIDEO GENERATOR
echo                   Instalacao Automatica
echo.
echo ============================================================
echo.

:: ============================================
:: VERIFICAR PYTHON
:: ============================================
echo [1/7] Verificando Python...

where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [ERRO] Python nao encontrado!
        echo.
        echo    Por favor, instale o Python 3.10+ em:
        echo    https://www.python.org/downloads/
        echo.
        echo    IMPORTANTE: Marque a opcao "Add Python to PATH" durante a instalacao!
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
    )
) else (
    set PYTHON_CMD=python
)

for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    [OK] Python %PYTHON_VERSION% encontrado

:: ============================================
:: VERIFICAR NODE.JS
:: ============================================
echo.
echo [2/7] Verificando Node.js...

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Node.js nao encontrado!
    echo.
    echo    Por favor, instale o Node.js 18+ em:
    echo    https://nodejs.org/
    echo.
    echo    Reinicie o terminal apos a instalacao.
    echo.
    pause
    exit /b 1
)

for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
echo    [OK] Node.js %NODE_VERSION% encontrado

:: ============================================
:: VERIFICAR NPM
:: ============================================
echo.
echo [3/7] Verificando npm...

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] npm nao encontrado!
    echo.
    echo    Reinstale o Node.js em: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=1" %%i in ('npm --version 2^>^&1') do set NPM_VERSION=%%i
echo    [OK] npm %NPM_VERSION% encontrado

:: ============================================
:: VERIFICAR FFMPEG
:: ============================================
echo.
echo [4/7] Verificando FFMPEG...

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] FFMPEG nao encontrado!
    echo.
    echo    O FFMPEG e necessario para gerar videos.
    echo    Instale usando um dos metodos:
    echo.
    echo    1. Winget: winget install ffmpeg
    echo    2. Chocolatey: choco install ffmpeg
    echo    3. Download: https://ffmpeg.org/download.html
    echo.
    set FFMPEG_MISSING=1
) else (
    echo    [OK] FFMPEG encontrado
)

:: ============================================
:: CRIAR AMBIENTE VIRTUAL PYTHON
:: ============================================
echo.
echo [5/7] Configurando ambiente Python...

cd /d "%~dp0backend"
if %errorlevel% neq 0 (
    echo [ERRO] Pasta backend nao encontrada!
    pause
    exit /b 1
)

if not exist "venv" (
    echo    Criando ambiente virtual...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual
        echo    Tente: %PYTHON_CMD% -m pip install virtualenv
        pause
        exit /b 1
    )
)

echo    Ativando ambiente virtual...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar ambiente virtual
    pause
    exit /b 1
)

echo    Atualizando pip...
python -m pip install --upgrade pip

echo    Instalando dependencias Python...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias Python
    echo    Verifique sua conexao com a internet
    pause
    exit /b 1
)
echo    [OK] Dependencias Python instaladas

:: Criar diretorios necessarios
if not exist "storage" mkdir storage
if not exist "storage\temp" mkdir storage\temp
if not exist "storage\outputs" mkdir storage\outputs
if not exist "storage\music" mkdir storage\music
echo    [OK] Diretorios de storage criados

cd /d "%~dp0"

:: ============================================
:: INSTALAR DEPENDENCIAS NODE.JS
:: ============================================
echo.
echo [6/7] Instalando dependencias do Frontend...

cd /d "%~dp0frontend"
if %errorlevel% neq 0 (
    echo [ERRO] Pasta frontend nao encontrada!
    pause
    exit /b 1
)

echo    Executando npm install (pode demorar alguns minutos)...
call npm install
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias Node.js
    echo    Tente executar manualmente: cd frontend ^&^& npm install
    pause
    exit /b 1
)
echo    [OK] Dependencias do Frontend instaladas

cd /d "%~dp0"

:: ============================================
:: CRIAR SCRIPTS DE EXECUCAO
:: ============================================
echo.
echo [7/7] Criando scripts de execucao...

:: Script para iniciar o backend
(
echo @echo off
echo title Bambi Express - Backend
echo cd /d "%%~dp0backend"
echo call venv\Scripts\activate.bat
echo echo.
echo echo ==========================================
echo echo   Bambi Express - Backend API
echo echo   http://localhost:8000
echo echo ==========================================
echo echo.
echo python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
echo pause
) > start-backend.bat

:: Script para iniciar o frontend
(
echo @echo off
echo title Bambi Express - Frontend
echo cd /d "%%~dp0frontend"
echo echo.
echo echo ==========================================
echo echo   Bambi Express - Frontend
echo echo   http://localhost:3000
echo echo ==========================================
echo echo.
echo call npm run dev
echo pause
) > start-frontend.bat

:: Script para iniciar tudo
(
echo @echo off
echo title Bambi Express
echo echo.
echo echo Iniciando Bambi Express...
echo echo.
echo start "Backend" cmd /k "%%~dp0start-backend.bat"
echo timeout /t 5 /nobreak ^>nul
echo start "Frontend" cmd /k "%%~dp0start-frontend.bat"
echo timeout /t 8 /nobreak ^>nul
echo start http://localhost:3000
) > start.bat

echo    [OK] Scripts criados: start.bat, start-backend.bat, start-frontend.bat

:: ============================================
:: FINALIZACAO
:: ============================================
echo.
echo ============================================================
echo.
echo              INSTALACAO CONCLUIDA COM SUCESSO!
echo.
echo ============================================================
echo.

if defined FFMPEG_MISSING (
    echo [ATENCAO] Instale o FFMPEG antes de usar!
    echo.
)

echo PROXIMOS PASSOS:
echo.
echo    1. Configure suas API keys na interface web
echo       (Configuracoes ^> APIs)
echo.
echo    2. Execute start.bat para iniciar a aplicacao
echo.
echo    3. Acesse http://localhost:3000 no navegador
echo.
echo ============================================================
echo.
pause
