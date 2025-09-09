#!/usr/bin/env python3
"""
Validador de señales de trading
"""

import requests
import json
from datetime import datetime

def validate_signals():
    symbols = ['LINKUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'SOLUSDT']
    
    print('🔍 VALIDACIÓN DE SEÑALES - ANÁLISIS DE MERCADO')
    print('='*60)
    print(f'Hora: {datetime.now().strftime("%H:%M:%S")}')
    
    signals_validation = []
    
    for symbol in symbols:
        try:
            # Obtener precio actual y datos 24h
            url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}'
            response = requests.get(url, timeout=3)
            data = response.json()
            
            current_price = float(data['lastPrice'])
            high_24h = float(data['highPrice'])
            low_24h = float(data['lowPrice'])
            change_24h = float(data['priceChangePercent'])
            volume = float(data['volume'])
            quote_volume = float(data['quoteVolume'])
            
            # Obtener datos de 1h para análisis más preciso
            klines_url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=24'
            klines_response = requests.get(klines_url, timeout=3)
            klines = klines_response.json()
            
            # Calcular RSI aproximado
            closes = [float(k[4]) for k in klines]
            gains = []
            losses = []
            for i in range(1, len(closes)):
                diff = closes[i] - closes[i-1]
                if diff > 0:
                    gains.append(diff)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(diff))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            # Calcular posición en rango del día
            price_position = ((current_price - low_24h) / (high_24h - low_24h)) * 100 if high_24h != low_24h else 50
            
            # Análisis de volumen
            avg_volume = quote_volume / 24  # Promedio por hora
            current_hour_volume = float(klines[-1][7])  # Volume de la última hora
            volume_ratio = current_hour_volume / avg_volume if avg_volume > 0 else 1
            
            print(f'\n📊 {symbol.replace("USDT", "")}:')
            print(f'  Precio actual: ${current_price:.6f}')
            print(f'  Cambio 24h: {change_24h:+.2f}%')
            print(f'  RSI (24h): {rsi:.1f}')
            print(f'  Posición en rango: {price_position:.1f}% (0=mínimo, 100=máximo)')
            print(f'  Volumen relativo: {volume_ratio:.2f}x promedio')
            
            # Validación de señal SELL
            validation_score = 0
            reasons = []
            
            if rsi > 70:
                validation_score += 30
                reasons.append(f'RSI alto ({rsi:.0f})')
            elif rsi > 60:
                validation_score += 15
                reasons.append(f'RSI moderado ({rsi:.0f})')
                
            if price_position > 80:
                validation_score += 30
                reasons.append('Cerca del máximo diario')
            elif price_position > 60:
                validation_score += 15
                reasons.append('Por encima del promedio')
                
            if change_24h > 10:
                validation_score += 25
                reasons.append(f'Subida fuerte ({change_24h:.1f}%)')
            elif change_24h > 5:
                validation_score += 15
                reasons.append(f'Subida moderada ({change_24h:.1f}%)')
            elif change_24h < -5:
                validation_score -= 20
                reasons.append(f'Ya en caída ({change_24h:.1f}%)')
                
            if volume_ratio > 1.5:
                validation_score += 15
                reasons.append(f'Volumen alto ({volume_ratio:.1f}x)')
                
            # Resultado de validación
            if validation_score >= 70:
                print(f'  ✅ SEÑAL VÁLIDA ({validation_score}%): {", ".join(reasons)}')
            elif validation_score >= 40:
                print(f'  ⚠️ SEÑAL NEUTRAL ({validation_score}%): {", ".join(reasons)}')
            else:
                print(f'  ❌ SEÑAL DÉBIL ({validation_score}%): {", ".join(reasons) if reasons else "Sin condiciones favorables"}')
                
            signals_validation.append({
                'symbol': symbol.replace('USDT', ''),
                'score': validation_score,
                'price': current_price,
                'rsi': rsi,
                'position': price_position
            })
            
        except Exception as e:
            print(f'\n❌ Error verificando {symbol}: {str(e)[:50]}')
    
    print('\n' + '='*60)
    print('📌 RESUMEN DE VALIDACIÓN:')
    
    valid_signals = [s for s in signals_validation if s['score'] >= 70]
    neutral_signals = [s for s in signals_validation if 40 <= s['score'] < 70]
    weak_signals = [s for s in signals_validation if s['score'] < 40]
    
    print(f'  ✅ Señales Válidas: {len(valid_signals)} - {", ".join([s["symbol"] for s in valid_signals])}')
    print(f'  ⚠️ Señales Neutrales: {len(neutral_signals)} - {", ".join([s["symbol"] for s in neutral_signals])}')
    print(f'  ❌ Señales Débiles: {len(weak_signals)} - {", ".join([s["symbol"] for s in weak_signals])}')
    
    print('\n💡 RECOMENDACIONES:')
    print('  1. Las señales con 90%+ confianza del Sistema Avanzado usan IA')
    print('  2. Considerar RSI > 70 como sobrecompra confirmada')
    print('  3. Usar stop-loss del 2-3% para proteger capital')
    print('  4. Revisar timeframes mayores (4h, 1d) para confirmar tendencia')
    
    return signals_validation

if __name__ == "__main__":
    validate_signals()