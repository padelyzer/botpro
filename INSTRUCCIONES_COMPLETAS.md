# 🚀 INSTRUCCIONES COMPLETAS - SIGNAL HAVEN DESK

## 📦 Estructura del Sistema

```
/Users/ja/saby/
├── trading_api/          # Backend (FastAPI + Filósofos)
│   ├── fastapi_server.py # Servidor principal
│   ├── philosophers.py   # 4 filósofos originales
│   ├── philosophers_extended.py # 6 filósofos adicionales
│   └── binance_integration.py   # Conexión Binance
│
└── signal-haven-desk/    # Frontend (React + Vite)
    ├── src/
    │   ├── services/api.ts    # Cliente API
    │   ├── hooks/useTrading.ts # Hooks personalizados
    │   └── components/         # UI Components
    └── package.json
```

## 🔧 INSTALACIÓN PASO A PASO

### 1️⃣ Backend (FastAPI)

```bash
# Navegar al directorio del backend
cd /Users/ja/saby/trading_api

# Instalar dependencias si no están instaladas
pip install fastapi uvicorn websockets pandas numpy yfinance ccxt python-dotenv

# Iniciar el servidor
python3 fastapi_server.py
```

El backend estará disponible en:
- API REST: http://localhost:8000
- WebSocket: ws://localhost:8000/ws
- Docs: http://localhost:8000/docs

### 2️⃣ Frontend (React)

```bash
# En una nueva terminal, navegar al frontend
cd /Users/ja/saby/signal-haven-desk

# Instalar dependencias
npm install

# Iniciar el servidor de desarrollo
npm run dev
```

El frontend estará disponible en:
- http://localhost:5173

## 🎮 CÓMO USAR EL SISTEMA

### Inicio Rápido (7:00 AM)

1. **Abrir 2 terminales:**
   ```bash
   # Terminal 1 - Backend
   cd /Users/ja/saby/trading_api && python3 fastapi_server.py
   
   # Terminal 2 - Frontend
   cd /Users/ja/saby/signal-haven-desk && npm run dev
   ```

2. **Abrir navegador:**
   - Ve a http://localhost:5173
   - Verás el dashboard de Signal Haven Desk

3. **Iniciar el Bot:**
   - Click en el botón "Start Bot" en el header
   - El sistema comenzará a analizar con los filósofos

### Configuración del Bot

En el panel "Bot Controls" puedes ajustar:
- **Max Positions**: 3 (máximo de posiciones abiertas)
- **Risk per Trade**: 1% (riesgo por operación)
- **Stop Loss**: 3% (stop loss automático)
- **Take Profit**: 5% (take profit automático)
- **Trade Amount**: $100 (monto por trade)
- **Symbols**: BTC/USDT, ETH/USDT, SOL/USDT
- **Philosophers**: Seleccionar cuáles usar

### Filósofos Disponibles

**Conservadores:**
- SOCRATES - Mean reversion en rangos
- CONFUCIO - Busca equilibrio y armonía
- KANT - Reglas estrictas sin excepciones

**Balanceados:**
- PLATON - Busca patrones perfectos
- DESCARTES - Duda metódica, múltiples confirmaciones
- ARISTOTELES - Trend following lógico

**Agresivos:**
- NIETZSCHE - Contrarian extremo
- SUNTZU - Timing de guerra perfecto
- MAQUIAVELO - Pragmático oportunista

**Adaptativo:**
- HERACLITO - Fluye con el mercado

## 📊 MONITOREO EN TIEMPO REAL

### Panel de Posiciones
- Muestra todas las posiciones abiertas
- P&L en tiempo real
- Botón para cerrar manualmente

### Performance Metrics
- Win Rate
- Total P&L
- Daily P&L
- Trades ejecutados

### Alerts & Logs
- Señales detectadas
- Consenso entre filósofos
- Errores y warnings
- Trades ejecutados

