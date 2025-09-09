#!/bin/bash

# ===========================================
# BOTPHIA - PRODUCTION STARTER
# Sistema de Trading con Operación Continua
# ===========================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio base
BASE_DIR="/Users/ja/saby"
API_DIR="$BASE_DIR/trading_api"
FRONTEND_DIR="$BASE_DIR/botphia"
LOG_DIR="$API_DIR/logs"

echo -e "${BLUE}===========================================
BOTPHIA - Production Deployment
===========================================${NC}"

# 1. Verificar directorios
echo -e "${YELLOW}📁 Verificando estructura de directorios...${NC}"
mkdir -p $LOG_DIR
mkdir -p $API_DIR/cache
mkdir -p $API_DIR/data

# 2. Verificar Python y dependencias
echo -e "${YELLOW}🐍 Verificando Python y dependencias...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 no está instalado${NC}"
    exit 1
fi

# Instalar dependencias si es necesario
cd $API_DIR
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Instalando dependencias Python...${NC}"
    pip3 install -q -r requirements.txt
fi

# 3. Verificar Node y dependencias del frontend
echo -e "${YELLOW}🔧 Verificando Node.js y dependencias...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js no está instalado${NC}"
    exit 1
fi

cd $FRONTEND_DIR
if [ -f "package.json" ]; then
    echo -e "${YELLOW}📦 Instalando dependencias Node...${NC}"
    npm install --quiet
fi

# 4. Construir frontend para producción
echo -e "${YELLOW}🏗️ Construyendo frontend para producción...${NC}"
npm run build

# 5. Detener procesos existentes
echo -e "${YELLOW}⏹️ Deteniendo procesos existentes...${NC}"
pkill -f "fastapi_server.py" || true
pkill -f "signal_generator.py" || true
pkill -f "run_system.py" || true
pkill -f "npm run dev" || true
sleep 2

# 6. Iniciar Backend API
echo -e "${GREEN}🚀 Iniciando Backend API...${NC}"
cd $API_DIR
nohup python3 -m uvicorn fastapi_server:app --host 0.0.0.0 --port 8000 \
    > $LOG_DIR/api.log 2>&1 &
API_PID=$!
echo "   ✅ API iniciada (PID: $API_PID)"

# 7. Esperar a que la API esté lista
echo -e "${YELLOW}⏳ Esperando a que la API esté lista...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/api/status > /dev/null; then
        echo -e "${GREEN}   ✅ API respondiendo correctamente${NC}"
        break
    fi
    sleep 1
done

# 8. Iniciar Sistema de Trading Continuo
echo -e "${GREEN}🤖 Iniciando Sistema de Trading Continuo...${NC}"
cd $API_DIR
nohup python3 run_system.py > $LOG_DIR/trading_system.log 2>&1 &
TRADING_PID=$!
echo "   ✅ Sistema de Trading iniciado (PID: $TRADING_PID)"

# 9. Servir Frontend con servidor estático
echo -e "${GREEN}🌐 Sirviendo Frontend...${NC}"
cd $FRONTEND_DIR
if [ -d "dist" ]; then
    # Usar un servidor estático simple para producción
    npx serve -s dist -l 5173 > $LOG_DIR/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "   ✅ Frontend servido en puerto 5173 (PID: $FRONTEND_PID)"
else
    echo -e "${RED}❌ No se encontró el build de producción${NC}"
    echo "   Ejecutando en modo desarrollo..."
    npm run dev > $LOG_DIR/frontend_dev.log 2>&1 &
    FRONTEND_PID=$!
fi

# 10. Guardar PIDs para gestión
echo -e "${YELLOW}💾 Guardando información de procesos...${NC}"
cat > $API_DIR/production.pid << EOF
API_PID=$API_PID
TRADING_PID=$TRADING_PID
FRONTEND_PID=$FRONTEND_PID
STARTED_AT=$(date)
EOF

# 11. Verificación final
sleep 5
echo -e "${BLUE}
===========================================
📊 ESTADO DEL SISTEMA
===========================================${NC}"

# Verificar API
if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✅ API: Activa (PID: $API_PID)${NC}"
else
    echo -e "${RED}❌ API: No activa${NC}"
fi

# Verificar Trading System
if ps -p $TRADING_PID > /dev/null; then
    echo -e "${GREEN}✅ Trading System: Activo (PID: $TRADING_PID)${NC}"
else
    echo -e "${RED}❌ Trading System: No activo${NC}"
fi

# Verificar Frontend
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Frontend: Activo (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}❌ Frontend: No activo${NC}"
fi

echo -e "${BLUE}
===========================================
🔗 ACCESOS
===========================================${NC}"
echo -e "Frontend: ${GREEN}http://localhost:5173${NC}"
echo -e "API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "Logs: ${GREEN}$LOG_DIR${NC}"

echo -e "${BLUE}
===========================================
📝 COMANDOS ÚTILES
===========================================${NC}"
echo "Ver logs en tiempo real:"
echo "  tail -f $LOG_DIR/trading_system.log"
echo ""
echo "Detener sistema:"
echo "  $API_DIR/stop_production.sh"
echo ""
echo "Ver estado:"
echo "  $API_DIR/check_status.sh"

echo -e "${GREEN}
✅ Sistema iniciado correctamente
${NC}"