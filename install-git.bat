@echo off
title Instalando Git...

echo.
echo ============================================================
echo              INSTALANDO GIT PARA WINDOWS
echo ============================================================
echo.

:: Verificar se ja tem Git
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Git ja esta instalado!
    git --version
    echo.
    pause
    exit /b 0
)

:: Tentar com winget primeiro (Windows 10/11)
echo Tentando instalar com winget...
winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements
if %errorlevel% equ 0 (
    echo.
    echo [OK] Git instalado com sucesso via winget!
    echo.
    echo IMPORTANTE: Feche este terminal e abra um novo para usar o git.
    echo.
    pause
    exit /b 0
)

:: Se winget falhar, baixar manualmente
echo.
echo Winget nao disponivel. Baixando instalador...
echo.

:: Criar pasta temp se nao existir
if not exist "%TEMP%\git-install" mkdir "%TEMP%\git-install"

:: Baixar Git usando PowerShell
echo Baixando Git (pode demorar alguns minutos)...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe' -OutFile '%TEMP%\git-install\git-installer.exe'}"

if not exist "%TEMP%\git-install\git-installer.exe" (
    echo.
    echo [ERRO] Falha ao baixar o Git.
    echo.
    echo Baixe manualmente em: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando Git (aguarde)...
"%TEMP%\git-install\git-installer.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] Git instalado com sucesso!
    echo ============================================================
    echo.
    echo IMPORTANTE: Feche TODOS os terminais e abra um novo!
    echo Depois execute update.bat para atualizar o projeto.
    echo.
) else (
    echo.
    echo [ERRO] Falha na instalacao.
    echo Tente instalar manualmente: https://git-scm.com/download/win
    echo.
)

:: Limpar
del /q "%TEMP%\git-install\git-installer.exe" 2>nul

pause
