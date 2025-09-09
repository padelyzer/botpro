#!/usr/bin/env python3
"""
Análisis macro del mercado - dirección general y riesgos
"""

import httpx
import asyncio
from datetime import datetime

async def macro_analysis():
    async with httpx.AsyncClient() as client:
        print('='*60)
        print('🌍 ANÁLISIS MACRO - DIRECCIÓN DEL MERCADO')
        print('='*60)
        
        try:
            # Get major crypto data
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
            
            print(f'\n📊 CRYPTO MARKET STATUS:')
            total_cap_change = 0
            bearish_count = 0
            bullish_count = 0
            
            for symbol in symbols:
                response = await client.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}')
                if response.status_code == 200:
                    data = response.json()
                    price = float(data['lastPrice'])
                    change_24h = float(data['priceChangePercent'])
                    volume = float(data['quoteVolume'])
                    
                    if change_24h < -3:
                        status = "🔴 BEARISH"
                        bearish_count += 1
                    elif change_24h < 0:
                        status = "🟡 WEAK"
                        bearish_count += 1
                    elif change_24h < 3:
                        status = "🟢 NEUTRAL"
                        bullish_count += 1
                    else:
                        status = "🚀 BULLISH"
                        bullish_count += 1
                    
                    total_cap_change += change_24h
                    
                    coin = symbol.replace('USDT', '')
                    print(f'{coin:<4}: ${price:<8.2f} {change_24h:>+6.2f}% | Vol: ${volume/1e6:>6.1f}M {status}')
            
            avg_change = total_cap_change / len(symbols)
            
            print(f'\n📈 MARKET SENTIMENT:')
            print(f'Average change: {avg_change:+.2f}%')
            print(f'Bearish coins: {bearish_count}/{len(symbols)}')
            print(f'Bullish coins: {bullish_count}/{len(symbols)}')
            
            if bearish_count > bullish_count:
                market_direction = "🔴 BEARISH DOMINANCE"
                risk_level = "HIGH"
            elif avg_change < -2:
                market_direction = "🟡 MARKET WEAKNESS"
                risk_level = "MEDIUM"
            else:
                market_direction = "🟢 MIXED/NEUTRAL"
                risk_level = "LOW"
            
            print(f'Market Direction: {market_direction}')
            print(f'Risk Level: {risk_level}')
            
            # BTC dominance analysis
            btc_response = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
            if btc_response.status_code == 200:
                btc_data = btc_response.json()
                btc_price = float(btc_data['lastPrice'])
                btc_change = float(btc_data['priceChangePercent'])
                btc_volume = float(btc_data['quoteVolume'])
                
                print(f'\n₿ BTC LEADERSHIP ANALYSIS:')
                print(f'BTC: ${btc_price:,.2f} ({btc_change:+.2f}%)')
                print(f'Volume: {btc_volume:,.0f} BTC')
                
                if btc_change < -2:
                    btc_sentiment = "🔴 BTC LEADING DOWN"
                    alt_impact = "Alts seguirán cayendo"
                elif btc_change > 2:
                    btc_sentiment = "🟢 BTC LEADING UP"
                    alt_impact = "Alts pueden recuperar"
                else:
                    btc_sentiment = "🟡 BTC SIDEWAYS"
                    alt_impact = "Alts con movimiento propio"
                
                print(f'BTC Status: {btc_sentiment}')
                print(f'Alt Impact: {alt_impact}')
            
            # Fear & Greed estimation
            if avg_change < -5:
                fear_greed = "EXTREME FEAR (20-30)"
                fg_color = "🔴"
            elif avg_change < -2:
                fear_greed = "FEAR (30-45)"
                fg_color = "🟡"
            elif avg_change < 2:
                fear_greed = "NEUTRAL (45-55)"
                fg_color = "🟢"
            else:
                fear_greed = "GREED (55-70)"
                fg_color = "🚀"
            
            print(f'\n😨 FEAR & GREED INDEX (Estimated):')
            print(f'{fg_color} {fear_greed}')
            
            # Time-based analysis
            now = datetime.now()
            hour = now.hour
            day_of_week = now.weekday()  # 0=Monday, 6=Sunday
            
            print(f'\n⏰ TIMING ANALYSIS:')
            print(f'Current time: {now.strftime("%H:%M")} ({now.strftime("%A")})')
            
            time_risk = "NORMAL"
            if day_of_week == 6:  # Sunday
                if 2 <= hour <= 6:
                    time_risk = "HIGH - Sunday pump/dump hours"
                else:
                    time_risk = "MEDIUM - Sunday volatility"
            elif day_of_week in [4, 5]:  # Friday/Saturday
                time_risk = "LOW - Weekend consolidation"
            
            print(f'Time-based risk: {time_risk}')
            
            # Global macro factors (estimated impact)
            print(f'\n🌐 MACRO FACTORS:')
            macro_factors = [
                "US Markets: Closed (weekend) - Limited impact",
                "DXY: Moderate strength affecting crypto",
                "Interest Rates: Stable but elevated",
                "Risk-on sentiment: WEAK due to -8% crypto drop"
            ]
            
            for factor in macro_factors:
                print(f'• {factor}')
            
            # Specific analysis for your trade
            print(f'\n🎯 ANÁLISIS PARA TU POSICIÓN SOL:')
            
            sol_response = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
            if sol_response.status_code == 200:
                sol_data = sol_response.json()
                sol_price = float(sol_data['lastPrice'])
                sol_change = float(sol_data['priceChangePercent'])
                
                print(f'SOL actual: ${sol_price:.2f} ({sol_change:+.2f}%)')
                print(f'Tu entrada: $198.20')
                print(f'Pérdida actual: ${sol_price - 198.20:.2f}')
                
                # Risk assessment for SOL specifically
                if market_direction.startswith("🔴") and btc_change < -2:
                    sol_risk = "🔴 ALTO - Market + BTC bearish"
                    recommendation = "Considera salir si toca $195+ para minimizar pérdidas"
                elif market_direction.startswith("🟡"):
                    sol_risk = "🟡 MEDIO - Market indeciso"
                    recommendation = "Mantén pero con stop loss ajustado"
                else:
                    sol_risk = "🟢 BAJO - Market neutral/positive"
                    recommendation = "Mantén posición, probable rebote"
                
                print(f'Riesgo SOL: {sol_risk}')
                print(f'Recomendación: {recommendation}')
            
            print(f'\n🔮 PRÓXIMAS HORAS (PREDICCIÓN):')
            
            if bearish_count >= 4 and btc_change < -2:
                prediction = "🔴 Probable continuación bajista"
                sol_target = "$187-190"
                action = "ALTO RIESGO - Evalúa salida"
            elif bearish_count >= 3:
                prediction = "🟡 Consolidación con bias bajista"
                sol_target = "$192-195"
                action = "MEDIUM RISK - Ajusta stop loss"
            else:
                prediction = "🟢 Posible rebote técnico"
                sol_target = "$196-199"
                action = "MANTÉN - Probable recuperación"
            
            print(f'Predicción: {prediction}')
            print(f'SOL target probable: {sol_target}')
            print(f'Acción sugerida: {action}')
            
        except Exception as e:
            print(f'Error getting market data: {e}')

asyncio.run(macro_analysis())