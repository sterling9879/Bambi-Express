#!/bin/bash

# =============================================================================
# BAMBI-EXPRESS - Script de Instalação Completa para Ubuntu/WSL
# =============================================================================
# Execute com: chmod +x install.sh && ./install.sh
# =============================================================================

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=============================================="
echo "   BAMBI-EXPRESS - Instalação Automática"
echo "=============================================="
echo -e "${NC}"

# Verificar se está rodando como root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Por favor, NÃO execute como root (sem sudo)${NC}"
    exit 1
fi

# Diretório base do projeto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Diretório do projeto: $PROJECT_DIR${NC}"
echo ""

# =============================================================================
# 1. Atualizar sistema e instalar dependências base
# =============================================================================
echo -e "${GREEN}[1/7] Atualizando sistema e instalando dependências base...${NC}"

sudo apt-get update
sudo apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# =============================================================================
# 2. Instalar Python 3.11+
# =============================================================================
echo -e "${GREEN}[2/7] Instalando Python 3.11...${NC}"

# Adicionar repositório deadsnakes para Python mais recente
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update

sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip

# Criar aliases
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 || true

echo -e "${YELLOW}Python instalado: $(python3.11 --version)${NC}"

# =============================================================================
# 3. Instalar Node.js 20 LTS
# =============================================================================
echo -e "${GREEN}[3/7] Instalando Node.js 20 LTS...${NC}"

# Instalar via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo -e "${YELLOW}Node.js instalado: $(node --version)${NC}"
echo -e "${YELLOW}NPM instalado: $(npm --version)${NC}"

# =============================================================================
# 4. Instalar FFMPEG
# =============================================================================
echo -e "${GREEN}[4/7] Instalando FFMPEG...${NC}"

sudo apt-get install -y ffmpeg

echo -e "${YELLOW}FFMPEG instalado: $(ffmpeg -version | head -1)${NC}"

# =============================================================================
# 5. Configurar Backend Python
# =============================================================================
echo -e "${GREEN}[5/7] Configurando Backend Python...${NC}"

cd "$PROJECT_DIR/backend"

# Criar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt

deactivate
echo -e "${YELLOW}Backend configurado!${NC}"

# =============================================================================
# 6. Configurar Frontend Node.js
# =============================================================================
echo -e "${GREEN}[6/7] Configurando Frontend Node.js...${NC}"

cd "$PROJECT_DIR/frontend"

# Instalar dependências
npm install

echo -e "${YELLOW}Frontend configurado!${NC}"

# =============================================================================
# 7. Criar diretórios e arquivos de configuração
# =============================================================================
echo -e "${GREEN}[7/7] Criando estrutura de diretórios...${NC}"

cd "$PROJECT_DIR"

# Criar diretórios necessários
mkdir -p storage/music/alegre
mkdir -p storage/music/animado
mkdir -p storage/music/calmo
mkdir -p storage/music/dramatico
mkdir -p storage/music/inspirador
mkdir -p storage/music/melancolico
mkdir -p storage/music/neutro
mkdir -p storage/music/epico
mkdir -p storage/music/suspense
mkdir -p storage/temp
mkdir -p storage/outputs
mkdir -p storage/cache

# Criar arquivo de configuração padrão se não existir
if [ ! -f "storage/config.json" ]; then
    cat > storage/config.json << 'EOF'
{
    "api": {
        "elevenlabs": {
            "api_key": "",
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "model_id": "eleven_multilingual_v2"
        },
        "assemblyai": {
            "api_key": "",
            "language_code": "pt"
        },
        "gemini": {
            "api_key": "",
            "model": "gemini-2.0-flash"
        },
        "wavespeed": {
            "api_key": "",
            "model": "flux-dev",
            "resolution": "1280x720",
            "image_style": "cinematic, 8k, photorealistic"
        }
    },
    "music": {
        "mode": "library",
        "volume": 0.3,
        "ducking_enabled": true,
        "ducking_intensity": 0.7,
        "fade_in_ms": 2000,
        "fade_out_ms": 3000,
        "crossfade_ms": 1000,
        "auto_select_by_mood": true
    },
    "ffmpeg": {
        "resolution": {
            "width": 1280,
            "height": 720,
            "preset": "720p"
        },
        "fps": 30,
        "crf": 23,
        "preset": "medium",
        "scene_duration": {
            "mode": "auto",
            "min_duration": 3.0,
            "max_duration": 6.0
        },
        "transition": {
            "type": "fade",
            "duration": 0.3,
            "vary": false
        },
        "effects": {
            "ken_burns": {
                "enabled": true,
                "intensity": 0.05,
                "direction": "alternate"
            },
            "vignette": {
                "enabled": true,
                "intensity": 0.3
            },
            "grain": {
                "enabled": false,
                "intensity": 0.1
            }
        },
        "audio": {
            "codec": "aac",
            "bitrate": 192,
            "narration_volume": 1.0,
            "normalize": true,
            "target_lufs": -16
        }
    },
    "gpu": {
        "enabled": false,
        "provider": "wavespeed",
        "vram_mode": "auto",
        "auto_fallback_to_api": true
    }
}
EOF
    echo -e "${YELLOW}Arquivo de configuração criado em storage/config.json${NC}"
fi

# Criar arquivo .env para o frontend se não existir
if [ ! -f "frontend/.env.local" ]; then
    cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo -e "${YELLOW}Arquivo .env.local criado para o frontend${NC}"
fi

# =============================================================================
# Finalização
# =============================================================================
echo ""
echo -e "${GREEN}=============================================="
echo "   INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "==============================================${NC}"
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo ""
echo "1. Inicie os serviços:"
echo "   ${BLUE}cd $PROJECT_DIR && ./scripts/start.sh${NC}"
echo ""
echo "2. Acesse o frontend e configure suas API keys:"
echo "   ${BLUE}http://localhost:3000${NC}"
echo "   Vá na aba 'Configurações' para adicionar suas keys"
echo ""
echo "3. Ou inicie manualmente:"
echo "   Backend:  ${BLUE}cd backend && source venv/bin/activate && uvicorn src.main:app --reload${NC}"
echo "   Frontend: ${BLUE}cd frontend && npm run dev${NC}"
echo ""
echo -e "${YELLOW}URLs após iniciar:${NC}"
echo "   Frontend:      http://localhost:3000"
echo "   Backend API:   http://localhost:8000"
echo "   Documentação:  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}APIs necessárias:${NC}"
echo "   - ElevenLabs (narração): https://elevenlabs.io"
echo "   - AssemblyAI (transcrição): https://assemblyai.com"
echo "   - Google Gemini (análise): https://ai.google.dev"
echo "   - WaveSpeed (imagens): https://wavespeed.ai"
echo ""
