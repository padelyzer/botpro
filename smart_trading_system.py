#!/usr/bin/env python3
"""
SMART TRADING SYSTEM - HÍBRIDO (DEMO/TESTNET/REAL)
Sistema inteligente que funciona con o sin API keys
Detecta automáticamente el modo y se adapta
"""

import os
import logging
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import asyncio
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================
# ESTRUCTURAS DE DATOS
# ===========================================

@dataclass
class TradingSignal:
    """Señal de trading unificada"""
    id: str
    timestamp: datetime
    symbol: str
    action: str  # BUY, SELL, HOLD
    philosopher: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: List[str]
    risk_reward: float
    metadata: Dict[str, Any] = None

@dataclass
class Position:
    """Posición de trading"""
    id: str
    user_id: str
    symbol: str
    side: str  # LONG, SHORT
    entry_price: float
    current_price: float
    quantity: float
    pnl: float
    pnl_percentage: float
    status: str  # OPEN, CLOSED
    opened_at: datetime
    closed_at: Optional[datetime] = None
    philosopher: str = ""
    mode: str = "DEMO"  # DEMO, TESTNET, REAL

@dataclass
class Portfolio:
    """Portfolio del usuario"""
    user_id: str
    initial_balance: float
    current_balance: float
    total_pnl: float
    total_pnl_percentage: float
    open_positions: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    mode: str  # DEMO, TESTNET, REAL

# ===========================================
# CLASE BASE: TRADING ENGINE
# ===========================================

class TradingEngine:
    """Motor base de trading"""
    
    def __init__(self, mode: str = "DEMO"):
        self.mode = mode
        self.positions = {}
        self.portfolio = None
        self.db_connection = None
        self.initialize_database()
        
    def initialize_database(self):
        """Inicializar base de datos"""
        db_path = os.getenv('DATABASE_PATH', 'trading_bot.db')
        self.db_connection = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
        
    def create_tables(self):
        """Crear tablas necesarias"""
        cursor = self.db_connection.cursor()
        
        # Tabla de portfolios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                user_id TEXT PRIMARY KEY,
                initial_balance REAL DEFAULT 220.0,
                current_balance REAL DEFAULT 220.0,
                total_pnl REAL DEFAULT 0,
                total_pnl_percentage REAL DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                mode TEXT DEFAULT 'DEMO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de posiciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                current_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_percentage REAL,
                status TEXT,
                opened_at TIMESTAMP,
                closed_at TIMESTAMP,
                philosopher TEXT,
                mode TEXT,
                FOREIGN KEY (user_id) REFERENCES portfolios (user_id)
            )
        ''')
        
        # Tabla de histórico de trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                position_id TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_percentage REAL,
                philosopher TEXT,
                reasoning TEXT,
                mode TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES portfolios (user_id)
            )
        ''')
        
        # Tabla de señales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                symbol TEXT,
                action TEXT,
                philosopher TEXT,
                confidence REAL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                reasoning TEXT,
                risk_reward REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.db_connection.commit()
    
    def get_or_create_portfolio(self, user_id: str) -> Portfolio:
        """Obtener o crear portfolio del usuario"""
        cursor = self.db_connection.cursor()
        
        # Buscar portfolio existente
        cursor.execute('SELECT * FROM portfolios WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return Portfolio(
                user_id=row[0],
                initial_balance=row[1],
                current_balance=row[2],
                total_pnl=row[3],
                total_pnl_percentage=row[4],
                open_positions=row[5],
                total_trades=row[6],
                winning_trades=row[7],
                losing_trades=row[8],
                win_rate=row[9],
                mode=row[10]
            )
        else:
            # Crear nuevo portfolio
            portfolio = Portfolio(
                user_id=user_id,
                initial_balance=220.0,
                current_balance=220.0,
                total_pnl=0,
                total_pnl_percentage=0,
                open_positions=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                mode=self.mode
            )
            
            cursor.execute('''
                INSERT INTO portfolios 
                (user_id, initial_balance, current_balance, mode)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 220.0, 220.0, self.mode))
            
            self.db_connection.commit()
            return portfolio
    
    def execute_trade(self, signal: TradingSignal, user_id: str) -> Optional[Position]:
        """Ejecutar trade (debe ser implementado por subclases)"""
        raise NotImplementedError
    
    def close_position(self, position_id: str, current_price: float) -> bool:
        """Cerrar posición"""
        raise NotImplementedError
    
    def update_portfolio(self, user_id: str, pnl: float, is_win: bool):
        """Actualizar portfolio después de un trade"""
        cursor = self.db_connection.cursor()
        
        # Obtener portfolio actual
        portfolio = self.get_or_create_portfolio(user_id)
        
        # Actualizar valores
        new_balance = portfolio.current_balance + pnl
        total_pnl = portfolio.total_pnl + pnl
        total_trades = portfolio.total_trades + 1
        winning_trades = portfolio.winning_trades + (1 if is_win else 0)
        losing_trades = portfolio.losing_trades + (0 if is_win else 1)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_percentage = (total_pnl / portfolio.initial_balance * 100)
        
        # Actualizar en base de datos
        cursor.execute('''
            UPDATE portfolios 
            SET current_balance = ?, total_pnl = ?, total_pnl_percentage = ?,
                total_trades = ?, winning_trades = ?, losing_trades = ?,
                win_rate = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_balance, total_pnl, pnl_percentage, total_trades,
              winning_trades, losing_trades, win_rate, user_id))
        
        self.db_connection.commit()
        
        logger.info(f"Portfolio updated for {user_id}: Balance ${new_balance:.2f}, PnL ${pnl:.2f}")

