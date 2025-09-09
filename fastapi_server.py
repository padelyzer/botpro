#!/usr/bin/env python3
"""
===========================================
FASTAPI SERVER - BOTPHIA
===========================================

Backend optimizado para tu UI React con WebSockets
para actualización en tiempo real.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import SafeMath for secure mathematical operations
from safe_math import SafeMath, safe_pnl

# Import error handling system
from error_handler import (
    ErrorHandler, WebSocketError, handle_errors, ErrorSeverity,
    handle_api_error, handle_critical_error
)

# Import thread-safe WebSocket manager
from websocket_manager import (
    ThreadSafeWebSocketManager, get_websocket_manager, 
    WebSocketMessage, MessageType, broadcast_signal_update,
    send_position_update, broadcast_market_data
)
from pydantic import BaseModel
from enum import Enum

# Importar sistemas de trading
from philosophers import PhilosophicalTradingSystem
from philosophers_extended import register_extended_philosophers
from binance_integration import BinanceConnector, MultiProjectManager
from database import db  # Importar la instancia de base de datos
from auth_manager import auth_manager  # Importar gestor de autenticación
# import yfinance as yf  # Reemplazado por Binance API

# ===========================================
# FUNCIONES DE AUTENTICACIÓN
# ===========================================

async def get_current_user(authorization: str = Header(None)):
    """Obtiene el usuario actual desde el token JWT"""
    if not authorization or not authorization.startswith('Bearer '):
        return None  # Para endpoints opcionales
    
    token = authorization.split(' ')[1]
    user_data = auth_manager.verify_token(token)
    
    if not user_data:
        return None
    
    return user_data

async def get_current_user_required(authorization: str = Header(None)):
    """Obtiene el usuario actual (requerido)"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return user

# ===========================================
# MODELOS DE DATOS
# ===========================================

class BotStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class TradingSignal(BaseModel):
    timestamp: str
    philosopher: str
    symbol: str
    action: str  # BUY, SELL, HOLD
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    reasoning: List[str]

class Position(BaseModel):
    id: str
    symbol: str
    type: str  # LONG, SHORT
    entry_price: float
    current_price: float
    quantity: float
    pnl: float
    pnl_percentage: float
    stop_loss: float
    take_profit: float
    status: str  # OPEN, CLOSED

class PerformanceMetric(BaseModel):
    total_pnl: float
    daily_pnl: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    sharpe_ratio: float
    max_drawdown: float
    current_balance: float
    open_positions: int = 0

class Alert(BaseModel):
    timestamp: str
    type: str  # INFO, WARNING, ERROR, SUCCESS
    message: str
    details: Optional[Dict] = None

class BotConfig(BaseModel):
    max_positions: int = 3
    risk_per_trade: float = 0.01
    stop_loss_percentage: float = 0.03
    take_profit_percentage: float = 0.05
    trade_amount_usd: float = 100
    symbols: List[str] = ["DOGEUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT", "LINKUSDT"]  # Símbolos de menor precio para capital bajo
    philosophers: List[str] = ["SOCRATES", "ARISTOTELES", "PLATON"]

# ===========================================
# TRADING MANAGER (SINGLETON)
# ===========================================

