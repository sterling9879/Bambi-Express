@echo off
title Bambi Express - Atualizador

echo.
echo ============================================================
echo              BAMBI EXPRESS - ATUALIZADOR
echo ============================================================
echo.

cd /d "%~dp0"

echo Verificando atualizacoes...
echo.

git pull origin main
if %errorlevel% neq 0 (
    echo.
    echo Tentando branch atual...
    git pull
)

echo.
echo ============================================================
echo.

if %errorlevel% equ 0 (
    echo [OK] Codigo atualizado com sucesso!
    echo.
    echo Se houve mudancas nas dependencias, execute:
    echo   - Backend: cd backend ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    echo   - Frontend: cd frontend ^&^& npm install
) else (
    echo [AVISO] Verifique se o git esta instalado
    echo   Download: https://git-scm.com/download/win
)

echo.
echo ============================================================
echo.
pause
