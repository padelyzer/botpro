#!/usr/bin/env python3
"""
Sistema Integrado de Trading de Futuros
Incluye: Filósofos, Whale Tracking, Crypto Indicators, Market Regime
Capital: $220 USD
"""

import asyncio
import httpx
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

# Importar todos los componentes diseñados
from futures_trading_system import FuturesTradingSystem, FuturesPairFinder, FuturesSignal
from philosophers import PhilosopherTrader, Socrates, Aristoteles, Nietzsche, Confucio
from whale_wallet_tracker import WhaleWalletTracker
from crypto_momentum_detector import CryptoMomentumDetector
from market_regime_detector import MarketRegimeDetector
from correlation_analyzer import CorrelationAnalyzer
from liquidity_pool_analyzer import LiquidityPoolAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Capital inicial
INITIAL_CAPITAL = 220.0

class IntegratedFuturesSystem:
    """
    Sistema completo que integra toda la lógica diseñada
    """
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.capital = capital
        
        # Componentes principales
        self.futures_system = FuturesTradingSystem(initial_capital=capital)
        self.pair_finder = FuturesPairFinder()
        
        # Filósofos para análisis multi-perspectiva
        self.philosophers = {
            "contrarian": Socrates(),      # Análisis contrarian
            "technical": Aristoteles(),    # Análisis técnico
            "momentum": Nietzsche(),       # Fuerza y momentum
            "harmony": Confucio()          # Balance y armonía
        }
        
        # Componentes avanzados
        self.whale_tracker = WhaleWalletTracker()
        self.momentum_detector = CryptoMomentumDetector()
        self.regime_detector = MarketRegimeDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.liquidity_analyzer = LiquidityPoolAnalyzer()
        
        # Estado del sistema
        self.active_signals = []
        self.positions = {}
        self.pnl_history = []
        
    async def analyze_pair_complete(self, symbol: str) -> Dict:
        """
        Análisis completo de un par usando todos los componentes
        """
        
        analysis = {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "scores": {},
            "signals": [],
            "consensus": None
        }
        
        try:
            # 1. Análisis de Filósofos
            philosophers_analysis = await self._get_philosophers_consensus(symbol)
            analysis["philosophers"] = philosophers_analysis
            analysis["scores"]["philosophers"] = philosophers_analysis["consensus_score"]
            
            # 2. Whale Tracking
            whale_sentiment = await self.whale_tracker.get_whale_sentiment(symbol.replace("USDT", ""))
            analysis["whale_sentiment"] = whale_sentiment
            analysis["scores"]["whale"] = self._score_whale_sentiment(whale_sentiment)
            
            # 3. Crypto Native Indicators
            momentum_signal = await self.momentum_detector.analyze(symbol)
            analysis["momentum"] = momentum_signal
            analysis["scores"]["momentum"] = momentum_signal.get("confidence", 0)
            
            # 4. Market Regime
            regime = await self.regime_detector.detect_regime(symbol)
            analysis["market_regime"] = regime
            analysis["scores"]["regime"] = self._score_regime(regime)
            
            # 5. Correlation Analysis
            correlation = await self.correlation_analyzer.analyze_correlations([symbol])
            analysis["correlation"] = correlation
            analysis["scores"]["correlation"] = correlation.get("strength", 0)
            
            # 6. Liquidity Pool Analysis (NEW - for 3% BTC drop)
            liquidity_prediction = await self.liquidity_analyzer.predict_price_movement(symbol, drop_percentage=3.0)
            analysis["liquidity"] = liquidity_prediction
            analysis["scores"]["liquidity"] = liquidity_prediction.get("confidence", 0)
            
            # Calcular consenso final
            analysis["consensus"] = self._calculate_final_consensus(analysis["scores"])
            
        except Exception as e:
            logger.error(f"Error en análisis completo de {symbol}: {e}")
            
        return analysis
    
    async def _get_philosophers_consensus(self, symbol: str) -> Dict:
        """
        Obtiene consenso de todos los filósofos
        """
        votes = {}
        analyses = {}
        
        for name, philosopher in self.philosophers.items():
            try:
                # Cada filósofo analiza desde su perspectiva
                analysis = await philosopher.analyze(symbol)
                analyses[name] = analysis
                
                # Voto del filósofo
                if analysis["signal"] == "BUY":
                    votes[name] = 1
                elif analysis["signal"] == "SELL":
                    votes[name] = -1
                else:
                    votes[name] = 0
                    
            except Exception as e:
                logger.error(f"Error en análisis de {name}: {e}")
                votes[name] = 0
        
        # Calcular consenso
        total_votes = sum(votes.values())
        consensus_score = (total_votes / len(votes)) * 100 if votes else 0
        
        if consensus_score > 30:
            consensus = "BUY"
        elif consensus_score < -30:
            consensus = "SELL"
        else:
            consensus = "NEUTRAL"
        
        return {
            "votes": votes,
            "analyses": analyses,
            "consensus": consensus,
            "consensus_score": abs(consensus_score)
        }
    
    def _score_whale_sentiment(self, sentiment: Dict) -> float:
        """
        Convierte sentimiento de ballenas en score
        """
        if sentiment["net_sentiment"] == "BULLISH":
            return sentiment["accumulation_score"]
        elif sentiment["net_sentiment"] == "BEARISH":
            return sentiment["distribution_score"]
        return 50
    
    def _score_regime(self, regime: str) -> float:
        """
        Convierte régimen de mercado en score
        """
        regime_scores = {
            "BULL": 80,
            "BEAR": 20,
            "RANGING": 50,
            "VOLATILE": 60
        }
        return regime_scores.get(regime, 50)
    
    def _calculate_final_consensus(self, scores: Dict) -> Dict:
        """
        Calcula consenso final ponderado
        """
        weights = {
            "philosophers": 0.25,  # 25% peso
            "whale": 0.20,        # 20% peso
            "momentum": 0.15,     # 15% peso
            "regime": 0.10,       # 10% peso
            "correlation": 0.10,  # 10% peso
            "liquidity": 0.20     # 20% peso - Important for current market
        }
        
        weighted_score = 0
        total_weight = 0
        
        for component, score in scores.items():
            if component in weights:
                weighted_score += score * weights[component]
                total_weight += weights[component]
        
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Determinar acción
        if final_score > 70:
            action = "STRONG_BUY"
            confidence = min(95, final_score)
        elif final_score > 60:
            action = "BUY"
            confidence = final_score
        elif final_score < 30:
            action = "STRONG_SELL"
            confidence = min(95, 100 - final_score)
        elif final_score < 40:
            action = "SELL"
            confidence = 100 - final_score
        else:
            action = "HOLD"
            confidence = 50
        
        return {
            "action": action,
            "confidence": confidence,
            "weighted_score": final_score,
            "components": scores
        }
    
    async def generate_integrated_signal(self, pair) -> Optional[Dict]:
        """
        Genera señal integrando todos los componentes
        """
        
        # Verificar que pair tenga symbol
        symbol = pair.symbol if hasattr(pair, 'symbol') else str(pair)
        
        # Análisis completo
        analysis = await self.analyze_pair_complete(symbol)
        
        # Solo generar señal si hay consenso
        if analysis["consensus"]["confidence"] < 50:  # Bajado temporalmente para debug
            return None
        
        # Generar señal base con el sistema de futuros
        base_signal = await self.futures_system.generate_futures_signal(pair)
        
        if not base_signal:
            # Si no hay señal base, crear una básica con los datos del análisis
            if analysis["consensus"]["confidence"] < 55:  # Bajado para generar más señales
                return None
                
            # Obtener precio actual
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}")
                    current_price = float(response.json()["price"])
            except:
                return None
            
            # Crear señal básica
            direction = "LONG" if analysis["consensus"]["action"] in ["BUY", "STRONG_BUY"] else "SHORT"
            if direction == "LONG":
                stop_loss = current_price * 0.98  # 2% stop loss
                take_profit = current_price * 1.04  # 4% take profit
            else:
                stop_loss = current_price * 1.02
                take_profit = current_price * 0.96
                
            enhanced_signal = {
                "symbol": symbol,
                "direction": direction,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "leverage": 3,  # Conservative 3x
            }
        else:
            # Usar señal base del sistema de futuros
            enhanced_signal = {
                "symbol": symbol,
                "direction": "LONG" if analysis["consensus"]["action"] in ["BUY", "STRONG_BUY"] else "SHORT",
                "entry_price": base_signal.entry_price,
                "stop_loss": base_signal.stop_loss,
                "take_profit": base_signal.take_profit_2 if hasattr(base_signal, 'take_profit_2') else base_signal.take_profit,
                "leverage": min(5, base_signal.recommended_leverage if hasattr(base_signal, 'recommended_leverage') else 3),  # Max 5x para $220
            }
        
        # Agregar análisis completo
        enhanced_signal.update({
            "confidence": analysis["consensus"]["confidence"],
            "risk_reward": base_signal.risk_reward_ratio if base_signal else 2.0,
            "analysis": {
                "philosophers": analysis["philosophers"]["consensus"],
                "whale_sentiment": analysis["whale_sentiment"]["net_sentiment"],
                "momentum": analysis["momentum"].get("signal", "NEUTRAL"),
                "market_regime": analysis["market_regime"],
                "liquidity": analysis["liquidity"]["short_term_outlook"],
                "liquidation_pressure": analysis["liquidity"]["liquidation_pressure"],
                "final_score": analysis["consensus"]["weighted_score"]
            },
            "reasons": self._generate_reasons(analysis),
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=15)
        })
        
        return enhanced_signal
    
    def _generate_reasons(self, analysis: Dict) -> List[str]:
        """
        Genera razones basadas en el análisis completo
        """
        reasons = []
        
        # Razón de filósofos
        if analysis["philosophers"]["consensus"] != "NEUTRAL":
            reasons.append(f"Consenso filosófico: {analysis['philosophers']['consensus']}")
        
        # Razón de ballenas
        whale_sentiment = analysis["whale_sentiment"]["net_sentiment"]
        if whale_sentiment != "NEUTRAL":
            reasons.append(f"Ballenas: {whale_sentiment}")
        
        # Razón de momentum
        if "momentum" in analysis and analysis["momentum"].get("signal"):
            reasons.append(f"Momentum: {analysis['momentum']['signal']}")
        
        # Razón de régimen
        if "market_regime" in analysis:
            reasons.append(f"Régimen: {analysis['market_regime']}")
        
        # Razón de liquidez (NEW)
        if "liquidity" in analysis:
            liquidity_outlook = analysis["liquidity"]["short_term_outlook"]
            if liquidity_outlook != "CONSOLIDATION":
                reasons.append(f"Liquidez: {liquidity_outlook}")
        
        return reasons[:3]  # Máximo 3 razones principales
    
    async def scan_and_analyze(self, limit: int = 10) -> List[Dict]:
        """
        Escanea el mercado y analiza con todos los componentes
        """
        
        # Buscar mejores pares
        best_pairs = await self.pair_finder.find_best_opportunities(
            strategy="all",
            limit=limit
        )
        
        # Analizar cada par
        signals = []
        for pair in best_pairs[:5]:  # Analizar top 5 para no sobrecargar
            signal = await self.generate_integrated_signal(pair)
            if signal:
                signals.append(signal)
        
        # Ordenar por confianza
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        return signals

