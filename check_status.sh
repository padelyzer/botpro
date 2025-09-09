#!/bin/bash

# ===========================================
# BOTPHIA - SYSTEM MONITOR
# Monitoreo y supervisión del sistema
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

API_DIR="/Users/ja/saby/trading_api"
LOG_DIR="$API_DIR/logs"
PID_FILE="$API_DIR/production.pid"

clear

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              BOTPHIA - MONITOR DE SISTEMA                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Estado de Procesos
echo -e "${CYAN}🔍 ESTADO DE PROCESOS${NC}"
echo -e "${CYAN}─────────────────────────────────────${NC}"

# Verificar API
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/status)
if [ "$API_STATUS" == "200" ]; then
    echo -e "API Backend:        ${GREEN}✅ ACTIVO${NC} (Puerto 8000)"
    
    # Obtener estadísticas de la API
    API_DATA=$(curl -s http://localhost:8000/api/status)
    if [ ! -z "$API_DATA" ]; then
        UPTIME=$(echo $API_DATA | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('uptime', 'N/A'))" 2>/dev/null || echo "N/A")
        echo -e "  └─ Uptime: ${YELLOW}$UPTIME${NC}"
    fi
else
    echo -e "API Backend:        ${RED}❌ INACTIVO${NC}"
fi

# Verificar Trading System
TRADING_PID=$(ps aux | grep -E "run_system.py" | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$TRADING_PID" ]; then
    echo -e "Trading System:     ${GREEN}✅ ACTIVO${NC} (PID: $TRADING_PID)"
    
    # Verificar componentes del trading system
    SIGNAL_GEN=$(ps aux | grep -E "signal_generator.py" | grep -v grep | wc -l)
    if [ $SIGNAL_GEN -gt 0 ]; then
        echo -e "  ├─ Signal Generator: ${GREEN}✓${NC}"
    else
        echo -e "  ├─ Signal Generator: ${YELLOW}○${NC}"
    fi
else
    echo -e "Trading System:     ${RED}❌ INACTIVO${NC}"
fi

# Verificar Frontend
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
if [ "$FRONTEND_STATUS" == "200" ] || [ "$FRONTEND_STATUS" == "304" ]; then
    echo -e "Frontend:           ${GREEN}✅ ACTIVO${NC} (Puerto 5173)"
else
    echo -e "Frontend:           ${RED}❌ INACTIVO${NC}"
fi

echo ""

# 2. Estadísticas del Sistema
echo -e "${CYAN}📊 ESTADÍSTICAS DEL SISTEMA${NC}"
echo -e "${CYAN}─────────────────────────────────────${NC}"

# Obtener datos de trading si la API está activa
if [ "$API_STATUS" == "200" ]; then
    # Señales recientes
    SIGNALS=$(curl -s http://localhost:8000/api/signals/BTCUSDT 2>/dev/null)
    if [ ! -z "$SIGNALS" ]; then
        TOTAL_SIGNALS=$(echo $SIGNALS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_signals', 0))" 2>/dev/null || echo "0")
        HIGH_QUALITY=$(echo $SIGNALS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('high_quality_signals', 0))" 2>/dev/null || echo "0")
        CONSENSUS=$(echo $SIGNALS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('consensus', {}).get('action', 'N/A'))" 2>/dev/null || echo "N/A")
        
        echo -e "Señales Totales:    ${YELLOW}$TOTAL_SIGNALS${NC}"
        echo -e "Alta Calidad:       ${GREEN}$HIGH_QUALITY${NC}"
        echo -e "Consenso Actual:    ${BLUE}$CONSENSUS${NC}"
    fi
fi

echo ""

# 3. Uso de Recursos
echo -e "${CYAN}💻 USO DE RECURSOS${NC}"
echo -e "${CYAN}─────────────────────────────────────${NC}"

# CPU y Memoria
if [ ! -z "$TRADING_PID" ]; then
    CPU_USAGE=$(ps aux | grep $TRADING_PID | grep -v grep | awk '{print $3}' | head -1)
    MEM_USAGE=$(ps aux | grep $TRADING_PID | grep -v grep | awk '{print $4}' | head -1)
    echo -e "Trading System:"
    echo -e "  ├─ CPU:  ${YELLOW}${CPU_USAGE}%${NC}"
    echo -e "  └─ RAM:  ${YELLOW}${MEM_USAGE}%${NC}"
fi

# Espacio en disco
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
DISK_FREE=$(df -h / | tail -1 | awk '{print $4}')
echo -e "Disco:"
echo -e "  ├─ Usado: ${YELLOW}$DISK_USAGE${NC}"
echo -e "  └─ Libre: ${GREEN}$DISK_FREE${NC}"

echo ""

# 4. Logs Recientes
echo -e "${CYAN}📝 ÚLTIMAS LÍNEAS DE LOG${NC}"
echo -e "${CYAN}─────────────────────────────────────${NC}"

if [ -f "$LOG_DIR/trading_system.log" ]; then
    echo -e "${YELLOW}Trading System:${NC}"
    tail -3 "$LOG_DIR/trading_system.log" | sed 's/^/  /'
fi

if [ -f "$LOG_DIR/api.log" ]; then
    echo -e "${YELLOW}API:${NC}"
    tail -3 "$LOG_DIR/api.log" | sed 's/^/  /'
fi

echo ""

# 5. Alertas y Avisos
echo -e "${CYAN}⚠️  ALERTAS Y AVISOS${NC}"
echo -e "${CYAN}─────────────────────────────────────${NC}"

# Verificar si hay archivos de error grandes
if [ -f "$LOG_DIR/error.log" ]; then
    ERROR_SIZE=$(du -h "$LOG_DIR/error.log" | cut -f1)
    ERROR_COUNT=$(grep -c "ERROR" "$LOG_DIR/error.log" 2>/dev/null || echo "0")
    if [ $ERROR_COUNT -gt 0 ]; then
        echo -e "${RED}⚠️  $ERROR_COUNT errores en logs (Tamaño: $ERROR_SIZE)${NC}"
    else
        echo -e "${GREEN}✅ Sin errores recientes${NC}"
    fi
else
    echo -e "${GREEN}✅ Sin archivo de errores${NC}"
fi

# Verificar conectividad con Binance
BINANCE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.binance.com/api/v3/ping)
if [ "$BINANCE_STATUS" == "200" ]; then
    echo -e "${GREEN}✅ Conexión con Binance API activa${NC}"
else
    echo -e "${RED}❌ Problema de conexión con Binance${NC}"
fi

echo ""
echo -e "${CYAN}─────────────────────────────────────${NC}"
echo -e "${BLUE}Última actualización: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# 6. Comandos Rápidos
echo -e "${CYAN}📌 COMANDOS RÁPIDOS:${NC}"
echo -e "  Ver logs en tiempo real:  ${YELLOW}tail -f $LOG_DIR/trading_system.log${NC}"
echo -e "  Reiniciar sistema:        ${YELLOW}$API_DIR/restart_production.sh${NC}"
echo -e "  Detener sistema:          ${YELLOW}$API_DIR/stop_production.sh${NC}"
echo ""