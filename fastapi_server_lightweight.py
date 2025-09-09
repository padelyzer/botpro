#!/usr/bin/env python3
"""
FASTAPI SERVER LIGHTWEIGHT - Versión Optimizada para Producción
Reduce el uso de memoria manteniendo toda la funcionalidad
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import os
import random
import httpx
import asyncio

# Configurar logging minimalista
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ===========================================
# MODELOS DE DATOS (Simplificados)
# ===========================================

class LoginRequest(BaseModel):
    email: str
    password: str

class SignalResponse(BaseModel):
    id: str
    timestamp: str
    symbol: str
    action: str
    philosopher: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: List[str]
    timeframe: Optional[str] = "SWING"
    duration: Optional[str] = "1-3 días"

class PositionResponse(BaseModel):
    id: str
    symbol: str
    side: str
    entry_price: float
    current_price: float
    quantity: float
    pnl: float
    pnl_percentage: float
    status: str
    philosopher: str

class PortfolioResponse(BaseModel):
    balance: float
    initial_balance: float
    total_pnl: float
    total_pnl_percentage: float
    open_positions: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    mode: str

# ===========================================
# SISTEMA DE TRADING MINIMALISTA
# ===========================================

class LightweightTradingSystem:
    """Sistema de trading optimizado para bajo consumo de memoria"""
    
    def __init__(self):
        self.mode = "DEMO"
        self.is_running = False
        # Use local path for database
        self.db_path = os.getenv('DATABASE_PATH', '/Users/ja/saby/trading_api/trading_bot.db')
        self.price_cache = {}  # Cache de precios reales
        self.cache_timestamp = None
        self.init_database()
        
    def init_database(self):
        """Inicializar base de datos"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            
            # Crear tablas mínimas necesarias
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS signals (
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
                    risk_reward REAL,
                    timeframe TEXT,
                    duration TEXT,
                    metadata TEXT
                )
            ''')
            
            self.conn.execute('''
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
                    philosopher TEXT,
                    opened_at TEXT,
                    closed_at TEXT
                )
            ''')
            
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS portfolios (
                    user_id TEXT PRIMARY KEY,
                    balance REAL,
                    initial_balance REAL,
                    total_pnl REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER
                )
            ''')
            
            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database init error: {e}")
            # Usar base de datos en memoria si falla
            self.conn = sqlite3.connect(':memory:', check_same_thread=False)
            
    def start(self):
        self.is_running = True
        logger.info("Trading system started")
        
    def stop(self):
        self.is_running = False
        logger.info("Trading system stopped")
        
    def get_status(self):
        return {
            'running': self.is_running,
            'mode': self.mode,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_portfolio(self, user_id: str) -> Dict:
        """Obtener portfolio del usuario"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM portfolios WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'current_balance': row[1],
                    'initial_balance': row[2],
                    'total_pnl': row[3],
                    'total_pnl_percentage': (row[3] / row[2] * 100) if row[2] > 0 else 0,
                    'open_positions': 0,
                    'total_trades': row[4],
                    'winning_trades': row[5],
                    'losing_trades': row[6],
                    'win_rate': (row[5] / row[4] * 100) if row[4] > 0 else 0,
                    'mode': self.mode
                }
            else:
                # Portfolio por defecto
                return {
                    'current_balance': 10000,
                    'initial_balance': 10000,
                    'total_pnl': 0,
                    'total_pnl_percentage': 0,
                    'open_positions': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'mode': self.mode
                }
        except Exception as e:
            logger.error(f"Get portfolio error: {e}")
            return {
                'current_balance': 10000,
                'initial_balance': 10000,
                'total_pnl': 0,
                'total_pnl_percentage': 0,
                'open_positions': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'mode': self.mode
            }
    
    def get_positions(self, user_id: str, status: str = "OPEN") -> List[Dict]:
        """Obtener posiciones"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM positions WHERE user_id = ? AND status = ?', (user_id, status))
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'id': row[0],
                    'symbol': row[2],
                    'side': row[3],
                    'entry_price': row[4],
                    'current_price': row[5],
                    'quantity': row[6],
                    'pnl': row[7],
                    'pnl_percentage': row[8],
                    'status': row[9],
                    'philosopher': row[10]
                })
            return positions
        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return []
    
    async def get_real_prices(self) -> Dict[str, float]:
        """Obtener precios reales de Binance API pública"""
        # Cache de 30 segundos para evitar demasiadas llamadas
        if self.cache_timestamp and (datetime.now() - self.cache_timestamp).seconds < 30:
            return self.price_cache
            
        try:
            # Add proper headers to avoid Binance rate limiting
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://api.binance.com/api/v3/ticker/price',
                    headers=headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    prices = response.json()
                    self.price_cache = {item['symbol']: float(item['price']) for item in prices}
                    self.cache_timestamp = datetime.now()
                    logger.info(f"Updated prices: BTC=${self.price_cache.get('BTCUSDT', 0):.2f}")
                    return self.price_cache
        except Exception as e:
            logger.error(f"Error getting real prices: {e}")
            
        # Precios por defecto actualizados Dic 2024 (reales)
        self.price_cache = {
            'BTCUSDT': 115250.0,
            'ETHUSDT': 4790.0,
            'BNBUSDT': 883.0,
            'SOLUSDT': 204.0,
            'ADAUSDT': 0.92,
            'XRPUSDT': 3.05,
            'DOGEUSDT': 0.24
        }
        self.cache_timestamp = datetime.now()
        logger.warning("Using default prices - Binance API unavailable")
        return self.price_cache
    
    def clean_old_signals(self):
        """Limpiar señales con precios incorrectos"""
        try:
            cursor = self.conn.cursor()
            # Eliminar señales con precios irreales (actualizado Dic 2024)
            cursor.execute('''
                DELETE FROM signals 
                WHERE (symbol = 'BTCUSDT' AND (entry_price < 100000 OR entry_price > 130000)) 
                   OR (symbol = 'ETHUSDT' AND (entry_price < 4000 OR entry_price > 6000))
                   OR (symbol = 'BNBUSDT' AND (entry_price < 700 OR entry_price > 1200))
                   OR (symbol = 'SOLUSDT' AND (entry_price < 150 OR entry_price > 300))
                   OR (symbol = 'ADAUSDT' AND (entry_price < 0.5 OR entry_price > 2.0))
                   OR (symbol = 'XRPUSDT' AND (entry_price < 2.0 OR entry_price > 5.0))
                   OR (symbol = 'DOGEUSDT' AND (entry_price < 0.15 OR entry_price > 0.5))
                   OR (symbol = 'BTCUSDT' AND entry_price = 65000)
                   OR (symbol = 'SOLUSDT' AND entry_price > 500)
                   OR (symbol = 'BNBUSDT' AND entry_price > 1500)
            ''')
            deleted = cursor.rowcount
            self.conn.commit()
            logger.info(f"Cleaned {deleted} signals with incorrect prices")
            return deleted
        except Exception as e:
            logger.error(f"Error cleaning signals: {e}")
            return 0
    
    def generate_demo_signal(self) -> Dict:
        """Generar señal demo con precios reales y temporalidad"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]
        philosophers = ["Socrates", "Aristoteles", "Nietzsche", "Confucio", "Platon", "Kant", "Descartes", "Sun Tzu"]
        actions = ["BUY", "SELL", "HOLD"]
        
        symbol = random.choice(symbols)
        
        # SIEMPRE usar precios reales correctos - Dic 2024
        default_prices = {
            'BTCUSDT': 115250.0,
            'ETHUSDT': 4790.0,
            'BNBUSDT': 883.0,
            'SOLUSDT': 204.0,
            'ADAUSDT': 0.92,  # CORREGIDO: era 1.30, ahora 0.92
            'XRPUSDT': 3.05,
            'DOGEUSDT': 0.24
        }
        
        # Primero intentar del cache, si no hay usar default CORRECTO
        price = self.price_cache.get(symbol, default_prices.get(symbol))
        
        # Validación adicional: si el precio es incorrecto, usar default
        if symbol == 'SOLUSDT' and price > 500:
            price = default_prices['SOLUSDT']
        elif symbol == 'BNBUSDT' and price > 1500:
            price = default_prices['BNBUSDT']
        elif symbol == 'ADAUSDT' and price > 10:
            price = default_prices['ADAUSDT']
        
        # Determinar temporalidad y ajustar TP/SL según el timeframe
        timeframe_options = [
            {"type": "SCALPING", "duration": "5-30 min", "tp_mult": 1.005, "sl_mult": 0.997, "weight": 25},
            {"type": "INTRADAY", "duration": "1-4 horas", "tp_mult": 1.015, "sl_mult": 0.99, "weight": 35},
            {"type": "SWING", "duration": "1-3 días", "tp_mult": 1.03, "sl_mult": 0.98, "weight": 30},
            {"type": "POSITION", "duration": "3+ días", "tp_mult": 1.05, "sl_mult": 0.96, "weight": 10}
        ]
        
        # Selección ponderada de timeframe
        weights = [opt["weight"] for opt in timeframe_options]
        timeframe = random.choices(timeframe_options, weights=weights)[0]
        
        action = random.choice(actions)
        
        # Calcular TP y SL basados en el tipo de acción y timeframe
        if action == "BUY":
            stop_loss = price * timeframe["sl_mult"]
            take_profit = price * timeframe["tp_mult"]
        elif action == "SELL":
            # Para shorts, invertir la lógica
            stop_loss = price * (2 - timeframe["sl_mult"])
            take_profit = price * (2 - timeframe["tp_mult"])
        else:  # HOLD
            stop_loss = price * timeframe["sl_mult"]
            take_profit = price * ((timeframe["tp_mult"] - 1) * 0.6 + 1)  # TP más conservador para HOLD
        
        # Generar reasoning basado en timeframe
        reasoning_map = {
            "SCALPING": f"Movimiento rápido detectado en {symbol}. Entrada y salida en minutos.",
            "INTRADAY": f"Oportunidad intradía en {symbol}. Cerrar posición antes del cierre.",
            "SWING": f"Tendencia de corto plazo en {symbol}. Mantener 1-3 días.",
            "POSITION": f"Cambio estructural en {symbol}. Posición de mediano plazo."
        }
        
        philosopher = random.choice(philosophers)
        
        signal = {
            'id': f"{symbol}_{datetime.now().timestamp()}",
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'philosopher': philosopher,
            'confidence': random.uniform(60, 95),
            'entry_price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timeframe': timeframe["type"],
            'duration': timeframe["duration"],
            'reasoning': [
                f"{philosopher} detecta oportunidad en {symbol}",
                reasoning_map[timeframe["type"]]
            ],
            'risk_reward': abs((take_profit - price) / (price - stop_loss)) if price != stop_loss else 1.5
        }
        
        # Guardar en base de datos
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO signals 
                (id, timestamp, symbol, action, philosopher, confidence,
                 entry_price, stop_loss, take_profit, reasoning, risk_reward,
                 timeframe, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (signal['id'], signal['timestamp'], signal['symbol'], 
                  signal['action'], signal['philosopher'], signal['confidence'],
                  signal['entry_price'], signal['stop_loss'], signal['take_profit'],
                  json.dumps(signal['reasoning']), signal['risk_reward'],
                  signal['timeframe'], signal['duration']))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Save signal error: {e}")
        
        return signal

# Singleton del sistema
trading_system = LightweightTradingSystem()

# ===========================================
# LIFESPAN MANAGER
# ===========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Lightweight FastAPI server...")
    trading_system.start()
    
    # Limpiar señales con precios incorrectos
    deleted = trading_system.clean_old_signals()
    logger.info(f"🧹 Cleaned {deleted} old signals with incorrect prices")
    
    # Cargar precios reales al inicio
    await trading_system.get_real_prices()
    logger.info(f"📊 Loaded {len(trading_system.price_cache)} real prices from Binance")
    
    # Generar señales iniciales con precios reales
    for _ in range(10):  # Más señales para llenar la UI
        trading_system.generate_demo_signal()
    
    # Task para actualizar precios y generar señales
    async def update_task():
        while trading_system.is_running:
            await asyncio.sleep(30)
            await trading_system.get_real_prices()
            # Limpiar señales viejas periódicamente
            trading_system.clean_old_signals()
            # Generar nuevas señales con precios actualizados
            for _ in range(3):
                trading_system.generate_demo_signal()
    
    # Iniciar task en background
    asyncio.create_task(update_task())
    
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")
    trading_system.stop()

# ===========================================
# APLICACIÓN FASTAPI
# ===========================================

app = FastAPI(
    title="BotPhia Trading API Lightweight",
    description="Sistema de trading optimizado para bajo consumo de memoria",
    version="2.0.1",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# DEPENDENCIAS
# ===========================================

async def get_current_user_optional(authorization: str = Header(None)):
    """Obtener usuario actual (opcional)"""
    if not authorization or not authorization.startswith('Bearer '):
        return None
    return {'user_id': 'default', 'email': 'demo@botphia.com'}

async def get_current_user_required(authorization: str = Header(None)):
    """Obtener usuario actual (requerido)"""
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return user

# ===========================================
# ENDPOINTS
# ===========================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login de usuario"""
    return {
        'success': True,
        'message': 'Login exitoso',
        'user': {
            'id': 'default_user',
            'email': request.email,
            'name': request.email.split('@')[0],
            'role': 'trader'
        },
        'token': 'demo_token_' + datetime.now().strftime('%Y%m%d%H%M%S')
    }

