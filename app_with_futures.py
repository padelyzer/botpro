#!/usr/bin/env python3
"""
Sistema Completo de Trading con Pipeline de Futuros
Dashboard + Spot + Futures + Signals
Capital inicial: $220 USD
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import pandas as pd
import numpy as np

# Import sistemas existentes
from futures_trading_system import FuturesTradingSystem, FuturesPairFinder, FuturesSignal
from professional_trading_system import ProfessionalTradingSystem

# ============================================
# CONFIGURACIÓN
# ============================================

app = FastAPI(
    title="Trading System Complete",
    description="Sistema completo con Dashboard + Spot + Futures + Pipeline",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Capital inicial
INITIAL_CAPITAL = 220.0

# ============================================
# ESTADO GLOBAL
# ============================================

class SystemState:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.futures_system = FuturesTradingSystem(initial_capital=INITIAL_CAPITAL)
        self.spot_system = ProfessionalTradingSystem()
        self.pair_finder = FuturesPairFinder()
        self.active_positions = {}
        self.signals_history = []
        self.pnl_history = []
        self.best_pairs_cache = None
        self.last_scan = None
        
system_state = SystemState()

# ============================================
# MODELOS
# ============================================

class PipelineConfig(BaseModel):
    capital: float = INITIAL_CAPITAL
    max_leverage: int = 10
    risk_per_trade: float = 0.02
    max_positions: int = 3
    strategy: str = "all"
    min_confidence: float = 70

class FuturesPairResponse(BaseModel):
    symbol: str
    mark_price: float
    volume_24h: float
    volatility: float
    funding_rate: float
    long_ratio: float
    short_ratio: float
    score: float

class SignalRequest(BaseModel):
    symbols: List[str]
    strategy: str = "all"

# ============================================
# HTML INTERFACE
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading System - Complete Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .nav {
            display: flex;
            gap: 2rem;
            align-items: center;
            justify-content: space-between;
        }
        
        .nav-links {
            display: flex;
            gap: 1rem;
        }
        
        .nav-link {
            padding: 0.5rem 1rem;
            text-decoration: none;
            color: #333;
            border-radius: 5px;
            transition: all 0.3s;
        }
        
        .nav-link:hover, .nav-link.active {
            background: #667eea;
            color: white;
        }
        
        .capital-display {
            font-size: 1.2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        
        .tab-content {
            display: none;
            animation: fadeIn 0.5s;
        }
        
        .tab-content.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #333;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0.5rem 0;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .pipeline-controls {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .control-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .control-item {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        label {
            font-weight: 500;
            color: #555;
        }
        
        input, select {
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        .btn:hover {
            background: #5a67d8;
            transform: translateY(-2px);
        }
        
        .btn-group {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }
        
        .pairs-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        
        .pairs-table th, .pairs-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        .pairs-table th {
            background: #f7f7f7;
            font-weight: 600;
        }
        
        .pairs-table tr:hover {
            background: #f9f9f9;
        }
        
        .signal-card {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        }
        
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .signal-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        
        .signal-metric {
            display: flex;
            flex-direction: column;
        }
        
        .signal-metric-label {
            font-size: 0.9rem;
            color: #666;
        }
        
        .signal-metric-value {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
        }
        
        .position-card {
            background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
            border: 1px solid #667eea40;
        }
        
        .profit { color: #10b981; }
        .loss { color: #ef4444; }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .status-active { background: #10b98120; color: #059669; }
        .status-pending { background: #fbbf2420; color: #d97706; }
        .status-closed { background: #6b728020; color: #4b5563; }
    </style>
</head>
<body>
    <header class="header">
        <nav class="nav">
            <div class="nav-links">
                <a href="#dashboard" class="nav-link active" onclick="showTab('dashboard')">📊 Dashboard</a>
                <a href="#spot" class="nav-link" onclick="showTab('spot')">💰 Spot</a>
                <a href="#futures" class="nav-link" onclick="showTab('futures')">🚀 Futures</a>
                <a href="#pipeline" class="nav-link" onclick="showTab('pipeline')">⚡ Pipeline</a>
                <a href="#signals" class="nav-link" onclick="showTab('signals')">📈 Signals</a>
            </div>
            <div class="capital-display">
                💼 Capital: $<span id="capital">220.00</span>
            </div>
        </nav>
    </header>

    <div class="container">
        <!-- Dashboard Tab -->
        <div id="dashboard-tab" class="tab-content active">
            <h2 style="color: white; margin-bottom: 2rem;">Dashboard General</h2>
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-title">📊 Estado del Sistema</div>
                    <div class="metric">
                        <span>PnL Total</span>
                        <span class="metric-value" id="total-pnl">$0.00</span>
                    </div>
                    <div class="metric">
                        <span>Posiciones Activas</span>
                        <span class="metric-value" id="active-positions">0</span>
                    </div>
                    <div class="metric">
                        <span>Win Rate</span>
                        <span class="metric-value" id="win-rate">0%</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">⚡ Rendimiento</div>
                    <div class="metric">
                        <span>ROI</span>
                        <span class="metric-value" id="roi">0%</span>
                    </div>
                    <div class="metric">
                        <span>Trades Hoy</span>
                        <span class="metric-value" id="trades-today">0</span>
                    </div>
                    <div class="metric">
                        <span>Mejor Trade</span>
                        <span class="metric-value" id="best-trade">$0.00</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">⚙️ Configuración</div>
                    <div class="metric">
                        <span>Max Leverage</span>
                        <span class="metric-value" id="max-leverage">10x</span>
                    </div>
                    <div class="metric">
                        <span>Risk por Trade</span>
                        <span class="metric-value" id="risk-per-trade">2%</span>
                    </div>
                    <div class="metric">
                        <span>Estrategia</span>
                        <span class="metric-value" id="strategy">All</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Pipeline Tab -->
        <div id="pipeline-tab" class="tab-content">
            <h2 style="color: white; margin-bottom: 2rem;">⚡ Pipeline de Futuros</h2>
            
            <div class="pipeline-controls">
                <h3>Configuración del Pipeline</h3>
                
                <div class="control-group">
                    <div class="control-item">
                        <label>Capital ($)</label>
                        <input type="number" id="pipeline-capital" value="220" min="100" max="10000">
                    </div>
                    <div class="control-item">
                        <label>Max Leverage</label>
                        <input type="number" id="pipeline-leverage" value="10" min="1" max="20">
                    </div>
                    <div class="control-item">
                        <label>Risk por Trade (%)</label>
                        <input type="number" id="pipeline-risk" value="2" min="0.5" max="5" step="0.5">
                    </div>
                    <div class="control-item">
                        <label>Max Posiciones</label>
                        <input type="number" id="pipeline-positions" value="3" min="1" max="10">
                    </div>
                    <div class="control-item">
                        <label>Estrategia</label>
                        <select id="pipeline-strategy">
                            <option value="all">Todas</option>
                            <option value="momentum">Momentum</option>
                            <option value="reversal">Reversal</option>
                            <option value="volatility">Volatilidad</option>
                            <option value="funding">Funding Arbitrage</option>
                        </select>
                    </div>
                    <div class="control-item">
                        <label>Min Confianza (%)</label>
                        <input type="number" id="pipeline-confidence" value="70" min="50" max="90">
                    </div>
                </div>
                
                <div class="btn-group">
                    <button class="btn" onclick="scanMarket()">🔍 Escanear Mercado</button>
                    <button class="btn" onclick="generateSignals()">📈 Generar Señales</button>
                    <button class="btn" onclick="startPipeline()">▶️ Iniciar Pipeline</button>
                    <button class="btn" onclick="stopPipeline()">⏸️ Detener Pipeline</button>
                </div>
            </div>
            
            <div id="pipeline-results" style="margin-top: 2rem;">
                <!-- Results will be inserted here -->
            </div>
        </div>

        <!-- Futures Tab -->
        <div id="futures-tab" class="tab-content">
            <h2 style="color: white; margin-bottom: 2rem;">🚀 Mejores Pares de Futuros</h2>
            
            <div class="card">
                <div class="card-title">Top Oportunidades</div>
                <table class="pairs-table" id="futures-pairs-table">
                    <thead>
                        <tr>
                            <th>Símbolo</th>
                            <th>Precio</th>
                            <th>Volumen 24h</th>
                            <th>Volatilidad</th>
                            <th>Funding</th>
                            <th>L/S Ratio</th>
                            <th>Score</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody id="futures-pairs-body">
                        <!-- Pairs will be inserted here -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Signals Tab -->
        <div id="signals-tab" class="tab-content">
            <h2 style="color: white; margin-bottom: 2rem;">📈 Señales Activas</h2>
            
            <div id="signals-container">
                <!-- Signals will be inserted here -->
            </div>
        </div>

        <!-- Spot Tab -->
        <div id="spot-tab" class="tab-content">
            <h2 style="color: white; margin-bottom: 2rem;">💰 Trading Spot</h2>
            
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-title">Mercado Spot</div>
                    <p>Sistema de trading spot profesional</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // State
        let pipelineRunning = false;
        let ws = null;
        
        // Tab navigation
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active from all nav links
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            
            // Set active nav link
            document.querySelector(`a[href="#${tabName}"]`).classList.add('active');
        }
        
        // Format number
        function formatNumber(num, decimals = 2) {
            return parseFloat(num).toFixed(decimals);
        }
        
        // Format currency
        function formatCurrency(num) {
            return '$' + formatNumber(num, 2);
        }
        
        // Scan market
        async function scanMarket() {
            const resultsDiv = document.getElementById('pipeline-results');
            resultsDiv.innerHTML = '<div class="card"><div class="loading"></div> Escaneando mercado...</div>';
            
            try {
                const response = await fetch('/api/pipeline/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        strategy: document.getElementById('pipeline-strategy').value
                    })
                });
                
                const data = await response.json();
                displayScanResults(data);
            } catch (error) {
                resultsDiv.innerHTML = '<div class="card">Error: ' + error.message + '</div>';
            }
        }
        
        // Display scan results
        function displayScanResults(pairs) {
            const resultsDiv = document.getElementById('pipeline-results');
            const tbody = document.getElementById('futures-pairs-body');
            
            let html = '<div class="card"><div class="card-title">✅ ' + pairs.length + ' pares encontrados</div>';
            html += '<table class="pairs-table"><thead><tr>';
            html += '<th>Símbolo</th><th>Precio</th><th>Volumen</th><th>Score</th>';
            html += '</tr></thead><tbody>';
            
            tbody.innerHTML = '';
            
            pairs.forEach(pair => {
                // Add to main table
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td><strong>${pair.symbol}</strong></td>
                    <td>$${formatNumber(pair.mark_price, 4)}</td>
                    <td>$${formatNumber(pair.volume_24h/1e6, 1)}M</td>
                    <td>${formatNumber(pair.volatility, 2)}%</td>
                    <td>${formatNumber(pair.funding_rate * 100, 3)}%</td>
                    <td>${formatNumber(pair.long_ratio, 0)}/${formatNumber(pair.short_ratio, 0)}</td>
                    <td><strong>${formatNumber(pair.score, 1)}</strong></td>
                    <td><button class="btn" onclick="analyzeP

air('${pair.symbol}')">Analizar</button></td>
                `;
                
                // Add to results
                html += '<tr>';
                html += '<td>' + pair.symbol + '</td>';
                html += '<td>$' + formatNumber(pair.mark_price, 4) + '</td>';
                html += '<td>$' + formatNumber(pair.volume_24h/1e6, 1) + 'M</td>';
                html += '<td>' + formatNumber(pair.score, 1) + '</td>';
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            resultsDiv.innerHTML = html;
        }
        
        // Generate signals
        async function generateSignals() {
            const signalsDiv = document.getElementById('signals-container');
            signalsDiv.innerHTML = '<div class="card"><div class="loading"></div> Generando señales...</div>';
            
            try {
                const response = await fetch('/api/pipeline/signals', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        min_confidence: parseFloat(document.getElementById('pipeline-confidence').value)
                    })
                });
                
                const signals = await response.json();
                displaySignals(signals);
            } catch (error) {
                signalsDiv.innerHTML = '<div class="card">Error: ' + error.message + '</div>';
            }
        }
        
        // Display signals
        function displaySignals(signals) {
            const container = document.getElementById('signals-container');
            
            if (signals.length === 0) {
                container.innerHTML = '<div class="card">No hay señales disponibles</div>';
                return;
            }
            
            let html = '';
            signals.forEach(signal => {
                const isLong = signal.direction === 'LONG';
                html += `
                    <div class="signal-card">
                        <div class="signal-header">
                            <h3>${isLong ? '🟢' : '🔴'} ${signal.symbol}</h3>
                            <span class="status-badge status-active">${signal.direction}</span>
                        </div>
                        <div class="signal-details">
                            <div class="signal-metric">
                                <span class="signal-metric-label">Entrada</span>
                                <span class="signal-metric-value">$${formatNumber(signal.entry_price, 4)}</span>
                            </div>
                            <div class="signal-metric">
                                <span class="signal-metric-label">Stop Loss</span>
                                <span class="signal-metric-value">$${formatNumber(signal.stop_loss, 4)}</span>
                            </div>
                            <div class="signal-metric">
                                <span class="signal-metric-label">Take Profit</span>
                                <span class="signal-metric-value">$${formatNumber(signal.take_profit, 4)}</span>
                            </div>
                            <div class="signal-metric">
                                <span class="signal-metric-label">Leverage</span>
                                <span class="signal-metric-value">${signal.leverage}x</span>
                            </div>
                            <div class="signal-metric">
                                <span class="signal-metric-label">R:R Ratio</span>
                                <span class="signal-metric-value">${formatNumber(signal.risk_reward, 2)}</span>
                            </div>
                            <div class="signal-metric">
                                <span class="signal-metric-label">Confianza</span>
                                <span class="signal-metric-value">${signal.confidence}%</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // Start pipeline
        async function startPipeline() {
            if (pipelineRunning) {
                alert('Pipeline ya está ejecutándose');
                return;
            }
            
            const config = {
                capital: parseFloat(document.getElementById('pipeline-capital').value),
                max_leverage: parseInt(document.getElementById('pipeline-leverage').value),
                risk_per_trade: parseFloat(document.getElementById('pipeline-risk').value) / 100,
                max_positions: parseInt(document.getElementById('pipeline-positions').value),
                strategy: document.getElementById('pipeline-strategy').value,
                min_confidence: parseFloat(document.getElementById('pipeline-confidence').value)
            };
            
            try {
                const response = await fetch('/api/pipeline/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                
                if (response.ok) {
                    pipelineRunning = true;
                    connectWebSocket();
                    alert('Pipeline iniciado');
                }
            } catch (error) {
                alert('Error iniciando pipeline: ' + error.message);
            }
        }
        
        // Stop pipeline
        async function stopPipeline() {
            try {
                const response = await fetch('/api/pipeline/stop', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    pipelineRunning = false;
                    if (ws) ws.close();
                    alert('Pipeline detenido');
                }
            } catch (error) {
                alert('Error deteniendo pipeline: ' + error.message);
            }
        }
        
        // WebSocket connection
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws/pipeline');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        // Update dashboard
        function updateDashboard(data) {
            if (data.capital) {
                document.getElementById('capital').textContent = formatNumber(data.capital, 2);
            }
            if (data.pnl !== undefined) {
                document.getElementById('total-pnl').textContent = formatCurrency(data.pnl);
            }
            if (data.positions !== undefined) {
                document.getElementById('active-positions').textContent = data.positions;
            }
            if (data.win_rate !== undefined) {
                document.getElementById('win-rate').textContent = formatNumber(data.win_rate, 1) + '%';
            }
        }
        
        // Analyze pair
        async function analyzePair(symbol) {
            alert('Analizando ' + symbol + '...');
            // TODO: Implement pair analysis
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            // Load initial data
            updateDashboard({
                capital: 220,
                pnl: 0,
                positions: 0,
                win_rate: 0
            });
        });
    </script>
</body>
</html>
"""

