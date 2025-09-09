#!/usr/bin/env python3
"""
Nakamoto - El Filósofo Crypto-Nativo
Especializado en análisis de momentum, volumen y rotación de capital
"""

import asyncio
from typing import Dict, List
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_api.crypto_momentum_detector import CryptoMomentumDetector
from trading_api.correlation_analyzer import CorrelationAnalyzer
from trading_api.market_regime_detector import MarketRegimeDetector

class NakamotoPhilosopher:
    """
    Satoshi Nakamoto - El filósofo crypto-nativo
    
    Filosofía:
    - "El volumen precede al precio"
    - "Sigue el flujo del dinero, no las emociones"
    - "En crypto, el momentum es todo"
    - "Los indicadores tradicionales son para mercados tradicionales"
    """
    
    def __init__(self):
        self.name = "Nakamoto"
        self.style = "CRYPTO_NATIVE"
        
        # Initialize crypto-native analyzers
        self.momentum_detector = CryptoMomentumDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.market_regime = MarketRegimeDetector()
        
        # Trading principles
        self.principles = [
            "Volume spikes reveal smart money moves",
            "Follow sector rotation, not individual coins",
            "Trade with the macro trend, not against it",
            "Order flow > Technical patterns",
            "Funding rates reveal true sentiment"
        ]
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """
        Análisis crypto-nativo completo
        """
        # 1. Check macro conditions first
        market_filters = await self.market_regime.get_market_filters()
        
        if not market_filters['can_trade']:
            return {
                "action": "HOLD",
                "confidence": 30,
                "reasoning": [
                    f"{self.name}: Market conditions unfavorable",
                    f"Regime: {market_filters['regime']}",
                    "Waiting for better macro conditions"
                ],
                "analysis_type": "MACRO_FILTER",
                "indicators": market_filters
            }
        
        # 2. Get comprehensive momentum analysis
        momentum = await self.momentum_detector.get_comprehensive_momentum(symbol)
        
        # 3. Check rotation and correlation
        money_flow = await self.correlation_analyzer.get_money_flow_map()
        
        # 4. Determine action based on crypto-native signals
        action, confidence, reasoning = await self._determine_action(
            symbol, momentum, money_flow, market_filters
        )
        
        # 5. Calculate stops and targets
        stops_targets = self._calculate_crypto_stops(
            action, current_price, momentum, confidence
        )
        
        return {
            "philosopher": self.name,
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "analysis_type": "CRYPTO_NATIVE",
            "entry_price": current_price,
            "stop_loss": stops_targets['stop_loss'],
            "take_profit": stops_targets['take_profit'],
            "indicators": {
                "volume_roc": momentum['indicators']['volume_roc'],
                "price_acceleration": momentum['indicators']['price_acceleration'],
                "order_flow": momentum['indicators']['order_flow'],
                "funding_rate": momentum['indicators']['funding_rate'],
                "market_regime": market_filters['regime'],
                "altcoin_season_index": money_flow.get('altcoin_season_index', 50)
            },
            "signals": {
                "momentum_signal": momentum['final_signal'],
                "entry_conditions_met": momentum['entry_conditions_met'],
                "sector_rotation": money_flow.get('leading_sector'),
                "best_pair_trade": money_flow.get('best_pairs')
            }
        }
    
    async def _determine_action(self, symbol: str, momentum: Dict, 
                                money_flow: Dict, market_filters: Dict) -> tuple:
        """
        Determinar acción basada en señales crypto-nativas
        """
        reasoning = [f"{self.name}: Analyzing {symbol} with crypto-native indicators"]
        
        # Count bullish vs bearish signals
        bullish_signals = 0
        bearish_signals = 0
        
        # 1. Volume Analysis (Most Important)
        if momentum['indicators']['volume_roc']['spike']:
            bullish_signals += 2
            reasoning.append(f"🔥 Volume spike detected ({momentum['indicators']['volume_roc']['percent']:.0f}%)")
        elif momentum['indicators']['volume_roc']['value'] < 0.5:
            bearish_signals += 1
            reasoning.append("📉 Volume dying")
        
        # 2. Price Acceleration
        if momentum['indicators']['price_acceleration']['trend'] == "UP":
            bullish_signals += 1
            reasoning.append("📈 Price accelerating upward")
        elif momentum['indicators']['price_acceleration']['trend'] == "DOWN":
            bearish_signals += 1
            reasoning.append("📉 Price accelerating downward")
        
        # 3. Order Flow
        buy_pressure = momentum['indicators']['order_flow']['buy_pressure']
        if buy_pressure > 60:
            bullish_signals += 1
            reasoning.append(f"💪 Strong buy pressure ({buy_pressure:.0f}%)")
        elif buy_pressure < 40:
            bearish_signals += 1
            reasoning.append(f"🔻 Sell pressure dominant ({100-buy_pressure:.0f}%)")
        
        # 4. Funding Rate
        funding = momentum['indicators']['funding_rate']['value']
        if 0 < funding < 0.05:
            bullish_signals += 1
            reasoning.append(f"✅ Healthy funding rate ({funding:.3f}%)")
        elif funding > 0.1:
            bearish_signals += 1
            reasoning.append(f"⚠️ Overheated funding ({funding:.3f}%)")
        
        # 5. Sector Rotation
        symbol_base = symbol.replace("USDT", "")
        if self._is_in_leading_sector(symbol_base, money_flow):
            bullish_signals += 1
            reasoning.append(f"🔄 In leading sector: {money_flow.get('leading_sector', 'Unknown')}")
        
        # 6. Market Regime
        if market_filters['regime'] in ["BULL_MARKET", "EARLY_BULL"]:
            bullish_signals += 1
            reasoning.append(f"🐂 {market_filters['regime'].replace('_', ' ').title()}")
        elif market_filters['regime'] == "BEAR_MARKET":
            bearish_signals += 1
            reasoning.append("🐻 Bear market regime")
        
        # Determine action and confidence
        if bullish_signals >= 4 and momentum['entry_conditions_met']['volume_spike']:
            action = "BUY"
            confidence = min(95, 60 + bullish_signals * 5)
            reasoning.append(f"Strong BUY signal ({bullish_signals} bullish indicators)")
        elif bullish_signals > bearish_signals + 1:
            action = "BUY"
            confidence = min(85, 50 + bullish_signals * 5)
            reasoning.append(f"BUY signal ({bullish_signals} vs {bearish_signals})")
        elif bearish_signals > bullish_signals + 1:
            action = "SELL"
            confidence = min(85, 50 + bearish_signals * 5)
            reasoning.append(f"SELL signal ({bearish_signals} bearish indicators)")
        else:
            action = "HOLD"
            confidence = 50
            reasoning.append("Mixed signals - waiting for clarity")
        
        # Add Nakamoto wisdom
        if action == "BUY" and momentum['indicators']['volume_roc']['spike']:
            reasoning.append("💎 'Volume precedes price' - Nakamoto")
        elif action == "SELL" and funding > 0.1:
            reasoning.append("📊 'When everyone's long, it's time to short' - Nakamoto")
        elif action == "HOLD":
            reasoning.append("⏳ 'Patience is the ultimate alpha' - Nakamoto")
        
        return action, confidence, reasoning
    
    def _is_in_leading_sector(self, symbol: str, money_flow: Dict) -> bool:
        """Check if symbol is in the leading sector"""
        sector_mapping = {
            "BTC": "STORE_OF_VALUE",
            "ETH": "SMART_CONTRACTS",
            "BNB": "SMART_CONTRACTS",
            "SOL": "HIGH_PERFORMANCE",
            "AVAX": "HIGH_PERFORMANCE",
            "ADA": "SMART_CONTRACTS",
            "XRP": "PAYMENTS",
            "DOGE": "MEME",
            "SHIB": "MEME"
        }
        
        symbol_sector = sector_mapping.get(symbol, "UNKNOWN")
        leading_sector = money_flow.get('leading_sector', "UNKNOWN")
        
        return symbol_sector == leading_sector
    
    def _calculate_crypto_stops(self, action: str, price: float, 
                               momentum: Dict, confidence: float) -> Dict:
        """
        Calculate crypto-specific stops and targets
        Based on volatility and momentum, not fixed percentages
        """
        # Base risk based on confidence
        if confidence > 80:
            risk_mult = 0.03  # 3% risk for high confidence
            reward_mult = 0.06  # 2:1 R:R minimum
        elif confidence > 65:
            risk_mult = 0.02  # 2% risk for medium confidence
            reward_mult = 0.03  # 1.5:1 R:R
        else:
            risk_mult = 0.015  # 1.5% risk for low confidence
            reward_mult = 0.02  # 1.3:1 R:R
        
        # Adjust based on funding rate (higher funding = tighter stops)
        funding = momentum['indicators']['funding_rate']['value']
        if funding > 0.08:
            risk_mult *= 0.7  # Tighter stop when overheated
        
        # Adjust based on volume (high volume = wider targets)
        if momentum['indicators']['volume_roc']['spike']:
            reward_mult *= 1.5  # Bigger targets on volume spikes
        
        if action == "BUY":
            stop_loss = price * (1 - risk_mult)
            take_profit = price * (1 + reward_mult)
        elif action == "SELL":
            stop_loss = price * (1 + risk_mult)
            take_profit = price * (1 - reward_mult)
        else:  # HOLD
            stop_loss = price * 0.97
            take_profit = price * 1.03
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": reward_mult / risk_mult if risk_mult > 0 else 1.5
        }
    
    async def get_quick_signal(self, symbol: str) -> Dict:
        """
        Quick signal generation for real-time decisions
        """
        # Check if we should enter
        entry = await self.momentum_detector.should_enter_position(symbol)
        
        if entry['action'] == "BUY":
            return {
                "philosopher": self.name,
                "action": "BUY",
                "confidence": entry['confidence'],
                "reasoning": [
                    f"{self.name}: Entry conditions met",
                    f"Volume: {entry['reasons']['volume_spike']}",
                    f"Momentum: {entry['reasons']['positive_momentum']}",
                    f"Funding: {entry['reasons']['healthy_funding']}",
                    f"Order Flow: {entry['reasons']['buy_pressure']}"
                ]
            }
        
        return {
            "philosopher": self.name,
            "action": "WAIT",
            "confidence": 40,
            "reasoning": [
                f"{self.name}: Entry conditions not met",
                "Waiting for volume spike and momentum"
            ]
        }

