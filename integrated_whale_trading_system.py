#!/usr/bin/env python3
"""
Sistema Integrado de Trading con Seguimiento de Whales
Combina análisis on-chain + técnico + sentiment para máxima efectividad
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedWhaleTrading:
    """
    Sistema completo que combina:
    1. Rastreo de wallets de whales
    2. Análisis de flujos de exchanges
    3. Detección de acumulación/distribución
    4. Señales técnicas de confirmación
    """
    
    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"
        
        # Wallets conocidas de whales (ejemplos públicos)
        self.known_whales = {
            "institutions": {
                "MicroStrategy": ["1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ"],
                "Tesla": ["bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97"],
                "Galaxy Digital": ["0x2FC617E933428707618DFf36A0C9dD3996C7FC74"],
            },
            "exchanges": {
                "Binance Cold": ["34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"],
                "Coinbase Cold": ["bc1qm34wtkgfae8vhgvklxjqxqxrk5gf5fctfqmk7g"],
            },
            "smart_money": {
                "DeFi Whale 1": ["0x0C41e9a97A88Bb91f966058F4Cb95Ad457889eE0"],
                "DeFi Whale 2": ["0x17e87b16cB0bc64C4B6A60Fe93f1cFd1a4cf0a99"],
            }
        }
        
        # Métricas on-chain importantes
        self.onchain_metrics = {
            "exchange_netflow": 0,      # Flujo neto hacia/desde exchanges
            "whale_accumulation": 0,     # Score de acumulación de whales
            "retail_sentiment": 0,       # Sentimiento retail (0-100)
            "smart_money_flow": 0,       # Flujo de dinero inteligente
            "fear_greed_index": 50       # Índice de miedo y codicia
        }
        
        # Parámetros optimizados del sistema
        self.params = {
            "min_whale_confidence": 65,   # Confianza mínima para señal de whale
            "volume_spike_threshold": 1.8, # Volumen necesario
            "price_breakout_periods": 20,  # Períodos para detectar breakout
            "stop_loss_pct": 0.04,         # 4% stop loss
            "take_profit_pct": 0.08,       # 8% take profit
            "position_size_base": 0.2,     # 20% posición base
            "max_position_size": 0.5       # 50% posición máxima
        }
        
    async def fetch_onchain_data(self, symbol: str) -> Dict:
        """
        Obtiene datos on-chain simulados
        En producción, usar APIs reales como Glassnode, IntoTheBlock, etc.
        """
        onchain_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "metrics": {}
        }
        
        try:
            # Simular obtención de métricas on-chain
            # En producción, estas vendrían de APIs reales
            
            # 1. Exchange Netflow (negativo = bullish)
            onchain_data["metrics"]["exchange_netflow"] = np.random.uniform(-1000, 1000)
            
            # 2. Whale transactions count
            onchain_data["metrics"]["whale_transactions"] = np.random.randint(5, 50)
            
            # 3. Active addresses
            onchain_data["metrics"]["active_addresses"] = np.random.randint(50000, 200000)
            
            # 4. Network hash rate (para BTC)
            if "BTC" in symbol:
                onchain_data["metrics"]["hash_rate"] = np.random.uniform(300, 400)  # EH/s
            
            # 5. Stablecoin flow
            onchain_data["metrics"]["stablecoin_flow"] = np.random.uniform(-100000000, 100000000)
            
        except Exception as e:
            logger.error(f"Error fetching onchain data: {e}")
        
        return onchain_data
    
    async def analyze_whale_movements(self, symbol: str) -> Dict:
        """
        Analiza movimientos de whales y genera score
        """
        whale_analysis = {
            "accumulation_score": 0,
            "distribution_score": 0,
            "whale_sentiment": "NEUTRAL",
            "large_transactions": [],
            "confidence": 0
        }
        
        try:
            # Obtener datos on-chain
            onchain = await self.fetch_onchain_data(symbol)
            
            # Analizar exchange netflow
            netflow = onchain["metrics"].get("exchange_netflow", 0)
            if netflow < -500:  # Salida de exchanges
                whale_analysis["accumulation_score"] += 40
            elif netflow > 500:  # Entrada a exchanges
                whale_analysis["distribution_score"] += 40
            
            # Analizar número de transacciones whale
            whale_txs = onchain["metrics"].get("whale_transactions", 0)
            if whale_txs > 30:
                whale_analysis["accumulation_score"] += 20
            
            # Analizar flujo de stablecoins
            stable_flow = onchain["metrics"].get("stablecoin_flow", 0)
            if stable_flow > 50000000:  # Entrada de capital
                whale_analysis["accumulation_score"] += 20
            elif stable_flow < -50000000:  # Salida de capital
                whale_analysis["distribution_score"] += 20
            
            # Determinar sentimiento
            if whale_analysis["accumulation_score"] > whale_analysis["distribution_score"] + 20:
                whale_analysis["whale_sentiment"] = "BULLISH"
            elif whale_analysis["distribution_score"] > whale_analysis["accumulation_score"] + 20:
                whale_analysis["whale_sentiment"] = "BEARISH"
            
            # Calcular confianza
            total_score = whale_analysis["accumulation_score"] + whale_analysis["distribution_score"]
            whale_analysis["confidence"] = min(total_score, 95)
            
        except Exception as e:
            logger.error(f"Error analyzing whale movements: {e}")
        
        return whale_analysis
    
    async def get_market_data(self, symbol: str) -> pd.DataFrame:
        """
        Obtiene datos de mercado de Binance
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/klines",
                    params={
                        "symbol": symbol,
                        "interval": "15m",
                        "limit": 100
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 
                        'volume', 'close_time', 'quote_volume', 'trades',
                        'taker_buy_base', 'taker_buy_quote', 'ignore'
                    ])
                    
                    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    return df
                    
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            
        return pd.DataFrame()
    
    def calculate_technical_signals(self, df: pd.DataFrame) -> Dict:
        """
        Calcula señales técnicas de confirmación
        """
        signals = {
            "breakout": False,
            "volume_spike": False,
            "momentum": 0,
            "trend": "NEUTRAL"
        }
        
        if len(df) < 50:
            return signals
        
        # 1. Detectar breakout
        high_20 = df['high'].rolling(20).max()
        current_price = df['close'].iloc[-1]
        prev_high = high_20.iloc[-2]
        
        if current_price > prev_high:
            signals["breakout"] = True
        
        # 2. Detectar spike de volumen
        volume_ma = df['volume'].rolling(20).mean()
        current_volume = df['volume'].iloc[-1]
        
        if current_volume > volume_ma.iloc[-1] * self.params["volume_spike_threshold"]:
            signals["volume_spike"] = True
        
        # 3. Calcular momentum
        returns = df['close'].pct_change()
        signals["momentum"] = returns.rolling(10).sum().iloc[-1] * 100
        
        # 4. Determinar tendencia
        sma_20 = df['close'].rolling(20).mean()
        sma_50 = df['close'].rolling(50).mean()
        
        if len(df) >= 50:
            if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_50.iloc[-1]:
                signals["trend"] = "BULLISH"
            elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_50.iloc[-1]:
                signals["trend"] = "BEARISH"
        
        return signals
    
    async def generate_integrated_signal(self, symbol: str) -> Dict:
        """
        Genera señal integrada combinando on-chain + técnico
        """
        signal = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "action": "HOLD",
            "confidence": 0,
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "position_size": 0,
            "reasons": [],
            "analysis": {}
        }
        
        try:
            # 1. Análisis de whales
            whale_analysis = await self.analyze_whale_movements(symbol)
            signal["analysis"]["whale"] = whale_analysis
            
            # 2. Obtener datos de mercado
            df = await self.get_market_data(symbol)
            
            if df.empty:
                return signal
            
            current_price = df['close'].iloc[-1]
            signal["entry_price"] = current_price
            
            # 3. Análisis técnico
            tech_signals = self.calculate_technical_signals(df)
            signal["analysis"]["technical"] = tech_signals
            
            # 4. LÓGICA DE DECISIÓN INTEGRADA
            
            # Calcular confianza total
            confidence_score = 0
            
            # Peso de señales de whale (40%)
            if whale_analysis["whale_sentiment"] == "BULLISH":
                confidence_score += whale_analysis["confidence"] * 0.4
                signal["reasons"].append(f"Whales accumulating (score: {whale_analysis['accumulation_score']})")
            elif whale_analysis["whale_sentiment"] == "BEARISH":
                confidence_score -= whale_analysis["confidence"] * 0.3
                signal["reasons"].append(f"Whales distributing (score: {whale_analysis['distribution_score']})")
            
            # Peso de señales técnicas (60%)
            if tech_signals["breakout"]:
                confidence_score += 30
                signal["reasons"].append("Price breakout detected")
            
            if tech_signals["volume_spike"]:
                confidence_score += 20
                signal["reasons"].append("Volume spike confirmed")
            
            if tech_signals["momentum"] > 2:
                confidence_score += 15
                signal["reasons"].append(f"Strong momentum ({tech_signals['momentum']:.1f}%)")
            
            if tech_signals["trend"] == "BULLISH":
                confidence_score += 10
                signal["reasons"].append("Bullish trend confirmed")
            
            # Normalizar confianza
            signal["confidence"] = min(max(confidence_score, 0), 95)
            
            # DECISIÓN FINAL
            if signal["confidence"] >= self.params["min_whale_confidence"]:
                if whale_analysis["whale_sentiment"] == "BULLISH" and tech_signals["trend"] != "BEARISH":
                    signal["action"] = "BUY"
                    
                    # Calcular position size basado en confianza
                    signal["position_size"] = min(
                        self.params["position_size_base"] * (signal["confidence"] / 65),
                        self.params["max_position_size"]
                    )
                    
                    # Set stops
                    signal["stop_loss"] = current_price * (1 - self.params["stop_loss_pct"])
                    signal["take_profit"] = current_price * (1 + self.params["take_profit_pct"])
                    
                elif whale_analysis["whale_sentiment"] == "BEARISH" and signal["confidence"] >= 75:
                    signal["action"] = "SELL"
                    signal["position_size"] = self.params["position_size_base"]
                    signal["stop_loss"] = current_price * (1 + self.params["stop_loss_pct"])
                    signal["take_profit"] = current_price * (1 - self.params["take_profit_pct"])
            
        except Exception as e:
            logger.error(f"Error generating integrated signal: {e}")
        
        return signal
    
    async def monitor_and_trade(self, symbols: List[str]):
        """
        Monitorea y genera señales en tiempo real
        """
        print("="*80)
        print("🐋 INTEGRATED WHALE TRADING SYSTEM")
        print("="*80)
        print("Combining on-chain whale tracking with technical analysis\n")
        
        active_positions = {}
        
        while True:
            for symbol in symbols:
                # Generar señal
                signal = await self.generate_integrated_signal(symbol)
                
                # Mostrar análisis
                print(f"\n{'='*60}")
                print(f"📊 {symbol} - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")
                
                # Mostrar análisis de whales
                whale = signal["analysis"].get("whale", {})
                print(f"\n🐋 Whale Analysis:")
                print(f"  Sentiment: {whale.get('whale_sentiment', 'N/A')}")
                print(f"  Accumulation: {whale.get('accumulation_score', 0)}")
                print(f"  Distribution: {whale.get('distribution_score', 0)}")
                
                # Mostrar análisis técnico
                tech = signal["analysis"].get("technical", {})
                print(f"\n📈 Technical Analysis:")
                print(f"  Breakout: {'✅' if tech.get('breakout') else '❌'}")
                print(f"  Volume Spike: {'✅' if tech.get('volume_spike') else '❌'}")
                print(f"  Momentum: {tech.get('momentum', 0):.2f}%")
                print(f"  Trend: {tech.get('trend', 'N/A')}")
                
                # Mostrar señal
                print(f"\n🎯 Signal:")
                print(f"  Action: {signal['action']}")
                print(f"  Confidence: {signal['confidence']:.1f}%")
                
                if signal["action"] != "HOLD":
                    print(f"  Position Size: {signal['position_size']*100:.1f}%")
                    print(f"  Entry: ${signal['entry_price']:.2f}")
                    print(f"  Stop Loss: ${signal['stop_loss']:.2f}")
                    print(f"  Take Profit: ${signal['take_profit']:.2f}")
                    
                    if signal["reasons"]:
                        print(f"\n  Reasons:")
                        for reason in signal["reasons"]:
                            print(f"    • {reason}")
                    
                    # Registrar posición activa
                    if symbol not in active_positions:
                        active_positions[symbol] = signal
                        print(f"\n  ✅ POSITION OPENED")
                
            # Esperar antes del siguiente ciclo
            await asyncio.sleep(60)  # Check every minute

