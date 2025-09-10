#!/usr/bin/env python3
"""
🌐 BotphIA Web API - Sistema de señales de trading accesible vía web
FastAPI backend para servir señales y monitores en tiempo real
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from pathlib import Path

# Importar nuestros módulos del sistema de trading
try:
    from enhanced_signal_detector import EnhancedPatternDetector
    try:
        from telegram_notifier import create_telegram_notifier
        TELEGRAM_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Telegram notifier not available: {e}")
        TELEGRAM_AVAILABLE = False
        create_telegram_notifier = lambda: None
    # Crear funciones auxiliares para compatibilidad
    def get_enhanced_signals_data():
        # Datos de ejemplo con el sistema enriquecido RSI 73/28
        from datetime import datetime, timedelta
        import random
        
        signals = [
            {
                "symbol": "BTCUSDT",
                "signal_type": "BUY", 
                "timeframe": "4h",
                "pattern_type": "Double Bottom",
                "entry_price": "65420.50",
                "stop_loss": "64200.00", 
                "take_profit_1": "67800.00",
                "take_profit_2": "69200.00",
                "recommended_leverage": "8x",
                "risk_reward_ratio": "2.1",
                "timestamp": datetime.now().isoformat(),
                "confidence": "HIGH",
                "atr_volatility": "1.2%"
            },
            {
                "symbol": "ETHUSDT",
                "signal_type": "SELL",
                "timeframe": "1h", 
                "pattern_type": "Double Top",
                "entry_price": "3245.80",
                "stop_loss": "3290.00",
                "take_profit_1": "3180.00", 
                "take_profit_2": "3120.00",
                "recommended_leverage": "10x",
                "risk_reward_ratio": "1.9",
                "timestamp": datetime.now().isoformat(),
                "confidence": "MEDIUM",
                "atr_volatility": "0.8%"
            },
            {
                "symbol": "DOGEUSDT", 
                "signal_type": "BUY",
                "timeframe": "4h",
                "pattern_type": "Support Bounce",
                "entry_price": "0.1245",
                "stop_loss": "0.1210",
                "take_profit_1": "0.1310",
                "take_profit_2": "0.1340", 
                "recommended_leverage": "12x",
                "risk_reward_ratio": "2.3",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "confidence": "HIGH",
                "atr_volatility": "2.1%"
            },
            {
                "symbol": "AVAXUSDT",
                "signal_type": "BUY",
                "timeframe": "15m",
                "pattern_type": "Breakout", 
                "entry_price": "28.45",
                "stop_loss": "27.80",
                "take_profit_1": "29.60",
                "take_profit_2": "30.20",
                "recommended_leverage": "6x", 
                "risk_reward_ratio": "2.0",
                "timestamp": (datetime.now() - timedelta(minutes=8)).isoformat(),
                "confidence": "MEDIUM",
                "atr_volatility": "1.5%"
            }
        ]
        return signals
    
    def get_current_signals():
        return get_enhanced_signals_data()
        
except ImportError as e:
    logging.error(f"Error importing trading modules: {e}")
    print("⚠️ Error: No se pudieron importar los módulos de trading")
    
    # Funciones fallback
    def get_enhanced_signals_data():
        return []
    
    def get_current_signals():
        return []

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="BotphIA Trading Signals API",
    description="Sistema de señales de trading con RSI 73/28, R:R dinámico y apalancamiento adaptativo",
    version="1.0.0"
)

# Configurar CORS para permitir acceso desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global para señales y conexiones WebSocket
class SignalState:
    def __init__(self):
        self.current_signals: List[Dict] = []
        self.last_update: datetime = datetime.now()
        self.websocket_connections: List[WebSocket] = []
        self.detector = None
        
    async def initialize_detector(self):
        """Inicializar el detector de señales"""
        try:
            self.detector = EnhancedPatternDetector()
            logger.info("✅ Detector de señales inicializado")
        except Exception as e:
            logger.error(f"❌ Error al inicializar detector: {e}")

signal_state = SignalState()

# Inicializar notificador de Telegram
telegram_notifier = None
if TELEGRAM_AVAILABLE:
    try:
        telegram_notifier = create_telegram_notifier()
        if telegram_notifier:
            logger.info("✅ Telegram notifier initialized")
        else:
            logger.warning("⚠️ Telegram notifier not configured")
    except Exception as e:
        logger.warning(f"⚠️ Telegram initialization failed: {e}")
        telegram_notifier = None
else:
    logger.info("ℹ️ Telegram feature not available")

@app.on_event("startup")
async def startup_event():
    """Inicializar el sistema al arrancar"""
    logger.info("🚀 Iniciando BotphIA Web API...")
    await signal_state.initialize_detector()
    
    # Crear directorio para archivos estáticos si no existe
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Iniciar bot automáticamente
    bot_state["running"] = True
    bot_state["start_time"] = datetime.now()
    bot_state["task"] = asyncio.create_task(run_signal_generator())
    logger.info("🤖 Bot iniciado automáticamente")
    
    # Enviar notificación de startup a Telegram
    if telegram_notifier:
        await telegram_notifier.send_status_update("🚀 BotphIA Web API iniciado correctamente - Bot running")
    
    logger.info("✅ Sistema iniciado correctamente")

# =================== ENDPOINTS REST API ===================

@app.get("/")
async def root():
    """Página de inicio con información del API"""
    return {
        "system": "BotphIA Trading Signals API",
        "version": "2.0.1",
        "status": "online",
        "bot_status": "running" if bot_state.get("running", False) else "stopped",
        "signals_generated": bot_state.get("signals_count", 0),
        "features": [
            "RSI 73/28 threshold signals",
            "Dynamic R:R ratio (1.8-2.7:1)",
            "Adaptive leverage (2x-12x)",
            "Real-time WebSocket updates",
            "12 trading pairs support",
            "4 timeframes (5m, 15m, 1h, 4h)"
        ],
        "endpoints": {
            "signals": "/api/signals",
            "signals_enhanced": "/api/signals/enhanced", 
            "dashboard": "/dashboard",
            "professional_dashboard": "/pro",
            "websocket": "/ws"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint para Render"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/signals")
async def get_signals():
    """Obtener señales actuales básicas"""
    try:
        # Obtener señales usando la función existente
        signals_data = get_current_signals_data()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_signals": len(signals_data),
            "signals": signals_data,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error obteniendo señales: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/enhanced")
async def get_enhanced_signals():
    """Obtener señales enriquecidas con métricas completas"""
    try:
        # Obtener señales enriquecidas (usando datos de ejemplo)
        enhanced_data = get_enhanced_signals_data()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_config": {
                "rsi_overbought": 73,
                "rsi_oversold": 28,
                "dynamic_rr": True,
                "adaptive_leverage": True
            },
            "signals": enhanced_data,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error obteniendo señales enriquecidas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pairs")
async def get_trading_pairs():
    """Obtener lista de pares de trading disponibles"""
    pairs = [
        "AVAXUSDT", "LINKUSDT", "NEARUSDT", "XRPUSDT", "PENGUUSDT",
        "ADAUSDT", "SUIUSDT", "DOTUSDT", "DOGEUSDT", "UNIUSDT", 
        "ETHUSDT", "BTCUSDT"
    ]
    
    return {
        "total_pairs": len(pairs),
        "pairs": pairs,
        "timeframes": ["5m", "15m", "1h", "4h"]
    }

@app.get("/api/config")
async def get_system_config():
    """Obtener configuración actual del sistema"""
    return {
        "rsi_config": {
            "overbought": 73,
            "oversold": 28,
            "period": 14
        },
        "risk_reward": {
            "type": "dynamic",
            "range": "1.8:1 - 2.7:1",
            "based_on": "ATR volatility"
        },
        "leverage": {
            "type": "adaptive", 
            "range": "2x - 12x",
            "based_on": "inverse volatility"
        },
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/system/files")
async def check_files():
    """Verificar archivos disponibles en el sistema"""
    import os
    files = {
        "current_dir": os.getcwd(),
        "files_in_root": os.listdir("."),
        "static_exists": os.path.exists("static"),
        "static_files": os.listdir("static") if os.path.exists("static") else [],
        "dashboard_exists": os.path.exists("static/dashboard.html"),
        "pro_dashboard_exists": os.path.exists("static/professional_dashboard.html")
    }
    return files

@app.get("/api/stats")
async def get_system_stats():
    """Obtener estadísticas del sistema"""
    try:
        # Cargar estadísticas del último reporte de backtesting
        backtest_file = "backtest_report_20250908_183110.json"
        if Path(backtest_file).exists():
            with open(backtest_file, 'r') as f:
                backtest_data = json.load(f)
                
            return {
                "backtest_results": backtest_data.get("results", {}),
                "top_pairs": backtest_data.get("top_pairs", []),
                "best_patterns": backtest_data.get("patterns", [])[:3],
                "report_date": backtest_data.get("timestamp", "")
            }
        else:
            return {
                "message": "No backtest data available",
                "status": "no_data"
            }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {"error": str(e)}

# =================== TELEGRAM ENDPOINTS ===================

@app.post("/api/signals/send-telegram")
async def send_signal_to_telegram(signal_data: dict):
    """Enviar señal específica a Telegram"""
    if not telegram_notifier:
        raise HTTPException(status_code=503, detail="Telegram not configured")
    
    try:
        success = await telegram_notifier.send_signal(signal_data)
        return {
            "status": "success" if success else "failed",
            "message": "Signal sent to Telegram" if success else "Failed to send signal",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/test")
async def test_telegram_connection():
    """Test conexión con Telegram"""
    if not telegram_notifier:
        raise HTTPException(status_code=503, detail="Telegram not configured")
    
    try:
        success = await telegram_notifier.send_status_update("🧪 Test de conexión exitoso")
        return {
            "status": "success" if success else "failed", 
            "message": "Test message sent" if success else "Failed to send test message",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error testing Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== WEBSOCKET ===================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para actualizaciones en tiempo real"""
    await websocket.accept()
    signal_state.websocket_connections.append(websocket)
    
    try:
        logger.info(f"🔌 Nueva conexión WebSocket. Total: {len(signal_state.websocket_connections)}")
        
        # Enviar señales actuales inmediatamente
        current_signals = get_enhanced_signals_data()
        await websocket.send_json({
            "type": "initial_signals",
            "timestamp": datetime.now().isoformat(),
            "data": current_signals
        })
        
        # Mantener conexión activa
        while True:
            # Enviar ping cada 30 segundos
            await asyncio.sleep(30)
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        signal_state.websocket_connections.remove(websocket)
        logger.info(f"🔌 Conexión WebSocket cerrada. Total: {len(signal_state.websocket_connections)}")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        if websocket in signal_state.websocket_connections:
            signal_state.websocket_connections.remove(websocket)

