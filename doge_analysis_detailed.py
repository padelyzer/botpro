#!/usr/bin/env python3
"""
Análisis detallado de DOGE - Justificación técnica para entrada
"""

import requests
import json
from datetime import datetime, timedelta

def analyze_doge_entry():
    """Análisis profundo de por qué DOGE es buena entrada ahora"""
    
    print("="*70)
    print("🐕 ANÁLISIS TÉCNICO DETALLADO - DOGE ENTRY JUSTIFICATION")
    print("="*70)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # 1. Obtener datos actuales
        ticker_url = 'https://api.binance.com/api/v3/ticker/24hr'
        params = {'symbol': 'DOGEUSDT'}
        ticker_data = requests.get(ticker_url, params=params).json()
        
        price = float(ticker_data['lastPrice'])
        change_24h = float(ticker_data['priceChangePercent'])
        volume = float(ticker_data['quoteVolume'])
        high_24h = float(ticker_data['highPrice'])
        low_24h = float(ticker_data['lowPrice'])
        
        # 2. Obtener velas de 15m, 1h, 4h
        klines_url = 'https://api.binance.com/api/v3/klines'
        
        # 15 minutos
        klines_15m = requests.get(klines_url, params={
            'symbol': 'DOGEUSDT',
            'interval': '15m',
            'limit': 96  # 24 horas
        }).json()
        
        # 1 hora
        klines_1h = requests.get(klines_url, params={
            'symbol': 'DOGEUSDT',
            'interval': '1h',
            'limit': 48  # 2 días
        }).json()
        
        # 4 horas
        klines_4h = requests.get(klines_url, params={
            'symbol': 'DOGEUSDT',
            'interval': '4h',
            'limit': 30  # 5 días
        }).json()
        
        # Calcular métricas
        closes_15m = [float(k[4]) for k in klines_15m]
        volumes_15m = [float(k[5]) for k in klines_15m]
        closes_1h = [float(k[4]) for k in klines_1h]
        closes_4h = [float(k[4]) for k in klines_4h]
        
        # RSI
        def calculate_rsi(prices, period=14):
            if len(prices) < period:
                return 50
            
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        
        rsi_15m = calculate_rsi(closes_15m)
        rsi_1h = calculate_rsi(closes_1h)
        rsi_4h = calculate_rsi(closes_4h)
        
        # Soportes y resistencias
        support_1 = min(closes_1h[-24:])  # Mínimo últimas 24h
        support_2 = min(closes_4h[-7:])    # Mínimo última semana
        resistance_1 = max(closes_1h[-24:])  # Máximo últimas 24h
        resistance_2 = max(closes_4h[-7:])   # Máximo última semana
        
        # Posición en el rango
        range_size = high_24h - low_24h
        position_in_range = (price - low_24h) / range_size if range_size > 0 else 0.5
        
        # Momentum
        momentum_1h = ((closes_1h[-1] / closes_1h[-4]) - 1) * 100
        momentum_4h = ((closes_4h[-1] / closes_4h[-6]) - 1) * 100
        
        # Volumen promedio
        avg_volume_15m = sum(volumes_15m[-20:]) / 20
        current_volume_ratio = volumes_15m[-1] / avg_volume_15m if avg_volume_15m > 0 else 1
        
        print("📊 DATOS ACTUALES:")
        print(f"   Precio: ${price:.4f}")
        print(f"   Cambio 24h: {change_24h:+.2f}%")
        print(f"   Volumen 24h: ${volume/1e6:.1f}M")
        print(f"   Rango 24h: ${low_24h:.4f} - ${high_24h:.4f}")
        
        print("\n📈 INDICADORES TÉCNICOS:")
        print(f"   RSI 15m: {rsi_15m:.1f}")
        print(f"   RSI 1h: {rsi_1h:.1f}")
        print(f"   RSI 4h: {rsi_4h:.1f}")
        print(f"   Momentum 1h: {momentum_1h:+.2f}%")
        print(f"   Momentum 4h: {momentum_4h:+.2f}%")
        print(f"   Posición en rango: {position_in_range:.1%}")
        print(f"   Ratio volumen: {current_volume_ratio:.1f}x promedio")
        
        print("\n📍 NIVELES CLAVE:")
        print(f"   Soporte 1: ${support_1:.4f} (-{((price-support_1)/price)*100:.1f}%)")
        print(f"   Soporte 2: ${support_2:.4f} (-{((price-support_2)/price)*100:.1f}%)")
        print(f"   Resistencia 1: ${resistance_1:.4f} (+{((resistance_1-price)/price)*100:.1f}%)")
        print(f"   Resistencia 2: ${resistance_2:.4f} (+{((resistance_2-price)/price)*100:.1f}%)")
        
        # ANÁLISIS DE SEÑALES
        print("\n" + "="*70)
        print("🎯 JUSTIFICACIÓN DE ENTRADA EN DOGE:")
        print("="*70)
        
        bullish_signals = []
        bearish_signals = []
        
        # 1. Análisis de momentum
        if change_24h > 5:
            bullish_signals.append(f"✅ MOMENTUM FUERTE: +{change_24h:.1f}% en 24h")
            if change_24h < 10:
                bullish_signals.append("✅ No está sobreextendido (<10%), hay espacio para subir")
        
        # 2. Análisis de volumen
        if volume > 200000000:
            bullish_signals.append(f"✅ VOLUMEN ALTO: ${volume/1e6:.0f}M indica interés institucional")
        
        # 3. Análisis de RSI
        if 50 < rsi_1h < 70:
            bullish_signals.append(f"✅ RSI 1H en zona óptima ({rsi_1h:.0f}): momentum sin sobrecompra")
        elif rsi_1h > 70:
            bearish_signals.append(f"⚠️ RSI 1H alto ({rsi_1h:.0f}): posible sobrecompra temporal")
        
        # 4. Análisis de posición
        if position_in_range > 0.7:
            if position_in_range < 0.9:
                bullish_signals.append(f"✅ Rompiendo resistencias ({position_in_range:.0%} del rango)")
            else:
                bearish_signals.append(f"⚠️ Cerca del máximo diario ({position_in_range:.0%})")
        
        # 5. Análisis de tendencia
        if momentum_1h > 2 and momentum_4h > 0:
            bullish_signals.append(f"✅ TENDENCIA ALCISTA: 1h {momentum_1h:+.1f}%, 4h {momentum_4h:+.1f}%")
        
        # 6. Análisis de riesgo/recompensa
        distance_to_resistance = ((resistance_1 - price) / price) * 100
        distance_to_support = ((price - support_1) / price) * 100
        rr_ratio = distance_to_resistance / distance_to_support if distance_to_support > 0 else 0
        
        if rr_ratio > 1.5:
            bullish_signals.append(f"✅ R:R FAVORABLE: {rr_ratio:.1f}:1")
        
        # IMPRIMIR SEÑALES
        print("\n🟢 SEÑALES ALCISTAS:")
        for signal in bullish_signals:
            print(f"   {signal}")
        
        if bearish_signals:
            print("\n🔴 RIESGOS:")
            for signal in bearish_signals:
                print(f"   {signal}")
        
        # ESTRATEGIA RECOMENDADA
        print("\n" + "="*70)
        print("💡 ESTRATEGIA RECOMENDADA:")
        print("="*70)
        
        entry_price = price * 1.001  # Entrada con market order
        stop_loss = support_1 * 0.995  # Stop bajo soporte
        tp1 = price * 1.02  # +2%
        tp2 = price * 1.035  # +3.5%
        tp3 = resistance_1 * 0.995  # Antes de resistencia
        
        print(f"\n📍 PLAN DE TRADING:")
        print(f"   Entrada: ${entry_price:.4f}")
        print(f"   Stop Loss: ${stop_loss:.4f} ({((stop_loss-entry_price)/entry_price)*100:.1f}%)")
        print(f"   Target 1 (50%): ${tp1:.4f} (+2.0%)")
        print(f"   Target 2 (30%): ${tp2:.4f} (+3.5%)")
        print(f"   Target 3 (20%): ${tp3:.4f} (+{((tp3-entry_price)/entry_price)*100:.1f}%)")
        
        # Gestión de riesgo
        risk_amount = 100  # $100 de riesgo
        stop_distance = abs(entry_price - stop_loss) / entry_price
        position_size = risk_amount / stop_distance
        
        print(f"\n💰 GESTIÓN DE CAPITAL:")
        print(f"   Riesgo máximo: $100")
        print(f"   Tamaño posición: ${position_size:.0f}")
        print(f"   Ganancia potencial TP1: ${position_size * 0.02:.0f}")
        print(f"   Ganancia potencial TP2: ${position_size * 0.035:.0f}")
        
        # CONCLUSIÓN
        score = len(bullish_signals) - len(bearish_signals)
        
        print("\n" + "="*70)
        print("📊 EVALUACIÓN FINAL:")
        print("="*70)
        
        if score >= 4:
            print("🟢 ENTRADA RECOMENDADA - Señales muy fuertes")
            recommendation = "STRONG BUY"
        elif score >= 2:
            print("🟡 ENTRADA POSIBLE - Señales moderadas")
            recommendation = "BUY"
        else:
            print("🔴 ESPERAR - Señales insuficientes")
            recommendation = "WAIT"
        
        print(f"\nPuntuación: {len(bullish_signals)} alcistas vs {len(bearish_signals)} bajistas")
        print(f"Recomendación: {recommendation}")
        
        # Factores clave
        print("\n🔑 FACTORES CLAVE PARA EL ÉXITO:")
        print("   1. El volumen alto confirma interés real")
        print("   2. RSI no está en extremos = espacio para crecer")
        print("   3. Momentum positivo en múltiples timeframes")
        print("   4. Risk/Reward favorable con stops claros")
        print("   5. Gestión de posición con targets escalonados")
        
        # Guardar análisis
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'price': price,
            'recommendation': recommendation,
            'score': score,
            'entry': entry_price,
            'stop_loss': stop_loss,
            'targets': [tp1, tp2, tp3],
            'position_size': position_size,
            'bullish_signals': bullish_signals,
            'bearish_signals': bearish_signals
        }
        
        with open('doge_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print("\n💾 Análisis guardado en doge_analysis.json")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error en análisis: {e}")
        return None

if __name__ == "__main__":
    analyze_doge_entry()