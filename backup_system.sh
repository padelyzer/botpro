#!/bin/bash

# ===========================================
# BOTPHIA - BACKUP AUTOMÁTICO
# Sistema de respaldo de datos críticos
# ===========================================

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuración
BASE_DIR="/Users/ja/saby"
API_DIR="$BASE_DIR/trading_api"
BACKUP_DIR="$BASE_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="botphia_backup_$DATE"

# Crear directorio de backup si no existe
mkdir -p $BACKUP_DIR

echo -e "${BLUE}===========================================
BOTPHIA - Sistema de Backup
=========================================="

echo -e "${YELLOW}🔄 Iniciando backup: $BACKUP_NAME${NC}"

# 1. Crear directorio temporal para el backup
TEMP_BACKUP="$BACKUP_DIR/temp_$BACKUP_NAME"
mkdir -p $TEMP_BACKUP

# 2. Backup de Base de Datos
echo -e "${YELLOW}📊 Respaldando base de datos...${NC}"
if [ -f "$API_DIR/trading_bot.db" ]; then
    cp "$API_DIR/trading_bot.db" "$TEMP_BACKUP/trading_bot.db"
    echo -e "${GREEN}  ✅ Base de datos principal${NC}"
fi

if [ -f "$API_DIR/signals.db" ]; then
    cp "$API_DIR/signals.db" "$TEMP_BACKUP/signals.db"
    echo -e "${GREEN}  ✅ Base de datos de señales${NC}"
fi

# 3. Backup de Configuraciones
echo -e "${YELLOW}⚙️  Respaldando configuraciones...${NC}"
mkdir -p "$TEMP_BACKUP/config"

# Archivos de configuración importantes
CONFIG_FILES=(
    "bot_config.json"
    "trading_config.py"
    "signal_validator.py"
    "crypto_expert_agents_v2.py"
    ".env"
)

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$API_DIR/$file" ]; then
        cp "$API_DIR/$file" "$TEMP_BACKUP/config/"
        echo -e "${GREEN}  ✅ $file${NC}"
    fi
done

# 4. Backup de Estados del Sistema
echo -e "${YELLOW}💾 Respaldando estados del sistema...${NC}"
mkdir -p "$TEMP_BACKUP/states"

# Archivos de estado
STATE_FILES=(
    "system_state.json"
    "expert_agents_state_v2.json"
    "active_trades.json"
    "trade_history.json"
)

for file in "${STATE_FILES[@]}"; do
    if [ -f "$API_DIR/$file" ]; then
        cp "$API_DIR/$file" "$TEMP_BACKUP/states/"
        echo -e "${GREEN}  ✅ $file${NC}"
    fi
done

# 5. Backup de Logs Recientes (últimas 1000 líneas)
echo -e "${YELLOW}📝 Respaldando logs recientes...${NC}"
mkdir -p "$TEMP_BACKUP/logs"

if [ -d "$API_DIR/logs" ]; then
    for logfile in $API_DIR/logs/*.log; do
        if [ -f "$logfile" ]; then
            filename=$(basename "$logfile")
            tail -1000 "$logfile" > "$TEMP_BACKUP/logs/$filename"
            echo -e "${GREEN}  ✅ $filename (últimas 1000 líneas)${NC}"
        fi
    done
fi

# 6. Backup de Scripts de Deployment
echo -e "${YELLOW}🚀 Respaldando scripts de deployment...${NC}"
mkdir -p "$TEMP_BACKUP/deployment"

DEPLOY_SCRIPTS=(
    "start_production.sh"
    "stop_production.sh"
    "check_status.sh"
    "run_system.py"
    "trading_bot.service"
    "logrotate.conf"
)

for script in "${DEPLOY_SCRIPTS[@]}"; do
    if [ -f "$API_DIR/$script" ]; then
        cp "$API_DIR/$script" "$TEMP_BACKUP/deployment/"
        echo -e "${GREEN}  ✅ $script${NC}"
    fi
done

# 7. Crear archivo de información del backup
echo -e "${YELLOW}📋 Creando información del backup...${NC}"
cat > "$TEMP_BACKUP/backup_info.txt" << EOF
BOTPHIA - Información de Backup
==========================================
Fecha: $(date)
Hostname: $(hostname)
Usuario: $(whoami)
Directorio Base: $BASE_DIR

Contenido del Backup:
- Bases de datos SQLite
- Configuraciones del sistema
- Estados del trading bot
- Logs recientes (1000 líneas)
- Scripts de deployment

Estadísticas del Sistema al momento del backup:
- Procesos activos: $(ps aux | grep -E "(fastapi|signal_generator|run_system)" | grep -v grep | wc -l)
- Espacio usado: $(du -sh $API_DIR | cut -f1)
- Archivos totales: $(find $API_DIR -type f | wc -l)
EOF

# 8. Comprimir el backup
echo -e "${YELLOW}🗜️  Comprimiendo backup...${NC}"
cd $BACKUP_DIR
tar -czf "$BACKUP_NAME.tar.gz" "temp_$BACKUP_NAME"
BACKUP_SIZE=$(du -h "$BACKUP_NAME.tar.gz" | cut -f1)
echo -e "${GREEN}  ✅ Backup comprimido: $BACKUP_SIZE${NC}"

# 9. Limpiar directorio temporal
rm -rf "$TEMP_BACKUP"

# 10. Rotación de backups antiguos (mantener últimos 7)
echo -e "${YELLOW}♻️  Rotando backups antiguos...${NC}"
BACKUP_COUNT=$(ls -1 $BACKUP_DIR/botphia_backup_*.tar.gz 2>/dev/null | wc -l)
if [ $BACKUP_COUNT -gt 7 ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - 7))
    ls -1t $BACKUP_DIR/botphia_backup_*.tar.gz | tail -$REMOVE_COUNT | xargs rm -f
    echo -e "${GREEN}  ✅ Eliminados $REMOVE_COUNT backups antiguos${NC}"
fi

# 11. Verificar integridad del backup
echo -e "${YELLOW}🔍 Verificando integridad...${NC}"
if tar -tzf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ Backup verificado correctamente${NC}"
else
    echo -e "${RED}  ❌ Error en la integridad del backup${NC}"
    exit 1
fi

# 12. Resumen final
echo -e "${BLUE}
===========================================
✅ BACKUP COMPLETADO EXITOSAMENTE
===========================================
${NC}"
echo -e "Archivo: ${GREEN}$BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
echo -e "Tamaño: ${GREEN}$BACKUP_SIZE${NC}"
echo -e "Backups totales: ${GREEN}$(ls -1 $BACKUP_DIR/botphia_backup_*.tar.gz 2>/dev/null | wc -l)${NC}"

# 13. Agregar entrada al log
echo "$(date): Backup completado - $BACKUP_NAME.tar.gz ($BACKUP_SIZE)" >> $API_DIR/logs/backup.log

echo -e "${BLUE}
Para restaurar desde este backup:
  tar -xzf $BACKUP_DIR/$BACKUP_NAME.tar.gz
  cd temp_$BACKUP_NAME
  ./restore.sh
${NC}"