@app.get("/api/status")
async def get_status():
    """Obtener estado del sistema"""
    return {
        'status': 'online',
        'mode': trading_system.mode,
        'running': trading_system.is_running,
        'timestamp': datetime.now().isoformat(),
        'memory_optimized': True
    }

@app.get("/api/bot/status")
async def get_bot_status(user=Depends(get_current_user_optional)):
    """Obtener estado del bot"""
    return trading_system.get_status()

@app.post("/api/bot/start")
async def start_bot(user=Depends(get_current_user_required)):
    """Iniciar bot de trading"""
    trading_system.start()
    return {'success': True, 'message': 'Bot iniciado'}

@app.post("/api/bot/stop")
async def stop_bot(user=Depends(get_current_user_required)):
    """Detener bot de trading"""
    trading_system.stop()
    return {'success': True, 'message': 'Bot detenido'}

@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio(user=Depends(get_current_user_optional)):
    """Obtener portfolio del usuario"""
    user_id = user['user_id'] if user else 'default'
    portfolio = trading_system.get_portfolio(user_id)
    
    return PortfolioResponse(
        balance=portfolio['current_balance'],
        initial_balance=portfolio['initial_balance'],
        total_pnl=portfolio['total_pnl'],
        total_pnl_percentage=portfolio['total_pnl_percentage'],
        open_positions=portfolio['open_positions'],
        total_trades=portfolio['total_trades'],
        winning_trades=portfolio['winning_trades'],
        losing_trades=portfolio['losing_trades'],
        win_rate=portfolio['win_rate'],
        mode=portfolio['mode']
    )

