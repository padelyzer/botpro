#!/bin/bash

# 🌐 BotphIA Web Dashboard - Script de inicio
# Este script inicia el dashboard web accesible públicamente

echo "🚀 Iniciando BotphIA Web Dashboard..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo "🤖 BotphIA Web Dashboard - Comandos disponibles:"
    echo ""
    echo "  ./start_web_dashboard.sh start    - Iniciar dashboard web"
    echo "  ./start_web_dashboard.sh docker   - Iniciar con Docker"
    echo "  ./start_web_dashboard.sh stop     - Detener dashboard"
    echo "  ./start_web_dashboard.sh status   - Ver estado"
    echo "  ./start_web_dashboard.sh logs     - Ver logs"
    echo ""
}

# Función para verificar dependencias
check_dependencies() {
    echo -e "${BLUE}🔍 Verificando dependencias...${NC}"
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 no encontrado${NC}"
        exit 1
    fi
    
    # Verificar pip
    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}❌ pip3 no encontrado${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dependencias verificadas${NC}"
}

# Función para instalar requirements
install_requirements() {
    echo -e "${BLUE}📦 Instalando dependencias...${NC}"
    
    if [ -f "requirements_web.txt" ]; then
        pip3 install -r requirements_web.txt
        echo -e "${GREEN}✅ Dependencias instaladas${NC}"
    else
        echo -e "${YELLOW}⚠️ requirements_web.txt no encontrado${NC}"
    fi
}

# Función para iniciar el dashboard
start_dashboard() {
    echo -e "${BLUE}🌐 Iniciando BotphIA Web Dashboard...${NC}"
    
    # Verificar que el archivo existe
    if [ ! -f "web_api.py" ]; then
        echo -e "${RED}❌ web_api.py no encontrado${NC}"
        exit 1
    fi
    
    # Crear directorio static si no existe
    mkdir -p static
    
    # Verificar que dashboard.html existe
    if [ ! -f "static/dashboard.html" ]; then
        echo -e "${RED}❌ static/dashboard.html no encontrado${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}🚀 Iniciando servidor...${NC}"
    echo -e "${YELLOW}📊 Dashboard disponible en: http://localhost:8888/dashboard${NC}"
    echo -e "${YELLOW}🔧 API docs en: http://localhost:8888/docs${NC}"
    echo -e "${YELLOW}📡 WebSocket en: ws://localhost:8888/ws${NC}"
    echo ""
    echo -e "${BLUE}Presiona Ctrl+C para detener${NC}"
    echo ""
    
    # Iniciar el servidor
    python3 web_api.py
}

# Función para iniciar con Docker
start_docker() {
    echo -e "${BLUE}🐳 Iniciando con Docker...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker no encontrado${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose no encontrado${NC}"
        exit 1
    fi
    
    # Build y start con docker-compose
    docker-compose -f docker-compose.web.yml up --build
}

# Función para detener
stop_dashboard() {
    echo -e "${BLUE}🛑 Deteniendo dashboard...${NC}"
    
    # Buscar proceso Python ejecutando web_api.py
    PID=$(pgrep -f "python.*web_api.py")
    
    if [ ! -z "$PID" ]; then
        kill $PID
        echo -e "${GREEN}✅ Dashboard detenido${NC}"
    else
        echo -e "${YELLOW}⚠️ No se encontró proceso activo${NC}"
    fi
    
    # Detener Docker si está corriendo
    if [ -f "docker-compose.web.yml" ]; then
        docker-compose -f docker-compose.web.yml down
    fi
}

# Función para ver estado
show_status() {
    echo -e "${BLUE}📊 Estado del sistema:${NC}"
    
    # Verificar proceso Python
    PID=$(pgrep -f "python.*web_api.py")
    if [ ! -z "$PID" ]; then
        echo -e "${GREEN}✅ Dashboard activo (PID: $PID)${NC}"
        echo -e "${YELLOW}🌐 URL: http://localhost:8888/dashboard${NC}"
    else
        echo -e "${RED}❌ Dashboard no activo${NC}"
    fi
    
    # Verificar Docker
    if docker-compose -f docker-compose.web.yml ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Docker container activo${NC}"
    fi
    
    # Verificar puerto
    if netstat -tuln 2>/dev/null | grep -q ":8888"; then
        echo -e "${GREEN}✅ Puerto 8888 en uso${NC}"
    else
        echo -e "${RED}❌ Puerto 8888 libre${NC}"
    fi
}

# Función para ver logs
show_logs() {
    echo -e "${BLUE}📋 Logs del dashboard:${NC}"
    
    # Logs de Docker si está activo
    if docker-compose -f docker-compose.web.yml ps | grep -q "Up"; then
        docker-compose -f docker-compose.web.yml logs -f
    else
        echo -e "${YELLOW}⚠️ No hay contenedor Docker activo${NC}"
        echo -e "${BLUE}Para ver logs en tiempo real, ejecuta el dashboard con:${NC}"
        echo -e "${YELLOW}./start_web_dashboard.sh start${NC}"
    fi
}

# Main script
case "$1" in
    "start")
        check_dependencies
        install_requirements
        start_dashboard
        ;;
    "docker")
        start_docker
        ;;
    "stop")
        stop_dashboard
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Comando no reconocido: $1${NC}"
        show_help
        exit 1
        ;;
esac