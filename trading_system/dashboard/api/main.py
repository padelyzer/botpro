#!/usr/bin/env python3
"""
Crypto Operations Center - Main Dashboard API
Professional Trading System Web Interface
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.market_data import market_fetcher, market_analyzer
from monitors import entry_alert_monitor, wait_strategy_monitor, correlation_monitor
from monitors.philosophers import philosopher_council
import sys
sys.path.append('/Users/ja/saby/trading_api/trading_system')
from signal_validator import SignalValidator

app = FastAPI(title="Crypto Operations Center", description="Professional Trading System Dashboard")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")

class WebSocketManager:
    """Manage WebSocket connections for real-time data"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.monitor_tasks: Dict[str, asyncio.Task] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket client connected. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ WebSocket client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = WebSocketManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Crypto Operations Center"
    })

@app.get("/api/system/status")
async def system_status():
    """Get overall system status"""
    try:
        # Get market data
        btc_data, sol_data = await market_fetcher.get_btc_sol_data()
        market_overview = await market_fetcher.get_market_overview()
        
        # Parse current prices
        btc_price = float(btc_data['lastPrice']) if btc_data else 0
        btc_change = float(btc_data['priceChangePercent']) if btc_data else 0
        sol_price = float(sol_data['lastPrice']) if sol_data else 0
        sol_change = float(sol_data['priceChangePercent']) if sol_data else 0
        
        # System status
        status = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "status": "online",
                "version": "v2.0",
                "uptime": "active"
            },
            "market": {
                "btc": {
                    "price": btc_price,
                    "change_24h": btc_change,
                    "status": "strong" if btc_price > 110000 else "neutral" if btc_price > 108000 else "weak"
                },
                "sol": {
                    "price": sol_price,
                    "change_24h": sol_change,
                    "distance_to_target": ((sol_price - 180) / sol_price * 100) if sol_price > 0 else 0
                }
            },
            "monitors": {
                "entry_alerts": {"status": "ready", "active": False},
                "wait_strategy": {"status": "ready", "active": False},
                "correlation": {"status": "ready", "active": False}
            },
            "position": {
                "liquidation_price": config.get('position.current_liquidation', 152.05),
                "breakeven_price": config.get('position.breakeven_price', 204.0),
                "size": config.get('position.current_size', 29.82)
            }
        }
        
        return status
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.get("/api/monitors/{monitor_name}/data")
async def get_monitor_data(monitor_name: str):
    """Get data from specific monitor"""
    try:
        if monitor_name == "entry_alerts":
            data = await entry_alert_monitor.monitor_step()
        elif monitor_name == "wait_strategy":
            data = await wait_strategy_monitor.monitor_step()
        elif monitor_name == "correlation":
            data = await correlation_monitor.monitor_step()
        elif monitor_name == "philosophers":
            data = await philosopher_council.analyze_signal('SOL')
        else:
            return {"error": "Monitor not found"}
            
        return {"status": "success", "data": data}
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.post("/api/validate-signal")
async def validate_signal(request: Request):
    """Validate a trading signal"""
    try:
        body = await request.json()
        signal_text = body.get('signal', '')
        current_position = body.get('position', {'size': 0})
        
        validator = SignalValidator()
        result = await validator.validate_signal(signal_text, current_position)
        
        return {"status": "success", "validation": result}
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.get("/api/philosophers/analysis")
async def get_philosopher_analysis():
    """Get current philosopher council analysis"""
    try:
        analysis = await philosopher_council.analyze_signal('SOL')
        return {"status": "success", "analysis": analysis}
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.post("/api/monitors/{monitor_name}/start")
async def start_monitor(monitor_name: str):
    """Start a specific monitor"""
    try:
        if monitor_name in manager.monitor_tasks:
            return {"error": "Monitor already running", "status": "error"}
        
        if monitor_name == "entry_alerts":
            task = asyncio.create_task(entry_alert_monitor.monitor_continuous())
        elif monitor_name == "wait_strategy":
            task = asyncio.create_task(wait_strategy_monitor.monitor_continuous())
        elif monitor_name == "correlation":
            task = asyncio.create_task(correlation_monitor.monitor_continuous())
        else:
            return {"error": "Monitor not found"}
        
        manager.monitor_tasks[monitor_name] = task
        return {"status": "success", "message": f"{monitor_name} started"}
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.post("/api/monitors/{monitor_name}/stop")
async def stop_monitor(monitor_name: str):
    """Stop a specific monitor"""
    try:
        if monitor_name not in manager.monitor_tasks:
            return {"error": "Monitor not running", "status": "error"}
        
        task = manager.monitor_tasks[monitor_name]
        task.cancel()
        del manager.monitor_tasks[monitor_name]
        
        return {"status": "success", "message": f"{monitor_name} stopped"}
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await manager.connect(websocket)
    
    try:
        # Start sending real-time data
        while True:
            # Get system status
            try:
                btc_data, sol_data = await market_fetcher.get_btc_sol_data()
                
                if btc_data and sol_data:
                    btc_price = float(btc_data['lastPrice'])
                    btc_change = float(btc_data['priceChangePercent'])
                    sol_price = float(sol_data['lastPrice'])
                    sol_change = float(sol_data['priceChangePercent'])
                    
                    # Get monitor data
                    entry_data = await entry_alert_monitor.monitor_step()
                    wait_data = await wait_strategy_monitor.monitor_step()
                    corr_data = await correlation_monitor.monitor_step()
                    
                    # Calculate P&L and risk metrics
                    entry_price = 198.20  # User's entry price
                    position_size = config.get('position.current_size', 29.82)
                    liquidation_price = config.get('position.current_liquidation', 152.05)
                    
                    # Calculate P&L
                    price_diff = sol_price - entry_price
                    pnl_usd = price_diff * position_size
                    pnl_percent = (price_diff / entry_price) * 100
                    
                    # Calculate distance to liquidation
                    liq_distance = sol_price - liquidation_price
                    liq_distance_percent = (liq_distance / sol_price) * 100
                    
                    # Determine risk status
                    if liq_distance_percent > 30:
                        risk_status = "SAFE"
                        risk_level = "low"
                    elif liq_distance_percent > 15:
                        risk_status = "CAUTION"
                        risk_level = "medium"
                    else:
                        risk_status = "DANGER"
                        risk_level = "high"
                    
                    # Broadcast real-time data
                    realtime_data = {
                        "type": "realtime_update",
                        "timestamp": datetime.now().isoformat(),
                        "market": {
                            "btc": {"price": btc_price, "change": btc_change},
                            "sol": {"price": sol_price, "change": sol_change}
                        },
                        "position": {
                            "entry_price": entry_price,
                            "current_price": sol_price,
                            "size": position_size,
                            "pnl_usd": round(pnl_usd, 2),
                            "pnl_percent": round(pnl_percent, 2),
                            "liquidation_price": liquidation_price,
                            "liq_distance": round(liq_distance, 2),
                            "liq_distance_percent": round(liq_distance_percent, 2),
                            "risk_status": risk_status,
                            "risk_level": risk_level
                        },
                        "monitors": {
                            "entry_alerts": entry_data,
                            "wait_strategy": wait_data,
                            "correlation": corr_data
                        }
                    }
                    
                    await manager.broadcast(realtime_data)
                    
            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(error_data)
            
            # Wait 10 seconds before next update
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task for system monitoring
async def background_monitor():
    """Background task for system health monitoring"""
    while True:
        try:
            # System health check
            health_data = {
                "type": "system_health",
                "timestamp": datetime.now().isoformat(),
                "monitors_active": len(manager.monitor_tasks),
                "connections": len(manager.active_connections)
            }
            
            await manager.broadcast(health_data)
            await asyncio.sleep(30)  # Every 30 seconds
            
        except Exception as e:
            print(f"Background monitor error: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup"""
    print("🚀 Starting Crypto Operations Center...")
    print(f"📊 Dashboard will be available at http://localhost:8080")
    
    # Start background monitoring
    asyncio.create_task(background_monitor())

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )