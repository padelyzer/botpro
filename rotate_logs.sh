#!/bin/bash

# Script para rotar logs manualmente o via cron
# Ejecutar con: ./rotate_logs.sh o añadir a crontab

LOGROTATE_CONF="/Users/ja/saby/trading_api/logrotate.conf"
STATE_FILE="/Users/ja/saby/trading_api/.logrotate.state"

# Ejecutar rotación de logs
/usr/sbin/logrotate -s $STATE_FILE $LOGROTATE_CONF

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "✅ Logs rotados exitosamente - $(date)"
else
    echo "❌ Error rotando logs - $(date)"
    exit 1
fi