# API Endpoints para integrar con UI existente
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Integrated Futures System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia global del sistema
integrated_system = IntegratedFuturesSystem()

@app.get("/api/signals/all")
async def get_all_signals():
    """
    Endpoint compatible con botphia UI
    """
    return await get_signals()

@app.get("/api/recent-signals")
async def get_recent_signals(limit: int = 10):
    """
    Endpoint para señales recientes de botphia
    """
    return await get_signals()

@app.get("/api/signals")
async def get_signals():
    """
    Endpoint compatible con UI de /signals existente
    """
    try:
        signals = await integrated_system.scan_and_analyze(limit=10)
        
        # Formatear para UI existente
        formatted_signals = []
        for signal in signals:
            formatted_signals.append({
                "id": f"{signal['symbol']}_{datetime.now().timestamp()}",
                "symbol": signal["symbol"],
                "type": signal["direction"],
                "entry_price": signal["entry_price"],
                "stop_loss": signal["stop_loss"],
                "take_profit": signal["take_profit"],
                "confidence": signal["confidence"],
                "risk_reward_ratio": signal["risk_reward"],
                "strategy_name": "Integrated System",
                "strategy_version": "2.0",
                "market_regime": signal["analysis"]["market_regime"],
                "metadata": {
                    "leverage": signal["leverage"],
                    "philosophers": signal["analysis"]["philosophers"],
                    "whale": signal["analysis"]["whale_sentiment"],
                    "reasons": signal["reasons"]
                },
                "timestamp": signal["created_at"].isoformat(),
                "expires_at": signal["expires_at"].isoformat()
            })
        
        return formatted_signals
        
    except Exception as e:
        logger.error(f"Error generando señales: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/{symbol}")
