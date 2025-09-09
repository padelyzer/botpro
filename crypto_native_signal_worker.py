#!/usr/bin/env python3
"""
Crypto-Native Signal Worker
Sistema de señales basado en indicadores crypto-nativos
Reemplaza RSI/MACD con Volume ROC, Order Flow, y Rotación de Sector
"""

import asyncio
import sqlite3
import json
import os
from datetime import datetime
import logging
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_api.crypto_momentum_detector import CryptoMomentumDetector
from trading_api.correlation_analyzer import CorrelationAnalyzer
from trading_api.market_regime_detector import MarketRegimeDetector
from trading_api.nakamoto_philosopher import NakamotoPhilosopher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CryptoNativeSignalWorker:
    """Worker que genera señales usando indicadores crypto-nativos"""
    
    def __init__(self):
        self.running = False
        self.scan_interval = int(os.getenv('SIGNAL_SCAN_INTERVAL', '60'))
        self.db_path = os.getenv('DATABASE_PATH', '/app/data/trading_bot.db')
        
        # Initialize crypto-native components
        self.momentum_detector = CryptoMomentumDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.market_regime = MarketRegimeDetector()
        self.nakamoto = NakamotoPhilosopher()
        
        # Symbols to monitor
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except:
            return sqlite3.connect(':memory:')
    
    async def generate_crypto_native_signal(self, symbol: str) -> dict:
        """
        Generate signal using crypto-native indicators
        No RSI, MACD, or Bollinger Bands!
        """
        try:
            # 1. Check market regime first (macro filter)
            can_trade = await self.market_regime.should_trade(aggressive=False)
            if not can_trade['can_trade']:
                logger.info(f"⏸️ {symbol}: Market conditions unfavorable ({can_trade['regime']})")
                return None
            
            # 2. Get comprehensive momentum analysis
            momentum = await self.momentum_detector.get_comprehensive_momentum(symbol)
            
            # 3. Check if entry conditions are met
            entry_check = await self.momentum_detector.should_enter_position(symbol)
            
            # 4. Get Nakamoto's analysis
            # Get current price from momentum data
            current_price = await self._get_current_price(symbol)
            nakamoto_analysis = await self.nakamoto.analyze(symbol, current_price)
            
            # 5. Check sector rotation
            money_flow = await self.correlation_analyzer.get_money_flow_map()
            
            # Generate signal if conditions are favorable
            if entry_check['action'] == "BUY" and nakamoto_analysis['confidence'] > 65:
                signal = {
                    'id': f"{symbol}_{datetime.now().timestamp()}",
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'action': "BUY",
                    'philosopher': "Nakamoto",
                    'confidence': nakamoto_analysis['confidence'],
                    'entry_price': current_price,
                    'stop_loss': nakamoto_analysis['stop_loss'],
                    'take_profit': nakamoto_analysis['take_profit'],
                    'timeframe': self._determine_timeframe(momentum),
                    'reasoning': nakamoto_analysis['reasoning'],
                    'indicators': {
                        'volume_roc': momentum['indicators']['volume_roc']['percent'],
                        'price_acceleration': momentum['indicators']['price_acceleration']['value'],
                        'order_flow': momentum['indicators']['order_flow']['buy_pressure'],
                        'funding_rate': momentum['indicators']['funding_rate']['value'],
                        'market_regime': can_trade['regime'],
                        'sector_rotation': money_flow.get('leading_sector', 'Unknown')
                    },
                    'entry_conditions': entry_check['reasons']
                }
                
                return signal
            
            # Check for exit conditions if we might be in a position
            elif momentum['final_signal'] == "SELL" or nakamoto_analysis['action'] == "SELL":
                # Simulate entry at -2% for exit check
                exit_check = await self.momentum_detector.should_exit_position(
                    symbol, current_price * 1.02
                )
                
                if exit_check['action'] == "SELL":
                    signal = {
                        'id': f"{symbol}_{datetime.now().timestamp()}",
                        'timestamp': datetime.now().isoformat(),
                        'symbol': symbol,
                        'action': "SELL",
                        'philosopher': "Nakamoto",
                        'confidence': 75,
                        'entry_price': current_price,
                        'stop_loss': current_price * 1.03,
                        'take_profit': current_price * 0.97,
                        'timeframe': "EXIT",
                        'reasoning': [
                            "Exit conditions triggered",
                            f"Volume: {exit_check['reasons']['volume_dying']}",
                            f"Funding: {exit_check['reasons']['overheated_funding']}",
                            f"Momentum: {exit_check['reasons']['losing_momentum']}"
                        ],
                        'indicators': momentum['indicators'],
                        'exit_conditions': exit_check['reasons']
                    }
                    
                    return signal
            
            logger.debug(f"📊 {symbol}: No clear signal (Confidence: {nakamoto_analysis['confidence']}%)")
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": symbol},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return float(response.json()['price'])
        except:
            pass
        
        # Fallback prices
        defaults = {
            "BTCUSDT": 115000, "ETHUSDT": 4800, "BNBUSDT": 880,
            "SOLUSDT": 205, "ADAUSDT": 0.92, "XRPUSDT": 3.05, "DOGEUSDT": 0.24
        }
        return defaults.get(symbol, 100)
    
    def _determine_timeframe(self, momentum: Dict) -> str:
        """Determine timeframe based on momentum indicators"""
        vroc = momentum['indicators']['volume_roc']['value']
        
        if vroc > 3.0:
            return "SCALPING"  # High volume = quick trades
        elif vroc > 2.0:
            return "INTRADAY"
        elif vroc > 1.5:
            return "SWING"
        else:
            return "POSITION"
    
    def save_signal(self, signal: dict):
        """Save signal to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crypto_signals (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    symbol TEXT,
                    action TEXT,
                    philosopher TEXT,
                    confidence REAL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    reasoning TEXT,
                    timeframe TEXT,
                    indicators TEXT,
                    conditions TEXT
                )
            ''')
            
            # Insert signal
            cursor.execute('''
                INSERT OR REPLACE INTO crypto_signals 
                (id, timestamp, symbol, action, philosopher, confidence,
                 entry_price, stop_loss, take_profit, reasoning, timeframe,
                 indicators, conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (signal['id'], signal['timestamp'], signal['symbol'], 
                  signal['action'], signal['philosopher'], signal['confidence'],
                  signal['entry_price'], signal['stop_loss'], signal['take_profit'],
                  json.dumps(signal['reasoning']), signal['timeframe'],
                  json.dumps(signal.get('indicators', {})),
                  json.dumps(signal.get('entry_conditions', signal.get('exit_conditions', {})))))
            
            conn.commit()
            conn.close()
            
            self._log_signal(signal)
            
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
    
    def _log_signal(self, signal: dict):
        """Log signal details"""
        logger.info(f"""
        ╔══════════════════════════════════════════════════════════╗
        ║ 🚀 CRYPTO-NATIVE SIGNAL GENERATED                       ║
        ╠══════════════════════════════════════════════════════════╣
        ║ Symbol: {signal['symbol']:<20} Action: {signal['action']:<10} ║
        ║ Confidence: {signal['confidence']:.1f}%                                    ║
        ║ Entry: ${signal['entry_price']:<15.2f} Timeframe: {signal['timeframe']:<10} ║
        ║ TP: ${signal['take_profit']:<15.2f} SL: ${signal['stop_loss']:<15.2f} ║
        ╟──────────────────────────────────────────────────────────╢
        ║ CRYPTO INDICATORS:                                       ║
        ║ Volume ROC: {signal['indicators'].get('volume_roc', 0):>6.0f}%                             ║
        ║ Order Flow: {signal['indicators'].get('order_flow', 50):>6.0f}% buy pressure                ║
        ║ Funding:    {signal['indicators'].get('funding_rate', 0):>6.3f}%                           ║
        ║ Regime:     {signal['indicators'].get('market_regime', 'Unknown'):<20}        ║
        ╚══════════════════════════════════════════════════════════╝
        """)
    
    async def scan_markets(self):
        """Scan markets using crypto-native indicators"""
        signals_generated = 0
        
        logger.info("=" * 60)
        logger.info("🔍 CRYPTO-NATIVE MARKET SCAN")
        logger.info("=" * 60)
        
        # First check overall market conditions
        market_filters = await self.market_regime.get_market_filters()
        
        logger.info(f"📊 Market Regime: {market_filters['regime']}")
        logger.info(f"   Can Trade: {'✅' if market_filters['can_trade'] else '❌'}")
        
        if not market_filters['can_trade']:
            logger.info("⏸️ Market conditions unfavorable - skipping scan")
            return
        
        # Get money flow analysis
        money_flow = await self.correlation_analyzer.get_money_flow_map()
        logger.info(f"🔄 Leading Sector: {money_flow.get('leading_sector', 'Unknown')}")
        logger.info(f"📈 Alt Season Index: {money_flow.get('altcoin_season_index', 0):.0f}")
        
        # Prioritize symbols based on sector rotation
        prioritized_symbols = self._prioritize_symbols(money_flow)
        
        # Scan prioritized symbols
        for symbol in prioritized_symbols:
            try:
                logger.info(f"\n🎯 Analyzing {symbol}...")
                
                signal = await self.generate_crypto_native_signal(symbol)
                
                if signal and signal['confidence'] >= 65:
                    self.save_signal(signal)
                    signals_generated += 1
                    
                    # Limit signals per scan
                    if signals_generated >= 3:
                        logger.info("📊 Signal limit reached for this scan")
                        break
                        
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
        
        if signals_generated > 0:
            logger.info(f"\n✅ Generated {signals_generated} crypto-native signals")
        else:
            logger.info("\n📊 No high-confidence signals in this scan")
        
        logger.info("=" * 60)
    
    def _prioritize_symbols(self, money_flow: Dict) -> list:
        """Prioritize symbols based on sector rotation"""
        sector_symbols = {
            "STORE_OF_VALUE": ["BTCUSDT"],
            "SMART_CONTRACTS": ["ETHUSDT", "BNBUSDT"],
            "HIGH_PERFORMANCE": ["SOLUSDT"],
            "PAYMENTS": ["XRPUSDT"],
            "MEME": ["DOGEUSDT"],
            "DEFI": ["ADAUSDT"]
        }
        
        leading_sector = money_flow.get('leading_sector', "UNKNOWN")
        
        # Start with leading sector symbols
        prioritized = sector_symbols.get(leading_sector, [])
        
        # Add other symbols
        for symbol in self.symbols:
            if symbol not in prioritized:
                prioritized.append(symbol)
        
        return prioritized[:5]  # Limit to top 5
    
    async def start(self):
        """Start the crypto-native signal worker"""
        self.running = True
        
        logger.info("""
        ╔══════════════════════════════════════════════════════════╗
        ║     🚀 CRYPTO-NATIVE SIGNAL WORKER - BOTPHIA 🚀         ║
        ║                                                          ║
        ║  Crypto-Native Trading System                           ║
        ║  • NO RSI, MACD, or Bollinger Bands                     ║
        ║  • Volume Rate of Change (VROC)                         ║
        ║  • Order Flow Imbalance                                 ║
        ║  • Funding Rate Analysis                                ║
        ║  • Sector Rotation Detection                            ║
        ║  • Market Regime Filters                                ║
        ║                                                          ║
        ║  Philosophy: "Volume precedes price"                    ║
        ║              "Follow the money flow"                    ║
        ║              "Trade with momentum, not against it"      ║
        ╚══════════════════════════════════════════════════════════╝
        """)
        
        logger.info(f"⚙️ Configuration:")
        logger.info(f"   • Scan interval: {self.scan_interval} seconds")
        logger.info(f"   • Symbols: {', '.join(self.symbols)}")
        logger.info(f"   • Database: {self.db_path}")
        
        scan_count = 0
        while self.running:
            try:
                scan_count += 1
                logger.info(f"\n🔄 Scan #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Scan markets with crypto-native indicators
                await self.scan_markets()
                
                # Wait before next scan
                logger.info(f"⏰ Next scan in {self.scan_interval} seconds...")
                await asyncio.sleep(self.scan_interval)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in signal worker: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("Crypto-Native Signal Worker stopped")

async def main():
    """Main function"""
    worker = CryptoNativeSignalWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
        worker.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        worker.stop()

if __name__ == "__main__":
    asyncio.run(main())