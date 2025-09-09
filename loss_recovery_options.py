#!/usr/bin/env python3
"""
Opciones de recuperación para posición SOL con pérdida -$42 USD
"""

def analyze_options():
    print('='*60)
    print('🔥 OPCIONES DE RECUPERACIÓN - PÉRDIDA $42 USD')
    print('='*60)
    
    # Current situation
    current_price = 192.44
    entry_price = 198.20
    loss_usd = 42
    liquidation = 169.0
    
    print(f'\n📊 SITUACIÓN ACTUAL:')
    print(f'SOL: ${current_price}')
    print(f'Entrada: ${entry_price}')
    print(f'Pérdida: -${loss_usd} USD')
    print(f'Liquidación: ${liquidation}')
    print(f'Distancia a liq: {((current_price - liquidation)/current_price)*100:.1f}%')
    
    print(f'\n🎯 OPCIONES DISPONIBLES:')
    
    # OPTION 1: HOLD
    print(f'\n1️⃣ MANTENER (HOLD):')
    print(f'✅ Pros:')
    print(f'   • Posible rebote técnico desde $192')
    print(f'   • RSI oversold -> probable bounce')
    print(f'   • Liquidación lejana (13.9%)')
    print(f'   • No cristalizar pérdida')
    
    print(f'❌ Contras:')
    print(f'   • Market bearish dominante')
    print(f'   • BTC débil por factores macro')
    print(f'   • Puede ir a $187-190 (-5% adicional)')
    print(f'   • Tiempo incierto de recuperación')
    
    print(f'🎲 Probabilidad éxito: 40%')
    print(f'🎯 Target realista: $195-197 (recuperar -$15-25)')
    
    # OPTION 2: CLOSE NOW
    print(f'\n2️⃣ CERRAR AHORA:')
    print(f'✅ Pros:')
    print(f'   • Preservar capital restante')
    print(f'   • Evitar pérdidas mayores')
    print(f'   • Liberar margin para nuevas oportunidades')
    print(f'   • Sleep better at night')
    
    print(f'❌ Contras:')
    print(f'   • Cristalizar pérdida -$42')
    print(f'   • Perder posible rebote')
    print(f'   • FOMO si SOL rebota después')
    
    print(f'💰 Pérdida final: -$42 USD (-2.8% del capital)')
    print(f'💸 Capital preservado: ~$208 USD')
    
    # OPTION 3: PARTIAL CLOSE
    print(f'\n3️⃣ CERRAR PARCIAL (50%):')
    print(f'✅ Pros:')
    print(f'   • Reducir riesgo a la mitad')
    print(f'   • Preservar algo de capital')
    print(f'   • Mantener exposure para rebote')
    print(f'   • Psicológicamente más fácil')
    
    print(f'❌ Contras:')
    print(f'   • Cristalizar pérdida parcial')
    print(f'   • Complejidad de management')
    
    print(f'💰 Pérdida cristalizada: -$21 USD')
    print(f'📊 Exposure restante: 50% del original')
    
    # OPTION 4: AVERAGE DOWN
    print(f'\n4️⃣ PROMEDIAR HACIA ABAJO:')
    print(f'⚠️ ALTO RIESGO - NO RECOMENDADO')
    print(f'❌ Contras:')
    print(f'   • Duplicar el riesgo')
    print(f'   • Market bearish confirmado')
    print(f'   • Puede empeorar pérdidas')
    print(f'   • Acercarse más a liquidación')
    
    print(f'🚫 NO RECOMENDADO en market bearish')
    
    # OPTION 5: HEDGING
    print(f'\n5️⃣ HEDGE CON SHORT:')
    print(f'✅ Pros:')
    print(f'   • Neutralizar dirección')
    print(f'   • Ganar si sigue bajando')
    print(f'   • Mantener posición original')
    
    print(f'❌ Contras:')
    print(f'   • Complejidad alta')
    print(f'   • Fees adicionales')
    print(f'   • Risk management difícil')
    
    print(f'📝 Setup: SHORT $50-75 posición')
    print(f'🎯 Target SHORT: $187-190')
    
    # RECOMMENDATIONS
    print(f'\n🏆 RECOMENDACIONES POR ESCENARIO:')
    
    print(f'\n🔴 SI ERES RISK AVERSE:')
    print(f'✅ CERRAR AHORA')
    print(f'• Pérdida controlada: -$42')
    print(f'• Preserve capital para mejores oportunidades')
    print(f'• Market conditions no favorables')
    
    print(f'\n🟡 SI QUIERES BALANCE:')
    print(f'✅ CERRAR 50%')
    print(f'• Reduce riesgo pero mantiene upside')
    print(f'• Pérdida parcial: -$21')
    print(f'• Psychological relief')
    
    print(f'\n🟢 SI ERES RISK TOLERANT:')
    print(f'✅ MANTENER + STOP LOSS')
    print(f'• Stop loss en $190 (-$32 adicionales)')
    print(f'• Target rebote: $195-197')
    print(f'• Monitor BTC closely')
    
    print(f'\n📊 MI RECOMENDACIÓN PERSONAL:')
    print(f'🎯 CERRAR 50% AHORA')
    print(f'Razones:')
    print(f'• Market bearish confirmado (6/6 cryptos red)')
    print(f'• BTC weakness por factores macro')
    print(f'• Preserve 50% capital')
    print(f'• Reduce psychological stress')
    print(f'• Mantiene upside potential con menos risk')
    
    print(f'\n⏱️ TIMING:')
    print(f'• Si decides mantener: pon stop en $190')
    print(f'• Si decides cerrar: hazlo pronto (antes de más caída)')
    print(f'• Monitor BTC $108k nivel crítico')
    
    print(f'\n💡 LECCIÓN APRENDIDA:')
    print(f'• Market bearish + macro headwinds = reduce positions')
    print(f'• Position sizing más conservador en momentos así')
    print(f'• Consider market conditions antes de entries')
    
    print('='*60)

if __name__ == "__main__":
    analyze_options()