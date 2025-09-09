#!/usr/bin/env python3
"""
BOTPHIA PAPER TRADING - MODO DEMO
Sistema de paper trading automático sin necesidad de API keys reales
Usa datos públicos de Binance para simular trading
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ccxt
from typing import Dict, List, Optional
import time
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DemoPaperTradingBot:
    """Bot de paper trading que funciona con datos públicos"""
    
    def __init__(self):
        self.initial_balance = 200.0  # $200 USD inicial
        self.current_balance = 200.0
        self.positions = {}  # Posiciones abiertas
        self.trade_history = []
        self.max_positions = 3
        self.risk_per_trade = 0.15  # 15% del balance por trade
        self.min_confidence = 65  # Mínimo 65% confianza
        
        # Símbolos a operar
        self.symbols = [
            'DOGE/USDT', 'ADA/USDT', 'XRP/USDT', 'DOT/USDT',
            'LINK/USDT', 'AVAX/USDT', 'LTC/USDT', 'TRX/USDT'
        ]
        
        # Exchange público (sin API keys)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # Métricas
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.start_time = datetime.now()
        
        # Estado del bot
        self.running = False
        
        # Base de datos
        self.init_database()
        
        logger.info(f"🤖 Bot Demo inicializado con ${self.current_balance:.2f} USD")
    
    def init_database(self):
        """Inicializar base de datos para guardar trades"""
        self.conn = sqlite3.connect('paper_trading_demo.db')
        self.cursor = self.conn.cursor()
        
        # Crear tabla de trades si no existe
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                action TEXT,
                price REAL,
                amount REAL,
                value REAL,
                balance_after REAL,
                pnl REAL,
                strategy TEXT,
                confidence REAL
            )
        ''')
        
        # Crear tabla de estado
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_state (
                id INTEGER PRIMARY KEY,
                balance REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                total_pnl REAL,
                last_update TEXT
            )
        ''')
        
        self.conn.commit()
        self.load_state()
    
    def load_state(self):
        """Cargar estado previo del bot"""
        self.cursor.execute('SELECT * FROM bot_state WHERE id = 1')
        state = self.cursor.fetchone()
        
        if state:
            self.current_balance = state[1]
            self.total_trades = state[2]
            self.winning_trades = state[3]
            self.total_pnl = state[4]
            logger.info(f"📂 Estado cargado: Balance ${self.current_balance:.2f}, PnL total: ${self.total_pnl:.2f}")
    
    def save_state(self):
        """Guardar estado actual del bot"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO bot_state (id, balance, total_trades, winning_trades, total_pnl, last_update)
            VALUES (1, ?, ?, ?, ?, ?)
        ''', (self.current_balance, self.total_trades, self.winning_trades, 
              self.total_pnl, datetime.now().isoformat()))
        self.conn.commit()
    
    def save_trade(self, trade_data):
        """Guardar trade en la base de datos"""
        self.cursor.execute('''
            INSERT INTO trades (timestamp, symbol, action, price, amount, value, 
                              balance_after, pnl, strategy, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', trade_data)
        self.conn.commit()
    
    async def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Obtener datos de mercado públicos"""
        try:
            # Obtener últimas 100 velas de 15 minutos
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=100)
            
            if not ohlcv:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calcular indicadores básicos
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """Generar señal de trading basada en indicadores"""
        if df is None or len(df) < 50:
            return None
        
        current_price = df['close'].iloc[-1]
        sma_20 = df['sma_20'].iloc[-1]
        sma_50 = df['sma_50'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        
        # Estrategia simple de cruce de medias + RSI
        signal = None
        confidence = 0
        reasoning = []
        
        # Señal de compra
        if sma_20 > sma_50 and rsi < 70 and current_price > sma_20:
            signal = 'BUY'
            confidence = 70
            
            if rsi < 30:  # Sobreventa
                confidence += 15
                reasoning.append("RSI en sobreventa")
            elif rsi < 50:
                confidence += 10
                reasoning.append("RSI favorable")
            
            if (current_price - sma_20) / sma_20 < 0.02:  # Cerca de la media
                confidence += 10
                reasoning.append("Precio cerca de SMA20")
            
            reasoning.append(f"Cruce alcista de medias")
            
        # Señal de venta
        elif sma_20 < sma_50 and rsi > 30 and current_price < sma_20:
            signal = 'SELL'
            confidence = 70
            
            if rsi > 70:  # Sobrecompra
                confidence += 15
                reasoning.append("RSI en sobrecompra")
            elif rsi > 50:
                confidence += 10
                reasoning.append("RSI desfavorable")
            
            reasoning.append(f"Cruce bajista de medias")
        
        if signal and confidence >= self.min_confidence:
            return {
                'symbol': symbol,
                'action': signal,
                'price': current_price,
                'confidence': confidence,
                'reasoning': ' | '.join(reasoning),
                'timestamp': datetime.now().isoformat(),
                'rsi': rsi,
                'sma_20': sma_20,
                'sma_50': sma_50
            }
        
        return None
    
    async def execute_trade(self, signal: Dict):
        """Ejecutar trade en papel"""
        symbol = signal['symbol']
        action = signal['action']
        current_price = signal['price']
        
        # Calcular tamaño de posición
        position_value = self.current_balance * self.risk_per_trade
        amount = position_value / current_price
        
        if action == 'BUY' and symbol not in self.positions:
            # Abrir posición larga
            self.positions[symbol] = {
                'entry_price': current_price,
                'amount': amount,
                'value': position_value,
                'stop_loss': current_price * 0.95,  # 5% stop loss
                'take_profit': current_price * 1.10,  # 10% take profit
                'entry_time': datetime.now(),
                'confidence': signal['confidence'],
                'reasoning': signal['reasoning']
            }
            
            self.current_balance -= position_value
            self.total_trades += 1
            
            # Guardar trade
            trade_data = (
                datetime.now().isoformat(),
                symbol,
                'BUY',
                current_price,
                amount,
                position_value,
                self.current_balance,
                0,
                'Demo Strategy',
                signal['confidence']
            )
            self.save_trade(trade_data)
            
            logger.info(f"✅ COMPRA: {symbol} @ ${current_price:.4f}")
            logger.info(f"   Cantidad: {amount:.4f} | Valor: ${position_value:.2f}")
            logger.info(f"   Razón: {signal['reasoning']}")
            logger.info(f"   Balance restante: ${self.current_balance:.2f}")
    
    async def check_positions(self):
        """Verificar y cerrar posiciones si es necesario"""
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            try:
                # Obtener precio actual
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Calcular PnL
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                pnl_value = position['value'] * pnl_pct
                
                # Verificar condiciones de salida
                should_close = False
                reason = ""
                
                if current_price <= position['stop_loss']:
                    should_close = True
                    reason = "Stop Loss"
                elif current_price >= position['take_profit']:
                    should_close = True
                    reason = "Take Profit"
                elif pnl_pct < -0.05:  # Pérdida mayor al 5%
                    should_close = True
                    reason = "Max Loss"
                elif pnl_pct > 0.10:  # Ganancia mayor al 10%
                    should_close = True
                    reason = "Target Profit"
                
                # Tiempo en posición (cerrar después de 24 horas)
                time_in_position = datetime.now() - position['entry_time']
                if time_in_position.total_seconds() > 86400:  # 24 horas
                    should_close = True
                    reason = "Time Limit"
                
                if should_close:
                    positions_to_close.append(symbol)
                    
                    # Actualizar balance
                    final_value = position['value'] + pnl_value
                    self.current_balance += final_value
                    self.total_pnl += pnl_value
                    
                    if pnl_value > 0:
                        self.winning_trades += 1
                    
                    # Guardar trade de cierre
                    trade_data = (
                        datetime.now().isoformat(),
                        symbol,
                        'CLOSE',
                        current_price,
                        position['amount'],
                        final_value,
                        self.current_balance,
                        pnl_value,
                        reason,
                        0
                    )
                    self.save_trade(trade_data)
                    
                    logger.info(f"💰 CIERRE: {symbol} @ ${current_price:.4f}")
                    logger.info(f"   PnL: ${pnl_value:.2f} ({pnl_pct*100:.2f}%)")
                    logger.info(f"   Razón: {reason}")
                    logger.info(f"   Balance actual: ${self.current_balance:.2f}")
                    
            except Exception as e:
                logger.error(f"Error verificando posición {symbol}: {e}")
        
        # Eliminar posiciones cerradas
        for symbol in positions_to_close:
            del self.positions[symbol]
    
    async def run(self):
        """Bucle principal del bot"""
        self.running = True
        logger.info("🚀 Iniciando Bot de Paper Trading Demo...")
        logger.info(f"💼 Balance inicial: ${self.current_balance:.2f}")
        logger.info(f"📊 Símbolos a operar: {', '.join(self.symbols)}")
        
        cycle = 0
        while self.running:
            try:
                cycle += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"📍 Ciclo #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"💰 Balance: ${self.current_balance:.2f} | PnL Total: ${self.total_pnl:.2f}")
                logger.info(f"📈 Posiciones abiertas: {len(self.positions)}/{self.max_positions}")
                
                # Verificar posiciones existentes
                if self.positions:
                    await self.check_positions()
                
                # Buscar nuevas señales si hay espacio
                if len(self.positions) < self.max_positions:
                    logger.info("🔍 Buscando oportunidades...")
                    
                    for symbol in self.symbols:
                        if symbol in self.positions:
                            continue
                        
                        # Obtener datos y generar señal
                        df = await self.get_market_data(symbol)
                        if df is not None:
                            signal = self.generate_signal(df, symbol)
                            
                            if signal:
                                logger.info(f"📡 Señal detectada para {symbol}:")
                                logger.info(f"   Acción: {signal['action']} | Confianza: {signal['confidence']}%")
                                
                                if len(self.positions) < self.max_positions:
                                    await self.execute_trade(signal)
                                    await asyncio.sleep(1)  # Pequeña pausa entre trades
                        
                        await asyncio.sleep(2)  # Rate limiting
                
                # Guardar estado
                self.save_state()
                
                # Mostrar estadísticas
                if self.total_trades > 0:
                    win_rate = (self.winning_trades / self.total_trades) * 100
                    logger.info(f"\n📊 Estadísticas:")
                    logger.info(f"   Total trades: {self.total_trades}")
                    logger.info(f"   Win rate: {win_rate:.1f}%")
                    logger.info(f"   ROI: {((self.current_balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
                
                # Esperar antes del siguiente ciclo
                logger.info(f"\n⏳ Esperando 60 segundos hasta el próximo ciclo...")
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Bot detenido por el usuario")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Error en el bucle principal: {e}")
                await asyncio.sleep(30)
    
    def stop(self):
        """Detener el bot"""
        self.running = False
        self.save_state()
        self.conn.close()
        logger.info("🛑 Bot detenido correctamente")

async def main():
    """Función principal"""
    bot = DemoPaperTradingBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Cerrando bot...")
        bot.stop()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        bot.stop()

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║           🤖 BOTPHIA PAPER TRADING - MODO DEMO 🤖        ║
║                                                          ║
║  Sistema de trading automático con $200 USD simulados   ║
║  NO requiere API keys - Usa datos públicos de Binance   ║
║                                                          ║
║  Presiona Ctrl+C para detener el bot                    ║
╔══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())