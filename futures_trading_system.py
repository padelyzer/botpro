#!/usr/bin/env python3
"""
Sistema de Trading para Futuros de Binance
Con buscador inteligente de pares y gestión de apalancamiento
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

class MarketCondition(Enum):
    """Condición del mercado para futuros"""
    STRONG_TREND = "strong_trend"
    MODERATE_TREND = "moderate_trend"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

class FuturesSignalType(Enum):
    """Tipos de señales para futuros"""
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    FUNDING_ARBITRAGE = "funding_arbitrage"

@dataclass
class FuturesPair:
    """Información de un par de futuros"""
    symbol: str
    mark_price: float
    index_price: float
    funding_rate: float
    next_funding_time: datetime
    volume_24h_usd: float
    volume_24h_base: float
    open_interest: float
    open_interest_value: float
    max_leverage: int
    tick_size: float
    contract_type: str  # PERPETUAL, QUARTERLY, etc
    long_ratio: float  # % de traders en long
    short_ratio: float  # % de traders en short
    taker_buy_volume: float
    taker_sell_volume: float
    price_change_24h: float
    high_24h: float
    low_24h: float
    volatility: float
    spread: float
    timestamp: datetime

@dataclass
class FuturesSignal:
    """Señal de trading para futuros"""
    pair: FuturesPair
    signal_type: FuturesSignalType
    direction: str  # LONG or SHORT
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    recommended_leverage: int
    position_size_percent: float
    risk_amount: float
    potential_profit: float
    risk_reward_ratio: float
    confidence: float
    reasons: List[str]
    market_condition: MarketCondition
    created_at: datetime
    expires_at: datetime
    metadata: Dict = field(default_factory=dict)

class FuturesPairFinder:
    """Buscador inteligente de pares de futuros"""
    
    def __init__(self):
        self.binance_futures_api = "https://fapi.binance.com/fapi/v1"
        self.binance_futures_v2 = "https://fapi.binance.com/fapi/v2"
        
        # Criterios de búsqueda
        self.search_criteria = {
            "min_volume_24h": 50000000,  # $50M mínimo
            "min_open_interest": 10000000,  # $10M mínimo
            "max_spread_percent": 0.1,  # 0.1% máximo
            "min_volatility": 1.5,  # 1.5% mínimo para oportunidades
            "max_volatility": 15,  # 15% máximo para control de riesgo
        }
        
        # Cache de datos
        self.pairs_cache = {}
        self.last_update = None
        
    async def get_all_futures_pairs(self) -> List[Dict]:
        """Obtiene todos los pares de futuros disponibles"""
        try:
            async with httpx.AsyncClient() as client:
                # Exchange info
                exchange_info = await client.get(
                    f"{self.binance_futures_api}/exchangeInfo"
                )
                
                if exchange_info.status_code == 200:
                    data = exchange_info.json()
                    # Filtrar solo PERPETUAL activos
                    pairs = [
                        s for s in data['symbols'] 
                        if s['contractType'] == 'PERPETUAL' 
                        and s['status'] == 'TRADING'
                        and s['quoteAsset'] == 'USDT'
                    ]
                    return pairs
                    
        except Exception as e:
            logger.error(f"Error getting futures pairs: {e}")
        
        return []
    
    async def get_pair_metrics(self, symbol: str) -> Optional[FuturesPair]:
        """Obtiene métricas completas de un par de futuros"""
        try:
            async with httpx.AsyncClient() as client:
                # Múltiples llamadas en paralelo
                tasks = [
                    # Ticker 24hr
                    client.get(
                        f"{self.binance_futures_api}/ticker/24hr",
                        params={"symbol": symbol}
                    ),
                    # Funding rate
                    client.get(
                        f"{self.binance_futures_api}/premiumIndex",
                        params={"symbol": symbol}
                    ),
                    # Open Interest
                    client.get(
                        f"{self.binance_futures_api}/openInterest",
                        params={"symbol": symbol}
                    ),
                    # Long/Short Ratio
                    client.get(
                        f"{self.binance_futures_v2}/positionSide/dual",
                        params={"symbol": symbol, "period": "5m"}
                    ),
                    # Order book (para spread)
                    client.get(
                        f"{self.binance_futures_api}/depth",
                        params={"symbol": symbol, "limit": 5}
                    ),
                    # Klines para volatilidad
                    client.get(
                        f"{self.binance_futures_api}/klines",
                        params={
                            "symbol": symbol,
                            "interval": "1h",
                            "limit": 24
                        }
                    )
                ]
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar respuestas
                ticker = responses[0].json() if not isinstance(responses[0], Exception) and responses[0].status_code == 200 else None
                premium = responses[1].json() if not isinstance(responses[1], Exception) and responses[1].status_code == 200 else None
                open_interest = responses[2].json() if not isinstance(responses[2], Exception) and responses[2].status_code == 200 else None
                depth = responses[4].json() if not isinstance(responses[4], Exception) and responses[4].status_code == 200 else None
                klines = responses[5].json() if not isinstance(responses[5], Exception) and responses[5].status_code == 200 else None
                
                if not ticker or not premium:
                    return None
                
                # Calcular volatilidad
                volatility = 0
                if klines:
                    closes = [float(k[4]) for k in klines]
                    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                    volatility = np.std(returns) * np.sqrt(24) * 100  # Volatilidad diaria
                
                # Calcular spread
                spread = 0
                if depth:
                    best_bid = float(depth['bids'][0][0]) if depth['bids'] else 0
                    best_ask = float(depth['asks'][0][0]) if depth['asks'] else 0
                    if best_bid and best_ask:
                        spread = ((best_ask - best_bid) / best_bid) * 100
                
                # Calcular buy/sell volume
                taker_buy = float(ticker.get('buyQuoteVolume', 0)) if ticker else 0
                taker_sell = float(ticker.get('sellQuoteVolume', 0)) if ticker else 0
                total_volume = taker_buy + taker_sell
                
                # Long/Short ratio
                long_ratio = (taker_buy / total_volume * 100) if total_volume > 0 else 50
                short_ratio = 100 - long_ratio
                
                return FuturesPair(
                    symbol=symbol,
                    mark_price=float(premium.get('markPrice', 0)) if premium else 0,
                    index_price=float(premium.get('indexPrice', 0)) if premium else 0,
                    funding_rate=float(premium.get('lastFundingRate', 0)) if premium else 0,
                    next_funding_time=datetime.fromtimestamp(
                        int(premium.get('nextFundingTime', 0)) / 1000
                    ) if premium else datetime.now(),
                    volume_24h_usd=float(ticker.get('quoteVolume', 0)) if ticker else 0,
                    volume_24h_base=float(ticker.get('volume', 0)) if ticker else 0,
                    open_interest=float(open_interest.get('openInterest', 0)) if open_interest else 0,
                    open_interest_value=float(open_interest.get('openInterest', 0)) * float(ticker.get('lastPrice', 0)) if open_interest and ticker else 0,
                    max_leverage=125,  # Default para USDT perpetual
                    tick_size=0.01,  # Simplificado
                    contract_type="PERPETUAL",
                    long_ratio=long_ratio,
                    short_ratio=short_ratio,
                    taker_buy_volume=taker_buy,
                    taker_sell_volume=taker_sell,
                    price_change_24h=float(ticker.get('priceChangePercent', 0)) if ticker else 0,
                    high_24h=float(ticker.get('highPrice', 0)) if ticker else 0,
                    low_24h=float(ticker.get('lowPrice', 0)) if ticker else 0,
                    volatility=volatility,
                    spread=spread,
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Error getting metrics for {symbol}: {e}")
        
        return None
    
    async def find_best_opportunities(self, 
                                     strategy: str = "all",
                                     limit: int = 10) -> List[FuturesPair]:
        """
        Encuentra las mejores oportunidades según estrategia
        
        Estrategias:
        - momentum: Pares con fuerte momentum
        - reversal: Pares sobrevendidos/sobrecomprados
        - volatility: Alta volatilidad para scalping
        - funding: Funding rate arbitrage
        - volume: Mayor volumen y liquidez
        - all: Combinación de todas
        """
        
        print("\n🔍 Buscando mejores oportunidades en Futuros...")
        
        # Obtener todos los pares
        all_pairs = await self.get_all_futures_pairs()
        print(f"📊 Analizando {len(all_pairs)} pares...")
        
        # Obtener métricas para cada par
        tasks = []
        symbols = [p['symbol'] for p in all_pairs[:50]]  # Top 50 por volumen
        
        for symbol in symbols:
            tasks.append(self.get_pair_metrics(symbol))
        
        pairs_data = await asyncio.gather(*tasks)
        
        # Filtrar None y aplicar criterios mínimos
        valid_pairs = []
        for pair in pairs_data:
            if pair and self._meets_minimum_criteria(pair):
                valid_pairs.append(pair)
        
        print(f"✅ {len(valid_pairs)} pares cumplen criterios mínimos")
        
        # Scoring según estrategia
        scored_pairs = []
        for pair in valid_pairs:
            score = self._calculate_opportunity_score(pair, strategy)
            if score > 0:
                scored_pairs.append((pair, score))
        
        # Ordenar por score
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Retornar top N
        top_pairs = [pair for pair, score in scored_pairs[:limit]]
        
        print(f"\n🎯 Top {len(top_pairs)} oportunidades encontradas:")
        for i, pair in enumerate(top_pairs[:5], 1):
            print(f"  {i}. {pair.symbol}: Vol=${pair.volume_24h_usd/1e6:.1f}M, "
                  f"Chg={pair.price_change_24h:.1f}%, "
                  f"Funding={pair.funding_rate*100:.3f}%")
        
        return top_pairs
    
    def _meets_minimum_criteria(self, pair: FuturesPair) -> bool:
        """Verifica si un par cumple criterios mínimos"""
        return (
            pair.volume_24h_usd >= self.search_criteria["min_volume_24h"] and
            pair.open_interest_value >= self.search_criteria["min_open_interest"] and
            pair.spread <= self.search_criteria["max_spread_percent"] and
            self.search_criteria["min_volatility"] <= pair.volatility <= self.search_criteria["max_volatility"]
        )
    
    def _calculate_opportunity_score(self, pair: FuturesPair, strategy: str) -> float:
        """Calcula score de oportunidad según estrategia"""
        score = 0
        
        if strategy in ["momentum", "all"]:
            # Momentum score
            if pair.price_change_24h > 5 and pair.long_ratio > 60:
                score += 30
            elif pair.price_change_24h < -5 and pair.short_ratio > 60:
                score += 30
        
        if strategy in ["reversal", "all"]:
            # Reversal score
            if pair.price_change_24h > 10 and pair.short_ratio > 55:
                score += 25  # Posible reversión bajista
            elif pair.price_change_24h < -10 and pair.long_ratio > 55:
                score += 25  # Posible reversión alcista
        
        if strategy in ["volatility", "all"]:
            # Volatility score (sweet spot para scalping)
            if 3 < pair.volatility < 8:
                score += 20
        
        if strategy in ["funding", "all"]:
            # Funding arbitrage score
            if abs(pair.funding_rate) > 0.0001:  # 0.01%
                score += 15
            if abs(pair.funding_rate) > 0.0003:  # 0.03%
                score += 10
        
        if strategy in ["volume", "all"]:
            # Volume score
            if pair.volume_24h_usd > 100000000:  # $100M+
                score += 10
            if pair.volume_24h_usd > 500000000:  # $500M+
                score += 10
        
        # Bonus por liquidez y spread tight
        if pair.spread < 0.05:
            score += 5
        
        return score

class FuturesTradingSystem:
    """Sistema completo de trading para futuros"""
    
    def __init__(self, initial_capital: float = 10000):
        self.pair_finder = FuturesPairFinder()
        self.binance_futures_api = "https://fapi.binance.com/fapi/v1"
        
        self.capital = initial_capital
        self.positions = {}
        
        # Configuración de futuros
        self.futures_config = {
            "max_positions": 3,
            "max_leverage": 10,  # Conservador
            "default_leverage": 5,
            "risk_per_trade": 0.02,  # 2% del capital
            "max_daily_loss": 0.05,  # 5% pérdida máxima diaria
            "use_cross_margin": False,  # Isolated margin por defecto
            "auto_deleverage_at_loss": 0.03,  # Reducir leverage si pérdida > 3%
            
            # Take profits escalonados
            "tp1_percent": 0.015,  # 1.5%
            "tp2_percent": 0.03,   # 3%
            "tp3_percent": 0.05,   # 5%
            "tp_sizes": [0.4, 0.3, 0.3],  # 40%, 30%, 30%
            
            # Risk management
            "use_trailing_stop": True,
            "trailing_distance": 0.01,  # 1%
            "breakeven_at_tp1": True,
        }
        
        # Estado del sistema
        self.daily_pnl = 0
        self.daily_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
    def calculate_position_size(self, signal: FuturesSignal, leverage: int) -> Dict:
        """Calcula el tamaño de posición para futuros"""
        
        # Capital disponible
        available_capital = self.capital * (1 - len(self.positions) * 0.2)  # Reservar capital
        
        # Riesgo máximo por trade
        max_risk = self.capital * self.futures_config["risk_per_trade"]
        
        # Distancia al stop loss
        entry = signal.entry_price
        stop = signal.stop_loss
        distance_to_stop = abs(entry - stop) / entry
        
        # Tamaño sin leverage
        position_value = max_risk / distance_to_stop
        
        # Aplicar leverage
        margin_required = position_value / leverage
        
        # Verificar que no exceda capital disponible
        if margin_required > available_capital * 0.3:  # Max 30% del capital disponible
            margin_required = available_capital * 0.3
            position_value = margin_required * leverage
        
        # Cantidad de contratos
        quantity = position_value / entry
        
        return {
            "quantity": quantity,
            "position_value": position_value,
            "margin_required": margin_required,
            "leverage": leverage,
            "max_loss": max_risk,
            "risk_percent": (max_risk / self.capital) * 100
        }
    
    def analyze_market_condition(self, pair: FuturesPair) -> MarketCondition:
        """Analiza la condición actual del mercado"""
        
        # Volatilidad
        if pair.volatility > 10:
            return MarketCondition.HIGH_VOLATILITY
        elif pair.volatility < 2:
            return MarketCondition.LOW_VOLATILITY
        
        # Tendencia
        if abs(pair.price_change_24h) > 5:
            return MarketCondition.STRONG_TREND
        elif abs(pair.price_change_24h) > 2:
            return MarketCondition.MODERATE_TREND
        
        return MarketCondition.RANGING
    
    async def generate_futures_signal(self, pair: FuturesPair) -> Optional[FuturesSignal]:
        """Genera señal de trading para futuros"""
        
        try:
            async with httpx.AsyncClient() as client:
                # Obtener klines para análisis técnico
                klines_response = await client.get(
                    f"{self.binance_futures_api}/klines",
                    params={
                        "symbol": pair.symbol,
                        "interval": "15m",
                        "limit": 100
                    }
                )
                
                if klines_response.status_code != 200:
                    return None
                
                klines = klines_response.json()
                closes = [float(k[4]) for k in klines]
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                
                # Análisis técnico básico
                sma_20 = np.mean(closes[-20:])
                sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma_20
                
                current_price = closes[-1]
                
                # ATR para stops
                atr = self._calculate_atr(highs, lows, closes)
                
                # Condición del mercado
                market_condition = self.analyze_market_condition(pair)
                
                # Lógica de señales
                signal_type = None
                direction = None
                confidence = 0
                reasons = []
                
                # 1. Señal de Momentum
                if pair.price_change_24h > 3 and pair.long_ratio > 60 and current_price > sma_20:
                    signal_type = FuturesSignalType.MOMENTUM
                    direction = "LONG"
                    confidence = 75
                    reasons.append(f"Momentum alcista: {pair.price_change_24h:.1f}%")
                    reasons.append(f"Long ratio dominante: {pair.long_ratio:.0f}%")
                    
                elif pair.price_change_24h < -3 and pair.short_ratio > 60 and current_price < sma_20:
                    signal_type = FuturesSignalType.MOMENTUM
                    direction = "SHORT"
                    confidence = 75
                    reasons.append(f"Momentum bajista: {pair.price_change_24h:.1f}%")
                    reasons.append(f"Short ratio dominante: {pair.short_ratio:.0f}%")
                
                # 2. Señal de Breakout
                recent_high = max(highs[-20:])
                recent_low = min(lows[-20:])
                
                if current_price > recent_high * 0.995 and pair.volume_24h_usd > 100000000:
                    signal_type = FuturesSignalType.BREAKOUT
                    direction = "LONG"
                    confidence = 80
                    reasons.append("Rompimiento de resistencia")
                    reasons.append(f"Alto volumen: ${pair.volume_24h_usd/1e6:.0f}M")
                    
                elif current_price < recent_low * 1.005 and pair.volume_24h_usd > 100000000:
                    signal_type = FuturesSignalType.BREAKOUT
                    direction = "SHORT"
                    confidence = 80
                    reasons.append("Rompimiento de soporte")
                    reasons.append(f"Alto volumen: ${pair.volume_24h_usd/1e6:.0f}M")
                
                # 3. Funding Rate Arbitrage
                if abs(pair.funding_rate) > 0.0003:  # 0.03%
                    if pair.funding_rate > 0.0003:
                        # Funding positivo alto, favorece shorts
                        signal_type = FuturesSignalType.FUNDING_ARBITRAGE
                        direction = "SHORT"
                        confidence = 70
                        reasons.append(f"Funding rate alto: {pair.funding_rate*100:.3f}%")
                        reasons.append("Arbitraje de funding favorable")
                    else:
                        # Funding negativo alto, favorece longs
                        signal_type = FuturesSignalType.FUNDING_ARBITRAGE
                        direction = "LONG"
                        confidence = 70
                        reasons.append(f"Funding rate negativo: {pair.funding_rate*100:.3f}%")
                        reasons.append("Cobro de funding favorable")
                
                # Solo generar señal si hay dirección clara
                if not direction or confidence < 60:
                    return None
                
                # Calcular niveles
                if direction == "LONG":
                    entry = current_price
                    stop_loss = entry - (atr * 1.5)
                    tp1 = entry + (atr * 2)
                    tp2 = entry + (atr * 3.5)
                    tp3 = entry + (atr * 5)
                else:  # SHORT
                    entry = current_price
                    stop_loss = entry + (atr * 1.5)
                    tp1 = entry - (atr * 2)
                    tp2 = entry - (atr * 3.5)
                    tp3 = entry - (atr * 5)
                
                # Calcular leverage recomendado según volatilidad
                if pair.volatility < 3:
                    recommended_leverage = 8
                elif pair.volatility < 5:
                    recommended_leverage = 5
                elif pair.volatility < 8:
                    recommended_leverage = 3
                else:
                    recommended_leverage = 2
                
                # Risk/Reward
                risk = abs(entry - stop_loss)
                reward = abs(tp2 - entry)
                rr_ratio = reward / risk if risk > 0 else 0
                
                # Position sizing
                position_size = 0.2  # 20% base
                if confidence > 80:
                    position_size = 0.3
                elif confidence > 70:
                    position_size = 0.25
                
                return FuturesSignal(
                    pair=pair,
                    signal_type=signal_type,
                    direction=direction,
                    entry_price=entry,
                    stop_loss=stop_loss,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    take_profit_3=tp3,
                    recommended_leverage=recommended_leverage,
                    position_size_percent=position_size,
                    risk_amount=self.capital * self.futures_config["risk_per_trade"],
                    potential_profit=abs(tp2 - entry) * position_size * self.capital / entry,
                    risk_reward_ratio=rr_ratio,
                    confidence=confidence,
                    reasons=reasons,
                    market_condition=market_condition,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=4),
                    metadata={
                        "atr": atr,
                        "sma_20": sma_20,
                        "sma_50": sma_50
                    }
                )
                
        except Exception as e:
            logger.error(f"Error generating signal for {pair.symbol}: {e}")
        
        return None
    
    def _calculate_atr(self, highs: List[float], lows: List[float], 
                      closes: List[float], period: int = 14) -> float:
        """Calcula ATR"""
        if len(highs) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        return np.mean(true_ranges[-period:]) if true_ranges else 0
    
    async def execute_futures_pipeline(self):
        """Pipeline completo de trading de futuros"""
        
        print("="*80)
        print("🚀 SISTEMA DE TRADING DE FUTUROS - BINANCE")
        print("="*80)
        print(f"Capital: ${self.capital:,.2f}")
        print(f"Max Leverage: {self.futures_config['max_leverage']}x")
        print(f"Risk por Trade: {self.futures_config['risk_per_trade']*100}%")
        print(f"Max Posiciones: {self.futures_config['max_positions']}")
        print("="*80)
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-"*60)
                
                # 1. BUSCAR MEJORES OPORTUNIDADES
                best_pairs = await self.pair_finder.find_best_opportunities(
                    strategy="all",
                    limit=10
                )
                
                # 2. GENERAR SEÑALES
                signals = []
                for pair in best_pairs[:5]:  # Analizar top 5
                    signal = await self.generate_futures_signal(pair)
                    if signal:
                        signals.append(signal)
                
                # 3. MOSTRAR SEÑALES
                if signals:
                    print(f"\n📈 {len(signals)} Señales Generadas:")
                    for signal in signals:
                        print(f"\n  🎯 {signal.pair.symbol} - {signal.direction}")
                        print(f"     Tipo: {signal.signal_type.value}")
                        print(f"     Confianza: {signal.confidence}%")
                        print(f"     Entrada: ${signal.entry_price:.4f}")
                        print(f"     SL: ${signal.stop_loss:.4f}")
                        print(f"     TP2: ${signal.take_profit_2:.4f}")
                        print(f"     Leverage: {signal.recommended_leverage}x")
                        print(f"     R:R: {signal.risk_reward_ratio:.2f}")
                        
                        # Calcular position size
                        position_info = self.calculate_position_size(
                            signal, 
                            signal.recommended_leverage
                        )
                        print(f"     Tamaño: {position_info['quantity']:.4f} contratos")
                        print(f"     Margen: ${position_info['margin_required']:.2f}")
                        print(f"     Risk: ${position_info['max_loss']:.2f}")
                        
                        for reason in signal.reasons[:2]:
                            print(f"     • {reason}")
                else:
                    print("\n📊 No hay señales claras en este momento")
                
                # 4. RESUMEN DE ESTADO
                print(f"\n💼 Estado del Portfolio:")
                print(f"   PnL Diario: ${self.daily_pnl:+.2f}")
                print(f"   Trades Hoy: {self.daily_trades}")
                print(f"   Win Rate: {(self.winning_trades/(self.winning_trades+self.losing_trades)*100) if (self.winning_trades+self.losing_trades) > 0 else 0:.1f}%")
                
                # Esperar antes del próximo scan
                await asyncio.sleep(300)  # 5 minutos
                
            except Exception as e:
                logger.error(f"Error in pipeline: {e}")
                await asyncio.sleep(60)

# Testing
async def test_futures_system():
    """Prueba el sistema de futuros"""
    system = FuturesTradingSystem(initial_capital=10000)
    
    print("="*80)
    print("🔍 TEST DEL SISTEMA DE FUTUROS")
    print("="*80)
    
    # Test 1: Buscar mejores pares
    print("\n1️⃣ Buscando mejores oportunidades...")
    best_pairs = await system.pair_finder.find_best_opportunities(
        strategy="all",
        limit=5
    )
    
    # Test 2: Generar señales
    if best_pairs:
        print("\n2️⃣ Generando señales para top pares...")
        for pair in best_pairs[:3]:
            signal = await system.generate_futures_signal(pair)
            
            if signal:
                print(f"\n✅ Señal para {pair.symbol}:")
                print(f"   Dirección: {signal.direction}")
                print(f"   Tipo: {signal.signal_type.value}")
                print(f"   Leverage: {signal.recommended_leverage}x")
                print(f"   R:R: {signal.risk_reward_ratio:.2f}")
                print(f"   Confianza: {signal.confidence}%")
    
    print("\n" + "="*80)
    print("Sistema de futuros validado!")
    print("Para ejecutar: await system.execute_futures_pipeline()")

if __name__ == "__main__":
    asyncio.run(test_futures_system())