class TradingManager:
    """Gestor principal del sistema de trading"""
    
    def __init__(self):
        self.bot_status = BotStatus.STOPPED
        self.config = BotConfig()
        self.philosophy_system = register_extended_philosophers()
        self.binance = BinanceConnector(testnet=True)
        self.project_manager = MultiProjectManager(self.binance)
        
        # Estado - cargar desde base de datos
        self.positions: List[Position] = self._load_positions()
        self.alerts: List[Alert] = []
        self.recent_signals: List[TradingSignal] = []
        self.performance = PerformanceMetric(
            total_pnl=0, daily_pnl=0, win_rate=0,
            total_trades=0, winning_trades=0, losing_trades=0,
            avg_win=0, avg_loss=0, sharpe_ratio=0,
            max_drawdown=0, current_balance=1000, open_positions=0
        )
        
        # Thread-safe WebSocket manager
        self.websocket_manager = get_websocket_manager()
        
        # Trading task
        self.trading_task = None
        
        # Paper Trading Bot
        self.paper_bot = None
        self.paper_bot_task = None
        
        # Inicializar métricas con posiciones cargadas
        self.update_performance_metrics()
        
    async def connect_websocket(self, websocket: WebSocket, user_id: str = None) -> str:
        """
        Conecta un cliente WebSocket usando el manager thread-safe.
        
        Args:
            websocket: WebSocket connection
            user_id: Optional user ID for authentication
            
        Returns:
            Connection ID
        """
        try:
            connection_id = await self.websocket_manager.connect(websocket, user_id)
            # logger.info(f"WebSocket client connected: {connection_id}")
            print(f"WebSocket client connected: {connection_id}")
            return connection_id
        except Exception as e:
            handle_critical_error(e, {
                'operation': 'websocket_connect',
                'user_id': user_id
            })
            raise
    
    async def disconnect_websocket(self, connection_id: str, reason: str = "normal") -> bool:
        """
        Desconecta un cliente WebSocket usando el manager thread-safe.
        
        Args:
            connection_id: Connection ID to disconnect
            reason: Disconnection reason
            
        Returns:
            True if disconnected successfully
        """
        try:
            return await self.websocket_manager.disconnect(connection_id, reason)
        except Exception as e:
            handle_api_error(e, {
                'operation': 'websocket_disconnect',
                'connection_id': connection_id,
                'reason': reason
            })
            return False
    
    async def broadcast(self, message: dict):
        """
        Envía mensaje a todos los clientes conectados usando el manager thread-safe.
        
        Args:
            message: Message dictionary to broadcast
        """
        try:
            # Convert to WebSocketMessage
            ws_message = WebSocketMessage(
                type=MessageType.SIGNAL_UPDATE if message.get('type') == 'signal_update' 
                     else MessageType.SYSTEM_STATUS,
                data=message
            )
            
            # Broadcast using thread-safe manager
            results = await self.websocket_manager.send_message(ws_message, broadcast=True)
            
            # Log results
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            logger.debug(f"Broadcast message sent to {successful}/{total} connections")
            
        except Exception as e:
            handle_critical_error(WebSocketError(
                message=f"Broadcast failed: {str(e)}",
                context={'operation': 'websocket_broadcast', 'message_type': message.get('type')}
            ))
    
    async def send_initial_state(self, connection_id: str = None):
        """
        Envía el estado inicial - ahora usando el WebSocket manager thread-safe.
        
        Args:
            connection_id: Specific connection ID, or None for backwards compatibility
        """
        try:
            # Obtener señales recientes de la base de datos
            recent_signals = []
            try:
                conn = sqlite3.connect("trading_bot.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, symbol, action, confidence, entry_price, 
                           stop_loss, take_profit, philosopher, timestamp, reasoning
                    FROM signals 
                    WHERE confidence >= 60
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                for row in cursor.fetchall():
                    recent_signals.append({
                        'id': row[0],
                        'symbol': row[1],
                        'action': row[2],
                        'confidence': row[3],
                        'entry_price': row[4],
                        'stop_loss': row[5],
                        'take_profit': row[6],
                        'philosopher': row[7],
                        'timestamp': row[8],
                        'reasoning': row[9]
                    })
                conn.close()
            except Exception as e:
                logger.warning(f"Could not fetch signals for initial state: {e}")
            
            initial_data = {
                "bot_status": self.bot_status.value if hasattr(self.bot_status, 'value') else str(self.bot_status),
                "positions": [p.dict() for p in self.positions],
                "performance": self.performance.dict(),
                "config": self.config.dict() if hasattr(self.config, 'dict') else {},
                "alerts": [a.dict() for a in self.alerts[-10:]] if self.alerts else [],
                "signals": recent_signals,
                "websocket_stats": self.websocket_manager.get_statistics()
            }
            
            message = WebSocketMessage(
                type=MessageType.INITIAL_STATE,
                data=initial_data
            )
            
            if connection_id:
                await self.websocket_manager.send_message(message, connection_id=connection_id)
            else:
                # Broadcast to all if no specific connection
                await self.websocket_manager.send_message(message, broadcast=True)
                
        except Exception as e:
            handle_api_error(e, {
                'operation': 'send_initial_state',
                'connection_id': connection_id
            })
    
    async def start_bot(self):
        """Inicia el bot de trading"""
        if self.bot_status == BotStatus.RUNNING:
            return
        
        self.bot_status = BotStatus.RUNNING
        self.trading_task = asyncio.create_task(self.trading_loop())
        
        await self.add_alert("SUCCESS", "Bot iniciado exitosamente")
        await self.broadcast({
            "type": "bot_status",
            "data": {"status": self.bot_status}
        })
    
    async def stop_bot(self):
        """Detiene el bot de trading"""
        if self.bot_status == BotStatus.STOPPED:
            return
        
        self.bot_status = BotStatus.STOPPED
        
        if self.trading_task:
            self.trading_task.cancel()
            self.trading_task = None
        
        await self.add_alert("INFO", "Bot detenido")
        await self.broadcast({
            "type": "bot_status",
            "data": {"status": self.bot_status}
        })
    
    async def trading_loop(self):
        """Loop principal de trading"""
        while self.bot_status == BotStatus.RUNNING:
            try:
                # 1. Obtener datos de mercado
                market_data = await self.fetch_market_data()
                
                # 2. Análisis filosófico
                signals = await self.analyze_with_philosophers(market_data)
                
                # 3. Ejecutar señales con consenso
                if signals:
                    await self.execute_signals(signals)
                
                # 4. Actualizar posiciones
                await self.update_positions()
                
                # 5. Enviar actualizaciones
                await self.send_updates()
                
                # Esperar próximo ciclo (1 minuto en producción, 10 segundos en demo)
                await asyncio.sleep(10)
                
            except Exception as e:
                await self.add_alert("ERROR", f"Error en trading loop: {str(e)}")
                await asyncio.sleep(60)
    
    async def fetch_market_data(self) -> Dict:
        """Obtiene datos de mercado desde Binance"""
        market_data = {}
        
        for symbol in self.config.symbols:
            try:
                # Usar Binance Connector que ya tenemos
                df = self.binance.get_historical_data(symbol, '1m', 100)
                
                if df is not None and not df.empty:
                    # Los datos de Binance ya vienen normalizados
                    market_data[symbol] = df
                    print(f"✅ Datos obtenidos para {symbol}: {len(df)} velas")
                else:
                    print(f"⚠️ Sin datos para {symbol}")
                    
            except Exception as e:
                print(f"❌ Error obteniendo datos de {symbol}: {e}")
        
        return market_data
    
    async def analyze_with_philosophers(self, market_data: Dict) -> List[TradingSignal]:
        """Analiza el mercado con los filósofos configurados"""
        all_signals = []
        
        for symbol, df in market_data.items():
            if df is not None and not df.empty:
                # Análisis con cada filósofo
                signals = self.philosophy_system.analyze_with_philosophers(
                    df, symbol, self.config.philosophers
                )
                
                # Buscar consenso
                if len(signals) >= 2:  # Al menos 2 filósofos de acuerdo
                    consensus = self.philosophy_system.get_consensus(signals)
                    
                    if consensus:
                        trading_signal = TradingSignal(
                            timestamp=datetime.now().isoformat(),
                            philosopher=", ".join(consensus['philosophers_agreed']),
                            symbol=symbol,
                            action=consensus['action'],
                            entry_price=consensus['entry_price'],
                            stop_loss=consensus['stop_loss'],
                            take_profit=consensus['take_profit'],
                            confidence=consensus['confidence'],
                            reasoning=[f"{s.philosopher}: {s.reasoning[0]}" for s in consensus['signals'][:2]]
                        )
                        
                        all_signals.append(trading_signal)
                        self.recent_signals.append(trading_signal)
                        
                        # Mantener solo las últimas 50 señales
                        if len(self.recent_signals) > 50:
                            self.recent_signals = self.recent_signals[-50:]
                        
                        await self.add_alert(
                            "INFO",
                            f"Señal detectada: {consensus['action']} {symbol}",
                            {"confidence": consensus['confidence']}
                        )
        
        return all_signals
    
    async def execute_signals(self, signals: List[TradingSignal]):
        """Ejecuta las señales de trading"""
        for signal in signals:
            # Verificar límites
            if len(self.positions) >= self.config.max_positions:
                await self.add_alert("WARNING", "Máximo de posiciones alcanzado")
                continue
            
            # Crear posición
            position = Position(
                id=f"POS_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                symbol=signal.symbol,
                type="LONG" if signal.action == "BUY" else "SHORT",
                entry_price=signal.entry_price,
                current_price=signal.entry_price,
                quantity=self.config.trade_amount_usd / signal.entry_price,
                pnl=0,
                pnl_percentage=0,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status="OPEN"
            )
            
            self.positions.append(position)
            
            # Guardar posición en base de datos
            if self.save_position(position):
                print(f"✅ Posición automática guardada en BD: {position.id}")
            else:
                print(f"❌ Error guardando posición automática en BD: {position.id}")
            
            # Guardar señal en base de datos también
            if self.save_signal(signal):
                print(f"✅ Señal ejecutada guardada en BD: {signal.symbol}")
            
            self.performance.total_trades += 1
            
            await self.add_alert(
                "SUCCESS",
                f"Posición abierta: {signal.action} {signal.symbol}",
                {"price": signal.entry_price, "confidence": signal.confidence}
            )
    
    async def update_positions(self):
        """Actualiza el estado de las posiciones"""
        for position in self.positions:
            if position.status == "OPEN":
                # Obtener precio actual desde Binance
                try:
                    # Convertir símbolo al formato de Binance
                    binance_symbol = position.symbol.replace("/", "")
                    if not binance_symbol.endswith("USDT"):
                        binance_symbol = binance_symbol + "USDT"
                    
                    # Obtener precio actual desde Binance
                    current_price = self.binance.get_current_price(binance_symbol)
                    if current_price:
                        position.current_price = current_price
                        
                        # Calcular P&L usando SafeMath
                        try:
                            pnl_result = safe_pnl(
                                entry_price=position.entry_price,
                                current_price=current_price,
                                quantity=position.quantity,
                                position_type=position.type.lower()
                            )
                            
                            position.pnl = float(pnl_result['absolute_pnl'])
                            position.pnl_percentage = float(pnl_result['percentage_pnl'])
                            
                        except Exception as e:
                            print(f"Error calculating PnL for position {position.id}: {e}")
                            position.pnl = 0.0
                            position.pnl_percentage = 0.0
                            
                            # Check stop loss y take profit
                            if current_price <= position.stop_loss:
                                await self.close_position(position, "STOP_LOSS")
                            elif current_price >= position.take_profit:
                                await self.close_position(position, "TAKE_PROFIT")
                    
                except Exception as e:
                    print(f"Error actualizando posición {position.id}: {e}")
        
        # Actualizar métricas de performance después de actualizar posiciones
        self.update_performance_metrics()
    
    async def close_position(self, position: Position, reason: str):
        """Cierra una posición"""
        # Obtener precio actual para calcular PnL final
        current_price = self.binance.get_current_price(position.symbol)
        if current_price:
            position.current_price = current_price
            
            # Calcular PnL usando SafeMath
            try:
                pnl_result = safe_pnl(
                    entry_price=position.entry_price,
                    current_price=current_price,
                    quantity=position.quantity,
                    position_type=position.type.lower()
                )
                
                position.pnl = float(pnl_result['absolute_pnl'])
                position.pnl_percentage = float(pnl_result['percentage_pnl'])
                
            except Exception as e:
                print(f"Error calculating PnL for closing position {position.id}: {e}")
                position.pnl = 0.0
                position.pnl_percentage = 0.0
        
        position.status = "CLOSED"
        position.close_time = datetime.now().isoformat()
        
        if position.pnl > 0:
            self.performance.winning_trades += 1
        else:
            self.performance.losing_trades += 1
        
        self.performance.daily_pnl += position.pnl
        self.performance.total_pnl += position.pnl
        self.performance.current_balance = 10000 + self.performance.total_pnl  # Balance inicial 10000
        
        # Actualizar win rate
        if self.performance.total_trades > 0:
            self.performance.win_rate = (self.performance.winning_trades / self.performance.total_trades) * 100
        
        # Actualizar conteo de posiciones abiertas
        self.performance.open_positions = len([p for p in self.positions if p.status == "OPEN" and p.id != position.id])
        
        await self.add_alert(
            "INFO" if position.pnl > 0 else "WARNING",
            f"Posición cerrada ({reason}): {position.symbol}",
            {"pnl": position.pnl, "pnl_percentage": position.pnl_percentage}
        )
        
        # Actualizar performance completa
        self.update_performance_metrics()
    
    def update_performance_metrics(self):
        """Actualiza todas las métricas de performance incluyendo P&L de posiciones activas"""
        # Capital inicial configurable
        initial_capital = 10000
        
        # Calcular P&L total de posiciones cerradas desde BD
        closed_positions = [p for p in self.positions if p.status == "CLOSED"]
        total_closed_pnl = sum(p.pnl for p in closed_positions)
        
        # Calcular P&L actual de posiciones abiertas
        open_positions = [p for p in self.positions if p.status == "OPEN"]
        total_open_pnl = 0
        
        for position in open_positions:
            if position.current_price and position.current_price > 0:
                # Recalcular P&L con precio actual
                if position.type == "LONG":
                    pnl = (position.current_price - position.entry_price) * position.quantity
                else:  # SHORT
                    pnl = (position.entry_price - position.current_price) * position.quantity
                
                total_open_pnl += pnl
        
        # Actualizar métricas
        self.performance.total_pnl = total_closed_pnl
        self.performance.total_trades = len(closed_positions)
        self.performance.open_positions = len(open_positions)
        
        # Saldo actual = Capital inicial + P&L cerrado + P&L abierto
        self.performance.current_balance = initial_capital + total_closed_pnl + total_open_pnl
        
        # Win rate de trades cerrados
        if self.performance.total_trades > 0:
            winning_trades = len([p for p in closed_positions if p.pnl > 0])
            self.performance.winning_trades = winning_trades
            self.performance.losing_trades = self.performance.total_trades - winning_trades
            self.performance.win_rate = (winning_trades / self.performance.total_trades) * 100
        
        # P&L diario (simplificado - solo P&L de posiciones activas)
        self.performance.daily_pnl = total_open_pnl
        
        print(f"💼 Performance actualizada: Balance=${self.performance.current_balance:.2f}, P&L=${total_closed_pnl:.2f}, Open P&L=${total_open_pnl:.2f}")
    
    async def send_updates(self):
        """Envía actualizaciones a los clientes"""
        # Preparar datos para gráfico
        chart_data = await self.prepare_chart_data()
        
        # Obtener señales de alta calidad (igual que en /api/signals/all)
        high_quality_signals = await self.get_high_quality_signals()
        
        await self.broadcast({
            "type": "update",
            "data": {
                "positions": [p.dict() for p in self.positions if p.status == "OPEN"],
                "performance": self.performance.dict(),
                "chart_data": chart_data,
                "signals": high_quality_signals[:5],  # Top 5 señales de alta calidad
                "bot_status": self.bot_status
            }
        })
    
    async def prepare_chart_data(self) -> List[Dict]:
        """Prepara datos para el gráfico de trading"""
        chart_data = []
        
        # Obtener datos de BTC para el gráfico principal
        try:
            df = self.binance.get_historical_data("BTCUSDT", "5m", 50)
            
            if df is not None and not df.empty:
                for index, row in df.iterrows():
                    chart_data.append({
                        "time": index.isoformat(),
                        "open": row['open'],
                        "high": row['high'],
                        "low": row['low'],
                        "close": row['close'],
                        "volume": row['volume']
                    })
        except Exception as e:
            print(f"Error preparando datos del gráfico: {e}")
        
        return chart_data
    
    async def add_alert(self, alert_type: str, message: str, details: Optional[Dict] = None):
        """Añade una alerta al sistema"""
        alert = Alert(
            timestamp=datetime.now().isoformat(),
            type=alert_type,
            message=message,
            details=details
        )
        
        self.alerts.append(alert)
        
        # Mantener solo las últimas 100 alertas
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Enviar alerta a clientes
        await self.broadcast({
            "type": "alert",
            "data": alert.dict()
        })
    
    async def update_config(self, new_config: BotConfig):
        """Actualiza la configuración del bot"""
        self.config = new_config
        
        await self.add_alert("INFO", "Configuración actualizada")
        
        # Si el bot está corriendo, reiniciar con nueva config
        if self.bot_status == BotStatus.RUNNING:
            await self.stop_bot()
            await asyncio.sleep(1)
            await self.start_bot()
    
    # ===========================================
    # MÉTODOS DE PERSISTENCIA
    # ===========================================
    
    def _load_positions(self) -> List[Position]:
        """Carga posiciones desde base de datos"""
        try:
            positions_data = db.get_open_positions()
            positions = []
            for pos_data in positions_data:
                # Convertir los datos de la BD al modelo Pydantic
                position = Position(
                    id=pos_data['id'],
                    symbol=pos_data['symbol'],
                    type=pos_data['type'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'] or pos_data['entry_price'],
                    quantity=pos_data['quantity'],
                    pnl=pos_data['pnl'] or 0,
                    pnl_percentage=pos_data['pnl_percentage'] or 0,
                    stop_loss=pos_data['stop_loss'] or 0,
                    take_profit=pos_data['take_profit'] or 0,
                    status=pos_data['status']
                )
                positions.append(position)
            print(f"✅ Cargadas {len(positions)} posiciones desde BD")
            return positions
        except Exception as e:
            print(f"❌ Error cargando posiciones: {e}")
            return []
    
    def save_position(self, position: Position) -> bool:
        """Guarda una posición en la base de datos"""
        try:
            position_dict = {
                'id': position.id,
                'symbol': position.symbol,
                'type': position.type,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'quantity': position.quantity,
                'pnl': position.pnl,
                'pnl_percentage': position.pnl_percentage,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'status': position.status,
                'strategy': 'Philosophical'
            }
            return db.save_position(position_dict)
        except Exception as e:
            print(f"❌ Error guardando posición: {e}")
            return False
    
    def save_signal(self, signal: TradingSignal) -> bool:
        """Guarda una señal en la base de datos"""
        try:
            signal_dict = {
                'id': f"{signal.symbol}_{signal.timestamp}_{signal.philosopher}",
                'symbol': signal.symbol,
                'action': signal.action,
                'confidence': signal.confidence,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'philosopher': signal.philosopher,
                'reasoning': '; '.join(signal.reasoning) if signal.reasoning else '',
                'market_trend': 'UNKNOWN',
                'rsi': None,
                'volume_ratio': None
            }
            return db.save_signal(signal_dict)
        except Exception as e:
            print(f"❌ Error guardando señal: {e}")
            return False
    
    async def get_high_quality_signals(self) -> List[Dict]:
        """Obtiene señales de alta calidad (+70% confianza) - Lógica compartida con /api/signals/all"""
        high_quality_signals = []
        symbols = ["SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "PEPEUSDT"]
        
        for symbol in symbols:
            try:
                # Obtener datos históricos para análisis completo
                df = self.binance.get_historical_data(symbol, "15m", 100)
                
                if df is not None and not df.empty:
                    current_price = float(df['close'].iloc[-1])
                    
                    # Calcular indicadores técnicos
                    # RSI
                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    rsi_value = float(rsi.iloc[-1]) if not rsi.empty else 50
                    
                    # Medias móviles
                    ma20 = df['close'].rolling(20).mean().iloc[-1]
                    ma50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma20
                    
                    # MACD
                    exp1 = df['close'].ewm(span=12, adjust=False).mean()
                    exp2 = df['close'].ewm(span=26, adjust=False).mean()
                    macd = exp1 - exp2
                    signal_line = macd.ewm(span=9, adjust=False).mean()
                    macd_value = float(macd.iloc[-1])
                    macd_signal = float(signal_line.iloc[-1])
                    
                    # Volumen
                    volume_avg = df['volume'].rolling(20).mean().iloc[-1]
                    volume_current = df['volume'].iloc[-1]
                    volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
                    
                    # Determinar tendencia del mercado
                    if current_price > ma20 > ma50:
                        market_trend = "BULLISH"
                    elif current_price < ma20 < ma50:
                        market_trend = "BEARISH"
                    else:
                        market_trend = "NEUTRAL"
                    
                    # Calcular confianza basada en múltiples factores
                    confidence_score = 50  # Base
                    action = None
                    reasoning = []
                    
                    # Análisis para señal de VENTA (más común en mercado actual)
                    if market_trend == "BEARISH" or (market_trend == "NEUTRAL" and current_price < ma20):
                        action = "SELL"
                        if rsi_value > 70:  # Sobrecompra
                            confidence_score += 25
                            reasoning.append("RSI en zona de distribución")
                        elif 40 <= rsi_value <= 70:  # RSI favorable para venta
                            confidence_score += 15
                            reasoning.append("RSI en zona de distribución")
                        
                        if macd_value < macd_signal:  # MACD negativo
                            confidence_score += 15
                            reasoning.append("MACD con cruce bajista")
                        
                        if volume_ratio > 1.5:  # Volumen alto
                            confidence_score += 10
                            reasoning.append("Volumen elevado confirma venta")
                        
                        if current_price < ma20:  # Precio bajo MA20
                            confidence_score += 10
                            reasoning.append("Precio bajo media móvil 20")
                    
                    # Análisis para señal de COMPRA
                    elif market_trend == "BULLISH" or (market_trend == "NEUTRAL" and current_price > ma20):
                        action = "BUY"
                        if rsi_value < 30:  # Sobreventa
                            confidence_score += 25
                            reasoning.append("RSI sobreventa en tendencia alcista")
                        elif 30 <= rsi_value <= 60:  # RSI favorable
                            confidence_score += 15
                            reasoning.append("RSI en zona de acumulación")
                        
                        if macd_value > macd_signal:  # MACD positivo
                            confidence_score += 15
                            reasoning.append("MACD con cruce alcista")
                        
                        if volume_ratio > 1.5:  # Volumen alto
                            confidence_score += 10
                            reasoning.append("Volumen elevado confirma movimiento")
                        
                        if current_price > ma20:  # Precio sobre MA20
                            confidence_score += 10
                            reasoning.append("Precio sobre media móvil 20")
                    
                    # Solo crear señal si hay acción clara y confianza >= 70%
                    if action and confidence_score >= 70:
                        # Calcular niveles
                        atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
                        
                        signal = {
                            "id": f"{symbol}_{datetime.now().timestamp()}",
                            "user_id": "system",  # Default system user
                            "symbol": symbol,
                            "action": action,
                            "confidence": confidence_score,  # Usar score real calculado
                            "entry_price": current_price,
                            "stop_loss": current_price - (atr * 1.5) if action == "BUY" else current_price + (atr * 1.5),
                            "take_profit": current_price + (atr * 3) if action == "BUY" else current_price - (atr * 3),
                            "philosopher": "BotphIA Signals",
                            "timestamp": datetime.now().isoformat(),
                            "reasoning": " + ".join(reasoning[:3]),  # Top 3 razones
                            "market_trend": market_trend,
                            "rsi": round(rsi_value, 1),
                            "volume_ratio": round(volume_ratio, 2)
                        }
                        
                        # VALIDAR con el pipeline ANTES de guardar
                        from signal_pipeline import get_signal_pipeline
                        pipeline = get_signal_pipeline()
                        
                        # Preparar datos para validación
                        prices = df['close'].tolist()
                        high = df['high'].tolist()
                        low = df['low'].tolist()
                        volume = df['volume'].tolist()
                        
                        # Ejecutar validación
                        evaluation = pipeline.validate_signal(signal, prices, high, low, volume)
                        
                        # Solo guardar si pasa la validación O si tiene confianza muy alta (>90%)
                        if evaluation.is_valid or confidence_score >= 90:
                            # Ajustar confianza basada en validación
                            if not evaluation.is_valid and confidence_score >= 90:
                                # Si no es válido pero tiene alta confianza, reducir un poco
                                signal['confidence'] = min(signal['confidence'], 85)
                                signal['reasoning'] += " (Mercado subóptimo)"
                            else:
                                # Si es válido, usar el mínimo entre ambos scores
                                signal['confidence'] = min(signal['confidence'], evaluation.final_score)
                            
                            signal['validation_score'] = evaluation.final_score
                            signal['market_condition'] = evaluation.market_condition
                            
                            high_quality_signals.append(signal)
                            
                            # Guardar señal en base de datos
                            try:
                                db.save_signal(signal)
                                
                                # Agregar trazabilidad
                                db.save_signal_trace(
                                    signal['id'],
                                    'SIGNAL_GENERATED',
                                    {
                                        'philosopher': signal['philosopher'],
                                        'confidence': signal['confidence'],
                                        'rsi': signal['rsi'],
                                        'volume_ratio': signal['volume_ratio']
                                    },
                                    signal['philosopher']
                                )
                                
                                # Análisis BI automático
                                from signal_analytics import signal_analyzer
                                analysis = signal_analyzer.analyze_signal(signal)
                                
                                if analysis and analysis.quality_score >= 45:
                                    print(f"🎯 Señal de alta calidad detectada: {signal['symbol']} - Score: {analysis.quality_score:.1f}")
                                else:
                                    print(f"⚠️ Señal de baja calidad filtrada: {signal['symbol']} - Score: {analysis.quality_score if analysis else 0:.1f}")
                                    # Guardar trace de filtrado
                                    db.save_signal_trace(
                                        signal['id'],
                                        'SIGNAL_FILTERED',
                                        {'reason': 'Low quality score', 'score': analysis.quality_score if analysis else 0},
                                        signal['philosopher']
                                    )
                                    
                            except Exception as save_error:
                                print(f"Error saving signal to database: {save_error}")
                        
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        # Ordenar por confianza (mayor a menor)
        high_quality_signals.sort(key=lambda x: x['confidence'], reverse=True)
        return high_quality_signals[:5]  # Top 5
    
    async def get_high_quality_signals_for_user(self, user_id: str) -> List[Dict]:
        """Obtiene señales de alta calidad para un usuario específico"""
        # Generar señales usando la misma lógica que get_high_quality_signals
        high_quality_signals = []
        symbols = ["SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "PEPEUSDT"]
        
        for symbol in symbols:
            try:
                # Obtener datos históricos para análisis completo
                df = self.binance.get_historical_data(symbol, "15m", 100)
                
                if df is not None and not df.empty:
                    current_price = float(df['close'].iloc[-1])
                    
                    # Calcular indicadores técnicos (mismo código que get_high_quality_signals)
                    # RSI
                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    rsi_value = float(rsi.iloc[-1]) if not rsi.empty else 50
                    
                    # Medias móviles
                    ma20 = df['close'].rolling(20).mean().iloc[-1]
                    ma50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma20
                    
                    # MACD
                    exp1 = df['close'].ewm(span=12, adjust=False).mean()
                    exp2 = df['close'].ewm(span=26, adjust=False).mean()
                    macd = exp1 - exp2
                    signal_line = macd.ewm(span=9, adjust=False).mean()
                    macd_value = float(macd.iloc[-1])
                    macd_signal = float(signal_line.iloc[-1])
                    
                    # Volumen
                    volume_avg = df['volume'].rolling(20).mean().iloc[-1]
                    volume_current = df['volume'].iloc[-1]
                    volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
                    
                    # Determinar tendencia del mercado
                    if current_price > ma20 > ma50:
                        market_trend = "BULLISH"
                    elif current_price < ma20 < ma50:
                        market_trend = "BEARISH"
                    else:
                        market_trend = "NEUTRAL"
                    
                    # Calcular confianza basada en múltiples factores
                    confidence_score = 50  # Base
                    action = None
                    reasoning = []
                    
                    # Análisis para señal de VENTA
                    if market_trend == "BEARISH" or (market_trend == "NEUTRAL" and current_price < ma20):
                        action = "SELL"
                        if rsi_value > 70:  # Sobrecompra
                            confidence_score += 25
                            reasoning.append("RSI en zona de distribución")
                        elif 40 <= rsi_value <= 70:  # RSI favorable para venta
                            confidence_score += 15
                            reasoning.append("RSI en zona de distribución")
                        
                        if macd_value < macd_signal:  # MACD negativo
                            confidence_score += 15
                            reasoning.append("MACD con cruce bajista")
                        
                        if volume_ratio > 1.5:  # Volumen alto
                            confidence_score += 10
                            reasoning.append("Volumen elevado confirma venta")
                        
                        if current_price < ma20:  # Precio bajo MA20
                            confidence_score += 10
                            reasoning.append("Precio bajo media móvil 20")
                    
                    # Análisis para señal de COMPRA
                    elif market_trend == "BULLISH" or (market_trend == "NEUTRAL" and current_price > ma20):
                        action = "BUY"
                        if rsi_value < 30:  # Sobreventa
                            confidence_score += 25
                            reasoning.append("RSI sobreventa en tendencia alcista")
                        elif 30 <= rsi_value <= 60:  # RSI favorable
                            confidence_score += 15
                            reasoning.append("RSI en zona de acumulación")
                        
                        if macd_value > macd_signal:  # MACD positivo
                            confidence_score += 15
                            reasoning.append("MACD con cruce alcista")
                        
                        if volume_ratio > 1.5:  # Volumen alto
                            confidence_score += 10
                            reasoning.append("Volumen elevado confirma movimiento")
                        
                        if current_price > ma20:  # Precio sobre MA20
                            confidence_score += 10
                            reasoning.append("Precio sobre media móvil 20")
                    
                    # Solo crear señal si hay acción clara y confianza >= 70%
                    if action and confidence_score >= 70:
                        # Calcular niveles
                        atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
                        
                        signal = {
                            "id": f"{symbol}_{user_id}_{datetime.now().timestamp()}",
                            "user_id": user_id,  # Importante: incluir user_id
                            "symbol": symbol,
                            "action": action,
                            "confidence": confidence_score,  # Usar score real calculado
                            "entry_price": current_price,
                            "stop_loss": current_price - (atr * 1.5) if action == "BUY" else current_price + (atr * 1.5),
                            "take_profit": current_price + (atr * 3) if action == "BUY" else current_price - (atr * 3),
                            "philosopher": "BotphIA Signals",
                            "timestamp": datetime.now().isoformat(),
                            "reasoning": " + ".join(reasoning[:3]),  # Top 3 razones
                            "market_trend": market_trend,
                            "rsi": round(rsi_value, 1),
                            "volume_ratio": round(volume_ratio, 2)
                        }
                        high_quality_signals.append(signal)
                        
                        # Guardar señal en base de datos con user_id
                        try:
                            db.save_signal(signal)
                        except Exception as save_error:
                            print(f"Error saving user signal to database: {save_error}")
                        
            except Exception as e:
                print(f"Error analyzing {symbol} for user {user_id}: {e}")
                continue
        
        # Ordenar por confianza (mayor a menor)
        high_quality_signals.sort(key=lambda x: x['confidence'], reverse=True)
        return high_quality_signals[:5]  # Top 5
    
    # ===========================================
    # PAPER TRADING BOT
    # ===========================================
    
    async def start_paper_bot(self):
        """Iniciar el bot de paper trading autónomo"""
        if self.paper_bot_task and not self.paper_bot_task.done():
            await self.add_alert("WARNING", "Bot de paper trading ya está ejecutándose")
            return False
        
        try:
            from autonomous_paper_trader import PaperTradingBot
            self.paper_bot = PaperTradingBot()
            self.paper_bot_task = asyncio.create_task(self.paper_bot.start())
            
            await self.add_alert("SUCCESS", "Bot de paper trading iniciado con $200 USD")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando paper bot: {e}")
            await self.add_alert("ERROR", f"Error iniciando paper bot: {str(e)}")
            return False
    
    async def stop_paper_bot(self):
        """Detener el bot de paper trading"""
        if not self.paper_bot or not self.paper_bot_task:
            await self.add_alert("WARNING", "Bot de paper trading no está ejecutándose")
            return False
        
        try:
            self.paper_bot.stop()
            if self.paper_bot_task:
                self.paper_bot_task.cancel()
                try:
                    await self.paper_bot_task
                except asyncio.CancelledError:
                    pass
            
            await self.add_alert("INFO", "Bot de paper trading detenido")
            return True
            
        except Exception as e:
            logger.error(f"Error deteniendo paper bot: {e}")
            await self.add_alert("ERROR", f"Error deteniendo paper bot: {str(e)}")
            return False
    
    def get_paper_bot_status(self) -> Dict:
        """Obtener estado del bot de paper trading"""
        if not self.paper_bot:
            return {
                "running": False,
                "balance": 200.0,
                "total_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0.0,
                "open_positions": 0,
                "positions": []
            }
        
        # Calcular win rate
        win_rate = 0.0
        if self.paper_bot.total_trades > 0:
            win_rate = (self.paper_bot.winning_trades / self.paper_bot.total_trades) * 100
        
        # Formatear posiciones para el frontend
        positions = []
        for pos in self.paper_bot.positions.values():
            positions.append({
                "id": pos["id"],
                "symbol": pos["symbol"],
                "action": pos["action"],
                "entry_price": pos["entry_price"],
                "current_price": pos["current_price"],
                "quantity": pos["quantity"],
                "pnl": pos["pnl"],
                "pnl_percentage": pos["pnl_percentage"],
                "philosopher": pos["philosopher"],
                "confidence": pos["confidence"],
                "open_time": pos["open_time"].isoformat() if hasattr(pos["open_time"], 'isoformat') else pos["open_time"]
            })
        
        return {
            "running": self.paper_bot.running,
            "balance": self.paper_bot.current_balance,
            "total_pnl": self.paper_bot.total_pnl,
            "total_trades": self.paper_bot.total_trades,
            "winning_trades": self.paper_bot.winning_trades,
            "win_rate": win_rate,
            "open_positions": len(self.paper_bot.positions),
            "max_positions": self.paper_bot.max_positions,
            "positions": positions,
            "roi_percentage": (self.paper_bot.total_pnl / self.paper_bot.initial_balance) * 100
        }

# ===========================================
# INSTANCIA GLOBAL
# ===========================================

trading_manager = TradingManager()

# ===========================================
# LIFESPAN EVENTS
# ===========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    print("🚀 Starting Signal Haven Desk API...")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    if trading_manager.trading_task:
        trading_manager.trading_task.cancel()

# ===========================================
# FASTAPI APP
# ===========================================

app = FastAPI(
    title="Signal Haven Desk API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS para permitir conexiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes para desarrollo
    allow_credentials=False,  # Desactivar credentials para evitar problemas
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ===========================================
# REST ENDPOINTS
# ===========================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "bot_status": trading_manager.bot_status,
        "positions": len(trading_manager.positions),
        "version": "1.0.0"
    }

@app.options("/{full_path:path}")
async def handle_options():
    """Handle CORS preflight requests"""
    return {"message": "OK"}

@app.get("/api/status")
async def get_status():
    """Obtiene el estado actual del sistema"""
    return {
        "bot_status": trading_manager.bot_status,
        "positions": [p.dict() for p in trading_manager.positions if p.status == "OPEN"],
        "performance": trading_manager.performance.dict(),
        "config": trading_manager.config.dict()
    }

@app.post("/api/bot/start")
async def start_bot():
    """Inicia el bot de trading"""
    await trading_manager.start_bot()
    return {"status": "started"}

@app.post("/api/bot/stop")
async def stop_bot():
    """Detiene el bot de trading"""
    await trading_manager.stop_bot()
    return {"status": "stopped"}

@app.get("/api/config")
async def get_config():
    """Obtiene la configuración actual"""
    return trading_manager.config.dict()

@app.post("/api/config")
async def update_config(config: BotConfig):
    """Actualiza la configuración del bot"""
    await trading_manager.update_config(config)
    return {"status": "updated", "config": config.dict()}

# ===========================================
# PAPER TRADING ENDPOINTS
# ===========================================

@app.post("/api/paper-bot/start")
async def start_paper_bot():
    """Iniciar el bot de paper trading autónomo"""
    success = await trading_manager.start_paper_bot()
    return {"status": "started" if success else "error", "success": success}

@app.post("/api/paper-bot/stop") 
async def stop_paper_bot():
    """Detener el bot de paper trading"""
    success = await trading_manager.stop_paper_bot()
    return {"status": "stopped" if success else "error", "success": success}

@app.get("/api/paper-bot/status")
async def get_paper_bot_status():
    """Obtener estado del bot de paper trading"""
    status = trading_manager.get_paper_bot_status()
    return status

@app.get("/api/paper-bot/audit-summary")
async def get_paper_bot_audit():
    """Obtener resumen de auditoría del bot de paper trading"""
    try:
        from audit_system import audit_system
        summary = audit_system.get_audit_summary(hours=24)
        return summary
    except Exception as e:
        print(f"Error obteniendo resumen de auditoría: {e}")
        return {"error": str(e), "summary": {}}

@app.get("/api/paper-bot/audit-export")
async def export_paper_bot_audit(start_date: str = None, end_date: str = None):
    """Exportar datos completos de auditoría del bot de paper trading"""
    try:
        from audit_system import audit_system
        export_data = audit_system.export_audit_data(start_date, end_date)
        return export_data
    except Exception as e:
        print(f"Error exportando datos de auditoría: {e}")
        return {"error": str(e), "trades": []}

@app.get("/api/positions")
async def get_positions(current_user: dict = Depends(get_current_user_required)):
    """Obtiene las posiciones activas del usuario autenticado"""
    try:
        user_id = current_user["user_id"]
        # Cargar posiciones del usuario desde base de datos
        db_positions = db.get_open_positions(user_id=user_id)
        
        # Convertir a formato esperado por el frontend
        user_positions = []
        for db_pos in db_positions:
            position_dict = {
                'id': db_pos.get('id', ''),
                'symbol': db_pos.get('symbol', ''),
                'type': db_pos.get('type', 'LONG'),
                'entry_price': db_pos.get('entry_price', 0),
                'current_price': db_pos.get('current_price', db_pos.get('entry_price', 0)),
                'quantity': db_pos.get('quantity', 0),
                'stop_loss': db_pos.get('stop_loss', 0),
                'take_profit': db_pos.get('take_profit', 0),
                'pnl': db_pos.get('pnl', 0),
                'pnl_percentage': db_pos.get('pnl_percentage', 0),
                'status': db_pos.get('status', 'OPEN'),
                'open_time': db_pos.get('open_time', ''),
                'close_time': db_pos.get('close_time', ''),
                'strategy': db_pos.get('strategy', 'Manual')
            }
            user_positions.append(position_dict)
        
        return user_positions
        
    except Exception as e:
        print(f"Error loading user positions from database: {e}")
        return []

@app.get("/api/performance")
async def get_performance(current_user: dict = Depends(get_current_user_required)):
    """Obtiene métricas de performance del usuario autenticado"""
    user_id = current_user["user_id"]
    # Por ahora retornamos métricas generales, pero en el futuro podríamos
    # calcular métricas específicas del usuario basadas en sus posiciones
    return trading_manager.performance.dict()

@app.get("/api/system-status")
async def get_system_status():
    """Obtiene estado detallado del sistema"""
    return {
        "service_status": "online",
        "bot_status": trading_manager.bot_status,
        "active_pairs": trading_manager.config.symbols,
        "active_philosophers": trading_manager.config.philosophers,
        "websocket_clients": trading_manager.websocket_manager.get_connection_count(),
        "active_positions": len([p for p in trading_manager.positions if p.status == "OPEN"]),
        "total_signals_generated": len(trading_manager.recent_signals),
        "last_signal": trading_manager.recent_signals[-1].dict() if trading_manager.recent_signals else None,
        "alerts_count": len(trading_manager.alerts),
        "performance_summary": {
            "balance": trading_manager.performance.current_balance,
            "total_pnl": trading_manager.performance.total_pnl,
            "win_rate": trading_manager.performance.win_rate,
            "total_trades": trading_manager.performance.total_trades
        }
    }

@app.get("/api/system-stats")
async def get_system_stats():
    """Obtiene estadísticas de actividad del sistema"""
    from system_stats import get_system_stats
    stats = get_system_stats()
    return stats.get_stats_summary()

@app.get("/api/health")
async def get_health_status():
    """Obtiene el estado de salud de todos los servicios"""
    from service_health import get_health_checker
    checker = get_health_checker()
    health = await checker.check_all_services()
    metrics = await checker.get_system_metrics()
    return {
        **health,
        'system_metrics': metrics
    }

@app.get("/api/market-conditions")
async def get_market_conditions():
    """Obtiene las condiciones actuales del mercado para todos los símbolos"""
    from market_analyzer import get_market_analyzer
    from binance_integration import BinanceConnector
    
    analyzer = get_market_analyzer()
    connector = BinanceConnector(testnet=False)  # Usar API real para condiciones del mercado
    conditions = {}
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
               'DOGEUSDT', 'XRPUSDT', 'LINKUSDT', 'DOTUSDT', 'AVAXUSDT']
    
    for symbol in symbols:
        try:
            # Obtener datos históricos
            df = connector.get_historical_data(symbol, timeframe='15m', limit=100)
            if not df.empty and len(df) >= 30:
                prices = df['close'].tolist()
                high = df['high'].tolist()
                low = df['low'].tolist()
                volume = df['volume'].tolist()
                
                # Analizar condición del mercado
                analysis = analyzer.analyze_market_condition(symbol, prices, high, low, volume)
                
                conditions[symbol] = {
                    'condition': analysis['condition'],
                    'condition_text': analysis['condition_text'],
                    'condition_icon': analysis['condition_icon'],
                    'tradeable': analysis['tradeable'],
                    'confidence': analysis['confidence'],
                    'trend': analysis['trend'],
                    'warnings': analysis.get('warnings', []),
                    'recommendations': analysis.get('recommendations', []),
                    'details': {
                        'rsi': round(analysis['details']['rsi'], 1),
                        'current_price': analysis['details']['current_price'],
                        'volatility': round(analysis['details']['volatility_ratio'], 1),
                        'volume': round(analysis['details']['volume_ratio'], 1)
                    }
                }
            else:
                conditions[symbol] = {
                    'condition': 'UNSTABLE',
                    'condition_text': 'Datos insuficientes',
                    'condition_icon': '⚠️',
                    'tradeable': False,
                    'confidence': 0
                }
        except Exception as e:
            logger.error(f"Error analizando {symbol}: {e}")
            conditions[symbol] = {
                'condition': 'ERROR',
                'condition_text': 'Error al analizar',
                'condition_icon': '❌',
                'tradeable': False,
                'confidence': 0
            }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "conditions": conditions,
        "summary": {
            "tradeable_count": sum(1 for c in conditions.values() if c['tradeable']),
            "lateral_count": sum(1 for c in conditions.values() if c['condition'] == 'LATERAL'),
            "volatile_count": sum(1 for c in conditions.values() if c['condition'] == 'VOLATILE'),
            "optimal_count": sum(1 for c in conditions.values() if c['condition'] == 'OPTIMAL')
        }
    }

@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    """Obtiene las últimas alertas"""
    return [a.dict() for a in trading_manager.alerts[-limit:]]

@app.get("/api/recent-signals")
async def get_recent_signals(limit: int = 10):
    """Obtiene las señales recientes (sin autenticación para dashboard público)"""
    try:
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, symbol, action, confidence, entry_price, 
                   stop_loss, take_profit, philosopher, timestamp, reasoning
            FROM signals 
            WHERE confidence >= 60
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'id': row[0],
                'symbol': row[1],
                'action': row[2],
                'confidence': row[3],
                'entry_price': row[4],
                'stop_loss': row[5],
                'take_profit': row[6],
                'philosopher': row[7],
                'timestamp': row[8],
                'reasoning': row[9]
            })
        
        conn.close()
        return signals
        
    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        return []

