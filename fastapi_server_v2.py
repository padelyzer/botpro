#!/usr/bin/env python3
"""
FASTAPI SERVER V2 - CON SISTEMA HÍBRIDO
Backend actualizado con sistema de trading híbrido
Funciona con o sin API keys
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# Sistema de trading híbrido
from smart_trading_system import get_trading_system, TradingSignal
from signal_worker import SignalWorker
from websocket_manager import get_websocket_manager
from auth_manager import auth_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================
# MODELOS DE DATOS
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
# LIFESPAN MANAGER
# ===========================================

signal_worker_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionar el ciclo de vida de la aplicación"""
    global signal_worker_task
    
    # Startup
    logger.info("🚀 Starting FastAPI server...")
    
    # Inicializar sistema de trading
    trading_system = get_trading_system()
    logger.info(f"Trading system initialized in {trading_system.mode} mode")
    
    # Iniciar signal worker en background
    signal_worker = SignalWorker()
    signal_worker_task = asyncio.create_task(signal_worker.start())
    logger.info("Signal worker started")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    if signal_worker_task:
        signal_worker_task.cancel()
        try:
            await signal_worker_task
        except asyncio.CancelledError:
            pass

# ===========================================
# APLICACIÓN FASTAPI
# ===========================================

app = FastAPI(
    title="BotPhia Trading API V2",
    description="Sistema de trading híbrido con 8 filósofos",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
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
    
    token = authorization.split(' ')[1]
    user_data = auth_manager.verify_token(token)
    return user_data

async def get_current_user_required(authorization: str = Header(None)):
    """Obtener usuario actual (requerido)"""
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return user

# ===========================================
# ENDPOINTS DE AUTENTICACIÓN
# ===========================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login de usuario"""
    try:
        # Para demo, aceptar cualquier login
        if request.email and request.password:
            user_data = {
                'id': 'default_user',
                'email': request.email,
                'name': request.email.split('@')[0],
                'role': 'trader'
            }
            
            token = auth_manager.create_token(user_data)
            
            return {
                'success': True,
                'message': 'Login exitoso',
                'user': user_data,
                'token': token
            }
        else:
            return {
                'success': False,
                'message': 'Credenciales inválidas'
            }
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/logout")
async def logout(user=Depends(get_current_user_optional)):
    """Logout de usuario"""
    if user:
        auth_manager.logout_user(user['user_id'])
    return {'success': True, 'message': 'Logout exitoso'}

# ===========================================
# ENDPOINTS DE ESTADO
# ===========================================

@app.get("/api/status")
async def get_status():
    """Obtener estado del sistema"""
    trading_system = get_trading_system()
    return {
        'status': 'online',
        'mode': trading_system.mode,
        'running': trading_system.is_running,
        'timestamp': datetime.now().isoformat()
    }

@app.get("/api/bot/status")
async def get_bot_status(user=Depends(get_current_user_optional)):
    """Obtener estado del bot"""
    trading_system = get_trading_system()
    return trading_system.get_status()

@app.post("/api/bot/start")
async def start_bot(user=Depends(get_current_user_required)):
    """Iniciar bot de trading"""
    trading_system = get_trading_system()
    trading_system.start()
    return {'success': True, 'message': 'Bot iniciado'}

@app.post("/api/bot/stop")
async def stop_bot(user=Depends(get_current_user_required)):
    """Detener bot de trading"""
    trading_system = get_trading_system()
    trading_system.stop()
    return {'success': True, 'message': 'Bot detenido'}

# ===========================================
# ENDPOINTS DE PORTFOLIO
# ===========================================

@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio(user=Depends(get_current_user_optional)):
    """Obtener portfolio del usuario"""
    trading_system = get_trading_system()
    user_id = user['user_id'] if user else 'default'
    
    portfolio = trading_system.get_portfolio(user_id)
    
    return PortfolioResponse(
        balance=portfolio.current_balance,
        initial_balance=portfolio.initial_balance,
        total_pnl=portfolio.total_pnl,
        total_pnl_percentage=portfolio.total_pnl_percentage,
        open_positions=portfolio.open_positions,
        total_trades=portfolio.total_trades,
        winning_trades=portfolio.winning_trades,
        losing_trades=portfolio.losing_trades,
        win_rate=portfolio.win_rate,
        mode=portfolio.mode
    )

@app.get("/api/performance")
async def get_performance(user=Depends(get_current_user_optional)):
    """Obtener métricas de rendimiento"""
    trading_system = get_trading_system()
    user_id = user['user_id'] if user else 'default'
    
    portfolio = trading_system.get_portfolio(user_id)
    
    return {
        'balance': portfolio.current_balance,
        'total_pnl': portfolio.total_pnl,
        'daily_pnl': 0,  # TODO: Calcular PnL diario
        'open_pnl': 0,  # TODO: Calcular PnL abierto
        'win_rate': portfolio.win_rate,
        'total_trades': portfolio.total_trades,
        'winning_trades': portfolio.winning_trades,
        'losing_trades': portfolio.losing_trades
    }

# ===========================================
# ENDPOINTS DE POSICIONES
# ===========================================

@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions(user=Depends(get_current_user_optional)):
    """Obtener posiciones abiertas"""
    trading_system = get_trading_system()
    user_id = user['user_id'] if user else 'default'
    
    positions = trading_system.get_positions(user_id, "OPEN")
    
    return [
        PositionResponse(
            id=pos.id,
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            current_price=pos.current_price,
            quantity=pos.quantity,
            pnl=pos.pnl,
            pnl_percentage=pos.pnl_percentage,
            status=pos.status,
            philosopher=pos.philosopher
        )
        for pos in positions
    ]

@app.post("/api/positions/{position_id}/close")
async def close_position(position_id: str, user=Depends(get_current_user_required)):
    """Cerrar una posición"""
    trading_system = get_trading_system()
    
    success = trading_system.engine.close_position(position_id)
    
    if success:
        return {'success': True, 'message': 'Posición cerrada'}
    else:
        raise HTTPException(status_code=404, detail="Posición no encontrada")

# ===========================================
# ENDPOINTS DE SEÑALES
# ===========================================

@app.get("/api/signals/active", response_model=List[SignalResponse])
async def get_active_signals(user=Depends(get_current_user_optional)):
    """Obtener señales activas"""
    trading_system = get_trading_system()
    
    # Obtener últimas señales de la base de datos
    cursor = trading_system.engine.db_connection.cursor()
    cursor.execute('''
        SELECT * FROM signals 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''')
    
    signals = []
    for row in cursor.fetchall():
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
            reasoning=json.loads(row[9]) if row[9] else []
        ))
    
    return signals

