#!/usr/bin/env python3
"""
Análisis Completo en Tiempo Real
Considera TODAS las variables: técnicas, liquidez, block orders, funding, etc.
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime
import json

class ComprehensiveAnalyzer:
    """Análisis completo considerando todas las variables"""
    
    def __init__(self):
        self.api_base = "http://localhost:8002"
        
    async def get_complete_analysis(self, symbol: str):
        """Obtiene análisis completo de un símbolo"""
        
        async with httpx.AsyncClient() as client:
            try:
                # Obtener datos en paralelo
                tasks = [
                    client.get(f"{self.api_base}/api/liquidity/{symbol}"),
                    client.get(f"{self.api_base}/api/block-orders/{symbol}"),
                    self._get_market_data(symbol),
                    self._get_funding_sentiment(symbol)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                liquidity_data = results[0].json() if not isinstance(results[0], Exception) and results[0].status_code == 200 else {}
                block_orders = results[1].json() if not isinstance(results[1], Exception) and results[1].status_code == 200 else {}
                market_data = results[2] if not isinstance(results[2], Exception) else {}
                funding_data = results[3] if not isinstance(results[3], Exception) else {}
                
                # Compilar análisis completo
                analysis = self._compile_comprehensive_analysis(
                    symbol, liquidity_data, block_orders, market_data, funding_data
                )
                
                return analysis
                
            except Exception as e:
                return {"error": f"Error analyzing {symbol}: {e}"}
    
    async def _get_market_data(self, symbol: str):
        """Obtiene datos de mercado técnicos"""
        try:
            async with httpx.AsyncClient() as client:
                # Price data
                price_response = await client.get(
                    "https://fapi.binance.com/fapi/v1/ticker/price",
                    params={"symbol": symbol}
                )
                
                # 24h stats
                stats_response = await client.get(
                    "https://fapi.binance.com/fapi/v1/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                # Recent klines for indicators
                klines_response = await client.get(
                    "https://fapi.binance.com/fapi/v1/klines",
                    params={"symbol": symbol, "interval": "1h", "limit": 50}
                )
                
                market_data = {}
                
                if price_response.status_code == 200:
                    market_data["current_price"] = float(price_response.json()["price"])
                
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    market_data["24h_change"] = float(stats["priceChangePercent"])
                    market_data["24h_volume"] = float(stats["volume"])
                    market_data["high_24h"] = float(stats["highPrice"])
                    market_data["low_24h"] = float(stats["lowPrice"])
                
                if klines_response.status_code == 200:
                    klines = klines_response.json()
                    df = pd.DataFrame(klines, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote', 'ignore'
                    ])
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    # Calculate indicators
                    indicators = self._calculate_technical_indicators(df)
                    market_data["indicators"] = indicators
                
                return market_data
                
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> dict:
        """Calcula indicadores técnicos avanzados"""
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 0.00001)
        rsi = 100 - (100 / (1 + rs))
        
        # EMAs
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = macd - macd_signal
        
        # Bollinger Bands
        bb_middle = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        bb_position = (df['close'] - bb_lower) / (bb_upper - bb_lower + 0.00001)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        atr = ranges.max(axis=1).rolling(14).mean()
        
        # Volume indicators
        volume_sma = df['volume'].rolling(20).mean()
        volume_ratio = df['volume'] / volume_sma
        
        # Trend indicators
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        last_idx = -1
        
        return {
            "rsi": float(rsi.iloc[last_idx]) if not pd.isna(rsi.iloc[last_idx]) else 50,
            "rsi_signal": "OVERSOLD" if rsi.iloc[last_idx] < 30 else "OVERBOUGHT" if rsi.iloc[last_idx] > 70 else "NEUTRAL",
            "macd": float(macd.iloc[last_idx]) if not pd.isna(macd.iloc[last_idx]) else 0,
            "macd_histogram": float(macd_histogram.iloc[last_idx]) if not pd.isna(macd_histogram.iloc[last_idx]) else 0,
            "macd_signal": "BULLISH" if macd_histogram.iloc[last_idx] > 0 else "BEARISH",
            "bb_position": float(bb_position.iloc[last_idx]) if not pd.isna(bb_position.iloc[last_idx]) else 0.5,
            "bb_signal": "OVERSOLD" if bb_position.iloc[last_idx] < 0.2 else "OVERBOUGHT" if bb_position.iloc[last_idx] > 0.8 else "NEUTRAL",
            "atr": float(atr.iloc[last_idx]) if not pd.isna(atr.iloc[last_idx]) else 0,
            "volume_ratio": float(volume_ratio.iloc[last_idx]) if not pd.isna(volume_ratio.iloc[last_idx]) else 1.0,
            "volume_signal": "HIGH" if volume_ratio.iloc[last_idx] > 1.5 else "LOW" if volume_ratio.iloc[last_idx] < 0.8 else "NORMAL",
            "trend": "UPTREND" if ema_20.iloc[last_idx] > ema_50.iloc[last_idx] else "DOWNTREND",
            "trend_strength": abs(float(ema_20.iloc[last_idx] - ema_50.iloc[last_idx])) / float(df['close'].iloc[last_idx]) * 100
        }
    
    async def _get_funding_sentiment(self, symbol: str):
        """Obtiene datos de funding y sentiment"""
        try:
            async with httpx.AsyncClient() as client:
                # Funding rate
                funding_response = await client.get(
                    "https://fapi.binance.com/fapi/v1/fundingRate",
                    params={"symbol": symbol, "limit": 3}
                )
                
                # Long/Short ratio
                ratio_response = await client.get(
                    "https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio",
                    params={"symbol": symbol, "period": "1h", "limit": 3}
                )
                
                # Open Interest
                oi_response = await client.get(
                    "https://fapi.binance.com/fapi/v1/openInterest",
                    params={"symbol": symbol}
                )
                
                funding_data = {}
                
                if funding_response.status_code == 200:
                    funding = funding_response.json()
                    if funding:
                        current_funding = float(funding[0]["fundingRate"]) * 100
                        avg_funding = np.mean([float(f["fundingRate"]) * 100 for f in funding[:3]])
                        
                        funding_data["funding_rate"] = {
                            "current": current_funding,
                            "average_3h": avg_funding,
                            "interpretation": self._interpret_funding(current_funding),
                            "trend": "INCREASING" if len(funding) > 1 and current_funding > float(funding[1]["fundingRate"]) * 100 else "DECREASING"
                        }
                
                if ratio_response.status_code == 200:
                    ratios = ratio_response.json()
                    if ratios:
                        current_ratio = float(ratios[0]["longShortRatio"])
                        avg_ratio = np.mean([float(r["longShortRatio"]) for r in ratios[:3]])
                        
                        funding_data["long_short_ratio"] = {
                            "current": current_ratio,
                            "average": avg_ratio,
                            "interpretation": self._interpret_ratio(current_ratio),
                            "squeeze_risk": "HIGH" if current_ratio < 0.6 else "LOW" if current_ratio > 1.5 else "MEDIUM"
                        }
                
                if oi_response.status_code == 200:
                    oi = oi_response.json()
                    funding_data["open_interest"] = {
                        "value": float(oi["openInterest"]),
                        "sum_value": float(oi["sumOpenInterest"]),
                        "interpretation": "HIGH_ACTIVITY" if float(oi["openInterest"]) > 50000 else "NORMAL_ACTIVITY"
                    }
                
                return funding_data
                
        except Exception as e:
            return {"error": str(e)}
    
    def _interpret_funding(self, funding_rate: float) -> str:
        """Interpreta funding rate"""
        if funding_rate > 0.02:
            return "EXTREME_BULLISH_PRESSURE"
        elif funding_rate > 0.01:
            return "BULLISH_PRESSURE"
        elif funding_rate > -0.01:
            return "NEUTRAL"
        elif funding_rate > -0.02:
            return "BEARISH_PRESSURE"
        else:
            return "EXTREME_BEARISH_PRESSURE"
    
    def _interpret_ratio(self, ratio: float) -> str:
        """Interpreta long/short ratio"""
        if ratio > 2.0:
            return "EXTREMELY_LONG_HEAVY"
        elif ratio > 1.5:
            return "LONG_HEAVY"
        elif ratio > 0.8:
            return "BALANCED"
        elif ratio > 0.5:
            return "SHORT_HEAVY"
        else:
            return "EXTREMELY_SHORT_HEAVY"
    
    def _compile_comprehensive_analysis(self, symbol: str, liquidity_data: dict, block_orders: dict, market_data: dict, funding_data: dict) -> dict:
        """Compila análisis completo considerando todas las variables"""
        
        analysis = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "overall_signal": "NEUTRAL",
            "confidence": 0,
            "entry_recommendation": "WAIT",
            "risk_level": "MEDIUM",
            "key_factors": [],
            "detailed_analysis": {}
        }
        
        # Variables para scoring
        bullish_score = 0
        bearish_score = 0
        confidence_factors = []
        risk_factors = []
        
        # 1. ANÁLISIS TÉCNICO
        if "indicators" in market_data:
            indicators = market_data["indicators"]
            
            # RSI Analysis
            if indicators["rsi_signal"] == "OVERSOLD":
                bullish_score += 15
                confidence_factors.append(f"RSI oversold ({indicators['rsi']:.1f})")
            elif indicators["rsi_signal"] == "OVERBOUGHT":
                bearish_score += 15
                confidence_factors.append(f"RSI overbought ({indicators['rsi']:.1f})")
            
            # MACD Analysis
            if indicators["macd_signal"] == "BULLISH" and indicators["macd_histogram"] > 0:
                bullish_score += 12
                confidence_factors.append("MACD bullish crossover")
            elif indicators["macd_signal"] == "BEARISH" and indicators["macd_histogram"] < 0:
                bearish_score += 12
                confidence_factors.append("MACD bearish crossover")
            
            # Bollinger Bands
            if indicators["bb_signal"] == "OVERSOLD":
                bullish_score += 10
                confidence_factors.append(f"BB oversold ({indicators['bb_position']:.2f})")
            elif indicators["bb_signal"] == "OVERBOUGHT":
                bearish_score += 10
                confidence_factors.append(f"BB overbought ({indicators['bb_position']:.2f})")
            
            # Volume
            if indicators["volume_signal"] == "HIGH":
                # High volume confirms the signal
                confidence_factors.append("High volume confirmation")
                if bullish_score > bearish_score:
                    bullish_score += 8
                else:
                    bearish_score += 8
            
            # Trend
            if indicators["trend"] == "UPTREND" and indicators["trend_strength"] > 1:
                bullish_score += 8
                confidence_factors.append(f"Strong uptrend ({indicators['trend_strength']:.2f}%)")
            elif indicators["trend"] == "DOWNTREND" and indicators["trend_strength"] > 1:
                bearish_score += 8
                confidence_factors.append(f"Strong downtrend ({indicators['trend_strength']:.2f}%)")
        
        # 2. ANÁLISIS DE LIQUIDEZ
        if "order_book_analysis" in liquidity_data:
            ob_analysis = liquidity_data["order_book_analysis"]
            
            # Order Book Imbalance
            if "imbalance" in ob_analysis:
                imbalance = ob_analysis["imbalance"]
                if imbalance > 20:
                    bullish_score += 12
                    confidence_factors.append(f"Strong bid imbalance ({imbalance:.1f}%)")
                elif imbalance < -20:
                    bearish_score += 12
                    confidence_factors.append(f"Strong ask imbalance ({imbalance:.1f}%)")
                elif abs(imbalance) > 10:
                    score = 6 if imbalance > 0 else -6
                    if imbalance > 0:
                        bullish_score += 6
                    else:
                        bearish_score += 6
                    confidence_factors.append(f"Moderate imbalance ({imbalance:.1f}%)")
            
            # Large Orders Analysis
            if "large_orders" in ob_analysis:
                large_orders = ob_analysis["large_orders"]
                
                # Whale activity
                if large_orders.get("whale_activity"):
                    confidence_factors.append("🐋 WHALE ACTIVITY DETECTED")
                    analysis["risk_level"] = "HIGH"
                
                # Large bids (support)
                large_bids_count = len(large_orders.get("large_bids", []))
                large_asks_count = len(large_orders.get("large_asks", []))
                
                if large_bids_count > large_asks_count:
                    bullish_score += 10
                    confidence_factors.append(f"More large bids than asks ({large_bids_count} vs {large_asks_count})")
                elif large_asks_count > large_bids_count:
                    bearish_score += 10
                    confidence_factors.append(f"More large asks than bids ({large_asks_count} vs {large_bids_count})")
                
                # Check nearby large orders
                current_price = ob_analysis.get("current_price", 0)
                if current_price > 0:
                    nearby_support = [
                        bid for bid in large_orders.get("large_bids", [])
                        if bid["distance_pct"] < 2.0
                    ]
                    nearby_resistance = [
                        ask for ask in large_orders.get("large_asks", [])
                        if ask["distance_pct"] < 2.0
                    ]
                    
                    if nearby_support:
                        bullish_score += 8
                        total_support_value = sum([bid["usd_value"] for bid in nearby_support])
                        confidence_factors.append(f"Large support nearby (${total_support_value/1000:.0f}k)")
                    
                    if nearby_resistance:
                        bearish_score += 8
                        total_resistance_value = sum([ask["usd_value"] for ask in nearby_resistance])
                        confidence_factors.append(f"Large resistance nearby (${total_resistance_value/1000:.0f}k)")
            
            # Spread Analysis
            if "spread_bps" in ob_analysis:
                spread = ob_analysis["spread_bps"]
                if spread < 1:
                    confidence_factors.append("Excellent liquidity (tight spread)")
                elif spread > 10:
                    risk_factors.append("Poor liquidity (wide spread)")
                    analysis["risk_level"] = "HIGH"
        
        # 3. FUNDING & SENTIMENT ANALYSIS
        if "funding_rate" in funding_data:
            funding = funding_data["funding_rate"]
            
            if funding["interpretation"] == "EXTREME_BULLISH_PRESSURE":
                bearish_score += 15  # Contrarian
                confidence_factors.append(f"Extreme positive funding ({funding['current']:.3f}%) - contrarian short setup")
            elif funding["interpretation"] == "EXTREME_BEARISH_PRESSURE":
                bullish_score += 15  # Contrarian
                confidence_factors.append(f"Extreme negative funding ({funding['current']:.3f}%) - contrarian long setup")
            elif funding["interpretation"] == "BULLISH_PRESSURE":
                bearish_score += 8
                confidence_factors.append(f"Positive funding ({funding['current']:.3f}%) - mild short bias")
            elif funding["interpretation"] == "BEARISH_PRESSURE":
                bullish_score += 8
                confidence_factors.append(f"Negative funding ({funding['current']:.3f}%) - mild long bias")
        
        if "long_short_ratio" in funding_data:
            ratio_data = funding_data["long_short_ratio"]
            
            if ratio_data["interpretation"] == "EXTREMELY_LONG_HEAVY":
                bearish_score += 20
                risk_factors.append(f"EXTREME long imbalance ({ratio_data['current']:.2f}) - liquidation cascade risk")
                confidence_factors.append("Long liquidation cascade setup")
            elif ratio_data["interpretation"] == "LONG_HEAVY":
                bearish_score += 12
                confidence_factors.append(f"Long heavy ({ratio_data['current']:.2f}) - short opportunity")
            elif ratio_data["interpretation"] == "EXTREMELY_SHORT_HEAVY":
                bullish_score += 20
                risk_factors.append(f"EXTREME short imbalance ({ratio_data['current']:.2f}) - short squeeze risk")
                confidence_factors.append("Short squeeze setup")
            elif ratio_data["interpretation"] == "SHORT_HEAVY":
                bullish_score += 12
                confidence_factors.append(f"Short heavy ({ratio_data['current']:.2f}) - long opportunity")
        
        # 4. PRICE ACTION ANALYSIS
        if "24h_change" in market_data:
            change_24h = market_data["24h_change"]
            
            if abs(change_24h) > 5:
                if change_24h > 5:
                    risk_factors.append(f"Large 24h pump ({change_24h:.1f}%) - potential reversal")
                else:
                    risk_factors.append(f"Large 24h dump ({change_24h:.1f}%) - potential bounce")
            
            # Price position in 24h range
            if "current_price" in market_data and "high_24h" in market_data and "low_24h" in market_data:
                current = market_data["current_price"]
                high_24h = market_data["high_24h"]
                low_24h = market_data["low_24h"]
                
                range_position = (current - low_24h) / (high_24h - low_24h) if high_24h != low_24h else 0.5
                
                if range_position < 0.2:
                    bullish_score += 8
                    confidence_factors.append(f"Near 24h low ({range_position*100:.0f}% of range)")
                elif range_position > 0.8:
                    bearish_score += 8
                    confidence_factors.append(f"Near 24h high ({range_position*100:.0f}% of range)")
        
        # 5. LIQUIDATION ANALYSIS
        if "liquidation_analysis" in liquidity_data:
            liq_analysis = liquidity_data["liquidation_analysis"]
            
            if "liquidation_zones" in liq_analysis:
                zones = liq_analysis["liquidation_zones"]
                
                # Check for high risk zones
                high_risk_zones = zones.get("high_risk_zones", [])
                for zone in high_risk_zones:
                    if zone["risk_level"] == "HIGH":
                        risk_factors.append(f"HIGH RISK: {zone['reason']} - potential {zone['direction']} cascade")
                        
                        if zone["direction"] == "DOWN":
                            bearish_score += 15
                        else:
                            bullish_score += 15
        
        # 6. COMPILAR RESULTADO FINAL
        net_score = bullish_score - bearish_score
        total_score = bullish_score + bearish_score
        
        # Determinar señal principal
        if net_score > 15:
            analysis["overall_signal"] = "STRONG_BULLISH"
        elif net_score > 5:
            analysis["overall_signal"] = "BULLISH"
        elif net_score < -15:
            analysis["overall_signal"] = "STRONG_BEARISH"
        elif net_score < -5:
            analysis["overall_signal"] = "BEARISH"
        else:
            analysis["overall_signal"] = "NEUTRAL"
        
        # Calcular confianza
        analysis["confidence"] = min(100, total_score * 2)
        
        # Determinar recomendación de entrada
        if analysis["confidence"] > 70 and abs(net_score) > 10:
            if net_score > 0:
                analysis["entry_recommendation"] = "LONG"
            else:
                analysis["entry_recommendation"] = "SHORT"
        elif analysis["confidence"] > 50 and abs(net_score) > 15:
            if net_score > 0:
                analysis["entry_recommendation"] = "LONG"
            else:
                analysis["entry_recommendation"] = "SHORT"
        else:
            analysis["entry_recommendation"] = "WAIT"
        
        # Nivel de riesgo
        if len(risk_factors) > 2 or any("EXTREME" in factor for factor in risk_factors):
            analysis["risk_level"] = "HIGH"
        elif len(risk_factors) > 0:
            analysis["risk_level"] = "MEDIUM"
        else:
            analysis["risk_level"] = "LOW"
        
        # Factores clave
        analysis["key_factors"] = confidence_factors[:8]  # Top 8 factors
        analysis["risk_factors"] = risk_factors
        
        # Análisis detallado
        analysis["detailed_analysis"] = {
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "net_score": net_score,
            "technical_analysis": market_data.get("indicators", {}),
            "liquidity_summary": {
                "imbalance": liquidity_data.get("order_book_analysis", {}).get("imbalance", 0),
                "whale_activity": liquidity_data.get("order_book_analysis", {}).get("large_orders", {}).get("whale_activity", False),
                "spread_quality": "EXCELLENT" if liquidity_data.get("order_book_analysis", {}).get("spread_bps", 100) < 1 else "GOOD"
            },
            "funding_summary": funding_data,
            "market_context": {
                "24h_change": market_data.get("24h_change", 0),
                "current_price": market_data.get("current_price", 0)
            }
        }
        
        return analysis

async def main():
    """Analiza BTC, SOL y BNB con TODAS las variables"""
    
    print("="*80)
    print("ANÁLISIS COMPLETO - TODAS LAS VARIABLES")
    print("="*80)
    print("Considerando: Técnicos, Liquidez, Block Orders, Funding, Sentiment, Liquidaciones")
    print("="*80)
    
    analyzer = ComprehensiveAnalyzer()
    
    symbols = ["BTCUSDT", "SOLUSDT", "BNBUSDT"]
    
    for symbol in symbols:
        print(f"\n🔍 ANÁLISIS COMPLETO: {symbol}")
        print("="*60)
        
        analysis = await analyzer.get_complete_analysis(symbol)
        
        if "error" in analysis:
            print(f"❌ Error: {analysis['error']}")
            continue
        
        # RESUMEN EJECUTIVO
        signal_emoji = "🟢" if "BULLISH" in analysis["overall_signal"] else "🔴" if "BEARISH" in analysis["overall_signal"] else "⚪"
        risk_emoji = "🔴" if analysis["risk_level"] == "HIGH" else "🟡" if analysis["risk_level"] == "MEDIUM" else "🟢"
        
        print(f"\n📊 RESUMEN EJECUTIVO:")
        print(f"   Señal: {signal_emoji} {analysis['overall_signal']} (Confianza: {analysis['confidence']}%)")
        print(f"   Recomendación: {analysis['entry_recommendation']}")
        print(f"   Nivel de Riesgo: {risk_emoji} {analysis['risk_level']}")
        print(f"   Precio Actual: ${analysis['detailed_analysis']['market_context']['current_price']:,.2f}")
        print(f"   Cambio 24h: {analysis['detailed_analysis']['market_context']['24h_change']:+.2f}%")
        
        # FACTORES CLAVE
        print(f"\n🔑 FACTORES CLAVE ({len(analysis['key_factors'])} detectados):")
        for i, factor in enumerate(analysis['key_factors'], 1):
            print(f"   {i}. {factor}")
        
        # FACTORES DE RIESGO
        if analysis['risk_factors']:
            print(f"\n⚠️ FACTORES DE RIESGO:")
            for risk in analysis['risk_factors']:
                print(f"   • {risk}")
        
        # ANÁLISIS TÉCNICO DETALLADO
        tech = analysis['detailed_analysis']['technical_analysis']
        if tech:
            print(f"\n📈 TÉCNICO:")
            print(f"   RSI: {tech['rsi']:.1f} ({tech['rsi_signal']})")
            print(f"   MACD: {tech['macd_signal']} (Histogram: {tech['macd_histogram']:.4f})")
            print(f"   BB: {tech['bb_signal']} (Posición: {tech['bb_position']:.2f})")
            print(f"   Tendencia: {tech['trend']} (Fuerza: {tech['trend_strength']:.2f}%)")
            print(f"   Volumen: {tech['volume_signal']} (Ratio: {tech['volume_ratio']:.2f}x)")
        
        # ANÁLISIS DE LIQUIDEZ
        liq = analysis['detailed_analysis']['liquidity_summary']
        print(f"\n💧 LIQUIDEZ:")
        print(f"   Imbalance: {liq['imbalance']:+.1f}% {'(Más bids)' if liq['imbalance'] > 0 else '(Más asks)'}")
        print(f"   Whale Activity: {'🐋 SÍ' if liq['whale_activity'] else '❌ No'}")
        print(f"   Calidad Spread: {liq['spread_quality']}")
        
        # FUNDING & SENTIMENT
        funding = analysis['detailed_analysis']['funding_summary']
        if 'funding_rate' in funding:
            fr = funding['funding_rate']
            print(f"\n💰 FUNDING & SENTIMENT:")
            print(f"   Funding Rate: {fr['current']:+.3f}% ({fr['interpretation']})")
            print(f"   Tendencia: {fr['trend']}")
        
        if 'long_short_ratio' in funding:
            lsr = funding['long_short_ratio']
            print(f"   Long/Short Ratio: {lsr['current']:.2f} ({lsr['interpretation']})")
            print(f"   Riesgo Squeeze: {lsr['squeeze_risk']}")
        
        # SCORES INTERNOS
        scores = analysis['detailed_analysis']
        print(f"\n🎯 SCORES INTERNOS:")
        print(f"   Bullish Score: +{scores['bullish_score']}")
        print(f"   Bearish Score: -{scores['bearish_score']}")
        print(f"   Score Neto: {scores['net_score']:+d}")
        
        print(f"\n{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())