# 🚀 BotphIA Web Dashboard - Inicio Rápido

## ⚡ Comando de 1 Línea

```bash
cd /Users/ja/saby/trading_api && ./start_web_dashboard.sh start
```

## 🌐 URLs de Acceso

Una vez iniciado:

- **📊 Dashboard Principal:** http://localhost:8888/dashboard
- **🔧 API Documentation:** http://localhost:8888/docs  
- **📡 WebSocket Test:** ws://localhost:8888/ws

## 🎯 Características

✅ **Señales en Tiempo Real** - WebSocket para actualizaciones automáticas
✅ **RSI 73/28** - Umbrales optimizados para menos señales falsas  
✅ **R:R Dinámico** - 1.8:1 a 2.7:1 según volatilidad ATR
✅ **Apalancamiento Adaptativo** - 2x a 12x inversamente proporcional a volatilidad
✅ **12 Pares** - AVAX, LINK, NEAR, XRP, PENGU, ADA, SUI, DOT, DOGE, UNI, ETH, BTC
✅ **4 Timeframes** - 5m, 15m, 1h, 4h

## 📱 Interfaz

- **Dashboard Responsivo** - Funciona en móvil y desktop
- **Conexión en Tiempo Real** - Indicador de estado WebSocket
- **Métricas del Sistema** - Win rate 61%, R:R 2.1:1, Leverage 7.2x
- **Señales Detalladas** - Entry, SL, TP, leverage, patrón, timeframe

## 🔧 Comandos Útiles

```bash
# Iniciar dashboard
./start_web_dashboard.sh start

# Ver estado
./start_web_dashboard.sh status

# Detener
./start_web_dashboard.sh stop

# Iniciar con Docker
./start_web_dashboard.sh docker
```

## 🌍 Para Acceso Público

1. **Cambiar host en web_api.py:**
   ```python
   uvicorn.run("web_api:app", host="0.0.0.0", port=8888)
   ```

2. **Abrir puerto en firewall:**
   ```bash
   sudo ufw allow 8888
   ```

3. **Acceder desde cualquier dispositivo:**
   ```
   http://TU-IP:8888/dashboard
   ```

---

**¡Sistema listo para uso inmediato! 🎉**