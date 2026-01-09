#!/bin/bash

# =============================================================================
# BAMBI-EXPRESS - Setup Rápido (Um Comando)
# =============================================================================
# Use: curl -sSL https://raw.githubusercontent.com/SEU_USUARIO/Bambi-Express/main/scripts/quick-setup.sh | bash
# Ou baixe e execute: chmod +x quick-setup.sh && ./quick-setup.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "=============================================="
echo "   BAMBI-EXPRESS - Setup Rápido"
echo "=============================================="
echo -e "${NC}"

# Diretório de instalação
INSTALL_DIR="${HOME}/Bambi-Express"

# Verificar se já existe
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Diretório $INSTALL_DIR já existe.${NC}"
    read -p "Deseja atualizar? (s/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        cd "$INSTALL_DIR"
        git pull origin main
    fi
else
    # Clonar repositório
    echo -e "${GREEN}Clonando repositório...${NC}"
    git clone https://github.com/sterling9879/Bambi-Express.git "$INSTALL_DIR"
fi

# Executar instalação
cd "$INSTALL_DIR"
chmod +x scripts/*.sh
./scripts/install.sh

echo -e "${GREEN}Setup concluído!${NC}"
