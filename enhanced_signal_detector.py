#!/usr/bin/env python3
"""
ENHANCED SIGNAL DETECTOR - BotphIA
Detector mejorado con apalancamiento recomendado y R:R dinámico basado en ATR
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import ta

from multi_timeframe_signal_detector import (
    Signal, PatternType, PatternStage,
    PatternDetector
)
from trading_config import RSI_CONFIG, get_rsi_levels, is_rsi_overbought, is_rsi_oversold

@dataclass
class EnhancedSignal(Signal):
    """Señal mejorada con métricas adicionales"""
    recommended_leverage: int = 1
    atr_value: float = 0.0
    volatility_percentile: float = 0.0
    dynamic_rr_ratio: float = 2.0
    position_size_percent: float = 1.0
    max_loss_percent: float = 2.0
    market_conditions: Dict = field(default_factory=dict)

class EnhancedPatternDetector(PatternDetector):
    """Detector de patrones mejorado con métricas avanzadas"""
    
    def calculate_atr_metrics(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """Calcula métricas basadas en ATR"""
        
        # Calcular ATR
        atr = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=period
        ).average_true_range()
        
        current_atr = atr.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # ATR como porcentaje del precio
        atr_percentage = (current_atr / current_price) * 100
        
        # Percentil de volatilidad (comparado con últimas 100 velas)
        atr_series = atr.iloc[-100:] if len(atr) >= 100 else atr
        volatility_percentile = (atr_series < current_atr).sum() / len(atr_series) * 100
        
        # Calcular volatilidad histórica
        returns = df['close'].pct_change().dropna()
        historical_volatility = returns.std() * np.sqrt(252) * 100  # Anualizada
        
        return {
            'atr': current_atr,
            'atr_percentage': atr_percentage,
            'volatility_percentile': volatility_percentile,
            'historical_volatility': historical_volatility
        }
    
    def calculate_dynamic_rr(self, atr_percentage: float, volatility_percentile: float, 
                           pattern_type: PatternType, timeframe: str) -> float:
        """
        Calcula R:R dinámico basado en ATR y condiciones del mercado
        
        Lógica:
        - Mayor volatilidad = Mayor R:R objetivo (más potencial de movimiento)
        - Menor volatilidad = R:R más conservador
        - Ajustado por timeframe (más largo = mayor R:R)
        """
        
        # R:R base según volatilidad
        if atr_percentage > 5:  # Alta volatilidad
            base_rr = 2.5
        elif atr_percentage > 3:  # Volatilidad media-alta
            base_rr = 2.3
        elif atr_percentage > 2:  # Volatilidad media
            base_rr = 2.1
        elif atr_percentage > 1:  # Volatilidad media-baja
            base_rr = 2.0
        else:  # Baja volatilidad
            base_rr = 1.8
        
        # Ajuste por percentil de volatilidad
        if volatility_percentile > 80:  # Volatilidad inusualmente alta
            base_rr += 0.3
        elif volatility_percentile > 60:
            base_rr += 0.1
        elif volatility_percentile < 20:  # Volatilidad inusualmente baja
            base_rr -= 0.2
        
        # Ajuste por timeframe
        timeframe_multipliers = {
            '5m': 0.9,    # Scalping - R:R más conservador
            '15m': 0.95,
            '1h': 1.0,    # Base
            '4h': 1.1     # Swing - R:R más ambicioso
        }
        
        multiplier = timeframe_multipliers.get(timeframe, 1.0)
        final_rr = base_rr * multiplier
        
        # Ajuste por tipo de patrón (algunos patrones son más confiables)
        reliable_patterns = [
            PatternType.DOUBLE_BOTTOM,
            PatternType.DOUBLE_TOP,
            PatternType.HEAD_SHOULDERS
        ]
        
        if pattern_type in reliable_patterns:
            final_rr += 0.1
        
        # Limitar entre 1.5 y 3.5
        return round(max(1.5, min(3.5, final_rr)), 1)
    
    def calculate_recommended_leverage(self, atr_percentage: float, confidence: float,
                                      volatility_percentile: float, timeframe: str) -> int:
        """
        Calcula apalancamiento recomendado basado en:
        - Volatilidad (ATR)
        - Confianza de la señal
        - Timeframe
        
        Principio: Mayor volatilidad = Menor apalancamiento
        """
        
        # Apalancamiento base según volatilidad
        if atr_percentage > 5:  # Muy volátil (>5% ATR)
            base_leverage = 2
        elif atr_percentage > 3:  # Alta volatilidad (3-5% ATR)
            base_leverage = 3
        elif atr_percentage > 2:  # Volatilidad media (2-3% ATR)
            base_leverage = 5
        elif atr_percentage > 1:  # Volatilidad baja (1-2% ATR)
            base_leverage = 8
        else:  # Muy baja volatilidad (<1% ATR)
            base_leverage = 10
        
        # Ajuste por confianza de la señal
        if confidence >= 80:
            leverage_multiplier = 1.2
        elif confidence >= 70:
            leverage_multiplier = 1.0
        elif confidence >= 60:
            leverage_multiplier = 0.8
        else:
            leverage_multiplier = 0.6
        
        # Ajuste por timeframe (menor timeframe = menor apalancamiento)
        timeframe_limits = {
            '5m': 0.6,   # Máximo 60% del calculado
            '15m': 0.8,  # Máximo 80% del calculado
            '1h': 1.0,   # 100% del calculado
            '4h': 1.2    # Hasta 120% del calculado
        }
        
        timeframe_mult = timeframe_limits.get(timeframe, 1.0)
        
        # Calcular apalancamiento final
        final_leverage = base_leverage * leverage_multiplier * timeframe_mult
        
        # Si la volatilidad está en percentil extremo, ajustar
        if volatility_percentile > 90:  # Volatilidad extremadamente alta
            final_leverage *= 0.5
        elif volatility_percentile < 10:  # Volatilidad extremadamente baja
            final_leverage *= 1.3
        
        # Redondear y limitar
        final_leverage = int(round(final_leverage))
        
        # Límites máximos por timeframe
        max_leverage_by_tf = {
            '5m': 5,
            '15m': 8,
            '1h': 10,
            '4h': 15
        }
        
        max_allowed = max_leverage_by_tf.get(timeframe, 10)
        
        return max(1, min(final_leverage, max_allowed))
    
    def calculate_position_size(self, leverage: int, volatility: float, 
                              account_risk_percent: float = 2.0) -> float:
        """
        Calcula el tamaño de posición recomendado
        
        Kelly Criterion simplificado para crypto
        """
        
        # Factor de Kelly conservador
        kelly_fraction = 0.25  # Usar solo 25% del Kelly completo
        
        # Ajustar por volatilidad
        if volatility > 100:  # Volatilidad anual > 100%
            size_multiplier = 0.5
        elif volatility > 75:
            size_multiplier = 0.7
        elif volatility > 50:
            size_multiplier = 0.9
        else:
            size_multiplier = 1.0
        
        # Posición base (% del capital)
        base_position = account_risk_percent / leverage
        
        # Aplicar Kelly y multiplicadores
        final_position = base_position * kelly_fraction * size_multiplier
        
        return round(final_position, 2)
    
    def enhance_signal(self, signal: Signal, df: pd.DataFrame, 
                      symbol: str, timeframe: str) -> EnhancedSignal:
        """Mejora una señal con métricas adicionales"""
        
        # Calcular métricas ATR
        atr_metrics = self.calculate_atr_metrics(df)
        
        # Calcular R:R dinámico
        dynamic_rr = self.calculate_dynamic_rr(
            atr_metrics['atr_percentage'],
            atr_metrics['volatility_percentile'],
            signal.pattern_type,
            timeframe
        )
        
        # Calcular apalancamiento recomendado
        recommended_leverage = self.calculate_recommended_leverage(
            atr_metrics['atr_percentage'],
            signal.confidence,
            atr_metrics['volatility_percentile'],
            timeframe
        )
        
        # Calcular tamaño de posición
        position_size = self.calculate_position_size(
            recommended_leverage,
            atr_metrics['historical_volatility']
        )
        
        # Recalcular take profits con R:R dinámico
        entry = signal.entry_price
        stop_loss = signal.stop_loss
        risk = abs(entry - stop_loss)
        
        if signal.pattern_type in [PatternType.DOUBLE_BOTTOM, PatternType.SUPPORT_BOUNCE, 
                                  PatternType.BREAKOUT, PatternType.HAMMER]:
            # Señal alcista
            take_profit_1 = entry + (risk * dynamic_rr)
            take_profit_2 = entry + (risk * dynamic_rr * 1.5)
        else:
            # Señal bajista
            take_profit_1 = entry - (risk * dynamic_rr)
            take_profit_2 = entry - (risk * dynamic_rr * 1.5)
        
        # Crear señal mejorada
        enhanced = EnhancedSignal(
            id=signal.id,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            pattern_type=signal.pattern_type,
            stage=signal.stage,
            confidence=signal.confidence,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            risk_reward_ratio=dynamic_rr,
            formation_start=signal.formation_start,
            current_timestamp=signal.current_timestamp,
            notes=signal.notes,
            # Nuevos campos
            recommended_leverage=recommended_leverage,
            atr_value=atr_metrics['atr'],
            volatility_percentile=atr_metrics['volatility_percentile'],
            dynamic_rr_ratio=dynamic_rr,
            position_size_percent=position_size,
            max_loss_percent=2.0,
            market_conditions={
                'atr_percentage': atr_metrics['atr_percentage'],
                'historical_volatility': atr_metrics['historical_volatility'],
                'timeframe': timeframe
            }
        )
        
        return enhanced
    
    def detect_and_enhance_patterns(self, df: pd.DataFrame, symbol: str, 
                                   timeframe: str) -> List[EnhancedSignal]:
        """Detecta patrones y los mejora con métricas adicionales"""
        
        # Detectar patrones base
        base_signals = self.detect_all_patterns(df, symbol, timeframe)
        
        # Mejorar cada señal
        enhanced_signals = []
        for signal in base_signals:
            try:
                enhanced = self.enhance_signal(signal, df, symbol, timeframe)
                enhanced_signals.append(enhanced)
            except Exception as e:
                print(f"Error mejorando señal: {e}")
                continue
        
        return enhanced_signals