async def broadcast_signals_update():
    """Enviar actualización de señales a todas las conexiones WebSocket"""
    if not signal_state.websocket_connections:
        return
        
    try:
        signals = get_enhanced_signals_data()
        message = {
            "type": "signals_update",
            "timestamp": datetime.now().isoformat(),
            "data": signals
        }
        
        # Enviar a todas las conexiones activas
        disconnected = []
        for websocket in signal_state.websocket_connections:
            try:
                await websocket.send_json(message)
            except:
                disconnected.append(websocket)
        
        # Limpiar conexiones cerradas
        for ws in disconnected:
            signal_state.websocket_connections.remove(ws)
            
    except Exception as e:
        logger.error(f"Error broadcasting signals: {e}")

# =================== FUNCIONES AUXILIARES ===================

def get_current_signals_data():
    """Función auxiliar para obtener señales actuales"""
    try:
        # Retornar datos de ejemplo para demo
        return [
            {
                "symbol": "BTCUSDT",
                "signal": "BUY",
                "timeframe": "4h",
                "pattern": "Double Bottom",
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "ETHUSDT", 
                "signal": "SELL",
                "timeframe": "1h",
                "pattern": "Double Top",
                "timestamp": datetime.now().isoformat()
            }
        ]
    except Exception as e:
        logger.error(f"Error en get_current_signals_data: {e}")
        return []

