# 🤖 BotphIA - Comandos Sistema Enriquecido

## 🎯 COMANDO PRINCIPAL - Sistema Completo con Señales Enriquecidas

### Ver todas las señales actuales con Entry, SL, TP, Apalancamiento y R:R Dinámico:
```bash
cd /Users/ja/saby/trading_api
python3 display_complete_signals.py
```

**Este comando muestra:**
- ✅ Señales CONFIRMADAS listas para ejecutar
- 📍 Entry, Stop Loss, TP1 y TP2 exactos
- 📊 Apalancamiento recomendado (basado en volatilidad)
- 📈 R:R dinámico (1.8:1 a 2.7:1 según ATR)
- 💰 Tamaño de posición sugerido
- 📊 Métricas de volatilidad y ATR

---

## 🚀 OTROS COMANDOS ÚTILES

### 1. Monitor Balanceado (Detecta señales continuamente):
```bash
python3 balanced_signal_monitor.py
```

### 2. Ver señales mejoradas con métricas:
```bash
python3 show_enhanced_signals.py
```

### 3. Monitor de precisión 24/7:
```bash
python3 run_monitor.py
```

### 4. Verificar señales actuales rápidamente:
```bash
python3 show_current_signals.py
```

### 5. Diagnóstico del sistema:
```bash
python3 signal_monitor_diagnostic.py
```

### 6. Probar configuración RSI (73/28):
```bash
python3 test_rsi_config.py
```

---

## 📊 CARACTERÍSTICAS DEL SISTEMA ENRIQUECIDO

### Métricas Dinámicas:
- **R:R Variable:** Se ajusta según volatilidad (ATR)
  - Baja volatilidad: 1.8-2.0:1
  - Media volatilidad: 2.0-2.3:1  
  - Alta volatilidad: 2.3-2.7:1

- **Apalancamiento Inteligente:** Inversamente proporcional a volatilidad
  - ATR < 1%: 10-12x
  - ATR 1-2%: 5-8x
  - ATR 2-3%: 3-5x
  - ATR > 3%: 2-3x

### Umbrales RSI Actualizados:
- **Sobrecompra:** 73 (antes 70)
- **Sobreventa:** 28 (antes 30)

---

## 💡 WORKFLOW RECOMENDADO

1. **Ver señales actuales:**
```bash
python3 display_complete_signals.py
```

2. **Si quieres monitoreo continuo:**
```bash
python3 balanced_signal_monitor.py
```

3. **Para ejecutar en background:**
```bash
./start_precision_monitor.sh start
```

4. **Ver logs del monitor:**
```bash
./start_precision_monitor.sh logs
```

---

## 🎯 COMANDO RÁPIDO (COPIAR Y PEGAR)

```bash
cd /Users/ja/saby/trading_api && python3 display_complete_signals.py
```

Este es el comando principal que muestra todas las señales con la información completa enriquecida.