# ===========================================
# DEMO TRADING ENGINE (Sin API Keys)
# ===========================================

class DemoTradingEngine(TradingEngine):
    """Motor de trading demo - funciona sin API keys"""
    
    def __init__(self):
        super().__init__(mode="DEMO")
        self.simulated_balance = 220.0
        self.simulated_positions = {}
        logger.info("🎮 Demo Trading Engine initialized (No API keys required)")
    
    def get_market_price(self, symbol: str) -> float:
        """Obtener precio de mercado desde API pública"""
        try:
            # Binance API pública (no requiere autenticación)
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url)
            if response.status_code == 200:
                return float(response.json()['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
        
        # Precios fallback
        fallback_prices = {
            'BTCUSDT': 98000.0,
            'ETHUSDT': 3500.0,
            'BNBUSDT': 650.0,
            'SOLUSDT': 180.0,
            'ADAUSDT': 0.85
        }
        return fallback_prices.get(symbol, 100.0)
    
    def execute_trade(self, signal: TradingSignal, user_id: str) -> Optional[Position]:
        """Ejecutar trade simulado"""
        try:
            # Obtener portfolio
            portfolio = self.get_or_create_portfolio(user_id)
            
            # Calcular tamaño de posición (2% del balance)
            position_size = portfolio.current_balance * 0.02
            current_price = self.get_market_price(signal.symbol)
            quantity = position_size / current_price
            
            # Crear posición
            position = Position(
                id=f"DEMO_{datetime.now().timestamp()}",
                user_id=user_id,
                symbol=signal.symbol,
                side="LONG" if signal.action == "BUY" else "SHORT",
                entry_price=current_price,
                current_price=current_price,
                quantity=quantity,
                pnl=0,
                pnl_percentage=0,
                status="OPEN",
                opened_at=datetime.now(),
                philosopher=signal.philosopher,
                mode="DEMO"
            )
            
            # Guardar en base de datos
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO positions 
                (id, user_id, symbol, side, entry_price, current_price, 
                 quantity, pnl, pnl_percentage, status, opened_at, philosopher, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (position.id, user_id, position.symbol, position.side,
                  position.entry_price, position.current_price, position.quantity,
                  0, 0, "OPEN", datetime.now(), position.philosopher, "DEMO"))
            
            # Actualizar portfolio
            cursor.execute('''
                UPDATE portfolios 
                SET open_positions = open_positions + 1
                WHERE user_id = ?
            ''', (user_id,))
            
            self.db_connection.commit()
            
            logger.info(f"✅ DEMO Trade executed: {signal.symbol} {signal.action} @ ${current_price:.2f}")
            return position
            
        except Exception as e:
            logger.error(f"Error executing demo trade: {e}")
            return None
    
    def close_position(self, position_id: str, current_price: Optional[float] = None) -> bool:
        """Cerrar posición simulada"""
        try:
            cursor = self.db_connection.cursor()
            
            # Obtener posición
            cursor.execute('SELECT * FROM positions WHERE id = ? AND status = "OPEN"', 
                          (position_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
            
            # Calcular PnL
            symbol = row[2]
            side = row[3]
            entry_price = row[4]
            quantity = row[6]
            user_id = row[1]
            
            if not current_price:
                current_price = self.get_market_price(symbol)
            
            if side == "LONG":
                pnl = (current_price - entry_price) * quantity
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl = (entry_price - current_price) * quantity
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
            
            # Actualizar posición
            cursor.execute('''
                UPDATE positions 
                SET current_price = ?, pnl = ?, pnl_percentage = ?,
                    status = "CLOSED", closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (current_price, pnl, pnl_percentage, position_id))
            
            # Guardar en histórico
            cursor.execute('''
                INSERT INTO trade_history 
                (user_id, position_id, symbol, side, entry_price, exit_price,
                 quantity, pnl, pnl_percentage, philosopher, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, position_id, symbol, side, entry_price, current_price,
                  quantity, pnl, pnl_percentage, row[12], "DEMO"))
            
            # Actualizar portfolio
            self.update_portfolio(user_id, pnl, pnl > 0)
            
            cursor.execute('''
                UPDATE portfolios 
                SET open_positions = open_positions - 1
                WHERE user_id = ?
            ''', (user_id,))
            
            self.db_connection.commit()
            
            logger.info(f"✅ Position closed: {symbol} PnL: ${pnl:.2f} ({pnl_percentage:.2f}%)")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

# ===========================================
# REAL TRADING ENGINE (Con API Keys)
# ===========================================

class RealTradingEngine(TradingEngine):
    """Motor de trading real - requiere API keys"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        super().__init__(mode="TESTNET" if testnet else "REAL")
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.max_capital = 220.0  # Límite de capital
        
        # Aquí conectarías con Binance real
        # self.client = BinanceClient(api_key, api_secret, testnet)
        
        logger.info(f"💰 Real Trading Engine initialized - Mode: {self.mode}")
    
    def execute_trade(self, signal: TradingSignal, user_id: str) -> Optional[Position]:
        """Ejecutar trade real en Binance"""
        # Implementación real con Binance API
        # Por ahora retorna demo
        logger.info(f"Real trade would be executed here: {signal.symbol}")
        return None
    
    def close_position(self, position_id: str, current_price: float) -> bool:
        """Cerrar posición real en Binance"""
        # Implementación real con Binance API
        logger.info(f"Real position would be closed here: {position_id}")
        return False

# ===========================================
# SMART TRADING SYSTEM (Sistema Principal)
# ===========================================

class SmartTradingSystem:
    """Sistema de trading inteligente que detecta el modo automáticamente"""
    
    def __init__(self):
        self.mode = self._detect_mode()
        self.engine = self._initialize_engine()
        self.signal_generator = SignalGenerator()
        self.is_running = False
        
        logger.info(f"🚀 Smart Trading System initialized in {self.mode} mode")
    
    def _detect_mode(self) -> str:
        """Detectar modo de trading según configuración"""
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_SECRET_KEY', '')
        
        if not api_key or not api_secret or api_key == 'demo':
            return 'DEMO'
        
        trading_mode = os.getenv('TRADING_MODE', 'testnet').lower()
        if trading_mode == 'live':
            return 'REAL'
        else:
            return 'TESTNET'
    
    def _initialize_engine(self) -> TradingEngine:
        """Inicializar motor según el modo"""
        if self.mode == 'DEMO':
            return DemoTradingEngine()
        else:
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_SECRET_KEY')
            testnet = self.mode == 'TESTNET'
            return RealTradingEngine(api_key, api_secret, testnet)
    
    def get_status(self) -> Dict:
        """Obtener estado del sistema"""
        return {
            'running': self.is_running,
            'mode': self.mode,
            'engine': type(self.engine).__name__,
            'can_trade': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def start(self):
        """Iniciar sistema de trading"""
        self.is_running = True
        logger.info(f"System started in {self.mode} mode")
    
    def stop(self):
        """Detener sistema de trading"""
        self.is_running = False
        logger.info("System stopped")
    
    def execute_signal(self, signal: TradingSignal, user_id: str = "default") -> Optional[Position]:
        """Ejecutar señal de trading"""
        if not self.is_running:
            logger.warning("System is not running")
            return None
        
        return self.engine.execute_trade(signal, user_id)
    
    def get_portfolio(self, user_id: str = "default") -> Portfolio:
        """Obtener portfolio del usuario"""
        return self.engine.get_or_create_portfolio(user_id)
    
    def get_positions(self, user_id: str = "default", status: str = "OPEN") -> List[Position]:
        """Obtener posiciones del usuario"""
        cursor = self.engine.db_connection.cursor()
        cursor.execute('''
            SELECT * FROM positions 
            WHERE user_id = ? AND status = ?
            ORDER BY opened_at DESC
        ''', (user_id, status))
        
        positions = []
        for row in cursor.fetchall():
            positions.append(Position(
                id=row[0],
                user_id=row[1],
                symbol=row[2],
                side=row[3],
                entry_price=row[4],
                current_price=row[5],
                quantity=row[6],
                pnl=row[7],
                pnl_percentage=row[8],
                status=row[9],
                opened_at=row[10],
                closed_at=row[11],
                philosopher=row[12],
                mode=row[13]
            ))
        
        return positions
    
    def get_trade_history(self, user_id: str = "default", limit: int = 100) -> List[Dict]:
        """Obtener histórico de trades"""
        cursor = self.engine.db_connection.cursor()
        cursor.execute('''
            SELECT * FROM trade_history 
            WHERE user_id = ?
            ORDER BY executed_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'symbol': row[3],
                'side': row[4],
                'entry_price': row[5],
                'exit_price': row[6],
                'quantity': row[7],
                'pnl': row[8],
                'pnl_percentage': row[9],
                'philosopher': row[10],
                'mode': row[12],
                'executed_at': row[13]
            })
        
        return history

# ===========================================
# GENERADOR DE SEÑALES
# ===========================================

class SignalGenerator:
    """Generador de señales de trading"""
    
    def __init__(self):
        self.philosophers = [
            'SOCRATES', 'ARISTOTELES', 'NIETZSCHE', 'CONFUCIO',
            'PLATON', 'KANT', 'DESCARTES', 'SUNTZU'
        ]
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
    
    def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Obtener datos de mercado desde API pública"""
        try:
            # Binance API pública para klines
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': '15m',
                'limit': 100
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                    'taker_buy_quote_volume', 'ignore'
                ])
                
                # Convertir a numérico
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col])
                
                # Calcular indicadores
                df['sma_20'] = df['close'].rolling(window=20).mean()
                df['sma_50'] = df['close'].rolling(window=50).mean()
                df['rsi'] = self.calculate_rsi(df['close'])
                
                return df
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signal(self, symbol: str, philosopher: str) -> Optional[TradingSignal]:
        """Generar señal según el filósofo"""
        df = self.get_market_data(symbol)
        if df is None or len(df) < 50:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0
        reasoning = []
        
        # Lógica según filósofo
        if philosopher == 'SOCRATES':
            # Cuestiona los extremos
            if current['rsi'] < 30:
                signal = 'BUY'
                confidence = 75
                reasoning.append("RSI indica sobreventa extrema")
            elif current['rsi'] > 70:
                signal = 'SELL'
                confidence = 75
                reasoning.append("RSI indica sobrecompra extrema")
        
        elif philosopher == 'ARISTOTELES':
            # Lógica de tendencias
            if current['sma_20'] > current['sma_50'] and prev['sma_20'] <= prev['sma_50']:
                signal = 'BUY'
                confidence = 80
                reasoning.append("Cruce alcista de medias móviles")
            elif current['sma_20'] < current['sma_50'] and prev['sma_20'] >= prev['sma_50']:
                signal = 'SELL'
                confidence = 80
                reasoning.append("Cruce bajista de medias móviles")
        
        elif philosopher == 'NIETZSCHE':
            # Contrarian extremo
            if current['rsi'] < 25:
                signal = 'BUY'
                confidence = 85
                reasoning.append("Pánico extremo del mercado - oportunidad contrarian")
            elif current['rsi'] > 75:
                signal = 'SELL'
                confidence = 85
                reasoning.append("Euforia extrema del mercado - momento de vender")
        
        # Más filósofos...
        
        if signal and confidence >= 70:
            return TradingSignal(
                id=f"{symbol}_{philosopher}_{datetime.now().timestamp()}",
                timestamp=datetime.now(),
                symbol=symbol,
                action=signal,
                philosopher=philosopher,
                confidence=confidence,
                entry_price=float(current['close']),
                stop_loss=float(current['close'] * 0.98 if signal == 'BUY' else current['close'] * 1.02),
                take_profit=float(current['close'] * 1.03 if signal == 'BUY' else current['close'] * 0.97),
                reasoning=reasoning,
                risk_reward=1.5,
                metadata={'rsi': float(current['rsi']), 'volume': float(current['volume'])}
            )
        
        return None
    
    async def scan_markets(self) -> List[TradingSignal]:
        """Escanear mercados en busca de señales"""
        signals = []
        
        for symbol in self.symbols:
            for philosopher in self.philosophers:
                signal = self.generate_signal(symbol, philosopher)
                if signal:
                    signals.append(signal)
                    logger.info(f"📡 Signal: {symbol} - {philosopher} - {signal.action} ({signal.confidence}%)")
        
        return signals

