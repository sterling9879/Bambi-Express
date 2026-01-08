@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Bambi Express - Instalador

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║              BAMBI EXPRESS - VIDEO GENERATOR                 ║
echo ║                   Instalação Automática                      ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: ============================================
:: VERIFICAR PYTHON
:: ============================================
echo [1/7] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERRO: Python não encontrado!
    echo.
    echo    Por favor, instale o Python 3.10+ em:
    echo    https://www.python.org/downloads/
    echo.
    echo    IMPORTANTE: Marque a opção "Add Python to PATH" durante a instalação!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    ✓ Python %PYTHON_VERSION% encontrado

:: ============================================
:: VERIFICAR NODE.JS
:: ============================================
echo.
echo [2/7] Verificando Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERRO: Node.js não encontrado!
    echo.
    echo    Por favor, instale o Node.js 18+ em:
    echo    https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
echo    ✓ Node.js %NODE_VERSION% encontrado

:: ============================================
:: VERIFICAR FFMPEG
:: ============================================
echo.
echo [3/7] Verificando FFMPEG...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  AVISO: FFMPEG não encontrado!
    echo.
    echo    O FFMPEG é necessário para gerar vídeos.
    echo    Instale usando um dos métodos:
    echo.
    echo    1. Winget (recomendado):
    echo       winget install ffmpeg
    echo.
    echo    2. Chocolatey:
    echo       choco install ffmpeg
    echo.
    echo    3. Download manual:
    echo       https://ffmpeg.org/download.html
    echo       (Adicione ao PATH após instalar)
    echo.
    set FFMPEG_MISSING=1
) else (
    echo    ✓ FFMPEG encontrado
)

:: ============================================
:: CRIAR AMBIENTE VIRTUAL PYTHON
:: ============================================
echo.
echo [4/7] Configurando ambiente Python...

cd /d "%~dp0backend"

if not exist "venv" (
    echo    Criando ambiente virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ ERRO: Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
)

echo    Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo    Atualizando pip...
python -m pip install --upgrade pip --quiet

echo    Instalando dependências Python...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ❌ ERRO: Falha ao instalar dependências Python
    pause
    exit /b 1
)
echo    ✓ Dependências Python instaladas

:: ============================================
:: CONFIGURAR .ENV
:: ============================================
echo.
echo [5/7] Configurando variáveis de ambiente...

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo    ✓ Arquivo .env criado a partir do .env.example
        echo.
        echo    ⚠️  IMPORTANTE: Edite o arquivo backend\.env com suas API keys:
        echo       - ELEVENLABS_API_KEY
        echo       - ASSEMBLYAI_API_KEY
        echo       - GEMINI_API_KEY
        echo       - WAVESPEED_API_KEY
    ) else (
        echo    ⚠️  Arquivo .env.example não encontrado
    )
) else (
    echo    ✓ Arquivo .env já existe
)

:: Criar diretórios necessários
if not exist "storage" mkdir storage
if not exist "storage\temp" mkdir storage\temp
if not exist "storage\outputs" mkdir storage\outputs
if not exist "storage\music" mkdir storage\music
echo    ✓ Diretórios de storage criados

cd /d "%~dp0"

:: ============================================
:: INSTALAR DEPENDÊNCIAS NODE.JS
:: ============================================
echo.
echo [6/7] Instalando dependências do Frontend...

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo    Executando npm install (pode demorar alguns minutos)...
    call npm install --silent
    if %errorlevel% neq 0 (
        echo ❌ ERRO: Falha ao instalar dependências Node.js
        pause
        exit /b 1
    )
) else (
    echo    Atualizando dependências...
    call npm install --silent
)
echo    ✓ Dependências do Frontend instaladas

cd /d "%~dp0"

:: ============================================
:: CRIAR SCRIPTS DE EXECUÇÃO
:: ============================================
echo.
echo [7/7] Criando scripts de execução...

:: Script para iniciar apenas o backend
echo @echo off > start-backend.bat
echo chcp 65001 ^>nul >> start-backend.bat
echo title Bambi Express - Backend >> start-backend.bat
echo cd /d "%%~dp0backend" >> start-backend.bat
echo call venv\Scripts\activate.bat >> start-backend.bat
echo echo. >> start-backend.bat
echo echo ========================================== >> start-backend.bat
echo echo   Bambi Express - Backend API >> start-backend.bat
echo echo   http://localhost:8000 >> start-backend.bat
echo echo ========================================== >> start-backend.bat
echo echo. >> start-backend.bat
echo python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 >> start-backend.bat

:: Script para iniciar apenas o frontend
echo @echo off > start-frontend.bat
echo chcp 65001 ^>nul >> start-frontend.bat
echo title Bambi Express - Frontend >> start-frontend.bat
echo cd /d "%%~dp0frontend" >> start-frontend.bat
echo echo. >> start-frontend.bat
echo echo ========================================== >> start-frontend.bat
echo echo   Bambi Express - Frontend >> start-frontend.bat
echo echo   http://localhost:3000 >> start-frontend.bat
echo echo ========================================== >> start-frontend.bat
echo echo. >> start-frontend.bat
echo npm run dev >> start-frontend.bat

:: Script para iniciar tudo
echo @echo off > start.bat
echo chcp 65001 ^>nul >> start.bat
echo title Bambi Express >> start.bat
echo echo. >> start.bat
echo echo Iniciando Bambi Express... >> start.bat
echo echo. >> start.bat
echo start "Backend" cmd /k "%%~dp0start-backend.bat" >> start.bat
echo timeout /t 3 /nobreak ^>nul >> start.bat
echo start "Frontend" cmd /k "%%~dp0start-frontend.bat" >> start.bat
echo timeout /t 5 /nobreak ^>nul >> start.bat
echo start http://localhost:3000 >> start.bat

echo    ✓ Scripts criados: start.bat, start-backend.bat, start-frontend.bat

:: ============================================
:: FINALIZAÇÃO
:: ============================================
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║                 ✓ INSTALAÇÃO CONCLUÍDA!                      ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

if defined FFMPEG_MISSING (
    echo ⚠️  ATENÇÃO: Instale o FFMPEG antes de usar!
    echo.
)

echo PRÓXIMOS PASSOS:
echo.
echo    1. Edite o arquivo backend\.env com suas API keys
echo.
echo    2. Execute start.bat para iniciar a aplicação
echo       (ou use start-backend.bat e start-frontend.bat separadamente)
echo.
echo    3. Acesse http://localhost:3000 no navegador
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
pause
