#!/usr/bin/env python3
"""
Estrategia: ¿Programar recompras o solo mantener posición actual?
Análisis completo con cash disponible y niveles óptimos
"""

def analyze_recompra_strategy():
    print('='*60)
    print('💰 ESTRATEGIA: RECOMPRA vs SOLO HOLD')
    print('='*60)
    
    current_price = 191.0
    liquidation = 152.05
    current_position = 29.82  # 50% restante
    available_cash = 130.0    # Cash disponible
    breakeven_current = 204.0
    
    print(f'\n📊 SITUACIÓN ACTUAL:')
    print(f'SOL precio: ${current_price}')
    print(f'Posición actual: ${current_position} (50% restante)')
    print(f'Cash disponible: ${available_cash}')
    print(f'Breakeven actual: ${breakeven_current}')
    print(f'Liquidación: ${liquidation}')
    print(f'Buffer liquidación: {((current_price - liquidation)/current_price)*100:.1f}%')
    
    print(f'\n🎯 OPCIÓN 1: SOLO HOLD (No recompra)')
    print(f'✅ Pros:')
    print(f'   • Sin riesgo adicional')
    print(f'   • Preserve cash para otras oportunidades')
    print(f'   • Menos complejidad')
    print(f'   • Liquidación lejana (20% buffer)')
    
    print(f'❌ Contras:')
    print(f'   • Breakeven alto ($204)')
    print(f'   • Recovery lenta con solo 50% position')
    print(f'   • Pierdes oportunidad de promediar down')
    print(f'   • No optimizas el cash disponible')
    
    # Scenarios for hold-only
    recovery_scenarios_hold = [
        (195, -4.4, "Rebote técnico"),
        (200, -2.0, "Resistance break"),
        (204, 0.0, "Breakeven!"),
        (210, +2.9, "New momentum"),
    ]
    
    print(f'\n📈 Escenarios HOLD-ONLY:')
    for price, pnl_pct, description in recovery_scenarios_hold:
        pnl_usd = (price - breakeven_current) * (current_position / current_price)
        print(f'   SOL ${price}: {pnl_pct:+.1f}% (${pnl_usd:+.1f}) | {description}')
    
    print(f'\n🎯 OPCIÓN 2: RECOMPRA PROGRAMADA')
    
    # Optimal recompra levels based on technical analysis
    recompra_levels = [
        (187, 25, "Primera liquidación masiva", 0.70),
        (183, 30, "Soporte técnico fuerte", 0.75), 
        (175, 35, "Zona de pánico selling", 0.80),
        (165, 40, "Oversold extremo", 0.85),
    ]
    
    print(f'\n💰 PLAN DE RECOMPRAS SUGERIDO:')
    total_recompra = 0
    weighted_avg_entry = current_price * current_position
    
    for level, amount, reason, success_prob in recompra_levels:
        if amount <= available_cash - total_recompra:
            total_recompra += amount
            weighted_avg_entry += level * amount
            distance = ((current_price - level) / current_price) * 100
            print(f'   ${level}: ${amount} USD | -{distance:.1f}% | {reason}')
            print(f'      Prob rebote: {success_prob*100:.0f}%')
        else:
            remaining = available_cash - total_recompra
            if remaining > 0:
                weighted_avg_entry += level * remaining
                total_recompra += remaining
                distance = ((current_price - level) / current_price) * 100
                print(f'   ${level}: ${remaining} USD | -{distance:.1f}% | {reason} (FINAL)')
                break
    
    # Calculate new breakeven with recompras
    if total_recompra > 0:
        total_position_value = weighted_avg_entry + (breakeven_current * current_position)
        total_position_size = current_position + total_recompra
        new_breakeven = total_position_value / total_position_size
    else:
        new_breakeven = breakeven_current
        total_position_size = current_position
    
    print(f'\n📊 RESULTADO CON RECOMPRAS:')
    print(f'Total a invertir adicional: ${total_recompra}')
    print(f'Nuevo tamaño posición: ${total_position_size:.1f}')
    print(f'Nuevo breakeven: ${new_breakeven:.2f}')
    print(f'Mejora breakeven: ${breakeven_current - new_breakeven:.2f}')
    
    # Recovery scenarios with recompras
    print(f'\n📈 Escenarios CON RECOMPRAS:')
    recovery_scenarios_recompra = [
        (195, "Rebote técnico"),
        (200, "Resistance break"),
        (new_breakeven, "NUEVO Breakeven"),
        (210, "Strong momentum"),
    ]
    
    for price, description in recovery_scenarios_recompra:
        pnl_usd = (price - new_breakeven) * (total_position_size / price)
        pnl_pct = ((price / new_breakeven) - 1) * 100
        marker = "🎯" if abs(price - new_breakeven) < 1 else ""
        print(f'   SOL ${price}: {pnl_pct:+.1f}% (${pnl_usd:+.1f}) | {description} {marker}')
    
    # Risk analysis
    print(f'\n⚠️ ANÁLISIS DE RIESGOS:')
    
    # New liquidation risk with additional position
    if total_recompra > 0:
        # Estimate new liquidation (approximated)
        leverage_increase = total_position_size / current_position
        new_liquidation_approx = liquidation / leverage_increase * 0.85  # Conservative estimate
        
        print(f'\n🔴 Riesgos con RECOMPRAS:')
        print(f'   • Inversión total: ${total_recompra + current_position:.1f}')
        print(f'   • Liquidación aproximada: ${new_liquidation_approx:.1f}')
        print(f'   • Si SOL sigue cayendo: pérdidas mayores')
        print(f'   • Menos cash para otras oportunidades')
        
        liq_buffer_new = ((current_price - new_liquidation_approx) / current_price) * 100
        print(f'   • Nuevo buffer liquidación: {liq_buffer_new:.1f}%')
    
    print(f'\n🟢 Beneficios con RECOMPRAS:')
    print(f'   • Breakeven baja ${breakeven_current - new_breakeven:.2f}')
    print(f'   • Recovery más rápida si rebota')
    print(f'   • Aprovecha precios baratos')
    print(f'   • Psychological benefit (promedio down)')
    
    # Market timing consideration
    print(f'\n⏰ CONSIDERACIONES DE TIMING:')
    
    print(f'\n🔍 Market Conditions:')
    print(f'   • BTC débil → SOL seguirá débil')
    print(f'   • 6/6 cryptos en rojo → sentiment bearish')
    print(f'   • Weekend → volumen bajo')
    print(f'   • Probability más caída: 65%')
    
    print(f'\n📅 Timeline probable:')
    print(f'   • Próximas 24-48h: Test $185-187')
    print(f'   • Próxima semana: Posible $180-183')
    print(f'   • Si bear continúa: $175 posible')
    
    # RECOMMENDATION
    print(f'\n🏆 MI RECOMENDACIÓN:')
    print(f'🎯 RECOMPRA GRADUAL (Ladder Strategy)')
    
    # Optimized ladder
    optimal_ladder = [
        (185, 30, "Wait for first test"),
        (180, 40, "Strong technical level"),
        (175, 50, "If available and confirmed bear"),
    ]
    
    print(f'\nPlan Optimizado:')
    ladder_total = 0
    for price, amount, reason in optimal_ladder:
        if ladder_total + amount <= available_cash:
            ladder_total += amount
            distance = ((current_price - price) / current_price) * 100
            print(f'✅ ${price}: ${amount} USD (-{distance:.1f}%) | {reason}')
        else:
            remaining = available_cash - ladder_total
            if remaining >= 20:  # Minimum viable amount
                distance = ((current_price - price) / current_price) * 100
                print(f'✅ ${price}: ${remaining} USD (-{distance:.1f}%) | {reason}')
                ladder_total += remaining
                break
    
    print(f'\nTotal ladder: ${ladder_total} de ${available_cash} disponible')
    
    # Calculate optimal new breakeven
    if ladder_total > 0:
        # Weighted average calculation for ladder
        optimal_weighted = current_price * current_position
        ladder_weighted = 0
        ladder_amount_total = 0
        
        for price, amount, _ in optimal_ladder:
            if ladder_amount_total + amount <= available_cash:
                optimal_weighted += price * amount
                ladder_weighted += amount
                ladder_amount_total += amount
            else:
                remaining = available_cash - ladder_amount_total
                if remaining >= 20:
                    optimal_weighted += price * remaining
                    ladder_weighted += remaining
                break
        
        optimal_breakeven = optimal_weighted / (current_position + ladder_weighted)
        
        print(f'\n📊 RESULTADO LADDER OPTIMIZADO:')
        print(f'Breakeven actual: ${breakeven_current:.2f}')
        print(f'Nuevo breakeven: ${optimal_breakeven:.2f}')
        print(f'Mejora: ${breakeven_current - optimal_breakeven:.2f} ({((breakeven_current - optimal_breakeven)/breakeven_current)*100:.1f}%)')
    
    print(f'\n💡 RAZONES PARA LADDER:')
    print(f'• Market bearish confirmado → probable más caída')
    print(f'• Aprovechas DCA en niveles técnicos')
    print(f'• Reduces breakeven significativamente')
    print(f'• Mantienes algo de cash como buffer')
    print(f'• Psychological: "buying the dips"')
    
    print(f'\n⚡ EJECUCIÓN:')
    print(f'1. MANTÉN posición actual')
    print(f'2. CONFIGURA buy orders en $185, $180, $175')
    print(f'3. MONITOR BTC como leading indicator')
    print(f'4. ADJUST orders si market conditions cambian')
    
    print(f'\n🚨 STOP CONDITIONS:')
    print(f'• Si BTC > $112k: CANCEL buy orders (market may recover)')
    print(f'• Si SOL > $195: CANCEL lower orders')
    print(f'• Si cash < $30: STOP adding (preserve emergency fund)')
    
    print('='*60)

if __name__ == "__main__":
    analyze_recompra_strategy()