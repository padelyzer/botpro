#!/usr/bin/env python3
"""
Check BTC status and SOL liquidation zones below $186.50
Real-time market analysis
"""

import httpx
import asyncio

async def check_market_and_liquidations():
    async with httpx.AsyncClient() as client:
        print('='*60)
        print('🔍 MARKET CHECK - BTC STATUS + SOL LIQUIDATION ZONES')
        print('='*60)
        
        # Get BTC data
        btc_resp = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
        btc_data = btc_resp.json()
        btc_price = float(btc_data['lastPrice'])
        btc_change = float(btc_data['priceChangePercent'])
        btc_low = float(btc_data['lowPrice'])
        btc_high = float(btc_data['highPrice'])
        
        # Get SOL data
        sol_resp = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
        sol_data = sol_resp.json()
        sol_price = float(sol_data['lastPrice'])
        sol_change = float(sol_data['priceChangePercent'])
        sol_low = float(sol_data['lowPrice'])
        sol_volume = float(sol_data['quoteVolume'])
        
        # Get other major cryptos
        symbols = ["ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
        
        print(f'\n₿ BTC STATUS:')
        print(f'Price: ${btc_price:,.2f}')
        print(f'24h Change: {btc_change:+.2f}%')
        print(f'24h Range: ${btc_low:,.2f} - ${btc_high:,.2f}')
        
        # BTC critical levels
        if btc_price > 110000:
            btc_status = "🟢 HOLDING SUPPORT"
        elif btc_price > 108000:
            btc_status = "🟡 NEUTRAL ZONE"
        else:
            btc_status = "🔴 BEARISH - BELOW KEY SUPPORT"
        
        print(f'Status: {btc_status}')
        print(f'Key level: $108,000 ({"ABOVE ✅" if btc_price > 108000 else "BELOW ❌"})')
        
        print(f'\n📊 SOL SITUATION:')
        print(f'Current: ${sol_price:.2f}')
        print(f'Rebote desde: $186.50')
        print(f'24h Change: {sol_change:+.2f}%')
        print(f'24h Low: ${sol_low:.2f}')
        print(f'Volume: ${sol_volume/1e6:.1f}M')
        
        # Market breadth
        print(f'\n🌍 MARKET BREADTH:')
        bearish_count = 1 if btc_change < 0 else 0
        bearish_count += 1 if sol_change < 0 else 0
        
        for symbol in symbols:
            resp = await client.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}')
            data = resp.json()
            price = float(data['lastPrice'])
            change = float(data['priceChangePercent'])
            
            coin = symbol.replace('USDT', '')
            status_icon = "🔴" if change < -2 else "🟡" if change < 0 else "🟢"
            
            if change < 0:
                bearish_count += 1
            
            price_str = f'{price:.4f}' if price < 10 else f'{price:.2f}'
            print(f'{coin}: ${price_str} ({change:+.2f}%) {status_icon}')
        
        market_sentiment = f"{bearish_count}/6 coins bearish"
        
        if bearish_count >= 5:
            market_status = "🔴 BEARISH DOMINANT"
        elif bearish_count >= 3:
            market_status = "🟡 MIXED/WEAK"
        else:
            market_status = "🟢 RECOVERY ATTEMPT"
        
        print(f'\nMarket: {market_sentiment} - {market_status}')
        
        # SOL Liquidation analysis
        print(f'\n💥 LIQUIDACIÓN ZONES BELOW $186.50:')
        
        current_bounce = 186.50
        
        liquidation_zones = [
            (185.0, 100_000, "25x longs desde $194", "🟡 LIGHT"),
            (183.0, 250_000, "20x longs desde $192", "🟠 MODERATE"), 
            (180.0, 500_000, "10x longs desde $200", "🔴 HEAVY"),
            (175.0, 750_000, "5x longs desde $195", "💀 MASSIVE"),
            (170.0, 1_000_000, "Panic zone - cascada", "☠️ EXTREME"),
            (165.0, 500_000, "Soporte histórico", "🔵 SUPPORT"),
        ]
        
        print(f'\n📍 Rebote actual: ${current_bounce}')
        print(f'Precio actual: ${sol_price:.2f}')
        print(f'{"↗️ BOUNCING" if sol_price > current_bounce else "↘️ TESTING"} desde el rebote\n')
        
        total_liq_below = 0
        for level, estimated_liq, description, severity in liquidation_zones:
            if level < current_bounce:
                total_liq_below += estimated_liq
                distance = ((current_bounce - level) / current_bounce) * 100
                print(f'${level:6.2f}: ~${estimated_liq/1000:,.0f}k liq | -{distance:4.1f}% | {description} {severity}')
        
        print(f'\n💰 TOTAL LIQUIDEZ ABAJO: ~${total_liq_below/1e6:.1f}M')
        
        # Analysis of bounce strength
        print(f'\n📈 ANÁLISIS DEL REBOTE EN $186.50:')
        
        bounce_strength = ((sol_price - current_bounce) / current_bounce) * 100
        volume_vs_avg = (sol_volume / 2_000_000_000) * 100  # Assuming 2B is average
        
        print(f'Fuerza rebote: {bounce_strength:+.2f}%')
        print(f'Volumen: {volume_vs_avg:.0f}% del promedio')
        
        if bounce_strength > 2:
            bounce_quality = "🟢 STRONG - Posible bottom local"
        elif bounce_strength > 0.5:
            bounce_quality = "🟡 WEAK - Needs confirmation"
        else:
            bounce_quality = "🔴 FAILING - Probable más caída"
        
        print(f'Calidad: {bounce_quality}')
        
        # Recommendations based on current data
        print(f'\n🎯 ANÁLISIS Y RECOMENDACIONES:')
        
        if btc_price < 108000:
            print(f'\n⚠️ BTC BELOW $108k - BEARISH SIGNAL')
            print(f'• SOL probable test $180-183')
            print(f'• Mucha liquidez en $180 (500k)')
            print(f'• Si rompe $183 → cascada posible')
            recommendation = "WAIT - No comprar aún"
        elif btc_price > 110000 and bounce_strength > 1:
            print(f'\n✅ BTC HOLDING + SOL BOUNCING')
            print(f'• Posible bottom local en $186.50')
            print(f'• Target rebote: $192-195')
            print(f'• Stop loss: $184')
            recommendation = "CONSIDERAR entrada pequeña"
        else:
            print(f'\n🟡 SITUACIÓN MIXTA')
            print(f'• BTC indeciso en rango')
            print(f'• SOL puede retestar $186.50')
            print(f'• Siguiente soporte: $183')
            recommendation = "OBSERVAR - Esperar confirmación"
        
        print(f'\n📋 ACCIÓN: {recommendation}')
        
        # Specific levels to watch
        print(f'\n👁️ NIVELES CLAVE A VIGILAR:')
        print(f'• $183: MEGA liquidaciones (250k) - probable bounce')
        print(f'• $180: SUPER crítico (500k liq) - strong support')
        print(f'• $175: PANIC zone - si llega aquí, capitulación')
        
        # Your position analysis
        print(f'\n💼 TU POSICIÓN:')
        your_liquidation = 152.05
        distance_to_liq = ((sol_price - your_liquidation) / sol_price) * 100
        
        print(f'Tu liquidación: ${your_liquidation}')
        print(f'Distancia: {distance_to_liq:.1f}%')
        
        if sol_price < 175:
            position_risk = "🔴 HIGH RISK - Consider adding margin"
        elif sol_price < 180:
            position_risk = "🟡 MEDIUM RISK - Monitor closely"
        else:
            position_risk = "🟢 SAFE - Good buffer"
        
        print(f'Risk level: {position_risk}')
        
        print('='*60)

asyncio.run(check_market_and_liquidations())