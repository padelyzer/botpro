#!/usr/bin/env python3
"""
SIGNAL VALIDATION PIPELINE - BotphIA
Pipeline de validación multi-filtro para señales de trading
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

# Import error handling system
try:
    from error_handler import handle_calculation_error, CalculationError
except ImportError:
    # Fallback if error_handler not available
    def handle_calculation_error(error, context=None):
        print(f"Calculation Error: {error}")
    class CalculationError(Exception): pass

logger = logging.getLogger(__name__)

class FilterResult(Enum):
    """Resultado de un filtro"""
    PASS = "pass"
    REJECT = "reject"
    WARNING = "warning"

@dataclass
class SignalEvaluation:
    """Evaluación completa de una señal"""
    original_signal: Dict[str, Any]
    final_score: float
    is_valid: bool
    filters_passed: List[str]
    filters_failed: List[str]
    warnings: List[str]
    recommendations: List[str]
    market_condition: str
    execution_priority: str  # HIGH, MEDIUM, LOW

class SignalValidationPipeline:
    """Pipeline de validación con múltiples filtros"""
    
    def __init__(self):
        # Importar analizador de mercado
        from market_analyzer import get_market_analyzer
        self.market_analyzer = get_market_analyzer()
        
        # Configurar pesos de cada filtro
        self.filter_weights = {
            'market_condition': 0.25,  # Condición general del mercado
            'trend_alignment': 0.20,   # Alineación con tendencia
            'rsi_validation': 0.15,    # RSI apropiado
            'volume_check': 0.15,      # Volumen suficiente
            'volatility': 0.10,        # Volatilidad aceptable
            'correlation': 0.10,       # Correlación con mercado
            'time_filter': 0.05        # Horario de trading
        }
        
        # Umbrales de validación
        self.thresholds = {
            'min_score': 60,           # Score mínimo para aprobar
            'high_priority': 85,       # Score para prioridad alta
            'medium_priority': 70,     # Score para prioridad media
            'max_volatility': 5.0,     # Volatilidad máxima (%)
            'min_volume_ratio': 0.5,   # Volumen mínimo vs promedio
            'correlation_threshold': 0.7  # Correlación con BTC
        }
    
    def filter_market_condition(self, signal: Dict, market_data: Dict) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 1: Condición general del mercado"""
        messages = []
        score = 0
        
        condition = market_data.get('condition', 'UNKNOWN')
        tradeable = market_data.get('tradeable', False)
        confidence = market_data.get('confidence', 0)
        
        if not tradeable:
            if condition == 'OVERSOLD' and signal['action'] == 'SELL':
                messages.append(f"❌ No vender en {condition}")
                return FilterResult.REJECT, 0, messages
            elif condition == 'OVERBOUGHT' and signal['action'] == 'BUY':
                messages.append(f"❌ No comprar en {condition}")
                return FilterResult.REJECT, 0, messages
            elif condition == 'LATERAL':
                messages.append(f"⚠️ Mercado lateral - señal débil")
                score = 30
            elif condition == 'VOLATILE':
                messages.append(f"⚠️ Alta volatilidad - riesgo elevado")
                score = 40
            else:
                score = 20
                messages.append(f"⚠️ Condición {condition} no óptima")
        else:
            score = min(100, confidence)
            messages.append(f"✅ Mercado {condition} apto para operar")
        
        return FilterResult.PASS if score > 50 else FilterResult.WARNING, score, messages
    
    def filter_trend_alignment(self, signal: Dict, market_data: Dict) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 2: Alineación con la tendencia"""
        messages = []
        score = 100
        
        trend = market_data.get('trend', 'LATERAL')
        
        if signal['action'] == 'BUY':
            if trend == 'TRENDING_UP':
                messages.append("✅ Compra alineada con tendencia alcista")
                score = 100
            elif trend == 'TRENDING_DOWN':
                messages.append("⚠️ Compra contra tendencia bajista")
                score = 30
            else:
                messages.append("📊 Sin tendencia clara")
                score = 60
        else:  # SELL
            if trend == 'TRENDING_DOWN':
                messages.append("✅ Venta alineada con tendencia bajista")
                score = 100
            elif trend == 'TRENDING_UP':
                messages.append("⚠️ Venta contra tendencia alcista")
                score = 30
            else:
                messages.append("📊 Sin tendencia clara")
                score = 60
        
        return FilterResult.PASS if score > 50 else FilterResult.WARNING, score, messages
    
    def filter_rsi_validation(self, signal: Dict, market_data: Dict) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 3: Validación de RSI"""
        messages = []
        rsi = market_data.get('details', {}).get('rsi', 50)
        
        if signal['action'] == 'BUY':
            if rsi < 30:
                score = 100
                messages.append(f"✅ RSI {rsi:.1f} - Sobreventa confirmada")
            elif rsi < 40:
                score = 80
                messages.append(f"✅ RSI {rsi:.1f} - Buena zona de compra")
            elif rsi < 50:
                score = 60
                messages.append(f"📊 RSI {rsi:.1f} - Zona neutral")
            elif rsi < 65:
                score = 30
                messages.append(f"⚠️ RSI {rsi:.1f} - Zona alta para compra")
            else:
                score = 0
                messages.append(f"❌ RSI {rsi:.1f} - Sobrecompra")
                return FilterResult.REJECT, score, messages
        else:  # SELL
            if rsi > 70:
                score = 100
                messages.append(f"✅ RSI {rsi:.1f} - Sobrecompra confirmada")
            elif rsi > 60:
                score = 80
                messages.append(f"✅ RSI {rsi:.1f} - Buena zona de venta")
            elif rsi > 50:
                score = 60
                messages.append(f"📊 RSI {rsi:.1f} - Zona neutral")
            elif rsi > 35:
                score = 30
                messages.append(f"⚠️ RSI {rsi:.1f} - Zona baja para venta")
            else:
                score = 0
                messages.append(f"❌ RSI {rsi:.1f} - Sobreventa")
                return FilterResult.REJECT, score, messages
        
        return FilterResult.PASS if score > 30 else FilterResult.WARNING, score, messages
    
    def filter_volume_check(self, signal: Dict, market_data: Dict) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 4: Verificación de volumen"""
        messages = []
        volume_ratio = market_data.get('details', {}).get('volume_ratio', 1.0)
        
        if volume_ratio < 0.3:
            score = 0
            messages.append(f"❌ Volumen muy bajo ({volume_ratio:.1f}x)")
            return FilterResult.REJECT, score, messages
        elif volume_ratio < 0.5:
            score = 30
            messages.append(f"⚠️ Volumen bajo ({volume_ratio:.1f}x)")
        elif volume_ratio < 0.8:
            score = 60
            messages.append(f"📊 Volumen moderado ({volume_ratio:.1f}x)")
        elif volume_ratio < 1.5:
            score = 80
            messages.append(f"✅ Volumen normal ({volume_ratio:.1f}x)")
        else:
            score = 100
            messages.append(f"✅ Volumen alto ({volume_ratio:.1f}x)")
        
        return FilterResult.PASS if score > 30 else FilterResult.WARNING, score, messages
    
    def filter_volatility(self, signal: Dict, market_data: Dict) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 5: Control de volatilidad"""
        messages = []
        volatility_ratio = market_data.get('details', {}).get('volatility_ratio', 0)
        
        if volatility_ratio > self.thresholds['max_volatility']:
            score = 20
            messages.append(f"⚠️ Volatilidad extrema ({volatility_ratio:.1f}%)")
            return FilterResult.WARNING, score, messages
        elif volatility_ratio > 3:
            score = 50
            messages.append(f"⚠️ Alta volatilidad ({volatility_ratio:.1f}%)")
        elif volatility_ratio > 1.5:
            score = 80
            messages.append(f"✅ Volatilidad normal ({volatility_ratio:.1f}%)")
        else:
            score = 100
            messages.append(f"✅ Baja volatilidad ({volatility_ratio:.1f}%)")
        
        return FilterResult.PASS, score, messages
    
    def filter_correlation(self, signal: Dict, btc_trend: str) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 6: Correlación con BTC"""
        messages = []
        
        # Simplificado: asumimos que las altcoins siguen a BTC
        if signal['symbol'].startswith('BTC'):
            score = 100
            messages.append("✅ BTC - Sin correlación necesaria")
        elif btc_trend == 'UP' and signal['action'] == 'BUY':
            score = 90
            messages.append("✅ Compra alineada con BTC alcista")
        elif btc_trend == 'DOWN' and signal['action'] == 'SELL':
            score = 90
            messages.append("✅ Venta alineada con BTC bajista")
        elif btc_trend == 'LATERAL':
            score = 70
            messages.append("📊 BTC lateral - correlación neutral")
        else:
            score = 40
            messages.append("⚠️ Señal contraria a tendencia BTC")
        
        return FilterResult.PASS if score > 50 else FilterResult.WARNING, score, messages
    
    def filter_time(self, signal: Dict) -> Tuple[FilterResult, float, List[str]]:
        """Filtro 7: Horario de trading"""
        messages = []
        current_hour = datetime.now().hour
        
        # Mejores horas: apertura de mercados principales
        # 9-11 AM EST (14-16 UTC) - Apertura NYSE
        # 2-4 AM EST (7-9 UTC) - Apertura Europa
        # 8-10 PM EST (1-3 UTC) - Apertura Asia
        
        best_hours = [1, 2, 3, 7, 8, 9, 14, 15, 16]
        good_hours = [4, 5, 6, 10, 11, 12, 13, 17, 18]
        
        if current_hour in best_hours:
            score = 100
            messages.append(f"✅ Horario óptimo ({current_hour}:00 UTC)")
        elif current_hour in good_hours:
            score = 80
            messages.append(f"✅ Buen horario ({current_hour}:00 UTC)")
        else:
            score = 60
            messages.append(f"📊 Horario regular ({current_hour}:00 UTC)")
        
        return FilterResult.PASS, score, messages
    
    def calculate_btc_trend(self) -> str:
        """Calcular tendencia actual de BTC"""
        try:
            from binance_integration import BinanceConnector
            connector = BinanceConnector(testnet=True)
            df = connector.get_historical_data('BTCUSDT', timeframe='1h', limit=24)
            
            if not df.empty:
                sma_short = df['close'].tail(6).mean()
                sma_long = df['close'].tail(24).mean()
                
                if sma_short > sma_long * 1.01:
                    return 'UP'
                elif sma_short < sma_long * 0.99:
                    return 'DOWN'
            
            return 'LATERAL'
        except Exception as e:
            handle_calculation_error(e, {
                'operation': 'detect_trend',
                'prices_length': len(prices) if prices else 0,
                'function': 'detect_trend'
            })
            return 'LATERAL'
    
    def validate_signal(self, 
                       signal: Dict[str, Any],
                       prices: List[float],
                       high: List[float],
                       low: List[float],
                       volume: List[float]) -> SignalEvaluation:
        """Ejecutar pipeline completo de validación"""
        
        # Analizar condición del mercado
        market_analysis = self.market_analyzer.analyze_market_condition(
            signal['symbol'], prices, high, low, volume
        )
        
        # Obtener tendencia de BTC
        btc_trend = self.calculate_btc_trend()
        
        # Ejecutar todos los filtros
        filters_results = {}
        total_score = 0
        all_messages = []
        filters_passed = []
        filters_failed = []
        warnings = []
        
        # Filtro 1: Condición del mercado
        result, score, messages = self.filter_market_condition(signal, market_analysis)
        filters_results['market_condition'] = (result, score)
        total_score += score * self.filter_weights['market_condition']
        all_messages.extend(messages)
        if result == FilterResult.REJECT:
            filters_failed.append('market_condition')
        elif result == FilterResult.WARNING:
            warnings.append('market_condition')
        else:
            filters_passed.append('market_condition')
        
        # Filtro 2: Alineación con tendencia
        result, score, messages = self.filter_trend_alignment(signal, market_analysis)
        filters_results['trend_alignment'] = (result, score)
        total_score += score * self.filter_weights['trend_alignment']
        all_messages.extend(messages)
        if result == FilterResult.WARNING:
            warnings.append('trend_alignment')
        else:
            filters_passed.append('trend_alignment')
        
        # Filtro 3: RSI
        result, score, messages = self.filter_rsi_validation(signal, market_analysis)
        filters_results['rsi_validation'] = (result, score)
        total_score += score * self.filter_weights['rsi_validation']
        all_messages.extend(messages)
        if result == FilterResult.REJECT:
            filters_failed.append('rsi_validation')
        elif result == FilterResult.WARNING:
            warnings.append('rsi_validation')
        else:
            filters_passed.append('rsi_validation')
        
        # Filtro 4: Volumen
        result, score, messages = self.filter_volume_check(signal, market_analysis)
        filters_results['volume_check'] = (result, score)
        total_score += score * self.filter_weights['volume_check']
        all_messages.extend(messages)
        if result == FilterResult.REJECT:
            filters_failed.append('volume_check')
        elif result == FilterResult.WARNING:
            warnings.append('volume_check')
        else:
            filters_passed.append('volume_check')
        
        # Filtro 5: Volatilidad
        result, score, messages = self.filter_volatility(signal, market_analysis)
        filters_results['volatility'] = (result, score)
        total_score += score * self.filter_weights['volatility']
        all_messages.extend(messages)
        if result == FilterResult.WARNING:
            warnings.append('volatility')
        else:
            filters_passed.append('volatility')
        
        # Filtro 6: Correlación con BTC
        result, score, messages = self.filter_correlation(signal, btc_trend)
        filters_results['correlation'] = (result, score)
        total_score += score * self.filter_weights['correlation']
        all_messages.extend(messages)
        if result == FilterResult.WARNING:
            warnings.append('correlation')
        else:
            filters_passed.append('correlation')
        
        # Filtro 7: Horario
        result, score, messages = self.filter_time(signal)
        filters_results['time_filter'] = (result, score)
        total_score += score * self.filter_weights['time_filter']
        all_messages.extend(messages)
        filters_passed.append('time_filter')
        
        # Determinar si la señal es válida
        # Permitir señales con score alto O de BotphIA Signals con advertencias
        is_system_advanced = signal.get('philosopher') in ['Sistema Avanzado', 'BotphIA Signals']
        is_valid = (
            (len(filters_failed) == 0 and total_score >= self.thresholds['min_score']) or
            (is_system_advanced and total_score >= 40)  # Umbral más bajo para BotphIA Signals
        )
        
        # Determinar prioridad de ejecución
        if total_score >= self.thresholds['high_priority']:
            execution_priority = 'HIGH'
        elif total_score >= self.thresholds['medium_priority']:
            execution_priority = 'MEDIUM'
        else:
            execution_priority = 'LOW'
        
        # Generar recomendaciones
        recommendations = []
        if is_valid:
            if execution_priority == 'HIGH':
                recommendations.append("🚀 Ejecutar inmediatamente - Alta confianza")
            elif execution_priority == 'MEDIUM':
                recommendations.append("✅ Ejecutar con precaución - Confianza media")
            else:
                recommendations.append("⚠️ Considerar ejecutar - Baja confianza")
            
            if len(warnings) > 0:
                recommendations.append(f"⚠️ Revisar: {', '.join(warnings)}")
        else:
            recommendations.append("❌ NO ejecutar señal")
            if len(filters_failed) > 0:
                recommendations.append(f"❌ Filtros fallidos: {', '.join(filters_failed)}")
        
        # Crear evaluación final
        evaluation = SignalEvaluation(
            original_signal=signal,
            final_score=total_score,
            is_valid=is_valid,
            filters_passed=filters_passed,
            filters_failed=filters_failed,
            warnings=warnings,
            recommendations=recommendations,
            market_condition=market_analysis.get('condition', 'UNKNOWN'),
            execution_priority=execution_priority
        )
        
        # Log del resultado
        logger.info(f"""
        📊 VALIDACIÓN DE SEÑAL: {signal['symbol']} - {signal['action']}
        Score Final: {total_score:.1f}/100
        Válida: {'✅ SI' if is_valid else '❌ NO'}
        Prioridad: {execution_priority}
        Filtros OK: {len(filters_passed)}/{len(self.filter_weights)}
        Condición: {market_analysis.get('condition_text', 'Unknown')}
        """)
        
        for msg in all_messages[:5]:  # Mostrar solo top 5 mensajes
            logger.info(f"  {msg}")
        
        return evaluation

# Instancia global
_signal_pipeline = None

def get_signal_pipeline() -> SignalValidationPipeline:
    """Obtiene instancia singleton del pipeline de validación"""
    global _signal_pipeline
    if _signal_pipeline is None:
        _signal_pipeline = SignalValidationPipeline()
    return _signal_pipeline