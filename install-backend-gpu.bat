@echo off
title Bambi Express - Instalador Backend GPU

echo.
echo ============================================================
echo         INSTALADOR DE DEPENDENCIAS GPU - BACKEND
echo ============================================================
echo.

cd /d "%~dp0backend"

echo [1/5] Ativando ambiente virtual...
if not exist "venv" (
    echo Criando venv...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo [2/5] Atualizando pip...
python -m pip install --upgrade pip

echo.
echo [3/5] Instalando dependencias base...
pip install -r requirements.txt

echo.
echo [4/5] Instalando PyTorch com CUDA...
echo (Isso pode demorar alguns minutos)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo [5/5] Instalando dependencias GPU (Diffusers, Transformers, etc)...
pip install diffusers>=0.30.0
pip install transformers>=4.44.0
pip install accelerate>=0.33.0
pip install bitsandbytes>=0.43.0
pip install safetensors>=0.4.0
pip install sentencepiece>=0.2.0
pip install huggingface-hub>=0.24.0

echo.
echo ============================================================
echo                    VERIFICANDO INSTALACAO
echo ============================================================
echo.

echo Verificando PyTorch...
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA disponivel: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"Nenhuma\"}')"

echo.
echo Verificando Diffusers...
python -c "import diffusers; print(f'Diffusers: {diffusers.__version__}')"

echo.
echo ============================================================
echo                    INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo Se CUDA disponivel = True, a GPU esta pronta!
echo.
echo Se CUDA disponivel = False:
echo   - Verifique se tem GPU NVIDIA
echo   - Instale drivers NVIDIA atualizados
echo   - Tente: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
echo.
pause