## 🔍 VERIFICAR QUE TODO FUNCIONA

### Backend Health Check
```bash
curl http://localhost:8000/
```

Deberías ver:
```json
{
  "status": "online",
  "bot_status": "stopped",
  "positions": 0,
  "version": "1.0.0"
}
```

### WebSocket Test
```javascript
// En la consola del navegador (F12)
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## 🛠️ SOLUCIÓN DE PROBLEMAS

### Error: "Cannot connect to server"
```bash
# Verificar que el backend esté corriendo
ps aux | grep fastapi_server

# Si no está corriendo, iniciarlo:
cd /Users/ja/saby/trading_api && python3 fastapi_server.py
```

### Error: "Module not found"
```bash
# Backend - Instalar dependencias faltantes
pip install -r requirements.txt

# Frontend - Reinstalar node_modules
cd /Users/ja/saby/signal-haven-desk
rm -rf node_modules
npm install
```

### Error: CORS
Si hay problemas de CORS, verificar que el backend tenga:
```python
allow_origins=["http://localhost:5173"]
```

## 📈 FLUJO DE TRADING DIARIO

### 7:00 AM - Inicio
1. Iniciar backend y frontend
2. Configurar filósofos del día
3. Ajustar parámetros de riesgo
4. Iniciar bot

### 7:00-10:00 AM - Sesión Principal
- Alta volatilidad esperada
- Filósofos agresivos activos
- Monitorear consenso

### 10:00 AM-2:00 PM - Mantenimiento
- Revisar posiciones
- Ajustar stops si necesario
- Preparar para sesión tarde

### 2:00-4:00 PM - Sesión NYSE
- Segunda ventana de oportunidad
- Filósofos conservadores
- Cerrar posiciones del día

### 11:00 PM - Cierre
1. Detener bot
2. Revisar performance del día
3. Exportar logs si necesario

## 🔐 SEGURIDAD (3 Usuarios)

Como son solo 3 usuarios, la seguridad es simple:

1. **No exponer puertos:**
   - Mantener todo en localhost
   - No abrir puertos al exterior

2. **Backup diario:**
   ```bash
   # Crear backup de logs
   cp -r /Users/ja/saby/trading_api/logs /Users/ja/saby/backups/$(date +%Y%m%d)
   ```

3. **Monitoreo:**
   - Revisar alerts en el dashboard
   - Verificar P&L diario

## 🚨 COMANDOS DE EMERGENCIA

### Detener Todo
```bash
# Detener bot desde UI o:
curl -X POST http://localhost:8000/api/bot/stop

# Cerrar todas las posiciones
curl -X DELETE http://localhost:8000/api/position/all
```

### Reset Completo
```bash
# Reiniciar backend
pkill -f fastapi_server
cd /Users/ja/saby/trading_api && python3 fastapi_server.py

# Reiniciar frontend
pkill -f vite
cd /Users/ja/saby/signal-haven-desk && npm run dev
```

## 📞 CONTACTO Y SOPORTE

Si algo falla:
1. Revisar logs en la consola del backend
2. Revisar consola del navegador (F12)
3. Verificar conexión WebSocket
4. Reiniciar ambos servicios

## ✅ CHECKLIST DIARIO

- [ ] 6:45 AM - Iniciar servicios
- [ ] 7:00 AM - Configurar bot
- [ ] 7:15 AM - Verificar primeras señales
- [ ] 8:00 AM - Revisar consenso filosófico
- [ ] 10:00 AM - Check posiciones
- [ ] 2:00 PM - Preparar sesión NYSE
- [ ] 4:00 PM - Revisar P&L
- [ ] 11:00 PM - Cerrar día

---

**¡Sistema listo para trading! 🚀**

Para cualquier modificación o calibración, editar:
- Filósofos: `/trading_api/philosophers.py`
- Config: Desde el UI o `/trading_api/fastapi_server.py`
- UI: `/signal-haven-desk/src/components/`