#!/bin/bash

# ===========================================
# BOTPHIA - PRODUCTION STOPPER
# Detiene el sistema de forma ordenada
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_DIR="/Users/ja/saby/trading_api"
PID_FILE="$API_DIR/production.pid"

echo -e "${YELLOW}⏹️ Deteniendo BotphIA...${NC}"

# Leer PIDs guardados
if [ -f "$PID_FILE" ]; then
    source $PID_FILE
    
    # Detener Trading System
    if [ ! -z "$TRADING_PID" ] && ps -p $TRADING_PID > /dev/null; then
        echo -e "${YELLOW}Deteniendo Trading System (PID: $TRADING_PID)...${NC}"
        kill -TERM $TRADING_PID
        sleep 2
        if ps -p $TRADING_PID > /dev/null; then
            kill -KILL $TRADING_PID
        fi
        echo -e "${GREEN}✅ Trading System detenido${NC}"
    fi
    
    # Detener API
    if [ ! -z "$API_PID" ] && ps -p $API_PID > /dev/null; then
        echo -e "${YELLOW}Deteniendo API (PID: $API_PID)...${NC}"
        kill -TERM $API_PID
        sleep 2
        if ps -p $API_PID > /dev/null; then
            kill -KILL $API_PID
        fi
        echo -e "${GREEN}✅ API detenida${NC}"
    fi
    
    # Detener Frontend
    if [ ! -z "$FRONTEND_PID" ] && ps -p $FRONTEND_PID > /dev/null; then
        echo -e "${YELLOW}Deteniendo Frontend (PID: $FRONTEND_PID)...${NC}"
        kill -TERM $FRONTEND_PID
        sleep 1
        if ps -p $FRONTEND_PID > /dev/null; then
            kill -KILL $FRONTEND_PID
        fi
        echo -e "${GREEN}✅ Frontend detenido${NC}"
    fi
    
    # Eliminar archivo de PIDs
    rm -f $PID_FILE
else
    echo -e "${YELLOW}No se encontró archivo de PIDs. Buscando procesos...${NC}"
    
    # Buscar y detener procesos por nombre
    pkill -f "fastapi_server" || true
    pkill -f "run_system.py" || true
    pkill -f "signal_generator.py" || true
    pkill -f "serve -s dist" || true
fi

# Verificación adicional
echo -e "${YELLOW}Verificando procesos restantes...${NC}"
REMAINING=$(ps aux | grep -E "(fastapi_server|run_system|signal_generator)" | grep -v grep | wc -l)

if [ $REMAINING -eq 0 ]; then
    echo -e "${GREEN}✅ Sistema detenido completamente${NC}"
else
    echo -e "${RED}⚠️ Aún hay $REMAINING procesos activos${NC}"
    ps aux | grep -E "(fastapi_server|run_system|signal_generator)" | grep -v grep
fi