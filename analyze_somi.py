#!/usr/bin/env python3
"""
Análisis técnico de SOMI/USDT usando el sistema BotphIA
"""

import asyncio
import logging
from datetime import datetime
import json
import pandas as pd
import numpy as np

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def analyze_somi():
    """Análisis completo de SOMI/USDT"""
    
    print("\n" + "="*60)
    print("🔍 ANÁLISIS TÉCNICO - SOMI/USDT")
    print("="*60)
    
    try:
        # Importar componentes del sistema
        from binance_integration import BinanceConnector
        from philosophers import get_trading_system
        from philosophers_extended import register_extended_philosophers
        from signal_pipeline import get_signal_pipeline
        from pinescript_generator import PineScriptGenerator
        
        # Inicializar sistema
        connector = BinanceConnector(testnet=False)  # Usar API real para obtener datos
        register_extended_philosophers()
        trading_system = get_trading_system()
        pipeline = get_signal_pipeline()
        pine_generator = PineScriptGenerator()
        
        symbol = "SOMIUSDT"
        
        # Obtener datos de múltiples timeframes
        print("\n📊 Obteniendo datos del mercado...")
        
        # Timeframe 15m para análisis detallado
        df_15m = connector.get_historical_data(symbol, timeframe='15m', limit=100)
        
        # Timeframe 1h para tendencia
        df_1h = connector.get_historical_data(symbol, timeframe='1h', limit=100)
        
        # Timeframe 4h para estructura mayor
        df_4h = connector.get_historical_data(symbol, timeframe='4h', limit=100)
        
        if df_15m.empty:
            print("❌ No se pudieron obtener datos para SOMI/USDT")
            print("   Es posible que el par no esté disponible en Binance")
            return
        
        # Precio actual
        current_price = float(df_15m['close'].iloc[-1])
        
        print(f"\n💰 Precio actual: ${current_price:.6f}")
        
        # Calcular indicadores técnicos
        print("\n📈 INDICADORES TÉCNICOS:")
        print("-" * 40)
        
        # RSI
        def calculate_rsi(data, period=14):
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        rsi_15m = calculate_rsi(df_15m['close']).iloc[-1]
        rsi_1h = calculate_rsi(df_1h['close']).iloc[-1]
        rsi_4h = calculate_rsi(df_4h['close']).iloc[-1]
        
        print(f"📊 RSI:")
        print(f"   15m: {rsi_15m:.1f}")
        print(f"   1h:  {rsi_1h:.1f}")
        print(f"   4h:  {rsi_4h:.1f}")
        
        # Medias móviles
        sma_20 = df_15m['close'].rolling(20).mean().iloc[-1]
        sma_50 = df_15m['close'].rolling(50).mean().iloc[-1]
        ema_9 = df_15m['close'].ewm(span=9).mean().iloc[-1]
        
        print(f"\n📉 MEDIAS MÓVILES:")
        print(f"   EMA 9:  ${ema_9:.6f}")
        print(f"   SMA 20: ${sma_20:.6f}")
        print(f"   SMA 50: ${sma_50:.6f}")
        
        # Bandas de Bollinger
        sma = df_15m['close'].rolling(20).mean()
        std = df_15m['close'].rolling(20).std()
        upper_band = (sma + 2 * std).iloc[-1]
        lower_band = (sma - 2 * std).iloc[-1]
        
        print(f"\n📊 BANDAS DE BOLLINGER:")
        print(f"   Superior: ${upper_band:.6f}")
        print(f"   Media:    ${sma.iloc[-1]:.6f}")
        print(f"   Inferior: ${lower_band:.6f}")
        
        # MACD
        exp1 = df_15m['close'].ewm(span=12).mean()
        exp2 = df_15m['close'].ewm(span=26).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9).mean()
        histogram = macd - signal_line
        
        print(f"\n📈 MACD:")
        print(f"   MACD: {macd.iloc[-1]:.8f}")
        print(f"   Signal: {signal_line.iloc[-1]:.8f}")
        print(f"   Histogram: {histogram.iloc[-1]:.8f}")
        
        # Volumen
        avg_volume = df_15m['volume'].rolling(20).mean().iloc[-1]
        current_volume = df_15m['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        print(f"\n📊 VOLUMEN:")
        print(f"   Actual: {current_volume:.2f}")
        print(f"   Promedio 20: {avg_volume:.2f}")
        print(f"   Ratio: {volume_ratio:.2f}x")
        
        # Soportes y resistencias
        highs = df_1h['high'].rolling(10).max()
        lows = df_1h['low'].rolling(10).min()
        resistance = highs.iloc[-1]
        support = lows.iloc[-1]
        
        print(f"\n🎯 NIVELES CLAVE:")
        print(f"   Resistencia: ${resistance:.6f}")
        print(f"   Soporte:     ${support:.6f}")
        
        # Análisis de tendencia
        trend_15m = "ALCISTA" if current_price > sma_20 else "BAJISTA"
        trend_1h = "ALCISTA" if df_1h['close'].iloc[-1] > df_1h['close'].rolling(20).mean().iloc[-1] else "BAJISTA"
        
        print(f"\n📊 TENDENCIA:")
        print(f"   15m: {trend_15m}")
        print(f"   1h:  {trend_1h}")
        
        # Análisis con filósofos
        print("\n" + "="*60)
        print("🧠 ANÁLISIS DE FILÓSOFOS DE TRADING")
        print("="*60)
        
        analyses = {}
        for name, philosopher in list(trading_system.philosophers.items())[:5]:
            analysis = philosopher.analyze_market(df_15m)
            if analysis:
                analyses[name] = analysis
                
                confidence = analysis.get('confidence', 0) * 100
                action = analysis.get('action', 'HOLD')
                
                # Determinar emoji según confianza
                if confidence >= 75:
                    emoji = "🟢"
                elif confidence >= 50:
                    emoji = "🟡"
                else:
                    emoji = "🔴"
                
                print(f"\n{emoji} {name}:")
                print(f"   Acción: {action}")
                print(f"   Confianza: {confidence:.1f}%")
                if analysis.get('reasoning'):
                    print(f"   Razón: {analysis['reasoning'][:100]}...")
        
        # Consenso
        if analyses:
            buy_count = sum(1 for a in analyses.values() if a.get('action') == 'BUY')
            sell_count = sum(1 for a in analyses.values() if a.get('action') == 'SELL')
            avg_confidence = np.mean([a.get('confidence', 0) * 100 for a in analyses.values()])
            
            print("\n" + "="*60)
            print("📊 CONSENSO DEL SISTEMA")
            print("="*60)
            print(f"   Señales BUY:  {buy_count}")
            print(f"   Señales SELL: {sell_count}")
            print(f"   Confianza promedio: {avg_confidence:.1f}%")
            
            # Determinar acción dominante
            if buy_count > sell_count:
                dominant_action = "BUY"
                dominant_count = buy_count
            elif sell_count > buy_count:
                dominant_action = "SELL"
                dominant_count = sell_count
            else:
                dominant_action = "NEUTRAL"
                dominant_count = 0
            
            if dominant_action != "NEUTRAL":
                print(f"\n🎯 SEÑAL DOMINANTE: {dominant_action} ({dominant_count}/{len(analyses)} filósofos)")
                
                # Calcular niveles
                if dominant_action == "BUY":
                    stop_loss = current_price * 0.97
                    take_profit_1 = current_price * 1.03
                    take_profit_2 = current_price * 1.05
                else:
                    stop_loss = current_price * 1.03
                    take_profit_1 = current_price * 0.97
                    take_profit_2 = current_price * 0.95
                
                print(f"\n💰 NIVELES SUGERIDOS:")
                print(f"   Entry: ${current_price:.6f}")
                print(f"   Stop Loss: ${stop_loss:.6f}")
                print(f"   Take Profit 1: ${take_profit_1:.6f}")
                print(f"   Take Profit 2: ${take_profit_2:.6f}")
                
                # Calcular riesgo/beneficio
                risk = abs(current_price - stop_loss)
                reward1 = abs(take_profit_1 - current_price)
                rr_ratio = reward1 / risk if risk > 0 else 0
                print(f"   R:R Ratio: {rr_ratio:.2f}:1")
                
                # Generar Pine Script
                signal_data = {
                    'symbol': symbol,
                    'action': dominant_action,
                    'confidence': avg_confidence,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit_1,
                    'philosopher': 'Sistema Consenso',
                    'timestamp': datetime.now().isoformat(),
                    'reasoning': f'Consenso de {dominant_count} filósofos',
                    'market_trend': trend_1h,
                    'rsi': rsi_15m,
                    'volume_ratio': volume_ratio
                }
                
                pinescript = pine_generator.generate_signal_script(signal_data)
                filename = f"SOMI_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
                filepath = pine_generator.save_to_file(pinescript, filename)
                
                print(f"\n📊 PINE SCRIPT GENERADO: {filepath}")
                print("   Copiar al portapapeles: cat " + filepath + " | pbcopy")
        
        # Resumen final
        print("\n" + "="*60)
        print("📋 RESUMEN DEL ANÁLISIS")
        print("="*60)
        
        # Señales de compra
        buy_signals = []
        if rsi_15m < 30:
            buy_signals.append("RSI sobreventa (15m)")
        if current_price < lower_band:
            buy_signals.append("Precio bajo banda inferior")
        if current_price > ema_9 and ema_9 > sma_20:
            buy_signals.append("Cruce alcista de medias")
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            buy_signals.append("MACD cruce alcista")
        
        # Señales de venta
        sell_signals = []
        if rsi_15m > 70:
            sell_signals.append("RSI sobrecompra (15m)")
        if current_price > upper_band:
            sell_signals.append("Precio sobre banda superior")
        if current_price < ema_9 and ema_9 < sma_20:
            sell_signals.append("Cruce bajista de medias")
        if histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0:
            sell_signals.append("MACD cruce bajista")
        
        if buy_signals:
            print("\n🟢 SEÑALES ALCISTAS:")
            for signal in buy_signals:
                print(f"   ✓ {signal}")
        
        if sell_signals:
            print("\n🔴 SEÑALES BAJISTAS:")
            for signal in sell_signals:
                print(f"   ✓ {signal}")
        
        if not buy_signals and not sell_signals:
            print("\n⚪ No hay señales claras en este momento")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error en el análisis: {e}")
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_somi())