#!/bin/bash

# =============================================================================
# BAMBI-EXPRESS - Script de Atualização
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}"
echo "=============================================="
echo "   BAMBI-EXPRESS - Atualização"
echo "=============================================="
echo -e "${NC}"

cd "$PROJECT_DIR"

# Parar serviços se estiverem rodando
if [ -f "scripts/stop.sh" ]; then
    ./scripts/stop.sh 2>/dev/null || true
fi

# Atualizar código
echo -e "${GREEN}[1/4] Atualizando código...${NC}"
git pull origin main

# Atualizar dependências do backend
echo -e "${GREEN}[2/4] Atualizando dependências do backend...${NC}"
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate

# Atualizar dependências do frontend
echo -e "${GREEN}[3/4] Atualizando dependências do frontend...${NC}"
cd ../frontend
npm install

# Rebuildar frontend (se necessário)
echo -e "${GREEN}[4/4] Verificando build do frontend...${NC}"
npm run build 2>/dev/null || echo -e "${YELLOW}Build não necessário para dev mode${NC}"

cd "$PROJECT_DIR"

echo ""
echo -e "${GREEN}=============================================="
echo "   Atualização Concluída!"
echo "==============================================${NC}"
echo ""
echo -e "${YELLOW}Para iniciar os serviços:${NC}"
echo "   ./scripts/start.sh"
echo ""
