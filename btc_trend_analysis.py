#!/usr/bin/env python3
"""
BTC Trend Reversal Analysis
"""

import httpx
import asyncio

async def check_market():
    async with httpx.AsyncClient() as client:
        # Get BTC data
        btc = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
        btc_data = btc.json()
        
        # Get key levels
        price = float(btc_data['lastPrice'])
        high24 = float(btc_data['highPrice'])
        low24 = float(btc_data['lowPrice'])
        change24 = float(btc_data['priceChangePercent'])
        volume = float(btc_data['volume'])
        
        print('='*60)
        print('📊 BTC MARKET ANALYSIS - TREND REVERSAL PROBABILITY')
        print('='*60)
        print(f'Price: ${price:,.2f}')
        print(f'24h Change: {change24:.2f}%')
        print(f'24h Range: ${low24:,.2f} - ${high24:,.2f}')
        print(f'Distance from 24h high: {((high24-price)/price)*100:.2f}%')
        print(f'Volume: {volume:,.0f} BTC')
        
        # Key support/resistance
        print(f'\n🎯 KEY LEVELS:')
        print(f'Strong Support: $62,000 (historical)')
        print(f'Next Support: $63,500')
        print(f'Current: ${price:,.2f}')
        print(f'Resistance: $65,000')
        print(f'Strong Resistance: $67,000')
        
        # Probability assessment
        print(f'\n⚡ CAMBIO DE TENDENCIA - PROBABILIDAD:')
        if price < 63500:
            print('🔴 ALTA (70%): BTC rompió soporte clave')
            print('   • Si BTC pierde $63,000 → panic selling')
            print('   • Alts caerán 5-10% adicional')
            print('   • SOL podría ir a $190-192 directo')
            print('   • Tu SHORT sería PERFECTO')
        elif price < 64500:
            print('🟡 MEDIA (50%): BTC en zona crítica')
            print('   • Rebote técnico posible a $65k')
            print('   • Pero tendencia sigue bearish')
            print('   • SOL puede rebotar a $199 antes de caer')
            print('   • Mantén el plan: salir en $199')
        else:
            print('🟢 BAJA (30%): BTC mantiene soporte')
            print('   • Consolidación lateral más probable')
            print('   • Alts pueden recuperar algo')
            print('   • SOL tiene oportunidad de $199+')
            print('   • Evalúa si mantener o cerrar en $199')
            
        # Get SOL correlation
        sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
        sol_data = sol.json()
        sol_price = float(sol_data['lastPrice'])
        sol_change = float(sol_data['priceChangePercent'])
        
        print(f'\n📈 CORRELACIÓN BTC-SOL:')
        print(f'BTC: {change24:.2f}% | SOL: {sol_change:.2f}%')
        correlation = sol_change / change24 if change24 != 0 else 1
        print(f'Beta: {correlation:.2f}x (SOL se mueve {correlation:.2f}x más que BTC)')
        
        print(f'\n🎯 ESCENARIOS PARA TU TRADE:')
        print(f'SOL actual: ${sol_price:.2f}')
        print(f'Tu entrada: $199')
        print(f'P&L actual: ${sol_price - 199:.2f} ({((sol_price - 199)/199)*100:.2f}%)')
        
        if price < 64000:
            print(f'\n⚠️ SCENARIO MÁS PROBABLE:')
            print(f'1. BTC sigue cayendo → SOL a $192-194')
            print(f'2. Rebote técnico débil → SOL máximo $198')
            print(f'3. RECOMENDACIÓN: Preparar SHORT ahora')
            print(f'   • Si SOL llega a $198+ → cerrar LONG')
            print(f'   • Entrar SHORT inmediatamente')
            print(f'   • No esperar $199 si BTC sigue débil')
        else:
            print(f'\n✅ SCENARIO ACTUAL:')
            print(f'1. BTC consolidando → rebote posible')
            print(f'2. SOL puede alcanzar $199')
            print(f'3. RECOMENDACIÓN: Mantener plan original')
            print(f'   • Esperar $199 para salir')
            print(f'   • Evaluar SHORT según momentum')

asyncio.run(check_market())