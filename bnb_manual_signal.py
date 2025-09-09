#!/usr/bin/env python3
"""
Señal Manual BNB - Con Correlación BTC
"""

import asyncio
import httpx
from btc_correlation_analyzer import BTCCorrelationAnalyzer

async def manual_bnb_signal():
    """Señal BNB con análisis de correlación BTC"""
    
    # Inicializar analizador BTC
    btc_analyzer = BTCCorrelationAnalyzer()
    
    print("🎯 SEÑAL BNB LONG - CON BTC CORRELATION")
    print("="*50)
    
    # Análisis BTC primero
    print("🔍 ANALIZANDO BTC...")
    btc_analysis = await btc_analyzer.get_btc_analysis()
    correlation_data = await btc_analyzer.get_altcoin_correlation("BNBUSDT")
    
    print(f"💰 BTC: ${btc_analysis.get('current_price', 0):,.0f}")
    print(f"📊 Resistencia 110k: {'PROBADA' if btc_analysis.get('resistance_110k', {}).get('tested') else 'No probada'}")
    print(f"📉 Pullback prob: {btc_analysis.get('pullback_probability', {}).get('probability', 0)*100:.0f}%")
    print(f"🔗 BNB-BTC correlation: {correlation_data.get('correlation', 0):.3f}")
    print(f"📈 BNB Beta: {correlation_data.get('beta', 0):.2f}")
    print()
    
    # Datos actuales
    current_price = 878.08
    imbalance = 4.6  # Positivo pero no extremo
    whale_activity = True
    large_bids = 5
    large_asks = 4
    
    print(f"💰 Precio actual: ${current_price}")
    print(f"📊 Order book imbalance: +{imbalance}%")
    print(f"🐋 Whale activity: {'SÍ' if whale_activity else 'No'}")
    
    # Análisis de 24h para contexto
    async with httpx.AsyncClient() as client:
        stats_response = await client.get(
            "https://fapi.binance.com/fapi/v1/ticker/24hr",
            params={"symbol": "BNBUSDT"}
        )
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            high_24h = float(stats["highPrice"])
            low_24h = float(stats["lowPrice"])
            change_24h = float(stats["priceChangePercent"])
            
            range_position = (current_price - low_24h) / (high_24h - low_24h)
            
            print(f"📈 24h High: ${high_24h}")
            print(f"📉 24h Low: ${low_24h}")
            print(f"📊 24h Change: {change_24h:+.2f}%")
            print(f"📍 Posición en rango 24h: {range_position*100:.1f}%")
    
    print(f"\n🎯 SETUP DE TRADING:")
    
    # Entry logic con BTC correlation
    btc_pullback_prob = btc_analysis.get('pullback_probability', {}).get('probability', 0)
    correlation = correlation_data.get('correlation', 0)
    beta = correlation_data.get('beta', 0)
    
    # Ajustar entry basado en BTC
    btc_risk_adjustment = 1.0
    if btc_pullback_prob > 0.7:  # Alta probabilidad BTC pullback
        if correlation > 0.5:  # BNB correlacionado
            btc_risk_adjustment = 1.5  # Más conservador
            entry_reason_btc = "BTC high pullback risk - correlación positiva"
        else:
            btc_risk_adjustment = 1.1
            entry_reason_btc = "BTC risk moderado - correlación baja"
    else:
        entry_reason_btc = "BTC condiciones favorables"
    
    if current_price > 875:  # Cerca del high
        pullback_distance = 0.005 * btc_risk_adjustment  # 0.5% más si BTC riesgoso
        entry_price = current_price * (1 - pullback_distance)
        entry_type = "LIMIT ORDER"
        entry_reason = f"Pullback entry (BTC adj: {btc_risk_adjustment:.1f}x) - {entry_reason_btc}"
    else:
        entry_price = current_price + 1.0  # Market buy
        entry_type = "MARKET ORDER" 
        entry_reason = f"Market buy - {entry_reason_btc}"
    
    # Stops basados en estructura técnica
    stop_loss = 865.00  # Strong support level
    take_profit_1 = 885.00  # First resistance
    take_profit_2 = 895.00  # Major resistance
    
    # Position sizing
    capital = 220.0
    risk_pct = 0.02
    leverage = 3
    
    risk_amount = capital * risk_pct  # $4.40
    risk_per_coin = entry_price - stop_loss  # Risk per BNB
    position_size_bnb = risk_amount / risk_per_coin  # Position size
    position_value = position_size_bnb * entry_price
    
    # Profits calculation
    profit_1 = (take_profit_1 - entry_price) * position_size_bnb
    profit_2 = (take_profit_2 - entry_price) * position_size_bnb
    
    rr_ratio_1 = profit_1 / risk_amount
    rr_ratio_2 = profit_2 / risk_amount
    
    print(f"💡 ENTRADA:")
    print(f"   Tipo: {entry_type}")
    print(f"   Precio: ${entry_price}")
    print(f"   Razón: {entry_reason}")
    
    print(f"\n🛡️ GESTIÓN DE RIESGO:")
    print(f"   Stop Loss: ${stop_loss}")
    print(f"   Riesgo por moneda: ${risk_per_coin:.2f}")
    print(f"   Riesgo total: ${risk_amount:.2f}")
    
    print(f"\n🎯 OBJETIVOS:")
    print(f"   TP1: ${take_profit_1} (R/R: 1:{rr_ratio_1:.2f})")
    print(f"   TP2: ${take_profit_2} (R/R: 1:{rr_ratio_2:.2f})")
    
    print(f"\n📊 POSITION SIZING:")
    print(f"   Capital: ${capital}")
    print(f"   Leverage: {leverage}x")
    print(f"   Position: {position_size_bnb:.4f} BNB")
    print(f"   Value: ${position_value:.2f}")
    print(f"   Max Risk: ${risk_amount:.2f} ({risk_pct*100}%)")
    
    print(f"\n✅ PLAN DE EJECUCIÓN:")
    print(f"   1. Colocar orden limit en ${entry_price}")
    print(f"   2. Stop loss inmediato en ${stop_loss}")
    print(f"   3. Vender 50% en ${take_profit_1}")
    print(f"   4. Mover stop a breakeven")
    print(f"   5. Vender resto en ${take_profit_2}")
    
    # Validaciones con BTC context
    print(f"\n⚠️ VALIDACIONES:")
    valid_rr = rr_ratio_1 > 1.5
    valid_imbalance = imbalance > 0
    valid_whale = whale_activity
    valid_btc = btc_pullback_prob < 0.8  # BTC no muy riesgoso
    
    print(f"   R/R Ratio: {'✅' if valid_rr else '❌'} {rr_ratio_1:.2f} (>1.5)")
    print(f"   Imbalance: {'✅' if valid_imbalance else '❌'} +{imbalance}% (>0%)")
    print(f"   Whale Activity: {'✅' if valid_whale else '❌'}")
    print(f"   BTC Risk: {'✅' if valid_btc else '⚠️'} {btc_pullback_prob*100:.0f}% pullback prob (<80%)")
    
    # BTC warning específico
    if btc_pullback_prob > 0.7:
        print(f"\n🟡 ALERTA BTC:")
        print(f"   BTC probando resistencia 110k con {btc_pullback_prob*100:.0f}% prob pullback")
        if correlation > 0.5:
            expected_bnb_drop = abs(((110000 - btc_analysis['current_price']) / btc_analysis['current_price']) * beta)
            print(f"   Si BTC cae a 110k, BNB podría caer {expected_bnb_drop*100:.1f}% por correlación")
    
    if valid_rr and valid_imbalance and valid_whale and valid_btc:
        print(f"\n🟢 SEÑAL VÁLIDA - EJECUTAR TRADE")
        print(f"Confianza: ALTA")
        print(f"Timeframe óptimo: 1H-4H")
    elif valid_rr and valid_imbalance and valid_whale:
        print(f"\n🟡 SEÑAL CONDICIONAL - MONITOR BTC")
        print(f"Confianza: MEDIA (riesgo BTC)")
        print(f"Acción: Esperar confirmación BTC o entry más conservador")
    else:
        print(f"\n🔴 SEÑAL NO VÁLIDA - ESPERAR MEJORES CONDICIONES")
    
    print(f"\n⏰ Válido por: 30 minutos")
    print(f"🔄 Re-evaluar si precio cambia >1%")

if __name__ == "__main__":
    asyncio.run(manual_bnb_signal())