# =================== TASK PERIÓDICA ===================

async def periodic_signal_update():
    """Tarea que actualiza las señales cada minuto"""
    while True:
        try:
            await broadcast_signals_update()
            await asyncio.sleep(60)  # Actualizar cada minuto
        except Exception as e:
            logger.error(f"Error en actualización periódica: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def start_background_tasks():
    """Iniciar tareas en background"""
    asyncio.create_task(periodic_signal_update())

# =================== DASHBOARD ===================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Servir el dashboard principal"""
    try:
        with open("static/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Dashboard no encontrado</h1><p>El archivo dashboard.html no existe.</p>",
            status_code=404
        )

@app.get("/pro", response_class=HTMLResponse)
async def professional_dashboard():
    """Servir el dashboard profesional con diseño estilo Binance"""
    try:
        import os
        # Verificar si el archivo existe
        file_path = os.path.join(os.path.dirname(__file__), "static", "professional_dashboard.html")
        
        # Si no existe en la ruta completa, intentar ruta relativa
        if not os.path.exists(file_path):
            file_path = "static/professional_dashboard.html"
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return HTMLResponse(content=content, status_code=200)
    except FileNotFoundError:
        # Retornar un dashboard mínimo funcional si no se encuentra el archivo
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>BotphIA Pro Dashboard</title>
                <meta charset="UTF-8">
                <style>
                    body { 
                        background: #0c0e16; 
                        color: white; 
                        font-family: Arial, sans-serif;
                        padding: 20px;
                    }
                    h1 { color: #fcd535; }
                    .info { 
                        background: #1e2329; 
                        padding: 20px; 
                        border-radius: 10px;
                        margin: 20px 0;
                    }
                    a { color: #02c076; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <h1>🤖 BotphIA Professional Dashboard</h1>
                <div class="info">
                    <h2>Welcome to BotphIA Trading System</h2>
                    <p>RSI: 73/28 | Dynamic R:R | Adaptive Leverage</p>
                    <p>
                        <a href="/api/signals/enhanced">View Signals</a> | 
                        <a href="/docs">API Documentation</a> |
                        <a href="/dashboard">Classic Dashboard</a>
                    </p>
                </div>
                <div class="info">
                    <h3>System Status: ✅ Online</h3>
                    <p>The professional dashboard is loading...</p>
                </div>
            </body>
            </html>
            """,
            status_code=200
        )

# =================== TRADING BOT INTEGRATION ===================

# Estado global del bot
bot_state = {
    "running": False,
    "task": None,
    "last_signal": None,
    "signals_count": 0,
    "start_time": None
}

async def run_signal_generator():
    """Ejecutar el generador de señales en background"""
    try:
        # Importar el generador de señales reales
        try:
            from simple_signal_generator import SimpleSignalGenerator
            generator = SimpleSignalGenerator()
            logger.info("✅ Generador de señales reales inicializado")
        except ImportError as e:
            logger.error(f"Error importando generador: {e}")
            generator = None
            
        bot_state["start_time"] = datetime.now()
        logger.info("🤖 Bot de trading iniciado con señales REALES")
        
        while bot_state["running"]:
            try:
                if generator:
                    # Generar señales reales
                    signals = await generator.generate_signals()
                    
                    if signals:
                        for signal in signals:
                            bot_state["last_signal"] = signal
                            bot_state["signals_count"] += 1
                            
                            logger.info(f"📊 Señal REAL: {signal['symbol']} - {signal['signal_type']} (Confianza: {signal['confidence']}%)")
                            
                            # Guardar en la lista de señales actuales
                            if "current_signals" not in bot_state:
                                bot_state["current_signals"] = []
                            
                            # Mantener solo las últimas 10 señales
                            bot_state["current_signals"].append(signal)
                            if len(bot_state["current_signals"]) > 10:
                                bot_state["current_signals"].pop(0)
                            
                            # Enviar a Telegram si está configurado
                            if telegram_notifier and signal['confidence'] >= 70:
                                await telegram_notifier.send_signal(signal)
                    else:
                        logger.info("⏳ No hay señales fuertes en este momento")
                else:
                    # Fallback: señal simulada si no hay generador
                    signal = {
                        "symbol": random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
                        "signal_type": random.choice(["BUY", "SELL"]),
                        "confidence": random.randint(60, 95),
                        "entry_price": f"{random.uniform(30000, 70000):.2f}",
                        "timestamp": datetime.now().isoformat(),
                        "warning": "Señal simulada - Generador real no disponible"
                    }
                    bot_state["last_signal"] = signal
                    bot_state["signals_count"] += 1
                    
                # Esperar 5 minutos antes de la siguiente verificación
                await asyncio.sleep(300)  # 5 minutos
                
            except Exception as e:
                logger.error(f"Error en generación de señales: {e}")
                await asyncio.sleep(60)
                
    except Exception as e:
        logger.error(f"Error fatal en bot: {e}")
    finally:
        bot_state["running"] = False
        logger.info("🛑 Bot de trading detenido")

@app.post("/api/bot/start")
async def start_bot():
    """Iniciar el bot de trading"""
    if bot_state["running"]:
        return {"status": "already_running", "message": "Bot already running"}
    
    bot_state["running"] = True
    bot_state["task"] = asyncio.create_task(run_signal_generator())
    
    return {
        "status": "started",
        "message": "Trading bot started successfully",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/bot/stop")
async def stop_bot():
    """Detener el bot de trading"""
    if not bot_state["running"]:
        return {"status": "not_running", "message": "Bot is not running"}
    
    bot_state["running"] = False
    if bot_state["task"]:
        bot_state["task"].cancel()
        
    return {
        "status": "stopped",
        "message": "Trading bot stopped successfully",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/bot/status")
async def bot_status():
    """Obtener estado del bot"""
    uptime = None
    if bot_state["start_time"]:
        uptime = str(datetime.now() - bot_state["start_time"])
    
    return {
        "running": bot_state["running"],
        "signals_count": bot_state["signals_count"],
        "last_signal": bot_state["last_signal"],
        "current_signals": bot_state.get("current_signals", []),
        "start_time": bot_state["start_time"].isoformat() if bot_state["start_time"] else None,
        "uptime": uptime
    }

@app.get("/api/bot/signals")
async def get_bot_signals():
    """Obtener las señales actuales del bot"""
    return {
        "signals": bot_state.get("current_signals", []),
        "total": len(bot_state.get("current_signals", [])),
        "last_update": bot_state["last_signal"]["timestamp"] if bot_state.get("last_signal") else None
    }

# =================== SERVIR ARCHIVOS ESTÁTICOS ===================

# Montar directorio estático para el frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import os
    
    # Puerto dinámico para deployment (GCP usa 8080 por defecto)
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("🚀 Iniciando BotphIA Web API...")
    print(f"📊 Dashboard disponible en: http://localhost:{port}")
    print(f"🔧 API docs en: http://localhost:{port}/docs")
    print(f"📡 WebSocket en: ws://localhost:{port}/ws")
    
    uvicorn.run(
        "web_api:app",
        host=host, 
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )