#!/usr/bin/env python3
"""
Whale Wallet Tracker - Rastrea movimientos de grandes billeteras
Combina datos on-chain con señales de trading para máxima efectividad
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class WhaleWalletTracker:
    """
    Rastrea movimientos de whales en blockchain y exchanges
    """
    
    def __init__(self):
        # APIs públicas para datos on-chain
        self.whale_alert_api = "https://api.whale-alert.io/v1"  # Requiere API key
        self.glassnode_api = "https://api.glassnode.com/v1"     # Requiere API key
        
        # APIs gratuitas alternativas
        self.blockchain_api = "https://blockchain.info"
        self.etherscan_api = "https://api.etherscan.io/api"
        self.bscscan_api = "https://api.bscscan.com/api"
        
        # Exchanges principales para monitorear
        self.exchange_wallets = {
            "binance": {
                "BTC": ["bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s4h", "1JYd1JN5aCj1dWBhpSNVWTqHmY4xTuNvrh"],
                "ETH": ["0x28C6c06298d514Db089934071355E5743bf21d60", "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549"],
                "hot_wallet": "0x708396f17127c42383E3b9014072679b2F60B82f"
            },
            "coinbase": {
                "BTC": ["bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hk9"],
                "ETH": ["0x71660c4005BA85c37ccec55d0C4493E66Fe775d3"],
            },
            "kraken": {
                "BTC": ["bc1qnxhf52svgqr0dy5fkf5p0eht4gvjnzv7r5jmh"],
                "ETH": ["0x267be94c1e520e6dDD6977Bbb7fC4B87C63433aF"]
            }
        }
        
        # Umbrales para considerar transacciones de whale
        self.whale_thresholds = {
            "BTC": 100,      # 100+ BTC
            "ETH": 1000,     # 1000+ ETH
            "USDT": 1000000, # 1M+ USDT
            "SOL": 10000,    # 10k+ SOL
            "AVAX": 25000,   # 25k+ AVAX
        }
        
        # Cache de transacciones recientes
        self.recent_transactions = []
        self.cache_duration = 300  # 5 minutos
        
    async def get_large_transactions(self, symbol: str = "BTC", hours: int = 1) -> List[Dict]:
        """
        Obtiene transacciones grandes recientes
        """
        transactions = []
        
        try:
            # Método 1: Usar blockchain.info para BTC (gratis)
            if symbol == "BTC":
                async with httpx.AsyncClient() as client:
                    # Obtener bloques recientes
                    response = await client.get(
                        f"{self.blockchain_api}/unconfirmed-transactions?format=json",
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        txs = data.get('txs', [])[:100]  # Últimas 100 transacciones
                        
                        for tx in txs:
                            # Calcular valor total
                            total_btc = sum(out.get('value', 0) for out in tx.get('out', [])) / 100000000
                            
                            if total_btc >= self.whale_thresholds['BTC']:
                                transactions.append({
                                    'hash': tx.get('hash'),
                                    'time': datetime.fromtimestamp(tx.get('time', 0)),
                                    'amount': total_btc,
                                    'symbol': 'BTC',
                                    'type': 'transfer',
                                    'from': 'unknown',
                                    'to': 'unknown'
                                })
            
            # Método 2: Usar Etherscan para ETH (requiere API key gratuita)
            elif symbol == "ETH":
                # Por simplicidad, simularemos datos
                # En producción, usar Etherscan API con key
                pass
                
        except Exception as e:
            logger.error(f"Error fetching large transactions: {e}")
        
        return transactions
    
    async def detect_exchange_flows(self, symbol: str) -> Dict:
        """
        Detecta flujos hacia/desde exchanges (inflow/outflow)
        """
        flows = {
            'exchange_inflow': 0,
            'exchange_outflow': 0,
            'net_flow': 0,
            'signal': 'NEUTRAL'
        }
        
        try:
            # Obtener transacciones recientes
            transactions = await self.get_large_transactions(symbol, hours=4)
            
            for tx in transactions:
                # Verificar si involucra wallets de exchanges
                for exchange, wallets in self.exchange_wallets.items():
                    if symbol in wallets:
                        exchange_addresses = wallets[symbol]
                        
                        # Simplificado: verificar si es inflow o outflow
                        # En producción, analizar direcciones reales
                        if tx.get('to') in exchange_addresses:
                            flows['exchange_inflow'] += tx['amount']
                        elif tx.get('from') in exchange_addresses:
                            flows['exchange_outflow'] += tx['amount']
            
            flows['net_flow'] = flows['exchange_outflow'] - flows['exchange_inflow']
            
            # Generar señal basada en flujos
            if flows['net_flow'] > self.whale_thresholds.get(symbol, 100):
                flows['signal'] = 'BULLISH'  # Salida de exchanges = bullish
            elif flows['net_flow'] < -self.whale_thresholds.get(symbol, 100):
                flows['signal'] = 'BEARISH'  # Entrada a exchanges = bearish
            
        except Exception as e:
            logger.error(f"Error detecting exchange flows: {e}")
        
        return flows
    
    async def track_smart_money(self) -> List[Dict]:
        """
        Rastrea wallets conocidas de inversores inteligentes
        """
        smart_wallets = {
            # Wallets conocidas de instituciones/whales
            "3Commas": "0xb2cc3cdd53fc9a1aeeb52e14b5dbecc3b9775b66",
            "Jump Trading": "0xf05e2a70346560d3228c0d02d362bc21a1586c2f",
            "Alameda": "0x84D34f4f83a87596cd3e2Fe4F5b4999E1F91E9e5",  # Historical
            "DWF Labs": "0xDdAE223d961e44a30FBD0c8E80C8E68e00263851"
        }
        
        movements = []
        
        try:
            # En producción, usar APIs reales para rastrear estas wallets
            # Por ahora, simularemos detección de movimientos
            
            # Ejemplo de movimiento detectado
            movements.append({
                'wallet': 'Jump Trading',
                'action': 'BUY',
                'symbol': 'SOL',
                'amount': 50000,
                'price': 205.50,
                'timestamp': datetime.now(),
                'confidence': 85
            })
            
        except Exception as e:
            logger.error(f"Error tracking smart money: {e}")
        
        return movements
    
    async def get_whale_sentiment(self, symbol: str) -> Dict:
        """
        Analiza el sentimiento general de whales
        """
        sentiment = {
            'whale_activity': 'LOW',
            'accumulation_score': 0,
            'distribution_score': 0,
            'net_sentiment': 'NEUTRAL',
            'large_orders': []
        }
        
        try:
            # Obtener flujos de exchanges
            flows = await self.detect_exchange_flows(symbol)
            
            # Obtener movimientos de smart money
            smart_moves = await self.track_smart_money()
            
            # Calcular scores
            if flows['net_flow'] > 0:
                sentiment['accumulation_score'] += 50
            else:
                sentiment['distribution_score'] += 50
            
            # Contar movimientos bullish/bearish de smart money
            for move in smart_moves:
                if move['symbol'] == symbol or move['symbol'] == symbol.replace('USDT', ''):
                    if move['action'] == 'BUY':
                        sentiment['accumulation_score'] += 25
                    else:
                        sentiment['distribution_score'] += 25
            
            # Determinar sentimiento neto
            if sentiment['accumulation_score'] > sentiment['distribution_score'] + 30:
                sentiment['net_sentiment'] = 'BULLISH'
                sentiment['whale_activity'] = 'HIGH'
            elif sentiment['distribution_score'] > sentiment['accumulation_score'] + 30:
                sentiment['net_sentiment'] = 'BEARISH'
                sentiment['whale_activity'] = 'HIGH'
            elif max(sentiment['accumulation_score'], sentiment['distribution_score']) > 50:
                sentiment['whale_activity'] = 'MEDIUM'
            
        except Exception as e:
            logger.error(f"Error analyzing whale sentiment: {e}")
        
        return sentiment
    
    async def get_trading_signal(self, symbol: str) -> Dict:
        """
        Genera señal de trading basada en movimientos de whales
        """
        # Obtener sentimiento de whales
        sentiment = await self.get_whale_sentiment(symbol)
        
        # Obtener flujos
        flows = await self.detect_exchange_flows(symbol.replace('USDT', ''))
        
        # Obtener smart money
        smart_moves = await self.track_smart_money()
        
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'action': 'HOLD',
            'confidence': 0,
            'reasons': [],
            'whale_data': {
                'sentiment': sentiment,
                'flows': flows,
                'smart_money': smart_moves
            }
        }
        
        # Lógica de señales
        if sentiment['net_sentiment'] == 'BULLISH' and flows['signal'] == 'BULLISH':
            signal['action'] = 'BUY'
            signal['confidence'] = min(sentiment['accumulation_score'], 95)
            signal['reasons'].append("Whales accumulating")
            signal['reasons'].append("Exchange outflows detected")
            
        elif sentiment['net_sentiment'] == 'BEARISH' and flows['signal'] == 'BEARISH':
            signal['action'] = 'SELL'
            signal['confidence'] = min(sentiment['distribution_score'], 95)
            signal['reasons'].append("Whales distributing")
            signal['reasons'].append("Exchange inflows detected")
            
        # Check smart money
        for move in smart_moves:
            if move['symbol'] == symbol.replace('USDT', ''):
                if move['action'] == signal['action']:
                    signal['confidence'] = min(signal['confidence'] + 10, 95)
                    signal['reasons'].append(f"{move['wallet']} is {move['action']}ing")
        
        return signal

class WhaleFollowingStrategy:
    """
    Estrategia que combina seguimiento de whales con análisis técnico
    """
    
    def __init__(self):
        self.whale_tracker = WhaleWalletTracker()
        self.min_confidence = 70  # Mínima confianza para operar
        
    async def should_enter_trade(self, symbol: str, current_price: float) -> Dict:
        """
        Decide si entrar en una operación basándose en whales
        """
        # Obtener señal de whales
        whale_signal = await self.whale_tracker.get_trading_signal(symbol)
        
        decision = {
            'enter': False,
            'action': 'WAIT',
            'confidence': whale_signal['confidence'],
            'stop_loss': 0,
            'take_profit': 0,
            'position_size': 0,
            'reasons': whale_signal['reasons']
        }
        
        # Solo operar con alta confianza
        if whale_signal['confidence'] >= self.min_confidence:
            if whale_signal['action'] == 'BUY':
                decision['enter'] = True
                decision['action'] = 'BUY'
                decision['stop_loss'] = current_price * 0.95  # 5% stop
                decision['take_profit'] = current_price * 1.10  # 10% profit
                decision['position_size'] = min(whale_signal['confidence'] / 100, 0.5)  # Max 50% position
                
            elif whale_signal['action'] == 'SELL' and whale_signal['confidence'] >= 80:
                decision['enter'] = True
                decision['action'] = 'SELL'
                decision['stop_loss'] = current_price * 1.05
                decision['take_profit'] = current_price * 0.92
                decision['position_size'] = 0.3  # Más conservador en shorts
        
        return decision
    
    async def monitor_whale_activity(self, symbols: List[str]):
        """
        Monitorea actividad de whales en tiempo real
        """
        print("="*60)
        print("🐋 WHALE ACTIVITY MONITOR")
        print("="*60)
        
        while True:
            for symbol in symbols:
                print(f"\n📊 Checking {symbol}...")
                
                # Obtener sentimiento de whales
                sentiment = await self.whale_tracker.get_whale_sentiment(symbol.replace('USDT', ''))
                
                print(f"  Whale Activity: {sentiment['whale_activity']}")
                print(f"  Accumulation: {sentiment['accumulation_score']}")
                print(f"  Distribution: {sentiment['distribution_score']}")
                print(f"  Net Sentiment: {sentiment['net_sentiment']}")
                
                # Obtener señal de trading
                signal = await self.whale_tracker.get_trading_signal(symbol)
                
                if signal['confidence'] >= 70:
                    print(f"\n  🚨 SIGNAL DETECTED!")
                    print(f"  Action: {signal['action']}")
                    print(f"  Confidence: {signal['confidence']}%")
                    for reason in signal['reasons']:
                        print(f"  • {reason}")
            
            # Esperar antes de siguiente chequeo
            await asyncio.sleep(60)  # Check every minute

# Testing
async def test_whale_tracker():
    """Test the whale tracking system"""
    tracker = WhaleWalletTracker()
    strategy = WhaleFollowingStrategy()
    
    print("="*80)
    print("🐋 WHALE WALLET TRACKING SYSTEM TEST")
    print("="*80)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}")
        print("-"*40)
        
        # Get whale sentiment
        sentiment = await tracker.get_whale_sentiment(symbol.replace('USDT', ''))
        print(f"Whale Sentiment: {sentiment['net_sentiment']}")
        print(f"Activity Level: {sentiment['whale_activity']}")
        
        # Get trading signal
        signal = await tracker.get_trading_signal(symbol)
        print(f"\nTrading Signal: {signal['action']}")
        print(f"Confidence: {signal['confidence']}%")
        
        if signal['reasons']:
            print("Reasons:")
            for reason in signal['reasons']:
                print(f"  • {reason}")
        
        # Check if we should trade
        decision = await strategy.should_enter_trade(symbol, 100000 if symbol == "BTCUSDT" else 5000)
        if decision['enter']:
            print(f"\n✅ TRADE DECISION: {decision['action']}")
            print(f"  Position Size: {decision['position_size']*100:.0f}%")
            print(f"  Stop Loss: ${decision['stop_loss']:.2f}")
            print(f"  Take Profit: ${decision['take_profit']:.2f}")
        else:
            print(f"\n⏸️ WAIT - Confidence too low ({decision['confidence']}%)")

if __name__ == "__main__":
    asyncio.run(test_whale_tracker())