#!/bin/bash

# =============================================================================
# BAMBI-EXPRESS - Script para Parar Serviços
# =============================================================================

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Parando serviços...${NC}"

# Parar via PID files
if [ -f "$PROJECT_DIR/logs/backend.pid" ]; then
    PID=$(cat "$PROJECT_DIR/logs/backend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo -e "${GREEN}Backend parado (PID: $PID)${NC}"
    fi
    rm -f "$PROJECT_DIR/logs/backend.pid"
fi

if [ -f "$PROJECT_DIR/logs/frontend.pid" ]; then
    PID=$(cat "$PROJECT_DIR/logs/frontend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo -e "${GREEN}Frontend parado (PID: $PID)${NC}"
    fi
    rm -f "$PROJECT_DIR/logs/frontend.pid"
fi

# Matar processos por porta (fallback)
echo -e "${YELLOW}Verificando processos restantes...${NC}"

# Backend na porta 8000
BACKEND_PID=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null || true
    echo -e "${GREEN}Processo na porta 8000 parado${NC}"
fi

# Frontend na porta 3000
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Processo na porta 3000 parado${NC}"
fi

echo -e "${GREEN}Todos os serviços foram parados!${NC}"