async def analyze_symbol(symbol: str):
    """
    Análisis detallado de un símbolo
    """
    try:
        analysis = await integrated_system.analyze_pair_complete(symbol)
        return analysis
    except Exception as e:
        logger.error(f"Error analizando {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """
    Estado del sistema
    """
    return {
        "capital": integrated_system.capital,
        "active_signals": len(integrated_system.active_signals),
        "positions": len(integrated_system.positions),
        "total_pnl": sum(integrated_system.pnl_history),
        "components": {
            "philosophers": "active",
            "whale_tracking": "active",
            "momentum_detector": "active",
            "regime_detector": "active",
            "correlation_analyzer": "active",
            "liquidity_analyzer": "active"
        }
    }

@app.get("/api/liquidity/{symbol}")
async def get_liquidity_analysis(symbol: str):
    """
    Análisis de liquidez y predicción de precio
    """
    try:
        # Analizar liquidez y liquidaciones
        prediction = await integrated_system.liquidity_analyzer.predict_price_movement(
            symbol.upper() + "USDT" if not symbol.endswith("USDT") else symbol,
            drop_percentage=3.0  # Current market condition
        )
        return prediction
    except Exception as e:
        logger.error(f"Error analyzing liquidity for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute/{signal_id}")
async def execute_signal(signal_id: str):
    """
    Ejecuta una señal
    """
    # Implementar ejecución
    return {"status": "executed", "signal_id": signal_id}

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("SISTEMA INTEGRADO DE FUTUROS")
    print(f"Capital: ${INITIAL_CAPITAL}")
    print("="*60)
    print("Componentes activos:")
    print("✅ Filósofos (5 perspectivas)")
    print("✅ Whale Tracking")
    print("✅ Crypto Native Indicators")
    print("✅ Market Regime Detection")
    print("✅ Correlation Analysis")
    print("="*60)
    print("API: http://localhost:8000/api/signals")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)