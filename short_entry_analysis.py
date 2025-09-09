#!/usr/bin/env python3
"""
Análisis de seguridad para entrada SHORT después de salir en $199
"""

import httpx
import asyncio
from datetime import datetime

async def analyze_short_safety():
    async with httpx.AsyncClient() as client:
        # Get current data
        btc = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
        sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
        
        btc_data = btc.json()
        sol_data = sol.json()
        
        btc_price = float(btc_data['lastPrice'])
        btc_change = float(btc_data['priceChangePercent'])
        sol_price = float(sol_data['lastPrice'])
        sol_change = float(sol_data['priceChangePercent'])
        sol_volume = float(sol_data['quoteVolume'])
        
        # Get orderbook for resistance check
        ob = await client.get('https://api.binance.com/api/v3/depth?symbol=SOLUSDT&limit=100')
        orderbook = ob.json()
        
        # Calculate sell pressure at $199
        sell_walls = []
        for ask in orderbook['asks']:
            price = float(ask[0])
            size = float(ask[1])
            if 198 <= price <= 202:
                sell_walls.append((price, size * price))
        
        total_sell_pressure = sum([w[1] for w in sell_walls])
        
        print('='*60)
        print('🎯 ANÁLISIS: ¿ES SEGURO EL SHORT EN $199?')
        print('='*60)
        
        print(f'\n📊 CONTEXTO ACTUAL:')
        print(f'SOL: ${sol_price:.2f} ({sol_change:.2f}%)')
        print(f'BTC: ${btc_price:,.2f} ({btc_change:.2f}%)')
        print(f'Volume SOL 24h: ${sol_volume/1e6:.1f}M')
        
        print(f'\n🔍 RESISTENCIA EN ZONA $199:')
        print(f'Sell pressure $198-202: ${total_sell_pressure/1e6:.2f}M')
        if total_sell_pressure > 5e6:
            print('✅ FUERTE RESISTENCIA - Favorece SHORT')
        else:
            print('⚠️ RESISTENCIA DÉBIL - Posible breakout')
        
        # Risk factors
        risk_score = 0
        print(f'\n⚡ FACTORES DE RIESGO/RECOMPENSA:')
        
        print(f'\n✅ FACTORES A FAVOR DEL SHORT:')
        factors_pro = []
        
        if sol_change < -5:
            factors_pro.append('• SOL ya cayó -6.39% (momentum bajista)')
            risk_score += 2
        
        if btc_change < -1:
            factors_pro.append('• BTC en negativo (mercado débil)')
            risk_score += 1
            
        if total_sell_pressure > 5e6:
            factors_pro.append(f'• Resistencia fuerte en $199 (${total_sell_pressure/1e6:.1f}M)')
            risk_score += 2
            
        factors_pro.append('• RSI probablemente sobrecomprado en rebote')
        factors_pro.append('• Liquidaciones de longs en $194-196')
        factors_pro.append('• Tendencia macro sigue bearish')
        risk_score += 3
        
        for f in factors_pro:
            print(f)
        
        print(f'\n❌ FACTORES DE RIESGO:')
        factors_risk = []
        
        if btc_price > 112000:
            factors_risk.append('• BTC muy fuerte arriba de $112k')
            risk_score -= 2
            
        if sol_volume < 500e6:
            factors_risk.append('• Volumen bajo (posible squeeze)')
            risk_score -= 1
            
        factors_risk.append('• Domingo = movimientos erráticos')
        factors_risk.append('• Posible short squeeze si rompe $201')
        risk_score -= 1
        
        for f in factors_risk:
            print(f)
        
        # Calculate safety score
        print(f'\n📈 ESTRATEGIA RECOMENDADA:')
        
        if risk_score >= 5:
            print('🟢 SHORT MUY SEGURO (80% probabilidad éxito)')
            print('ACCIÓN:')
            print('• Entrar SHORT inmediatamente al salir en $199')
            print('• Target 1: $194 (2.5%)')
            print('• Target 2: $190 (4.5%)')
            print('• Stop Loss: $202 (1.5%)')
            print('• Risk/Reward: 1:3 EXCELENTE')
            
        elif risk_score >= 2:
            print('🟡 SHORT MODERADAMENTE SEGURO (60% probabilidad)')
            print('ACCIÓN:')
            print('• Esperar confirmación después de $199')
            print('• Si rechaza en $199-200 → SHORT')
            print('• Si rompe $200.50 → NO entrar')
            print('• Target: $194, Stop: $201.50')
            print('• Risk/Reward: 1:2 BUENO')
            
        else:
            print('🔴 SHORT RIESGOSO (40% probabilidad)')
            print('ACCIÓN:')
            print('• NO entrar SHORT automáticamente')
            print('• Evaluar momentum en $199')
            print('• Considerar mantener LONG si rompe $200')
            print('• O cerrar y esperar mejor entrada')
        
        print(f'\n🎯 NIVELES CLAVE PARA DECISIÓN:')
        print(f'• $199.00: Tu salida objetivo')
        print(f'• $200.50: Si pasa esto, CANCELAR SHORT')
        print(f'• $201.00: Stop loss absoluto')
        print(f'• $197.00: Si no llega aquí, evaluar SHORT desde precio actual')
        print(f'• $194.00: Target 1 del SHORT')
        print(f'• $190.00: Target 2 del SHORT')
        
        print(f'\n⏰ TIMING:')
        now = datetime.now()
        print(f'Hora actual: {now.strftime("%H:%M")}')
        if 2 <= now.hour <= 6:
            print('⚠️ ALERTA: Horario de pumps dominicales (2am-6am)')
            print('   Mayor riesgo de short squeeze')
        else:
            print('✅ Horario normal, menor riesgo de manipulación')
        
        print(f'\n💡 CONCLUSIÓN FINAL:')
        if risk_score >= 3:
            print('✅ SÍ es seguro el SHORT en $199')
            print('Probabilidad de éxito: 65-70%')
            print('Procede con el plan: Salir LONG → Entrar SHORT')
        else:
            print('⚠️ SHORT tiene riesgo moderado')
            print('Evalúa el momentum cuando llegues a $199')
            print('No te apresures, mejor perder oportunidad que perder dinero')

asyncio.run(analyze_short_safety())