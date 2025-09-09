#!/usr/bin/env python3
"""
Sistema Profesional de Trading con Análisis Multi-Estrategia
Integración de señales técnicas, fundamentales y de flujo de mercado
"""

import asyncio
import httpx
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict
import hashlib
import hmac

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Supabase
SUPABASE_URL = "https://qrzzmazvflrpwlsbdvmm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFyenptYXp2ZmxycHdsc2Jkdm1tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ0ODY2MDUsImV4cCI6MjA1MDA2MjYwNX0.l_9v9L90D_Ym9GGfYj1ILmMZzKySQC7HpUCE6rCRqxQ"

class AnalysisModule(Enum):
    """Módulos de análisis del sistema"""
    TECHNICAL = "technical_analysis"
    VOLUME = "volume_analysis"
    MOMENTUM = "momentum_analysis"
    VOLATILITY = "volatility_analysis"
    CORRELATION = "correlation_analysis"
    SENTIMENT = "sentiment_analysis"
    RISK = "risk_management"

@dataclass
class MarketData:
    """Datos de mercado unificados"""
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    high_24h: float
    low_24h: float
    bid: float
    ask: float
    timestamp: datetime
    klines: List[Dict] = field(default_factory=list)
    order_book: Dict = field(default_factory=dict)
    
