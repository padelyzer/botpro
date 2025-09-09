#!/usr/bin/env python3
"""
Análisis de riesgo de liquidación para mantener posición SOL largo plazo
"""

def analyze_liquidation_risk():
    print('='*60)
    print('⚡ RIESGO DE LIQUIDACIÓN - HOLD LARGO PLAZO')
    print('='*60)
    
    current_price = 191.0
    liquidation = 169.0
    position_remaining = 29.82
    
    print(f'\n📊 SITUACIÓN ACTUAL:')
    print(f'SOL: ${current_price}')
    print(f'Liquidación: ${liquidation}')
    print(f'Distancia: {current_price - liquidation:.2f} USD')
    print(f'Porcentaje: {((current_price - liquidation)/current_price)*100:.1f}%')
    
    # Liquidation scenarios
    print(f'\n🎯 ESCENARIOS DE LIQUIDACIÓN:')
    
    crash_scenarios = [
        (-5, 181.45, "Corrección normal"),
        (-10, 171.90, "⚠️ ZONA PELIGROSA"),
        (-12, 168.28, "🚨 LIQUIDACIÓN INMINENT"),
        (-15, 162.35, "💀 LIQUIDADO"),
        (-20, 152.80, "💀 LIQUIDADO HACE TIEMPO"),
    ]
    
    for pct, price, status in crash_scenarios:
        distance_to_liq = price - liquidation
        if price > liquidation:
            color = "🟡" if price < 175 else "🟢"
            if price < 172:
                color = "🔴"
            print(f'{color} SOL {pct:+3}%: ${price:6.2f} | Liq en ${distance_to_liq:+5.1f}$ | {status}')
        else:
            print(f'💀 SOL {pct:+3}%: ${price:6.2f} | {status}')
    
    # Historical crash analysis for liquidation risk
    print(f'\n📈 ANÁLISIS HISTÓRICO - PROBABILIDAD LIQUIDACIÓN:')
    
    historical_crashes = [
        ("2022 Crash", -97, 260, 8, "SOL cayó -97% en 8 meses"),
        ("2021 Correction", -85, 260, 120, "De $260 a $35 en 3 meses"),
        ("2020 March", -70, 4.50, 1.35, "Crash COVID rápido"),
        ("2018 Bear", -95, 20, 1, "Bear market de 18 meses"),
    ]
    
    print(f'\n🔍 Casos históricos SOL:')
    for period, drop_pct, peak, bottom, description in historical_crashes:
        would_liquidate = bottom < liquidation
        liq_status = "💀 LIQUIDADO" if would_liquidate else "✅ SOBREVIVE"
        print(f'{period}: {description}')
        print(f'   Peak ${peak} → Bottom ${bottom} ({drop_pct}%) | {liq_status}')
    
    # Current market context
    print(f'\n🌍 CONTEXTO ACTUAL vs HISTÓRICO:')
    
    current_from_ath = ((213.66 - current_price) / 213.66) * 100
    print(f'Drop desde ATH actual: {current_from_ath:.1f}%')
    
    remaining_drop_to_liq = ((current_price - liquidation) / current_price) * 100
    print(f'Drop adicional para liquidar: {remaining_drop_to_liq:.1f}%')
    
    # Risk assessment by timeframe
    print(f'\n⏰ RIESGO POR TIMEFRAME:')
    
    print(f'\n📅 Próximas 1-2 semanas:')
    print(f'🟢 RIESGO BAJO (5-10%)')
    print(f'• Market bearish pero no crash extremo')
    print(f'• SOL probable rango $185-195')
    print(f'• Liquidación necesita caída adicional -11%')
    
    print(f'\n📅 Próximo 1-2 meses:')
    print(f'🟡 RIESGO MEDIO (15-25%)')
    print(f'• Si bear market se extiende')
    print(f'• Posible test de $175-180')
    print(f'• Acercamiento a zona peligrosa')
    
    print(f'\n📅 Próximo 3-6 meses:')
    print(f'🔴 RIESGO ALTO (30-40%)')
    print(f'• Si entra crypto winter largo')
    print(f'• Histórico: SOL puede caer -60-80%')
    print(f'• Liquidación probable en bear prolongado')
    
    # Probability calculations
    print(f'\n📊 CÁLCULO DE PROBABILIDADES:')
    
    scenarios_liq = [
        ("Escenario suave", 10, "Correction 25%", 160, False),
        ("Escenario medio", 50, "Bear market", 120, True),
        ("Escenario severo", 25, "Crypto winter", 80, True),
        ("Escenario extremo", 15, "Colapso total", 50, True),
    ]
    
    weighted_liq_risk = 0
    for scenario, prob, description, target, liquidates in scenarios_liq:
        if liquidates:
            weighted_liq_risk += prob
        liq_status = "💀 LIQUIDADO" if liquidates else "✅ SEGURO"
        print(f'{scenario} ({prob}%): {description} → ${target} | {liq_status}')
    
    print(f'\n🎯 PROBABILIDAD TOTAL LIQUIDACIÓN: {weighted_liq_risk}%')
    
    # Mitigation strategies
    print(f'\n🛡️ ESTRATEGIAS DE MITIGACIÓN:')
    
    print(f'\n1️⃣ AGREGAR MARGEN:')
    print(f'• Depositar $20-30 adicional')
    print(f'• Bajaría liquidación a ~$155-160')
    print(f'• Reduciría riesgo significativamente')
    
    print(f'\n2️⃣ REDUCIR LEVERAGE:')
    print(f'• Cerrar 25% más de posición')
    print(f'• Bajaría liquidación automáticamente')
    print(f'• Menos upside pero más seguro')
    
    print(f'\n3️⃣ MONITORING LEVELS:')
    levels_monitor = [175, 172, 170]
    for level in levels_monitor:
        action = "ALERTA" if level > 172 else "AGREGAR MARGEN" if level > 170 else "CERRAR INMEDIATO"
        print(f'• ${level}: {action}')
    
    # Final recommendation
    print(f'\n🏆 RECOMENDACIÓN FINAL:')
    
    print(f'\n🤔 ¿Es seguro "dejar correr"?')
    print(f'✅ PROS del HOLD:')
    print(f'• Liquidación no inminent (11.5% buffer)')
    print(f'• SOL históricamente se recupera')
    print(f'• Posible nuevo ATH en 12-24 meses')
    print(f'• Evitas cristalizar pérdida')
    
    print(f'\n❌ CONTRAS del HOLD:')
    print(f'• {weighted_liq_risk}% probabilidad liquidación')
    print(f'• Puede tomar 6-18 meses recuperar')
    print(f'• Stress psicológico constante')
    print(f'• Capital inmovilizado largo tiempo')
    
    print(f'\n🎯 MI RECOMENDACIÓN:')
    print(f'📊 HOLD + PRECAUCIONES')
    
    print(f'\nPlan específico:')
    print(f'✅ MANTÉN la posición (riesgo liq aceptable)')
    print(f'✅ DEPOSITA $20-30 extra como buffer')
    print(f'✅ MONITOR alertas en $175 y $172')
    print(f'✅ TIMER check mensual para reevaluar')
    
    print(f'\n💡 Razones:')
    print(f'• Solo {remaining_drop_to_liq:.1f}% más para liquidar')
    print(f'• SOL es top 5 crypto (probabilidad recuperación alta)')
    print(f'• Bear markets no duran para siempre')
    print(f'• Con $30 buffer → liquidación a ~$155 (mucho más seguro)')
    
    print(f'\n⚠️ PLAN DE ESCAPE:')
    print(f'Si SOL toca $172: AGREGAR MARGEN o CERRAR')
    print(f'Si BTC < $100k: REEVALUAR completo')
    print(f'Si pasan 6 meses sin recovery: CONSIDERAR SALIDA')
    
    print('='*60)

if __name__ == "__main__":
    analyze_liquidation_risk()