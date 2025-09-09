# 🌐 BotphIA Web Dashboard - Guía Completa

## 📋 Resumen del Sistema

El **BotphIA Web Dashboard** es una interfaz web que permite acceder a las señales de trading enriquecidas a través de cualquier navegador. El sistema incluye:

- ✅ **API REST** con FastAPI
- 🔄 **WebSocket** para actualizaciones en tiempo real
- 📊 **Dashboard interactivo** con Bootstrap
- 🐳 **Docker** para deployment fácil
- 🛡️ **CORS** configurado para acceso público

---

## 🚀 Inicio Rápido

### Opción 1: Ejecución Directa
```bash
cd /Users/ja/saby/trading_api
./start_web_dashboard.sh start
```

### Opción 2: Con Docker
```bash
cd /Users/ja/saby/trading_api
./start_web_dashboard.sh docker
```

### Acceso al Dashboard
Una vez iniciado, accede a:
- **Dashboard:** http://localhost:8888/dashboard
- **API Docs:** http://localhost:8888/docs
- **WebSocket:** ws://localhost:8888/ws

---

## 📂 Estructura del Sistema

```
trading_api/
├── web_api.py                  # Backend FastAPI
├── static/
│   └── dashboard.html         # Frontend del dashboard
├── requirements_web.txt       # Dependencias
├── Dockerfile.web            # Docker configuration
├── docker-compose.web.yml    # Docker Compose
├── start_web_dashboard.sh    # Script de inicio
└── WEB_DASHBOARD_GUIDE.md    # Esta guía
```

---

## 🔧 Instalación y Configuración

### Requisitos Previos
- Python 3.11+
- pip3
- Docker (opcional)

### Instalación de Dependencias
```bash
pip3 install -r requirements_web.txt
```

### Dependencias Principales
- **FastAPI:** Framework web moderno
- **Uvicorn:** Servidor ASGI
- **WebSockets:** Comunicación en tiempo real
- **Rich:** Formateo y logging elegante

---

## 🌐 Endpoints del API

### REST Endpoints

#### `GET /`
**Información del sistema**
```json
{
  "system": "BotphIA Trading Signals API",
  "version": "1.0.0",
  "status": "active",
  "features": [...]
}
```

#### `GET /api/signals`
**Señales básicas**
```json
{
  "timestamp": "2025-09-09T...",
  "total_signals": 5,
  "signals": [...],
  "status": "success"
}
```

#### `GET /api/signals/enhanced`
**Señales enriquecidas con métricas completas**
```json
{
  "timestamp": "2025-09-09T...",
  "system_config": {
    "rsi_overbought": 73,
    "rsi_oversold": 28,
    "dynamic_rr": true,
    "adaptive_leverage": true
  },
  "signals": [...]
}
```

#### `GET /api/pairs`
**Pares de trading disponibles**
```json
{
  "total_pairs": 12,
  "pairs": ["BTCUSDT", "ETHUSDT", ...],
  "timeframes": ["5m", "15m", "1h", "4h"]
}
```

#### `GET /api/config`
**Configuración del sistema**
```json
{
  "rsi_config": {
    "overbought": 73,
    "oversold": 28,
    "period": 14
  },
  "risk_reward": {
    "type": "dynamic",
    "range": "1.8:1 - 2.7:1"
  },
  "leverage": {
    "type": "adaptive", 
    "range": "2x - 12x"
  }
}
```

#### `GET /api/stats`
**Estadísticas del backtesting**
```json
{
  "backtest_results": {
    "total_return": 84.5,
    "win_rate": 61.0,
    "sharpe_ratio": 1.85
  },
  "top_pairs": [...],
  "best_patterns": [...]
}
```

### WebSocket Endpoint

#### `WS /ws`
**Conexión en tiempo real**

Mensajes recibidos:
```json
{
  "type": "initial_signals",
  "timestamp": "2025-09-09T...",
  "data": [...]
}

{
  "type": "signals_update", 
  "timestamp": "2025-09-09T...",
  "data": [...]
}

{
  "type": "ping",
  "timestamp": "2025-09-09T..."
}
```

---

## 📊 Características del Dashboard

### Métricas en Tiempo Real
- **Señales Activas:** Contador dinámico
- **Win Rate:** 61% (del backtesting)
- **R:R Promedio:** 2.1:1
- **Apalancamiento Promedio:** 7.2x

### Señales Detalladas
Cada señal muestra:
- **Símbolo:** Par de trading (ej. BTCUSDT)
- **Dirección:** BUY/LONG o SELL/SHORT
- **Precios:** Entry, Stop Loss, Take Profit
- **Apalancamiento:** Recomendado según volatilidad
- **R:R Ratio:** Dinámico basado en ATR
- **Patrón:** Tipo de patrón detectado
- **Timeframe:** 5m, 15m, 1h, 4h
- **Timestamp:** Momento de detección

### Indicadores Visuales
- 🟢 **Verde:** Señales BUY/LONG
- 🔴 **Rojo:** Señales SELL/SHORT
- 🟡 **Amarillo:** Timeframes
- 🔵 **Azul:** Patrones detectados

### Estados de Conexión
- **Conectado:** WebSocket activo
- **Desconectado:** Sin conexión en tiempo real

---

## 🛠️ Comandos del Script

### `./start_web_dashboard.sh start`
Inicia el dashboard en modo desarrollo
- Verifica dependencias
- Instala requirements
- Ejecuta servidor en localhost:8888

