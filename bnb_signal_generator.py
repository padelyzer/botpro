#!/usr/bin/env python3
"""
Generador de Señal Específica para BNB
Basado en el análisis completo que mostró BULLISH
"""

import asyncio
import httpx
import json
from datetime import datetime

async def generate_bnb_signal():
    """Genera señal específica para BNB con entry price sugerido"""
    
    print("🔍 GENERANDO SEÑAL PARA BNB...")
    print("="*50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Obtener análisis completo
            liquidity_response = await client.get("http://localhost:8002/api/liquidity/BNBUSDT")
            
            if liquidity_response.status_code != 200:
                print("❌ Error obteniendo datos de liquidez")
                return
            
            liquidity_data = liquidity_response.json()
            ob_analysis = liquidity_data["order_book_analysis"]
            liq_analysis = liquidity_data.get("liquidation_analysis", {})
            
            current_price = ob_analysis["current_price"]
            imbalance = ob_analysis["imbalance"]
            large_orders = ob_analysis["large_orders"]
            support_levels = ob_analysis["support_levels"]
            resistance_levels = ob_analysis["resistance_levels"]
            
            print(f"💰 PRECIO ACTUAL: ${current_price:,.2f}")
            print(f"📊 IMBALANCE: {imbalance:+.1f}% {'(MÁS BIDS)' if imbalance > 0 else '(MÁS ASKS)'}")
            print(f"🐋 WHALE ACTIVITY: {'SÍ' if large_orders['whale_activity'] else 'No'}")
            print(f"📈 BIDS GRANDES: {len(large_orders['large_bids'])}")
            print(f"📉 ASKS GRANDES: {len(large_orders['large_asks'])}")
            
            # Obtener datos técnicos de Binance
            tech_response = await client.get(
                "https://fapi.binance.com/fapi/v1/klines",
                params={"symbol": "BNBUSDT", "interval": "1h", "limit": 50}
            )
            
            if tech_response.status_code == 200:
                klines = tech_response.json()
                last_candle = klines[-1]
                
                open_price = float(last_candle[1])
                high_price = float(last_candle[2])
                low_price = float(last_candle[3])
                close_price = float(last_candle[4])
                volume = float(last_candle[5])
                
                # Calcular posición en la vela actual
                candle_position = (current_price - low_price) / (high_price - low_price) if high_price != low_price else 0.5
                candle_change = ((current_price - open_price) / open_price) * 100
                
                print(f"\n📊 ANÁLISIS TÉCNICO ACTUAL:")
                print(f"   Vela 1H: Open ${open_price:,.2f} | High ${high_price:,.2f} | Low ${low_price:,.2f}")
                print(f"   Posición en vela: {candle_position*100:.1f}% {'(cerca del high)' if candle_position > 0.7 else '(cerca del low)' if candle_position < 0.3 else '(medio)'}")
                print(f"   Cambio vela: {candle_change:+.2f}%")
            
            print(f"\n🎯 ANÁLISIS DE NIVELES:")
            
            # Support levels
            print(f"📈 SOPORTE (para stops):")
            strongest_support = None
            for i, level in enumerate(support_levels[:3]):
                strength_emoji = "🟢" if level["strength"] == "HIGH" else "🟡"
                print(f"   {i+1}. {strength_emoji} ${level['price']:,.2f} (Vol: {level['volume']:,.0f}, -{level['distance_pct']:.2f}%)")
                if not strongest_support or level['volume'] > strongest_support['volume']:
                    strongest_support = level
            
            # Resistance levels  
            print(f"📉 RESISTENCIA (para targets):")
            nearest_resistance = None
            for i, level in enumerate(resistance_levels[:3]):
                strength_emoji = "🔴" if level["strength"] == "HIGH" else "🟡"
                print(f"   {i+1}. {strength_emoji} ${level['price']:,.2f} (Vol: {level['volume']:,.0f}, +{level['distance_pct']:.2f}%)")
                if not nearest_resistance or level['distance_pct'] < nearest_resistance['distance_pct']:
                    nearest_resistance = level
            
            # Large orders cerca del precio
            print(f"\n🐋 ÓRDENES GRANDES CERCANAS:")
            nearby_bids = [bid for bid in large_orders['large_bids'] if bid['distance_pct'] < 3.0]
            nearby_asks = [ask for ask in large_orders['large_asks'] if ask['distance_pct'] < 3.0]
            
            for bid in nearby_bids[:3]:
                print(f"   🟢 BID: ${bid['price']:,.2f} (${bid['usd_value']/1000:,.0f}k) -{bid['distance_pct']:.2f}%")
            
            for ask in nearby_asks[:3]:
                print(f"   🔴 ASK: ${ask['price']:,.2f} (${ask['usd_value']/1000:,.0f}k) +{ask['distance_pct']:.2f}%")
            
            # GENERAR SEÑAL
            print(f"\n" + "="*50)
            print(f"🎯 SEÑAL BNB LONG")
            print(f"="*50)
            
            # Entry strategy basada en liquidez
            if imbalance > 20:  # Fuerte imbalance bullish
                if candle_position < 0.5:
                    entry_price = current_price + (current_price * 0.001)  # Market buy con slippage
                    entry_reason = "MARKET BUY - Strong bid pressure + low in candle"
                else:
                    entry_price = current_price - (current_price * 0.002)  # Limit order
                    entry_reason = "LIMIT ORDER - Wait for small pullback"
            else:
                entry_price = current_price - (current_price * 0.0015)  # Conservative entry
                entry_reason = "CONSERVATIVE ENTRY - Wait for better price"
            
            # Stop loss basado en soporte de liquidez
            if strongest_support:
                stop_loss = strongest_support['price'] * 0.995  # 0.5% below strongest support
                stop_reason = f"Below strongest liquidity support (${strongest_support['price']:,.2f})"
            else:
                stop_loss = current_price * 0.975  # 2.5% stop
                stop_reason = "Technical stop (2.5%)"
            
            # Take profit basado en resistencia
            if nearest_resistance:
                take_profit = nearest_resistance['price'] * 0.995  # Just below resistance
                tp_reason = f"Just below nearest resistance (${nearest_resistance['price']:,.2f})"
            else:
                take_profit = current_price * 1.04  # 4% target
                tp_reason = "Technical target (4%)"
            
            # Position sizing
            capital = 220.0
            risk_per_trade = 0.02
            leverage = 3
            
            risk_amount = capital * risk_per_trade
            risk_distance = abs(entry_price - stop_loss) / entry_price
            position_size_usd = (risk_amount * leverage) / risk_distance
            position_size_bnb = position_size_usd / entry_price
            
            potential_profit = (take_profit - entry_price) / entry_price * position_size_usd
            risk_reward_ratio = potential_profit / risk_amount
            
            print(f"💡 ENTRY PRICE: ${entry_price:,.2f}")
            print(f"   Razón: {entry_reason}")
            print(f"   Distancia del precio actual: {((entry_price - current_price) / current_price) * 100:+.3f}%")
            
            print(f"\n🛡️ STOP LOSS: ${stop_loss:,.2f}")
            print(f"   Razón: {stop_reason}")
            print(f"   Riesgo: {((entry_price - stop_loss) / entry_price) * 100:.2f}%")
            
            print(f"\n🎯 TAKE PROFIT: ${take_profit:,.2f}")
            print(f"   Razón: {tp_reason}")
            print(f"   Ganancia: {((take_profit - entry_price) / entry_price) * 100:.2f}%")
            
            print(f"\n📊 POSITION SIZING:")
            print(f"   Capital: ${capital:,.2f}")
            print(f"   Riesgo por trade: {risk_per_trade*100}%")
            print(f"   Leverage: {leverage}x")
            print(f"   Position size: {position_size_bnb:.4f} BNB (${position_size_usd:,.2f})")
            print(f"   Riesgo máximo: ${risk_amount:,.2f}")
            print(f"   Ganancia potencial: ${potential_profit:,.2f}")
            print(f"   Risk/Reward: 1:{risk_reward_ratio:.2f}")
            
            # Condiciones de mercado
            print(f"\n⚠️ CONDICIONES PARA ENTRADA:")
            print(f"   ✓ Imbalance bullish: {imbalance:+.1f}% (>+10% requerido)")
            print(f"   ✓ Whale activity: {'SÍ' if large_orders['whale_activity'] else 'NO'}")
            print(f"   ✓ Liquidez: Excelente (spread {ob_analysis.get('spread_bps', 0):.2f} bps)")
            print(f"   ✓ Risk/Reward: 1:{risk_reward_ratio:.2f} (>1.5 requerido)")
            
            # Timing
            print(f"\n⏰ TIMING:")
            print(f"   Señal generada: {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Validez: 15 minutos (condiciones de liquidez cambian rápido)")
            print(f"   Monitor: Verificar imbalance antes de ejecutar")
            
            if imbalance > 10 and risk_reward_ratio > 1.5:
                print(f"\n✅ SEÑAL VÁLIDA - EJECUTAR")
            else:
                print(f"\n⚠️ SEÑAL CONDICIONAL - VERIFICAR CONDICIONES")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(generate_bnb_signal())