@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions(user=Depends(get_current_user_optional)):
    """Obtener posiciones abiertas"""
    user_id = user['user_id'] if user else 'default'
    positions = trading_system.get_positions(user_id, "OPEN")
    
    return [
        PositionResponse(
            id=pos['id'],
            symbol=pos['symbol'],
            side=pos['side'],
            entry_price=pos['entry_price'],
            current_price=pos['current_price'],
            quantity=pos['quantity'],
            pnl=pos['pnl'],
            pnl_percentage=pos['pnl_percentage'],
            status=pos['status'],
            philosopher=pos['philosopher']
        )
        for pos in positions
    ]

@app.get("/api/signals/active", response_model=List[SignalResponse])
async def get_active_signals(user=Depends(get_current_user_optional)):
    """Obtener señales activas"""
    try:
        cursor = trading_system.conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        
        signals = []
        for row in cursor.fetchall():
            # Manejar columnas opcionales para compatibilidad
            timeframe = row[11] if len(row) > 11 else "SWING"
            duration = row[12] if len(row) > 12 else "1-3 días"
            
            signals.append(SignalResponse(
                id=row[0],
                timestamp=row[1],
                symbol=row[2],
                action=row[3],
                philosopher=row[4],
                confidence=row[5],
                entry_price=row[6],
                stop_loss=row[7],
                take_profit=row[8],
                reasoning=json.loads(row[9]) if row[9] else [],
                timeframe=timeframe,
                duration=duration
            ))
        
        # Si no hay señales, generar una demo
        if not signals:
            demo_signal = trading_system.generate_demo_signal()
            signals.append(SignalResponse(**demo_signal))
        
        return signals
    except Exception as e:
        logger.error(f"Get signals error: {e}")
        # Retornar señal demo en caso de error
        demo_signal = trading_system.generate_demo_signal()
        return [SignalResponse(**demo_signal)]

