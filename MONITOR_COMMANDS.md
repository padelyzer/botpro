# 🤖 BotphIA Precision Monitor - Comandos

## 🎯 Monitor de Precisión (RECOMENDADO)

Monitor de alta precisión que solo notifica señales confiables con alta probabilidad de éxito.

### Ejecutar Monitor de Precisión
```bash
cd /Users/ja/saby/trading_api
python3 run_monitor.py
```

**Características:**
- ✅ Solo señales con confianza ≥ 65%
- ✅ Risk/Reward mínimo 1.5:1
- ✅ Confirmación de volumen requerida
- ✅ Alineación con tendencia del mercado
- ✅ Sin falsos positivos
- ✅ Notificaciones solo para señales confirmadas

## 🔧 Control del Monitor (Background)

### Iniciar en Background
```bash
cd /Users/ja/saby/trading_api
./start_precision_monitor.sh start
```

### Detener Monitor
```bash
./start_precision_monitor.sh stop
```

### Ver Estado
```bash
./start_precision_monitor.sh status
```

### Ver Logs en Tiempo Real
```bash
./start_precision_monitor.sh logs
```

### Reiniciar
```bash
./start_precision_monitor.sh restart
```

## 📊 Otros Monitores Disponibles

### 1. Monitor con Visualización Rica
```bash
python3 enhanced_signal_monitor.py
```
- Dashboard interactivo con colores
- Múltiples modos de sensibilidad
- Visualización mejorada

### 2. Monitor Básico
```bash
python3 realtime_signal_monitor.py
```
- Versión simple
- Menor uso de recursos

### 3. Monitor Adaptativo
```bash
python3 adaptive_signal_monitor.py
```
- Se ajusta a condiciones del mercado
- Sensibilidad automática

### 4. Diagnóstico del Sistema
```bash
python3 signal_monitor_diagnostic.py
```
- Verifica conexión con Binance
- Prueba todos los componentes
- Detecta problemas

## 📈 Configuración del Monitor de Precisión

El monitor de precisión usa estos parámetros:

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| Confianza Mínima | 65% | Solo señales con alta confianza |
| Risk/Reward Mínimo | 1.5:1 | Relación riesgo/beneficio mínima |
| Confirmación Volumen | Sí | Requiere volumen > 1.2x promedio |
| Alineación Tendencia | Sí | Señal debe alinearse con tendencia |
| Score Mínimo | 65% | Score general de calidad |

## 📱 Notificaciones

El monitor envía notificaciones por:
- **Terminal**: Visualización en tiempo real
- **Logs**: Archivo en `logs/precision_monitor.log`
- **Base de datos**: SQLite para historial
- **Telegram**: Si está configurado

## 🔍 Pares Monitoreados

```
AVAX, LINK, NEAR, XRP, PENGU, ADA, SUI, DOT, DOGE, UNI, ETH, BTC
```

## ⏱ Frecuencia de Escaneo

- **5m**: Cada minuto
- **15m**: Cada 3 minutos
- **1h**: Cada 5 minutos
- **4h**: Cada 10 minutos

## 📊 Interpretación de Señales

### Stages de Señales
1. **POTENTIAL** 🔍 - Posible patrón (no notifica)
2. **FORMING** 📈 - Formándose (no notifica)
3. **NEARLY_COMPLETE** ⏰ - Casi listo (prepara notificación)
4. **CONFIRMED** ✅ - Confirmado (NOTIFICA Y EJECUTA)

### Calidad de Señales
- **Score > 80%**: Excelente oportunidad 🟢
- **Score 70-80%**: Buena oportunidad 🟡
- **Score 65-70%**: Oportunidad aceptable 🟠
- **Score < 65%**: No se notifica ❌

## 💾 Archivos Generados

- `logs/precision_monitor.log` - Log principal
- `precision_stats_*.json` - Estadísticas de sesión
- `notifications.db` - Base de datos de notificaciones

## 🛠️ Solución de Problemas

### Si no detecta señales:
1. Es normal en mercados laterales
2. El monitor solo notifica señales de alta calidad
3. Verifica con `python3 signal_monitor_diagnostic.py`

### Si el monitor se detiene:
1. Verifica logs en `logs/`
2. Reinicia con `./start_precision_monitor.sh restart`
3. Verifica conexión a internet

### Para más sensibilidad:
- NO se recomienda bajar los umbrales
- Mejor esperar señales de calidad
- El objetivo es precisión, no cantidad

## ✨ Tips de Uso

1. **Déjalo corriendo 24/7** - El monitor está diseñado para operación continua
2. **Confía en las señales** - Solo notifica alta probabilidad
3. **No fuerces detección** - Calidad sobre cantidad
4. **Revisa logs diariamente** - Para estadísticas y mejoras

---

**Versión**: 3.0 - Monitor de Precisión
**Actualizado**: Sistema optimizado para señales confiables