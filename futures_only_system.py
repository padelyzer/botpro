#!/usr/bin/env python3
"""
Sistema Exclusivo de Trading de Futuros
Capital inicial: $220 USD
Solo operaciones con futuros de Binance
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import numpy as np

# Import sistema de futuros
from futures_trading_system import FuturesTradingSystem, FuturesPairFinder, FuturesSignal

# ============================================
# CONFIGURACIÓN
# ============================================

app = FastAPI(
    title="Futures Trading System",
    description="Sistema exclusivo de trading de futuros - Capital $220",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Capital inicial fijo
INITIAL_CAPITAL = 220.0

# ============================================
# ESTADO DEL SISTEMA
# ============================================

class FuturesSystemState:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.available_margin = INITIAL_CAPITAL
        self.futures_system = FuturesTradingSystem(initial_capital=INITIAL_CAPITAL)
        self.pair_finder = FuturesPairFinder()
        self.active_positions = {}
        self.pending_orders = {}
        self.signals_history = []
        self.pnl_history = []
        self.best_pairs_cache = []
        self.last_scan = None
        self.pipeline_running = False
        
system_state = FuturesSystemState()

# ============================================
# MODELOS
# ============================================

class FuturesConfig(BaseModel):
    max_leverage: int = 5  # Conservador para $220
    risk_per_trade: float = 0.02  # 2% = $4.40
    max_positions: int = 2  # Máximo 2 posiciones con $220
    min_confidence: float = 70
    strategy: str = "all"
    use_trailing_stop: bool = True
    partial_tp: bool = True

class PositionRequest(BaseModel):
    symbol: str
    direction: str  # LONG or SHORT
    leverage: int
    amount: float

# ============================================
# HTML - INTERFAZ SOLO FUTUROS
# ============================================

HTML_FUTURES_ONLY = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Futures Trading - $220 Capital</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f;
            color: #fff;
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(90deg, #1a1a1a 0%, #2a2a2a 100%);
            padding: 1rem 2rem;
            border-bottom: 2px solid #00d4ff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            color: #00d4ff;
        }
        
        .capital-info {
            display: flex;
            gap: 2rem;
            align-items: center;
        }
        
        .capital-item {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        
        .capital-label {
            font-size: 0.75rem;
            color: #888;
        }
        
        .capital-value {
            font-size: 1.25rem;
            font-weight: bold;
            color: #00d4ff;
        }
        
        .main-container {
            display: grid;
            grid-template-columns: 300px 1fr;
            height: calc(100vh - 70px);
        }
        
        .sidebar {
            background: #1a1a1a;
            padding: 1.5rem;
            border-right: 1px solid #333;
            overflow-y: auto;
        }
        
        .content {
            padding: 1.5rem;
            overflow-y: auto;
        }
        
        .section {
            margin-bottom: 2rem;
        }
        
        .section-title {
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: #00d4ff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .control-group {
            margin-bottom: 1.5rem;
        }
        
        .control-label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: #aaa;
        }
        
        .control-input {
            width: 100%;
            padding: 0.5rem;
            background: #2a2a2a;
            border: 1px solid #444;
            border-radius: 4px;
            color: #fff;
            font-size: 0.9rem;
        }
        
        .control-input:focus {
            outline: none;
            border-color: #00d4ff;
        }
        
        .btn {
            width: 100%;
            padding: 0.75rem;
            margin: 0.5rem 0;
            background: linear-gradient(90deg, #00d4ff 0%, #0099cc 100%);
            color: #000;
            border: none;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,212,255,0.3);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .btn-danger {
            background: linear-gradient(90deg, #ff0040 0%, #cc0033 100%);
        }
        
        .btn-success {
            background: linear-gradient(90deg, #00ff88 0%, #00cc6a 100%);
            color: #000;
        }
        
        .pairs-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
        }
        
        .pair-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 1rem;
            transition: all 0.3s;
        }
        
        .pair-card:hover {
            border-color: #00d4ff;
            transform: translateY(-2px);
        }
        
        .pair-symbol {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        
        .pair-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            font-size: 0.85rem;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
        }
        
        .metric-label {
            color: #888;
        }
        
        .metric-value {
            color: #fff;
            font-weight: 500;
        }
        
        .positions-container {
            display: grid;
            gap: 1rem;
        }
        
        .position-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            border: 1px solid #444;
            border-radius: 8px;
            padding: 1.5rem;
        }
        
        .position-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .position-symbol {
            font-size: 1.2rem;
            font-weight: bold;
        }
        
        .position-direction {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
        }
        
        .long {
            background: #00ff8820;
            color: #00ff88;
        }
        
        .short {
            background: #ff004020;
            color: #ff0040;
        }
        
        .position-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        
        .position-metric {
            display: flex;
            flex-direction: column;
        }
        
        .position-metric-label {
            font-size: 0.75rem;
            color: #888;
            margin-bottom: 0.25rem;
        }
        
        .position-metric-value {
            font-size: 1rem;
            font-weight: 500;
        }
        
        .pnl-positive {
            color: #00ff88;
        }
        
        .pnl-negative {
            color: #ff0040;
        }
        
        .signals-list {
            display: grid;
            gap: 1rem;
        }
        
        .signal-card {
            background: #1a1a1a;
            border-left: 3px solid #00d4ff;
            padding: 1rem;
            border-radius: 4px;
        }
        
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        
        .signal-details {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            font-size: 0.85rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }
        
        .stat-card {
            background: #1a1a1a;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #00d4ff;
            margin-bottom: 0.25rem;
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: #888;
        }
        
        .alert {
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        .alert-success {
            background: #00ff8820;
            border: 1px solid #00ff88;
            color: #00ff88;
        }
        
        .alert-danger {
            background: #ff004020;
            border: 1px solid #ff0040;
            color: #ff0040;
        }
        
        .alert-info {
            background: #00d4ff20;
            border: 1px solid #00d4ff;
            color: #00d4ff;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #333;
            border-top: 3px solid #00d4ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .pipeline-status {
            padding: 0.5rem 1rem;
            background: #2a2a2a;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ff0040;
        }
        
        .status-dot.active {
            background: #00ff88;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">🚀 FUTURES TRADING</div>
        <div class="capital-info">
            <div class="capital-item">
                <span class="capital-label">Capital Total</span>
                <span class="capital-value" id="total-capital">$220.00</span>
            </div>
            <div class="capital-item">
                <span class="capital-label">Margen Disponible</span>
                <span class="capital-value" id="available-margin">$220.00</span>
            </div>
            <div class="capital-item">
                <span class="capital-label">PnL Total</span>
                <span class="capital-value" id="total-pnl">$0.00</span>
            </div>
            <div class="pipeline-status">
                <span class="status-dot" id="pipeline-status"></span>
                <span id="pipeline-text">Pipeline Detenido</span>
            </div>
        </div>
    </header>

    <div class="main-container">
        <aside class="sidebar">
            <div class="section">
                <h3 class="section-title">⚙️ Configuración</h3>
                
                <div class="control-group">
                    <label class="control-label">Max Leverage</label>
                    <input type="number" class="control-input" id="max-leverage" value="5" min="1" max="10">
                </div>
                
                <div class="control-group">
                    <label class="control-label">Risk por Trade (%)</label>
                    <input type="number" class="control-input" id="risk-per-trade" value="2" min="1" max="5" step="0.5">
                </div>
                
                <div class="control-group">
                    <label class="control-label">Max Posiciones</label>
                    <input type="number" class="control-input" id="max-positions" value="2" min="1" max="3">
                </div>
                
                <div class="control-group">
                    <label class="control-label">Min Confianza (%)</label>
                    <input type="number" class="control-input" id="min-confidence" value="70" min="60" max="90">
                </div>
                
                <div class="control-group">
                    <label class="control-label">Estrategia</label>
                    <select class="control-input" id="strategy">
                        <option value="all">Todas</option>
                        <option value="momentum">Momentum</option>
                        <option value="reversal">Reversal</option>
                        <option value="volatility">Volatilidad</option>
                        <option value="funding">Funding Arbitrage</option>
                    </select>
                </div>
            </div>

            <div class="section">
                <h3 class="section-title">🎮 Controles</h3>
                <button class="btn" onclick="scanMarket()">🔍 Escanear Mercado</button>
                <button class="btn" onclick="generateSignals()">📈 Generar Señales</button>
                <button class="btn btn-success" onclick="startPipeline()">▶️ Iniciar Pipeline</button>
                <button class="btn btn-danger" onclick="stopPipeline()">⏸️ Detener Pipeline</button>
            </div>

            <div class="section">
                <h3 class="section-title">📊 Estadísticas</h3>
                <div class="stats-grid" style="grid-template-columns: 1fr;">
                    <div class="stat-card">
                        <div class="stat-value" id="win-rate">0%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="total-trades">0</div>
                        <div class="stat-label">Total Trades</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="roi">0%</div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
            </div>
        </aside>

        <main class="content">
            <div class="section">
                <h2 class="section-title">📈 Mejores Oportunidades</h2>
                <div class="pairs-grid" id="pairs-grid">
                    <div class="alert alert-info">
                        Haz click en "Escanear Mercado" para buscar oportunidades
                    </div>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">💼 Posiciones Activas</h2>
                <div class="positions-container" id="positions-container">
                    <div class="alert alert-info">
                        No hay posiciones activas
                    </div>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">🎯 Señales Recientes</h2>
                <div class="signals-list" id="signals-list">
                    <div class="alert alert-info">
                        No hay señales generadas
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        // Estado
        let ws = null;
        let pipelineRunning = false;
        
        // Formateo
        function formatCurrency(value) {
            return '$' + parseFloat(value).toFixed(2);
        }
        
        function formatPercent(value) {
            return parseFloat(value).toFixed(1) + '%';
        }
        
        // Escanear mercado
        async function scanMarket() {
            const grid = document.getElementById('pairs-grid');
            grid.innerHTML = '<div class="loading"></div> Escaneando mercado de futuros...';
            
            try {
                const response = await fetch('/api/futures/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        strategy: document.getElementById('strategy').value
                    })
                });
                
                const pairs = await response.json();
                displayPairs(pairs);
            } catch (error) {
                grid.innerHTML = '<div class="alert alert-danger">Error: ' + error.message + '</div>';
            }
        }
        
        // Mostrar pares
        function displayPairs(pairs) {
            const grid = document.getElementById('pairs-grid');
            
            if (pairs.length === 0) {
                grid.innerHTML = '<div class="alert alert-info">No se encontraron oportunidades</div>';
                return;
            }
            
            let html = '';
            pairs.forEach(pair => {
                html += `
                    <div class="pair-card">
                        <div class="pair-symbol">${pair.symbol}</div>
                        <div class="pair-metrics">
                            <div class="metric">
                                <span class="metric-label">Precio:</span>
                                <span class="metric-value">$${pair.mark_price.toFixed(4)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Volumen:</span>
                                <span class="metric-value">$${(pair.volume_24h/1e6).toFixed(1)}M</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Volatilidad:</span>
                                <span class="metric-value">${pair.volatility.toFixed(2)}%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Funding:</span>
                                <span class="metric-value">${(pair.funding_rate*100).toFixed(3)}%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Long/Short:</span>
                                <span class="metric-value">${pair.long_ratio.toFixed(0)}/${pair.short_ratio.toFixed(0)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Score:</span>
                                <span class="metric-value" style="color: #00d4ff;">${pair.score.toFixed(0)}</span>
                            </div>
                        </div>
                        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #333;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span class="position-direction ${pair.recommended_direction.toLowerCase()}" style="font-size: 0.9rem;">
                                    ${pair.recommended_direction === 'LONG' ? '🟢' : pair.recommended_direction === 'SHORT' ? '🔴' : '⚪'} ${pair.recommended_direction}
                                </span>
                                <span style="font-size: 0.8rem; color: #888;">${pair.direction_confidence}% confianza</span>
                            </div>
                            <div style="font-size: 0.75rem; color: #aaa; margin-top: 0.25rem;">${pair.direction_reason}</div>
                        </div>
                    </div>
                `;
            });
            
            grid.innerHTML = html;
        }
        
        // Generar señales
        async function generateSignals() {
            const list = document.getElementById('signals-list');
            list.innerHTML = '<div class="loading"></div> Generando señales...';
            
            try {
                const response = await fetch('/api/futures/signals', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        min_confidence: parseFloat(document.getElementById('min-confidence').value)
                    })
                });
                
                const signals = await response.json();
                displaySignals(signals);
            } catch (error) {
                list.innerHTML = '<div class="alert alert-danger">Error: ' + error.message + '</div>';
            }
        }
        
        // Mostrar señales
        function displaySignals(signals) {
            const list = document.getElementById('signals-list');
            
            if (signals.length === 0) {
                list.innerHTML = '<div class="alert alert-info">No hay señales disponibles</div>';
                return;
            }
            
            let html = '';
            signals.forEach(signal => {
                const directionClass = signal.direction === 'LONG' ? 'long' : 'short';
                html += `
                    <div class="signal-card">
                        <div class="signal-header">
                            <span class="position-symbol">${signal.symbol}</span>
                            <span class="position-direction ${directionClass}">${signal.direction}</span>
                        </div>
                        <div class="signal-details">
                            <div>
                                <div class="position-metric-label">Entrada</div>
                                <div class="position-metric-value">$${signal.entry_price.toFixed(4)}</div>
                            </div>
                            <div>
                                <div class="position-metric-label">Stop Loss</div>
                                <div class="position-metric-value">$${signal.stop_loss.toFixed(4)}</div>
                            </div>
                            <div>
                                <div class="position-metric-label">Take Profit</div>
                                <div class="position-metric-value">$${signal.take_profit.toFixed(4)}</div>
                            </div>
                            <div>
                                <div class="position-metric-label">Leverage</div>
                                <div class="position-metric-value">${signal.leverage}x</div>
                            </div>
                        </div>
                        <div style="margin-top: 0.5rem; display: flex; gap: 1rem; font-size: 0.85rem;">
                            <span>R:R ${signal.risk_reward.toFixed(2)}</span>
                            <span>Confianza: ${signal.confidence}%</span>
                            <span>Riesgo: $${signal.risk_amount.toFixed(2)}</span>
                        </div>
                        ${signal.is_actionable ? `
                        <div style="margin-top: 0.5rem; padding: 0.5rem; background: #00ff8820; border-radius: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: #00ff88; font-size: 0.85rem;">✅ OPERABLE AHORA</span>
                                <span style="color: #aaa; font-size: 0.75rem;">${Math.floor(signal.time_remaining / 60)} min restantes</span>
                            </div>
                            <button class="btn btn-success" style="margin-top: 0.5rem; padding: 0.5rem;" onclick="executeSignal('${signal.symbol}', '${signal.direction}', ${signal.leverage})">Ejecutar Trade</button>
                        </div>
                        ` : ''}
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }
        
        // Iniciar pipeline
        async function startPipeline() {
            if (pipelineRunning) {
                alert('El pipeline ya está en ejecución');
                return;
            }
            
            const config = {
                max_leverage: parseInt(document.getElementById('max-leverage').value),
                risk_per_trade: parseFloat(document.getElementById('risk-per-trade').value) / 100,
                max_positions: parseInt(document.getElementById('max-positions').value),
                min_confidence: parseFloat(document.getElementById('min-confidence').value),
                strategy: document.getElementById('strategy').value
            };
            
            try {
                const response = await fetch('/api/futures/pipeline/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                
                if (response.ok) {
                    pipelineRunning = true;
                    document.getElementById('pipeline-status').classList.add('active');
                    document.getElementById('pipeline-text').textContent = 'Pipeline Activo';
                    connectWebSocket();
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        // Detener pipeline
        async function stopPipeline() {
            try {
                const response = await fetch('/api/futures/pipeline/stop', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    pipelineRunning = false;
                    document.getElementById('pipeline-status').classList.remove('active');
                    document.getElementById('pipeline-text').textContent = 'Pipeline Detenido';
                    if (ws) ws.close();
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        // WebSocket
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8501/ws/futures');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        // Actualizar dashboard
        function updateDashboard(data) {
            if (data.capital !== undefined) {
                document.getElementById('total-capital').textContent = formatCurrency(data.capital);
            }
            if (data.available_margin !== undefined) {
                document.getElementById('available-margin').textContent = formatCurrency(data.available_margin);
            }
            if (data.pnl !== undefined) {
                const pnlElement = document.getElementById('total-pnl');
                pnlElement.textContent = formatCurrency(data.pnl);
                pnlElement.className = data.pnl >= 0 ? 'capital-value pnl-positive' : 'capital-value pnl-negative';
            }
            if (data.win_rate !== undefined) {
                document.getElementById('win-rate').textContent = formatPercent(data.win_rate);
            }
            if (data.total_trades !== undefined) {
                document.getElementById('total-trades').textContent = data.total_trades;
            }
            if (data.roi !== undefined) {
                document.getElementById('roi').textContent = formatPercent(data.roi);
            }
            if (data.positions) {
                updatePositions(data.positions);
            }
        }
        
        // Actualizar posiciones
        function updatePositions(positions) {
            const container = document.getElementById('positions-container');
            
            if (positions.length === 0) {
                container.innerHTML = '<div class="alert alert-info">No hay posiciones activas</div>';
                return;
            }
            
            let html = '';
            positions.forEach(pos => {
                const pnlClass = pos.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
                const directionClass = pos.direction === 'LONG' ? 'long' : 'short';
                
                html += `
                    <div class="position-card">
                        <div class="position-header">
                            <span class="position-symbol">${pos.symbol}</span>
                            <span class="position-direction ${directionClass}">${pos.direction} ${pos.leverage}x</span>
                        </div>
                        <div class="position-details">
                            <div class="position-metric">
                                <span class="position-metric-label">Entrada</span>
                                <span class="position-metric-value">$${pos.entry_price.toFixed(4)}</span>
                            </div>
                            <div class="position-metric">
                                <span class="position-metric-label">Actual</span>
                                <span class="position-metric-value">$${pos.current_price.toFixed(4)}</span>
                            </div>
                            <div class="position-metric">
                                <span class="position-metric-label">Tamaño</span>
                                <span class="position-metric-value">${pos.size.toFixed(4)}</span>
                            </div>
                            <div class="position-metric">
                                <span class="position-metric-label">Margen</span>
                                <span class="position-metric-value">$${pos.margin.toFixed(2)}</span>
                            </div>
                            <div class="position-metric">
                                <span class="position-metric-label">PnL</span>
                                <span class="position-metric-value ${pnlClass}">$${pos.pnl.toFixed(2)}</span>
                            </div>
                            <div class="position-metric">
                                <span class="position-metric-label">PnL %</span>
                                <span class="position-metric-value ${pnlClass}">${pos.pnl_percent.toFixed(2)}%</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // Ejecutar señal
        async function executeSignal(symbol, direction, leverage) {
            if (!confirm(`¿Ejecutar ${direction} en ${symbol} con ${leverage}x leverage?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/futures/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        symbol: symbol,
                        direction: direction,
                        leverage: leverage
                    })
                });
                
                if (response.ok) {
                    alert('Trade ejecutado exitosamente');
                    // Actualizar posiciones
                    fetch('/api/futures/status')
                        .then(response => response.json())
                        .then(data => updateDashboard(data));
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.detail);
                }
            } catch (error) {
                alert('Error ejecutando trade: ' + error.message);
            }
        }
        
        // Actualización automática de señales
        setInterval(async function() {
            if (document.getElementById('signals-list').children.length > 0) {
                // Actualizar tiempo restante de señales
                const signals = document.querySelectorAll('.signal-card');
                signals.forEach(signal => {
                    const timeElement = signal.querySelector('[data-time-remaining]');
                    if (timeElement) {
                        let remaining = parseInt(timeElement.dataset.timeRemaining) - 30;
                        if (remaining <= 0) {
                            signal.style.opacity = '0.5';
                            signal.querySelector('.btn-success').disabled = true;
                        }
                        timeElement.dataset.timeRemaining = remaining;
                        timeElement.textContent = Math.floor(remaining / 60) + ' min restantes';
                    }
                });
            }
        }, 30000);  // Cada 30 segundos
        
        // Inicializar
        document.addEventListener('DOMContentLoaded', function() {
            // Cargar datos iniciales
            fetch('/api/futures/status')
                .then(response => response.json())
                .then(data => updateDashboard(data));
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
    """Página principal - Solo Futuros"""
    return HTML_FUTURES_ONLY

@app.get("/api/futures/status")
async def get_status():
    """Estado actual del sistema"""
    return {
        "capital": system_state.capital + sum(system_state.pnl_history),
        "available_margin": system_state.available_margin,
        "pnl": sum(system_state.pnl_history),
        "win_rate": calculate_win_rate(),
        "total_trades": len(system_state.pnl_history),
        "roi": calculate_roi(),
        "positions": get_active_positions()
    }

@app.post("/api/futures/scan")
async def scan_futures_market(strategy: str = "all"):
    """Escanear mercado de futuros con dirección recomendada"""
    
    pairs = await system_state.pair_finder.find_best_opportunities(
        strategy=strategy,
        limit=12
    )
    
    system_state.best_pairs_cache = pairs
    system_state.last_scan = datetime.now()
    
    # Formatear respuesta con análisis de dirección
    result = []
    for pair in pairs:
        # Determinar dirección recomendada
        direction = analyze_direction(pair)
        
        result.append({
            "symbol": pair.symbol,
            "mark_price": pair.mark_price,
            "volume_24h": pair.volume_24h_usd,
            "volatility": pair.volatility,
            "funding_rate": pair.funding_rate,
            "long_ratio": pair.long_ratio,
            "short_ratio": pair.short_ratio,
            "score": calculate_opportunity_score(pair),
            "recommended_direction": direction["direction"],
            "direction_confidence": direction["confidence"],
            "direction_reason": direction["reason"]
        })
    
    return result

@app.post("/api/futures/signals")
async def generate_futures_signals(min_confidence: float = 70):
    """Generar señales de trading operables en tiempo real"""
    
    if not system_state.best_pairs_cache:
        raise HTTPException(status_code=400, detail="Primero escanea el mercado")
    
    signals = []
    current_time = datetime.now()
    
    for pair in system_state.best_pairs_cache[:6]:
        signal = await system_state.futures_system.generate_futures_signal(pair)
        
        if signal and signal.confidence >= min_confidence:
            # Verificar si la señal es operable ahora
            time_since_signal = (current_time - signal.created_at).seconds
            
            # Solo señales de los últimos 15 minutos son operables
            if time_since_signal < 900:  # 15 minutos
                # Calcular tamaño con $220
                position_info = system_state.futures_system.calculate_position_size(
                    signal, 
                    signal.recommended_leverage
                )
                
                # Verificar que tengamos margen suficiente
                if position_info['margin_required'] <= system_state.available_margin:
                    signals.append({
                        "symbol": signal.pair.symbol,
                        "direction": signal.direction,
                        "entry_price": signal.entry_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit_2,
                        "leverage": signal.recommended_leverage,
                        "confidence": signal.confidence,
                        "risk_reward": signal.risk_reward_ratio,
                        "risk_amount": position_info['max_loss'],
                        "margin_required": position_info['margin_required'],
                        "position_size": position_info['quantity'],
                        "time_remaining": 900 - time_since_signal,  # Segundos restantes
                        "is_actionable": True,
                        "signal_type": signal.signal_type.value
                    })
            
            system_state.signals_history.append(signal)
    
    # Ordenar por confianza
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    return signals

@app.post("/api/futures/pipeline/start")
async def start_futures_pipeline(config: FuturesConfig):
    """Iniciar pipeline automatizado"""
    
    system_state.futures_system.futures_config.update({
        "max_leverage": config.max_leverage,
        "risk_per_trade": config.risk_per_trade,
        "max_positions": config.max_positions
    })
    
    system_state.pipeline_running = True
    
    # Iniciar tarea asíncrona
    asyncio.create_task(run_pipeline(config))
    
    return {"status": "started", "message": f"Pipeline iniciado con capital ${INITIAL_CAPITAL}"}

@app.post("/api/futures/pipeline/stop")
async def stop_futures_pipeline():
    """Detener pipeline"""
    system_state.pipeline_running = False
    return {"status": "stopped"}

@app.post("/api/futures/execute")
async def execute_trade(request: PositionRequest):
    """Ejecutar trade manualmente"""
    
    # Verificar margen disponible
    margin_required = (request.amount * request.leverage) / 100  # Simplificado
    
    if margin_required > system_state.available_margin:
        raise HTTPException(
            status_code=400, 
            detail=f"Margen insuficiente. Requerido: ${margin_required:.2f}, Disponible: ${system_state.available_margin:.2f}"
        )
    
    # Verificar posiciones máximas
    if len(system_state.active_positions) >= system_state.futures_system.futures_config['max_positions']:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo de posiciones alcanzado ({system_state.futures_system.futures_config['max_positions']})"
        )
    
    # Crear posición
    position_id = f"{request.symbol}_{datetime.now().timestamp()}"
    system_state.active_positions[request.symbol] = {
        "direction": request.direction,
        "leverage": request.leverage,
        "entry_price": request.amount,  # Precio actual simulado
        "size": margin_required * request.leverage / request.amount,
        "margin": margin_required,
        "opened_at": datetime.now()
    }
    
    # Actualizar margen disponible
    system_state.available_margin -= margin_required
    
    return {
        "status": "executed",
        "position_id": position_id,
        "symbol": request.symbol,
        "direction": request.direction,
        "leverage": request.leverage,
        "margin_used": margin_required,
        "margin_remaining": system_state.available_margin
    }

@app.websocket("/ws/futures")
async def websocket_futures(websocket: WebSocket):
    """WebSocket para actualizaciones en tiempo real"""
    await websocket.accept()
    
    try:
        while True:
            await asyncio.sleep(2)
            
            if system_state.pipeline_running:
                data = {
                    "capital": system_state.capital + sum(system_state.pnl_history),
                    "available_margin": system_state.available_margin,
                    "pnl": sum(system_state.pnl_history),
                    "win_rate": calculate_win_rate(),
                    "total_trades": len(system_state.pnl_history),
                    "roi": calculate_roi(),
                    "positions": get_active_positions()
                }
                
                await websocket.send_json(data)
                
    except WebSocketDisconnect:
        pass

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def calculate_win_rate() -> float:
    if not system_state.pnl_history:
        return 0
    wins = len([p for p in system_state.pnl_history if p > 0])
    return (wins / len(system_state.pnl_history)) * 100

def calculate_roi() -> float:
    total_pnl = sum(system_state.pnl_history)
    return (total_pnl / INITIAL_CAPITAL) * 100

def calculate_opportunity_score(pair) -> float:
    score = 0
    if pair.volume_24h_usd > 100000000:
        score += 30
    if 3 < pair.volatility < 8:
        score += 25
    if abs(pair.funding_rate) > 0.0001:
        score += 20
    if abs(pair.price_change_24h) > 3:
        score += 15
    if pair.spread < 0.05:
        score += 10
    return min(score, 100)

def analyze_direction(pair) -> Dict:
    """Analiza la dirección recomendada para un par"""
    
    direction_score = 0
    reasons = []
    
    # Análisis de momentum
    if pair.price_change_24h > 2:
        direction_score += 30
        reasons.append("Momentum alcista")
    elif pair.price_change_24h < -2:
        direction_score -= 30
        reasons.append("Momentum bajista")
    
    # Análisis de ratio long/short
    if pair.long_ratio > 60:
        direction_score += 20
        reasons.append(f"Long ratio alto ({pair.long_ratio:.0f}%)")
    elif pair.short_ratio > 60:
        direction_score -= 20
        reasons.append(f"Short ratio alto ({pair.short_ratio:.0f}%)")
    
    # Análisis de funding rate
    if pair.funding_rate > 0.0001:  # Funding positivo alto
        direction_score -= 15  # Favorece shorts
        reasons.append("Funding favorece shorts")
    elif pair.funding_rate < -0.0001:  # Funding negativo
        direction_score += 15  # Favorece longs
        reasons.append("Funding favorece longs")
    
    # Análisis de volumen
    if pair.taker_buy_volume > pair.taker_sell_volume * 1.2:
        direction_score += 10
        reasons.append("Presión compradora")
    elif pair.taker_sell_volume > pair.taker_buy_volume * 1.2:
        direction_score -= 10
        reasons.append("Presión vendedora")
    
    # Determinar dirección
    if direction_score > 20:
        direction = "LONG"
        confidence = min(abs(direction_score), 90)
    elif direction_score < -20:
        direction = "SHORT"
        confidence = min(abs(direction_score), 90)
    else:
        direction = "NEUTRAL"
        confidence = 50
    
    return {
        "direction": direction,
        "confidence": confidence,
        "reason": reasons[0] if reasons else "Mercado lateral"
    }

def get_active_positions() -> List[Dict]:
    positions = []
    for symbol, pos in system_state.active_positions.items():
        # Simular precio actual
        current_price = pos['entry_price'] * (1 + np.random.uniform(-0.02, 0.02))
        
        # Calcular PnL
        if pos['direction'] == 'LONG':
            pnl = (current_price - pos['entry_price']) * pos['size']
        else:
            pnl = (pos['entry_price'] - current_price) * pos['size']
        
        pnl_percent = (pnl / pos['margin']) * 100
        
        positions.append({
            "symbol": symbol,
            "direction": pos['direction'],
            "leverage": pos['leverage'],
            "entry_price": pos['entry_price'],
            "current_price": current_price,
            "size": pos['size'],
            "margin": pos['margin'],
            "pnl": pnl,
            "pnl_percent": pnl_percent
        })
    
    return positions

async def run_pipeline(config: FuturesConfig):
    """Ejecutar pipeline automatizado"""
    while system_state.pipeline_running:
        try:
            # Escanear cada 5 minutos
            if not system_state.last_scan or (datetime.now() - system_state.last_scan).seconds > 300:
                await scan_futures_market(config.strategy)
                
                # Generar señales
                await generate_futures_signals(config.min_confidence)
            
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"Error en pipeline: {e}")
            await asyncio.sleep(60)

# ============================================
# INICIO
# ============================================

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("SISTEMA EXCLUSIVO DE FUTUROS")
    print(f"💰 Capital: ${INITIAL_CAPITAL}")
    print("="*60)
    print("✅ Dashboard: http://localhost:8501")
    print("✅ Solo operaciones con futuros")
    print("✅ Leverage máximo recomendado: 5x")
    print("✅ Risk por trade: $4.40 (2%)")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8501)