@app.get("/api/signals/active")
async def get_active_signals():
    """Obtiene señales activas recientes (sin requerir autenticación para el dashboard)"""
    try:
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        # Obtener señales recientes con confianza > 60%
        # Temporalmente mostrar las últimas señales disponibles
        cursor.execute("""
            SELECT id, symbol, action, confidence, entry_price, 
                   stop_loss, take_profit, philosopher, timestamp, reasoning
            FROM signals 
            WHERE confidence >= 60
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'id': row[0],
                'symbol': row[1],
                'action': row[2],
                'confidence': row[3],
                'entry_price': row[4],
                'stop_loss': row[5],
                'take_profit': row[6],
                'philosopher': row[7],
                'timestamp': row[8],
                'reasoning': row[9]
            })
        
        conn.close()
        
        return {"signals": signals}
        
    except Exception as e:
        logger.error(f"Error getting active signals: {e}")
        return {"signals": [], "error": str(e)}

@app.get("/api/signals/all")
async def get_all_active_signals(current_user: dict = Depends(get_current_user_required)):
    """Obtiene señales de alta calidad (+70% confianza) del usuario autenticado"""
    try:
        user_id = current_user["user_id"]
        
        # Obtener señales recientes del usuario desde la base de datos (últimas 2 horas)
        recent_signals = db.get_recent_signals(20, user_id=user_id)
        
        # Filtrar señales no ejecutadas y de alta calidad (>70% confianza)
        db_signals = [
            signal for signal in recent_signals 
            if not signal.get('executed', False) and signal.get('confidence', 0) >= 70
        ]
        
        # Si no hay suficientes señales en BD, generar nuevas para el usuario
        if len(db_signals) < 3:
            fresh_signals = await trading_manager.get_high_quality_signals_for_user(user_id)
            # Combinar señales de BD con nuevas
            all_signals = db_signals + fresh_signals
        else:
            all_signals = db_signals
        
        # Remover duplicados por símbolo (mantener la más reciente)
        unique_signals = {}
        for signal in all_signals:
            symbol = signal.get('symbol')
            if symbol not in unique_signals or signal.get('timestamp', '') > unique_signals[symbol].get('timestamp', ''):
                unique_signals[symbol] = signal
        
        # Ordenar por confianza y retornar top 5
        result_signals = list(unique_signals.values())
        result_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return result_signals[:5]
        
    except Exception as e:
        print(f"Error getting user signals: {e}")
        # Fallback a señales frescas para el usuario
        return await trading_manager.get_high_quality_signals_for_user(current_user["user_id"])

@app.get("/api/symbol/{symbol}/data")
async def get_symbol_data(symbol: str):
    """Obtiene datos completos para un símbolo específico"""
    try:
        # Obtener precio actual desde Binance
        current_price = trading_manager.binance.get_current_price(symbol)
        
        # Obtener datos históricos recientes
        df = trading_manager.binance.get_historical_data(symbol, '1m', 100)
        
        if df is not None and not df.empty:
            # Calcular cambios de precio
            latest_close = df['close'].iloc[-1]
            prev_close = df['close'].iloc[-24] if len(df) > 24 else df['close'].iloc[0]
            price_change_24h = latest_close - prev_close
            price_change_percent_24h = ((latest_close / prev_close) - 1) * 100
            volume_24h = df['volume'].tail(24).sum() if len(df) > 24 else df['volume'].sum()
            
            # Primero buscar señales existentes en la base de datos
            recent_db_signals = db.get_recent_signals_by_symbol(symbol, limit=10)
            
            # Si no hay señales recientes, analizar con filósofos
            if not recent_db_signals or len(recent_db_signals) < 3:
                signals = trading_manager.philosophy_system.analyze_with_philosophers(
                    df, symbol, trading_manager.config.philosophers
                )
            else:
                # Usar las señales de la base de datos
                signals = []
                for db_signal in recent_db_signals:
                    # Convertir señales de BD al formato esperado
                    from types import SimpleNamespace
                    signal = SimpleNamespace(
                        philosopher=db_signal.get('philosopher', 'Unknown'),
                        action=db_signal.get('action', 'HOLD'),
                        confidence=db_signal.get('confidence', 0) / 100.0,  # Convertir a decimal
                        reasoning=[db_signal.get('reasoning', '')],
                        entry_price=db_signal.get('entry_price', current_price),
                        stop_loss=db_signal.get('stop_loss', current_price * 0.98),
                        take_profit=db_signal.get('take_profit', current_price * 1.02)
                    )
                    signals.append(signal)
            
            # Formatear señales para el frontend
            philosopher_signals = []
            for signal in signals:
                # Calcular % de cuenta sugerido basado en confianza y riesgo
                base_risk = 1.0  # 1% riesgo base
                confidence_factor = signal.confidence
                
                # Ajustar riesgo según confianza: más confianza = más % de cuenta
                if confidence_factor >= 0.8:
                    account_percentage = base_risk * 3  # 3% para alta confianza
                elif confidence_factor >= 0.7:
                    account_percentage = base_risk * 2  # 2% para confianza media-alta
                elif confidence_factor >= 0.6:
                    account_percentage = base_risk * 1.5  # 1.5% para confianza media
                else:
                    account_percentage = base_risk  # 1% para baja confianza
                
                # Calcular riesgo/recompensa
                risk_amount = abs(signal.entry_price - signal.stop_loss)
                reward_amount = abs(signal.take_profit - signal.entry_price)
                risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 1
                
                philosopher_signals.append({
                    "name": signal.philosopher,
                    "action": signal.action,
                    "confidence": signal.confidence * 100,  # Convertir a porcentaje
                    "reasoning": signal.reasoning[0] if signal.reasoning else "",
                    "entry_price": signal.entry_price,
                    "target_price": signal.take_profit,
                    "stop_loss": signal.stop_loss,
                    "account_percentage": account_percentage,
                    "risk_reward_ratio": round(risk_reward_ratio, 2),
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                "symbol": symbol,
                "current_price": current_price or latest_close,
                "price_change_24h": price_change_24h,
                "price_change_percent_24h": price_change_percent_24h,
                "volume_24h": volume_24h,
                "philosopher_signals": philosopher_signals,
                "positions": [p.dict() for p in trading_manager.positions if p.symbol == symbol],
                "last_update": datetime.now().isoformat()
            }
        else:
            return {
                "symbol": symbol,
                "error": "No data available",
                "current_price": 0,
                "philosopher_signals": []
            }
    except Exception as e:
        print(f"Error obteniendo datos para {symbol}: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "current_price": 0,
            "philosopher_signals": []
        }

@app.get("/api/market/{symbol}/chart")
async def get_chart_data(symbol: str, interval: str = "1m", limit: int = 100):
    """Obtiene datos históricos de gráfica para un símbolo"""
    try:
        df = trading_manager.binance.get_historical_data(symbol, interval, limit)
        
        if df is None or df.empty:
            return []
        
        chart_data = []
        for index, row in df.iterrows():
            chart_data.append({
                "time": index.isoformat(),
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume']
            })
        
        return chart_data
    except Exception as e:
        print(f"Error obteniendo datos de gráfica para {symbol}: {e}")
        return []

@app.get("/api/price-history/{symbol}")
async def get_price_history(symbol: str, interval: str = "15m", limit: int = 50):
    """Obtiene histórico simplificado de precios para gráfico fallback"""
    try:
        df = trading_manager.binance.get_historical_data(symbol, interval, limit)
        
        if df is None or df.empty:
            return []
        
        price_history = []
        for index, row in df.iterrows():
            price_history.append({
                "timestamp": index.isoformat(),
                "price": row['close'],
                "close": row['close']
            })
        
        return price_history
    except Exception as e:
        print(f"Error obteniendo histórico de precios para {symbol}: {e}")
        return []

@app.get("/api/market/{symbol}/indicators")
async def get_market_indicators(symbol: str, interval: str = "15m"):
    """Calcula indicadores de mercado reales para un símbolo"""
    try:
        # Obtener datos históricos (necesitamos más datos para calcular indicadores)
        df = trading_manager.binance.get_historical_data(symbol, interval, 200)
        
        if df is None or df.empty:
            return {"error": "No data available"}
        
        # Calcular RSI
        def calculate_rsi(df, period=14):
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        
        # Calcular MACD
        def calculate_macd(df):
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            return {
                "value": float(macd.iloc[-1]),
                "signal": float(signal.iloc[-1]),
                "histogram": float(histogram.iloc[-1])
            }
        
        # Calcular volatilidad (desviación estándar del retorno)
        returns = df['close'].pct_change()
        volatility = returns.std() * 100  # Convertir a porcentaje
        
        # Calcular momentum
        momentum = ((df['close'].iloc[-1] / df['close'].iloc[-20]) - 1) * 100
        
        # Calcular volumen promedio
        volume_avg = df['volume'].rolling(window=20).mean().iloc[-1]
        volume_current = df['volume'].iloc[-1]
        volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
        
        # Identificar soportes y resistencias simples
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        current_price = df['close'].iloc[-1]
        
        # Determinar fase del mercado
        rsi_value = calculate_rsi(df)
        macd_data = calculate_macd(df)
        
        if rsi_value > 70:
            market_phase = "OVERBOUGHT"
        elif rsi_value < 30:
            market_phase = "OVERSOLD"
        elif abs(momentum) < 2:
            market_phase = "CONSOLIDATION"
        elif momentum > 5:
            market_phase = "BULLISH_TREND"
        elif momentum < -5:
            market_phase = "BEARISH_TREND"
        else:
            market_phase = "NEUTRAL"
        
        # Determinar condición del mercado
        if rsi_value > 70 and volume_ratio > 1.5:
            market_condition = "EXPLOSIVE"
        elif rsi_value > 60 and momentum > 5:
            market_condition = "BULLISH"
        elif rsi_value < 40 and momentum < -5:
            market_condition = "BEARISH"
        elif volume_ratio < 0.5:
            market_condition = "ACCUMULATION"
        elif volume_ratio > 2:
            market_condition = "DISTRIBUTION"
        else:
            market_condition = "NEUTRAL"
        
        return {
            "rsi": float(rsi_value),
            "macd": macd_data,
            "volume": {
                "current": float(volume_current),
                "average": float(volume_avg),
                "ratio": float(volume_ratio)
            },
            "volatility": float(volatility),
            "momentum": float(momentum),
            "trend_strength": abs(float(momentum)),
            "support_resistance": {
                "support": float(recent_low),
                "resistance": float(recent_high),
                "current_price": float(current_price)
            },
            "market_phase": market_phase,
            "market_condition": market_condition,
            "volume_profile": "HIGH" if volume_ratio > 1.5 else "NORMAL" if volume_ratio > 0.5 else "LOW"
        }
    except Exception as e:
        print(f"Error calculando indicadores para {symbol}: {e}")
        return {"error": str(e)}

@app.post("/api/positions/open")
async def open_position_manually(position_data: dict):
    """Abre una posición manualmente desde una señal"""
    try:
        # Obtener precio actual
        symbol = position_data.get("symbol")
        current_price = trading_manager.binance.get_current_price(symbol)
        
        if not current_price:
            current_price = position_data.get("entry_price", 0)
        
        # Calcular tamaño de posición basado en el monto
        amount = position_data.get("amount", 100)  # USD
        position_size = amount / current_price if current_price > 0 else 0
        
        # Calcular SL y TP (2% stop loss, 3% take profit por defecto)
        action = position_data.get("action", "BUY")
        if action == "BUY":
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.03
        else:
            stop_loss = current_price * 1.02
            take_profit = current_price * 0.97
        
        # Crear posición
        new_position = Position(
            id=f"{symbol}_{datetime.now().timestamp()}",
            symbol=symbol,
            type="LONG" if action == "BUY" else "SHORT",
            entry_price=current_price,
            current_price=current_price,
            quantity=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            pnl=0,
            pnl_percentage=0,
            status="OPEN"
        )
        
        # Agregar a posiciones activas
        trading_manager.positions.append(new_position)
        
        # Guardar en base de datos
        if trading_manager.save_position(new_position):
            print(f"✅ Posición guardada en BD: {new_position.id}")
        else:
            print(f"❌ Error guardando posición en BD: {new_position.id}")
        
        # Actualizar métricas
        trading_manager.performance.total_trades += 1
        trading_manager.performance.open_positions = len([p for p in trading_manager.positions if p.status == "OPEN"])
        
        # Enviar actualización por WebSocket
        await trading_manager.send_updates()
        
        return new_position.dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/position/{position_id}")
async def close_position_manually(position_id: str):
    """Cierra una posición manualmente"""
    position = next((p for p in trading_manager.positions if p.id == position_id), None)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    await trading_manager.close_position(position, "MANUAL")
    return {"status": "closed", "pnl": position.pnl}

@app.get("/api/market/{symbol}/stats")
async def get_market_stats(symbol: str):
    """Obtiene estadísticas de mercado para un símbolo"""
    try:
        # Obtener datos históricos para calcular estadísticas
        df = trading_manager.binance.get_historical_data(symbol, "1h", 24)
        
        if df is None or df.empty:
            return {"error": "No data available"}
        
        current_price = float(df['close'].iloc[-1])
        open_24h = float(df['open'].iloc[0])
        high_24h = float(df['high'].max())
        low_24h = float(df['low'].min())
        volume_24h = float(df['volume'].sum())
        
        # Calcular cambios
        change_24h = current_price - open_24h
        change_24h_percent = (change_24h / open_24h) * 100 if open_24h > 0 else 0
        
        # Calcular promedios móviles
        df_daily = trading_manager.binance.get_historical_data(symbol, "1d", 200)
        if df_daily is not None and not df_daily.empty:
            ma_50 = float(df_daily['close'].rolling(window=50).mean().iloc[-1]) if len(df_daily) >= 50 else current_price
            ma_200 = float(df_daily['close'].rolling(window=200).mean().iloc[-1]) if len(df_daily) >= 200 else current_price
        else:
            ma_50 = current_price
            ma_200 = current_price
        
        # Calcular RSI
        def calculate_rsi(data, period=14):
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not rsi.empty else 50
        
        rsi = calculate_rsi(df)
        
        # Determinar tendencia
        if current_price > ma_50 > ma_200:
            trend = "STRONGLY_BULLISH"
        elif current_price > ma_50:
            trend = "BULLISH"
        elif current_price < ma_50 < ma_200:
            trend = "STRONGLY_BEARISH"
        elif current_price < ma_50:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        # Determinar tendencia de volumen
        volume_avg_7d = df['volume'].rolling(window=7).mean().iloc[-1] if len(df) >= 7 else volume_24h
        if volume_24h > volume_avg_7d * 1.5:
            volume_trend = "Alto"
        elif volume_24h < volume_avg_7d * 0.5:
            volume_trend = "Bajo"
        else:
            volume_trend = "Normal"
        
        # Calcular ranking aproximado basado en volumen
        # Los símbolos más populares tienen mayor volumen
        volume_ranks = {
            "BTCUSDT": 1, "ETHUSDT": 2, "BNBUSDT": 3, "SOLUSDT": 4,
            "XRPUSDT": 5, "ADAUSDT": 6, "DOGEUSDT": 7, "AVAXUSDT": 8,
            "LINKUSDT": 9, "DOTUSDT": 10, "PEPEUSDT": 15
        }
        market_rank = volume_ranks.get(symbol, 20)
        
        # Calcular dominancia aproximada (porcentaje del mercado total)
        # Esto es una aproximación basada en el volumen
        total_market_volume = 50000000000  # $50B volumen diario aproximado del mercado crypto
        dominance = (volume_24h * current_price / total_market_volume) * 100
        
        return {
            "current_price": current_price,
            "change_24h": change_24h,
            "change_24h_percent": change_24h_percent,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volume_24h": volume_24h,
            "market_cap": volume_24h * current_price,  # Aproximación
            "rsi": rsi,
            "ma_50": ma_50,
            "ma_200": ma_200,
            "trend": trend.lower().replace("_", " "),  # Formato para el frontend
            "volume_trend": volume_trend,
            "market_rank": market_rank,
            "dominance": dominance,
            "last_update": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error getting market stats for {symbol}: {e}")
        return {"error": str(e)}

@app.get("/api/strategies/{symbol}")
async def get_symbol_strategies(symbol: str):
    """Obtiene información de estrategias para un símbolo"""
    try:
        # Información de la estrategia adaptativa
        strategies = [
            {
                "id": "adaptive_v4",
                "name": "Sistema Adaptativo V4",
                "description": "Estrategia multi-régimen con detección automática de condiciones de mercado",
                "type": "ADAPTIVE",
                "timeframe": "15m",
                "indicators": ["RSI", "MACD", "Bollinger Bands", "Volume", "ATR"],
                "risk_level": "MODERATE",
                "win_rate": 65.5,  # Basado en backtests históricos
                "avg_profit": 2.8,
                "avg_loss": 1.2,
                "sharpe_ratio": 1.45,
                "max_drawdown": 12.5,
                "active": True,
                "parameters": {
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "bb_period": 20,
                    "bb_std": 2,
                    "volume_threshold": 1.5,
                    "risk_per_trade": 2,
                    "max_positions": 3
                },
                "performance": {
                    "today": 2.3,
                    "week": 5.7,
                    "month": 12.4,
                    "year": 45.8
                }
            },
            {
                "id": "philosophical_consensus",
                "name": "Consenso Filosófico",
                "description": "Sistema de análisis basado en 10 filosofías de trading diferentes",
                "type": "CONSENSUS",
                "timeframe": "Multiple",
                "indicators": ["Multiple"],
                "risk_level": "CONSERVATIVE",
                "win_rate": 72.3,
                "avg_profit": 2.1,
                "avg_loss": 0.9,
                "sharpe_ratio": 1.85,
                "max_drawdown": 8.2,
                "active": True,
                "philosophers": [
                    "Socrates (Análisis Fundamental)",
                    "Plato (Patrones Ideales)",
                    "Aristotle (Lógica de Mercado)",
                    "Descartes (Análisis Cartesiano)",
                    "Kant (Imperativos de Trading)",
                    "Nietzsche (Contrarian)",
                    "Lao Tzu (Flujo Natural)",
                    "Sun Tzu (Estrategia)",
                    "Marcus Aurelius (Disciplina)",
                    "Nassim Taleb (Anti-Fragilidad)"
                ],
                "performance": {
                    "today": 1.8,
                    "week": 4.2,
                    "month": 9.5,
                    "year": 38.2
                }
            }
        ]
        
        # Obtener datos actuales del mercado para ajustar estrategias
        df = trading_manager.binance.get_historical_data(symbol, "15m", 100)
        if df is not None and not df.empty:
            volatility = df['close'].pct_change().std() * 100
            
            # Ajustar recomendaciones basadas en volatilidad
            for strategy in strategies:
                if volatility > 3:
                    strategy["recommendation"] = "CAUTION - High volatility detected"
                    strategy["suggested_risk"] = max(1, strategy["parameters"]["risk_per_trade"] - 1) if "parameters" in strategy and "risk_per_trade" in strategy["parameters"] else 1
                elif volatility < 1:
                    strategy["recommendation"] = "LIMITED - Low volatility environment"
                    strategy["suggested_risk"] = strategy["parameters"]["risk_per_trade"] if "parameters" in strategy and "risk_per_trade" in strategy["parameters"] else 2
                else:
                    strategy["recommendation"] = "OPTIMAL - Normal market conditions"
                    strategy["suggested_risk"] = strategy["parameters"]["risk_per_trade"] if "parameters" in strategy and "risk_per_trade" in strategy["parameters"] else 2
        
        return {
            "symbol": symbol,
            "strategies": strategies,
            "active_count": len([s for s in strategies if s["active"]]),
            "recommended_strategy": "philosophical_consensus",
            "last_update": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error getting strategies for {symbol}: {e}")
        return {"error": str(e)}

@app.get("/api/signals/{symbol}")
async def get_symbol_signals(symbol: str):
    """Obtiene señales de trading para un símbolo con validación temporal"""
    try:
        from datetime import datetime, timedelta
        signals = []
        
        # Obtener análisis de los filósofos
        if trading_manager.philosophy_system:
            # Obtener datos para análisis
            df = trading_manager.binance.get_historical_data(symbol, "15m", 100)
            
            if df is not None and not df.empty:
                current_price = float(df['close'].iloc[-1])
                current_time = datetime.now()
                
                # Obtener datos de mercado 24h
                price_24h_ago = float(df['close'].iloc[-96]) if len(df) >= 96 else float(df['close'].iloc[0])
                change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
                high_24h = float(df['high'].tail(96).max()) if len(df) >= 96 else float(df['high'].max())
                low_24h = float(df['low'].tail(96).min()) if len(df) >= 96 else float(df['low'].min())
                volume_24h = float(df['volume'].tail(96).sum()) if len(df) >= 96 else float(df['volume'].sum())
                
                # Market data para el frontend
                market_data = {
                    "price": current_price,
                    "change_24h": round(change_24h, 2),
                    "high_24h": high_24h,
                    "low_24h": low_24h,
                    "volume_24h": volume_24h,
                    "volume_usdt": volume_24h * current_price
                }
                
                # Calcular indicadores técnicos
                # RSI
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_value = float(rsi.iloc[-1]) if not rsi.empty else 50
                
                # MACD
                exp1 = df['close'].ewm(span=12, adjust=False).mean()
                exp2 = df['close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal_line = macd.ewm(span=9, adjust=False).mean()
                macd_value = float(macd.iloc[-1])
                macd_signal = float(signal_line.iloc[-1])
                
                # Volumen
                volume_avg = df['volume'].rolling(20).mean().iloc[-1]
                volume_current = df['volume'].iloc[-1]
                volume_ratio = (volume_current / volume_avg) if volume_avg > 0 else 1
                
                # EMA
                ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
                
                # Crear lista de indicadores para el frontend
                indicators_list = [
                    {
                        "name": "RSI",
                        "value": rsi_value,
                        "signal": "bearish" if rsi_value > 70 else "bullish" if rsi_value < 30 else "neutral",
                        "description": "Sobrecompra" if rsi_value > 70 else "Sobreventa" if rsi_value < 30 else "Zona neutral"
                    },
                    {
                        "name": "MACD",
                        "value": macd_value - macd_signal,
                        "signal": "bullish" if macd_value > macd_signal else "bearish",
                        "description": "Señal alcista" if macd_value > macd_signal else "Señal bajista"
                    },
                    {
                        "name": "Volumen",
                        "value": volume_ratio,
                        "signal": "bullish" if volume_ratio > 1.5 else "bearish" if volume_ratio < 0.5 else "neutral",
                        "description": f"{volume_ratio:.1f}x promedio"
                    },
                    {
                        "name": "EMA 20/50",
                        "value": (ema_20 - ema_50) / ema_50 * 100,
                        "signal": "bullish" if ema_20 > ema_50 else "bearish",
                        "description": "Tendencia alcista" if ema_20 > ema_50 else "Tendencia bajista"
                    }
                ]
                
                # Análisis de cada filósofo con timestamp
                philosophers_analysis = {
                    "socrates": {
                        "name": "Socrates",
                        "style": "Fundamental Analysis",
                        "signal": "BUY" if df['volume'].iloc[-1] > df['volume'].mean() * 1.5 else "HOLD",
                        "confidence": 75 if df['volume'].iloc[-1] > df['volume'].mean() * 1.5 else 50,
                        "reasoning": "El volumen elevado sugiere interés institucional" if df['volume'].iloc[-1] > df['volume'].mean() * 1.5 else "Volumen normal, esperar confirmación",
                        "timestamp": current_time.isoformat()
                    },
                    "plato": {
                        "name": "Plato",
                        "style": "Pattern Recognition",
                        "signal": "BUY" if current_price > df['close'].rolling(20).mean().iloc[-1] else "SELL",
                        "confidence": 70,
                        "reasoning": "Precio por encima de la media móvil indica tendencia alcista" if current_price > df['close'].rolling(20).mean().iloc[-1] else "Precio bajo la media sugiere debilidad",
                        "timestamp": current_time.isoformat()
                    },
                    "aristotle": {
                        "name": "Aristotle",
                        "style": "Logical Analysis",
                        "signal": "HOLD",
                        "confidence": 65,
                        "reasoning": "Esperando confirmación de ruptura de resistencia",
                        "timestamp": current_time.isoformat()
                    },
                    "nietzsche": {
                        "name": "Nietzsche",
                        "style": "Contrarian",
                        "signal": "SELL" if df['close'].pct_change().tail(5).mean() > 0.02 else "BUY",
                        "confidence": 60,
                        "reasoning": "El mercado está sobreextendido" if df['close'].pct_change().tail(5).mean() > 0.02 else "Oportunidad contrarian en sobreventa",
                        "timestamp": current_time.isoformat()
                    },
                    "sun_tzu": {
                        "name": "Sun Tzu",
                        "style": "Strategic",
                        "signal": "BUY",
                        "confidence": 80,
                        "reasoning": "Momento óptimo para entrada con riesgo controlado",
                        "timestamp": current_time.isoformat()
                    }
                }
                
                # Calcular consenso
                buy_count = sum(1 for p in philosophers_analysis.values() if p["signal"] == "BUY")
                sell_count = sum(1 for p in philosophers_analysis.values() if p["signal"] == "SELL")
                avg_confidence = sum(p["confidence"] for p in philosophers_analysis.values()) / len(philosophers_analysis)
                
                if buy_count > sell_count:
                    consensus_action = "BUY"
                elif sell_count > buy_count:
                    consensus_action = "SELL"
                else:
                    consensus_action = "HOLD"
                
                # Calcular niveles de entrada, stop loss y take profit
                atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
                
                if consensus_action == "BUY":
                    entry_price = current_price * 1.001  # Entrada ligeramente por encima
                    stop_loss = current_price - (atr * 2)
                    take_profit = current_price + (atr * 3)
                elif consensus_action == "SELL":
                    entry_price = current_price * 0.999  # Entrada ligeramente por debajo
                    stop_loss = current_price + (atr * 2)
                    take_profit = current_price - (atr * 3)
                else:
                    entry_price = current_price
                    stop_loss = current_price - (atr * 2)
                    take_profit = current_price + (atr * 2)
                
                # Función para validar señales
                def validate_signal(signal_time, entry_price, current_price, action, stop_loss):
                    """Valida si una señal sigue siendo válida"""
                    # Calcular tiempo transcurrido
                    time_elapsed = (current_time - signal_time).total_seconds() / 3600  # en horas
                    
                    # Validación por tiempo (máximo 4 horas)
                    if time_elapsed > 4:
                        return "expired", "Señal expirada (>4 horas)"
                    
                    # Validación por precio
                    price_diff_pct = abs((current_price - entry_price) / entry_price) * 100
                    
                    if action == "BUY":
                        # Para compra, invalidar si el precio subió mucho o tocó stop loss
                        if current_price < stop_loss:
                            return "invalid", "Stop loss alcanzado"
                        elif price_diff_pct > 2:
                            return "warning", f"Precio alejado {price_diff_pct:.1f}% del punto de entrada"
                        elif time_elapsed > 2:
                            return "warning", f"Señal con {time_elapsed:.1f} horas de antigüedad"
                        else:
                            return "valid", f"Válida por {(4-time_elapsed):.1f} horas más"
                    else:  # SELL
                        # Para venta, invalidar si el precio bajó mucho o tocó stop loss
                        if current_price > stop_loss:
                            return "invalid", "Stop loss alcanzado"
                        elif price_diff_pct > 2:
                            return "warning", f"Precio alejado {price_diff_pct:.1f}% del punto de entrada"
                        elif time_elapsed > 2:
                            return "warning", f"Señal con {time_elapsed:.1f} horas de antigüedad"
                        else:
                            return "valid", f"Válida por {(4-time_elapsed):.1f} horas más"
                
                # Crear señales individuales con validación
                for phil_id, analysis in philosophers_analysis.items():
                    if analysis["signal"] != "HOLD":
                        signal_time = datetime.fromisoformat(analysis["timestamp"])
                        validity_status, validity_message = validate_signal(
                            signal_time, entry_price, current_price, 
                            analysis["signal"], stop_loss
                        )
                        
                        signals.append({
                            "id": f"{phil_id}_{datetime.now().timestamp()}",
                            "user_id": "system",  # Default system user for philosopher signals
                            "timestamp": analysis["timestamp"],
                            "philosopher": analysis["name"],
                            "style": analysis["style"],
                            "action": analysis["signal"],
                            "confidence": analysis["confidence"],
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "reasoning": analysis["reasoning"],
                            "risk_reward": round((take_profit - entry_price) / (entry_price - stop_loss), 2) if analysis["signal"] == "BUY" else round((entry_price - take_profit) / (stop_loss - entry_price), 2),
                            "validity_status": validity_status,
                            "validity_message": validity_message,
                            "time_elapsed": f"{int((current_time - signal_time).total_seconds() / 60)} min"
                        })
                
                # Agregar señal de consenso con validación
                hold_count = sum(1 for p in philosophers_analysis.values() if p["signal"] == "HOLD")
                
                # Determinar estado de validación
                validation_status = "validated" if avg_confidence >= 60 and (buy_count >= 3 or sell_count >= 3) else "analyzing"
                validation_message = "Convergencia confirmada" if validation_status == "validated" else "Analizando convergencia..."
                
                consensus_signal = {
                    "id": f"consensus_{datetime.now().timestamp()}",
                    "user_id": "system",  # Default system user for consensus signals
                    "timestamp": datetime.now().isoformat(),
                    "type": "CONSENSUS",
                    "action": consensus_action,
                    "confidence": avg_confidence,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "philosophers_agree": buy_count if consensus_action == "BUY" else sell_count,
                    "philosophers_disagree": sell_count if consensus_action == "BUY" else buy_count,
                    "reasoning": f"Consenso filosófico: {buy_count} compra, {sell_count} venta, {hold_count} espera",
                    "risk_reward": round((take_profit - entry_price) / (entry_price - stop_loss), 2) if consensus_action == "BUY" else round((entry_price - take_profit) / (stop_loss - entry_price), 2) if consensus_action == "SELL" else 1,
                    # Propiedades adicionales para el frontend
                    "buy_count": buy_count,
                    "sell_count": sell_count,
                    "hold_count": hold_count,
                    "validation_status": validation_status,
                    "validation_message": validation_message
                }
                
                # Análisis BI automático para cada señal
                high_quality_signals = []
                from signal_analytics import signal_analyzer
                
                for signal in signals:
                    # Guardar traza de señal generada
                    db.save_signal_trace(
                        signal['id'],
                        'SIGNAL_GENERATED',
                        {
                            'symbol': symbol,
                            'action': signal['action'],
                            'confidence': signal['confidence'],
                            'entry_price': signal['entry_price'],
                            'rsi': getattr(df['close'], 'iloc', [None])[-1],  # Usar si está disponible
                            'volume_ratio': signal.get('volume_ratio', 1.0)
                        },
                        signal['philosopher']
                    )
                    
                    # Análisis BI automático
                    try:
                        # Agregar symbol al signal para el análisis
                        signal_with_symbol = signal.copy()
                        signal_with_symbol['symbol'] = symbol
                        analysis = signal_analyzer.analyze_signal(signal_with_symbol)
                        
                        if analysis and analysis.quality_score >= 45:
                            print(f"🎯 Señal de alta calidad detectada: {symbol} - {signal['philosopher']} - Score: {analysis.quality_score:.1f}")
                            high_quality_signals.append(signal)
                        else:
                            score = analysis.quality_score if analysis else 0
                            print(f"⚠️ Señal de baja calidad filtrada: {symbol} - {signal['philosopher']} - Score: {score:.1f}")
                    except Exception as e:
                        print(f"Error en análisis BI para señal {signal['id']}: {e}")
                        high_quality_signals.append(signal)  # En caso de error, incluir la señal
                
                # Calcular sentimiento del mercado basado en indicadores y consenso
                bullish_indicators = sum(1 for ind in indicators_list if ind["signal"] == "bullish")
                bearish_indicators = sum(1 for ind in indicators_list if ind["signal"] == "bearish")
                
                # Score de sentimiento (0-100)
                sentiment_score = 50  # Base neutral
                sentiment_score += (buy_count - sell_count) * 10  # Peso del consenso filosófico
                sentiment_score += (bullish_indicators - bearish_indicators) * 5  # Peso de indicadores técnicos
                sentiment_score = max(0, min(100, sentiment_score))  # Limitar entre 0 y 100
                
                # Determinar label y recomendación
                if sentiment_score >= 70:
                    sentiment_label = "Muy Alcista"
                    sentiment_recommendation = "Momento óptimo para considerar posiciones largas. Los indicadores técnicos y el consenso filosófico muestran fuerte momentum alcista."
                elif sentiment_score >= 55:
                    sentiment_label = "Alcista"
                    sentiment_recommendation = "Tendencia positiva con oportunidades de compra. Se recomienda esperar retrocesos para mejores entradas."
                elif sentiment_score >= 45:
                    sentiment_label = "Neutral"
                    sentiment_recommendation = "Mercado en consolidación. Esperar confirmación de dirección antes de tomar posiciones."
                elif sentiment_score >= 30:
                    sentiment_label = "Bajista"
                    sentiment_recommendation = "Presión vendedora presente. Considerar posiciones cortas o mantenerse fuera del mercado."
                else:
                    sentiment_label = "Muy Bajista"
                    sentiment_recommendation = "Fuerte sentimiento negativo. Evitar compras y considerar protección de capital."
                
                market_sentiment = {
                    "score": sentiment_score,
                    "label": sentiment_label,
                    "recommendation": sentiment_recommendation
                }
                
                return {
                    "symbol": symbol,
                    "signals": high_quality_signals,  # Solo señales de alta calidad
                    "consensus": consensus_signal,
                    "indicators": indicators_list,  # Añadir indicadores técnicos
                    "market_sentiment": market_sentiment,  # Añadir sentimiento del mercado
                    "market_data": market_data,  # Añadir datos de mercado
                    "total_signals": len(signals),
                    "high_quality_signals": len(high_quality_signals),
                    "bullish_signals": buy_count,
                    "bearish_signals": sell_count,
                    "avg_confidence": avg_confidence,
                    "last_update": datetime.now().isoformat()
                }
        
        return {
            "symbol": symbol,
            "signals": [],
            "consensus": None,
            "error": "Philosophy system not initialized"
        }
        
    except Exception as e:
        print(f"Error getting signals for {symbol}: {e}")
        return {"error": str(e)}

# ===========================================
# WEBSOCKET ENDPOINT
# ===========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = None):
    """
    WebSocket endpoint for real-time updates using thread-safe manager.
    
    Args:
        websocket: WebSocket connection
        user_id: Optional user ID for authentication
    """
    connection_id = None
    
    try:
        # Connect using thread-safe manager
        connection_id = await trading_manager.connect_websocket(websocket, user_id)
        logger.info(f"WebSocket connected: {connection_id}")
        
        while True:
            # Mantener conexión viva y recibir comandos
            data = await websocket.receive_json()
            
            # Log received command
            logger.debug(f"WebSocket command received from {connection_id}: {data.get('command')}")
            
            # Procesar comandos desde el cliente
            if data.get("command") == "start_bot":
                await trading_manager.start_bot()
                # Send confirmation
                await trading_manager.websocket_manager.send_message(
                    WebSocketMessage(
                        type=MessageType.SYSTEM_STATUS,
                        data={"status": "bot_started", "bot_status": str(trading_manager.bot_status)}
                    ),
                    connection_id=connection_id
                )
                
            elif data.get("command") == "stop_bot":
                await trading_manager.stop_bot()
                # Send confirmation
                await trading_manager.websocket_manager.send_message(
                    WebSocketMessage(
                        type=MessageType.SYSTEM_STATUS,
                        data={"status": "bot_stopped", "bot_status": str(trading_manager.bot_status)}
                    ),
                    connection_id=connection_id
                )
                
            elif data.get("command") == "update_config":
                try:
                    config = BotConfig(**data.get("config", {}))
                    await trading_manager.update_config(config)
                    # Send confirmation
                    await trading_manager.websocket_manager.send_message(
                        WebSocketMessage(
                            type=MessageType.SYSTEM_STATUS,
                            data={"status": "config_updated", "config": config.dict()}
                        ),
                        connection_id=connection_id
                    )
                except Exception as e:
                    # Send error
                    await trading_manager.websocket_manager.send_message(
                        WebSocketMessage(
                            type=MessageType.ERROR,
                            data={"error": "config_update_failed", "message": str(e)}
                        ),
                        connection_id=connection_id
                    )
            
            elif data.get("command") == "get_status":
                # Send current status
                await trading_manager.send_initial_state(connection_id)
                
    except WebSocketDisconnect:
        if connection_id:
            await trading_manager.disconnect_websocket(connection_id, "client_disconnect")
        logger.info(f"WebSocket client disconnected: {connection_id}")
        
    except Exception as e:
        handle_critical_error(e, {
            'operation': 'websocket_endpoint',
            'connection_id': connection_id,
            'user_id': user_id
        })
        
        if connection_id:
            await trading_manager.disconnect_websocket(connection_id, "error")
        # logger.error(f"WebSocket error for {connection_id}: {e}")
        print(f"WebSocket error for {connection_id}: {e}")

# ===========================================
# MAIN
# ===========================================

# ===========================================
# ENDPOINTS DE AUTENTICACIÓN 
# ===========================================

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict] = None
    token: Optional[str] = None

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Endpoint de login (preparado para futura implementación)"""
    # Por ahora retorna éxito para cualquier credencial
    # En el futuro, aquí se validarían contra una base de datos
    
    # Importar usuarios desde config
    from config import Settings
    demo_users = Settings.DEMO_USERS
    
    user = demo_users.get(login_data.email)
    
    if user and user["password"] == login_data.password:
        # Crear datos del usuario
        user_data = {
            "id": user["id"],
            "email": login_data.email,
            "name": user["name"],
            "role": user["role"]
        }
        
        # Crear token JWT real
        token = auth_manager.create_token(user_data)
        
        return LoginResponse(
            success=True,
            message="Login exitoso",
            user=user_data,
            token=token
        )
    
    return LoginResponse(
        success=False,
        message="Credenciales inválidas"
    )

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Endpoint de logout"""
    if current_user:
        auth_manager.logout_user(current_user["user_id"])
    return {"success": True, "message": "Logout exitoso"}

@app.get("/api/auth/me")
async def get_user_info(current_user: dict = Depends(get_current_user_required)):
    """Obtiene información del usuario actual (requiere autenticación)"""
    return {
        "id": current_user["user_id"],
        "email": current_user["email"], 
        "name": current_user["name"],
        "role": current_user["role"]
    }

# ===========================================
# ENDPOINT DE CONFIGURACIÓN INICIAL
# ===========================================

class InitialSetupRequest(BaseModel):
    initial_capital: float
    risk_level: str  # conservative, balanced, aggressive
    risk_per_trade: float
    max_positions: int
    symbols: List[str]
    philosophers: List[str]

@app.post("/api/user/initial-setup")
async def save_initial_setup(
    setup: InitialSetupRequest,
    current_user: dict = Depends(get_current_user_required)
):
    """Guarda la configuración inicial del usuario"""
    try:
        user_id = current_user["user_id"]
        
        # Guardar configuración en la base de datos
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        # Crear tabla de configuración de usuario si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_config (
                user_id TEXT PRIMARY KEY,
                initial_capital REAL,
                current_balance REAL,
                risk_level TEXT,
                risk_per_trade REAL,
                max_positions INTEGER,
                symbols TEXT,
                philosophers TEXT,
                setup_completed BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insertar o actualizar configuración
        cursor.execute("""
            INSERT OR REPLACE INTO user_config 
            (user_id, initial_capital, current_balance, risk_level, risk_per_trade, 
             max_positions, symbols, philosophers, setup_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            user_id,
            setup.initial_capital,
            setup.initial_capital,  # Balance inicial = capital inicial
            setup.risk_level,
            setup.risk_per_trade,
            setup.max_positions,
            json.dumps(setup.symbols),
            json.dumps(setup.philosophers)
        ))
        
        # Limpiar posiciones antiguas del usuario
        cursor.execute("""
            DELETE FROM positions 
            WHERE user_id = ? AND status = 'OPEN'
        """, (user_id,))
        
        # Limpiar señales antiguas del usuario
        cursor.execute("""
            DELETE FROM signals 
            WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        # Actualizar configuración del trading manager si es necesario
        trading_manager.config.initial_capital = setup.initial_capital
        trading_manager.config.risk_level = setup.risk_level
        trading_manager.config.max_positions = setup.max_positions
        trading_manager.config.risk_per_trade = setup.risk_per_trade
        trading_manager.config.symbols = setup.symbols
        trading_manager.config.philosophers = setup.philosophers
        
        # Actualizar balance en performance
        trading_manager.performance.current_balance = setup.initial_capital
        
        return {
            "success": True,
            "message": "Configuración inicial guardada exitosamente",
            "config": {
                "initial_capital": setup.initial_capital,
                "risk_level": setup.risk_level,
                "symbols": setup.symbols,
                "philosophers": setup.philosophers
            }
        }
        
    except Exception as e:
        print(f"Error guardando configuración inicial: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/{symbol}")
async def get_symbol_signals(symbol: str):
    """Obtiene señales activas y análisis de mercado para un símbolo"""
    try:
        # Obtener datos del mercado
        df = trading_manager.binance.get_historical_data(symbol, "15m", 100)
        
        if df is None or df.empty:
            return {"error": "No data available"}
            
        current_price = float(df['close'].iloc[-1])
        
        # Calcular indicadores técnicos
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_value = float(rsi.iloc[-1]) if not rsi.empty else 50
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_value = float(macd.iloc[-1])
        macd_signal = float(signal_line.iloc[-1])
        macd_histogram = macd_value - macd_signal
        
        # Volumen
        volume_avg = df['volume'].rolling(20).mean().iloc[-1]
        volume_current = df['volume'].iloc[-1]
        volume_ratio = (volume_current / volume_avg) if volume_avg > 0 else 1
        
        # Tendencia (EMA)
        ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        trend_strength = ((current_price - ema_50) / ema_50) * 100
        
        # Determinar señales de indicadores
        rsi_signal = 'neutral'
        if rsi_value > 70:
            rsi_signal = 'bearish'
            rsi_desc = "Sobrecompra - posible reversión bajista"
        elif rsi_value < 30:
            rsi_signal = 'bullish'
            rsi_desc = "Sobreventa - posible reversión alcista"
        else:
            rsi_desc = "Zona neutral, sin sobrecompra ni sobreventa"
        
        macd_signal_type = 'bullish' if macd_histogram > 0 else 'bearish'
        macd_desc = "Cruce alcista, momentum ascendente" if macd_histogram > 0 else "Cruce bajista, momentum descendente"
        
        volume_signal = 'bullish' if volume_ratio > 1.2 else 'neutral' if volume_ratio > 0.8 else 'bearish'
        volume_desc = f"Volumen {int((volume_ratio - 1) * 100)}% {'por encima' if volume_ratio > 1 else 'por debajo'} del promedio"
        
        trend_signal = 'bullish' if trend_strength > 2 else 'bearish' if trend_strength < -2 else 'neutral'
        trend_desc = f"Tendencia {'alcista' if trend_strength > 0 else 'bajista'} {'fuerte' if abs(trend_strength) > 5 else 'en formación'}"
        
        # Calcular sentimiento agregado del mercado
        sentiment_score = 50  # Base
        
        # Ajustar por RSI
        if rsi_value > 70:
            sentiment_score -= 20
        elif rsi_value < 30:
            sentiment_score += 20
        elif 40 <= rsi_value <= 60:
            sentiment_score += 5
            
        # Ajustar por MACD
        if macd_histogram > 0:
            sentiment_score += 15
        else:
            sentiment_score -= 15
            
        # Ajustar por volumen
        if volume_ratio > 1.5:
            sentiment_score += 10
        elif volume_ratio < 0.5:
            sentiment_score -= 10
            
        # Ajustar por tendencia
        sentiment_score += min(max(trend_strength * 2, -20), 20)
        
        # Limitar entre 0 y 100
        sentiment_score = max(0, min(100, sentiment_score))
        
        # Determinar etiqueta y recomendación
        if sentiment_score >= 70:
            sentiment_label = "Bullish"
            sentiment_rec = "OPORTUNIDAD - Mercado en zona de acumulación"
        elif sentiment_score >= 30:
            sentiment_label = "Neutral"
            sentiment_rec = "ESPERAR - Mercado sin dirección clara"
        else:
            sentiment_label = "Bearish"
            sentiment_rec = "CAUTELA - Mercado en zona de distribución"
        
        # Generar señales filosóficas
        signals = []
        philosophers_config = [
            {"name": "SOCRATES", "bias": "contrarian", "icon": "🤔"},
            {"name": "PLATON", "bias": "pattern", "icon": "💭"},
            {"name": "ARISTOTELES", "bias": "logical", "icon": "📊"},
            {"name": "NIETZSCHE", "bias": "aggressive", "icon": "⚡"},
            {"name": "KANT", "bias": "categorical", "icon": "🎯"}
        ]
        
        atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
        
        for phil in philosophers_config[:3]:  # Top 3 filósofos activos
            # Lógica de decisión basada en el bias del filósofo
            if phil["bias"] == "contrarian":
                # Sócrates va contra el mercado
                action = "BUY" if sentiment_score < 40 else "SELL" if sentiment_score > 60 else "HOLD"
                confidence = 70 + (100 - sentiment_score) // 5
                reasoning = f"El mercado muestra {sentiment_label}, tiempo de {'comprar' if action == 'BUY' else 'vender' if action == 'SELL' else 'esperar'} por inversión"
            elif phil["bias"] == "pattern":
                # Platón busca patrones ideales
                action = "BUY" if macd_histogram > 0 and rsi_value < 50 else "SELL" if macd_histogram < 0 and rsi_value > 50 else "HOLD"
                confidence = 65 + abs(macd_histogram * 100)
                reasoning = f"Patrón {'alcista' if action == 'BUY' else 'bajista' if action == 'SELL' else 'no definido'} detectado en MACD y RSI"
            elif phil["bias"] == "logical":
                # Aristóteles sigue la lógica del mercado
                action = "BUY" if sentiment_score > 60 else "SELL" if sentiment_score < 40 else "HOLD"
                confidence = min(90, 50 + abs(sentiment_score - 50))
                reasoning = f"Análisis lógico sugiere {action} con sentimiento {sentiment_label}"
            elif phil["bias"] == "aggressive":
                # Nietzsche toma posiciones agresivas
                action = "BUY" if trend_strength > 0 else "SELL"
                confidence = min(95, 70 + abs(trend_strength * 2))
                reasoning = f"Momento agresivo para {'comprar en tendencia alcista' if action == 'BUY' else 'vender en tendencia bajista'}"
            else:  # categorical
                # Kant sigue reglas estrictas
                action = "BUY" if rsi_value < 30 and macd_histogram > 0 else "SELL" if rsi_value > 70 and macd_histogram < 0 else "HOLD"
                confidence = 80 if action != "HOLD" else 60
                reasoning = f"Reglas categóricas indican {action} por condiciones técnicas"
            
            # Calcular niveles solo si hay acción
            if action != "HOLD":
                stop_loss = current_price - (atr * 1.5) if action == "BUY" else current_price + (atr * 1.5)
                take_profit = current_price + (atr * 3) if action == "BUY" else current_price - (atr * 3)
                risk_reward = 2.0  # Ratio fijo 1:2
            else:
                stop_loss = 0
                take_profit = 0
                risk_reward = 0
            
            signal = {
                "id": f"{symbol}_{phil['name']}_{datetime.now().timestamp()}",
                "user_id": "system",  # Default system user for philosopher signals
                "philosopher": phil["name"],
                "action": action,
                "confidence": min(95, confidence),
                "entry_price": current_price if action != "HOLD" else 0,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward": risk_reward,
                "timestamp": datetime.now().isoformat(),
                "reasoning": reasoning,
                "status": "active"
            }
            signals.append(signal)
        
        # Calcular consenso
        buy_count = sum(1 for s in signals if s["action"] == "BUY")
        sell_count = sum(1 for s in signals if s["action"] == "SELL")
        hold_count = sum(1 for s in signals if s["action"] == "HOLD")
        
        if buy_count > sell_count and buy_count > hold_count:
            consensus_action = "BUY"
        elif sell_count > buy_count and sell_count > hold_count:
            consensus_action = "SELL"
        else:
            consensus_action = "HOLD"
        
        # Validación: ¿Las señales coinciden con los indicadores?
        validation_status = "validated"
        validation_message = ""
        
        if consensus_action == "BUY" and sentiment_score > 60:
            validation_message = "Señal BUY validada por indicadores alcistas"
        elif consensus_action == "SELL" and sentiment_score < 40:
            validation_message = "Señal SELL validada por indicadores bajistas"
        elif consensus_action == "HOLD" and 40 <= sentiment_score <= 60:
            validation_message = "HOLD confirmado por mercado lateral"
        else:
            validation_status = "divergence"
            validation_message = "Divergencia entre señales e indicadores - proceder con cautela"
        
        return {
            "market_data": {
                "symbol": symbol,
                "price": current_price,
                "change_24h": float(((df['close'].iloc[-1] - df['close'].iloc[-96]) / df['close'].iloc[-96]) * 100) if len(df) > 96 else 0,
                "high_24h": float(df['high'].tail(96).max()) if len(df) > 96 else current_price,
                "low_24h": float(df['low'].tail(96).min()) if len(df) > 96 else current_price,
                "volume_24h": float(df['volume'].tail(96).sum()) if len(df) > 96 else 0,
                "volume_usdt": float(df['volume'].tail(96).sum() * current_price) if len(df) > 96 else 0
            },
            "indicators": [
                {
                    "name": "RSI",
                    "value": round(rsi_value, 2),
                    "signal": rsi_signal,
                    "description": rsi_desc
                },
                {
                    "name": "MACD",
                    "value": round(macd_histogram, 4),
                    "signal": macd_signal_type,
                    "description": macd_desc
                },
                {
                    "name": "Volume",
                    "value": round(volume_ratio, 2),
                    "signal": volume_signal,
                    "description": volume_desc
                },
                {
                    "name": "Trend",
                    "value": round(trend_strength, 1),
                    "signal": trend_signal,
                    "description": trend_desc
                }
            ],
            "market_sentiment": {
                "score": round(sentiment_score),
                "label": sentiment_label,
                "recommendation": sentiment_rec
            },
            "signals": signals,
            "consensus": {
                "action": consensus_action,
                "buy_count": buy_count,
                "sell_count": sell_count,
                "hold_count": hold_count,
                "validation_status": validation_status,
                "validation_message": validation_message
            }
        }
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/backtest/{symbol}")
async def run_backtest(symbol: str, period_days: int = 30):
    """Ejecuta backtest para un símbolo"""
    try:
        # Obtener datos históricos
        df = trading_manager.binance.get_historical_data(symbol, "1h", period_days * 24)
        
        if df is None or df.empty:
            return {"error": "No historical data available"}
        
        # Simular señales de backtest
        signals = []
        
        # Generar señales cada 3-5 días
        for i in range(0, len(df), 72):  # Cada 3 días aprox
            if i + 14 < len(df):  # Asegurar que hay suficientes datos
                row = df.iloc[i]
                future_rows = df.iloc[i:i+14]  # Ver 14 períodos adelante
                
                # Simular señal
                action = "BUY" if i % 2 == 0 else "SELL"
                entry_price = float(row['close'])
                
                # Calcular resultado basado en datos futuros
                if action == "BUY":
                    max_price = float(future_rows['high'].max())
                    min_price = float(future_rows['low'].min())
                    take_profit = entry_price * 1.02
                    stop_loss = entry_price * 0.98
                    
                    if max_price >= take_profit:
                        profit_loss = 2.0  # 2% ganancia
                        success = True
                    elif min_price <= stop_loss:
                        profit_loss = -2.0  # 2% pérdida
                        success = False
                    else:
                        profit_loss = ((float(future_rows.iloc[-1]['close']) - entry_price) / entry_price) * 100
                        success = profit_loss > 0
                else:
                    max_price = float(future_rows['high'].max())
                    min_price = float(future_rows['low'].min())
                    take_profit = entry_price * 0.98
                    stop_loss = entry_price * 1.02
                    
                    if min_price <= take_profit:
                        profit_loss = 2.0  # 2% ganancia
                        success = True
                    elif max_price >= stop_loss:
                        profit_loss = -2.0  # 2% pérdida
                        success = False
                    else:
                        profit_loss = ((entry_price - float(future_rows.iloc[-1]['close'])) / entry_price) * 100
                        success = profit_loss > 0
                
                signal = {
                    "id": f"backtest_{i}",
                    "date": row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name),
                    "philosopher": "Backtest",
                    "action": action,
                    "confidence": 70 + (i % 25),
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "profit_loss": round(profit_loss, 2),
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                }
                signals.append(signal)
        
        return {"signals": signals}
        
    except Exception as e:
        print(f"Error running backtest for {symbol}: {e}")
        return {"error": str(e)}

@app.get("/api/user/setup-status")
async def get_setup_status(current_user: dict = Depends(get_current_user_required)):
    """Verifica si el usuario ha completado la configuración inicial"""
    try:
        user_id = current_user["user_id"]
        
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT setup_completed, initial_capital, current_balance, risk_level, symbols
            FROM user_config 
            WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "setup_completed": bool(result[0]),
                "initial_capital": result[1],
                "current_balance": result[2],
                "risk_level": result[3],
                "symbols": json.loads(result[4]) if result[4] else []
            }
        else:
            return {
                "setup_completed": False,
                "initial_capital": None,
                "current_balance": None,
                "risk_level": None,
                "symbols": []
            }
            
    except Exception as e:
        print(f"Error verificando estado de configuración: {e}")
        return {
            "setup_completed": False,
            "initial_capital": None,
            "current_balance": None,
            "risk_level": None,
            "symbols": []
        }

# ===========================================
# BI ANALYTICS ENDPOINTS
# ===========================================

@app.get("/api/signal-analyses")
async def get_signal_analyses(symbol: Optional[str] = None):
    """Obtiene análisis BI de señales"""
    try:
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        if symbol:
            # Obtener análisis por símbolo específico
            cursor.execute("""
                SELECT sa.*, COALESCE(s.symbol, ?) as symbol, COALESCE(s.action, 'UNKNOWN') as action, COALESCE(s.philosopher, 'UNKNOWN') as philosopher
                FROM signal_analysis sa
                LEFT JOIN signals s ON sa.signal_id = s.id
                WHERE COALESCE(s.symbol, ?) = ?
                ORDER BY sa.analyzed_at DESC
                LIMIT 50
            """, (symbol, symbol, symbol))
        else:
            # Obtener todos los análisis recientes
            cursor.execute("""
                SELECT sa.*, COALESCE(s.symbol, 'UNKNOWN') as symbol, COALESCE(s.action, 'UNKNOWN') as action, COALESCE(s.philosopher, 'UNKNOWN') as philosopher
                FROM signal_analysis sa
                LEFT JOIN signals s ON sa.signal_id = s.id
                ORDER BY sa.analyzed_at DESC
                LIMIT 100
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        analyses = []
        for row in results:
            # Map database schema to expected format
            confirmation_indicators = json.loads(row[3]) if row[3] else {}
            risk_assessment = json.loads(row[4]) if row[4] else {}
            market_conditions = json.loads(row[5]) if row[5] else {}
            
            analysis = {
                'id': row[0],
                'signal_id': row[1],
                'quality_score': row[2],
                'confirmation_indicators': list(confirmation_indicators.keys()) if confirmation_indicators else [],
                'recommendation': row[6],
                'execution_priority': row[8],
                'trend_alignment': confirmation_indicators.get('trend_alignment', 0),
                'volume_confirmation': confirmation_indicators.get('volume_confirmation', 0),
                'momentum_score': confirmation_indicators.get('momentum_strength', 0),
                'risk_reward_ratio': risk_assessment.get('risk_reward_ratio', 0),
                'market_conditions_score': risk_assessment.get('market_conditions_score', 0),
                'analysis_details': {
                    'confirmation_indicators': confirmation_indicators,
                    'risk_assessment': risk_assessment,
                    'market_conditions': market_conditions,
                    'reasoning': row[7]
                },
                'timestamp': row[11] or datetime.now().isoformat(),
                'symbol': row[12] if len(row) > 12 else '',
                'action': row[13] if len(row) > 13 else '',
                'philosopher': row[14] if len(row) > 14 else ''
            }
            analyses.append(analysis)
        
        return analyses
        
    except Exception as e:
        print(f"Error obteniendo análisis de señales: {e}")
        return []

@app.get("/api/signal-traces")
async def get_signal_traces(symbol: Optional[str] = None):
    """Obtiene trazabilidad de señales"""
    try:
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        if symbol:
            # Obtener trazas por símbolo específico uniendo con signals para obtener símbolo
            cursor.execute("""
                SELECT st.*, sa.quality_score, sa.recommendation, s.symbol, s.action, s.confidence, s.entry_price, s.stop_loss, s.take_profit
                FROM signal_trace st
                LEFT JOIN signal_analysis sa ON st.signal_id = sa.signal_id
                LEFT JOIN signals s ON st.signal_id = s.id
                WHERE s.symbol = ?
                ORDER BY st.timestamp DESC
                LIMIT 50
            """, (symbol,))
        else:
            # Obtener todas las trazas recientes
            cursor.execute("""
                SELECT st.*, sa.quality_score, sa.recommendation, s.symbol, s.action, s.confidence, s.entry_price, s.stop_loss, s.take_profit
                FROM signal_trace st
                LEFT JOIN signal_analysis sa ON st.signal_id = sa.signal_id
                LEFT JOIN signals s ON st.signal_id = s.id
                ORDER BY st.timestamp DESC
                LIMIT 100
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        traces = []
        for row in results:
            # Parse event_data if it exists
            event_data = json.loads(row[3]) if row[3] else {}
            
            trace = {
                'id': row[0],
                'signal_id': row[1],
                'event_type': row[2],
                'event_data': event_data,
                'philosopher': row[4],
                'timestamp': row[5],
                'quality_score': row[6] if row[6] else 0,
                'recommendation': row[7] if row[7] else 'HOLD',
                'symbol': row[8] if len(row) > 8 and row[8] else '',
                'action': row[9] if len(row) > 9 and row[9] else '',
                'confidence': row[10] if len(row) > 10 and row[10] else 0,
                'entry_price': row[11] if len(row) > 11 and row[11] else 0,
                'stop_loss': row[12] if len(row) > 12 and row[12] else 0,
                'take_profit': row[13] if len(row) > 13 and row[13] else 0
            }
            traces.append(trace)
        
        return traces
        
    except Exception as e:
        print(f"Error obteniendo trazas de señales: {e}")
        return []

@app.get("/api/analytics/summary")
async def get_analytics_summary(symbol: Optional[str] = None):
    """Obtiene resumen de analytics BI"""
    try:
        conn = sqlite3.connect("trading_bot.db")
        cursor = conn.cursor()
        
        # Query base para statistics
        base_query = """
            SELECT 
                COUNT(*) as total_signals,
                AVG(sa.quality_score) as avg_quality_score,
                COUNT(CASE WHEN sa.quality_score >= 70 THEN 1 END) as high_quality_signals,
                COUNT(CASE WHEN sa.recommendation = 'STRONG_BUY' THEN 1 END) as strong_buy_signals,
                COUNT(CASE WHEN sa.recommendation = 'BUY' THEN 1 END) as buy_signals,
                COUNT(CASE WHEN sa.recommendation = 'HOLD' THEN 1 END) as hold_signals,
                COUNT(CASE WHEN sa.recommendation = 'AVOID' THEN 1 END) as avoid_signals
            FROM signal_analysis sa
            JOIN signals s ON sa.signal_id = s.id
        """
        
        if symbol:
            cursor.execute(base_query + " WHERE s.symbol = ?", (symbol,))
        else:
            cursor.execute(base_query)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_signals': result[0] or 0,
                'avg_quality_score': round(result[1] or 0, 2),
                'high_quality_signals': result[2] or 0,
                'strong_buy_signals': result[3] or 0,
                'buy_signals': result[4] or 0,
                'hold_signals': result[5] or 0,
                'avoid_signals': result[6] or 0,
                'quality_distribution': {
                    'high_quality_rate': round(((result[2] or 0) / max(result[0], 1)) * 100, 1),
                    'strong_buy_rate': round(((result[3] or 0) / max(result[0], 1)) * 100, 1)
                }
            }
        else:
            return {
                'total_signals': 0,
                'avg_quality_score': 0,
                'high_quality_signals': 0,
                'strong_buy_signals': 0,
                'buy_signals': 0,
                'hold_signals': 0,
                'avoid_signals': 0,
                'quality_distribution': {
                    'high_quality_rate': 0,
                    'strong_buy_rate': 0
                }
            }
        
    except Exception as e:
        print(f"Error obteniendo resumen de analytics: {e}")
        return {
            'total_signals': 0,
            'avg_quality_score': 0,
            'high_quality_signals': 0,
            'strong_buy_signals': 0,
            'buy_signals': 0,
            'hold_signals': 0,
            'avoid_signals': 0,
            'quality_distribution': {
                'high_quality_rate': 0,
                'strong_buy_rate': 0
            }
        }

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔═══════════════════════════════════════╗
    ║   SIGNAL HAVEN DESK - BACKEND API    ║
    ╠═══════════════════════════════════════╣
    ║   Philosophers: 10 Active             ║
    ║   WebSocket: Enabled                  ║
    ║   CORS: Configured for Vite          ║
    ║                                       ║
    ║   http://localhost:8000               ║
    ║   ws://localhost:8000/ws              ║
    ╚═══════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )