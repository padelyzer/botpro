#!/usr/bin/env python3
"""
Pipeline Completo de Daytrading para Temporada Alcista
Sistema modular para análisis, entrada y gestión de operaciones
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalStrength(Enum):
    """Fuerza de la señal de trading"""
    VERY_STRONG = 5
    STRONG = 4
    MODERATE = 3
    WEAK = 2
    VERY_WEAK = 1
    NO_SIGNAL = 0

class MarketPhase(Enum):
    """Fase del mercado para esta temporada"""
    ACCUMULATION = "accumulation"
    MARKUP = "markup"           # Bull run principal
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"

@dataclass
class TradingPair:
    """Información completa de un par de trading"""
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    volatility: float
    liquidity_score: float
    trend_score: float
    momentum_score: float
    last_update: datetime
    indicators: Dict = field(default_factory=dict)
    
@dataclass
class TradeSignal:
    """Señal de trading con toda la información necesaria"""
    pair: TradingPair
    action: str  # BUY, SELL, HOLD
    strength: SignalStrength
    entry_price: float
    stop_loss: float
    take_profit_1: float  # TP escalonados
    take_profit_2: float
    take_profit_3: float
    position_size: float  # % del capital
    risk_reward: float
    confidence: float
    reasons: List[str]
    timeframe: str
    created_at: datetime
    expires_at: datetime

@dataclass
class ActivePosition:
    """Posición activa en el mercado"""
    signal: TradeSignal
    entry_time: datetime
    entry_price: float
    current_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    status: str  # OPEN, PARTIAL_TP, CLOSED
    tp_hit: int  # Cuántos TPs se han alcanzado

class DaytradingPipeline:
    """
    Pipeline completo de daytrading optimizado para bull market
    """
    
    def __init__(self, initial_capital: float = 10000):
        self.binance_api = "https://api.binance.com/api/v3"
        self.capital = initial_capital
        self.positions: Dict[str, ActivePosition] = {}
        
        # Configuración para temporada alcista
        self.bull_config = {
            "max_positions": 5,
            "position_size_base": 0.2,  # 20% del capital por posición
            "risk_per_trade": 0.02,     # 2% riesgo máximo
            "min_rr_ratio": 2.0,        # Risk/Reward mínimo 1:2
            "tp1_percent": 0.02,         # 2% primer TP
            "tp2_percent": 0.035,        # 3.5% segundo TP
            "tp3_percent": 0.05,         # 5% tercer TP
            "sl_percent": 0.015,         # 1.5% stop loss
            "trailing_stop": True,
            "breakeven_at_tp1": True,
        }
        
        # Top 30 pares para daytrading (alta liquidez + volatilidad)
        self.universe = [
            # Majors
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            # Layer 1s
            "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "NEARUSDT",
            # DeFi
            "LINKUSDT", "UNIUSDT", "AAVEUSDT", "SUSHIUSDT", "CRVUSDT",
            # Layer 2s
            "ARBUSDT", "OPUSDT", "IMXUSDT",
            # Gaming/Metaverse
            "SANDUSDT", "MANAUSDT", "AXSUSDT", "ENJUSDT",
            # AI/New Narratives
            "FETUSDT", "AGIXUSDT", "OCEANUSDT",
            # Memes (alta volatilidad)
            "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "WIFUSDT"
        ]
        
        # Cache de datos
        self.market_data_cache: Dict[str, TradingPair] = {}
        self.last_scan = None
        
    async def fetch_market_data(self, symbol: str) -> Optional[TradingPair]:
        """Obtiene datos completos del mercado para un par"""
        try:
            async with httpx.AsyncClient() as client:
                # Ticker 24h
                ticker_response = await client.get(
                    f"{self.binance_api}/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                # Klines para análisis técnico
                klines_response = await client.get(
                    f"{self.binance_api}/klines",
                    params={
                        "symbol": symbol,
                        "interval": "15m",
                        "limit": 100
                    }
                )
                
                if ticker_response.status_code == 200 and klines_response.status_code == 200:
                    ticker = ticker_response.json()
                    klines = klines_response.json()
                    
                    # Procesar klines
                    closes = [float(k[4]) for k in klines]
                    highs = [float(k[2]) for k in klines]
                    lows = [float(k[3]) for k in klines]
                    volumes = [float(k[5]) for k in klines]
                    
                    # Calcular indicadores
                    indicators = self.calculate_indicators(closes, highs, lows, volumes)
                    
                    # Calcular scores
                    volatility = np.std(closes[-20:]) / np.mean(closes[-20:]) * 100
                    liquidity_score = min(100, float(ticker["quoteVolume"]) / 1000000)  # Normalizado a 100
                    
                    # Trend score basado en EMAs
                    ema_short = self.calculate_ema(closes, 9)
                    ema_long = self.calculate_ema(closes, 21)
                    trend_score = ((ema_short - ema_long) / ema_long * 100) if ema_long > 0 else 0
                    
                    # Momentum score
                    momentum_score = (closes[-1] - closes[-10]) / closes[-10] * 100
                    
                    return TradingPair(
                        symbol=symbol,
                        price=float(ticker["lastPrice"]),
                        volume_24h=float(ticker["quoteVolume"]),
                        change_24h=float(ticker["priceChangePercent"]),
                        volatility=volatility,
                        liquidity_score=liquidity_score,
                        trend_score=trend_score,
                        momentum_score=momentum_score,
                        last_update=datetime.now(),
                        indicators=indicators
                    )
                    
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
        
        return None
    
    def calculate_indicators(self, closes: List[float], highs: List[float], 
                           lows: List[float], volumes: List[float]) -> Dict:
        """Calcula indicadores técnicos"""
        indicators = {}
        
        # EMAs
        indicators['ema_9'] = self.calculate_ema(closes, 9)
        indicators['ema_21'] = self.calculate_ema(closes, 21)
        indicators['ema_50'] = self.calculate_ema(closes, 50)
        
        # RSI
        indicators['rsi'] = self.calculate_rsi(closes, 14)
        
        # VWAP
        indicators['vwap'] = self.calculate_vwap(closes, volumes)
        
        # ATR para volatilidad
        indicators['atr'] = self.calculate_atr(highs, lows, closes, 14)
        
        # Volume analysis
        indicators['volume_ratio'] = volumes[-1] / np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        
        # Price position
        recent_high = max(highs[-20:]) if len(highs) >= 20 else highs[-1]
        recent_low = min(lows[-20:]) if len(lows) >= 20 else lows[-1]
        indicators['price_position'] = (closes[-1] - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
        
        return indicators
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcula EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return 50
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_vwap(self, prices: List[float], volumes: List[float]) -> float:
        """Calcula VWAP"""
        if not prices or not volumes:
            return 0
        
        cumulative_pv = sum(p * v for p, v in zip(prices, volumes))
        cumulative_volume = sum(volumes)
        
        return cumulative_pv / cumulative_volume if cumulative_volume > 0 else prices[-1]
    
    def calculate_atr(self, highs: List[float], lows: List[float], 
                     closes: List[float], period: int = 14) -> float:
        """Calcula ATR (Average True Range)"""
        if len(highs) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_ranges.append(max(high_low, high_close, low_close))
        
        return np.mean(true_ranges[-period:]) if true_ranges else 0
    
    async def screen_pairs(self) -> List[TradingPair]:
        """Escanea y filtra los mejores pares para trading"""
        print("\n📊 Escaneando universo de trading...")
        
        screened_pairs = []
        
        # Fetch data for all pairs in parallel
        tasks = [self.fetch_market_data(symbol) for symbol in self.universe]
        results = await asyncio.gather(*tasks)
        
        for pair_data in results:
            if pair_data:
                # Filtros de calidad
                if (pair_data.volume_24h > 10000000 and  # $10M+ volumen
                    pair_data.volatility > 1.0 and        # Volatilidad mínima
                    pair_data.liquidity_score > 10):      # Liquidez decente
                    
                    screened_pairs.append(pair_data)
                    self.market_data_cache[pair_data.symbol] = pair_data
        
        # Ordenar por potencial (combinación de factores)
        screened_pairs.sort(
            key=lambda x: (x.trend_score * 0.4 + 
                          x.momentum_score * 0.3 + 
                          x.volatility * 0.2 + 
                          x.liquidity_score * 0.1),
            reverse=True
        )
        
        print(f"✅ {len(screened_pairs)} pares pasaron el screening")
        return screened_pairs[:15]  # Top 15 pairs
    
    def generate_signal(self, pair: TradingPair) -> Optional[TradeSignal]:
        """Genera señal de trading para un par"""
        indicators = pair.indicators
        signal_points = 0
        reasons = []
        
        # Sistema de puntos para generar señal
        
        # 1. Trend Analysis (máx 30 puntos)
        if indicators['ema_9'] > indicators['ema_21'] > indicators['ema_50']:
            signal_points += 30
            reasons.append("Tendencia alcista confirmada (EMAs)")
        elif indicators['ema_9'] > indicators['ema_21']:
            signal_points += 15
            reasons.append("Tendencia alcista corto plazo")
        
        # 2. Momentum (máx 25 puntos)
        if pair.momentum_score > 5:
            signal_points += 25
            reasons.append(f"Momentum fuerte: {pair.momentum_score:.1f}%")
        elif pair.momentum_score > 2:
            signal_points += 15
            reasons.append(f"Momentum positivo: {pair.momentum_score:.1f}%")
        
        # 3. RSI (máx 20 puntos)
        rsi = indicators['rsi']
        if 40 < rsi < 70:
            signal_points += 20
            reasons.append(f"RSI en zona óptima: {rsi:.0f}")
        elif 30 < rsi < 40:
            signal_points += 15
            reasons.append(f"RSI oversold, posible rebote: {rsi:.0f}")
        
        # 4. Volume (máx 15 puntos)
        if indicators['volume_ratio'] > 1.5:
            signal_points += 15
            reasons.append(f"Volumen alto: {indicators['volume_ratio']:.1f}x")
        elif indicators['volume_ratio'] > 1.2:
            signal_points += 10
            reasons.append(f"Volumen aumentando: {indicators['volume_ratio']:.1f}x")
        
        # 5. Price Position (máx 10 puntos)
        if 0.2 < indicators['price_position'] < 0.7:
            signal_points += 10
            reasons.append("Precio en zona media del rango")
        
        # Determinar fuerza de señal
        if signal_points >= 80:
            strength = SignalStrength.VERY_STRONG
        elif signal_points >= 65:
            strength = SignalStrength.STRONG
        elif signal_points >= 50:
            strength = SignalStrength.MODERATE
        elif signal_points >= 35:
            strength = SignalStrength.WEAK
        else:
            return None  # No hay señal
        
        # Generar señal solo si es moderada o mejor
        if strength.value >= SignalStrength.MODERATE.value:
            current_price = pair.price
            atr = indicators['atr']
            
            # Calcular niveles dinámicamente basados en ATR
            stop_loss = current_price - (atr * 1.5)
            take_profit_1 = current_price + (atr * 2)
            take_profit_2 = current_price + (atr * 3.5)
            take_profit_3 = current_price + (atr * 5)
            
            # Risk/Reward
            risk = current_price - stop_loss
            reward = take_profit_2 - current_price
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Position sizing basado en fuerza de señal
            base_size = self.bull_config['position_size_base']
            if strength == SignalStrength.VERY_STRONG:
                position_size = base_size * 1.5
            elif strength == SignalStrength.STRONG:
                position_size = base_size * 1.2
            else:
                position_size = base_size
            
            # Limitar posición al capital disponible
            position_size = min(position_size, 1.0 / max(1, len(self.positions) + 1))
            
            return TradeSignal(
                pair=pair,
                action="BUY",
                strength=strength,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                take_profit_3=take_profit_3,
                position_size=position_size,
                risk_reward=rr_ratio,
                confidence=min(95, signal_points),
                reasons=reasons,
                timeframe="15m",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=4)
            )
        
        return None
    
    async def execute_pipeline(self):
        """Ejecuta el pipeline completo de daytrading"""
        print("="*80)
        print("🚀 DAYTRADING PIPELINE - TEMPORADA ALCISTA")
        print("="*80)
        print(f"Capital: ${self.capital:,.2f}")
        print(f"Max Posiciones: {self.bull_config['max_positions']}")
        print(f"Risk por Trade: {self.bull_config['risk_per_trade']*100}%")
        print("="*80)
        
        while True:
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-"*60)
            
            # 1. SCREENING
            top_pairs = await self.screen_pairs()
            
            # 2. SIGNAL GENERATION
            signals = []
            for pair in top_pairs:
                signal = self.generate_signal(pair)
                if signal:
                    signals.append(signal)
            
            # Ordenar señales por fuerza
            signals.sort(key=lambda x: x.strength.value, reverse=True)
            
            print(f"\n📈 Señales Generadas: {len(signals)}")
            
            # 3. POSITION MANAGEMENT
            await self.manage_positions()
            
            # 4. EXECUTE NEW TRADES
            available_slots = self.bull_config['max_positions'] - len(self.positions)
            
            for signal in signals[:available_slots]:
                if signal.strength.value >= SignalStrength.MODERATE.value:
                    await self.open_position(signal)
            
            # 5. PORTFOLIO STATUS
            self.print_portfolio_status()
            
            # Wait before next scan
            await asyncio.sleep(60)  # Scan every minute
    
    async def open_position(self, signal: TradeSignal):
        """Abre una nueva posición"""
        if signal.pair.symbol not in self.positions:
            position = ActivePosition(
                signal=signal,
                entry_time=datetime.now(),
                entry_price=signal.entry_price,
                current_price=signal.entry_price,
                quantity=(self.capital * signal.position_size) / signal.entry_price,
                pnl=0,
                pnl_percent=0,
                status="OPEN",
                tp_hit=0
            )
            
            self.positions[signal.pair.symbol] = position
            
            print(f"\n✅ NUEVA POSICIÓN: {signal.pair.symbol}")
            print(f"   Entrada: ${signal.entry_price:.4f}")
            print(f"   SL: ${signal.stop_loss:.4f} | TP1: ${signal.take_profit_1:.4f}")
            print(f"   Tamaño: {signal.position_size*100:.1f}% | R:R: {signal.risk_reward:.1f}")
            print(f"   Razones: {', '.join(signal.reasons[:2])}")
    
    async def manage_positions(self):
        """Gestiona posiciones abiertas"""
        for symbol, position in list(self.positions.items()):
            # Update current price
            if symbol in self.market_data_cache:
                current_price = self.market_data_cache[symbol].price
                position.current_price = current_price
                
                # Calculate PnL
                position.pnl = (current_price - position.entry_price) * position.quantity
                position.pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
                
                # Check exit conditions
                signal = position.signal
                
                # Stop Loss
                if current_price <= signal.stop_loss:
                    print(f"\n❌ STOP LOSS: {symbol} | PnL: {position.pnl_percent:.2f}%")
                    del self.positions[symbol]
                    continue
                
                # Take Profits escalonados
                if position.tp_hit == 0 and current_price >= signal.take_profit_1:
                    print(f"\n💰 TP1 ALCANZADO: {symbol} | +{position.pnl_percent:.2f}%")
                    position.tp_hit = 1
                    # Mover SL a breakeven
                    if self.bull_config['breakeven_at_tp1']:
                        signal.stop_loss = signal.entry_price
                    # Cerrar 1/3 de la posición
                    position.quantity *= 0.67
                    
                elif position.tp_hit == 1 and current_price >= signal.take_profit_2:
                    print(f"\n💰 TP2 ALCANZADO: {symbol} | +{position.pnl_percent:.2f}%")
                    position.tp_hit = 2
                    # Cerrar otro 1/3 (queda 1/3)
                    position.quantity *= 0.5
                    
                elif position.tp_hit == 2 and current_price >= signal.take_profit_3:
                    print(f"\n🎯 TP3 ALCANZADO: {symbol} | +{position.pnl_percent:.2f}%")
                    del self.positions[symbol]
                    continue
                
                # Check expiry
                if datetime.now() > signal.expires_at:
                    print(f"\n⏱️ Señal expirada: {symbol} | PnL: {position.pnl_percent:.2f}%")
                    del self.positions[symbol]
    
    def print_portfolio_status(self):
        """Imprime estado del portfolio"""
        if self.positions:
            print("\n📊 POSICIONES ACTIVAS:")
            total_pnl = 0
            for symbol, pos in self.positions.items():
                status_icon = "🟢" if pos.pnl_percent > 0 else "🔴"
                print(f"   {status_icon} {symbol}: {pos.pnl_percent:+.2f}% | TP{pos.tp_hit}/3")
                total_pnl += pos.pnl
            
            print(f"\n   💼 PnL Total: ${total_pnl:+,.2f} ({(total_pnl/self.capital)*100:+.2f}%)")
        else:
            print("\n📊 Sin posiciones activas")

# Testing function
async def validate_pipeline():
    """Valida el pipeline de daytrading"""
    pipeline = DaytradingPipeline(initial_capital=10000)
    
    print("="*80)
    print("🔍 VALIDACIÓN DEL PIPELINE DE DAYTRADING")
    print("="*80)
    
    # Test 1: Screening
    print("\n1️⃣ TEST: Screening de Pares")
    print("-"*40)
    top_pairs = await pipeline.screen_pairs()
    
    if top_pairs:
        print(f"✅ Top 5 pares encontrados:")
        for i, pair in enumerate(top_pairs[:5], 1):
            print(f"   {i}. {pair.symbol}: Vol=${pair.volume_24h/1e6:.1f}M, "
                  f"Trend={pair.trend_score:.1f}, Mom={pair.momentum_score:.1f}%")
    
    # Test 2: Signal Generation
    print("\n2️⃣ TEST: Generación de Señales")
    print("-"*40)
    
    signals_generated = 0
    for pair in top_pairs[:5]:
        signal = pipeline.generate_signal(pair)
        if signal:
            signals_generated += 1
            print(f"\n✅ Señal para {pair.symbol}:")
            print(f"   Fuerza: {signal.strength.name}")
            print(f"   Confianza: {signal.confidence:.0f}%")
            print(f"   R:R Ratio: {signal.risk_reward:.2f}")
            print(f"   Razones: {', '.join(signal.reasons[:2])}")
    
    print(f"\n📊 Señales generadas: {signals_generated}/5 pares")
    
    # Test 3: Pipeline Configuration
    print("\n3️⃣ TEST: Configuración Bull Market")
    print("-"*40)
    print(f"✅ Max Posiciones: {pipeline.bull_config['max_positions']}")
    print(f"✅ Risk por Trade: {pipeline.bull_config['risk_per_trade']*100}%")
    print(f"✅ TP Escalonados: {pipeline.bull_config['tp1_percent']*100}%, "
          f"{pipeline.bull_config['tp2_percent']*100}%, "
          f"{pipeline.bull_config['tp3_percent']*100}%")
    print(f"✅ Stop Loss: {pipeline.bull_config['sl_percent']*100}%")
    print(f"✅ Breakeven en TP1: {pipeline.bull_config['breakeven_at_tp1']}")
    
    print("\n" + "="*80)
    print("Pipeline validado y listo para operar!")
    print("Para iniciar: await pipeline.execute_pipeline()")
    
    return pipeline

if __name__ == "__main__":
    # Run validation
    asyncio.run(validate_pipeline())