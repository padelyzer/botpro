#!/usr/bin/env python3
"""
AUTONOMOUS PAPER TRADING BOT - BotphIA
Sistema de trading autónomo con paper trading de $200 USD
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import time

from database import DatabaseManager
from philosophers import get_trading_system
from philosophers_extended import register_extended_philosophers
from signal_pipeline import get_signal_pipeline
from enhanced_trading_config import get_enhanced_config
from audit_system import audit_system

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PaperTradingBot:
    """Bot de paper trading autónomo con $200 USD"""
    
    def __init__(self):
        self.initial_balance = 200.0  # $200 USD inicial
        self.current_balance = 200.0
        self.max_positions = 3  # Máximo 3 trades simultáneos
        self.risk_per_trade = 0.15  # 15% del balance por trade ($30 aprox)
        self.max_loss_per_trade = 0.05  # 5% stop loss máximo
        self.min_confidence = 65  # Mínimo 65% confianza para abrir posición
        
        # Inicializar componentes
        self.db = DatabaseManager()
        
        # Importar aquí para evitar importación circular
        from binance_integration import BinanceConnector
        self.connector = BinanceConnector(testnet=True)
        register_extended_philosophers()
        self.trading_system = get_trading_system()
        self.signal_pipeline = get_signal_pipeline()
        self.config = get_enhanced_config()
        
        # Estado del bot
        self.positions = {}  # Posiciones abiertas
        self.trade_history = []
        self.last_signal_check = None
        self.running = False
        
        # Métricas de rendimiento
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        
        # Símbolos a operar (menor precio para mayor cantidad)
        self.symbols = [
            'DOGEUSDT', 'ADAUSDT', 'XRPUSDT', 'DOTUSDT', 
            'LINKUSDT', 'AVAXUSDT', 'LTCUSDT', 'TRXUSDT'
        ]
        
        logger.info(f"🤖 Bot de Paper Trading inicializado con ${self.current_balance:.2f} USD")
    
    async def start(self):
        """Iniciar el bot autónomo"""
        self.running = True
        logger.info("🚀 Iniciando bot de paper trading autónomo...")
        
        # Cargar estado previo si existe
        await self.load_state()
        
        # Bucle principal del bot
        while self.running:
            try:
                # 1. Actualizar precios de posiciones abiertas
                await self.update_open_positions()
                
                # 2. Verificar stop loss y take profit
                await self.check_exit_conditions()
                
                # 3. Buscar nuevas señales si tenemos espacio
                if len(self.positions) < self.max_positions:
                    await self.search_new_signals()
                
                # 4. Guardar estado
                await self.save_state()
                
                # 5. Log de estado cada 5 minutos
                await self.log_status()
                
                # Esperar 30 segundos antes del siguiente ciclo
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error en el bucle principal del bot: {e}")
                await asyncio.sleep(60)  # Esperar más tiempo si hay error
    
    async def search_new_signals(self):
        """Buscar nuevas señales de trading"""
        logger.info("🔍 Buscando nuevas oportunidades de trading...")
        
        best_signals = []
        
        for symbol in self.symbols:
            try:
                # Obtener datos del mercado
                df = self.connector.get_historical_data(symbol, "15m", 100)
                if df is None or len(df) < 50:
                    continue
                
                current_price = df['close'].iloc[-1]
                
                # Generar análisis de filósofos
                philosophers = ['SOCRATES', 'ARISTOTELES', 'NIETZSCHE', 'CONFUCIO']
                signals = self.trading_system.analyze_with_philosophers(df, symbol, philosophers)
                if not signals:
                    continue
                
                # Evaluar cada señal
                for phil_signal in signals:
                    if phil_signal.action in ['BUY', 'SELL']:
                        confidence = phil_signal.confidence
                        
                        # Solo considerar señales de alta confianza
                        if confidence >= self.min_confidence:
                            signal = {
                                'symbol': symbol,
                                'action': phil_signal.action,
                                'confidence': confidence,
                                'entry_price': current_price,
                                'philosopher': phil_signal.philosopher,
                                'reasoning': ' + '.join(phil_signal.reasoning) if isinstance(phil_signal.reasoning, list) else str(phil_signal.reasoning),
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Validar con pipeline
                            prices = df['close'].tolist()
                            high = df['high'].tolist()
                            low = df['low'].tolist()
                            volume = df['volume'].tolist()
                            
                            evaluation = self.signal_pipeline.validate_signal(
                                signal, prices, high, low, volume
                            )
                            
                            if evaluation.is_valid and evaluation.final_score >= 55:
                                signal['validation_score'] = evaluation.final_score
                                signal['market_condition'] = evaluation.market_condition
                                best_signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error analizando {symbol}: {e}")
                continue
        
        # Ordenar por confianza y score de validación
        best_signals.sort(key=lambda x: (x['confidence'] + x.get('validation_score', 0)) / 2, reverse=True)
        
        # Abrir las mejores posiciones disponibles
        spaces_available = self.max_positions - len(self.positions)
        for signal in best_signals[:spaces_available]:
            await self.open_position(signal)
    
    async def open_position(self, signal: Dict):
        """Abrir una nueva posición de paper trading"""
        symbol = signal['symbol']
        action = signal['action']
        entry_price = signal['entry_price']
        confidence = signal['confidence']
        
        # Calcular tamaño de la posición
        trade_amount = self.current_balance * self.risk_per_trade
        quantity = trade_amount / entry_price
        
        # Calcular stop loss y take profit
        if action == 'BUY':
            stop_loss = entry_price * (1 - self.max_loss_per_trade)
            take_profit = entry_price * (1 + (self.max_loss_per_trade * 2))  # Risk:Reward 1:2
        else:  # SELL
            stop_loss = entry_price * (1 + self.max_loss_per_trade)
            take_profit = entry_price * (1 - (self.max_loss_per_trade * 2))
        
        # Crear posición
        position = {
            'id': f"{symbol}_{datetime.now().timestamp()}",
            'symbol': symbol,
            'action': action,
            'entry_price': entry_price,
            'current_price': entry_price,
            'quantity': quantity,
            'trade_amount': trade_amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'philosopher': signal['philosopher'],
            'reasoning': signal.get('reasoning', ''),
            'open_time': datetime.now(),
            'status': 'OPEN',
            'pnl': 0.0,
            'pnl_percentage': 0.0
        }
        
        # Guardar posición
        self.positions[position['id']] = position
        
        # Reducir balance disponible
        self.current_balance -= trade_amount
        
        # Log
        logger.info(f"📈 POSICIÓN ABIERTA: {symbol} {action} @ ${entry_price:.6f}")
        logger.info(f"💰 Cantidad: {quantity:.2f} | Inversión: ${trade_amount:.2f}")
        logger.info(f"🎯 TP: ${take_profit:.6f} | 🛑 SL: ${stop_loss:.6f}")
        logger.info(f"🧠 Filósofo: {signal['philosopher']} (Confianza: {confidence}%)")
        
        # Guardar en base de datos
        try:
            self.db.save_position(position)
            
            # Auditar apertura de posición
            audit_system.log_trade_event('OPEN_POSITION', {
                'symbol': symbol,
                'action': action,
                'entry_price': entry_price,
                'quantity': quantity,
                'balance_before': self.current_balance + trade_amount,
                'balance_after': self.current_balance,
                'philosopher': signal['philosopher'],
                'confidence': confidence,
                'reasoning': signal.get('reasoning', ''),
                'market_conditions': signal.get('market_condition', {}),
                'signals_data': signal,
                'position_data': position
            })
            
            # Registrar señal ejecutada
            audit_system.log_signal_evaluation(signal, executed=True)
            
        except Exception as e:
            logger.error(f"Error guardando posición en BD: {e}")
    
    async def update_open_positions(self):
        """Actualizar precios de las posiciones abiertas"""
        if not self.positions:
            return
        
        for position_id, position in list(self.positions.items()):
            try:
                symbol = position['symbol']
                
                # Obtener precio actual
                df_current = self.connector.get_historical_data(symbol, "1m", 1)
                if df_current is None or len(df_current) == 0:
                    continue
                
                current_price = float(df_current['close'].iloc[-1])
                position['current_price'] = current_price
                
                # Calcular PnL
                entry_price = position['entry_price']
                quantity = position['quantity']
                
                if position['action'] == 'BUY':
                    pnl = (current_price - entry_price) * quantity
                else:  # SELL
                    pnl = (entry_price - current_price) * quantity
                
                position['pnl'] = pnl
                position['pnl_percentage'] = (pnl / position['trade_amount']) * 100
                
            except Exception as e:
                logger.error(f"Error actualizando posición {position_id}: {e}")
    
    async def check_exit_conditions(self):
        """Verificar condiciones de cierre (stop loss / take profit)"""
        for position_id, position in list(self.positions.items()):
            try:
                current_price = position['current_price']
                stop_loss = position['stop_loss']
                take_profit = position['take_profit']
                action = position['action']
                
                should_close = False
                close_reason = ""
                
                if action == 'BUY':
                    if current_price <= stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                    elif current_price >= take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                else:  # SELL
                    if current_price >= stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                    elif current_price <= take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                
                if should_close:
                    await self.close_position(position_id, close_reason)
                
            except Exception as e:
                logger.error(f"Error verificando condiciones de salida para {position_id}: {e}")
    
    async def close_position(self, position_id: str, reason: str):
        """Cerrar una posición"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Actualizar métricas
        pnl = position['pnl']
        self.total_pnl += pnl
        self.current_balance += position['trade_amount'] + pnl  # Devolver capital + ganancia/pérdida
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        
        # Marcar como cerrada
        position['status'] = 'CLOSED'
        position['close_time'] = datetime.now()
        position['close_reason'] = reason
        
        # Log
        symbol = position['symbol']
        action = position['action']
        entry_price = position['entry_price']
        current_price = position['current_price']
        pnl_pct = position['pnl_percentage']
        
        logger.info(f"🔚 POSICIÓN CERRADA: {symbol} {action} | {reason}")
        logger.info(f"📊 Entrada: ${entry_price:.6f} → Salida: ${current_price:.6f}")
        logger.info(f"💹 PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
        logger.info(f"💰 Balance actual: ${self.current_balance:.2f} USD")
        
        # Mover a historial
        self.trade_history.append(position)
        del self.positions[position_id]
        
        # Guardar en base de datos
        try:
            self.db.close_position(position_id, pnl, pnl_pct)
            
            # Auditar cierre de posición
            audit_system.log_trade_event('CLOSE_POSITION', {
                'symbol': position['symbol'],
                'action': position['action'],
                'entry_price': position['entry_price'],
                'exit_price': position['current_price'],
                'quantity': position['quantity'],
                'pnl': pnl,
                'pnl_percentage': pnl_pct,
                'balance_before': self.current_balance - position['trade_amount'] - pnl,
                'balance_after': self.current_balance,
                'philosopher': position['philosopher'],
                'confidence': position['confidence'],
                'reasoning': position.get('reasoning', ''),
                'position_data': position,
                'metadata': {'close_reason': reason}
            })
            
        except Exception as e:
            logger.error(f"Error cerrando posición en BD: {e}")
    
    async def log_status(self):
        """Log del estado actual del bot"""
        open_positions = len(self.positions)
        win_rate = (self.winning_trades / max(self.total_trades, 1)) * 100
        losing_trades = self.total_trades - self.winning_trades
        
        # Guardar snapshot en auditoría
        audit_system.save_bot_snapshot({
            'balance': self.current_balance,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'open_positions': open_positions,
            'positions': list(self.positions.values()),
            'metadata': {
                'max_positions': self.max_positions,
                'risk_per_trade': self.risk_per_trade,
                'min_confidence': self.min_confidence
            }
        })
        
        logger.info("=" * 60)
        logger.info("📊 ESTADO DEL BOT DE PAPER TRADING")
        logger.info(f"💰 Balance: ${self.current_balance:.2f} USD")
        logger.info(f"📈 PnL Total: ${self.total_pnl:.2f} USD")
        logger.info(f"🔢 Trades Totales: {self.total_trades}")
        logger.info(f"🎯 Win Rate: {win_rate:.1f}%")
        logger.info(f"📊 Posiciones Abiertas: {open_positions}/{self.max_positions}")
        
        if self.positions:
            logger.info("📋 Posiciones Activas:")
            for pos in self.positions.values():
                pnl_str = f"+${pos['pnl']:.2f}" if pos['pnl'] >= 0 else f"-${abs(pos['pnl']):.2f}"
                logger.info(f"  • {pos['symbol']} {pos['action']} @ ${pos['entry_price']:.6f} | PnL: {pnl_str} ({pos['pnl_percentage']:.2f}%)")
        
        logger.info("=" * 60)
    
    async def save_state(self):
        """Guardar estado del bot"""
        state = {
            'current_balance': self.current_balance,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'positions': {k: {**v, 'open_time': v['open_time'].isoformat()} for k, v in self.positions.items()},
            'last_update': datetime.now().isoformat()
        }
        
        try:
            with open('bot_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")
    
    async def load_state(self):
        """Cargar estado previo del bot"""
        try:
            with open('bot_state.json', 'r') as f:
                state = json.load(f)
            
            self.current_balance = state.get('current_balance', 200.0)
            self.total_pnl = state.get('total_pnl', 0.0)
            self.total_trades = state.get('total_trades', 0)
            self.winning_trades = state.get('winning_trades', 0)
            
            # Cargar posiciones (convertir datetime strings de vuelta)
            positions = state.get('positions', {})
            for k, v in positions.items():
                v['open_time'] = datetime.fromisoformat(v['open_time'])
                self.positions[k] = v
            
            logger.info(f"📥 Estado cargado: Balance ${self.current_balance:.2f}, {len(self.positions)} posiciones activas")
            
        except FileNotFoundError:
            logger.info("📁 No se encontró estado previo, iniciando con configuración por defecto")
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
    
    def stop(self):
        """Detener el bot"""
        self.running = False
        logger.info("🛑 Deteniendo bot de paper trading...")

# Función principal para ejecutar el bot
async def main():
    bot = PaperTradingBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupción del usuario")
        bot.stop()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        bot.stop()

if __name__ == "__main__":
    asyncio.run(main())