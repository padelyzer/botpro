# 🚀 DEPLOYMENT GUIDE - SISTEMA HÍBRIDO BOTPHIA

## 📋 RESUMEN
Sistema de trading híbrido que funciona en 3 modos:
- **DEMO**: Sin API keys (datos públicos)
- **TESTNET**: Con API keys de testnet
- **REAL**: Con API keys reales

## 🎯 CARACTERÍSTICAS
- ✅ Funciona SIN API keys inicialmente
- ✅ Genera señales automáticamente cada 30 segundos
- ✅ WebSocket para actualizaciones en tiempo real
- ✅ Base de datos persistente
- ✅ Fácil upgrade a trading real

## 📦 ARCHIVOS CREADOS

### 1. Backend Híbrido
- `smart_trading_system.py` - Sistema de trading con detección automática de modo
- `signal_worker.py` - Worker que genera señales cada 30 segundos
- `fastapi_server_v2.py` - Backend actualizado con sistema híbrido
- `websocket_manager.py` - Gestión de WebSocket para tiempo real

### 2. Deployment
- `Dockerfile.hybrid` - Docker con supervisor para múltiples procesos
- `fly-hybrid.toml` - Configuración de Fly.io
- `deploy_hybrid.sh` - Script automático de deployment

## 🚀 DEPLOYMENT A FLY.IO

### Paso 1: Login en Fly.io
```bash
flyctl auth login
```

### Paso 2: Deploy Automático
```bash
cd /Users/ja/saby/trading_api
./deploy_hybrid.sh
```

### Paso 3: Verificar
```bash
# Ver estado
flyctl status --app botphia-trading-api

# Ver logs
flyctl logs --app botphia-trading-api

# Test endpoint
curl https://botphia-trading-api.fly.dev/health
```

## 🔧 CONFIGURACIÓN

### Modo DEMO (Por defecto)
```bash
# Ya configurado automáticamente
TRADING_MODE=demo
BINANCE_API_KEY=demo
BINANCE_SECRET_KEY=demo
```

### Upgrade a TESTNET
```bash
flyctl secrets set \
  BINANCE_API_KEY="tu_testnet_api_key" \
  BINANCE_SECRET_KEY="tu_testnet_secret_key" \
  TRADING_MODE="testnet" \
  --app botphia-trading-api
```

### Upgrade a REAL
```bash
flyctl secrets set \
  BINANCE_API_KEY="tu_real_api_key" \
  BINANCE_SECRET_KEY="tu_real_secret_key" \
  TRADING_MODE="live" \
  --app botphia-trading-api
```

## 📊 FUNCIONAMIENTO

### 1. FastAPI Server
- Puerto: 8000
- Endpoints: `/api/*`
- WebSocket: `/ws`
- Health: `/health`

### 2. Signal Worker
- Escanea mercados cada 30 segundos
- Genera señales con 8 filósofos
- Guarda en base de datos
- Envía por WebSocket

### 3. Modos de Operación

#### DEMO Mode
- Usa API pública de Binance (sin autenticación)
- Simula trades en memoria
- Perfecto para testing

#### TESTNET Mode
- Requiere API keys de testnet
- Trades en testnet de Binance
- Testing realista

#### REAL Mode
- Requiere API keys reales
- Trading real con dinero real
- Producción completa

## 🔍 MONITOREO

### Ver Logs en Tiempo Real
```bash
# Todos los logs
flyctl logs --app botphia-trading-api

# Solo FastAPI
flyctl logs --app botphia-trading-api | grep fastapi

# Solo Signal Worker
flyctl logs --app botphia-trading-api | grep signal_worker
```

### Verificar Señales
```bash
# Ver últimas señales generadas
curl https://botphia-trading-api.fly.dev/api/signals/active
```

### Estado del Sistema
```bash
curl https://botphia-trading-api.fly.dev/api/status
```

## 🐛 TROUBLESHOOTING

### Problema: No se generan señales
```bash
# Verificar que signal_worker está corriendo
flyctl ssh console --app botphia-trading-api
ps aux | grep signal_worker
```

### Problema: WebSocket no conecta
```bash
# Verificar WebSocket endpoint
wscat -c wss://botphia-trading-api.fly.dev/ws
```

### Problema: Base de datos vacía
```bash
# SSH al contenedor
flyctl ssh console --app botphia-trading-api

# Verificar base de datos
sqlite3 /app/data/trading_bot.db
.tables
SELECT COUNT(*) FROM signals;
```

## 📈 FRONTEND (VERCEL)

El frontend ya está configurado para conectarse al backend:

### Variables de Entorno en Vercel
```
VITE_API_URL=https://botphia-trading-api.fly.dev
VITE_WS_URL=wss://botphia-trading-api.fly.dev/ws
```

## ✅ CHECKLIST DE VERIFICACIÓN

- [ ] Backend desplegado en Fly.io
- [ ] Health check respondiendo
- [ ] Signal worker generando señales
- [ ] WebSocket conectando
- [ ] Frontend mostrando señales reales
- [ ] Base de datos persistiendo datos

## 🎉 RESULTADO FINAL

Con este sistema híbrido:
1. **Funciona inmediatamente** sin necesidad de API keys
2. **Genera señales reales** cada 30 segundos
3. **Muestra datos en el frontend** via WebSocket
4. **Puede ser actualizado** a trading real cuando quieras

## 📞 SOPORTE

Si tienes problemas:
1. Revisa los logs: `flyctl logs --app botphia-trading-api`
2. Verifica el status: `flyctl status --app botphia-trading-api`
3. Reinicia si es necesario: `flyctl restart --app botphia-trading-api`