# 📊 Pine Scripts - BotphIA Trading System

Esta carpeta contiene los scripts de Pine Script generados automáticamente por el sistema de señales BotphIA.

## 📁 Estructura

- `somi_signal.pine` - Señal para SOMI/USDT con niveles de entrada, SL y TP
- Los nuevos scripts se guardarán aquí automáticamente

## 🚀 Uso Rápido

### Copiar script al portapapeles:
```bash
cat pine/somi_signal.pine | pbcopy
```

### Abrir en editor:
```bash
code pine/somi_signal.pine
```

### Ver contenido:
```bash
cat pine/somi_signal.pine
```

## 📈 Para usar en TradingView:

1. Copiar el contenido del archivo `.pine`
2. Ir a [TradingView.com](https://tradingview.com)
3. Abrir Pine Editor (botón inferior o Cmd+E)
4. Pegar el código
5. Click en "Add to Chart"

## 🔧 Generar nuevas señales:

```bash
# Analizar un par específico
python3 analyze_somi.py

# El Pine Script se guardará automáticamente en esta carpeta
```

## 📝 Características de los scripts:

- ✅ Líneas de Entry, Stop Loss y Take Profit
- ✅ Tabla informativa con datos de la señal
- ✅ Zonas coloreadas de riesgo y profit
- ✅ Alertas configurables
- ✅ Compatible con Pine Script v6