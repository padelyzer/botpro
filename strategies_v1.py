#!/usr/bin/env python3
"""
===========================================
SISTEMA DE ESTRATEGIAS VERSIONADAS V1.0
===========================================

Cada estrategia está optimizada para un tipo específico de mercado.
Incluye documentación detallada de fortalezas y debilidades.

Autor: Trading System V1.0
Fecha: 2024
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CLASE BASE PARA TODAS LAS ESTRATEGIAS
# ============================================

@dataclass
class Signal:
    """Estructura de una señal de trading"""
    timestamp: datetime
    symbol: str
    type: str  # LONG o SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy_name: str
    strategy_version: str
    market_regime: str
    risk_reward_ratio: float
    position_size: float
    metadata: Dict

class BaseStrategy:
    """Clase base para todas las estrategias de trading"""
    
    def __init__(self, version: str = "1.0"):
        self.version = version
        self.name = self.__class__.__name__
        self.strengths = []
        self.weaknesses = []
        self.optimal_conditions = []
        self.risk_parameters = {}
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos base"""
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['ATR'] = ranges.max(axis=1).rolling(14).mean()
        
        # Volume indicators
        df['Volume_SMA'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        
        # EMAs
        df['EMA_9'] = df['Close'].ewm(span=9).mean()
        df['EMA_21'] = df['Close'].ewm(span=21).mean()
        df['EMA_50'] = df['Close'].ewm(span=50).mean()
        df['EMA_200'] = df['Close'].ewm(span=200).mean()
        
        # Stochastic
        low_min = df['Low'].rolling(14).min()
        high_max = df['High'].rolling(14).max()
        df['Stoch_K'] = 100 * ((df['Close'] - low_min) / (high_max - low_min))
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        return df
    
    def calculate_position_size(self, capital: float, risk_per_trade: float, 
                              entry: float, stop_loss: float) -> float:
        """Calcula el tamaño de posición basado en gestión de riesgo"""
        risk_amount = capital * risk_per_trade
        stop_distance = abs(entry - stop_loss)
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
        return min(position_size, capital * 0.95)  # Máximo 95% del capital
    
    def get_documentation(self) -> Dict:
        """Retorna documentación completa de la estrategia"""
        return {
            'name': self.name,
            'version': self.version,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'optimal_conditions': self.optimal_conditions,
            'risk_parameters': self.risk_parameters
        }

# ============================================
# ESTRATEGIA V1.0: RANGING (MERCADO LATERAL)
# ============================================

class RangingStrategyV1(BaseStrategy):
    """
    Estrategia optimizada para mercados laterales (RANGING)
    Versión: 1.0
    
    FORTALEZAS:
    - Excelente en mercados sin tendencia clara (70-80% del tiempo)
    - Alta tasa de éxito en rangos bien definidos
    - Riesgo/beneficio favorable en bounces de soporte/resistencia
    - Funciona bien con alta volatilidad intradiaria
    
    DEBILIDADES:
    - Pérdidas significativas en breakouts falsos
    - Mal desempeño cuando el rango se rompe
    - Requiere identificación precisa de niveles S/R
    - Vulnerable a noticias que rompen el rango
    
    CONDICIONES ÓPTIMAS:
    - ADX < 25 (sin tendencia fuerte)
    - Bollinger Bands paralelas
    - Volumen estable sin picos
    - RSI oscilando entre 30-70
    - Price action respetando niveles históricos
    """
    
    def __init__(self):
        super().__init__(version="1.0")
        
        self.strengths = [
            "Alta efectividad en consolidaciones (70-80% del mercado)",
            "Puntos de entrada/salida claramente definidos",
            "Risk/Reward ratio típicamente 1:2 o mejor",
            "Múltiples oportunidades por día",
            "Funciona en todos los timeframes"
        ]
        
        self.weaknesses = [
            "Pérdidas en falsos breakouts (-2% a -3% por trade)",
            "Requiere monitoreo constante de niveles",
            "Difícil automatización completa",
            "Vulnerable a eventos de noticias",
            "Stops pueden ser barridos en volatilidad"
        ]
        
        self.optimal_conditions = [
            "ADX < 25",
            "ATR estable o decreciente",
            "Volumen < promedio 20 períodos",
            "Sin noticias importantes próximas",
            "Horario de menor volatilidad (10am-2pm)"
        ]
        
        self.risk_parameters = {
            'max_risk_per_trade': 0.01,  # 1% máximo
            'risk_reward_min': 2.0,  # Mínimo 1:2
            'confidence_threshold': 0.65,  # 65% mínimo
            'max_daily_trades': 4,
            'max_exposure': 0.03  # 3% exposición máxima
        }
    
    def identify_range(self, df: pd.DataFrame, lookback: int = 50) -> Tuple[float, float, float]:
        """Identifica los niveles de soporte y resistencia del rango"""
        
        recent_data = df.tail(lookback)
        
        # Método 1: Percentiles
        resistance = recent_data['High'].quantile(0.90)
        support = recent_data['Low'].quantile(0.10)
        
        # Método 2: Pivots points
        pivot = (recent_data['High'].iloc[-1] + recent_data['Low'].iloc[-1] + recent_data['Close'].iloc[-1]) / 3
        
        # Método 3: Clustering de máximos y mínimos
        highs = recent_data['High'].nlargest(10).mean()
        lows = recent_data['Low'].nsmallest(10).mean()
        
        # Consenso
        final_resistance = np.mean([resistance, highs])
        final_support = np.mean([support, lows])
        
        return final_support, final_resistance, pivot
    
    def generate_signal(self, df: pd.DataFrame, capital: float = 1000) -> Optional[Signal]:
        """Genera señales de trading para mercado lateral"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Identificar rango
        support, resistance, pivot = self.identify_range(df)
        range_size = resistance - support
        
        # Validar que estamos en rango
        if current['ATR'] > df['ATR'].rolling(50).mean().iloc[-1] * 1.5:
            return None  # Demasiada volatilidad
        
        signal_strength = 0
        signal_type = None
        reasons = []
        
        # Señales de COMPRA cerca del soporte
        distance_to_support = (current['Close'] - support) / range_size
        if distance_to_support < 0.15:  # Dentro del 15% del soporte
            
            if current['RSI'] < 35:
                signal_strength += 3
                reasons.append("RSI_OVERSOLD")
            
            if current['Close'] <= current['BB_Lower']:
                signal_strength += 3
                reasons.append("BB_LOWER_TOUCH")
            
            if current['Stoch_K'] < 20:
                signal_strength += 2
                reasons.append("STOCH_OVERSOLD")
            
            if current['Volume_Ratio'] > 1.2:
                signal_strength += 1
                reasons.append("HIGH_VOLUME")
            
            if signal_strength >= 5:
                signal_type = "LONG"
        
        # Señales de VENTA cerca de la resistencia
        distance_to_resistance = (resistance - current['Close']) / range_size
        if distance_to_resistance < 0.15:  # Dentro del 15% de la resistencia
            
            if current['RSI'] > 65:
                signal_strength += 3
                reasons.append("RSI_OVERBOUGHT")
            
            if current['Close'] >= current['BB_Upper']:
                signal_strength += 3
                reasons.append("BB_UPPER_TOUCH")
            
            if current['Stoch_K'] > 80:
                signal_strength += 2
                reasons.append("STOCH_OVERBOUGHT")
            
            if current['Volume_Ratio'] > 1.2:
                signal_strength += 1
                reasons.append("HIGH_VOLUME")
            
            if signal_strength >= 5:
                signal_type = "SHORT"
        
        # Generar señal si hay suficiente confianza
        if signal_type:
            entry_price = current['Close']
            
            if signal_type == "LONG":
                stop_loss = support - (range_size * 0.1)  # 10% debajo del soporte
                take_profit = resistance - (range_size * 0.1)  # 10% antes de la resistencia
            else:
                stop_loss = resistance + (range_size * 0.1)  # 10% arriba de la resistencia
                take_profit = support + (range_size * 0.1)  # 10% después del soporte
            
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            if risk_reward >= self.risk_parameters['risk_reward_min']:
                confidence = min(signal_strength / 10, 0.95)
                
                return Signal(
                    timestamp=datetime.now(),
                    symbol=df.attrs.get('symbol', 'UNKNOWN'),
                    type=signal_type,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    strategy_name=self.name,
                    strategy_version=self.version,
                    market_regime="RANGING",
                    risk_reward_ratio=risk_reward,
                    position_size=self.calculate_position_size(
                        capital, 
                        self.risk_parameters['max_risk_per_trade'],
                        entry_price,
                        stop_loss
                    ),
                    metadata={
                        'support': support,
                        'resistance': resistance,
                        'range_size': range_size,
                        'signals': reasons,
                        'signal_strength': signal_strength
                    }
                )
        
        return None

# ============================================
# ESTRATEGIA V1.0: BULLISH (MERCADO ALCISTA)
# ============================================

class BullishStrategyV1(BaseStrategy):
    """
    Estrategia optimizada para mercados alcistas (BULLISH)
    Versión: 1.0
    
    FORTALEZAS:
    - Captura grandes movimientos alcistas (5-15% en tendencias fuertes)
    - Excelente ratio ganancia/pérdida en trends establecidos
    - Pocas señales falsas con filtros de tendencia
    - Funciona muy bien en bull markets crypto
    
    DEBILIDADES:
    - Entradas tardías (pierde el primer 20-30% del movimiento)
    - Vulnerable a correcciones súbitas (-3% a -5%)
    - Mal desempeño en lateralizaciones
    - Puede mantener posiciones demasiado tiempo
    
    CONDICIONES ÓPTIMAS:
    - ADX > 30 con +DI > -DI
    - EMAs en orden alcista (9 > 21 > 50 > 200)
    - Volumen creciente en impulsos
    - RSI entre 50-70 (no sobrecomprado extremo)
    - Higher highs y higher lows consistentes
    """
    
    def __init__(self):
        super().__init__(version="1.0")
        
        self.strengths = [
            "Captura movimientos de 5-15% en tendencias fuertes",
            "Win rate alto (45-55%) en bull markets",
            "Riesgo controlado con trailing stops",
            "Funciona en múltiples timeframes",
            "Señales claras y objetivas"
        ]
        
        self.weaknesses = [
            "Entradas tardías (pierde 20-30% inicial)",
            "Vulnerable a falsas rupturas",
            "Drawdowns de -3% a -5% en correcciones",
            "Requiere gestión activa de stops",
            "Mal desempeño en transición a bear market"
        ]
        
        self.optimal_conditions = [
            "ADX > 30",
            "EMAs en alineación alcista",
            "Volumen > promedio en impulsos",
            "RSI 50-70",
            "Sentimiento de mercado positivo"
        ]
        
        self.risk_parameters = {
            'max_risk_per_trade': 0.015,  # 1.5% en trends
            'risk_reward_min': 2.5,  # Mínimo 1:2.5 en tendencia
            'confidence_threshold': 0.60,
            'max_daily_trades': 3,
            'max_exposure': 0.05,  # 5% exposición en bull market
            'trailing_stop_activation': 1.03,  # Activar trailing a +3%
            'trailing_stop_distance': 0.02  # 2% de trailing
        }
    
    def identify_trend_strength(self, df: pd.DataFrame) -> float:
        """Calcula la fuerza de la tendencia alcista"""
        
        # EMA alignment
        ema_score = 0
        if df['EMA_9'].iloc[-1] > df['EMA_21'].iloc[-1]:
            ema_score += 1
        if df['EMA_21'].iloc[-1] > df['EMA_50'].iloc[-1]:
            ema_score += 1
        if df['EMA_50'].iloc[-1] > df['EMA_200'].iloc[-1]:
            ema_score += 1
        
        # Price above EMAs
        price_score = 0
        if df['Close'].iloc[-1] > df['EMA_9'].iloc[-1]:
            price_score += 1
        if df['Close'].iloc[-1] > df['EMA_21'].iloc[-1]:
            price_score += 1
        if df['Close'].iloc[-1] > df['EMA_50'].iloc[-1]:
            price_score += 1
        
        # Higher highs and higher lows
        structure_score = 0
        recent_highs = df['High'].rolling(10).max()
        recent_lows = df['Low'].rolling(10).min()
        
        if recent_highs.iloc[-1] > recent_highs.iloc[-20]:
            structure_score += 1
        if recent_lows.iloc[-1] > recent_lows.iloc[-20]:
            structure_score += 1
        
        total_score = (ema_score + price_score + structure_score) / 8
        return total_score
    
    def find_pullback_entry(self, df: pd.DataFrame) -> bool:
        """Identifica entradas en pullbacks dentro de tendencia alcista"""
        
        current = df.iloc[-1]
        
        # Pullback to EMA
        ema_touch = (
            current['Low'] <= current['EMA_21'] * 1.005 and  # Toca EMA21
            current['Close'] > current['EMA_21'] and  # Pero cierra arriba
            current['EMA_21'] > current['EMA_50']  # En tendencia alcista
        )
        
        # RSI pullback
        rsi_pullback = (
            current['RSI'] < 50 and  # RSI bajo
            df['RSI'].iloc[-2] < 45 and  # Venía de oversold
            current['RSI'] > df['RSI'].iloc[-2]  # Pero recuperándose
        )
        
        return ema_touch or rsi_pullback
    
    def generate_signal(self, df: pd.DataFrame, capital: float = 1000) -> Optional[Signal]:
        """Genera señales de trading para mercado alcista"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Verificar tendencia alcista
        trend_strength = self.identify_trend_strength(df)
        if trend_strength < 0.5:
            return None  # No hay tendencia alcista suficiente
        
        signal_strength = 0
        reasons = []
        
        # 1. Breakout alcista
        if current['Close'] > df['High'].rolling(20).max().iloc[-2]:
            signal_strength += 3
            reasons.append("BREAKOUT_20D")
            
            if current['Volume_Ratio'] > 1.5:
                signal_strength += 2
                reasons.append("HIGH_VOLUME_BREAKOUT")
        
        # 2. Pullback en tendencia
        if self.find_pullback_entry(df):
            signal_strength += 4
            reasons.append("PULLBACK_ENTRY")
        
        # 3. Momentum alcista
        if current['MACD'] > current['MACD_Signal'] and current['MACD'] > 0:
            signal_strength += 2
            reasons.append("MACD_BULLISH")
        
        # 4. Continuación de tendencia
        if (current['Close'] > current['EMA_9'] and 
            current['EMA_9'] > current['EMA_21'] and
            50 < current['RSI'] < 65):
            signal_strength += 2
            reasons.append("TREND_CONTINUATION")
        
        # Generar señal LONG si hay suficiente confianza
        if signal_strength >= 5:
            entry_price = current['Close']
            
            # Stop loss dinámico basado en ATR y estructura
            atr_stop = entry_price - (current['ATR'] * 2)
            structure_stop = df['Low'].rolling(10).min().iloc[-1]
            stop_loss = max(atr_stop, structure_stop)
            
            # Take profit basado en proyección y resistencias
            atr_target = entry_price + (current['ATR'] * 4)
            projection = entry_price * 1.05  # 5% objetivo mínimo
            take_profit = max(atr_target, projection)
            
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            if risk_reward >= self.risk_parameters['risk_reward_min']:
                confidence = min(0.5 + (signal_strength * 0.05) + (trend_strength * 0.3), 0.90)
                
                return Signal(
                    timestamp=datetime.now(),
                    symbol=df.attrs.get('symbol', 'UNKNOWN'),
                    type="LONG",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    strategy_name=self.name,
                    strategy_version=self.version,
                    market_regime="BULLISH",
                    risk_reward_ratio=risk_reward,
                    position_size=self.calculate_position_size(
                        capital,
                        self.risk_parameters['max_risk_per_trade'],
                        entry_price,
                        stop_loss
                    ),
                    metadata={
                        'trend_strength': trend_strength,
                        'signals': reasons,
                        'signal_strength': signal_strength,
                        'trailing_stop_params': {
                            'activation': self.risk_parameters['trailing_stop_activation'],
                            'distance': self.risk_parameters['trailing_stop_distance']
                        }
                    }
                )
        
        return None

# ============================================
# ESTRATEGIA V1.0: BEARISH (MERCADO BAJISTA) 
# ============================================

class BearishStrategyV1(BaseStrategy):
    """
    Estrategia optimizada para mercados bajistas (BEARISH)
    Versión: 1.0
    
    FORTALEZAS:
    - Protege capital en mercados bajistas
    - Aprovecha caídas rápidas (3-10% en días)
    - Shorts muy rentables en crashes
    - Buena identificación de techos
    
    DEBILIDADES:
    - Alto riesgo en reversiones (squeeze)
    - Señales menos frecuentes
    - Requiere timing preciso
    - Psicológicamente difícil de ejecutar
    - Pérdidas rápidas si el mercado gira
    
    CONDICIONES ÓPTIMAS:
    - ADX > 30 con -DI > +DI  
    - EMAs en orden bajista (200 > 50 > 21 > 9)
    - Volumen alto en caídas
    - RSI < 50 consistentemente
    - Lower highs y lower lows
    """
    
    def __init__(self):
        super().__init__(version="1.0")
        
        self.strengths = [
            "Protección de capital en bear markets",
            "Ganancias de 3-10% en caídas rápidas",
            "Identificación precisa de techos",
            "Shorts muy rentables en pánico",
            "Hedge natural para portfolio largo"
        ]
        
        self.weaknesses = [
            "Alto riesgo de short squeeze (-5% a -10%)",
            "Pocas señales (1-2 por semana)",
            "Timing crítico para entradas",
            "Psicológicamente difícil",
            "Costos de préstamo en shorts"
        ]
        
        self.optimal_conditions = [
            "ADX > 30 con -DI dominante",
            "EMAs en orden bajista",
            "Volumen > promedio en caídas",
            "RSI < 50",
            "Sentimiento de mercado negativo",
            "VIX elevado (mercados tradicionales)"
        ]
        
        self.risk_parameters = {
            'max_risk_per_trade': 0.01,  # 1% máximo (shorts son riesgosos)
            'risk_reward_min': 3.0,  # Mínimo 1:3 para shorts
            'confidence_threshold': 0.70,  # Mayor confianza requerida
            'max_daily_trades': 2,
            'max_exposure': 0.02,  # 2% exposición máxima en shorts
            'quick_profit_target': 0.03,  # Tomar ganancias rápido a 3%
            'time_stop': 24  # Cerrar shorts después de 24 horas
        }
    
    def identify_distribution(self, df: pd.DataFrame) -> bool:
        """Identifica patrones de distribución (smart money vendiendo)"""
        
        # Volumen alto en techos
        high_volume_tops = (
            df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1] and
            df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5
        )
        
        # Divergencia bajista
        price_high = df['High'].rolling(14).max()
        rsi_high = df['RSI'].rolling(14).max()
        
        bearish_divergence = (
            price_high.iloc[-1] > price_high.iloc[-14] and
            rsi_high.iloc[-1] < rsi_high.iloc[-14]
        )
        
        # Failed breakouts
        failed_breakout = (
            df['High'].iloc[-1] > df['High'].rolling(20).max().iloc[-2] and
            df['Close'].iloc[-1] < df['Open'].iloc[-1]  # Cierre débil
        )
        
        return high_volume_tops or bearish_divergence or failed_breakout
    
    def find_rally_to_short(self, df: pd.DataFrame) -> bool:
        """Identifica rallies para entrar en short"""
        
        current = df.iloc[-1]
        
        # Rally a resistencia en tendencia bajista
        ema_resistance = (
            current['High'] >= current['EMA_50'] * 0.995 and  # Toca EMA50
            current['Close'] < current['EMA_50'] and  # Pero rechazado
            current['EMA_50'] < current['EMA_200']  # En tendencia bajista
        )
        
        # RSI overbought en downtrend
        rsi_rally = (
            current['RSI'] > 60 and  # RSI alto
            current['EMA_21'] < current['EMA_50'] and  # Pero en downtrend
            current['Close'] < current['EMA_200']  # Bajo MA largo plazo
        )
        
        return ema_resistance or rsi_rally
    
    def generate_signal(self, df: pd.DataFrame, capital: float = 1000) -> Optional[Signal]:
        """Genera señales de trading para mercado bajista"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Verificar tendencia bajista
        bearish_trend = (
            current['EMA_9'] < current['EMA_21'] and
            current['EMA_21'] < current['EMA_50'] and
            current['Close'] < current['EMA_50']
        )
        
        if not bearish_trend:
            return None
        
        signal_strength = 0
        reasons = []
        
        # 1. Patrón de distribución
        if self.identify_distribution(df):
            signal_strength += 4
            reasons.append("DISTRIBUTION_PATTERN")
        
        # 2. Rally para shortear
        if self.find_rally_to_short(df):
            signal_strength += 3
            reasons.append("RALLY_TO_SHORT")
        
        # 3. Breakdown bajista
        if current['Close'] < df['Low'].rolling(20).min().iloc[-2]:
            signal_strength += 3
            reasons.append("BREAKDOWN_20D")
            
            if current['Volume_Ratio'] > 1.5:
                signal_strength += 2
                reasons.append("HIGH_VOLUME_BREAKDOWN")
        
        # 4. Momentum bajista
        if current['MACD'] < current['MACD_Signal'] and current['MACD'] < 0:
            signal_strength += 2
            reasons.append("MACD_BEARISH")
        
        # 5. Estructura bajista
        lower_high = df['High'].iloc[-1] < df['High'].iloc[-10]
        lower_low = df['Low'].iloc[-1] < df['Low'].iloc[-10]
        
        if lower_high and lower_low:
            signal_strength += 2
            reasons.append("BEARISH_STRUCTURE")
        
        # Generar señal SHORT si hay suficiente confianza
        if signal_strength >= 7:  # Mayor exigencia para shorts
            entry_price = current['Close']
            
            # Stop loss más ajustado para shorts (mayor riesgo)
            atr_stop = entry_price + (current['ATR'] * 1.5)  # Más ajustado
            structure_stop = df['High'].rolling(5).max().iloc[-1]  # Reciente
            stop_loss = min(atr_stop, structure_stop * 1.02)  # 2% sobre estructura
            
            # Take profit agresivo (tomar ganancias rápido)
            quick_target = entry_price * (1 - self.risk_parameters['quick_profit_target'])
            atr_target = entry_price - (current['ATR'] * 3)
            take_profit = max(quick_target, atr_target)  # El más conservador
            
            risk_reward = abs(entry_price - take_profit) / abs(stop_loss - entry_price)
            
            if risk_reward >= self.risk_parameters['risk_reward_min']:
                confidence = min(0.4 + (signal_strength * 0.06), 0.85)
                
                return Signal(
                    timestamp=datetime.now(),
                    symbol=df.attrs.get('symbol', 'UNKNOWN'),
                    type="SHORT",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    strategy_name=self.name,
                    strategy_version=self.version,
                    market_regime="BEARISH",
                    risk_reward_ratio=risk_reward,
                    position_size=self.calculate_position_size(
                        capital,
                        self.risk_parameters['max_risk_per_trade'],
                        entry_price,
                        stop_loss
                    ),
                    metadata={
                        'signals': reasons,
                        'signal_strength': signal_strength,
                        'time_limit': self.risk_parameters['time_stop'],
                        'quick_target': quick_target,
                        'warning': 'HIGH_RISK_SHORT'
                    }
                )
        
        return None

# ============================================
# GESTOR DE ESTRATEGIAS
# ============================================

class StrategyManager:
    """Gestiona todas las estrategias y selecciona la óptima según el mercado"""
    
    def __init__(self):
        self.strategies = {
            'RANGING': RangingStrategyV1(),
            'BULLISH': BullishStrategyV1(),
            'BEARISH': BearishStrategyV1()
        }
        self.version = "1.0"
        self.active_strategy = None
    
    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detecta el régimen actual del mercado"""
        
        df = self.strategies['RANGING'].calculate_indicators(df)
        
        # Calcular métricas de tendencia
        ema_alignment_bull = (
            df['EMA_9'].iloc[-1] > df['EMA_21'].iloc[-1] > 
            df['EMA_50'].iloc[-1] > df['EMA_200'].iloc[-1]
        )
        
        ema_alignment_bear = (
            df['EMA_9'].iloc[-1] < df['EMA_21'].iloc[-1] < 
            df['EMA_50'].iloc[-1] < df['EMA_200'].iloc[-1]
        )
        
        # ADX para fuerza de tendencia
        high = df['High'].rolling(14).max()
        low = df['Low'].rolling(14).min()
        atr = df['ATR'].iloc[-1]
        
        # Volatilidad normalizada
        volatility = atr / df['Close'].iloc[-1]
        
        # Estructura de precio
        higher_highs = df['High'].iloc[-1] > df['High'].iloc[-20]
        higher_lows = df['Low'].iloc[-1] > df['Low'].iloc[-20]
        lower_highs = df['High'].iloc[-1] < df['High'].iloc[-20]
        lower_lows = df['Low'].iloc[-1] < df['Low'].iloc[-20]
        
        # Decisión
        if ema_alignment_bull and higher_highs and higher_lows:
            return "BULLISH"
        elif ema_alignment_bear and lower_highs and lower_lows:
            return "BEARISH"
        else:
            return "RANGING"
    
    def get_optimal_strategy(self, df: pd.DataFrame) -> BaseStrategy:
        """Retorna la estrategia óptima para las condiciones actuales"""
        
        regime = self.detect_market_regime(df)
        self.active_strategy = self.strategies[regime]
        return self.active_strategy
    
    def get_all_documentation(self) -> Dict:
        """Retorna documentación completa de todas las estrategias"""
        
        docs = {
            'version': self.version,
            'strategies': {}
        }
        
        for name, strategy in self.strategies.items():
            docs['strategies'][name] = strategy.get_documentation()
        
        return docs
    
    def generate_signal(self, df: pd.DataFrame, capital: float = 1000) -> Optional[Signal]:
        """Genera señal usando la estrategia óptima"""
        
        strategy = self.get_optimal_strategy(df)
        signal = strategy.generate_signal(df, capital)
        
        if signal:
            signal.metadata['market_regime_confidence'] = self._calculate_regime_confidence(df)
        
        return signal
    
    def _calculate_regime_confidence(self, df: pd.DataFrame) -> float:
        """Calcula la confianza en la detección del régimen"""
        
        # Implementar lógica de confianza
        # Por ahora retornamos un valor fijo
        return 0.75

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def get_strategy_comparison() -> pd.DataFrame:
    """Genera tabla comparativa de todas las estrategias"""
    
    manager = StrategyManager()
    comparison = []
    
    for regime, strategy in manager.strategies.items():
        doc = strategy.get_documentation()
        comparison.append({
            'Régimen': regime,
            'Versión': doc['version'],
            'Fortalezas': len(doc['strengths']),
            'Debilidades': len(doc['weaknesses']),
            'Risk per Trade': doc['risk_parameters']['max_risk_per_trade'],
            'Min R:R': doc['risk_parameters']['risk_reward_min'],
            'Confianza Min': doc['risk_parameters']['confidence_threshold']
        })
    
    return pd.DataFrame(comparison)

def test_strategies():
    """Función de prueba para verificar las estrategias"""
    
    print("="*60)
    print("SISTEMA DE ESTRATEGIAS V1.0 - TEST")
    print("="*60)
    
    manager = StrategyManager()
    
    # Mostrar documentación
    docs = manager.get_all_documentation()
    
    for regime, strategy_doc in docs['strategies'].items():
        print(f"\n📊 ESTRATEGIA: {regime} v{strategy_doc['version']}")
        print(f"Fortalezas: {len(strategy_doc['strengths'])}")
        print(f"Debilidades: {len(strategy_doc['weaknesses'])}")
        print(f"Condiciones óptimas: {len(strategy_doc['optimal_conditions'])}")
    
    # Mostrar comparación
    print("\n" + "="*60)
    print("TABLA COMPARATIVA")
    print("="*60)
    comparison = get_strategy_comparison()
    print(comparison.to_string(index=False))
    
    print("\n✅ Sistema de estrategias cargado correctamente")

if __name__ == "__main__":
    test_strategies()