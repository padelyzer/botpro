#!/usr/bin/env python3
"""
MULTI-TIMEFRAME SIGNAL DETECTOR - BotphIA
Sistema avanzado de detección de señales en múltiples temporalidades
con notificaciones progresivas desde formación hasta confirmación
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURACIÓN DE PARES Y TIMEFRAMES
# ========================================

TRADING_PAIRS = [
    'AVAXUSDT', 'LINKUSDT', 'NEARUSDT', 'XRPUSDT', 
    'PENGUUSDT', 'ADAUSDT', 'SUIUSDT', 'DOTUSDT', 
    'DOGEUSDT', 'UNIUSDT', 'ETHUSDT', 'BTCUSDT'
]

TIMEFRAMES = {
    '5m': {'interval': '5m', 'weight': 0.15, 'bars': 100},
    '15m': {'interval': '15m', 'weight': 0.25, 'bars': 100},
    '1h': {'interval': '1h', 'weight': 0.30, 'bars': 100},
    '4h': {'interval': '4h', 'weight': 0.30, 'bars': 100}
}

class PatternStage(Enum):
    """Etapas de formación de un patrón"""
    POTENTIAL = "potential"       # Posible formación detectada
    FORMING = "forming"           # Patrón formándose
    NEARLY_COMPLETE = "nearly"    # Casi completo
    CONFIRMED = "confirmed"       # Confirmado
    FAILED = "failed"            # Falló la formación

class PatternType(Enum):
    """Tipos de patrones detectables"""
    # Patrones de reversión
    DOUBLE_BOTTOM = "double_bottom"
    DOUBLE_TOP = "double_top"
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    
    # Patrones de continuación
    TRIANGLE_ASC = "triangle_ascending"
    TRIANGLE_DESC = "triangle_descending"
    FLAG_BULL = "flag_bullish"
    FLAG_BEAR = "flag_bearish"
    
    # Patrones de velas
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    DOJI = "doji"
    ENGULFING_BULL = "engulfing_bullish"
    ENGULFING_BEAR = "engulfing_bearish"
    
    # Patrones técnicos
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    SUPPORT_BOUNCE = "support_bounce"
    RESISTANCE_REJECT = "resistance_rejection"

@dataclass
class Signal:
    """Estructura de una señal detectada"""
    id: str
    symbol: str
    timeframe: str
    pattern_type: PatternType
    stage: PatternStage
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    formation_start: datetime
    current_timestamp: datetime
    notes: Dict
    pine_script: Optional[str] = None

class PatternDetector:
    """Detector de patrones técnicos"""
    
    def __init__(self):
        self.min_confidence = 40  # Confianza mínima para notificar
        
    def detect_all_patterns(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[Signal]:
        """Detecta todos los patrones posibles en los datos"""
        signals = []
        
        # Calcular indicadores técnicos
        df = self.calculate_indicators(df)
        
        # Detectar cada tipo de patrón
        patterns_checkers = [
            self.detect_double_bottom,
            self.detect_double_top,
            self.detect_support_bounce,
            self.detect_resistance_rejection,
            self.detect_breakout,
            self.detect_breakdown,
            self.detect_hammer,
            self.detect_engulfing,
            self.detect_triangle
        ]
        
        for checker in patterns_checkers:
            pattern_signals = checker(df, symbol, timeframe)
            if pattern_signals:
                signals.extend(pattern_signals if isinstance(pattern_signals, list) else [pattern_signals])
        
        return [s for s in signals if s and s.confidence >= self.min_confidence]
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos necesarios"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Moving Averages
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Support and Resistance
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def detect_double_bottom(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta patrón de doble suelo"""
        if len(df) < 50:
            return None
            
        recent = df.tail(50)
        lows = recent['low'].values
        
        # Buscar dos mínimos similares
        min_indices = []
        for i in range(5, len(lows) - 5):
            if lows[i] == min(lows[i-5:i+5]):
                min_indices.append(i)
        
        if len(min_indices) >= 2:
            # Verificar que los mínimos sean similares (diferencia < 1%)
            bottom1_idx = min_indices[-2]
            bottom2_idx = min_indices[-1]
            bottom1 = lows[bottom1_idx]
            bottom2 = lows[bottom2_idx]
            
            if abs(bottom1 - bottom2) / bottom1 < 0.01:
                # Verificar que haya un pico entre los dos suelos
                peak_between = max(lows[bottom1_idx:bottom2_idx])
                if peak_between > bottom1 * 1.02:
                    
                    current_price = float(df['close'].iloc[-1])
                    
                    # Determinar stage
                    if bottom2_idx == len(lows) - 1:
                        stage = PatternStage.FORMING
                        confidence = 60
                    elif current_price > peak_between:
                        stage = PatternStage.CONFIRMED
                        confidence = 85
                    else:
                        stage = PatternStage.NEARLY_COMPLETE
                        confidence = 70
                    
                    return Signal(
                        id=f"{symbol}_{timeframe}_DB_{datetime.now().timestamp()}",
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern_type=PatternType.DOUBLE_BOTTOM,
                        stage=stage,
                        confidence=confidence,
                        entry_price=peak_between,
                        stop_loss=min(bottom1, bottom2) * 0.98,
                        take_profit_1=peak_between * 1.05,
                        take_profit_2=peak_between * 1.10,
                        risk_reward_ratio=2.0,
                        formation_start=datetime.now() - timedelta(hours=bottom1_idx),
                        current_timestamp=datetime.now(),
                        notes={
                            'bottom1': bottom1,
                            'bottom2': bottom2,
                            'neckline': peak_between
                        }
                    )
        return None
    
    def detect_double_top(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta patrón de doble techo"""
        if len(df) < 50:
            return None
            
        recent = df.tail(50)
        highs = recent['high'].values
        
        # Buscar dos máximos similares
        max_indices = []
        for i in range(5, len(highs) - 5):
            if highs[i] == max(highs[i-5:i+5]):
                max_indices.append(i)
        
        if len(max_indices) >= 2:
            top1_idx = max_indices[-2]
            top2_idx = max_indices[-1]
            top1 = highs[top1_idx]
            top2 = highs[top2_idx]
            
            if abs(top1 - top2) / top1 < 0.01:
                valley_between = min(highs[top1_idx:top2_idx])
                if valley_between < top1 * 0.98:
                    
                    current_price = float(df['close'].iloc[-1])
                    
                    if top2_idx == len(highs) - 1:
                        stage = PatternStage.FORMING
                        confidence = 60
                    elif current_price < valley_between:
                        stage = PatternStage.CONFIRMED
                        confidence = 85
                    else:
                        stage = PatternStage.NEARLY_COMPLETE
                        confidence = 70
                    
                    return Signal(
                        id=f"{symbol}_{timeframe}_DT_{datetime.now().timestamp()}",
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern_type=PatternType.DOUBLE_TOP,
                        stage=stage,
                        confidence=confidence,
                        entry_price=valley_between,
                        stop_loss=max(top1, top2) * 1.02,
                        take_profit_1=valley_between * 0.95,
                        take_profit_2=valley_between * 0.90,
                        risk_reward_ratio=2.0,
                        formation_start=datetime.now() - timedelta(hours=top1_idx),
                        current_timestamp=datetime.now(),
                        notes={
                            'top1': top1,
                            'top2': top2,
                            'neckline': valley_between
                        }
                    )
        return None
    
    def detect_support_bounce(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta rebote en soporte"""
        if len(df) < 20:
            return None
            
        current_price = float(df['close'].iloc[-1])
        support = float(df['support'].iloc[-1])
        previous_low = float(df['low'].iloc[-2])
        current_low = float(df['low'].iloc[-1])
        
        # Verificar si tocó soporte y rebotó
        touch_support = current_low <= support * 1.005
        bounce = current_price > current_low * 1.002
        
        if touch_support and bounce:
            # Verificar volumen
            volume_increase = df['volume_ratio'].iloc[-1] > 1.2
            
            # Determinar stage
            if current_price < support * 1.01:
                stage = PatternStage.FORMING
                confidence = 55 if volume_increase else 45
            elif current_price > support * 1.02:
                stage = PatternStage.CONFIRMED
                confidence = 80 if volume_increase else 70
            else:
                stage = PatternStage.NEARLY_COMPLETE
                confidence = 65 if volume_increase else 55
            
            return Signal(
                id=f"{symbol}_{timeframe}_SUP_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=PatternType.SUPPORT_BOUNCE,
                stage=stage,
                confidence=confidence,
                entry_price=support * 1.005,
                stop_loss=support * 0.98,
                take_profit_1=support * 1.03,
                take_profit_2=support * 1.05,
                risk_reward_ratio=1.5,
                formation_start=datetime.now(),
                current_timestamp=datetime.now(),
                notes={
                    'support_level': support,
                    'bounce_strength': (current_price - current_low) / current_low * 100,
                    'volume_increase': volume_increase
                }
            )
        return None
    
    def detect_resistance_rejection(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta rechazo en resistencia"""
        if len(df) < 20:
            return None
            
        current_price = float(df['close'].iloc[-1])
        resistance = float(df['resistance'].iloc[-1])
        previous_high = float(df['high'].iloc[-2])
        current_high = float(df['high'].iloc[-1])
        
        # Verificar si tocó resistencia y fue rechazado
        touch_resistance = current_high >= resistance * 0.995
        rejection = current_price < current_high * 0.998
        
        if touch_resistance and rejection:
            volume_increase = df['volume_ratio'].iloc[-1] > 1.2
            
            if current_price > resistance * 0.99:
                stage = PatternStage.FORMING
                confidence = 55 if volume_increase else 45
            elif current_price < resistance * 0.98:
                stage = PatternStage.CONFIRMED
                confidence = 80 if volume_increase else 70
            else:
                stage = PatternStage.NEARLY_COMPLETE
                confidence = 65 if volume_increase else 55
            
            return Signal(
                id=f"{symbol}_{timeframe}_RES_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=PatternType.RESISTANCE_REJECT,
                stage=stage,
                confidence=confidence,
                entry_price=resistance * 0.995,
                stop_loss=resistance * 1.02,
                take_profit_1=resistance * 0.97,
                take_profit_2=resistance * 0.95,
                risk_reward_ratio=1.5,
                formation_start=datetime.now(),
                current_timestamp=datetime.now(),
                notes={
                    'resistance_level': resistance,
                    'rejection_strength': (current_high - current_price) / current_high * 100,
                    'volume_increase': volume_increase
                }
            )
        return None
    
    def detect_breakout(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta ruptura alcista"""
        if len(df) < 20:
            return None
            
        current_price = float(df['close'].iloc[-1])
        resistance = float(df['resistance'].iloc[-1])
        volume_ratio = float(df['volume_ratio'].iloc[-1])
        
        # Verificar ruptura con volumen
        breakout = current_price > resistance * 1.005
        volume_confirmation = volume_ratio > 1.5
        
        if breakout:
            if not volume_confirmation:
                stage = PatternStage.POTENTIAL
                confidence = 50
            elif current_price > resistance * 1.01:
                stage = PatternStage.CONFIRMED
                confidence = 85
            else:
                stage = PatternStage.FORMING
                confidence = 70
            
            return Signal(
                id=f"{symbol}_{timeframe}_BRK_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=PatternType.BREAKOUT,
                stage=stage,
                confidence=confidence,
                entry_price=resistance * 1.005,
                stop_loss=resistance * 0.98,
                take_profit_1=resistance * 1.03,
                take_profit_2=resistance * 1.05,
                risk_reward_ratio=2.0,
                formation_start=datetime.now(),
                current_timestamp=datetime.now(),
                notes={
                    'breakout_level': resistance,
                    'volume_ratio': volume_ratio,
                    'breakout_strength': (current_price - resistance) / resistance * 100
                }
            )
        return None
    
    def detect_breakdown(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta ruptura bajista"""
        if len(df) < 20:
            return None
            
        current_price = float(df['close'].iloc[-1])
        support = float(df['support'].iloc[-1])
        volume_ratio = float(df['volume_ratio'].iloc[-1])
        
        breakdown = current_price < support * 0.995
        volume_confirmation = volume_ratio > 1.5
        
        if breakdown:
            if not volume_confirmation:
                stage = PatternStage.POTENTIAL
                confidence = 50
            elif current_price < support * 0.99:
                stage = PatternStage.CONFIRMED
                confidence = 85
            else:
                stage = PatternStage.FORMING
                confidence = 70
            
            return Signal(
                id=f"{symbol}_{timeframe}_BRD_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=PatternType.BREAKDOWN,
                stage=stage,
                confidence=confidence,
                entry_price=support * 0.995,
                stop_loss=support * 1.02,
                take_profit_1=support * 0.97,
                take_profit_2=support * 0.95,
                risk_reward_ratio=2.0,
                formation_start=datetime.now(),
                current_timestamp=datetime.now(),
                notes={
                    'breakdown_level': support,
                    'volume_ratio': volume_ratio,
                    'breakdown_strength': (support - current_price) / support * 100
                }
            )
        return None
    
    def detect_hammer(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta patrón de vela martillo"""
        if len(df) < 3:
            return None
            
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        body = abs(last_candle['close'] - last_candle['open'])
        lower_shadow = last_candle['open'] - last_candle['low'] if last_candle['close'] > last_candle['open'] else last_candle['close'] - last_candle['low']
        upper_shadow = last_candle['high'] - last_candle['close'] if last_candle['close'] > last_candle['open'] else last_candle['high'] - last_candle['open']
        
        # Condiciones para martillo
        is_hammer = (
            lower_shadow > body * 2 and  # Sombra inferior al menos 2x el cuerpo
            upper_shadow < body * 0.5 and  # Sombra superior pequeña
            prev_candle['close'] < prev_candle['open']  # Tendencia bajista previa
        )
        
        if is_hammer:
            current_price = float(last_candle['close'])
            
            stage = PatternStage.FORMING
            confidence = 65 if df['rsi'].iloc[-1] < 40 else 55
            
            return Signal(
                id=f"{symbol}_{timeframe}_HAM_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=PatternType.HAMMER,
                stage=stage,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=last_candle['low'] * 0.99,
                take_profit_1=current_price * 1.02,
                take_profit_2=current_price * 1.04,
                risk_reward_ratio=1.5,
                formation_start=datetime.now(),
                current_timestamp=datetime.now(),
                notes={
                    'body_size': body,
                    'lower_shadow': lower_shadow,
                    'upper_shadow': upper_shadow
                }
            )
        return None
    
    def detect_engulfing(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta patrón envolvente"""
        if len(df) < 2:
            return None
            
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Envolvente alcista
        bull_engulfing = (
            previous['close'] < previous['open'] and  # Vela anterior bajista
            current['close'] > current['open'] and  # Vela actual alcista
            current['open'] < previous['close'] and  # Abre por debajo del cierre anterior
            current['close'] > previous['open']  # Cierra por encima de la apertura anterior
        )
        
        # Envolvente bajista
        bear_engulfing = (
            previous['close'] > previous['open'] and  # Vela anterior alcista
            current['close'] < current['open'] and  # Vela actual bajista
            current['open'] > previous['close'] and  # Abre por encima del cierre anterior
            current['close'] < previous['open']  # Cierra por debajo de la apertura anterior
        )
        
        if bull_engulfing or bear_engulfing:
            pattern = PatternType.ENGULFING_BULL if bull_engulfing else PatternType.ENGULFING_BEAR
            current_price = float(current['close'])
            
            confidence = 70 if df['volume_ratio'].iloc[-1] > 1.3 else 60
            
            if bull_engulfing:
                entry = current_price
                sl = min(current['low'], previous['low']) * 0.99
                tp1 = current_price * 1.02
                tp2 = current_price * 1.04
            else:
                entry = current_price
                sl = max(current['high'], previous['high']) * 1.01
                tp1 = current_price * 0.98
                tp2 = current_price * 0.96
            
            return Signal(
                id=f"{symbol}_{timeframe}_ENG_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=pattern,
                stage=PatternStage.FORMING,
                confidence=confidence,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                risk_reward_ratio=1.5,
                formation_start=datetime.now(),
                current_timestamp=datetime.now(),
                notes={
                    'engulfing_type': 'bullish' if bull_engulfing else 'bearish',
                    'volume_confirmation': df['volume_ratio'].iloc[-1] > 1.3
                }
            )
        return None
    
    def detect_triangle(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[Signal]:
        """Detecta patrones de triángulo"""
        if len(df) < 30:
            return None
            
        recent = df.tail(30)
        highs = recent['high'].values
        lows = recent['low'].values
        
        # Detectar convergencia de máximos y mínimos
        high_slope = np.polyfit(range(len(highs)), highs, 1)[0]
        low_slope = np.polyfit(range(len(lows)), lows, 1)[0]
        
        # Triángulo ascendente: resistencia plana, soporte ascendente
        if abs(high_slope) < 0.001 and low_slope > 0.001:
            pattern = PatternType.TRIANGLE_ASC
            breakout_level = highs[-1]
            
            return Signal(
                id=f"{symbol}_{timeframe}_TRI_ASC_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=pattern,
                stage=PatternStage.FORMING,
                confidence=65,
                entry_price=breakout_level * 1.005,
                stop_loss=lows[-1] * 0.99,
                take_profit_1=breakout_level * 1.03,
                take_profit_2=breakout_level * 1.05,
                risk_reward_ratio=2.0,
                formation_start=datetime.now() - timedelta(hours=30),
                current_timestamp=datetime.now(),
                notes={
                    'apex': breakout_level,
                    'pattern': 'ascending_triangle'
                }
            )
        
        # Triángulo descendente: soporte plano, resistencia descendente
        elif abs(low_slope) < 0.001 and high_slope < -0.001:
            pattern = PatternType.TRIANGLE_DESC
            breakdown_level = lows[-1]
            
            return Signal(
                id=f"{symbol}_{timeframe}_TRI_DESC_{datetime.now().timestamp()}",
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=pattern,
                stage=PatternStage.FORMING,
                confidence=65,
                entry_price=breakdown_level * 0.995,
                stop_loss=highs[-1] * 1.01,
                take_profit_1=breakdown_level * 0.97,
                take_profit_2=breakdown_level * 0.95,
                risk_reward_ratio=2.0,
                formation_start=datetime.now() - timedelta(hours=30),
                current_timestamp=datetime.now(),
                notes={
                    'apex': breakdown_level,
                    'pattern': 'descending_triangle'
                }
            )
        
        return None