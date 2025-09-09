#!/usr/bin/env python3
"""
Análisis de liquidaciones generadas en $192.50 y próximos niveles
"""

import httpx
import asyncio

async def analyze_liquidations():
    async with httpx.AsyncClient() as client:
        # Get current SOL data
        sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
        sol_data = sol.json()
        
        current_price = float(sol_data['lastPrice'])
        low_24h = float(sol_data['lowPrice'])
        high_24h = float(sol_data['highPrice'])
        volume = float(sol_data['quoteVolume'])
        
        print('='*60)
        print('🔥 ANÁLISIS DE LIQUIDACIONES SOL')
        print('='*60)
        
        print(f'\n📊 SITUACIÓN ACTUAL:')
        print(f'Precio actual: ${current_price:.2f}')
        print(f'Low 24h: ${low_24h:.2f}')
        print(f'High 24h: ${high_24h:.2f}')
        print(f'Volume 24h: ${volume/1e6:.1f}M')
        
        # Calculate liquidation zones
        resistance_hit = 192.50
        drop_from_high = ((high_24h - resistance_hit) / high_24h) * 100
        
        print(f'\n💥 LIQUIDACIONES EN ${resistance_hit:.2f}:')
        print(f'Caída desde high: {drop_from_high:.1f}%')
        
        # Estimate liquidations by leverage
        print(f'\n🎯 ESTIMACIÓN DE LIQUIDACIONES GENERADAS:')
        
        # Long positions liquidated at $192.50
        leverage_levels = [
            (5, 210.3),   # 5x longs liquidated if entered around $210
            (10, 202.8),  # 10x longs liquidated if entered around $203
            (20, 196.4),  # 20x longs liquidated if entered around $196
            (25, 195.5),  # 25x longs liquidated if entered around $195.5
            (50, 194.4),  # 50x longs liquidated if entered around $194.4
        ]
        
        total_estimated_liq = 0
        
        for leverage, entry_estimate in leverage_levels:
            if entry_estimate > resistance_hit:
                # Calculate how much was likely liquidated
                position_estimate = 50000 * (leverage / 10)  # Rough estimate
                total_estimated_liq += position_estimate
                
                print(f'  {leverage}x LONGS (entrada ~${entry_estimate:.1f}): ~${position_estimate:,.0f}')
        
        print(f'\n💸 TOTAL ESTIMADO LIQUIDADO: ~${total_estimated_liq:,.0f}')
        
        # Next resistance levels DOWN
        print(f'\n⬇️ PRÓXIMOS NIVELES DE LIQUIDACIÓN (HACIA ABAJO):')
        
        next_levels = [
            (190.0, "Psicológico + 100x longs desde $191"),
            (187.5, "25x longs desde $195 + soporte técnico"),
            (185.0, "20x longs desde $194"),  
            (180.0, "MEGA LIQUIDACIÓN - 10x longs desde $200"),
            (175.0, "5x longs desde $195"),
            (169.0, "TU LIQUIDACIÓN ⚠️"),
            (165.0, "Soporte histórico fuerte"),
            (160.0, "Liquidación masiva de longs antiguos"),
        ]
        
        for price, description in next_levels:
            distance = ((current_price - price) / current_price) * 100
            if price == 169.0:
                print(f'  ${price:.1f}: {description} (Distancia: {distance:.1f}%) 🚨')
            elif price > 175:
                print(f'  ${price:.1f}: {description} (Distancia: {distance:.1f}%) 🔴')
            else:
                print(f'  ${price:.1f}: {description} (Distancia: {distance:.1f}%)')
        
        # Volume analysis for liquidation cascade risk
        print(f'\n📈 RIESGO DE CASCADA DE LIQUIDACIONES:')
        
        if current_price > 188:
            risk_level = "🟢 BAJO"
            print(f'{risk_level}: Lejos de niveles críticos')
        elif current_price > 180:
            risk_level = "🟡 MEDIO"  
            print(f'{risk_level}: Acercándose a zona de $180-185')
        elif current_price > 175:
            risk_level = "🟠 ALTO"
            print(f'{risk_level}: En zona peligrosa - muchos 10x/20x en riesgo')
        else:
            risk_level = "🔴 CRÍTICO"
            print(f'{risk_level}: Cascada de liquidaciones probable')
        
        # Impact on your position
        print(f'\n💼 IMPACTO EN TU POSICIÓN:')
        your_liq = 169.0
        distance_to_liq = ((current_price - your_liq) / current_price) * 100
        
        print(f'Tu liquidación: ${your_liq}')
        print(f'Distancia actual: {distance_to_liq:.1f}%')
        
        if distance_to_liq > 15:
            print('✅ SEGURO: Muy lejos de liquidación')
        elif distance_to_liq > 10:
            print('🟡 PRECAUCIÓN: Monitorear $180 como nivel crítico')
        elif distance_to_liq > 5:
            print('🔴 PELIGRO: Considera reducir posición o cerrar')
        else:
            print('🚨 EMERGENCIA: Cierra posición INMEDIATAMENTE')
        
        print(f'\n🎯 CONCLUSIÓN:')
        print(f'• ${resistance_hit:.2f} generó liquidaciones masivas (~${total_estimated_liq:,.0f})')
        print(f'• Próximo nivel crítico: $187.5-190')
        print(f'• Tu posición está {distance_to_liq:.1f}% de liquidación')
        print(f'• Si rompe $185 → cascada probable hacia $180-175')

asyncio.run(analyze_liquidations())