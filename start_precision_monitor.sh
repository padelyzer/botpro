#!/bin/bash

# BotphIA Precision Monitor - Script de inicio
# Monitor de alta precisión para señales confiables

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio de trabajo
WORK_DIR="/Users/ja/saby/trading_api"
LOG_DIR="$WORK_DIR/logs"
PID_FILE="$WORK_DIR/.precision_monitor.pid"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# Función para verificar si el monitor está corriendo
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Función para iniciar el monitor
start_monitor() {
    if is_running; then
        echo -e "${YELLOW}⚠️  El monitor ya está en ejecución (PID: $(cat $PID_FILE))${NC}"
        return 1
    fi
    
    echo -e "${BLUE}🚀 Iniciando BotphIA Precision Monitor...${NC}"
    
    cd "$WORK_DIR"
    
    # Iniciar en background con nohup
    nohup python3 precision_signal_monitor.py > "$LOG_DIR/monitor_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
    
    # Guardar PID
    echo $! > "$PID_FILE"
    
    sleep 2
    
    if is_running; then
        echo -e "${GREEN}✅ Monitor iniciado exitosamente (PID: $(cat $PID_FILE))${NC}"
        echo -e "${GREEN}📁 Logs en: $LOG_DIR${NC}"
        echo -e "${GREEN}📊 Para ver el estado: tail -f $LOG_DIR/monitor_*.log${NC}"
    else
        echo -e "${RED}❌ Error al iniciar el monitor${NC}"
        return 1
    fi
}

# Función para detener el monitor
stop_monitor() {
    if ! is_running; then
        echo -e "${YELLOW}⚠️  El monitor no está en ejecución${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo -e "${YELLOW}⏹️  Deteniendo monitor (PID: $PID)...${NC}"
    
    kill "$PID"
    sleep 2
    
    if ! is_running; then
        echo -e "${GREEN}✅ Monitor detenido exitosamente${NC}"
        rm -f "$PID_FILE"
    else
        echo -e "${RED}❌ No se pudo detener el monitor, intentando kill -9${NC}"
        kill -9 "$PID"
        rm -f "$PID_FILE"
    fi
}

# Función para ver el estado
status_monitor() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Monitor en ejecución (PID: $PID)${NC}"
        
        # Mostrar información del proceso
        ps -p "$PID" -o pid,vsz,rss,comm,etime
        
        # Mostrar últimas líneas del log
        echo -e "\n${BLUE}📊 Últimas señales detectadas:${NC}"
        tail -n 20 "$LOG_DIR"/monitor_*.log 2>/dev/null | grep -E "(SEÑAL CONFIRMADA|Señal de alta calidad)" | tail -5
        
    else
        echo -e "${RED}❌ Monitor no está en ejecución${NC}"
    fi
}

# Función para reiniciar
restart_monitor() {
    echo -e "${YELLOW}🔄 Reiniciando monitor...${NC}"
    stop_monitor
    sleep 2
    start_monitor
}

# Función para ver logs en tiempo real
watch_logs() {
    if is_running; then
        echo -e "${BLUE}📊 Mostrando logs en tiempo real (Ctrl+C para salir)...${NC}"
        tail -f "$LOG_DIR"/monitor_*.log | grep --line-buffered -E "(SEÑAL|ERROR|WARNING|✅|🎯)"
    else
        echo -e "${RED}❌ El monitor no está en ejecución${NC}"
    fi
}

# Menú principal
case "$1" in
    start)
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    restart)
        restart_monitor
        ;;
    status)
        status_monitor
        ;;
    logs)
        watch_logs
        ;;
    *)
        echo -e "${BLUE}🤖 BotphIA Precision Monitor - Control Script${NC}"
        echo -e "Uso: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Comandos:"
        echo "  start   - Inicia el monitor en background"
        echo "  stop    - Detiene el monitor"
        echo "  restart - Reinicia el monitor"
        echo "  status  - Muestra el estado actual"
        echo "  logs    - Muestra logs en tiempo real"
        echo ""
        
        # Mostrar estado actual
        echo -e "Estado actual:"
        status_monitor
        ;;
esac