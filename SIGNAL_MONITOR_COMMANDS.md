# 🤖 BotphIA Signal Monitor - Comandos

## 🚀 Iniciar Monitor Mejorado

### Opción 1: Monitor con Visualización Rica
```bash
cd /Users/ja/saby/trading_api
python3 enhanced_signal_monitor.py
```

**Características:**
- Dashboard interactivo con colores
- Tarjetas visuales para cada señal
- Tabla resumen de todas las señales activas
- Panel de estadísticas en tiempo real
- Actualización cada 30 segundos

### Opción 2: Monitor Básico
```bash
cd /Users/ja/saby/trading_api
python3 realtime_signal_monitor.py
```

**Características:**
- Salida de texto simple
- Compatible con todas las terminales
- Menor uso de recursos

### Opción 3: Test Rápido del Sistema
```bash
cd /Users/ja/saby/trading_api
python3 test_signal_system.py
```

**Prueba:**
- Detección de patrones
- Sistema de notificaciones
- Escaneo multi-par
- Generación de Pine Script

## 📊 Modos de Operación

### 1. **Agresivo** 🚀
- Detecta TODAS las señales posibles
- Notifica desde etapa POTENCIAL
- Máximo 5 señales por par
- Confianza mínima: 40%

### 2. **Balanceado** ⚖️ (Recomendado)
- Balance entre cantidad y calidad
- Notifica desde etapa FORMÁNDOSE
- Máximo 3 señales por par
- Confianza mínima: 50%

### 3. **Conservador** 🛡️
- Solo señales de alta calidad
- Notifica solo CASI COMPLETO y CONFIRMADO
- Máximo 2 señales por par
- Confianza mínima: 70%

## 📈 Pares Monitoreados

```
AVAX, LINK, NEAR, XRP, PENGU, ADA, SUI, DOT, DOGE, UNI, ETH, BTC
```

## ⏱ Timeframes

- **5m**: Scalping, entradas rápidas
- **15m**: Day trading
- **1h**: Swing trading corto
- **4h**: Swing trading medio

## 🔔 Stages de Notificación

1. **🔍 POTENTIAL** - Posible patrón detectado
2. **📈 FORMING** - Patrón formándose
3. **⏰ NEARLY_COMPLETE** - Casi completo, preparar orden
4. **✅ CONFIRMED** - Confirmado, ejecutar entrada

## 💾 Exportar Señales

Al detener el monitor (Ctrl+C), puedes exportar las señales detectadas:
```
¿Exportar señales? (s/n): s
```

Genera archivo JSON con todas las señales activas.

## 🛠️ Instalación de Dependencias

```bash
pip3 install rich ccxt pandas numpy ta-lib
```

## 📱 Visualización en Terminal

### Display Mejorado Incluye:

**Señales Confirmadas** (Verde)
- Tarjetas con toda la información
- Entry, SL, TP1, TP2
- Risk/Reward ratio
- Confianza del patrón

**Señales Casi Completas** (Amarillo)
- Preparación para entrada
- Información completa de niveles

**Tabla Resumen**
- Todas las señales activas
- Ordenadas por confianza
- Colores según stage

**Panel de Estadísticas**
- Total de escaneos
- Señales detectadas/confirmadas
- Top patrones
- Mejores pares

## 🔧 Personalización

Puedes personalizar los pares al iniciar:
1. Selecciona "Personalizar pares"
2. Ingresa los símbolos separados por coma
3. Ejemplo: `BTC,ETH,SOL,AVAX`

## 📝 Logs y Debug

Los logs se muestran en la terminal con códigos de color:
- 🔵 Info: Información general
- 🟡 Alert: Alertas importantes
- 🔴 Warning: Advertencias
- 🟣 Critical: Señales confirmadas

## ⚡ Tips de Uso

1. **Para pantallas pequeñas**: Usa el modo compacto
2. **Para trading activo**: Usa modo Agresivo en 5m/15m
3. **Para swing trading**: Usa modo Conservador en 1h/4h
4. **Para monitoreo 24/7**: Usa modo Balanceado

## 🆘 Solución de Problemas

Si no ves colores en la terminal:
```bash
export TERM=xterm-256color
```

Si el monitor es muy lento:
- Reduce el número de pares
- Usa timeframes más largos
- Cambia a modo Conservador

---

**Última actualización**: Sistema funcionando con visualización mejorada
**Versión**: 2.0 - Multi-timeframe con notificaciones progresivas