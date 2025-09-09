#!/usr/bin/env python3
"""
Cómo validar una recuperación real del mercado crypto
Y cómo el ajuste de apalancamiento afecta la liquidación
"""

def analyze_recovery_and_leverage():
    print('='*60)
    print('📈 VALIDACIÓN DE RECUPERACIÓN + LEVERAGE STRATEGY')
    print('='*60)
    
    # PART 1: MARKET RECOVERY VALIDATION
    print(f'\n🔍 PARTE 1: CÓMO VALIDAR RECUPERACIÓN REAL')
    print('='*40)
    
    print(f'\n🎯 SEÑALES TÉCNICAS DE RECUPERACIÓN:')
    
    print(f'\n1️⃣ VOLUMEN:')
    print(f'✅ BULLISH: Volumen >50% encima del promedio 20 días')
    print(f'✅ BULLISH: Buy volume > Sell volume consistentemente')
    print(f'❌ FAKE: Volumen bajo en subidas (bull trap)')
    print(f'🎯 Indicador clave: Volume Profile + OBV')
    
    print(f'\n2️⃣ ESTRUCTURA DE PRECIOS:')
    print(f'✅ BULLISH: Higher highs + Higher lows')
    print(f'✅ BULLISH: Rompe resistencias con volumen')
    print(f'❌ FAKE: No puede mantener niveles ganados')
    print(f'🎯 SOL debe: Romper $195 → Mantener $192 → Target $200')
    
    print(f'\n3️⃣ MOVIMIENTO DE BTC:')
    print(f'✅ BULLISH: BTC lidera subida >3%')
    print(f'✅ BULLISH: BTC rompe $112k con volumen')
    print(f'❌ FAKE: Solo alts suben, BTC lateral')
    print(f'🎯 Regla: "BTC primero, alts después"')
    
    print(f'\n4️⃣ INDICADORES MOMENTUM:')
    print(f'✅ RSI: Sale de oversold (<30) hacia 40-50')
    print(f'✅ MACD: Cruce alcista + histograma verde')
    print(f'✅ MA: Precio cruza MA(7) y MA(25) hacia arriba')
    print(f'❌ FAKE: RSI divergencia negativa en rally')
    
    print(f'\n5️⃣ MARKET BREADTH:')
    print(f'✅ BULLISH: >70% cryptos en verde')
    print(f'✅ BULLISH: Top 10 todas positivas')
    print(f'❌ FAKE: Solo 2-3 coins suben')
    print(f'🎯 Check: BTC, ETH, SOL, BNB todos verdes')
    
    print(f'\n6️⃣ SENTIMENT & FUNDING:')
    print(f'✅ Fear & Greed: Sube de <30 a >40')
    print(f'✅ Funding rates: Neutrales o ligeramente positivos')
    print(f'❌ FAKE: Funding rates muy negativos aún')
    print(f'🎯 Señal: Shorts cerrando masivamente')
    
    print(f'\n📊 CONFIRMACIÓN TEMPORAL:')
    print(f'• 4H: Primera señal (puede ser fake)')
    print(f'• 12H: Confirmación inicial')
    print(f'• 1D: Confirmación sólida')
    print(f'• 3D: Trend change confirmado')
    
    print(f'\n✅ RECOVERY CONFIRMADA CUANDO:')
    print(f'1. BTC >$112k por 24+ horas')
    print(f'2. SOL >$195 con volumen alto')
    print(f'3. 3+ días consecutivos verdes')
    print(f'4. RSI >40 en daily')
    print(f'5. Volume consistently >average')
    
    # PART 2: LEVERAGE ADJUSTMENT
    print(f'\n='*40)
    print(f'⚙️ PARTE 2: AJUSTE DE APALANCAMIENTO')
    print('='*40)
    
    current_leverage = 10
    current_position = 29.82
    current_liquidation = 152.05
    current_price = 191.0
    
    print(f'\n📊 SITUACIÓN ACTUAL:')
    print(f'Leverage: {current_leverage}x')
    print(f'Posición: ${current_position}')
    print(f'Liquidación: ${current_liquidation}')
    print(f'Distancia: {((current_price - current_liquidation)/current_price)*100:.1f}%')
    
    print(f'\n🎯 CÓMO FUNCIONA EL LEVERAGE:')
    print(f'Formula liquidación = Entry - (100% / Leverage)')
    print(f'• 10x: Liquidación a -10% del entry')
    print(f'• 5x: Liquidación a -20% del entry')
    print(f'• 3x: Liquidación a -33% del entry')
    print(f'• 2x: Liquidación a -50% del entry')
    
    print(f'\n📉 REDUCIR LEVERAGE (Más seguro):')
    
    leverage_scenarios = [
        (10, 152.05, 20.4, "Actual"),
        (8, 143.25, 25.0, "Algo más seguro"),
        (5, 114.60, 40.0, "Mucho más seguro"),
        (3, 76.40, 60.0, "Ultra seguro"),
        (2, 57.30, 70.0, "Casi imposible liquidar"),
    ]
    
    print(f'\nEscenarios al REDUCIR leverage:')
    for lev, liq_price, buffer_pct, safety in leverage_scenarios:
        marker = "📍" if lev == current_leverage else ""
        print(f'{lev:2}x: Liq ${liq_price:6.2f} | Buffer {buffer_pct:4.1f}% | {safety} {marker}')
    
    print(f'\n✅ CÓMO REDUCIR LEVERAGE:')
    print(f'1. AGREGAR MARGEN (depositar más USD)')
    print(f'   • Depositas $30 → Leverage baja a ~5x')
    print(f'   • Liquidación se aleja proporcionalmente')
    print(f'2. CERRAR PARTE DE LA POSICIÓN')
    print(f'   • Cierras 50% → Mismo leverage pero menos exposure')
    print(f'3. MODO CROSS vs ISOLATED')
    print(f'   • Cross: Usa todo tu balance como margen')
    print(f'   • Isolated: Solo arriesgas el margen asignado')
    
    print(f'\n📈 AUMENTAR LEVERAGE (Más riesgo):')
    print(f'⚠️ NO RECOMENDADO en market bearish')
    print(f'• 15x: Liquidación a -6.7% ($178)')
    print(f'• 20x: Liquidación a -5% ($181)')
    print(f'• 25x: Liquidación a -4% ($183)')
    
    print(f'\n💡 ESTRATEGIA ÓPTIMA POR ESCENARIO:')
    
    print(f'\n🔴 Si market sigue BEARISH:')
    print(f'→ REDUCIR a 5x agregando $30 margen')
    print(f'→ Liquidación baja a ~$114')
    print(f'→ Casi imposible de liquidar')
    
    print(f'\n🟢 Si market confirma RECOVERY:')
    print(f'→ MANTENER 10x actual')
    print(f'→ Considerar agregar en dips con 5-8x')
    print(f'→ NUNCA aumentar leverage >10x')
    
    print(f'\n🟡 Si market LATERAL/UNCERTAIN:')
    print(f'→ REDUCIR a 7-8x por seguridad')
    print(f'→ Wait for clear direction')
    print(f'→ Preserve capital')
    
    # COMBINED STRATEGY
    print(f'\n='*40)
    print(f'🎯 ESTRATEGIA COMBINADA')
    print('='*40)
    
    print(f'\n📋 PLAN DE ACCIÓN:')
    
    print(f'\n1️⃣ MONITOREAR RECOVERY (Próximas 24-48h):')
    print(f'• BTC debe mantener >$110k')
    print(f'• SOL debe romper $195')
    print(f'• Volumen debe aumentar >50%')
    print(f'• Si TODO se cumple → Recovery probable')
    
    print(f'\n2️⃣ AJUSTAR LEVERAGE SEGÚN SEÑALES:')
    
    print(f'\n✅ Si CONFIRMA recovery:')
    print(f'• Mantén 10x actual')
    print(f'• Activa las recompras en $185, $180')
    print(f'• Target: $200-210 para tomar profits')
    
    print(f'\n❌ Si NO HAY recovery (BTC <$108k):')
    print(f'• INMEDIATO: Deposita $30 margen')
    print(f'• Reduce leverage a 5x')
    print(f'• Cancela órdenes de recompra')
    print(f'• Prepara stop loss en $175')
    
    print(f'\n🔍 CHECKPOINTS CRÍTICOS:')
    print(f'• Domingo 8pm: US futures open')
    print(f'• Lunes 9:30am: Stock market open') 
    print(f'• Martes: CPI data (si hay)')
    print(f'• Miércoles: Fed minutes')
    
    print(f'\n⚡ TRIGGERS DE ACCIÓN:')
    
    triggers = [
        ("BTC >$112k + Volume alto", "BULLISH", "Mantén leverage, activa recompras"),
        ("BTC <$108k", "BEARISH", "Reduce leverage a 5x AHORA"),
        ("SOL >$195 con volumen", "BULLISH", "Recovery confirmada, hold"),
        ("SOL <$185", "BEARISH", "Agrega margen o cierra"),
        ("RSI daily >50", "BULLISH", "Trend change, considera agregar"),
        ("Fear & Greed <25", "BEARISH", "Capitulación, reduce exposure"),
    ]
    
    print(f'\n📊 Tabla de decisión:')
    for trigger, signal, action in triggers:
        emoji = "🟢" if signal == "BULLISH" else "🔴"
        print(f'{emoji} {trigger:30} → {action}')
    
    print(f'\n💎 CONCLUSIÓN:')
    print(f'1. VALIDA recovery con múltiples señales')
    print(f'2. NO confíes en un solo indicador')
    print(f'3. AJUSTA leverage ANTES de problemas')
    print(f'4. Mejor estar "too safe" que liquidado')
    
    print('='*60)

if __name__ == "__main__":
    analyze_recovery_and_leverage()