#!/usr/bin/env python3
"""
Estrategia para manejar el 50% restante de la posición SOL
Breakeven actual: $204 - Precio actual: ~$191
"""

def analyze_remaining_position():
    print('='*60)
    print('🎯 ESTRATEGIA PARA 50% RESTANTE - SOL POSITION')
    print('='*60)
    
    current_price = 191.0
    breakeven_new = 204.0
    liquidation = 169.0
    remaining_position = 29.82  # ~50% del original
    
    print(f'\n📊 SITUACIÓN ACTUAL:')
    print(f'SOL: ${current_price}')
    print(f'Tu breakeven: ${breakeven_new}')
    print(f'Pérdida actual: ${current_price - breakeven_new:.2f} (-${abs(current_price - breakeven_new):.2f})')
    print(f'Liquidación: ${liquidation}')
    print(f'Posición restante: ${remaining_position} USD')
    print(f'Distancia a liquidación: {((current_price - liquidation)/current_price)*100:.1f}%')
    
    print(f'\n🎯 OPCIONES DISPONIBLES:')
    
    # OPTION 1: HOLD & HOPE
    print(f'\n1️⃣ MANTENER Y ESPERAR REBOTE:')
    print(f'✅ Pros:')
    print(f'   • Rebote técnico posible a $195-197')
    print(f'   • RSI oversold puede generar bounce')
    print(f'   • No cristalizar más pérdidas')
    print(f'   • Liquidación lejana ({((current_price - liquidation)/current_price)*100:.1f}%)')
    
    print(f'❌ Contras:')
    print(f'   • Breakeven muy alto ($204)')
    print(f'   • Market bearish confirmado')
    print(f'   • Posible caída a $185-187')
    print(f'   • Tiempo de recuperación incierto')
    
    rebote_target = 196
    loss_at_rebote = rebote_target - breakeven_new
    print(f'🎯 Si rebota a ${rebote_target}: Pérdida ${loss_at_rebote:.2f} (-${abs(loss_at_rebote):.2f})')
    print(f'📊 Probabilidad rebote > $195: 60%')
    print(f'⏱️ Timeframe: 12-24 horas')
    
    # OPTION 2: CLOSE NOW
    print(f'\n2️⃣ CERRAR AHORA:')
    print(f'✅ Pros:')
    print(f'   • Evitar pérdidas mayores')
    print(f'   • Preservar capital restante')
    print(f'   • Liberar margin para nuevas oportunidades')
    print(f'   • Paz mental')
    
    print(f'❌ Contras:')
    print(f'   • Cristalizar pérdida grande')
    print(f'   • FOMO si rebota después')
    print(f'   • No recuperar el -$6.20 del primer 50%')
    
    total_loss = (current_price - breakeven_new) * (remaining_position / current_price)
    print(f'💰 Pérdida total: ${total_loss:.2f}')
    print(f'💸 Capital preservado: ${remaining_position + total_loss:.2f}')
    
    # OPTION 3: TRAILING STOP
    print(f'\n3️⃣ TRAILING STOP LOSS:')
    print(f'✅ Setup recomendado:')
    print(f'   • Stop inicial: $189 (-1% desde actual)')
    print(f'   • Trail distance: $2-3')
    print(f'   • Si sube a $194 → stop se mueve a $191')
    print(f'   • Si sube a $197 → stop se mueve a $194')
    
    print(f'🎯 Ventajas:')
    print(f'   • Protege contra caídas bruscas')
    print(f'   • Permite capturar parte del rebote')
    print(f'   • Automatizado - menos emocional')
    
    # OPTION 4: HEDGE WITH SHORT
    print(f'\n4️⃣ HEDGE CON SHORT:')
    print(f'⚠️ Estrategia avanzada:')
    print(f'   • Abrir SHORT de $30-40 en SOL')
    print(f'   • Si baja más: SHORT compensa pérdida del LONG')
    print(f'   • Si sube: LONG mejora, cerrar SHORT con pérdida menor')
    
    print(f'❌ Riesgos:')
    print(f'   • Complejidad de management')
    print(f'   • Fees adicionales')
    print(f'   • Puede empeorar si se queda sideways')
    
    # OPTION 5: WAIT FOR SPECIFIC LEVELS
    print(f'\n5️⃣ ESPERAR NIVELES ESPECÍFICOS:')
    
    levels = [
        (195, "PRIMER TARGET - Cierra 25%", "Reduce riesgo parcialmente"),
        (200, "SEGUNDO TARGET - Cierra otro 25%", "Recupera parte de la inversión"), 
        (204, "BREAKEVEN - Evalúa cerrar todo", "Zero loss total"),
        (208, "PROFIT ZONE - Mantén o cierra", "Finally in green")
    ]
    
    print(f'📈 Plan escalonado:')
    for price, action, reason in levels:
        distance = ((price - current_price) / current_price) * 100
        print(f'   ${price}: {action} ({distance:+.1f}%)')
        print(f'      → {reason}')
    
    # MARKET CONDITIONS IMPACT
    print(f'\n📊 DEPENDENCIA DEL MERCADO:')
    
    print(f'\n🔴 Si BTC < $108k (Bearish scenario):')
    print(f'   • SOL probable a $185-188')
    print(f'   • Recomendación: CERRAR o TRAILING STOP tight')
    print(f'   • Time horizon: días/semanas')
    
    print(f'\n🟢 Si BTC > $110k (Recovery scenario):')
    print(f'   • SOL puede ir a $200+')
    print(f'   • Recomendación: MANTENER con targets')
    print(f'   • Time horizon: horas/días')
    
    # MY RECOMMENDATION
    print(f'\n🏆 MI RECOMENDACIÓN PERSONAL:')
    print(f'🎯 TRAILING STOP LOSS')
    
    print(f'\nSetup específico:')
    print(f'✅ Stop inicial: $189.50')
    print(f'✅ Trail distance: $2.50')
    print(f'✅ Si rebota a $195+ → dejar correr')
    print(f'✅ Si baja de $189.50 → SALIR')
    
    print(f'\n💡 Razones:')
    print(f'• Protege contra caída a $185-187')
    print(f'• Permite capturar rebote si ocurre')
    print(f'• Psicológicamente más fácil')
    print(f'• Reduce stress de monitoreo constante')
    print(f'• Si se ejecuta: pérdida ~$3-4 adicional vs cerrar ahora')
    
    print(f'\n⚖️ RISK/REWARD:')
    print(f'• Downside: -$3-4 adicional si se ejecuta stop')
    print(f'• Upside: +$5-13 si rebota a $196-204')
    print(f'• Ratio: 1:2 o 1:3 dependiendo del rebote')
    
    print(f'\n⏰ PRÓXIMAS 12-24 HORAS:')
    print(f'🎯 Niveles clave a observar:')
    print(f'• $194-195: Si rompe = posible continuar a $197-200')
    print(f'• $189-190: Si rompe = probable caída a $185-187')
    print(f'• Monitor BTC $108k como referencia macro')
    
    print('='*60)

if __name__ == "__main__":
    analyze_remaining_position()