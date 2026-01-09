#!/bin/bash

# =============================================================================
# BAMBI-EXPRESS - Script de Inicialização
# =============================================================================
# Execute com: ./start.sh
# Opções:
#   ./start.sh          - Inicia backend e frontend
#   ./start.sh backend  - Inicia apenas o backend
#   ./start.sh frontend - Inicia apenas o frontend
# =============================================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Diretório base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}"
echo "=============================================="
echo "   BAMBI-EXPRESS - Iniciando Serviços"
echo "=============================================="
echo -e "${NC}"

# Função para iniciar o backend
start_backend() {
    echo -e "${GREEN}Iniciando Backend...${NC}"
    cd "$PROJECT_DIR/backend"

    if [ ! -d "venv" ]; then
        echo -e "${RED}Ambiente virtual não encontrado! Execute install.sh primeiro.${NC}"
        exit 1
    fi

    source venv/bin/activate

    # Verificar se uvicorn está instalado
    if ! command -v uvicorn &> /dev/null; then
        echo -e "${YELLOW}Instalando uvicorn...${NC}"
        pip install uvicorn
    fi

    echo -e "${YELLOW}Backend rodando em http://localhost:8000${NC}"
    echo -e "${YELLOW}API Docs em http://localhost:8000/docs${NC}"
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
}

# Função para iniciar o frontend
start_frontend() {
    echo -e "${GREEN}Iniciando Frontend...${NC}"
    cd "$PROJECT_DIR/frontend"

    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Instalando dependências do frontend...${NC}"
        npm install
    fi

    echo -e "${YELLOW}Frontend rodando em http://localhost:3000${NC}"
    npm run dev
}

# Função para iniciar ambos em paralelo
start_both() {
    echo -e "${GREEN}Iniciando Backend e Frontend em paralelo...${NC}"
    echo ""

    # Criar arquivos de log
    mkdir -p "$PROJECT_DIR/logs"

    # Iniciar backend em background
    cd "$PROJECT_DIR/backend"
    source venv/bin/activate
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_DIR/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo -e "${YELLOW}Backend iniciado (PID: $BACKEND_PID)${NC}"

    # Aguardar backend inicializar
    sleep 3

    # Iniciar frontend em background
    cd "$PROJECT_DIR/frontend"
    npm run dev > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo -e "${YELLOW}Frontend iniciado (PID: $FRONTEND_PID)${NC}"

    echo ""
    echo -e "${GREEN}=============================================="
    echo "   Serviços Iniciados!"
    echo "==============================================${NC}"
    echo ""
    echo -e "${YELLOW}URLs:${NC}"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}Logs:${NC}"
    echo "   Backend:  $PROJECT_DIR/logs/backend.log"
    echo "   Frontend: $PROJECT_DIR/logs/frontend.log"
    echo ""
    echo -e "${YELLOW}Para parar os serviços:${NC}"
    echo "   ./scripts/stop.sh"
    echo ""
    echo -e "${YELLOW}Ou pressione Ctrl+C para parar${NC}"

    # Salvar PIDs para o script de stop
    echo "$BACKEND_PID" > "$PROJECT_DIR/logs/backend.pid"
    echo "$FRONTEND_PID" > "$PROJECT_DIR/logs/frontend.pid"

    # Aguardar e mostrar logs combinados
    tail -f "$PROJECT_DIR/logs/backend.log" "$PROJECT_DIR/logs/frontend.log"
}

# Processar argumentos
case "${1:-both}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    both|*)
        start_both
        ;;
esac
