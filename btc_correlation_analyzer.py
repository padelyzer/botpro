#!/usr/bin/env python3
"""
BTC Correlation Analyzer for Altcoins
Analiza correlación con BTC y liquidez debajo de niveles clave
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

class BTCCorrelationAnalyzer:
    """
    Analiza correlación de altcoins con BTC y zonas de liquidez
    """
    
    def __init__(self):
        self.binance_base = "https://fapi.binance.com/fapi/v1"
        self.spot_base = "https://api.binance.com/api/v3"
        self.liquidity_endpoint = "http://localhost:8002/api/liquidity"
    
    async def get_btc_analysis(self) -> Dict:
        """
        Analiza situación actual de BTC y liquidez debajo de 110k
        """
        async with httpx.AsyncClient() as client:
            try:
                # Precio actual BTC
                ticker = await client.get(f"{self.spot_base}/ticker/price", params={"symbol": "BTCUSDT"})
                current_btc = float(ticker.json()["price"])
                
                # Order book profundo para BTC
                depth = await client.get(f"{self.spot_base}/depth", params={"symbol": "BTCUSDT", "limit": 1000})
                depth_data = depth.json()
                
                # Análisis de liquidez debajo de 110k
                liquidity_below_110k = self._analyze_liquidity_below_level(
                    depth_data, current_btc, 110000
                )
                
                # Presión de liquidación
                liquidation_zones = await self._get_liquidation_zones(current_btc)
                
                # Funding rate y sentimiento
                funding = await client.get(f"{self.binance_base}/fundingRate", 
                                         params={"symbol": "BTCUSDT", "limit": 1})
                
                btc_analysis = {
                    "current_price": current_btc,
                    "resistance_110k": {
                        "distance_pct": ((110000 - current_btc) / current_btc) * 100,
                        "tested": current_btc >= 110000,
                        "liquidity_below": liquidity_below_110k
                    },
                    "liquidation_zones": liquidation_zones,
                    "funding_rate": float(funding.json()[0]["fundingRate"]) if funding.json() else 0,
                    "pullback_probability": self._calculate_pullback_probability(
                        current_btc, liquidity_below_110k, liquidation_zones
                    )
                }
                
                return btc_analysis
                
            except Exception as e:
                print(f"Error analyzing BTC: {e}")
                return {}
    
    def _analyze_liquidity_below_level(self, depth_data: Dict, current_price: float, level: float) -> Dict:
        """
        Analiza liquidez debajo de un nivel específico (ej: 110k)
        """
        bids = [[float(price), float(volume)] for price, volume in depth_data["bids"]]
        
        # Liquidez entre nivel y precio actual
        if level < current_price:
            relevant_bids = [bid for bid in bids if level <= bid[0] <= current_price]
        else:
            relevant_bids = [bid for bid in bids if current_price <= bid[0] <= level]
        
        if not relevant_bids:
            return {"total_liquidity": 0, "levels": [], "strength": "WEAK"}
        
        # Agrupar por zonas
        zones = []
        zone_size = (current_price - level) / 10 if level < current_price else (level - current_price) / 10
        
        for i in range(10):
            zone_start = level + (i * zone_size)
            zone_end = level + ((i + 1) * zone_size)
            
            zone_liquidity = sum([bid[1] for bid in relevant_bids 
                                if zone_start <= bid[0] < zone_end])
            
            if zone_liquidity > 0:
                zones.append({
                    "price_range": [zone_start, zone_end],
                    "mid_price": (zone_start + zone_end) / 2,
                    "liquidity": zone_liquidity,
                    "usd_value": zone_liquidity * ((zone_start + zone_end) / 2)
                })
        
        total_liquidity = sum([bid[1] for bid in relevant_bids])
        total_usd = sum([bid[0] * bid[1] for bid in relevant_bids])
        
        # Determinar fuerza de soporte
        strength = "WEAK"
        if total_usd > 100_000_000:  # >$100M
            strength = "VERY_STRONG"
        elif total_usd > 50_000_000:   # >$50M
            strength = "STRONG"
        elif total_usd > 20_000_000:   # >$20M
            strength = "MEDIUM"
        
        return {
            "total_liquidity": total_liquidity,
            "total_usd_value": total_usd,
            "strength": strength,
            "zones": zones[:5],  # Top 5 zones
            "key_support_level": zones[0]["mid_price"] if zones else level
        }
    
    async def _get_liquidation_zones(self, current_price: float) -> List[Dict]:
        """
        Calcula zonas de liquidación para diferentes leverages
        """
        zones = []
        leverages = [5, 10, 20, 50, 100]
        
        for leverage in leverages:
            # Long liquidation (price drops)
            long_liq = current_price * (1 - 0.9/leverage)  # 90% margin threshold
            
            zones.append({
                "type": "LONG_LIQUIDATION",
                "leverage": f"{leverage}x",
                "price": long_liq,
                "distance_pct": ((current_price - long_liq) / current_price) * 100
            })
        
        # Ordenar por proximidad
        zones.sort(key=lambda x: abs(x["distance_pct"]))
        return zones[:3]  # Top 3 más cercanas
    
    def _calculate_pullback_probability(self, current_price: float, liquidity_below: Dict, liquidation_zones: List[Dict]) -> Dict:
        """
        Calcula probabilidad de pullback basada en liquidez y liquidaciones
        """
        # Base probability
        probability = 0.3  # 30% base
        
        # Factor: Resistencia probada
        if current_price >= 110000:
            probability += 0.25  # +25% if testing 110k
        
        # Factor: Liquidez debajo
        if liquidity_below.get("strength") == "VERY_STRONG":
            probability += 0.2
        elif liquidity_below.get("strength") == "STRONG":
            probability += 0.15
        elif liquidity_below.get("strength") == "MEDIUM":
            probability += 0.1
        
        # Factor: Zona de liquidación cercana
        if liquidation_zones:
            closest_zone = liquidation_zones[0]
            if closest_zone["distance_pct"] < 5:  # <5% away
                probability += 0.15
        
        probability = min(probability, 0.95)  # Cap at 95%
        
        target_levels = []
        if liquidity_below.get("zones"):
            # Primeras 3 zonas de liquidez como targets
            for zone in liquidity_below["zones"][:3]:
                target_levels.append({
                    "price": zone["mid_price"],
                    "strength": "HIGH" if zone["usd_value"] > 20_000_000 else "MEDIUM",
                    "type": "LIQUIDITY_ZONE"
                })
        
        # Añadir zonas de liquidación
        for zone in liquidation_zones[:2]:
            target_levels.append({
                "price": zone["price"],
                "strength": "HIGH",
                "type": "LIQUIDATION_ZONE",
                "leverage": zone["leverage"]
            })
        
        return {
            "probability": probability,
            "confidence": "HIGH" if probability > 0.7 else "MEDIUM" if probability > 0.5 else "LOW",
            "target_levels": sorted(target_levels, key=lambda x: x["price"], reverse=True)[:5]
        }
    
    async def get_altcoin_correlation(self, symbol: str, timeframe: str = "1h", periods: int = 50) -> Dict:
        """
        Calcula correlación de altcoin con BTC
        """
        try:
            async with httpx.AsyncClient() as client:
                # Datos BTC
                btc_klines = await client.get(f"{self.binance_base}/klines", 
                                            params={"symbol": "BTCUSDT", "interval": timeframe, "limit": periods})
                
                # Datos Altcoin
                alt_klines = await client.get(f"{self.binance_base}/klines", 
                                            params={"symbol": symbol, "interval": timeframe, "limit": periods})
                
                if btc_klines.status_code != 200 or alt_klines.status_code != 200:
                    return {"error": "Failed to fetch data"}
                
                btc_data = btc_klines.json()
                alt_data = alt_klines.json()
                
                # Calcular retornos
                btc_returns = []
                alt_returns = []
                
                for i in range(1, len(btc_data)):
                    btc_close_prev = float(btc_data[i-1][4])
                    btc_close_curr = float(btc_data[i][4])
                    btc_returns.append((btc_close_curr - btc_close_prev) / btc_close_prev)
                    
                    alt_close_prev = float(alt_data[i-1][4])
                    alt_close_curr = float(alt_data[i][4])
                    alt_returns.append((alt_close_curr - alt_close_prev) / alt_close_prev)
                
                # Correlación
                correlation = np.corrcoef(btc_returns, alt_returns)[0, 1]
                
                # Beta (sensibilidad a BTC)
                btc_var = np.var(btc_returns)
                covariance = np.cov(btc_returns, alt_returns)[0, 1]
                beta = covariance / btc_var if btc_var != 0 else 0
                
                return {
                    "correlation": float(correlation),
                    "beta": float(beta),
                    "interpretation": self._interpret_correlation(correlation, beta)
                }
                
        except Exception as e:
            return {"error": f"Correlation calculation failed: {e}"}
    
    def _interpret_correlation(self, correlation: float, beta: float) -> Dict:
        """
        Interpreta correlación y beta
        """
        corr_strength = "WEAK"
        if abs(correlation) > 0.8:
            corr_strength = "VERY_STRONG"
        elif abs(correlation) > 0.6:
            corr_strength = "STRONG"
        elif abs(correlation) > 0.4:
            corr_strength = "MEDIUM"
        
        beta_interpretation = "NEUTRAL"
        if beta > 1.5:
            beta_interpretation = "HIGH_AMPLIFICATION"
        elif beta > 1.0:
            beta_interpretation = "AMPLIFIED"
        elif beta > 0.5:
            beta_interpretation = "FOLLOWS_BTC"
        elif beta < -0.5:
            beta_interpretation = "INVERSE"
        
        return {
            "correlation_strength": corr_strength,
            "beta_interpretation": beta_interpretation,
            "btc_influence": "HIGH" if abs(correlation) > 0.6 else "MEDIUM" if abs(correlation) > 0.3 else "LOW"
        }
    
    async def enhanced_altcoin_signal(self, symbol: str, btc_analysis: Dict, correlation_data: Dict) -> Dict:
        """
        Genera señal de altcoin considerando BTC
        """
        # Obtener datos del altcoin
        async with httpx.AsyncClient() as client:
            try:
                # Liquidez del altcoin
                liquidity_response = await client.get(f"{self.liquidity_endpoint}/{symbol}")
                liquidity_data = liquidity_response.json() if liquidity_response.status_code == 200 else {}
                
                current_alt_price = liquidity_data.get("order_book_analysis", {}).get("current_price", 0)
                
                signal = {
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat(),
                    "btc_context": {
                        "btc_price": btc_analysis.get("current_price", 0),
                        "pullback_probability": btc_analysis.get("pullback_probability", {}),
                        "resistance_110k_status": btc_analysis.get("resistance_110k", {})
                    },
                    "correlation": correlation_data,
                    "altcoin_data": {
                        "current_price": current_alt_price,
                        "liquidity": liquidity_data.get("order_book_analysis", {})
                    },
                    "recommendation": self._generate_recommendation(btc_analysis, correlation_data, liquidity_data)
                }
                
                return signal
                
            except Exception as e:
                return {"error": f"Signal generation failed: {e}"}
    
    def _generate_recommendation(self, btc_analysis: Dict, correlation_data: Dict, altcoin_liquidity: Dict) -> Dict:
        """
        Genera recomendación basada en análisis combinado
        """
        pullback_prob = btc_analysis.get("pullback_probability", {}).get("probability", 0)
        correlation = correlation_data.get("correlation", 0)
        beta = correlation_data.get("beta", 0)
        btc_influence = correlation_data.get("interpretation", {}).get("btc_influence", "LOW")
        
        recommendation = {
            "action": "WAIT",
            "confidence": "LOW",
            "reasoning": [],
            "entry_strategy": {},
            "risk_factors": []
        }
        
        # BTC probando resistencia 110k
        if btc_analysis.get("current_price", 0) >= 110000:
            if pullback_prob > 0.7:  # Alta probabilidad de pullback
                if correlation > 0.6:  # Fuerte correlación positiva
                    recommendation["action"] = "WAIT_FOR_BTC_PULLBACK"
                    recommendation["reasoning"].append("BTC testing 110k resistance with high pullback probability")
                    recommendation["reasoning"].append(f"Strong positive correlation ({correlation:.2f}) suggests altcoin will follow BTC down")
                    
                    # Calcular targets basados en BTC targets
                    btc_targets = btc_analysis.get("pullback_probability", {}).get("target_levels", [])
                    if btc_targets and beta > 0:
                        expected_alt_drop = abs(((btc_targets[0]["price"] - btc_analysis["current_price"]) / btc_analysis["current_price"]) * beta)
                        current_alt = altcoin_liquidity.get("order_book_analysis", {}).get("current_price", 0)
                        target_price = current_alt * (1 - expected_alt_drop)
                        
                        recommendation["entry_strategy"] = {
                            "type": "BTC_CORRELATION_ENTRY",
                            "wait_for_btc_level": btc_targets[0]["price"],
                            "expected_alt_target": target_price,
                            "expected_drop_pct": expected_alt_drop * 100
                        }
        
        # BTC ya en pullback
        elif pullback_prob < 0.4 and btc_analysis.get("current_price", 0) < 108000:
            if correlation > 0.5:
                recommendation["action"] = "CONSIDER_LONG"
                recommendation["reasoning"].append("BTC potentially finishing pullback")
                recommendation["reasoning"].append("Altcoin likely oversold due to BTC correlation")
                recommendation["confidence"] = "MEDIUM"
        
        # Factores de riesgo
        if btc_influence == "HIGH":
            recommendation["risk_factors"].append("High BTC influence - monitor BTC levels closely")
        
        if pullback_prob > 0.6:
            recommendation["risk_factors"].append("High BTC pullback probability affects market sentiment")
        
        return recommendation

# Test function
async def test_btc_correlation():
    """
    Test del analizador de correlación BTC
    """
    analyzer = BTCCorrelationAnalyzer()
    
    print("🔍 ANALIZANDO BTC Y CORRELACIONES...")
    print("="*60)
    
    # Análisis BTC
    btc_analysis = await analyzer.get_btc_analysis()
    
    print(f"💰 BTC Precio: ${btc_analysis.get('current_price', 0):,.2f}")
    print(f"📊 Resistencia 110k probada: {'SÍ' if btc_analysis.get('resistance_110k', {}).get('tested') else 'NO'}")
    print(f"🎯 Distancia a 110k: {btc_analysis.get('resistance_110k', {}).get('distance_pct', 0):+.2f}%")
    
    # Liquidez debajo de 110k
    liquidity = btc_analysis.get("resistance_110k", {}).get("liquidity_below", {})
    print(f"\n💧 LIQUIDEZ DEBAJO DE 110K:")
    print(f"   Fuerza: {liquidity.get('strength', 'N/A')}")
    print(f"   Valor USD: ${liquidity.get('total_usd_value', 0):,.0f}")
    print(f"   Soporte clave: ${liquidity.get('key_support_level', 0):,.0f}")
    
    # Probabilidad de pullback
    pullback = btc_analysis.get("pullback_probability", {})
    print(f"\n📉 PULLBACK PROBABILITY:")
    print(f"   Probabilidad: {pullback.get('probability', 0)*100:.1f}%")
    print(f"   Confianza: {pullback.get('confidence', 'N/A')}")
    
    print(f"\n🎯 NIVELES TARGET:")
    for level in pullback.get("target_levels", [])[:3]:
        print(f"   ${level['price']:,.0f} ({level['type']}) - {level['strength']}")
    
    # Correlaciones con altcoins
    altcoins = ["BNBUSDT", "SOLUSDT", "ADAUSDT"]
    
    print(f"\n📊 CORRELACIONES CON BTC:")
    for symbol in altcoins:
        corr_data = await analyzer.get_altcoin_correlation(symbol)
        if "error" not in corr_data:
            print(f"\n{symbol}:")
            print(f"   Correlación: {corr_data.get('correlation', 0):.3f}")
            print(f"   Beta: {corr_data.get('beta', 0):.2f}")
            print(f"   Influencia BTC: {corr_data.get('interpretation', {}).get('btc_influence', 'N/A')}")
            
            # Generar señal
            signal = await analyzer.enhanced_altcoin_signal(symbol, btc_analysis, corr_data)
            rec = signal.get("recommendation", {})
            print(f"   Acción: {rec.get('action', 'N/A')}")
            if rec.get("reasoning"):
                print(f"   Razón: {rec['reasoning'][0]}")

if __name__ == "__main__":
    asyncio.run(test_btc_correlation())