@dataclass
class TradingSignal:
    """Señal de trading profesional"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    position_size: float
    risk_reward_ratio: float
    analysis_modules: Dict[str, Dict]  # Resultados de cada módulo
    timestamp: datetime
    expires_at: datetime
    metadata: Dict = field(default_factory=dict)

class TechnicalAnalyzer:
    """Módulo de análisis técnico"""
    
    def analyze(self, data: MarketData) -> Dict:
        """Análisis técnico completo"""
        if not data.klines:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        closes = [float(k.get('close', 0)) for k in data.klines]
        highs = [float(k.get('high', 0)) for k in data.klines]
        lows = [float(k.get('low', 0)) for k in data.klines]
        volumes = [float(k.get('volume', 0)) for k in data.klines]
        
        # Indicadores
        sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]
        sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else closes[-1]
        
        # RSI
        rsi = self._calculate_rsi(closes)
        
        # MACD
        macd, signal, histogram = self._calculate_macd(closes)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
        
        # Señal
        score = 0
        if data.price > sma_20 > sma_50:
            score += 30
        if 30 < rsi < 70:
            score += 20
        if macd > signal:
            score += 25
        if bb_lower < data.price < bb_middle:
            score += 25
            
        return {
            "signal": "BUY" if score > 60 else "SELL" if score < 30 else "NEUTRAL",
            "confidence": min(score, 100),
            "indicators": {
                "rsi": rsi,
                "macd": macd,
                "sma_20": sma_20,
                "sma_50": sma_50,
                "bb_position": (data.price - bb_lower) / (bb_upper - bb_lower) if bb_upper > bb_lower else 0.5
            }
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return 50
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float, float]:
        """Calcula MACD"""
        if len(prices) < 26:
            return 0, 0, 0
            
        exp1 = pd.Series(prices).ewm(span=12, adjust=False).mean()
        exp2 = pd.Series(prices).ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        return macd.iloc[-1], signal.iloc[-1], histogram.iloc[-1]
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> Tuple[float, float, float]:
        """Calcula Bollinger Bands"""
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]
            
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        
        return upper, sma, lower

class VolumeAnalyzer:
    """Módulo de análisis de volumen"""
    
    def analyze(self, data: MarketData) -> Dict:
        """Análisis de volumen y flujo"""
        if not data.klines or len(data.klines) < 20:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        volumes = [float(k.get('volume', 0)) for k in data.klines]
        closes = [float(k.get('close', 0)) for k in data.klines]
        
        # Volume Rate of Change
        current_vol = volumes[-1]
        avg_vol = np.mean(volumes[-20:])
        vroc = (current_vol / avg_vol) if avg_vol > 0 else 1
        
        # On-Balance Volume trend
        obv = self._calculate_obv(closes, volumes)
        obv_trend = "UP" if obv[-1] > np.mean(obv[-10:]) else "DOWN"
        
        # Volume-Price Trend
        vpt = self._calculate_vpt(closes, volumes)
        
        # Money Flow Index
        mfi = self._calculate_mfi(data.klines)
        
        # Señal
        score = 0
        if vroc > 1.5:
            score += 35
        elif vroc > 1.2:
            score += 20
            
        if obv_trend == "UP":
            score += 25
            
        if mfi > 50:
            score += 20
        elif mfi > 80:
            score -= 10  # Sobrecomprado
            
        if vpt > 0:
            score += 20
            
        return {
            "signal": "BUY" if score > 60 else "SELL" if score < 30 else "NEUTRAL",
            "confidence": min(score, 100),
            "metrics": {
                "vroc": vroc,
                "obv_trend": obv_trend,
                "mfi": mfi,
                "vpt": vpt,
                "volume_24h_usd": data.volume_24h
            }
        }
    
    def _calculate_obv(self, closes: List[float], volumes: List[float]) -> List[float]:
        """Calcula On-Balance Volume"""
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        return obv
    
    def _calculate_vpt(self, closes: List[float], volumes: List[float]) -> float:
        """Calcula Volume-Price Trend"""
        if len(closes) < 2:
            return 0
            
        vpt = 0
        for i in range(1, len(closes)):
            price_change = (closes[i] - closes[i-1]) / closes[i-1] if closes[i-1] > 0 else 0
            vpt += volumes[i] * price_change
        return vpt
    
    def _calculate_mfi(self, klines: List[Dict], period: int = 14) -> float:
        """Calcula Money Flow Index"""
        if len(klines) < period + 1:
            return 50
            
        typical_prices = [(float(k['high']) + float(k['low']) + float(k['close'])) / 3 for k in klines]
        raw_money_flows = [typical_prices[i] * float(klines[i]['volume']) for i in range(len(klines))]
        
        positive_flows = []
        negative_flows = []
        
        for i in range(1, len(typical_prices)):
            if typical_prices[i] > typical_prices[i-1]:
                positive_flows.append(raw_money_flows[i])
                negative_flows.append(0)
            else:
                positive_flows.append(0)
                negative_flows.append(raw_money_flows[i])
        
        positive_mf = sum(positive_flows[-period:])
        negative_mf = sum(negative_flows[-period:])
        
        if negative_mf == 0:
            return 100
            
        mfi = 100 - (100 / (1 + positive_mf / negative_mf))
        return mfi

class MomentumAnalyzer:
    """Módulo de análisis de momentum"""
    
    def analyze(self, data: MarketData) -> Dict:
        """Análisis de momentum y fuerza del movimiento"""
        if not data.klines or len(data.klines) < 20:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        closes = [float(k.get('close', 0)) for k in data.klines]
        
        # Rate of Change
        roc_5 = self._calculate_roc(closes, 5)
        roc_10 = self._calculate_roc(closes, 10)
        roc_20 = self._calculate_roc(closes, 20)
        
        # Momentum Oscillator
        momentum = self._calculate_momentum(closes)
        
        # Stochastic
        stoch_k, stoch_d = self._calculate_stochastic(data.klines)
        
        # ADX para fuerza de tendencia
        adx = self._calculate_adx(data.klines)
        
        # Señal
        score = 0
        
        if roc_5 > 2 and roc_10 > 3:
            score += 30
        elif roc_5 > 0 and roc_10 > 0:
            score += 15
            
        if momentum > 100:
            score += 25
            
        if 20 < stoch_k < 80:
            score += 20
            
        if adx > 25:  # Tendencia fuerte
            score += 25
            
        return {
            "signal": "BUY" if score > 60 else "SELL" if score < 30 else "NEUTRAL",
            "confidence": min(score, 100),
            "metrics": {
                "roc_5": roc_5,
                "roc_10": roc_10,
                "momentum": momentum,
                "stochastic": stoch_k,
                "adx": adx
            }
        }
    
    def _calculate_roc(self, prices: List[float], period: int) -> float:
        """Calcula Rate of Change"""
        if len(prices) < period + 1:
            return 0
        return ((prices[-1] - prices[-period-1]) / prices[-period-1]) * 100
    
    def _calculate_momentum(self, prices: List[float], period: int = 10) -> float:
        """Calcula Momentum"""
        if len(prices) < period + 1:
            return 100
        return (prices[-1] / prices[-period-1]) * 100
    
    def _calculate_stochastic(self, klines: List[Dict], period: int = 14) -> Tuple[float, float]:
        """Calcula Stochastic Oscillator"""
        if len(klines) < period:
            return 50, 50
            
        highs = [float(k['high']) for k in klines[-period:]]
        lows = [float(k['low']) for k in klines[-period:]]
        close = float(klines[-1]['close'])
        
        highest = max(highs)
        lowest = min(lows)
        
        if highest == lowest:
            return 50, 50
            
        k = ((close - lowest) / (highest - lowest)) * 100
        
        # D es el SMA de K de 3 períodos
        return k, k  # Simplificado
    
    def _calculate_adx(self, klines: List[Dict], period: int = 14) -> float:
        """Calcula Average Directional Index"""
        if len(klines) < period + 1:
            return 0
            
        # Cálculo simplificado de ADX
        highs = [float(k['high']) for k in klines]
        lows = [float(k['low']) for k in klines]
        closes = [float(k['close']) for k in klines]
        
        plus_dm = []
        minus_dm = []
        tr = []
        
        for i in range(1, len(klines)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
            else:
                plus_dm.append(0)
                
            if low_diff > high_diff and low_diff > 0:
                minus_dm.append(low_diff)
            else:
                minus_dm.append(0)
                
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            ))
        
        if not tr:
            return 0
            
        atr = np.mean(tr[-period:])
        plus_di = (np.mean(plus_dm[-period:]) / atr * 100) if atr > 0 else 0
        minus_di = (np.mean(minus_dm[-period:]) / atr * 100) if atr > 0 else 0
        
        if plus_di + minus_di == 0:
            return 0
            
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
        return dx

class ProfessionalTradingSystem:
    """Sistema de Trading Profesional Multi-Estrategia"""
    
    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"
        
        # Analizadores
        self.technical_analyzer = TechnicalAnalyzer()
        self.volume_analyzer = VolumeAnalyzer()
        self.momentum_analyzer = MomentumAnalyzer()
        
        # Configuración profesional
        self.config = {
            "min_confidence": 70,
            "max_positions": 5,
            "risk_per_trade": 0.02,
            "default_rr_ratio": 2.0,
            "use_trailing_stop": True,
            "partial_tp_levels": [0.5, 0.3, 0.2],  # 50%, 30%, 20%
        }
        
        # Cache
        self.market_cache = {}
        self.signal_history = []
        
    async def fetch_market_data(self, symbol: str) -> Optional[MarketData]:
        """Obtiene datos de mercado completos"""
        try:
            async with httpx.AsyncClient() as client:
                # Ticker
                ticker_response = await client.get(
                    f"{self.binance_api}/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                # Klines
                klines_response = await client.get(
                    f"{self.binance_api}/klines",
                    params={
                        "symbol": symbol,
                        "interval": "15m",
                        "limit": 100
                    }
                )
                
                # Order book
                depth_response = await client.get(
                    f"{self.binance_api}/depth",
                    params={
                        "symbol": symbol,
                        "limit": 20
                    }
                )
                
                if all(r.status_code == 200 for r in [ticker_response, klines_response, depth_response]):
                    ticker = ticker_response.json()
                    klines_data = klines_response.json()
                    depth = depth_response.json()
                    
                    # Procesar klines
                    klines = []
                    for k in klines_data:
                        klines.append({
                            'time': k[0],
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        })
                    
                    return MarketData(
                        symbol=symbol,
                        price=float(ticker["lastPrice"]),
                        volume_24h=float(ticker["quoteVolume"]),
                        change_24h=float(ticker["priceChangePercent"]),
                        high_24h=float(ticker["highPrice"]),
                        low_24h=float(ticker["lowPrice"]),
                        bid=float(ticker["bidPrice"]),
                        ask=float(ticker["askPrice"]),
                        timestamp=datetime.now(),
                        klines=klines,
                        order_book=depth
                    )
                    
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
        
        return None
    
    async def analyze_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """Análisis completo de un símbolo"""
        # Obtener datos
        market_data = await self.fetch_market_data(symbol)
        if not market_data:
            return None
        
        # Ejecutar todos los análisis
        analyses = {}
        
        # Análisis Técnico
        technical_result = self.technical_analyzer.analyze(market_data)
        analyses[AnalysisModule.TECHNICAL.value] = technical_result
        
        # Análisis de Volumen
        volume_result = self.volume_analyzer.analyze(market_data)
        analyses[AnalysisModule.VOLUME.value] = volume_result
        
        # Análisis de Momentum
        momentum_result = self.momentum_analyzer.analyze(market_data)
        analyses[AnalysisModule.MOMENTUM.value] = momentum_result
        
        # Consenso
        total_confidence = 0
        buy_signals = 0
        sell_signals = 0
        
        for module, result in analyses.items():
            if result["signal"] == "BUY":
                buy_signals += 1
                total_confidence += result["confidence"]
            elif result["signal"] == "SELL":
                sell_signals += 1
                total_confidence -= result["confidence"]
        
        # Decisión final
        if buy_signals >= 2 and total_confidence > 150:
            action = "BUY"
            final_confidence = total_confidence / len(analyses)
        elif sell_signals >= 2 and abs(total_confidence) > 150:
            action = "SELL"
            final_confidence = abs(total_confidence) / len(analyses)
        else:
            return None  # No hay señal clara
        
        if final_confidence < self.config["min_confidence"]:
            return None
        
        # Calcular niveles
        atr = self._calculate_atr(market_data.klines)
        
        if action == "BUY":
            entry = market_data.price
            stop_loss = entry - (atr * 1.5)
            take_profit = entry + (atr * 3)
        else:
            entry = market_data.price
            stop_loss = entry + (atr * 1.5)
            take_profit = entry - (atr * 3)
        
        rr_ratio = abs(take_profit - entry) / abs(entry - stop_loss)
        
        # Position sizing basado en confianza
        base_size = 0.2  # 20% base
        if final_confidence > 85:
            position_size = base_size * 1.5
        elif final_confidence > 75:
            position_size = base_size * 1.2
        else:
            position_size = base_size
        
        return TradingSignal(
            symbol=symbol,
            action=action,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=final_confidence,
            position_size=position_size,
            risk_reward_ratio=rr_ratio,
            analysis_modules=analyses,
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=4),
            metadata={
                "atr": atr,
                "volume_usd": market_data.volume_24h,
                "24h_change": market_data.change_24h
            }
        )
    
    def _calculate_atr(self, klines: List[Dict], period: int = 14) -> float:
        """Calcula Average True Range"""
        if len(klines) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(1, len(klines)):
            high = klines[i]['high']
            low = klines[i]['low']
            prev_close = klines[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return np.mean(true_ranges[-period:]) if true_ranges else 0
    
    async def save_signal_to_db(self, signal: TradingSignal):
        """Guarda señal en base de datos"""
        try:
            async with httpx.AsyncClient() as client:
                signal_data = {
                    "symbol": signal.symbol,
                    "action": signal.action,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "confidence": signal.confidence,
                    "position_size": signal.position_size,
                    "risk_reward": signal.risk_reward_ratio,
                    "technical_analysis": json.dumps(signal.analysis_modules.get(AnalysisModule.TECHNICAL.value, {})),
                    "volume_analysis": json.dumps(signal.analysis_modules.get(AnalysisModule.VOLUME.value, {})),
                    "momentum_analysis": json.dumps(signal.analysis_modules.get(AnalysisModule.MOMENTUM.value, {})),
                    "created_at": signal.timestamp.isoformat()
                }
                
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/trading_signals",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Content-Type": "application/json"
                    },
                    json=signal_data
                )
                
                if response.status_code == 201:
                    logger.info(f"Signal saved for {signal.symbol}")
                else:
                    logger.error(f"Failed to save signal: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
    
    async def run_analysis_pipeline(self, symbols: List[str]):
        """Ejecuta pipeline de análisis para múltiples símbolos"""
        print("="*80)
        print("SISTEMA PROFESIONAL DE TRADING")
        print("="*80)
        print(f"Analizando {len(symbols)} símbolos...")
        print("-"*80)
        
        signals = []
        
        for symbol in symbols:
            print(f"\n📊 Analizando {symbol}...")
            
            signal = await self.analyze_symbol(symbol)
            
            if signal:
                signals.append(signal)
                
                print(f"✅ SEÑAL DETECTADA: {signal.action}")
                print(f"   Confianza: {signal.confidence:.1f}%")
                print(f"   Entrada: ${signal.entry_price:.4f}")
                print(f"   SL: ${signal.stop_loss:.4f} | TP: ${signal.take_profit:.4f}")
                print(f"   R:R Ratio: {signal.risk_reward_ratio:.2f}")
                print(f"   Tamaño: {signal.position_size*100:.1f}%")
                
                # Guardar en DB
                await self.save_signal_to_db(signal)
            else:
                print(f"   Sin señal clara")
        
        # Resumen
        print("\n" + "="*80)
        print(f"RESUMEN: {len(signals)} señales generadas")
        
        if signals:
            buy_signals = [s for s in signals if s.action == "BUY"]
            sell_signals = [s for s in signals if s.action == "SELL"]
            
            print(f"  • Compras: {len(buy_signals)}")
            print(f"  • Ventas: {len(sell_signals)}")
            print(f"  • Confianza promedio: {np.mean([s.confidence for s in signals]):.1f}%")
            
            print("\nTop 3 señales por confianza:")
            for i, signal in enumerate(sorted(signals, key=lambda x: x.confidence, reverse=True)[:3], 1):
                print(f"  {i}. {signal.symbol}: {signal.action} ({signal.confidence:.1f}%)")
        
        return signals

# Testing
async def test_professional_system():
    """Prueba el sistema profesional"""
    system = ProfessionalTradingSystem()
    
    # Símbolos de prueba
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"]
    
    # Ejecutar análisis
    await system.run_analysis_pipeline(test_symbols)

if __name__ == "__main__":
    asyncio.run(test_professional_system())