@app.post("/api/signals/{signal_id}/execute")
async def execute_signal(signal_id: str, user=Depends(get_current_user_required)):
    """Ejecutar una señal manualmente"""
    trading_system = get_trading_system()
    user_id = user['user_id']
    
    # Obtener señal de la base de datos
    cursor = trading_system.engine.db_connection.cursor()
    cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    
    # Crear objeto TradingSignal
    signal = TradingSignal(
        id=row[0],
        timestamp=datetime.fromisoformat(row[1]),
        symbol=row[2],
        action=row[3],
        philosopher=row[4],
        confidence=row[5],
        entry_price=row[6],
        stop_loss=row[7],
        take_profit=row[8],
        reasoning=json.loads(row[9]) if row[9] else [],
        risk_reward=row[10],
        metadata=json.loads(row[11]) if row[11] else None
    )
    
    # Ejecutar señal
    position = trading_system.execute_signal(signal, user_id)
    
    if position:
        return {'success': True, 'message': 'Señal ejecutada', 'position_id': position.id}
    else:
        raise HTTPException(status_code=500, detail="Error ejecutando señal")

# ===========================================
# ENDPOINTS DE HISTÓRICO
# ===========================================

@app.get("/api/history/trades")
async def get_trade_history(limit: int = 100, user=Depends(get_current_user_optional)):
    """Obtener histórico de trades"""
    trading_system = get_trading_system()
    user_id = user['user_id'] if user else 'default'
    
    history = trading_system.get_trade_history(user_id, limit)
    return {'trades': history}

# ===========================================
# WEBSOCKET
# ===========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para actualizaciones en tiempo real"""
    ws_manager = get_websocket_manager()
    
    await ws_manager.connect(websocket)
    
    try:
        # Enviar estado inicial
        trading_system = get_trading_system()
        initial_state = {
            'type': 'initial_state',
            'payload': {
                'mode': trading_system.mode,
                'running': trading_system.is_running,
                'timestamp': datetime.now().isoformat()
            }
        }
        await websocket.send_json(initial_state)
        
        # Mantener conexión
        while True:
            data = await websocket.receive_text()
            
            # Procesar mensajes del cliente
            try:
                message = json.loads(data)
                
                if message.get('type') == 'auth':
                    # Autenticar WebSocket
                    token = message.get('token')
                    user = auth_manager.verify_token(token) if token else None
                    if user:
                        logger.info(f"WebSocket authenticated for user {user['user_id']}")
                
                elif message.get('type') == 'ping':
                    # Responder a ping
                    await websocket.send_json({'type': 'pong'})
                
            except json.JSONDecodeError:
                logger.error(f"Invalid WebSocket message: {data}")
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

# ===========================================
# HEALTH CHECK
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    trading_system = get_trading_system()
    return {
        'name': 'BotPhia Trading API V2',
        'version': '2.0.0',
        'mode': trading_system.mode,
        'status': 'online',
        'message': 'Sistema híbrido de trading con 8 filósofos'
    }

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║             🚀 BOTPHIA TRADING API V2 🚀                ║
║                                                          ║
║  Sistema Híbrido de Trading                             ║
║  • Modo: {get_trading_system().mode:20s}              ║
║  • Puerto: {port:5d}                                     ║
║  • WebSocket: Habilitado                                ║
║  • Auto-señales: Cada 30 segundos                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)