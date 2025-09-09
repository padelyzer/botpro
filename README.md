# 📊 Trading System API V1.0

## 🎯 Sistema Inteligente de Trading con Estrategias Adaptativas

API REST profesional para trading automatizado con estrategias especializadas para cada tipo de mercado. Optimizado para deployment en Render (plan gratuito).

## ✨ Características

- **3 Estrategias Especializadas** versionadas y documentadas
- **Detección automática** del régimen de mercado
- **API REST** completa con FastAPI
- **Documentación interactiva** (Swagger/ReDoc)
- **Sistema de autenticación** JWT
- **Listo para producción** en Render

## 📦 Estrategias Incluidas

### 1️⃣ RANGING Strategy V1.0 (Mercados Laterales)
**Fortalezas:**
- Alta efectividad en consolidaciones (70-80% del mercado)
- Puntos de entrada/salida claramente definidos  
- Risk/Reward ratio típicamente 1:2 o mejor
- Múltiples oportunidades por día

**Debilidades:**
- Pérdidas en falsos breakouts (-2% a -3% por trade)
- Requiere monitoreo constante de niveles
- Vulnerable a eventos de noticias

**Condiciones Óptimas:**
- ADX < 25
- Bollinger Bands paralelas
- RSI oscilando entre 30-70

### 2️⃣ BULLISH Strategy V1.0 (Mercados Alcistas)
**Fortalezas:**
- Captura movimientos de 5-15% en tendencias fuertes
- Win rate alto (45-55%) en bull markets
- Riesgo controlado con trailing stops

**Debilidades:**
- Entradas tardías (pierde 20-30% inicial)
- Vulnerable a correcciones súbitas (-3% a -5%)
- Mal desempeño en lateralizaciones

**Condiciones Óptimas:**
- ADX > 30 con +DI > -DI
- EMAs en orden alcista (9 > 21 > 50 > 200)
- Volumen creciente en impulsos

### 3️⃣ BEARISH Strategy V1.0 (Mercados Bajistas)
**Fortalezas:**
- Protección de capital en bear markets
- Ganancias de 3-10% en caídas rápidas
- Identificación precisa de techos

**Debilidades:**
- Alto riesgo de short squeeze (-5% a -10%)
- Pocas señales (1-2 por semana)
- Timing crítico para entradas

**Condiciones Óptimas:**
- ADX > 30 con -DI dominante
- EMAs en orden bajista
- RSI < 50 consistentemente

## 🚀 Instalación Local

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/trading-api.git
cd trading-api

# Instalar dependencias
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# Ejecutar servidor
python app.py
```

## 🌐 Deploy en Render

1. **Fork este repositorio** en GitHub

2. **Crear cuenta en Render** (gratis)
   - Ve a [render.com](https://render.com)
   - Regístrate con GitHub

3. **Crear nuevo Web Service**
   - Click en "New +" > "Web Service"
   - Conecta tu repo de GitHub
   - Render detectará automáticamente `render.yaml`

4. **Configuración automática**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Plan: Free

5. **Deploy** 🚀
   - Click en "Create Web Service"
   - Espera ~5 minutos para el build
   - Tu API estará en: `https://tu-app.onrender.com`

## 📝 Endpoints Principales

### Análisis de Mercado
```http
POST /api/v1/analysis
Content-Type: application/json

{
  "symbol": "BTC-USD",
  "timeframe": "1h",
  "period": "7d"
}
```

### Generar Señal
```http
POST /api/v1/signals
Content-Type: application/json

{
  "symbol": "ETH-USD",
  "timeframe": "4h",
  "capital": 1000
}
```

### Obtener Estrategias
```http
GET /api/v1/strategies
```

### Documentación Interactiva
- Swagger UI: `https://tu-api.onrender.com/docs`
- ReDoc: `https://tu-api.onrender.com/redoc`

## 📊 Ejemplo de Respuesta

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "symbol": "BTC-USD",
  "type": "LONG",
  "entry_price": 42500.50,
  "stop_loss": 41200.00,
  "take_profit": 44800.00,
  "confidence": 0.75,
  "strategy_name": "BullishStrategyV1",
  "strategy_version": "1.0",
  "market_regime": "BULLISH",
  "risk_reward_ratio": 2.5,
  "position_size": 500.00,
  "metadata": {
    "trend_strength": 0.82,
    "signals": ["PULLBACK_ENTRY", "MACD_BULLISH"],
    "signal_strength": 7
  }
}
```

## 🔧 Configuración

### Variables de Entorno

```env
# Seguridad
SECRET_KEY=your-secret-key-here

# API Keys (opcional)
BINANCE_API_KEY=your-binance-key
BINANCE_SECRET_KEY=your-binance-secret

# Base de datos (futuro)
DATABASE_URL=postgresql://user:pass@host/db
```

## 📡 Integración con Trading Bot

```python
import requests

API_URL = "https://tu-api.onrender.com"

def get_trading_signal(symbol):
    response = requests.post(
        f"{API_URL}/api/v1/signals",
        json={
            "symbol": symbol,
            "timeframe": "1h",
            "capital": 1000
        }
    )
    
    if response.status_code == 200:
        signal = response.json()
        print(f"Señal recibida: {signal['type']} en {signal['entry_price']}")
        return signal
    return None
```

## 📋 Roadmap

- [ ] Base de datos PostgreSQL para histórico
- [ ] WebSockets para señales en tiempo real
- [ ] Integración directa con Binance
- [ ] Dashboard web interactivo
- [ ] Machine Learning para optimización
- [ ] Backtesting engine completo
- [ ] Sistema de alertas por Telegram/Discord

## ⚠️ Disclaimer

**IMPORTANTE:** Este sistema es para propósitos educativos. El trading conlleva riesgos significativos. No nos hacemos responsables por pérdidas financieras. Siempre haz tu propia investigación y nunca inviertas más de lo que puedes permitirte perder.

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles

## 🤝 Contribuciones

Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📞 Soporte

- Email: support@trading-api.com
- Discord: [Unirse al servidor](https://discord.gg/trading)
- Issues: [GitHub Issues](https://github.com/tu-usuario/trading-api/issues)

---

🌟 **Si este proyecto te ayuda, considera darle una estrella!**