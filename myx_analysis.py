#!/usr/bin/env python3
"""
Análisis detallado de MYXUSDT - Zonas de rebote post-breakout
"""

import requests
import json
from datetime import datetime, timedelta
import numpy as np

def analyze_myx():
    """Análisis completo de MYX/USDT"""
    
    print("="*70)
    print("📊 ANÁLISIS TÉCNICO DETALLADO - MYX/USDT")
    print("="*70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # 1. Obtener datos actuales
        ticker_url = 'https://api.binance.com/api/v3/ticker/24hr'
        params = {'symbol': 'MYXUSDT'}
        
        try:
            ticker_data = requests.get(ticker_url, params=params, timeout=10).json()
            
            # Si no existe en Binance, intentar con API alternativa
            if 'code' in ticker_data:
                print("⚠️ MYX no encontrado en Binance. Buscando en otros exchanges...")
                # Intentar CoinGecko o similar
                return analyze_alternative_myx()
                
        except:
            return analyze_alternative_myx()
        
        price = float(ticker_data['lastPrice'])
        change_24h = float(ticker_data['priceChangePercent'])
        volume = float(ticker_data['quoteVolume'])
        high_24h = float(ticker_data['highPrice'])
        low_24h = float(ticker_data['lowPrice'])
        
        # 2. Obtener velas para análisis técnico
        klines_url = 'https://api.binance.com/api/v3/klines'
        
        # Múltiples timeframes
        timeframes = {
            '15m': 96,   # 24 horas
            '1h': 168,   # 7 días
            '4h': 180,   # 30 días
            '1d': 90     # 3 meses
        }
        
        klines_data = {}
        for tf, limit in timeframes.items():
            params = {
                'symbol': 'MYXUSDT',
                'interval': tf,
                'limit': limit
            }
            klines = requests.get(klines_url, params=params, timeout=10).json()
            klines_data[tf] = klines
        
        # 3. Calcular indicadores técnicos
        closes_1h = [float(k[4]) for k in klines_data['1h']]
        highs_1h = [float(k[2]) for k in klines_data['1h']]
        lows_1h = [float(k[3]) for k in klines_data['1h']]
        volumes_1h = [float(k[5]) for k in klines_data['1h']]
        
        closes_4h = [float(k[4]) for k in klines_data['4h']]
        closes_1d = [float(k[4]) for k in klines_data['1d']]
        
        # RSI
        def calculate_rsi(prices, period=14):
            if len(prices) < period:
                return 50
            
            deltas = np.diff(prices)
            seed = deltas[:period+1]
            up = seed[seed >= 0].sum() / period
            down = -seed[seed < 0].sum() / period
            rs = up / down if down != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        
        rsi_1h = calculate_rsi(closes_1h)
        rsi_4h = calculate_rsi(closes_4h)
        rsi_1d = calculate_rsi(closes_1d)
        
        # 4. IDENTIFICAR NIVELES CLAVE DE SOPORTE/RESISTENCIA
        
        # Método 1: Pivots points clásicos
        pivot = (high_24h + low_24h + price) / 3
        r1 = 2 * pivot - low_24h
        r2 = pivot + (high_24h - low_24h)
        r3 = high_24h + 2 * (pivot - low_24h)
        s1 = 2 * pivot - high_24h
        s2 = pivot - (high_24h - low_24h)
        s3 = low_24h - 2 * (high_24h - pivot)
        
        # Método 2: Niveles de Fibonacci
        range_size = high_24h - low_24h
        fib_levels = {
            '0%': low_24h,
            '23.6%': low_24h + range_size * 0.236,
            '38.2%': low_24h + range_size * 0.382,
            '50%': low_24h + range_size * 0.5,
            '61.8%': low_24h + range_size * 0.618,
            '78.6%': low_24h + range_size * 0.786,
            '100%': high_24h
        }
        
        # Método 3: Análisis de volumen profile (zonas de alto volumen)
        price_levels = {}
        for i, kline in enumerate(klines_data['1h']):
            price_avg = (float(kline[2]) + float(kline[3])) / 2
            vol = float(kline[5])
            price_range = f"{price_avg:.4f}"
            if price_range not in price_levels:
                price_levels[price_range] = 0
            price_levels[price_range] += vol
        
        # Top 5 niveles con más volumen (zonas de soporte fuerte)
        volume_nodes = sorted(price_levels.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 5. ANÁLISIS POST-BREAKOUT
        
        # Detectar si hubo breakout reciente
        recent_high = max(closes_1h[-24:])  # Máximo últimas 24h
        previous_high = max(closes_1h[-48:-24])  # Máximo 24h anteriores
        
        breakout_detected = recent_high > previous_high * 1.05  # Breakout si supera 5%
        
        # Calcular retroceso esperado
        if breakout_detected:
            # Después de un breakout, es común retroceder 38.2% o 50% del movimiento
            breakout_move = recent_high - previous_high
            retracement_382 = recent_high - (breakout_move * 0.382)
            retracement_50 = recent_high - (breakout_move * 0.5)
            retracement_618 = recent_high - (breakout_move * 0.618)
        else:
            retracement_382 = s1
            retracement_50 = pivot
            retracement_618 = s2
        
        # 6. MOSTRAR RESULTADOS
        
        print("📊 DATOS ACTUALES:")
        print(f"   Precio: ${price:.6f}")
        print(f"   Cambio 24h: {change_24h:+.2f}%")
        print(f"   Volumen 24h: ${volume/1e6:.2f}M")
        print(f"   Rango 24h: ${low_24h:.6f} - ${high_24h:.6f}")
        
        print("\n📈 INDICADORES TÉCNICOS:")
        print(f"   RSI 1h: {rsi_1h:.1f}")
        print(f"   RSI 4h: {rsi_4h:.1f}")
        print(f"   RSI Daily: {rsi_1d:.1f}")
        
        print("\n🎯 NIVELES PIVOT:")
        print(f"   R3: ${r3:.6f} (Resistencia fuerte)")
        print(f"   R2: ${r2:.6f}")
        print(f"   R1: ${r1:.6f}")
        print(f"   Pivot: ${pivot:.6f} ← ZONA CLAVE")
        print(f"   S1: ${s1:.6f}")
        print(f"   S2: ${s2:.6f}")
        print(f"   S3: ${s3:.6f} (Soporte fuerte)")
        
        print("\n📐 NIVELES FIBONACCI:")
        for level, price_fib in fib_levels.items():
            marker = " ← REBOTE PROBABLE" if level in ['38.2%', '50%', '61.8%'] else ""
            print(f"   {level}: ${price_fib:.6f}{marker}")
        
        print("\n💎 ZONAS DE ALTO VOLUMEN (Soportes fuertes):")
        for i, (price_level, vol) in enumerate(volume_nodes, 1):
            print(f"   Zona {i}: ${float(price_level):.6f} (Vol: ${vol/1e6:.1f}M)")
        
        if breakout_detected:
            print("\n🚀 BREAKOUT DETECTADO!")
            print("   Niveles de retroceso esperados:")
            print(f"   38.2%: ${retracement_382:.6f} ← PRIMER SOPORTE")
            print(f"   50%: ${retracement_50:.6f} ← SOPORTE FUERTE")
            print(f"   61.8%: ${retracement_618:.6f} ← ÚLTIMO SOPORTE")
        
        # 7. ESTRATEGIA RECOMENDADA
        print("\n" + "="*70)
        print("💡 ESTRATEGIA POST-BREAKOUT:")
        print("="*70)
        
        # Determinar zonas de entrada
        entry_zones = []
        
        # Zona 1: Retroceso al 38.2%
        if price > retracement_382:
            entry_zones.append({
                'level': retracement_382,
                'type': 'Retroceso 38.2%',
                'strength': 'Media'
            })
        
        # Zona 2: Pivot point
        entry_zones.append({
            'level': pivot,
            'type': 'Pivot Central',
            'strength': 'Fuerte'
        })
        
        # Zona 3: Retroceso al 50%
        entry_zones.append({
            'level': retracement_50,
            'type': 'Retroceso 50%',
            'strength': 'Muy Fuerte'
        })
        
        print("\n📍 ZONAS DE COMPRA ESCALONADA:")
        for i, zone in enumerate(entry_zones, 1):
            print(f"\n   ZONA {i}: ${zone['level']:.6f}")
            print(f"   Tipo: {zone['type']}")
            print(f"   Fuerza: {zone['strength']}")
            print(f"   Cantidad: {33}% de la posición")
        
        # Stop loss y targets
        stop_loss = min(entry_zones, key=lambda x: x['level'])['level'] * 0.95
        target1 = recent_high if breakout_detected else r1
        target2 = r2
        target3 = r3
        
        print(f"\n🛡️ GESTIÓN DE RIESGO:")
        print(f"   Stop Loss: ${stop_loss:.6f} (-5% desde zona más baja)")
        print(f"   Target 1: ${target1:.6f} (+{((target1/price)-1)*100:.1f}%)")
        print(f"   Target 2: ${target2:.6f} (+{((target2/price)-1)*100:.1f}%)")
        print(f"   Target 3: ${target3:.6f} (+{((target3/price)-1)*100:.1f}%)")
        
        # Risk/Reward
        avg_entry = sum([z['level'] for z in entry_zones]) / len(entry_zones)
        risk = abs(avg_entry - stop_loss) / avg_entry
        reward = abs(target1 - avg_entry) / avg_entry
        rr_ratio = reward / risk if risk > 0 else 0
        
        print(f"\n📊 Risk/Reward: 1:{rr_ratio:.1f}")
        
        # Recomendación final
        print("\n" + "="*70)
        print("🎯 RECOMENDACIÓN:")
        print("="*70)
        
        if breakout_detected and price > retracement_382:
            print("✅ ESPERAR retroceso al 38.2% para primera entrada")
            print("✅ Añadir posición en pivot y 50% si llega")
            print("✅ El breakout es válido mientras se mantenga sobre pivot")
        elif rsi_1h < 40:
            print("✅ COMPRAR ahora, RSI oversold")
            print("✅ Zona de rebote inminente")
        else:
            print("⏳ ESPERAR a zonas de entrada identificadas")
            print("⏳ No perseguir el precio")
        
        print("\n💎 CLAVES DEL ÉXITO:")
        print("   1. Comprar en retrocesos, no en pumps")
        print("   2. Escalonar entradas en 3 zonas")
        print("   3. Stop loss estricto bajo soporte clave")
        print("   4. Tomar profits parciales en resistencias")
        
        # Guardar análisis
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'MYXUSDT',
            'price': price,
            'breakout': breakout_detected,
            'entry_zones': entry_zones,
            'stop_loss': stop_loss,
            'targets': [target1, target2, target3],
            'rr_ratio': rr_ratio
        }
        
        with open('myx_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print("\n💾 Análisis guardado en myx_analysis.json")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analizando MYX: {e}")
        return None

def analyze_alternative_myx():
    """Análisis alternativo si MYX no está en Binance"""
    print("\n🔍 Analizando MYX en fuentes alternativas...")
    
    # Intentar con CoinGecko
    try:
        # Buscar el token en CoinGecko
        search_url = 'https://api.coingecko.com/api/v3/search'
        params = {'query': 'MYX'}
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['coins']:
                coin_id = data['coins'][0]['id']
                
                # Obtener datos del precio
                price_url = f'https://api.coingecko.com/api/v3/simple/price'
                params = {
                    'ids': coin_id,
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'true',
                    'include_24hr_vol': 'true',
                    'include_market_cap': 'true'
                }
                
                price_data = requests.get(price_url, params=params).json()
                
                if coin_id in price_data:
                    info = price_data[coin_id]
                    print(f"\n✅ Encontrado: {coin_id.upper()}")
                    print(f"   Precio: ${info['usd']:.6f}")
                    print(f"   Cambio 24h: {info.get('usd_24h_change', 0):.2f}%")
                    print(f"   Volumen 24h: ${info.get('usd_24h_vol', 0)/1e6:.2f}M")
                    
                    # Análisis básico sin datos históricos
                    print("\n📊 ANÁLISIS LIMITADO (sin datos históricos)")
                    print("   Basado en cambio 24h y volumen:")
                    
                    change = info.get('usd_24h_change', 0)
                    if change > 10:
                        print("   ⚠️ SOBREEXTENDIDO - Esperar corrección")
                        print("   Zonas de retroceso probables:")
                        print(f"   - 5% retroceso: ${info['usd'] * 0.95:.6f}")
                        print(f"   - 10% retroceso: ${info['usd'] * 0.90:.6f}")
                        print(f"   - 15% retroceso: ${info['usd'] * 0.85:.6f}")
                    elif change < -10:
                        print("   ✅ OVERSOLD - Posible rebote")
                        print(f"   Entry: ${info['usd']:.6f}")
                        print(f"   Target: ${info['usd'] * 1.1:.6f}")
                    else:
                        print("   ➡️ NEUTRAL - Monitorear")
                    
                    return {'price': info['usd'], 'change': change}
        
    except Exception as e:
        print(f"❌ Error con fuentes alternativas: {e}")
    
    print("\n⚠️ MYX no encontrado en exchanges principales")
    print("   Posibles razones:")
    print("   1. Token muy nuevo o de baja capitalización")
    print("   2. Solo disponible en DEX (Uniswap, PancakeSwap)")
    print("   3. Ticker diferente en otros exchanges")
    
    print("\n💡 RECOMENDACIONES:")
    print("   1. Verificar el ticker correcto")
    print("   2. Buscar en CoinMarketCap o CoinGecko")
    print("   3. Revisar en qué exchange está listado")
    
    return None

if __name__ == "__main__":
    analyze_myx()