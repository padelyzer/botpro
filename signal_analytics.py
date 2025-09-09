#!/usr/bin/env python3
"""
Sistema de Análisis BI para Confirmación de Señales
Analiza la calidad y viabilidad de señales usando múltiples indicadores
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from database import db
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SignalAnalysis:
    """Análisis completo de una señal"""
    signal_id: str
    quality_score: float  # 0-100
    confirmation_indicators: Dict[str, float]
    risk_assessment: Dict[str, float]
    market_conditions: Dict[str, any]
    historical_performance: Dict[str, float]
    recommendation: str  # STRONG_BUY, BUY, HOLD, AVOID
    reasoning: List[str]
    confidence_level: float
    execution_priority: int  # 1-5 (1 = highest)

class SignalAnalyzer:
    """Analizador BI de señales de trading"""
    
    def __init__(self):
        self.min_quality_score = 70  # Score mínimo para ejecutar
        self.confirmation_weights = {
            'trend_alignment': 0.25,
            'volume_confirmation': 0.20,
            'momentum_strength': 0.20,
            'support_resistance': 0.15,
            'market_structure': 0.10,
            'volatility_assessment': 0.10
        }
    
    def analyze_signal(self, signal: Dict) -> SignalAnalysis:
        """Análisis completo de una señal"""
        try:
            # Obtener datos históricos para análisis
            market_data = self._get_market_context(signal['symbol'])
            
            # Análisis de indicadores técnicos
            tech_analysis = self._technical_analysis(market_data, signal)
            
            # Análisis de riesgo
            risk_analysis = self._risk_assessment(signal, market_data)
            
            # Análisis de condiciones de mercado
            market_conditions = self._market_conditions_analysis(market_data)
            
            # Performance histórica del filósofo
            historical_perf = self._historical_performance(signal['philosopher'], signal['symbol'])
            
            # Calcular score de calidad
            quality_score = self._calculate_quality_score(
                tech_analysis, risk_analysis, market_conditions, historical_perf
            )
            
            # Generar recomendación
            recommendation = self._generate_recommendation(quality_score, signal)
            
            # Reasoning detallado
            reasoning = self._generate_reasoning(tech_analysis, risk_analysis, market_conditions)
            
            analysis = SignalAnalysis(
                signal_id=signal['id'],
                quality_score=quality_score,
                confirmation_indicators=tech_analysis,
                risk_assessment=risk_analysis,
                market_conditions=market_conditions,
                historical_performance=historical_perf,
                recommendation=recommendation,
                reasoning=reasoning,
                confidence_level=quality_score / 100.0,
                execution_priority=self._calculate_priority(quality_score, signal)
            )
            
            # Guardar análisis en base de datos
            self._save_analysis(analysis, signal)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing signal {signal.get('id', 'unknown')}: {e}")
            return None
    
    def _technical_analysis(self, data: pd.DataFrame, signal: Dict) -> Dict[str, float]:
        """Análisis técnico detallado"""
        if data.empty:
            return {}
        
        try:
            # Trend alignment
            trend_score = self._analyze_trend_alignment(data, signal['action'])
            
            # Volume confirmation
            volume_score = self._analyze_volume_confirmation(data)
            
            # Momentum strength
            momentum_score = self._analyze_momentum(data, signal['action'])
            
            # Support/Resistance levels
            sr_score = self._analyze_support_resistance(data, signal['entry_price'])
            
            # Market structure
            structure_score = self._analyze_market_structure(data)
            
            # Volatility assessment
            volatility_score = self._analyze_volatility(data)
            
            return {
                'trend_alignment': trend_score,
                'volume_confirmation': volume_score,
                'momentum_strength': momentum_score,
                'support_resistance': sr_score,
                'market_structure': structure_score,
                'volatility_assessment': volatility_score
            }
        except Exception as e:
            logger.error(f"Technical analysis error: {e}")
            return {}
    
    def _analyze_trend_alignment(self, data: pd.DataFrame, action: str) -> float:
        """Analiza alineación con tendencia"""
        try:
            # Validar que tenemos datos
            if data.empty or 'close' not in data.columns:
                return 50.0  # Neutral score if no data
            
            # EMAs múltiples para confirmar tendencia
            data['ema_9'] = data['close'].ewm(span=9).mean()
            data['ema_21'] = data['close'].ewm(span=21).mean()
            data['ema_50'] = data['close'].ewm(span=50).mean()
            
            current_price = data['close'].iloc[-1]
            ema_9 = data['ema_9'].iloc[-1]
            ema_21 = data['ema_21'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            
            # Evaluar alineación de EMAs
            if action == 'BUY':
                if ema_9 > ema_21 > ema_50 and current_price > ema_9:
                    return 95  # Tendencia fuerte alcista
                elif ema_9 > ema_21 and current_price > ema_21:
                    return 75  # Tendencia moderada alcista
                elif current_price > ema_50:
                    return 50  # Tendencia débil alcista
                else:
                    return 20  # Contra tendencia
            else:  # SELL
                if ema_9 < ema_21 < ema_50 and current_price < ema_9:
                    return 95  # Tendencia fuerte bajista
                elif ema_9 < ema_21 and current_price < ema_21:
                    return 75  # Tendencia moderada bajista
                elif current_price < ema_50:
                    return 50  # Tendencia débil bajista
                else:
                    return 20  # Contra tendencia
                    
        except Exception as e:
            logger.error(f"Trend analysis error: {e}")
            return 50  # Score neutro en caso de error
    
    def _analyze_volume_confirmation(self, data: pd.DataFrame) -> float:
        """Analiza confirmación por volumen"""
        try:
            # Volumen promedio de los últimos 20 períodos
            avg_volume = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > 2.0:
                return 95  # Volumen muy alto
            elif volume_ratio > 1.5:
                return 80  # Volumen alto
            elif volume_ratio > 1.0:
                return 60  # Volumen normal
            else:
                return 30  # Volumen bajo
                
        except Exception as e:
            logger.error(f"Volume analysis error: {e}")
            return 50
    
    def _analyze_momentum(self, data: pd.DataFrame, action: str) -> float:
        """Analiza fuerza del momentum"""
        try:
            # Validar que tenemos datos
            if data.empty or 'close' not in data.columns:
                return 50.0  # Neutral score if no data
            
            # RSI
            rsi = self._calculate_rsi(data['close'], 14)
            current_rsi = rsi.iloc[-1]
            
            # MACD
            macd_line, signal_line, _ = self._calculate_macd(data['close'])
            macd_current = macd_line.iloc[-1]
            signal_current = signal_line.iloc[-1]
            
            score = 0
            
            # Evaluar RSI
            if action == 'BUY':
                if 30 <= current_rsi <= 70:  # RSI en rango saludable
                    score += 40
                elif current_rsi < 30:  # Sobreventa
                    score += 60
                else:  # Sobrecompra
                    score += 10
                    
                # Evaluar MACD
                if macd_current > signal_current:
                    score += 40
                else:
                    score += 10
                    
            else:  # SELL
                if 30 <= current_rsi <= 70:
                    score += 40
                elif current_rsi > 70:  # Sobrecompra
                    score += 60
                else:  # Sobreventa
                    score += 10
                    
                if macd_current < signal_current:
                    score += 40
                else:
                    score += 10
            
            return min(score, 100)
            
        except Exception as e:
            logger.error(f"Momentum analysis error: {e}")
            return 50
    
    def _analyze_support_resistance(self, data: pd.DataFrame, entry_price: float) -> float:
        """Analiza proximidad a soportes/resistencias"""
        try:
            # Identificar niveles de soporte y resistencia
            highs = data['high'].tail(50)
            lows = data['low'].tail(50)
            
            # Niveles de resistencia (máximos locales)
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):
                    resistance_levels.append(highs.iloc[i])
            
            # Niveles de soporte (mínimos locales)
            support_levels = []
            for i in range(2, len(lows) - 2):
                if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):
                    support_levels.append(lows.iloc[i])
            
            # Evaluar proximidad
            min_distance_to_resistance = float('inf')
            min_distance_to_support = float('inf')
            
            for level in resistance_levels:
                distance = abs(entry_price - level) / entry_price
                min_distance_to_resistance = min(min_distance_to_resistance, distance)
            
            for level in support_levels:
                distance = abs(entry_price - level) / entry_price
                min_distance_to_support = min(min_distance_to_support, distance)
            
            # Score basado en distancia a niveles clave
            if min_distance_to_resistance < 0.01 or min_distance_to_support < 0.01:  # Muy cerca
                return 30  # Riesgo alto
            elif min_distance_to_resistance < 0.02 or min_distance_to_support < 0.02:  # Cerca
                return 50  # Riesgo moderado
            else:  # Lejos de niveles
                return 80  # Buena ubicación
                
        except Exception as e:
            logger.error(f"S/R analysis error: {e}")
            return 50
    
    def _analyze_market_structure(self, data: pd.DataFrame) -> float:
        """Analiza estructura del mercado"""
        try:
            # Analizar patrones de higher highs/lower lows
            highs = data['high'].tail(10)
            lows = data['low'].tail(10)
            
            # Contar higher highs y lower lows
            higher_highs = sum(1 for i in range(1, len(highs)) if highs.iloc[i] > highs.iloc[i-1])
            lower_lows = sum(1 for i in range(1, len(lows)) if lows.iloc[i] < lows.iloc[i-1])
            
            # Evaluar estructura
            if higher_highs >= 6:  # Estructura alcista fuerte
                return 85
            elif higher_highs >= 4:  # Estructura alcista moderada
                return 70
            elif lower_lows >= 6:  # Estructura bajista fuerte
                return 85
            elif lower_lows >= 4:  # Estructura bajista moderada
                return 70
            else:  # Estructura lateral
                return 50
                
        except Exception as e:
            logger.error(f"Market structure analysis error: {e}")
            return 50
    
    def _analyze_volatility(self, data: pd.DataFrame) -> float:
        """Analiza volatilidad del mercado"""
        try:
            # ATR (Average True Range)
            atr = self._calculate_atr(data, 14)
            current_atr = atr.iloc[-1]
            avg_atr = atr.tail(50).mean()
            
            volatility_ratio = current_atr / avg_atr
            
            if volatility_ratio < 0.8:  # Baja volatilidad
                return 90  # Ideal para swing trading
            elif volatility_ratio < 1.2:  # Volatilidad normal
                return 75
            elif volatility_ratio < 1.8:  # Alta volatilidad
                return 50
            else:  # Volatilidad extrema
                return 20
                
        except Exception as e:
            logger.error(f"Volatility analysis error: {e}")
            return 50
    
    def _risk_assessment(self, signal: Dict, data: pd.DataFrame) -> Dict[str, float]:
        """Evaluación de riesgo de la señal"""
        try:
            # Validar que tenemos datos
            if data.empty or 'close' not in data.columns:
                return {
                    'risk_reward_ratio': 1.5,
                    'drawdown_risk': 0.05,
                    'position_size_rec': 0.02
                }
            
            entry_price = signal['entry_price']
            stop_loss = signal.get('stop_loss', entry_price * 0.95)  # 5% default
            take_profit = signal.get('take_profit', entry_price * 1.10)  # 10% default
            
            # Risk-Reward ratio
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Drawdown potential
            current_price = data['close'].iloc[-1]
            price_distance = abs(current_price - entry_price) / current_price
            
            # Position sizing recommendation
            recommended_size = self._calculate_position_size(risk, entry_price)
            
            return {
                'risk_reward_ratio': rr_ratio,
                'price_distance': price_distance,
                'stop_distance_pct': (risk / entry_price) * 100,
                'recommended_position_size': recommended_size,
                'risk_score': min(rr_ratio * 20, 100)  # Score basado en R:R
            }
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            return {}
    
    def _market_conditions_analysis(self, data: pd.DataFrame) -> Dict[str, any]:
        """Análisis de condiciones generales del mercado"""
        try:
            # Validar que tenemos datos
            if data.empty or 'close' not in data.columns:
                return {
                    'market_trend': 'SIDEWAYS',
                    'trend_strength': 'NEUTRAL',
                    'volatility_level': 'MEDIUM',
                    'market_phase': 'NEUTRAL'
                }
            
            # Tendencia general
            sma_20 = data['close'].rolling(20).mean().iloc[-1]
            sma_50 = data['close'].rolling(50).mean().iloc[-1]
            current_price = data['close'].iloc[-1]
            
            if current_price > sma_20 > sma_50:
                market_trend = "UPTREND"
                trend_strength = "STRONG"
            elif current_price > sma_50:
                market_trend = "UPTREND"
                trend_strength = "WEAK"
            elif current_price < sma_20 < sma_50:
                market_trend = "DOWNTREND"
                trend_strength = "STRONG"
            elif current_price < sma_50:
                market_trend = "DOWNTREND"
                trend_strength = "WEAK"
            else:
                market_trend = "SIDEWAYS"
                trend_strength = "NEUTRAL"
            
            # Volatilidad del mercado
            volatility = data['close'].pct_change().std() * 100
            
            return {
                'market_trend': market_trend,
                'trend_strength': trend_strength,
                'volatility_level': volatility,
                'market_phase': self._determine_market_phase(data)
            }
        except Exception as e:
            logger.error(f"Market conditions analysis error: {e}")
            return {}
    
    def _historical_performance(self, philosopher: str, symbol: str) -> Dict[str, float]:
        """Análisis de performance histórica del filósofo"""
        try:
            # Obtener señales históricas del filósofo para este símbolo
            historical_signals = db.get_philosopher_performance(philosopher, symbol, days=30)
            
            if not historical_signals:
                return {'win_rate': 50.0, 'avg_return': 0.0, 'signal_count': 0}
            
            total_signals = len(historical_signals)
            profitable_signals = sum(1 for s in historical_signals if s.get('profit', 0) > 0)
            win_rate = (profitable_signals / total_signals) * 100
            
            avg_return = np.mean([s.get('profit', 0) for s in historical_signals])
            
            return {
                'win_rate': win_rate,
                'avg_return': avg_return,
                'signal_count': total_signals,
                'reliability_score': min(win_rate, 100)
            }
        except Exception as e:
            logger.error(f"Historical performance analysis error: {e}")
            return {'win_rate': 50.0, 'avg_return': 0.0, 'signal_count': 0}
    
    def _calculate_quality_score(self, tech_analysis: Dict, risk_analysis: Dict, 
                                market_conditions: Dict, historical_perf: Dict) -> float:
        """Calcula el score de calidad general"""
        try:
            score = 0
            
            # Peso de análisis técnico (50%)
            if tech_analysis:
                tech_score = sum(
                    tech_analysis.get(indicator, 50) * weight 
                    for indicator, weight in self.confirmation_weights.items()
                )
                score += tech_score * 0.5
            
            # Peso de análisis de riesgo (20%)
            if risk_analysis:
                risk_score = risk_analysis.get('risk_score', 50)
                score += risk_score * 0.2
            
            # Peso de condiciones de mercado (15%)
            market_score = 75 if market_conditions.get('trend_strength') == 'STRONG' else 50
            score += market_score * 0.15
            
            # Peso de performance histórica (15%)
            if historical_perf:
                perf_score = historical_perf.get('reliability_score', 50)
                score += perf_score * 0.15
            
            return min(max(score, 0), 100)
        except Exception as e:
            logger.error(f"Quality score calculation error: {e}")
            return 50
    
    def _generate_recommendation(self, quality_score: float, signal: Dict) -> str:
        """Genera recomendación basada en el score"""
        if quality_score >= 85:
            return "STRONG_BUY" if signal['action'] == 'BUY' else "STRONG_SELL"
        elif quality_score >= 70:
            return signal['action']  # BUY o SELL
        elif quality_score >= 50:
            return "HOLD"
        else:
            return "AVOID"
    
    def _generate_reasoning(self, tech_analysis: Dict, risk_analysis: Dict, 
                          market_conditions: Dict) -> List[str]:
        """Genera reasoning detallado"""
        reasoning = []
        
        # Análisis técnico
        if tech_analysis.get('trend_alignment', 0) > 75:
            reasoning.append("✅ Fuerte alineación con tendencia dominante")
        elif tech_analysis.get('trend_alignment', 0) < 40:
            reasoning.append("⚠️ Señal contra tendencia - mayor riesgo")
        
        if tech_analysis.get('volume_confirmation', 0) > 80:
            reasoning.append("✅ Confirmación fuerte de volumen")
        elif tech_analysis.get('volume_confirmation', 0) < 40:
            reasoning.append("⚠️ Volumen débil - confirmación limitada")
        
        # Risk-Reward
        rr_ratio = risk_analysis.get('risk_reward_ratio', 0)
        if rr_ratio >= 2.0:
            reasoning.append(f"✅ Excelente ratio R:R de {rr_ratio:.1f}")
        elif rr_ratio < 1.5:
            reasoning.append(f"⚠️ Ratio R:R bajo: {rr_ratio:.1f}")
        
        # Condiciones de mercado
        if market_conditions.get('trend_strength') == 'STRONG':
            reasoning.append("✅ Condiciones de mercado favorables")
        
        return reasoning
    
    def _calculate_priority(self, quality_score: float, signal: Dict) -> int:
        """Calcula prioridad de ejecución (1=máxima, 5=mínima)"""
        if quality_score >= 85:
            return 1  # Máxima prioridad
        elif quality_score >= 75:
            return 2  # Alta prioridad
        elif quality_score >= 65:
            return 3  # Prioridad media
        elif quality_score >= 55:
            return 4  # Baja prioridad
        else:
            return 5  # Mínima prioridad
    
    def _save_analysis(self, analysis: SignalAnalysis, signal: Dict):
        """Guarda el análisis en base de datos"""
        try:
            analysis_data = {
                'signal_id': analysis.signal_id,
                'quality_score': analysis.quality_score,
                'confirmation_indicators': json.dumps(analysis.confirmation_indicators),
                'risk_assessment': json.dumps(analysis.risk_assessment),
                'market_conditions': json.dumps(analysis.market_conditions),
                'historical_performance': json.dumps(analysis.historical_performance),
                'recommendation': analysis.recommendation,
                'reasoning': json.dumps(analysis.reasoning),
                'confidence_level': analysis.confidence_level,
                'execution_priority': analysis.execution_priority,
                'analyzed_at': datetime.now().isoformat()
            }
            
            # Guardar en tabla de análisis
            db.save_signal_analysis(analysis_data)
            logger.info(f"Analysis saved for signal {analysis.signal_id} - Score: {analysis.quality_score:.1f}")
            
        except Exception as e:
            logger.error(f"Error saving analysis: {e}")
    
    # Utility methods
    def _get_market_context(self, symbol: str) -> pd.DataFrame:
        """Obtiene datos de mercado para análisis"""
        try:
            from binance_integration import BinanceConnector
            connector = BinanceConnector()
            df = connector.get_historical_data(symbol, '4h', limit=100)
            return df
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return pd.DataFrame()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series, fast=12, slow=26, signal=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def _calculate_position_size(self, risk_amount: float, entry_price: float) -> float:
        """Calcula tamaño de posición recomendado"""
        # 1% del capital en riesgo
        account_balance = 10000  # Esto debería venir de la configuración del usuario
        risk_per_trade = account_balance * 0.01
        return risk_per_trade / risk_amount
    
    def _determine_market_phase(self, data: pd.DataFrame) -> str:
        """Determina la fase del mercado"""
        volatility = data['close'].pct_change().rolling(20).std()
        current_vol = volatility.iloc[-1]
        avg_vol = volatility.mean()
        
        if current_vol > avg_vol * 1.5:
            return "HIGH_VOLATILITY"
        elif current_vol < avg_vol * 0.7:
            return "LOW_VOLATILITY"
        else:
            return "NORMAL_VOLATILITY"

# Instancia global del analizador
signal_analyzer = SignalAnalyzer()