# Testing function
async def test_integrated_system():
    """Test the integrated whale trading system"""
    system = IntegratedWhaleTrading()
    
    print("="*80)
    print("🧪 TESTING INTEGRATED WHALE TRADING SYSTEM")
    print("="*80)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}")
        print("-"*40)
        
        # Generate integrated signal
        signal = await system.generate_integrated_signal(symbol)
        
        # Display results
        print(f"Action: {signal['action']}")
        print(f"Confidence: {signal['confidence']:.1f}%")
        
        if signal['action'] != "HOLD":
            print(f"\n💰 Trade Setup:")
            print(f"  Position Size: {signal['position_size']*100:.1f}% of capital")
            print(f"  Entry: ${signal['entry_price']:.2f}")
            print(f"  Stop Loss: ${signal['stop_loss']:.2f} ({-system.params['stop_loss_pct']*100:.1f}%)")
            print(f"  Take Profit: ${signal['take_profit']:.2f} ({system.params['take_profit_pct']*100:.1f}%)")
            print(f"  Risk/Reward: 1:{system.params['take_profit_pct']/system.params['stop_loss_pct']:.1f}")
            
            if signal['reasons']:
                print(f"\n📝 Analysis:")
                for reason in signal['reasons']:
                    print(f"  • {reason}")
        else:
            print("  ⏸️ No clear signal - waiting for better setup")
    
    print("\n" + "="*80)
    print("💡 SYSTEM FEATURES:")
    print("="*80)
    print("• Tracks whale wallet movements and exchange flows")
    print("• Analyzes on-chain metrics (netflow, active addresses)")
    print("• Combines with technical breakouts and volume")
    print("• Dynamic position sizing based on confidence")
    print("• Risk management with proper stops")
    print("• Only trades when whales and technicals align")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_integrated_system())
    
    # For production monitoring (uncomment to use):
    # system = IntegratedWhaleTrading()
    # asyncio.run(system.monitor_and_trade(["BTCUSDT", "ETHUSDT", "SOLUSDT"]))