@app.get("/api/signals/{symbol}")
async def get_signals_by_symbol(symbol: str, user=Depends(get_current_user_optional)):
    """Obtener señales para un símbolo específico"""
    try:
        cursor = trading_system.conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            WHERE symbol = ?
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (symbol,))
        
        signals = []
        for row in cursor.fetchall():
            # Manejar columnas opcionales
            timeframe = row[11] if len(row) > 11 else "SWING"
            duration = row[12] if len(row) > 12 else "1-3 días"
            
            signals.append({
                'id': row[0],
                'timestamp': row[1],
                'symbol': row[2],
                'action': row[3],
                'philosopher': row[4],
                'confidence': row[5],
                'entry_price': row[6],
                'stop_loss': row[7],
                'take_profit': row[8],
                'reasoning': json.loads(row[9]) if row[9] else [],
                'timeframe': timeframe,
                'duration': duration
            })
        
        # Calcular consensus
        if signals:
            buy_signals = sum(1 for s in signals if s['action'] == 'BUY')
            sell_signals = sum(1 for s in signals if s['action'] == 'SELL')
            avg_confidence = sum(s['confidence'] for s in signals) / len(signals)
            
            if buy_signals > sell_signals:
                consensus_action = 'BUY'
            elif sell_signals > buy_signals:
                consensus_action = 'SELL'
            else:
                consensus_action = 'HOLD'
        else:
            # Generar señal demo si no hay señales - con precio correcto para el símbolo
            # Obtener el precio correcto para este símbolo
            default_prices = {
                'BTCUSDT': 115250.0,
                'ETHUSDT': 4790.0,
                'BNBUSDT': 883.0,
                'SOLUSDT': 204.0,
                'ADAUSDT': 0.92,
                'XRPUSDT': 3.05,
                'DOGEUSDT': 0.24
            }
            
            price = trading_system.price_cache.get(symbol, default_prices.get(symbol, 100.0))
            action = random.choice(["BUY", "SELL", "HOLD"])
            
            # Calcular TP y SL correctos
            if action == "BUY":
                stop_loss = price * 0.98
                take_profit = price * 1.03
            elif action == "SELL":
                stop_loss = price * 1.02
                take_profit = price * 0.97
            else:
                stop_loss = price * 0.98
                take_profit = price * 1.02
                
            demo_signal = {
                'id': f"{symbol}_{datetime.now().timestamp()}",
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'philosopher': random.choice(["Socrates", "Aristoteles", "Nietzsche", "Confucio"]),
                'confidence': random.uniform(60, 95),
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reasoning': [f"Señal generada para {symbol}"]
            }
            
            # Guardar en DB
            try:
                cursor = trading_system.conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO signals 
                    (id, timestamp, symbol, action, philosopher, confidence,
                     entry_price, stop_loss, take_profit, reasoning, risk_reward)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (demo_signal['id'], demo_signal['timestamp'], demo_signal['symbol'], 
                      demo_signal['action'], demo_signal['philosopher'], demo_signal['confidence'],
                      demo_signal['entry_price'], demo_signal['stop_loss'], demo_signal['take_profit'],
                      json.dumps(demo_signal['reasoning']), 1.5))
                trading_system.conn.commit()
            except:
                pass
                
            signals = [demo_signal]
            consensus_action = demo_signal['action']
            avg_confidence = demo_signal['confidence']
            buy_signals = 1 if demo_signal['action'] == 'BUY' else 0
            sell_signals = 1 if demo_signal['action'] == 'SELL' else 0
        
        return {
            'symbol': symbol,
            'signals': signals,
            'consensus': {
                'action': consensus_action,
                'confidence': avg_confidence,
                'philosophers_agree': len(signals),
                'entry_price': signals[0]['entry_price'] if signals else 0
            },
            'total_signals': len(signals),
            'high_quality_signals': sum(1 for s in signals if s['confidence'] > 70),
            'bullish_signals': buy_signals,
            'bearish_signals': sell_signals,
            'avg_confidence': avg_confidence,
            'last_update': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get signals by symbol error: {e}")
        # Retornar estructura con señal demo
        demo_signal = trading_system.generate_demo_signal()
        demo_signal['symbol'] = symbol
        return {
            'symbol': symbol,
            'signals': [demo_signal],
            'consensus': {
                'action': demo_signal['action'],
                'confidence': demo_signal['confidence'],
                'philosophers_agree': 1,
                'entry_price': demo_signal['entry_price']
            },
            'total_signals': 1,
            'high_quality_signals': 1 if demo_signal['confidence'] > 70 else 0,
            'bullish_signals': 1 if demo_signal['action'] == 'BUY' else 0,
            'bearish_signals': 1 if demo_signal['action'] == 'SELL' else 0,
            'avg_confidence': demo_signal['confidence'],
            'last_update': datetime.now().isoformat()
        }

@app.get("/api/performance")
async def get_performance(user=Depends(get_current_user_optional)):
    """Obtener métricas de rendimiento"""
    user_id = user['user_id'] if user else 'default'
    portfolio = trading_system.get_portfolio(user_id)
    
    return {
        'balance': portfolio['current_balance'],
        'total_pnl': portfolio['total_pnl'],
        'daily_pnl': 0,
        'open_pnl': 0,
        'win_rate': portfolio['win_rate'],
        'total_trades': portfolio['total_trades'],
        'winning_trades': portfolio['winning_trades'],
        'losing_trades': portfolio['losing_trades']
    }

@app.post("/api/signals/clean")
async def clean_signals(user=Depends(get_current_user_optional)):
    """Limpiar señales con precios incorrectos y regenerar con precios reales"""
    # Primero actualizar precios reales
    await trading_system.get_real_prices()
    
    # Limpiar TODAS las señales incorrectas
    deleted = trading_system.clean_old_signals()
    
    # Limpiar específicamente las señales problemáticas
    cursor = trading_system.conn.cursor()
    cursor.execute("DELETE FROM signals WHERE symbol = 'SOLUSDT' AND entry_price > 500")
    deleted_sol = cursor.rowcount
    cursor.execute("DELETE FROM signals WHERE symbol = 'BNBUSDT' AND entry_price > 1500")
    deleted_bnb = cursor.rowcount
    # CORRECCIÓN ESPECÍFICA PARA ADA
    cursor.execute("DELETE FROM signals WHERE symbol = 'ADAUSDT'")  # Eliminar TODAS las señales de ADA
    deleted_ada = cursor.rowcount
    trading_system.conn.commit()
    
    # Generar nuevas señales con precios correctos
    for symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]:
        for _ in range(3):  # 3 señales por símbolo
            signal = trading_system.generate_demo_signal()
            # Forzar el símbolo correcto
            signal['symbol'] = symbol
    
    return {
        "deleted_total": deleted + deleted_sol + deleted_bnb + deleted_ada,
        "deleted_sol": deleted_sol,
        "deleted_bnb": deleted_bnb,
        "deleted_ada": deleted_ada,
        "message": f"Cleaned {deleted + deleted_sol + deleted_bnb + deleted_ada} incorrect signals and generated new ones",
        "current_prices": {
            "BTCUSDT": trading_system.price_cache.get('BTCUSDT', 115250),
            "ETHUSDT": trading_system.price_cache.get('ETHUSDT', 4790),
            "BNBUSDT": trading_system.price_cache.get('BNBUSDT', 883),
            "SOLUSDT": trading_system.price_cache.get('SOLUSDT', 204),
            "ADAUSDT": trading_system.price_cache.get('ADAUSDT', 0.92),
            "XRPUSDT": trading_system.price_cache.get('XRPUSDT', 3.05),
            "DOGEUSDT": trading_system.price_cache.get('DOGEUSDT', 0.24)
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'memory_optimized': True
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        'name': 'BotPhia Trading API Lightweight',
        'version': '2.0.1',
        'mode': trading_system.mode,
        'status': 'online',
        'message': 'Sistema optimizado para bajo consumo de memoria'
    }

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║         🚀 BOTPHIA TRADING API LIGHTWEIGHT 🚀           ║
║                                                          ║
║  Sistema Optimizado para Producción                     ║
║  • Modo: {trading_system.mode:20s}                      ║
║  • Puerto: {port:5d}                                     ║
║  • Memoria: Optimizada                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)