#!/usr/bin/env python3
"""
Correlation Analyzer - Sistema de Rotación Inteligente
Detecta el flujo de dinero entre diferentes criptomonedas
BTC → ETH → SOL → AVAX → Small caps
"""

import asyncio
import httpx
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """Analiza la rotación de capital entre diferentes sectores crypto"""
    
    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"
        
        # Definir sectores y su jerarquía de flujo
        self.sectors = {
            "STORE_OF_VALUE": ["BTCUSDT"],
            "SMART_CONTRACTS": ["ETHUSDT", "BNBUSDT"],
            "HIGH_PERFORMANCE": ["SOLUSDT", "AVAXUSDT"],
            "DEFI": ["AAVEUSDT", "UNIUSDT", "SUSHIUSDT"],
            "MEME": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT"],
            "AI": ["FETUSDT", "AGIXUSDT", "OCEANUSDT"]
        }
        
        # Flujo típico de capital en bull market
        self.capital_flow = [
            "STORE_OF_VALUE",      # 1. BTC lidera
            "SMART_CONTRACTS",      # 2. ETH y L1s siguen
            "HIGH_PERFORMANCE",     # 3. SOL, AVAX explotan
            "DEFI",                # 4. DeFi tokens
            "AI",                  # 5. Narrativas (AI, Gaming)
            "MEME"                 # 6. Meme coins al final
        ]
        
        self.ratio_cache = {}
        self.cache_duration = 300  # 5 minutes
        
    async def get_price(self, symbol: str) -> float:
        """Obtener precio actual"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/ticker/price",
                    params={"symbol": symbol},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return float(response.json()['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
        return 0
    
    async def get_24h_change(self, symbol: str) -> Dict:
        """Obtener cambio de 24 horas"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/ticker/24hr",
                    params={"symbol": symbol},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "symbol": symbol,
                        "price_change_percent": float(data['priceChangePercent']),
                        "volume": float(data['volume']),
                        "quote_volume": float(data['quoteVolume'])
                    }
        except Exception as e:
            logger.error(f"Error getting 24h change for {symbol}: {e}")
        return {"symbol": symbol, "price_change_percent": 0, "volume": 0}
    
    async def calculate_ratio(self, symbol1: str, symbol2: str) -> Dict:
        """
        Calcular ratio entre dos cryptos
        Ratio subiendo = symbol1 outperforming symbol2
        """
        prices = await asyncio.gather(
            self.get_price(symbol1),
            self.get_price(symbol2)
        )
        
        if prices[0] and prices[1]:
            current_ratio = prices[0] / prices[1]
            
            # Get historical ratio (simplified - should use klines for real implementation)
            # For now, we'll use 24h change as proxy
            changes = await asyncio.gather(
                self.get_24h_change(symbol1),
                self.get_24h_change(symbol2)
            )
            
            change1 = changes[0]['price_change_percent']
            change2 = changes[1]['price_change_percent']
            ratio_change = change1 - change2  # Differential performance
            
            # Determine trend
            if ratio_change > 5:
                trend = "STRONGLY_OUTPERFORMING"
                signal = f"BUY_{symbol1}_SELL_{symbol2}"
            elif ratio_change > 2:
                trend = "OUTPERFORMING"
                signal = f"FAVOR_{symbol1}"
            elif ratio_change < -5:
                trend = "STRONGLY_UNDERPERFORMING"
                signal = f"SELL_{symbol1}_BUY_{symbol2}"
            elif ratio_change < -2:
                trend = "UNDERPERFORMING"
                signal = f"FAVOR_{symbol2}"
            else:
                trend = "NEUTRAL"
                signal = "HOLD"
            
            return {
                "pair": f"{symbol1}/{symbol2}",
                "current_ratio": current_ratio,
                "ratio_change_24h": ratio_change,
                "trend": trend,
                "signal": signal,
                "symbol1_performance": change1,
                "symbol2_performance": change2,
                "volume_ratio": changes[0]['volume'] / changes[1]['volume'] if changes[1]['volume'] > 0 else 0
            }
        
        return {
            "pair": f"{symbol1}/{symbol2}",
            "current_ratio": 0,
            "ratio_change_24h": 0,
            "trend": "UNKNOWN",
            "signal": "NO_DATA"
        }
    
    async def detect_sector_rotation(self) -> Dict:
        """
        Detectar hacia dónde está rotando el capital
        """
        sector_performance = {}
        
        # Analizar performance de cada sector
        for sector, symbols in self.sectors.items():
            if not symbols:
                continue
                
            performances = []
            volumes = []
            
            for symbol in symbols[:3]:  # Max 3 symbols per sector
                try:
                    data = await self.get_24h_change(symbol)
                    performances.append(data['price_change_percent'])
                    volumes.append(data['quote_volume'])
                except:
                    continue
            
            if performances:
                sector_performance[sector] = {
                    "avg_performance": np.mean(performances),
                    "max_performance": max(performances),
                    "total_volume": sum(volumes),
                    "symbols": symbols
                }
        
        # Ordenar sectores por performance
        sorted_sectors = sorted(
            sector_performance.items(),
            key=lambda x: x[1]['avg_performance'],
            reverse=True
        )
        
        # Detectar rotación
        if len(sorted_sectors) >= 2:
            leading_sector = sorted_sectors[0][0]
            lagging_sector = sorted_sectors[-1][0]
            
            # Calcular diferencial de momentum
            momentum_spread = sorted_sectors[0][1]['avg_performance'] - sorted_sectors[-1][1]['avg_performance']
            
            # Determinar fase del mercado
            if leading_sector == "STORE_OF_VALUE" and momentum_spread > 5:
                market_phase = "EARLY_BULL"
                next_sector = "SMART_CONTRACTS"
            elif leading_sector == "SMART_CONTRACTS" and "STORE_OF_VALUE" in [s[0] for s in sorted_sectors[:3]]:
                market_phase = "MID_BULL"
                next_sector = "HIGH_PERFORMANCE"
            elif leading_sector in ["HIGH_PERFORMANCE", "DEFI"]:
                market_phase = "LATE_BULL"
                next_sector = "MEME"
            elif leading_sector == "MEME":
                market_phase = "EUPHORIA"
                next_sector = "STORE_OF_VALUE"  # Rotation back to safety
            else:
                market_phase = "UNCERTAIN"
                next_sector = None
            
            return {
                "current_leader": leading_sector,
                "current_laggard": lagging_sector,
                "market_phase": market_phase,
                "next_rotation": next_sector,
                "momentum_spread": momentum_spread,
                "sector_ranking": [
                    {
                        "sector": s[0],
                        "performance": s[1]['avg_performance'],
                        "volume": s[1]['total_volume']
                    }
                    for s in sorted_sectors
                ],
                "rotation_signal": self._generate_rotation_signal(leading_sector, next_sector)
            }
        
        return {
            "current_leader": "UNKNOWN",
            "market_phase": "UNCERTAIN",
            "sector_ranking": []
        }
    
    def _generate_rotation_signal(self, current_leader: str, next_sector: str) -> Dict:
        """Generar señal de trading basada en rotación"""
        if not next_sector:
            return {"action": "HOLD", "target_sector": None}
        
        # Map sectors to specific tokens
        sector_tokens = {
            "STORE_OF_VALUE": "BTCUSDT",
            "SMART_CONTRACTS": "ETHUSDT",
            "HIGH_PERFORMANCE": "SOLUSDT",
            "DEFI": "AAVEUSDT",
            "MEME": "DOGEUSDT",
            "AI": "FETUSDT"
        }
        
        return {
            "action": "ROTATE",
            "from_sector": current_leader,
            "to_sector": next_sector,
            "from_token": sector_tokens.get(current_leader),
            "to_token": sector_tokens.get(next_sector),
            "reasoning": f"Capital rotating from {current_leader} to {next_sector}"
        }
    
    async def analyze_pair_dynamics(self, pairs: List[Tuple[str, str]]) -> Dict:
        """
        Analizar dinámicas entre pares específicos
        Ej: [("SOLUSDT", "BTCUSDT"), ("ETHUSDT", "BTCUSDT")]
        """
        results = {}
        
        for symbol1, symbol2 in pairs:
            ratio_data = await self.calculate_ratio(symbol1, symbol2)
            results[f"{symbol1}/{symbol2}"] = ratio_data
        
        # Determinar mejor oportunidad
        best_opportunity = None
        best_score = 0
        
        for pair, data in results.items():
            if "OUTPERFORMING" in data['trend']:
                score = abs(data['ratio_change_24h'])
                if score > best_score:
                    best_score = score
                    best_opportunity = {
                        "pair": pair,
                        "action": data['signal'],
                        "strength": score,
                        "data": data
                    }
        
        return {
            "pair_analysis": results,
            "best_opportunity": best_opportunity,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_altcoin_season_index(self) -> Dict:
        """
        Calcular índice de temporada de altcoins
        >75 = Alt season
        <25 = Bitcoin season
        """
        # Compare top alts vs BTC
        alts = ["ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        
        outperforming = 0
        total = len(alts)
        
        btc_change = await self.get_24h_change("BTCUSDT")
        btc_perf = btc_change['price_change_percent']
        
        alt_performances = []
        for alt in alts:
            alt_change = await self.get_24h_change(alt)
            alt_perf = alt_change['price_change_percent']
            alt_performances.append({
                "symbol": alt,
                "performance": alt_perf,
                "vs_btc": alt_perf - btc_perf
            })
            
            if alt_perf > btc_perf:
                outperforming += 1
        
        altcoin_index = (outperforming / total) * 100
        
        # Determine market state
        if altcoin_index > 75:
            market_state = "ALT_SEASON"
            recommendation = "Focus on quality altcoins"
        elif altcoin_index > 50:
            market_state = "ALT_FAVORABLE"
            recommendation = "Balanced allocation with alt preference"
        elif altcoin_index > 25:
            market_state = "NEUTRAL"
            recommendation = "Follow individual setups"
        else:
            market_state = "BTC_SEASON"
            recommendation = "Focus on Bitcoin"
        
        return {
            "altcoin_season_index": altcoin_index,
            "market_state": market_state,
            "recommendation": recommendation,
            "btc_performance": btc_perf,
            "alts_outperforming": outperforming,
            "total_alts": total,
            "alt_performances": sorted(alt_performances, key=lambda x: x['vs_btc'], reverse=True)
        }
    
    async def get_money_flow_map(self) -> Dict:
        """
        Mapa completo del flujo de dinero en el mercado
        """
        # Ejecutar análisis en paralelo
        results = await asyncio.gather(
            self.detect_sector_rotation(),
            self.get_altcoin_season_index(),
            self.analyze_pair_dynamics([
                ("SOLUSDT", "BTCUSDT"),
                ("ETHUSDT", "BTCUSDT"),
                ("SOLUSDT", "ETHUSDT")
            ])
        )
        
        sector_rotation = results[0]
        altcoin_index = results[1]
        pair_dynamics = results[2]
        
        # Generar recomendaciones
        recommendations = []
        
        # Based on sector rotation
        if sector_rotation.get('next_rotation'):
            recommendations.append(f"Rotate to {sector_rotation['next_rotation']} sector")
        
        # Based on altcoin season
        if altcoin_index['altcoin_season_index'] > 75:
            recommendations.append("Increase altcoin allocation")
        elif altcoin_index['altcoin_season_index'] < 25:
            recommendations.append("Reduce altcoin exposure, focus on BTC")
        
        # Based on pair dynamics
        if pair_dynamics.get('best_opportunity'):
            recommendations.append(f"Best pair trade: {pair_dynamics['best_opportunity']['action']}")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "market_phase": sector_rotation.get('market_phase', 'UNCERTAIN'),
            "altcoin_season_index": altcoin_index['altcoin_season_index'],
            "leading_sector": sector_rotation.get('current_leader'),
            "sector_performance": sector_rotation.get('sector_ranking', []),
            "best_pairs": pair_dynamics.get('best_opportunity'),
            "recommendations": recommendations,
            "signals": {
                "sector_rotation": sector_rotation.get('rotation_signal'),
                "altcoin_season": altcoin_index['market_state'],
                "pair_trade": pair_dynamics.get('best_opportunity')
            }
        }

# Testing
async def test_correlation_analyzer():
    """Test the correlation analyzer"""
    analyzer = CorrelationAnalyzer()
    
    print("="*60)
    print("CRYPTO CORRELATION & ROTATION ANALYZER")
    print("="*60)
    
    # Test money flow map
    print("\n📊 MONEY FLOW MAP:")
    money_flow = await analyzer.get_money_flow_map()
    
    print(f"\nMarket Phase: {money_flow['market_phase']}")
    print(f"Altcoin Season Index: {money_flow['altcoin_season_index']:.1f}")
    print(f"Leading Sector: {money_flow['leading_sector']}")
    
    print("\n📈 Sector Performance:")
    for sector in money_flow['sector_performance'][:5]:
        print(f"  {sector['sector']:20} {sector['performance']:+.2f}%")
    
    print("\n💡 Recommendations:")
    for rec in money_flow['recommendations']:
        print(f"  • {rec}")
    
    # Test specific ratios
    print("\n🔄 Key Pair Ratios:")
    pairs = await analyzer.analyze_pair_dynamics([
        ("SOLUSDT", "BTCUSDT"),
        ("ETHUSDT", "BTCUSDT"),
        ("BNBUSDT", "ETHUSDT")
    ])
    
    for pair, data in pairs['pair_analysis'].items():
        print(f"\n{pair}:")
        print(f"  Ratio Change 24h: {data['ratio_change_24h']:+.2f}%")
        print(f"  Trend: {data['trend']}")
        print(f"  Signal: {data['signal']}")

if __name__ == "__main__":
    asyncio.run(test_correlation_analyzer())