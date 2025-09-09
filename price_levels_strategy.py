#!/usr/bin/env python3
"""
Niveles clave de SOL para reconsiderar estrategia
"""

def analyze_key_levels():
    print('='*60)
    print('🎯 NIVELES CLAVE PARA RECONSIDERAR ESTRATEGIA SOL')
    print('='*60)
    
    current_price = 192.59
    position_size = 59.64
    available_cash = 130.0
    
    print(f'\n📊 SITUACIÓN ACTUAL:')
    print(f'SOL: ${current_price}')
    print(f'Posición actual: ${position_size} USD')
    print(f'Cash disponible: ${available_cash} USD')
    
    print(f'\n🎯 NIVELES CRÍTICOS DE DECISIÓN:')
    
    # BEARISH LEVELS (Downside)
    print(f'\n🔴 NIVELES BEARISH (HACIA ABAJO):')
    
    print(f'\n💰 $190.00 - PRIMERA ALERTA')
    print(f'Acción: EVALUAR STOP LOSS para posición actual')
    print(f'- Pérdida adicional: -${(current_price-190)*position_size/current_price:.1f}')
    print(f'- Distancia: {((current_price-190)/current_price)*100:.1f}%')
    print(f'- Reason: Soporte psicológico importante')
    
    print(f'\n💸 $187.50 - ZONA DE LIQUIDACIONES')
    print(f'Acción: PRIMERA OPORTUNIDAD DE RECOMPRA')
    print(f'- Recompra sugerida: $20-30 USD')
    print(f'- Probabilidad rebote: 60%')
    print(f'- Risk/Reward: 1:2')
    print(f'- Reason: Liquidaciones masivas 25x longs')
    
    print(f'\n🚨 $185.00 - ZONA DE ALTO VALOR')
    print(f'Acción: RECOMPRA MODERADA ($40-50)')
    print(f'- Probabilidad rebote: 70%')
    print(f'- Target rebote: $195-200')
    print(f'- Risk/Reward: 1:3')
    print(f'- Reason: Liquidaciones 20x + soporte técnico')
    
    print(f'\n⚠️ $180.00 - MEGA OPORTUNIDAD')
    print(f'Acción: RECOMPRA AGRESIVA ($60-80)')
    print(f'- Probabilidad rebote: 80%')
    print(f'- Target rebote: $200-210')
    print(f'- Risk/Reward: 1:4')
    print(f'- Reason: Liquidaciones masivas 10x longs')
    
    print(f'\n🔥 $175.00 - COMPRA DE PÁNICO')
    print(f'Acción: ALL-IN DISPONIBLE')
    print(f'- Usar todo el cash restante')
    print(f'- Probabilidad rebote: 85%')
    print(f'- Target: $190-200 (+8-14%)')
    print(f'- Reason: Oversold extremo')
    
    # BULLISH LEVELS (Upside)
    print(f'\n🟢 NIVELES BULLISH (HACIA ARRIBA):')
    
    print(f'\n📈 $195.00 - PRIMERA RESISTENCIA')
    print(f'Acción: MANTENER posición actual')
    print(f'- Si rechaza: Normal pullback')
    print(f'- Si rompe: Momentum alcista')
    print(f'- Ganancia actual: +${(195-current_price)*position_size/current_price:.1f}')
    
    print(f'\n🎯 $197.00 - ZONA CRÍTICA')
    print(f'Acción: CONSIDERAR CERRAR 25% MÁS')
    print(f'- Reducir riesgo antes de MA(25)')
    print(f'- Preservar ganancias parciales')
    print(f'- Reason: Resistencia técnica fuerte')
    
    print(f'\n✅ $200.00 - BREAKEVEN ZONE')
    print(f'Acción: CERRAR 50-75% DE POSICIÓN')
    print(f'- Recuperar capital invertido')
    print(f'- Mantener solo position runner')
    print(f'- Ganancia: ~Breakeven en posición original')
    
    print(f'\n🚀 $205.00 - MOMENTUM CONFIRMADO')
    print(f'Acción: MANTENER position runner')
    print(f'- Market showing recovery')
    print(f'- Possible continuation to $210-215')
    print(f'- Trail stop loss at $200')
    
    # BTC DEPENDENCY
    print(f'\n₿ DEPENDENCIA DE BTC:')
    
    print(f'\n🔴 Si BTC < $108,000:')
    print(f'- SOL probable a $185-190')
    print(f'- Usar niveles bearish arriba')
    print(f'- Más conservador en recompras')
    
    print(f'\n🟢 Si BTC > $112,000:')
    print(f'- SOL puede ir a $200+')
    print(f'- Usar niveles bullish arriba')
    print(f'- Más agresivo manteniendo posiciones')
    
    # TIMING CONSIDERATIONS
    print(f'\n⏰ CONSIDERACIONES DE TIEMPO:')
    
    print(f'\n📅 Próximas 4-8 horas:')
    print(f'- Market consolidation expected')
    print(f'- Watch for $190 break or $195 reclaim')
    print(f'- Volume will confirm direction')
    
    print(f'\n📅 Próximas 12-24 horas:')
    print(f'- Macro factors may change')
    print(f'- US market open impact')
    print(f'- Fed expectations updates')
    
    # RISK MANAGEMENT
    print(f'\n🛡️ GESTIÓN DE RIESGO:')
    
    print(f'\n📏 REGLAS DE POSITION SIZING:')
    print(f'- Recompra $187.50: Max $30 (23% of cash)')
    print(f'- Recompra $185.00: Max $50 (38% of cash)')
    print(f'- Recompra $180.00: Max $80 (62% of cash)')
    print(f'- Emergency $175.00: All-in remaining')
    
    print(f'\n🚫 STOP LOSS RULES:')
    print(f'- Current position: Stop at $188-190')
    print(f'- New buys: Stop 3-4% below entry')
    print(f'- Never risk more than 50% total portfolio')
    
    print(f'\n💡 PSYCHOLOGICAL LEVELS:')
    print(f'- $200: Major psychological resistance')
    print(f'- $190: Support (round number)')
    print(f'- $180: Panic selling zone')
    print(f'- $175: Capitulation bottom')
    
    # SUMMARY RECOMMENDATIONS
    print(f'\n🏆 RESUMEN DE RECOMENDACIONES:')
    
    print(f'\n🎯 ACCIÓN INMEDIATA (Próximas horas):')
    print(f'✅ MANTENER posición actual ($59.64)')
    print(f'✅ WATCH $190 level closely')
    print(f'✅ PREPARE buy orders at $187.50')
    print(f'✅ MONITOR BTC $108k support')
    
    print(f'\n📈 SI SUBE (SOL > $195):')
    print(f'• Monitor for rejection at $197')
    print(f'• Consider partial close at $200')
    print(f'• Trail stop if breaks $205')
    
    print(f'\n📉 SI BAJA (SOL < $190):')
    print(f'• Activate buy ladder strategy')
    print(f'• Start with $25-30 at $187.50')
    print(f'• Increase size as price drops')
    print(f'• Max risk: $130 cash available')
    
    print('='*60)

if __name__ == "__main__":
    analyze_key_levels()