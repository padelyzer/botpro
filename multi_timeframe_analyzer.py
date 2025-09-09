#!/usr/bin/env python3
"""
Analizador multi-timeframe para análisis técnico granular
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from binance_integration import BinanceConnector
from enhanced_trading_config import get_enhanced_config

logger = logging.getLogger(__name__)

class MultiTimeframeAnalyzer:
    """Analizador técnico usando múltiples timeframes"""
    
    def __init__(self):
        self.connector = BinanceConnector(use_optimized=True)
        self.config = get_enhanced_config()
        
        # Timeframes para análisis completo
        self.timeframes = {
            'short': '5m',    # Análisis a corto plazo
            'medium': '15m',  # Análisis medio
            'long': '1h',     # Análisis a largo plazo
            'trend': '4h'     # Análisis de tendencia
        }
        
        logger.info("📊 Analizador multi-timeframe inicializado")
    
    async def analyze_symbol_multitf(self, symbol: str) -> Dict:
        """Análisis completo de un símbolo en múltiples timeframes"""
        try:
            # Obtener datos de todos los timeframes
            timeframe_data = await self.fetch_all_timeframes(symbol)
            
            if not timeframe_data:
                return {}
            
            # Análisis técnico por timeframe
            tf_analysis = {}
            for tf_name, data in timeframe_data.items():
                tf_analysis[tf_name] = self.analyze_timeframe(data, tf_name)
            
            # Consolidar análisis
            consolidated = self.consolidate_analysis(tf_analysis, symbol)
            
            return consolidated
            
        except Exception as e:
            logger.error(f"Error en análisis multi-timeframe para {symbol}: {e}")
            return {}
    
    async def fetch_all_timeframes(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Obtiene datos de todos los timeframes en paralelo"""
        tasks = {}
        
        for tf_name, timeframe in self.timeframes.items():
            tasks[tf_name] = asyncio.create_task(
                asyncio.to_thread(
                    self.connector.get_historical_data, 
                    symbol, timeframe, 100
                )
            )
        
        # Ejecutar todas las tareas en paralelo
        results = {}
        for tf_name, task in tasks.items():
            try:
                data = await task
                if not data.empty:
                    results[tf_name] = data
                else:
                    logger.warning(f"⚠️ Datos vacíos para {symbol} {self.timeframes[tf_name]}")
            except Exception as e:
                logger.error(f"Error obteniendo datos {tf_name} para {symbol}: {e}")
        
        return results
    
    def analyze_timeframe(self, data: pd.DataFrame, tf_name: str) -> Dict:
        """Análisis técnico de un timeframe específico"""
        if data.empty:
            return {}
        
        try:
            analysis = {
                'timeframe': tf_name,
                'trend': self.detect_trend(data),
                'momentum': self.analyze_momentum(data),
                'support_resistance': self.find_support_resistance(data),
                'volume_analysis': self.analyze_volume(data),
                'volatility': self.calculate_volatility(data),
                'signals': self.generate_tf_signals(data)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando timeframe {tf_name}: {e}")
            return {}
    
    def detect_trend(self, data: pd.DataFrame) -> Dict:
        """Detecta tendencia usando EMAs"""
        try:
            # EMAs
            data['ema_20'] = data['close'].ewm(span=20).mean()
            data['ema_50'] = data['close'].ewm(span=50).mean()
            
            current_price = data['close'].iloc[-1]
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            
            # Determinar tendencia
            if current_price > ema_20 > ema_50:
                trend = 'UPTREND'
                strength = min(100, ((current_price - ema_50) / ema_50) * 100 * 10)
            elif current_price < ema_20 < ema_50:
                trend = 'DOWNTREND'
                strength = min(100, ((ema_50 - current_price) / ema_50) * 100 * 10)
            else:
                trend = 'SIDEWAYS'
                strength = 50
            
            return {
                'direction': trend,
                'strength': abs(strength),
                'ema_20': ema_20,
                'ema_50': ema_50,
                'price_vs_ema20': ((current_price - ema_20) / ema_20) * 100
            }
            
        except Exception as e:
            logger.error(f"Error detectando tendencia: {e}")
            return {'direction': 'NEUTRAL', 'strength': 50}
    
    def analyze_momentum(self, data: pd.DataFrame) -> Dict:
        """Análisis de momentum con RSI y MACD"""
        try:
            # RSI
            rsi = self.calculate_rsi(data['close'])
            current_rsi = rsi.iloc[-1]
            
            # MACD
            macd_line, signal_line, histogram = self.calculate_macd(data['close'])
            macd_current = macd_line.iloc[-1]
            signal_current = signal_line.iloc[-1]
            
            # Evaluación de momentum
            if current_rsi > 70:
                rsi_signal = 'OVERBOUGHT'
            elif current_rsi < 30:
                rsi_signal = 'OVERSOLD'
            else:
                rsi_signal = 'NEUTRAL'
            
            macd_signal = 'BULLISH' if macd_current > signal_current else 'BEARISH'
            
            return {
                'rsi': current_rsi,
                'rsi_signal': rsi_signal,
                'macd': macd_current,
                'macd_signal': macd_signal,
                'momentum_score': self.calculate_momentum_score(current_rsi, macd_current, signal_current)
            }
            
        except Exception as e:
            logger.error(f"Error analizando momentum: {e}")
            return {'momentum_score': 50}
    
    def find_support_resistance(self, data: pd.DataFrame, window: int = 20) -> Dict:
        """Encuentra niveles de soporte y resistencia"""
        try:
            highs = data['high'].rolling(window=window).max()
            lows = data['low'].rolling(window=window).min()
            
            current_price = data['close'].iloc[-1]
            
            # Encontrar niveles significativos
            resistance_levels = highs.dropna().unique()[-3:]  # Últimos 3 niveles
            support_levels = lows.dropna().unique()[-3:]      # Últimos 3 niveles
            
            # Filtrar niveles relevantes
            resistance = [r for r in resistance_levels if r > current_price]
            support = [s for s in support_levels if s < current_price]
            
            # Calcular distancias
            nearest_resistance = min(resistance) if resistance else None
            nearest_support = max(support) if support else None
            
            return {
                'resistance_levels': sorted(resistance)[:2],  # Top 2 resistencias
                'support_levels': sorted(support, reverse=True)[:2],  # Top 2 soportes
                'nearest_resistance': nearest_resistance,
                'nearest_support': nearest_support,
                'resistance_distance': ((nearest_resistance - current_price) / current_price * 100) if nearest_resistance else None,
                'support_distance': ((current_price - nearest_support) / current_price * 100) if nearest_support else None
            }
            
        except Exception as e:
            logger.error(f"Error encontrando soporte/resistencia: {e}")
            return {}
    
    def analyze_volume(self, data: pd.DataFrame) -> Dict:
        """Análisis de volumen"""
        try:
            # Volumen promedio
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Análisis de tendencia de volumen
            volume_trend = 'INCREASING' if volume_ratio > 1.2 else 'DECREASING' if volume_ratio < 0.8 else 'STABLE'
            
            return {
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'volume_score': min(100, volume_ratio * 50)
            }
            
        except Exception as e:
            logger.error(f"Error analizando volumen: {e}")
            return {'volume_score': 50}
    
    def calculate_volatility(self, data: pd.DataFrame) -> Dict:
        """Calcula métricas de volatilidad"""
        try:
            # ATR (Average True Range)
            atr = self.calculate_atr(data)
            current_atr = atr.iloc[-1]
            
            # Volatilidad basada en retornos
            returns = data['close'].pct_change()
            volatility = returns.std() * 100
            
            # Clasificación de volatilidad
            if volatility > 3:
                vol_level = 'HIGH'
            elif volatility > 1.5:
                vol_level = 'MEDIUM'
            else:
                vol_level = 'LOW'
            
            return {
                'atr': current_atr,
                'volatility_pct': volatility,
                'volatility_level': vol_level,
                'volatility_score': min(100, volatility * 20)
            }
            
        except Exception as e:
            logger.error(f"Error calculando volatilidad: {e}")
            return {'volatility_level': 'MEDIUM', 'volatility_score': 50}
    
    def generate_tf_signals(self, data: pd.DataFrame) -> Dict:
        """Genera señales específicas del timeframe"""
        try:
            # Análisis simple de señales
            trend = self.detect_trend(data)
            momentum = self.analyze_momentum(data)
            
            # Señal basada en alineación
            if (trend['direction'] == 'UPTREND' and 
                momentum['rsi_signal'] != 'OVERBOUGHT' and 
                momentum['macd_signal'] == 'BULLISH'):
                signal = 'BUY'
                confidence = 75
            elif (trend['direction'] == 'DOWNTREND' and 
                  momentum['rsi_signal'] != 'OVERSOLD' and 
                  momentum['macd_signal'] == 'BEARISH'):
                signal = 'SELL'
                confidence = 75
            else:
                signal = 'HOLD'
                confidence = 50
            
            return {
                'signal': signal,
                'confidence': confidence,
                'reasoning': f"Trend: {trend['direction']}, RSI: {momentum['rsi_signal']}, MACD: {momentum['macd_signal']}"
            }
            
        except Exception as e:
            logger.error(f"Error generando señales TF: {e}")
            return {'signal': 'HOLD', 'confidence': 50}
    
    def consolidate_analysis(self, tf_analysis: Dict, symbol: str) -> Dict:
        """Consolida análisis de múltiples timeframes"""
        try:
            # Ponderar análisis por timeframe
            weights = {
                'short': 0.2,   # Peso menor para corto plazo
                'medium': 0.3,  # Peso medio
                'long': 0.3,    # Peso alto
                'trend': 0.2    # Peso para tendencia general
            }
            
            consolidated = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'timeframe_analysis': tf_analysis,
                'overall_score': 0,
                'overall_signal': 'HOLD',
                'confidence_score': 0,
                'risk_level': 'MEDIUM'
            }
            
            # Calcular score general
            total_score = 0
            total_weight = 0
            signal_votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
            
            for tf_name, analysis in tf_analysis.items():
                weight = weights.get(tf_name, 0.25)
                
                # Score de señales
                if 'signals' in analysis:
                    signal = analysis['signals'].get('signal', 'HOLD')
                    confidence = analysis['signals'].get('confidence', 50)
                    
                    signal_votes[signal] += weight
                    total_score += confidence * weight
                    total_weight += weight
            
            # Determinar señal consolidada
            if signal_votes['BUY'] > signal_votes['SELL'] and signal_votes['BUY'] > signal_votes['HOLD']:
                consolidated['overall_signal'] = 'BUY'
            elif signal_votes['SELL'] > signal_votes['BUY'] and signal_votes['SELL'] > signal_votes['HOLD']:
                consolidated['overall_signal'] = 'SELL'
            
            # Calcular confidence final
            if total_weight > 0:
                consolidated['confidence_score'] = total_score / total_weight
                consolidated['overall_score'] = total_score / total_weight
            
            # Evaluar riesgo
            volatility_scores = [tf.get('volatility', {}).get('volatility_score', 50) 
                               for tf in tf_analysis.values()]
            avg_volatility = sum(volatility_scores) / len(volatility_scores) if volatility_scores else 50
            
            if avg_volatility > 70:
                consolidated['risk_level'] = 'HIGH'
            elif avg_volatility < 30:
                consolidated['risk_level'] = 'LOW'
            
            return consolidated
            
        except Exception as e:
            logger.error(f"Error consolidando análisis: {e}")
            return {'overall_signal': 'HOLD', 'confidence_score': 50}
    
    # Métodos auxiliares de cálculo técnico
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def calculate_momentum_score(self, rsi: float, macd: float, signal: float) -> float:
        """Calcula score de momentum combinado"""
        # Normalizar RSI (0-100 -> 0-100)
        rsi_score = rsi
        
        # Normalizar MACD (convertir a score 0-100)
        macd_diff = macd - signal
        macd_score = 50 + (macd_diff * 10)  # Aproximación
        macd_score = max(0, min(100, macd_score))
        
        # Promedio ponderado
        return (rsi_score * 0.6) + (macd_score * 0.4)

# Instancia global
multi_tf_analyzer = MultiTimeframeAnalyzer()

def get_multi_tf_analyzer() -> MultiTimeframeAnalyzer:
    """Obtiene instancia del analizador multi-timeframe"""
    return multi_tf_analyzer

if __name__ == "__main__":
    # Test del analizador
    async def test_analyzer():
        analyzer = get_multi_tf_analyzer()
        
        print("🧪 Probando analizador multi-timeframe...")
        analysis = await analyzer.analyze_symbol_multitf('BTCUSDT')
        
        if analysis:
            print(f"📊 Análisis completado para BTCUSDT")
            print(f"Señal general: {analysis.get('overall_signal')}")
            print(f"Score: {analysis.get('confidence_score', 0):.1f}%")
            print(f"Nivel de riesgo: {analysis.get('risk_level')}")
            
            # Mostrar análisis por timeframe
            for tf_name, tf_data in analysis.get('timeframe_analysis', {}).items():
                if 'signals' in tf_data:
                    print(f"  {tf_name}: {tf_data['signals'].get('signal')} ({tf_data['signals'].get('confidence')}%)")
        else:
            print("❌ No se pudo completar el análisis")
    
    # Ejecutar test
    asyncio.run(test_analyzer())