#!/usr/bin/env python3
"""
MARKET ANALYZER - BotphIA
Analizador de condiciones de mercado para evitar señales falsas
"""

import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """Analiza las condiciones del mercado y determina si es apto para operar"""
    
    def __init__(self):
        self.market_conditions = {
            'TRENDING_UP': {'tradeable': True, 'description': 'Tendencia Alcista', 'icon': '📈'},
            'TRENDING_DOWN': {'tradeable': True, 'description': 'Tendencia Bajista', 'icon': '📉'},
            'LATERAL': {'tradeable': False, 'description': 'Mercado Lateral', 'icon': '➡️'},
            'VOLATILE': {'tradeable': False, 'description': 'Alta Volatilidad', 'icon': '⚡'},
            'LOW_VOLUME': {'tradeable': False, 'description': 'Volumen Bajo', 'icon': '🔇'},
            'OVERSOLD': {'tradeable': True, 'description': 'Zona de Compra', 'icon': '🔻'},  # Cambiar a tradeable
            'OVERBOUGHT': {'tradeable': True, 'description': 'Zona de Venta', 'icon': '🔺'},  # Cambiar a tradeable
            'UNSTABLE': {'tradeable': False, 'description': 'Datos Insuficientes', 'icon': '⚠️'},
            'OPTIMAL': {'tradeable': True, 'description': 'Condiciones Óptimas', 'icon': '✅'}
        }
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcula el RSI"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            return 100.0
        
        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def calculate_atr(self, high: List[float], low: List[float], close: List[float], period: int = 14) -> float:
        """Calcula el Average True Range para medir volatilidad"""
        if len(high) < period:
            return 0.0
            
        tr_list = []
        for i in range(1, len(high)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        if not tr_list:
            return 0.0
            
        atr = np.mean(tr_list[-period:])
        return float(atr)
    
    def detect_trend(self, prices: List[float], period: int = 20) -> str:
        """Detecta la tendencia del mercado"""
        if len(prices) < period:
            return 'LATERAL'
            
        # Calcular medias móviles
        sma_short = np.mean(prices[-10:])
        sma_long = np.mean(prices[-period:])
        
        # Calcular pendiente
        x = np.arange(len(prices[-period:]))
        y = prices[-period:]
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalizar pendiente respecto al precio
        normalized_slope = (slope / sma_long) * 100
        
        # Hacer mucho más sensible para detectar micro-tendencias
        if normalized_slope > 0.05:  # Ultra sensible para testnet
            return 'TRENDING_UP'
        elif normalized_slope < -0.05:  # Ultra sensible para testnet
            return 'TRENDING_DOWN'
        else:
            return 'LATERAL'
    
    def analyze_market_condition(self, 
                                symbol: str,
                                prices: List[float],
                                high: List[float],
                                low: List[float],
                                volume: List[float]) -> Dict[str, Any]:
        """Analiza las condiciones completas del mercado"""
        
        if len(prices) < 30:
            return {
                'condition': 'UNSTABLE',
                'tradeable': False,
                'reasons': ['Datos insuficientes para análisis'],
                'confidence': 0,
                'details': {}
            }
        
        # Calcular indicadores
        rsi = self.calculate_rsi(prices)
        atr = self.calculate_atr(high, low, prices)
        trend = self.detect_trend(prices)
        
        # Calcular volatilidad relativa
        current_price = prices[-1]
        volatility_ratio = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Calcular volumen relativo
        avg_volume = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        current_volume = volume[-1] if volume else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # Determinar condición del mercado
        condition = 'OPTIMAL'
        reasons = []
        warnings = []
        
        # Verificar RSI extremo PRIMERO (condición más importante)
        if rsi < 25:
            condition = 'OVERSOLD'
            reasons.append(f'RSI muy bajo ({rsi:.1f})')
            warnings.append('⚠️ NO vender en sobreventa extrema')
        elif rsi > 75:
            condition = 'OVERBOUGHT'
            reasons.append(f'RSI muy alto ({rsi:.1f})')
            warnings.append('⚠️ NO comprar en sobrecompra extrema')
        # Condiciones favorables para trading
        elif 30 <= rsi <= 40 and trend == 'TRENDING_UP':
            condition = 'OPTIMAL'
            reasons.append(f'RSI bajo en tendencia alcista ({rsi:.1f})')
        elif 60 <= rsi <= 70 and trend == 'TRENDING_DOWN':
            condition = 'OPTIMAL'
            reasons.append(f'RSI alto en tendencia bajista ({rsi:.1f})')
        elif rsi < 35:
            warnings.append('📊 RSI bajo, posible rebote')
        elif rsi > 65:
            warnings.append('📊 RSI alto, posible corrección')
        
        # Verificar volatilidad
        if volatility_ratio > 5:
            condition = 'VOLATILE'
            reasons.append(f'Volatilidad extrema ({volatility_ratio:.1f}%)')
            warnings.append('⚡ Riesgo alto por volatilidad')
        
        # Verificar volumen
        if volume_ratio < 0.3:
            if condition == 'OPTIMAL':
                condition = 'LOW_VOLUME'
            reasons.append(f'Volumen muy bajo ({volume_ratio:.1f}x)')
            warnings.append('🔇 Liquidez insuficiente')
        
        # Verificar tendencia
        if trend == 'LATERAL' and condition == 'OPTIMAL':
            condition = 'LATERAL'
            reasons.append('Sin tendencia clara')
            warnings.append('➡️ Mercado sin dirección definida')
        
        # Calcular confianza para operar dinámicamente
        confidence = 50  # Base más realista
        
        # Bonos por condiciones favorables
        if condition == 'OPTIMAL':
            confidence += 40
        elif condition in ['TRENDING_UP', 'TRENDING_DOWN']:
            confidence += 25
        elif condition == 'OVERSOLD' or condition == 'OVERBOUGHT':
            confidence += 15  # Extremos tienen oportunidad pero riesgo
        
        # Ajustes por RSI
        if 40 <= rsi <= 60:  # RSI neutral es bueno
            confidence += 10
        elif rsi < 30 or rsi > 70:  # Extremos
            confidence -= 10
        
        # Ajustes por volumen
        if volume_ratio > 1.5:
            confidence += 15
        elif volume_ratio > 1.0:
            confidence += 5
        elif volume_ratio < 0.5:
            confidence -= 20
        
        # Ajustes por volatilidad
        if volatility_ratio < 1.0:  # Baja volatilidad es buena
            confidence += 10
        elif volatility_ratio > 3:
            confidence -= 15
        elif volatility_ratio > 5:
            confidence -= 25
        
        # Ajustes por tendencia
        if trend == 'LATERAL':
            confidence -= 15
        elif trend in ['TRENDING_UP', 'TRENDING_DOWN']:
            confidence += 10
        
        confidence = max(10, min(95, confidence))  # Entre 10% y 95%
        
        # Determinar si es tradeable
        tradeable = self.market_conditions[condition]['tradeable']
        
        # Generar recomendaciones
        recommendations = []
        if not tradeable:
            if condition == 'OVERSOLD':
                recommendations.append('✅ Considerar COMPRA cuando RSI suba de 30')
                recommendations.append('❌ NO VENDER ahora')
            elif condition == 'OVERBOUGHT':
                recommendations.append('✅ Considerar VENTA cuando RSI baje de 70')
                recommendations.append('❌ NO COMPRAR ahora')
            elif condition == 'LATERAL':
                recommendations.append('⏸️ Esperar ruptura de rango')
                recommendations.append('📊 Operar solo en extremos del rango')
            elif condition == 'VOLATILE':
                recommendations.append('⚠️ Reducir tamaño de posición')
                recommendations.append('🛡️ Usar stops más amplios')
            elif condition == 'LOW_VOLUME':
                recommendations.append('⏰ Esperar mayor actividad')
                recommendations.append('📊 Evitar órdenes grandes')
        
        return {
            'condition': condition,
            'condition_text': self.market_conditions[condition]['description'],
            'condition_icon': self.market_conditions[condition]['icon'],
            'tradeable': tradeable,
            'confidence': confidence,
            'trend': trend,
            'reasons': reasons,
            'warnings': warnings,
            'recommendations': recommendations,
            'details': {
                'rsi': rsi,
                'atr': atr,
                'volatility_ratio': volatility_ratio,
                'volume_ratio': volume_ratio,
                'current_price': current_price
            }
        }
    
    def validate_signal(self, 
                       signal_type: str,  # 'BUY' or 'SELL'
                       market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Valida si una señal es apropiada para las condiciones actuales"""
        
        is_valid = True
        validation_score = 100
        reasons = []
        
        rsi = market_analysis['details'].get('rsi', 50)
        condition = market_analysis['condition']
        
        # Validar señales SELL
        if signal_type == 'SELL':
            if rsi < 35:
                is_valid = False
                validation_score = 0
                reasons.append('❌ RSI muy bajo para vender')
            elif rsi < 45:
                validation_score -= 50
                reasons.append('⚠️ RSI bajo, venta arriesgada')
            elif rsi > 65:
                validation_score = min(100, validation_score + 20)
                reasons.append('✅ RSI favorable para venta')
            
            if condition == 'OVERSOLD':
                is_valid = False
                validation_score = 0
                reasons.append('❌ Mercado en sobreventa extrema')
            elif condition == 'TRENDING_UP':
                validation_score -= 30
                reasons.append('⚠️ Venta contra tendencia alcista')
        
        # Validar señales BUY
        elif signal_type == 'BUY':
            if rsi > 65:
                is_valid = False
                validation_score = 0
                reasons.append('❌ RSI muy alto para comprar')
            elif rsi > 55:
                validation_score -= 50
                reasons.append('⚠️ RSI alto, compra arriesgada')
            elif rsi < 35:
                validation_score = min(100, validation_score + 20)
                reasons.append('✅ RSI favorable para compra')
            
            if condition == 'OVERBOUGHT':
                is_valid = False
                validation_score = 0
                reasons.append('❌ Mercado en sobrecompra extrema')
            elif condition == 'TRENDING_DOWN':
                validation_score -= 30
                reasons.append('⚠️ Compra contra tendencia bajista')
        
        # Penalizaciones generales
        if condition == 'LATERAL':
            validation_score -= 20
            reasons.append('➡️ Mercado lateral, señal débil')
        elif condition == 'VOLATILE':
            validation_score -= 30
            reasons.append('⚡ Alta volatilidad, riesgo elevado')
        elif condition == 'LOW_VOLUME':
            validation_score -= 25
            reasons.append('🔇 Volumen bajo, liquidez limitada')
        
        validation_score = max(0, validation_score)
        
        return {
            'is_valid': is_valid and validation_score > 30,
            'score': validation_score,
            'reasons': reasons,
            'recommendation': '✅ Ejecutar' if is_valid and validation_score > 50 else 
                            '⚠️ Revisar' if validation_score > 30 else 
                            '❌ No ejecutar'
        }

# Instancia global
_market_analyzer = None

def get_market_analyzer() -> MarketAnalyzer:
    """Obtiene instancia singleton del analizador de mercado"""
    global _market_analyzer
    if _market_analyzer is None:
        _market_analyzer = MarketAnalyzer()
    return _market_analyzer