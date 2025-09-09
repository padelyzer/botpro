#!/bin/bash

# ===================================================
# BOTPHIA PAPER TRADING MANAGER
# Script de gestión del bot de paper trading
# ===================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Archivo PID
PID_FILE="paper_trading_bot.pid"
LOG_FILE="paper_trading_bot.log"

# Función para mostrar el menú
show_menu() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     🤖 BOTPHIA PAPER TRADING MANAGER 🤖     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}1.${NC} 🚀 Iniciar Bot"
    echo -e "${YELLOW}2.${NC} 🛑 Detener Bot"
    echo -e "${BLUE}3.${NC} 📊 Ver Estado"
    echo -e "${GREEN}4.${NC} 📈 Ver Estadísticas"
    echo -e "${YELLOW}5.${NC} 📜 Ver Logs"
    echo -e "${BLUE}6.${NC} 🔄 Reiniciar Bot"
    echo -e "${RED}7.${NC} 🗑️  Limpiar Base de Datos"
    echo -e "${NC}8. ❌ Salir"
    echo ""
}

# Función para iniciar el bot
start_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  El bot ya está en ejecución (PID: $PID)${NC}"
            return
        fi
    fi
    
    echo -e "${GREEN}🚀 Iniciando Bot de Paper Trading...${NC}"
    nohup python3 start_paper_trading_demo.py > $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    sleep 2
    
    if ps -p $(cat $PID_FILE) > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Bot iniciado correctamente (PID: $(cat $PID_FILE))${NC}"
    else
        echo -e "${RED}❌ Error al iniciar el bot${NC}"
        rm -f $PID_FILE
    fi
}

# Función para detener el bot
stop_bot() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}⚠️  No se encontró proceso del bot${NC}"
        return
    fi
    
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}🛑 Deteniendo bot (PID: $PID)...${NC}"
        kill -TERM $PID
        sleep 2
        
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${RED}⚠️  Forzando detención...${NC}"
            kill -9 $PID
        fi
        
        rm -f $PID_FILE
        echo -e "${GREEN}✅ Bot detenido${NC}"
    else
        echo -e "${YELLOW}⚠️  El bot no está en ejecución${NC}"
        rm -f $PID_FILE
    fi
}

# Función para ver el estado
check_status() {
    echo -e "${BLUE}📊 ESTADO DEL BOT${NC}"
    echo "══════════════════════════════"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "Estado: ${GREEN}● ACTIVO${NC}"
            echo -e "PID: $PID"
            echo -e "Tiempo activo: $(ps -o etime= -p $PID | xargs)"
            echo -e "Uso CPU: $(ps -o %cpu= -p $PID | xargs)%"
            echo -e "Uso RAM: $(ps -o rss= -p $PID | xargs | awk '{printf "%.2f MB", $1/1024}')"
        else
            echo -e "Estado: ${RED}● DETENIDO${NC}"
        fi
    else
        echo -e "Estado: ${RED}● NO INICIADO${NC}"
    fi
    
    # Verificar base de datos
    if [ -f "paper_trading_demo.db" ]; then
        echo ""
        echo -e "${BLUE}📁 Base de Datos${NC}"
        echo "══════════════════════════════"
        SIZE=$(du -h paper_trading_demo.db | cut -f1)
        echo -e "Tamaño: $SIZE"
        
        # Contar trades
        TRADES=$(sqlite3 paper_trading_demo.db "SELECT COUNT(*) FROM trades;" 2>/dev/null || echo "0")
        echo -e "Total trades: $TRADES"
    fi
}

# Función para ver estadísticas
show_stats() {
    if [ ! -f "paper_trading_demo.db" ]; then
        echo -e "${RED}❌ No hay datos disponibles${NC}"
        return
    fi
    
    echo -e "${BLUE}📈 ESTADÍSTICAS DE TRADING${NC}"
    echo "══════════════════════════════"
    
    # Obtener estadísticas de la base de datos
    sqlite3 paper_trading_demo.db <<EOF
.mode column
.headers on
SELECT 
    printf('%.2f', balance) as 'Balance USD',
    total_trades as 'Total Trades',
    winning_trades as 'Winning',
    printf('%.2f', total_pnl) as 'PnL Total',
    last_update as 'Última Actualización'
FROM bot_state WHERE id = 1;
EOF
    
    echo ""
    echo -e "${BLUE}📊 ÚLTIMOS 5 TRADES${NC}"
    echo "══════════════════════════════"
    
    sqlite3 paper_trading_demo.db <<EOF
.mode column
.headers on
SELECT 
    substr(timestamp, 12, 8) as 'Hora',
    symbol as 'Símbolo',
    action as 'Acción',
    printf('%.4f', price) as 'Precio',
    printf('%.2f', pnl) as 'PnL'
FROM trades 
ORDER BY timestamp DESC 
LIMIT 5;
EOF
}

# Función para ver logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}📜 ÚLTIMAS 30 LÍNEAS DEL LOG${NC}"
        echo "══════════════════════════════"
        tail -n 30 $LOG_FILE
    else
        echo -e "${RED}❌ No hay logs disponibles${NC}"
    fi
}

# Función para reiniciar el bot
restart_bot() {
    echo -e "${YELLOW}🔄 Reiniciando bot...${NC}"
    stop_bot
    sleep 2
    start_bot
}

# Función para limpiar base de datos
clean_database() {
    echo -e "${RED}⚠️  ADVERTENCIA: Esto borrará todos los datos de trading${NC}"
    read -p "¿Estás seguro? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        stop_bot
        rm -f paper_trading_demo.db
        echo -e "${GREEN}✅ Base de datos eliminada${NC}"
    else
        echo -e "${YELLOW}Operación cancelada${NC}"
    fi
}

# Bucle principal
while true; do
    show_menu
    read -p "Selecciona una opción: " choice
    
    case $choice in
        1) start_bot ;;
        2) stop_bot ;;
        3) check_status ;;
        4) show_stats ;;
        5) show_logs ;;
        6) restart_bot ;;
        7) clean_database ;;
        8) 
            echo -e "${GREEN}👋 Hasta luego!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Opción inválida${NC}"
            ;;
    esac
    
    echo ""
    read -p "Presiona ENTER para continuar..."
done