# ============================================
# ENDPOINTS
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main HTML interface"""
    return HTML_TEMPLATE

@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "capital": system_state.capital,
        "initial_capital": INITIAL_CAPITAL,
        "pnl": sum(system_state.pnl_history),
        "active_positions": len(system_state.active_positions),
        "total_trades": len(system_state.pnl_history),
        "win_rate": calculate_win_rate(),
        "roi": calculate_roi()
    }

@app.post("/api/pipeline/scan")
async def scan_market(strategy: str = "all"):
    """Scan futures market for opportunities"""
    
    best_pairs = await system_state.pair_finder.find_best_opportunities(
        strategy=strategy,
        limit=10
    )
    
    system_state.best_pairs_cache = best_pairs
    system_state.last_scan = datetime.now()
    
    # Convert to response format
    pairs_response = []
    for pair in best_pairs:
        pairs_response.append(FuturesPairResponse(
            symbol=pair.symbol,
            mark_price=pair.mark_price,
            volume_24h=pair.volume_24h,
            volatility=pair.volatility,
            funding_rate=pair.funding_rate,
            long_ratio=pair.long_ratio,
            short_ratio=pair.short_ratio,
            score=calculate_pair_score(pair)
        ))
    
    return pairs_response

@app.post("/api/pipeline/signals")
async def generate_signals(min_confidence: float = 70):
    """Generate trading signals"""
    
    if not system_state.best_pairs_cache:
        raise HTTPException(status_code=400, detail="Primero debes escanear el mercado")
    
    signals = []
    for pair in system_state.best_pairs_cache[:5]:
        signal = await system_state.futures_system.generate_futures_signal(pair)
        
        if signal and signal.confidence >= min_confidence:
            signals.append({
                "symbol": signal.pair.symbol,
                "direction": signal.direction,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit_2,
                "leverage": signal.recommended_leverage,
                "confidence": signal.confidence,
                "risk_reward": signal.risk_reward_ratio,
                "type": signal.signal_type.value,
                "reasons": signal.reasons[:2]
            })
            
            system_state.signals_history.append(signal)
    
    return signals

@app.post("/api/pipeline/start")
async def start_pipeline(config: PipelineConfig):
    """Start automated pipeline"""
    
    # Update system configuration
    system_state.futures_system.futures_config.update({
        "max_leverage": config.max_leverage,
        "risk_per_trade": config.risk_per_trade,
        "max_positions": config.max_positions
    })
    
    return {"status": "started", "config": config}

@app.post("/api/pipeline/stop")
async def stop_pipeline():
    """Stop automated pipeline"""
    return {"status": "stopped"}

@app.websocket("/ws/pipeline")
async def websocket_pipeline(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send updates every 5 seconds
            await asyncio.sleep(5)
            
            data = {
                "capital": system_state.capital + sum(system_state.pnl_history),
                "pnl": sum(system_state.pnl_history),
                "positions": len(system_state.active_positions),
                "win_rate": calculate_win_rate()
            }
            
            await websocket.send_json(data)
            
    except WebSocketDisconnect:
        pass

# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_win_rate() -> float:
    """Calculate win rate"""
    if not system_state.pnl_history:
        return 0
    
    wins = len([p for p in system_state.pnl_history if p > 0])
    return (wins / len(system_state.pnl_history)) * 100

def calculate_roi() -> float:
    """Calculate ROI"""
    total_pnl = sum(system_state.pnl_history)
    return (total_pnl / INITIAL_CAPITAL) * 100

def calculate_pair_score(pair) -> float:
    """Calculate opportunity score for a pair"""
    score = 0
    
    # Volume score
    if pair.volume_24h_usd > 100000000:
        score += 30
    elif pair.volume_24h_usd > 50000000:
        score += 20
    
    # Volatility score
    if 3 < pair.volatility < 8:
        score += 25
    
    # Funding score
    if abs(pair.funding_rate) > 0.0001:
        score += 15
    
    # Momentum score
    if abs(pair.price_change_24h) > 3:
        score += 20
    
    # Spread score
    if pair.spread < 0.05:
        score += 10
    
    return score

# ============================================
# STARTUP
# ============================================

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("TRADING SYSTEM COMPLETE")
    print(f"Capital Inicial: ${INITIAL_CAPITAL}")
    print("="*60)
    print("✅ Dashboard: http://localhost:8000")
    print("✅ Pipeline: http://localhost:8000/#pipeline")
    print("✅ Futures: http://localhost:8000/#futures")
    print("✅ Signals: http://localhost:8000/#signals")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)