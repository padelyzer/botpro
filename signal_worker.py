#!/usr/bin/env python3
"""
SIGNAL WORKER - Generador de Señales Automático
Proceso independiente que genera señales cada 30 segundos
Funciona con o sin API keys
"""

import asyncio
import logging
import json
from datetime import datetime
import os
import sys

# Agregar el directorio al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smart_trading_system import get_trading_system, SignalGenerator
from websocket_manager import get_websocket_manager, broadcast_signal_update

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalWorker:
    """Worker que genera señales continuamente"""
    
    def __init__(self):
        self.system = get_trading_system()
        self.signal_generator = SignalGenerator()
        self.ws_manager = get_websocket_manager()
        self.running = False
        self.scan_interval = int(os.getenv('SIGNAL_SCAN_INTERVAL', '30'))
        
        logger.info(f"📡 Signal Worker initialized")
        logger.info(f"   Mode: {self.system.mode}")
        logger.info(f"   Scan interval: {self.scan_interval} seconds")
    
    async def start(self):
        """Iniciar el worker"""
        self.running = True
        logger.info("🚀 Signal Worker started")
        
        # Iniciar el sistema de trading
        self.system.start()
        
        scan_count = 0
        while self.running:
            try:
                scan_count += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"🔍 Scan #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Generar señales
                signals = await self.signal_generator.scan_markets()
                
                if signals:
                    logger.info(f"📊 Found {len(signals)} signals")
                    
                    # Procesar las mejores señales
                    best_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5]
                    
                    for signal in best_signals:
                        await self.process_signal(signal)
                else:
                    logger.info("No signals found this scan")
                
                # Actualizar estadísticas
                await self.update_statistics()
                
                # Esperar antes del siguiente escaneo
                await asyncio.sleep(self.scan_interval)
                
            except KeyboardInterrupt:
                logger.info("⛔ Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in signal worker: {e}")
                await asyncio.sleep(60)
    
    async def process_signal(self, signal):
        """Procesar una señal"""
        try:
            # Guardar señal en base de datos
            cursor = self.system.engine.db_connection.cursor()
            cursor.execute('''
                INSERT INTO signals 
                (id, timestamp, symbol, action, philosopher, confidence,
                 entry_price, stop_loss, take_profit, reasoning, risk_reward, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (signal.id, signal.timestamp, signal.symbol, signal.action,
                  signal.philosopher, signal.confidence, signal.entry_price,
                  signal.stop_loss, signal.take_profit, 
                  json.dumps(signal.reasoning), signal.risk_reward,
                  json.dumps(signal.metadata) if signal.metadata else None))
            
            self.system.engine.db_connection.commit()
            
            # Enviar por WebSocket
            await self.broadcast_signal(signal)
            
            # Log de la señal
            logger.info(f"✅ Signal processed:")
            logger.info(f"   {signal.symbol} - {signal.philosopher}")
            logger.info(f"   Action: {signal.action} @ ${signal.entry_price:.2f}")
            logger.info(f"   Confidence: {signal.confidence}%")
            logger.info(f"   Reason: {signal.reasoning[0] if signal.reasoning else 'N/A'}")
            
            # Auto-ejecutar si la confianza es muy alta (opcional)
            if signal.confidence >= 85 and os.getenv('AUTO_TRADE', 'false').lower() == 'true':
                position = self.system.execute_signal(signal, "auto_trader")
                if position:
                    logger.info(f"🤖 Auto-trade executed: {position.id}")
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def broadcast_signal(self, signal):
        """Enviar señal por WebSocket"""
        try:
            message = {
                'type': 'signal',
                'data': {
                    'id': signal.id,
                    'timestamp': signal.timestamp.isoformat(),
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'philosopher': signal.philosopher,
                    'confidence': signal.confidence,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'reasoning': signal.reasoning,
                    'risk_reward': signal.risk_reward
                }
            }
            
            # Enviar a todos los clientes conectados
            await broadcast_signal_update(message)
            logger.debug(f"Signal broadcasted via WebSocket")
            
        except Exception as e:
            logger.error(f"Error broadcasting signal: {e}")
    
    async def update_statistics(self):
        """Actualizar y enviar estadísticas"""
        try:
            # Obtener estadísticas del día
            cursor = self.system.engine.db_connection.cursor()
            
            # Señales de hoy
            cursor.execute('''
                SELECT COUNT(*), AVG(confidence) 
                FROM signals 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            signals_today, avg_confidence = cursor.fetchone()
            
            # Trades de hoy
            cursor.execute('''
                SELECT COUNT(*), SUM(pnl) 
                FROM trade_history 
                WHERE DATE(executed_at) = DATE('now')
            ''')
            trades_today, pnl_today = cursor.fetchone()
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'mode': self.system.mode,
                'signals_today': signals_today or 0,
                'avg_confidence': avg_confidence or 0,
                'trades_today': trades_today or 0,
                'pnl_today': pnl_today or 0
            }
            
            # Enviar por WebSocket
            message = {
                'type': 'stats_update',
                'data': stats
            }
            
            await broadcast_signal_update(message)
            
            logger.info(f"📊 Stats: {signals_today} signals, {trades_today} trades, PnL: ${pnl_today or 0:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def stop(self):
        """Detener el worker"""
        self.running = False
        self.system.stop()
        logger.info("Signal Worker stopped")

async def main():
    """Función principal"""
    worker = SignalWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
        worker.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        worker.stop()

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║           📡 SIGNAL WORKER - BOTPHIA 📡                 ║
║                                                          ║
║  Generador automático de señales de trading             ║
║  • Escanea 5 criptomonedas principales                  ║
║  • Analiza con 8 estrategias filosóficas                ║
║  • Genera señales cada 30 segundos                      ║
║  • Funciona SIN API keys (modo demo)                    ║
║                                                          ║
║  Presiona Ctrl+C para detener                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())