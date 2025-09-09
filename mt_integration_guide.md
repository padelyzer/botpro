# 🔗 GUÍA COMPLETA: CONECTAR PYTHON CON METATRADER

## 📋 COMPONENTES NECESARIOS

### 1. **SOFTWARE REQUERIDO**
- ✅ MetaTrader 5 (MT5) - Descarga desde tu broker
- ✅ Python 3.8+ instalado
- ✅ Scripts de señales (ya los tienes)

### 2. **LIBRERÍAS PYTHON**
```bash
pip install MetaTrader5
pip install pandas numpy
```

### 3. **ARCHIVOS CREADOS**
- `metatrader_bridge.py` - Bridge Python ↔ MT5
- `PythonSignalReceiver.mq5` - Expert Advisor para MT5
- Scripts de señales existentes

---

## 🚀 INSTALACIÓN PASO A PASO

### PASO 1: CONFIGURAR METATRADER 5
1. **Descargar MT5** de tu broker (IC Markets, XM, etc.)
2. **Crear cuenta demo** para pruebas
3. **Anotar credenciales:**
   - Login (número de cuenta)
   - Password
   - Servidor del broker

### PASO 2: INSTALAR EXPERT ADVISOR
1. Abrir MT5
2. Ir a: `File → Open Data Folder`
3. Navegar a: `MQL5 → Experts`
4. Copiar `PythonSignalReceiver.mq5` ahí
5. En MT5: `Tools → MetaQuotes Language Editor`
6. Compilar el EA (F7)
7. Reiniciar MT5

### PASO 3: CONFIGURAR PYTHON BRIDGE
Editar `metatrader_bridge.py`:

```python
# Configurar tus credenciales
LOGIN = 12345678  # Tu número de cuenta
PASSWORD = "tu_password"
SERVER = "ICMarkets-Demo"  # Tu servidor
```

### PASO 4: ACTIVAR AUTO TRADING
En MT5:
1. `Tools → Options → Expert Advisors`
2. ✅ Allow automated trading
3. ✅ Allow DLL imports
4. ✅ Allow WebRequest

---

## 🔄 ARQUITECTURA DEL SISTEMA

```
┌─────────────────┐     Señales      ┌──────────────────┐
│  Python Scripts │ ───────────────> │ MetaTrader Bridge │
│  (Análisis)     │                   │  (metatrader_    │
└─────────────────┘                   │   bridge.py)     │
                                      └──────────────────┘
                                               │
                                          Socket/API
                                               │
                                               ▼
                                      ┌──────────────────┐
                                      │   MetaTrader 5   │
                                      │  (Expert Advisor)│
                                      │   Ejecuta Trades │
                                      └──────────────────┘
```

---

## 💻 CÓDIGO DE INTEGRACIÓN

### EJEMPLO 1: Enviar señal simple
```python
from metatrader_bridge import SignalSender

# Crear sender
sender = SignalSender()

# Enviar señal de compra
sender.send_signal(
    symbol="EURUSD",
    action="BUY",
    stop_loss=1.0850,
    take_profit=1.0950
)
```

### EJEMPLO 2: Integrar con scanner existente
```python
# En tu quick_profit_scanner.py, agregar:

from metatrader_bridge import MetaTraderBridge

# Conectar con MT5
bridge = MetaTraderBridge()
bridge.connect_mt5(login=12345678, password="pass", server="Demo")

# Cuando detectes una oportunidad:
if signal_strength > 70:
    bridge.send_order(
        symbol="EURUSD",
        action="BUY",
        volume=0.01,
        sl=stop_loss,
        tp=take_profit
    )
```

### EJEMPLO 3: Bot automatizado completo
```python
import time
from metatrader_bridge import MetaTraderBridge
from quick_profit_scanner import scan_opportunities

# Conectar
bridge = MetaTraderBridge()
bridge.connect_mt5(login=12345678, password="pass", server="Demo")

while True:
    # Escanear oportunidades
    opportunities, momentum = scan_opportunities()
    
    # Ejecutar las mejores
    for opp in opportunities[:2]:  # Max 2 trades
        if opp['strength'] > 75:
            bridge.send_order(
                symbol=opp['symbol'] + "USD",
                action=opp['action'],
                volume=0.01,
                sl=opp['stop'],
                tp=opp['target']
            )
    
    time.sleep(60)  # Revisar cada minuto
```

---

## ⚙️ CONFIGURACIÓN AVANZADA

### GESTIÓN DE RIESGO
```python
# Calcular tamaño de posición basado en riesgo
def calculate_lot_size(balance, risk_percent, stop_pips):
    risk_amount = balance * (risk_percent / 100)
    pip_value = 10  # Para pares XXX/USD con lotes estándar
    lot_size = risk_amount / (stop_pips * pip_value)
    return round(lot_size, 2)
```

### TRAILING STOP DINÁMICO
```python
# Modificar stops en posiciones ganadoras
def update_trailing_stop(bridge, ticket, new_sl):
    bridge.modify_position(ticket, sl=new_sl)
```

### FILTROS DE MERCADO
```python
# Solo operar en horario de Londres/NY
from datetime import datetime

def is_good_trading_time():
    hour = datetime.now().hour
    return 8 <= hour <= 20  # UTC
```

---

## 🔧 TROUBLESHOOTING

### ERROR: "No module named MetaTrader5"
```bash
pip install --upgrade MetaTrader5
```

### ERROR: "Connection failed"
- Verificar que MT5 esté abierto
- Comprobar credenciales
- Firewall puede bloquear conexión

### ERROR: "Symbol not found"
- Verificar sufijo del símbolo (USD, USDT, etc.)
- Algunos brokers usan nombres diferentes

### ERROR: "Trade not executed"
- Verificar Auto Trading activado
- Comprobar margen disponible
- Revisar horario del mercado

---

## 📊 MONITOREO Y LOGS

### Ver trades ejecutados
```python
# Obtener historial
positions = bridge.get_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['profit']}")
```

### Guardar logs
```python
import logging

logging.basicConfig(
    filename='mt5_trades.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
```

---

## 🎯 PRÓXIMOS PASOS

1. **Probar en cuenta DEMO primero**
2. **Ajustar tamaños de posición**
3. **Configurar stops y targets según tu estrategia**
4. **Monitorear performance**
5. **Optimizar parámetros**

---

## ⚠️ IMPORTANTE

- **SIEMPRE** probar en DEMO primero
- **NUNCA** arriesgar más del 2% por trade
- **SIEMPRE** usar stop loss
- **REVISAR** logs diariamente
- **ACTUALIZAR** EA si cambias estrategia

---

## 🆘 SOPORTE

Si necesitas ayuda:
1. Revisar logs de MT5: `View → Experts`
2. Verificar conexión: `print(mt5.terminal_info())`
3. Consultar documentación oficial MT5

¡Con esta integración, tus señales de Python se ejecutarán automáticamente en MetaTrader! 🚀