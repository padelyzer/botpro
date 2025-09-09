#!/usr/bin/env python3
"""
Market Regime Detector - Detecta el régimen macro del mercado crypto
Filtros de mercado para evitar operar en condiciones adversas
"""

import asyncio
import httpx
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MarketRegimeDetector:
    """Detecta el régimen del mercado crypto y aplica filtros macro"""
    
    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        
        # Thresholds for market conditions
        self.btc_dominance_threshold = 55  # Above = BTC season, Below = Alt season
        self.fear_greed_bullish = 60       # Above = Bullish sentiment
        self.fear_greed_bearish = 30       # Below = Bearish sentiment
        
        # Cache for expensive API calls
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
    async def get_btc_dominance(self) -> float:
        """
        Obtener dominancia de Bitcoin
        <55% = Temporada de altcoins favorable
        """
        cache_key = "btc_dominance"
        
        # Check cache
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < self.cache_duration:
                return cached_data['value']
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.coingecko_api}/global",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    btc_dominance = data['data']['market_cap_percentage']['btc']
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        'value': btc_dominance,
                        'timestamp': datetime.now()
                    }
                    
                    return btc_dominance
        except Exception as e:
            logger.error(f"Error getting BTC dominance: {e}")
        
        # Default fallback
        return 45.0  # Assume neutral dominance
    
    async def get_fear_greed_index(self) -> Dict:
        """
        Obtener índice de miedo y codicia
        >60 = Momentum alcista
        <30 = Miedo extremo
        """
        cache_key = "fear_greed"
        
        # Check cache
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < self.cache_duration:
                return cached_data['value']
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.alternative.me/fng/",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    fear_greed = {
                        'value': int(data['data'][0]['value']),
                        'classification': data['data'][0]['value_classification']
                    }
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        'value': fear_greed,
                        'timestamp': datetime.now()
                    }
                    
                    return fear_greed
        except Exception as e:
            logger.error(f"Error getting Fear & Greed index: {e}")
        
        # Default fallback
        return {'value': 50, 'classification': 'Neutral'}
    
    async def get_total_market_cap(self) -> Dict:
        """
        Obtener capitalización total del mercado crypto
        Detectar si está creciendo o decreciendo
        """
        cache_key = "market_cap"
        
        # Check cache
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < self.cache_duration:
                return cached_data['value']
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.coingecko_api}/global",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()['data']
                    market_cap = {
                        'total_market_cap': data['total_market_cap']['usd'],
                        'total_volume': data['total_volume']['usd'],
                        'market_cap_change_24h': data['market_cap_change_percentage_24h_usd'],
                        'trending': "UP" if data['market_cap_change_percentage_24h_usd'] > 0 else "DOWN"
                    }
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        'value': market_cap,
                        'timestamp': datetime.now()
                    }
                    
                    return market_cap
        except Exception as e:
            logger.error(f"Error getting market cap: {e}")
        
        # Default fallback
        return {
            'total_market_cap': 2_000_000_000_000,  # $2T
            'market_cap_change_24h': 0,
            'trending': "NEUTRAL"
        }
    
    async def get_stablecoin_flow(self) -> Dict:
        """
        Detectar flujo de stablecoins (USDT, USDC)
        Market cap creciendo = Entrada de dinero nuevo
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get USDT market cap
                response = await client.get(
                    f"{self.coingecko_api}/coins/tether",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    usdt_cap = data['market_data']['market_cap']['usd']
                    usdt_change = data['market_data']['market_cap_change_percentage_24h']
                    
                    # Determine flow direction
                    if usdt_change > 0.5:
                        flow = "INFLOW"
                        signal = "BULLISH"
                    elif usdt_change < -0.5:
                        flow = "OUTFLOW"
                        signal = "BEARISH"
                    else:
                        flow = "NEUTRAL"
                        signal = "NEUTRAL"
                    
                    return {
                        'usdt_market_cap': usdt_cap,
                        'usdt_change_24h': usdt_change,
                        'flow_direction': flow,
                        'signal': signal
                    }
        except Exception as e:
            logger.error(f"Error getting stablecoin flow: {e}")
        
        return {
            'usdt_market_cap': 100_000_000_000,  # $100B
            'usdt_change_24h': 0,
            'flow_direction': "NEUTRAL",
            'signal': "NEUTRAL"
        }
    
    async def detect_market_regime(self) -> Dict:
        """
        Detectar el régimen actual del mercado
        Combina múltiples indicadores macro
        """
        # Gather all macro indicators
        results = await asyncio.gather(
            self.get_btc_dominance(),
            self.get_fear_greed_index(),
            self.get_total_market_cap(),
            self.get_stablecoin_flow()
        )
        
        btc_dominance = results[0]
        fear_greed = results[1]
        market_cap = results[2]
        stablecoin_flow = results[3]
        
        # Analyze conditions
        conditions = {
            'btc_dominance': btc_dominance,
            'btc_dominance_favorable': btc_dominance < self.btc_dominance_threshold,
            'fear_greed_index': fear_greed['value'],
            'sentiment': fear_greed['classification'],
            'sentiment_bullish': fear_greed['value'] > self.fear_greed_bullish,
            'market_cap_trending': market_cap['trending'],
            'market_cap_change': market_cap['market_cap_change_24h'],
            'stablecoin_flow': stablecoin_flow['flow_direction'],
            'money_entering': stablecoin_flow['flow_direction'] == "INFLOW"
        }
        
        # Determine market regime
        bullish_signals = sum([
            conditions['btc_dominance_favorable'],
            conditions['sentiment_bullish'],
            market_cap['trending'] == "UP",
            conditions['money_entering']
        ])
        
        if bullish_signals >= 3:
            regime = "BULL_MARKET"
            confidence = 85
        elif bullish_signals >= 2:
            regime = "EARLY_BULL"
            confidence = 70
        elif bullish_signals == 1:
            regime = "NEUTRAL"
            confidence = 50
        else:
            regime = "BEAR_MARKET"
            confidence = 80
        
        # Specific market phases
        if btc_dominance < 40 and fear_greed['value'] > 75:
            phase = "ALT_SEASON_EUPHORIA"
        elif btc_dominance < 50 and market_cap['trending'] == "UP":
            phase = "ALT_SEASON"
        elif btc_dominance > 60 and fear_greed['value'] < 30:
            phase = "CRYPTO_WINTER"
        elif market_cap['market_cap_change_24h'] > 5:
            phase = "RALLY"
        elif market_cap['market_cap_change_24h'] < -5:
            phase = "CORRECTION"
        else:
            phase = "CONSOLIDATION"
        
        return {
            'regime': regime,
            'phase': phase,
            'confidence': confidence,
            'conditions': conditions,
            'bullish_signals': bullish_signals,
            'timestamp': datetime.now().isoformat()
        }
    
    async def should_trade(self, aggressive: bool = False) -> Dict:
        """
        Determinar si las condiciones macro son favorables para operar
        """
        regime = await self.detect_market_regime()
        
        # Define trading conditions based on regime
        if regime['regime'] == "BULL_MARKET":
            should_trade = True
            position_size = 1.0  # Full size
            preferred_assets = "ALTCOINS"
            risk_level = "HIGH"
        elif regime['regime'] == "EARLY_BULL":
            should_trade = True
            position_size = 0.75
            preferred_assets = "MAJORS"  # BTC, ETH, SOL
            risk_level = "MEDIUM"
        elif regime['regime'] == "NEUTRAL":
            should_trade = aggressive  # Only if aggressive mode
            position_size = 0.5
            preferred_assets = "BTC"
            risk_level = "LOW"
        else:  # BEAR_MARKET
            should_trade = False
            position_size = 0.0
            preferred_assets = "STABLECOINS"
            risk_level = "NONE"
        
        # Additional filters
        filters_passed = []
        filters_failed = []
        
        # Check each filter
        if regime['conditions']['btc_dominance_favorable']:
            filters_passed.append("✅ BTC Dominance < 55%")
        else:
            filters_failed.append(f"❌ BTC Dominance too high ({regime['conditions']['btc_dominance']:.1f}%)")
        
        if regime['conditions']['sentiment_bullish']:
            filters_passed.append(f"✅ Fear & Greed bullish ({regime['conditions']['fear_greed_index']})")
        else:
            filters_failed.append(f"❌ Sentiment not bullish ({regime['conditions']['sentiment']})")
        
        if regime['conditions']['market_cap_trending'] == "UP":
            filters_passed.append("✅ Market cap growing")
        else:
            filters_failed.append("❌ Market cap declining")
        
        if regime['conditions']['money_entering']:
            filters_passed.append("✅ Stablecoin inflow detected")
        else:
            filters_failed.append(f"❌ No stablecoin inflow ({regime['conditions']['stablecoin_flow']})")
        
        # Final decision
        can_trade = should_trade and (len(filters_passed) >= 2 or aggressive)
        
        return {
            'can_trade': can_trade,
            'regime': regime['regime'],
            'phase': regime['phase'],
            'confidence': regime['confidence'],
            'position_size_recommendation': position_size,
            'preferred_assets': preferred_assets,
            'risk_level': risk_level,
            'filters_passed': filters_passed,
            'filters_failed': filters_failed,
            'macro_conditions': regime['conditions'],
            'recommendation': self._get_recommendation(regime, can_trade)
        }
    
    def _get_recommendation(self, regime: Dict, can_trade: bool) -> str:
        """Generate trading recommendation based on regime"""
        if regime['regime'] == "BULL_MARKET":
            if regime['phase'] == "ALT_SEASON_EUPHORIA":
                return "⚠️ Market euphoric - Take profits on rallies"
            return "✅ Full send - Focus on momentum plays"
        elif regime['regime'] == "EARLY_BULL":
            return "✅ Accumulate quality projects on dips"
        elif regime['regime'] == "NEUTRAL":
            if can_trade:
                return "⚠️ Trade carefully - Reduce position sizes"
            return "⏸️ Wait for better conditions"
        else:  # BEAR
            return "🛑 Preserve capital - Stay in stables"
    
    async def get_market_filters(self) -> Dict:
        """
        Get all market filters in one call
        Used for pre-trade checks
        """
        regime = await self.detect_market_regime()
        trading_decision = await self.should_trade(aggressive=False)
        
        # Create simple filter checks
        all_filters = {
            'btc_dominance_ok': regime['conditions']['btc_dominance'] < self.btc_dominance_threshold,
            'sentiment_ok': regime['conditions']['fear_greed_index'] > self.fear_greed_bullish,
            'market_cap_ok': regime['conditions']['market_cap_trending'] == "UP",
            'stablecoin_ok': regime['conditions']['money_entering'],
            'btc_stable': await self._check_btc_stability()
        }
        
        # All filters must pass for ideal conditions
        all_pass = all(all_filters.values())
        
        return {
            'filters': all_filters,
            'all_pass': all_pass,
            'can_trade': trading_decision['can_trade'],
            'regime': regime['regime'],
            'phase': regime['phase'],
            'timestamp': datetime.now().isoformat()
        }
    
    async def _check_btc_stability(self) -> bool:
        """
        Check if BTC is stable (not dumping)
        BTC volatility affects entire market
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/ticker/24hr",
                    params={"symbol": "BTCUSDT"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    change_24h = float(data['priceChangePercent'])
                    
                    # BTC is stable if not dropping more than 3%
                    return change_24h > -3.0
        except Exception as e:
            logger.error(f"Error checking BTC stability: {e}")
        
        return True  # Assume stable if can't check

# Testing
async def test_market_regime():
    """Test the market regime detector"""
    detector = MarketRegimeDetector()
    
    print("="*60)
    print("CRYPTO MARKET REGIME DETECTOR")
    print("="*60)
    
    # Get market regime
    print("\n📊 DETECTING MARKET REGIME...")
    regime = await detector.detect_market_regime()
    
    print(f"\n🎯 Market Regime: {regime['regime']}")
    print(f"📈 Market Phase: {regime['phase']}")
    print(f"💪 Confidence: {regime['confidence']}%")
    
    print("\n📋 Market Conditions:")
    print(f"  BTC Dominance: {regime['conditions']['btc_dominance']:.1f}%")
    print(f"  Fear & Greed: {regime['conditions']['fear_greed_index']} ({regime['conditions']['sentiment']})")
    print(f"  Market Cap Trend: {regime['conditions']['market_cap_trending']}")
    print(f"  Stablecoin Flow: {regime['conditions']['stablecoin_flow']}")
    
    # Check if we should trade
    print("\n🤔 SHOULD WE TRADE?")
    
    # Conservative check
    conservative = await detector.should_trade(aggressive=False)
    print(f"\n📊 Conservative Mode:")
    print(f"  Can Trade: {'✅ YES' if conservative['can_trade'] else '❌ NO'}")
    print(f"  Position Size: {conservative['position_size_recommendation']*100:.0f}%")
    print(f"  Preferred Assets: {conservative['preferred_assets']}")
    print(f"  Risk Level: {conservative['risk_level']}")
    
    print("\n  Filters Passed:")
    for filter_msg in conservative['filters_passed']:
        print(f"    {filter_msg}")
    
    if conservative['filters_failed']:
        print("\n  Filters Failed:")
        for filter_msg in conservative['filters_failed']:
            print(f"    {filter_msg}")
    
    print(f"\n  💡 Recommendation: {conservative['recommendation']}")
    
    # Aggressive check
    aggressive = await detector.should_trade(aggressive=True)
    print(f"\n📊 Aggressive Mode:")
    print(f"  Can Trade: {'✅ YES' if aggressive['can_trade'] else '❌ NO'}")
    
    # Get all filters
    print("\n🔍 MARKET FILTERS CHECK:")
    filters = await detector.get_market_filters()
    
    for filter_name, passed in filters['filters'].items():
        status = "✅" if passed else "❌"
        print(f"  {filter_name}: {status}")
    
    print(f"\n  All Filters Pass: {'✅ YES' if filters['all_pass'] else '❌ NO'}")

if __name__ == "__main__":
    asyncio.run(test_market_regime())