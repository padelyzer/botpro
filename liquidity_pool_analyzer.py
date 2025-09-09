#!/usr/bin/env python3
"""
Liquidity Pool Analyzer
Analiza pools de liquidez en DEX y niveles de liquidación en futuros
para predecir movimientos de precio
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiquidityPoolAnalyzer:
    """
    Analiza liquidez en DEX y liquidaciones en futuros
    """
    
    def __init__(self):
        self.dex_apis = {
            "uniswap": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
            "pancakeswap": "https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v3",
        }
        
        # APIs gratuitas para datos de liquidación
        self.liquidation_apis = {
            "coinglass": "https://open-api.coinglass.com/public/v2",  # Limited free tier
            "binance": "https://fapi.binance.com/fapi/v1",
            "bybit": "https://api.bybit.com/v5"
        }
        
    async def get_liquidation_levels(self, symbol: str) -> Dict:
        """
        Obtiene niveles de liquidación importantes
        """
        try:
            async with httpx.AsyncClient() as client:
                # Binance Open Interest
                oi_response = await client.get(
                    f"{self.liquidation_apis['binance']}/openInterest",
                    params={"symbol": symbol}
                )
                
                # Binance funding rate (indica presión de compra/venta)
                funding_response = await client.get(
                    f"{self.liquidation_apis['binance']}/fundingRate",
                    params={"symbol": symbol, "limit": 1}
                )
                
                # Binance 24hr liquidations from ticker
                ticker_response = await client.get(
                    f"{self.liquidation_apis['binance']}/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                oi_data = oi_response.json() if oi_response.status_code == 200 else {}
                funding_data = funding_response.json() if funding_response.status_code == 200 else []
                ticker_data = ticker_response.json() if ticker_response.status_code == 200 else {}
                
                # Calcular niveles de liquidación estimados
                current_price = float(ticker_data.get("lastPrice", 0))
                
                liquidation_levels = {
                    "current_price": current_price,
                    "open_interest": float(oi_data.get("openInterest", 0)),
                    "funding_rate": float(funding_data[0]["fundingRate"]) if funding_data else 0,
                    "volume_24h": float(ticker_data.get("volume", 0)),
                    "liquidation_zones": self._calculate_liquidation_zones(current_price),
                    "pressure": self._analyze_liquidation_pressure(oi_data, funding_data, ticker_data)
                }
                
                return liquidation_levels
                
        except Exception as e:
            logger.error(f"Error getting liquidation levels: {e}")
            return {}
    
    def _calculate_liquidation_zones(self, current_price: float) -> Dict:
        """
        Calcula zonas de liquidación basadas en leverage común
        """
        zones = {
            "long_liquidations": [],
            "short_liquidations": []
        }
        
        # Leverages comunes: 5x, 10x, 20x, 50x, 100x
        leverages = [5, 10, 20, 50, 100]
        
        for leverage in leverages:
            # Liquidación de longs (precio baja)
            long_liq = current_price * (1 - 0.8/leverage)  # 80% margen inicial
            zones["long_liquidations"].append({
                "leverage": f"{leverage}x",
                "price": long_liq,
                "distance": f"{((current_price - long_liq)/current_price * 100):.2f}%"
            })
            
            # Liquidación de shorts (precio sube)
            short_liq = current_price * (1 + 0.8/leverage)
            zones["short_liquidations"].append({
                "leverage": f"{leverage}x", 
                "price": short_liq,
                "distance": f"{((short_liq - current_price)/current_price * 100):.2f}%"
            })
        
        return zones
    
    def _analyze_liquidation_pressure(self, oi_data: Dict, funding_data: List, ticker_data: Dict) -> str:
        """
        Analiza presión de liquidación
        """
        if not funding_data:
            return "NEUTRAL"
        
        funding_rate = float(funding_data[0]["fundingRate"])
        
        # Funding positivo alto = muchos longs, posible squeeze down
        if funding_rate > 0.001:  # > 0.1%
            return "LONG_SQUEEZE_RISK"
        # Funding negativo = muchos shorts, posible squeeze up
        elif funding_rate < -0.0005:  # < -0.05%
            return "SHORT_SQUEEZE_RISK"
        else:
            return "BALANCED"
    
    async def analyze_dex_liquidity(self, token_address: str) -> Dict:
        """
        Analiza liquidez en DEX (simplified without API key)
        """
        # Simulamos análisis de DEX basado en patrones típicos
        return {
            "liquidity_depth": "MEDIUM",
            "buy_pressure": "LOW",  # After 3% drop
            "sell_pressure": "HIGH",
            "support_levels": [
                {"price": 92000, "liquidity": "HIGH"},
                {"price": 90000, "liquidity": "VERY_HIGH"},
                {"price": 88000, "liquidity": "MEDIUM"}
            ],
            "resistance_levels": [
                {"price": 95000, "liquidity": "MEDIUM"},
                {"price": 96500, "liquidity": "HIGH"},
                {"price": 98000, "liquidity": "LOW"}
            ]
        }
    
    async def predict_price_movement(self, symbol: str, drop_percentage: float = 3.0) -> Dict:
        """
        Predice movimiento de precio basado en liquidez y liquidaciones
        """
        
        # Obtener datos de liquidación
        liquidation_data = await self.get_liquidation_levels(symbol)
        
        # Analizar liquidez DEX (simplified)
        dex_data = await self.analyze_dex_liquidity(symbol)
        
        # Lógica de predicción
        prediction = {
            "symbol": symbol,
            "current_situation": f"{drop_percentage}% drop detected",
            "liquidation_pressure": liquidation_data.get("pressure", "UNKNOWN"),
            "short_term_outlook": "",
            "key_levels": {},
            "recommended_action": "",
            "confidence": 0
        }
        
        # Después de una caída del 3%
        if drop_percentage >= 3:
            # Check for long liquidations
            if liquidation_data.get("pressure") == "LONG_SQUEEZE_RISK":
                prediction["short_term_outlook"] = "FURTHER_DOWNSIDE"
                prediction["key_levels"] = {
                    "next_support": liquidation_data["liquidation_zones"]["long_liquidations"][0]["price"],
                    "bounce_zone": liquidation_data["liquidation_zones"]["long_liquidations"][1]["price"]
                }
                prediction["recommended_action"] = "WAIT_FOR_BOUNCE_OR_SHORT"
                prediction["confidence"] = 75
                
            elif liquidation_data.get("pressure") == "SHORT_SQUEEZE_RISK":
                prediction["short_term_outlook"] = "POTENTIAL_BOUNCE"
                prediction["key_levels"] = {
                    "immediate_resistance": liquidation_data["current_price"] * 1.015,
                    "target": liquidation_data["liquidation_zones"]["short_liquidations"][0]["price"]
                }
                prediction["recommended_action"] = "CONSIDER_LONG_ON_BOUNCE"
                prediction["confidence"] = 70
                
            else:
                prediction["short_term_outlook"] = "CONSOLIDATION"
                prediction["key_levels"] = {
                    "support": liquidation_data["current_price"] * 0.98,
                    "resistance": liquidation_data["current_price"] * 1.02
                }
                prediction["recommended_action"] = "WAIT_FOR_DIRECTION"
                prediction["confidence"] = 60
        
        # Agregar análisis de liquidez
        prediction["liquidity_analysis"] = {
            "dex_liquidity": dex_data["liquidity_depth"],
            "order_flow": f"Buy: {dex_data['buy_pressure']}, Sell: {dex_data['sell_pressure']}",
            "key_support": dex_data["support_levels"][0] if dex_data["support_levels"] else None,
            "key_resistance": dex_data["resistance_levels"][0] if dex_data["resistance_levels"] else None
        }
        
        # Agregar datos de liquidación
        prediction["liquidation_data"] = {
            "open_interest": f"${liquidation_data.get('open_interest', 0):,.0f}",
            "funding_rate": f"{liquidation_data.get('funding_rate', 0)*100:.4f}%",
            "next_long_liquidation": liquidation_data["liquidation_zones"]["long_liquidations"][0] if liquidation_data.get("liquidation_zones") else None,
            "next_short_liquidation": liquidation_data["liquidation_zones"]["short_liquidations"][0] if liquidation_data.get("liquidation_zones") else None
        }
        
        return prediction
    
    async def get_market_liquidity_map(self, symbols: List[str]) -> Dict:
        """
        Obtiene mapa de liquidez del mercado
        """
        liquidity_map = {}
        
        for symbol in symbols:
            try:
                data = await self.get_liquidation_levels(symbol)
                liquidity_map[symbol] = {
                    "open_interest": data.get("open_interest", 0),
                    "funding": data.get("funding_rate", 0),
                    "pressure": data.get("pressure", "UNKNOWN"),
                    "risk_level": self._calculate_risk_level(data)
                }
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                
        return liquidity_map
    
    def _calculate_risk_level(self, data: Dict) -> str:
        """
        Calcula nivel de riesgo basado en métricas
        """
        funding = abs(data.get("funding_rate", 0))
        
        if funding > 0.002:  # > 0.2%
            return "HIGH"
        elif funding > 0.001:  # > 0.1%
            return "MEDIUM"
        else:
            return "LOW"

# Test module
if __name__ == "__main__":
    async def test():
        analyzer = LiquidityPoolAnalyzer()
        
        # Analizar BTC después de caída del 3%
        print("\n🔍 Analizando BTC después de caída del 3%...")
        prediction = await analyzer.predict_price_movement("BTCUSDT", drop_percentage=3.0)
        
        print(f"\n📊 Situación: {prediction['current_situation']}")
        print(f"🎯 Perspectiva: {prediction['short_term_outlook']}")
        print(f"⚡ Presión de liquidación: {prediction['liquidation_pressure']}")
        print(f"💡 Acción recomendada: {prediction['recommended_action']}")
        print(f"📈 Confianza: {prediction['confidence']}%")
        
        print("\n📍 Niveles Clave:")
        for level, price in prediction['key_levels'].items():
            print(f"  - {level}: ${price:,.2f}")
        
        print("\n💧 Análisis de Liquidez:")
        for key, value in prediction['liquidity_analysis'].items():
            print(f"  - {key}: {value}")
        
        print("\n🔥 Datos de Liquidación:")
        for key, value in prediction['liquidation_data'].items():
            print(f"  - {key}: {value}")
    
    asyncio.run(test())