# ===========================================
# FUNCIÓN PRINCIPAL
# ===========================================

async def run_signal_scanner(system: SmartTradingSystem):
    """Ejecutar escáner de señales continuamente"""
    signal_generator = SignalGenerator()
    
    while system.is_running:
        try:
            # Escanear mercados
            signals = await signal_generator.scan_markets()
            
            # Ejecutar las mejores señales
            for signal in signals[:3]:  # Máximo 3 señales
                if signal.confidence >= 75:
                    position = system.execute_signal(signal, "default")
                    if position:
                        logger.info(f"✅ Trade executed: {position.symbol} @ ${position.entry_price:.2f}")
            
            # Esperar 30 segundos
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in signal scanner: {e}")
            await asyncio.sleep(60)

# ===========================================
# SISTEMA GLOBAL
# ===========================================

# Crear instancia global del sistema
smart_trading_system = SmartTradingSystem()

def get_trading_system() -> SmartTradingSystem:
    """Obtener instancia del sistema de trading"""
    return smart_trading_system

if __name__ == "__main__":
    # Prueba del sistema
    system = get_trading_system()
    print(f"Sistema iniciado en modo: {system.mode}")
    print(f"Estado: {system.get_status()}")
    
    # Probar portfolio
    portfolio = system.get_portfolio("test_user")
    print(f"Portfolio: Balance ${portfolio.current_balance:.2f}")
    
    # Iniciar escáner (comentado para no ejecutar)
    # asyncio.run(run_signal_scanner(system))