### `./start_web_dashboard.sh docker`
Inicia con Docker
- Build automático de la imagen
- Configuración con docker-compose
- Puerto 8888 expuesto

### `./start_web_dashboard.sh stop`
Detiene el dashboard
- Mata procesos Python activos
- Detiene contenedores Docker

### `./start_web_dashboard.sh status`
Muestra estado del sistema
- Estado del proceso
- Estado del contenedor
- Estado del puerto 8888

### `./start_web_dashboard.sh logs`
Muestra logs en tiempo real
- Logs del contenedor Docker
- Información de debugging

---

## 🐳 Deployment con Docker

### Build Manual
```bash
docker build -f Dockerfile.web -t botphia-web .
docker run -p 8888:8888 botphia-web
```

### Con Docker Compose
```bash
docker-compose -f docker-compose.web.yml up --build -d
```

### Verificar Deployment
```bash
curl http://localhost:8888/
curl http://localhost:8888/api/signals
```

---

## 🌍 Deployment en Producción

### 1. Servidor VPS/Cloud
```bash
# Clonar repositorio
git clone <repo-url>
cd trading_api

# Iniciar con Docker
./start_web_dashboard.sh docker
```

### 2. Variables de Entorno
```bash
export PYTHONPATH=/app
export HOST=0.0.0.0
export PORT=8888
```

### 3. Proxy Reverso (Nginx)
```nginx
server {
    listen 80;
    server_name tu-dominio.com;
    
    location / {
        proxy_pass http://localhost:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 4. HTTPS con Let's Encrypt
```bash
sudo certbot --nginx -d tu-dominio.com
```

---

## 🔧 Personalización

### Modificar Puerto
Editar `web_api.py`:
```python
uvicorn.run("web_api:app", host="0.0.0.0", port=9999)
```

### Configurar CORS
Editar `web_api.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tu-dominio.com"],  # Dominios específicos
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Personalizar Dashboard
Editar `static/dashboard.html`:
- Cambiar colores en CSS
- Agregar nuevos componentes
- Modificar layout

---

## 🚨 Solución de Problemas

### Error: "Module not found"
```bash
pip3 install -r requirements_web.txt
```

### Error: "Port 8888 already in use"
```bash
./start_web_dashboard.sh stop
# O cambiar puerto en web_api.py
```

### Error: "Dashboard not found"
```bash
# Verificar que existe static/dashboard.html
ls -la static/
```

### WebSocket no conecta
- Verificar firewall
- Comprobar proxy settings
- Revisar logs del servidor

### Docker no funciona
```bash
docker --version
docker-compose --version
sudo systemctl start docker
```

---

## 📈 Métricas y Monitoreo

### Logs del Sistema
```bash
# Logs en tiempo real
./start_web_dashboard.sh logs

# Logs de Docker
docker-compose -f docker-compose.web.yml logs -f
```

### Monitoreo de Performance
- Conexiones WebSocket activas
- Tiempo de respuesta API
- Uso de memoria y CPU
- Frecuencia de actualizaciones

### Health Check
El sistema incluye health check automático:
```bash
curl http://localhost:8888/
```

---

## 🔐 Seguridad

### Consideraciones de Seguridad
- **CORS:** Configurado para desarrollo (*), restringir en producción
- **Rate Limiting:** Implementar si es necesario
- **Authentication:** Agregar autenticación para acceso privado
- **HTTPS:** Obligatorio en producción
- **Firewall:** Configurar reglas apropiadas

### Recomendaciones
1. Usar HTTPS en producción
2. Configurar firewall para puerto 8888
3. Implementar rate limiting
4. Monitorear logs de acceso
5. Actualizar dependencias regularmente

---

## 🎯 Casos de Uso

### 1. Desarrollo Local
```bash
./start_web_dashboard.sh start
# Acceder a http://localhost:8888/dashboard
```

### 2. Demo para Clientes
```bash
./start_web_dashboard.sh docker
# Compartir URL: http://tu-ip:8888/dashboard
```

### 3. Monitoreo 24/7
- Deploy en VPS
- Configurar autostart
- Implementar notificaciones

### 4. Integración con Terceros
- Usar API REST endpoints
- WebSocket para apps en tiempo real
- Embedable en iframes

---

## 📞 Soporte

### Comandos de Diagnóstico
```bash
# Estado del sistema
./start_web_dashboard.sh status

# Verificar dependencias
python3 -c "import fastapi, uvicorn; print('OK')"

# Test de API
curl http://localhost:8888/api/signals

# Test de WebSocket
wscat -c ws://localhost:8888/ws
```

### Archivos de Log
- Salida estándar del servidor
- Logs de Docker
- Logs del sistema operativo

---

## 🚀 Próximas Funcionalidades

### En Desarrollo
- [ ] Autenticación de usuarios
- [ ] Alertas por email/Telegram
- [ ] Histórico de señales
- [ ] Configuración dinámica
- [ ] API para crear señales manuales

### Roadmap
- [ ] Mobile app
- [ ] Integración con exchanges
- [ ] Backtesting web interface
- [ ] Advanced charting
- [ ] Portfolio tracking

---

**¡El sistema está listo para uso en producción! 🎉**

Para iniciar inmediatamente:
```bash
cd /Users/ja/saby/trading_api
./start_web_dashboard.sh start
```

Luego accede a: **http://localhost:8888/dashboard**