# Integration function for existing system
async def get_nakamoto_analysis(symbol: str, price: float) -> Dict:
    """
    Get Nakamoto's crypto-native analysis
    Can be integrated into existing philosopher council
    """
    nakamoto = NakamotoPhilosopher()
    return await nakamoto.analyze(symbol, price)

# Testing
async def test_nakamoto():
    """Test Nakamoto philosopher"""
    nakamoto = NakamotoPhilosopher()
    
    print("="*60)
    print("🎩 NAKAMOTO - THE CRYPTO-NATIVE PHILOSOPHER")
    print("="*60)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"Analyzing {symbol}")
        print('='*50)
        
        # Get current price (mock for testing)
        analysis = await nakamoto.analyze(symbol, 50000 if symbol == "BTCUSDT" else 3000)
        
        print(f"\n📊 NAKAMOTO'S ANALYSIS:")
        print(f"Action: {analysis['action']}")
        print(f"Confidence: {analysis['confidence']}%")
        
        print("\n💭 Reasoning:")
        for reason in analysis['reasoning']:
            print(f"  {reason}")
        
        print("\n📈 Key Indicators:")
        indicators = analysis['indicators']
        print(f"  Volume ROC: {indicators['volume_roc']['percent']:.0f}%")
        print(f"  Order Flow: {indicators['order_flow']['buy_pressure']:.0f}% buy pressure")
        print(f"  Funding Rate: {indicators['funding_rate']['value']:.3f}%")
        print(f"  Market Regime: {indicators['market_regime']}")
        
        if analysis['action'] != "HOLD":
            print(f"\n🎯 Targets:")
            print(f"  Entry: ${analysis['entry_price']:.2f}")
            print(f"  Stop Loss: ${analysis['stop_loss']:.2f}")
            print(f"  Take Profit: ${analysis['take_profit']:.2f}")

if __name__ == "__main__":
    asyncio.run(test_nakamoto())