#!/usr/bin/env python3
"""
MÓDULO DE ANÁLISIS FILOSÓFICO
Integración de filósofos en el sistema centralizado
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

class PhilosopherCouncil:
    """Consejo de filósofos para análisis de trading"""
    
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.philosophers = self._initialize_philosophers()
        
    def _initialize_philosophers(self) -> Dict:
        """Inicializar el consejo de filósofos"""
        return {
            'buffett': {
                'name': 'Warren Buffett',
                'style': 'Value Investor',
                'risk_tolerance': 0.2,
                'preferred_conditions': ['oversold', 'fear', 'value'],
                'avoid_conditions': ['overbought', 'greed', 'fomo']
            },
            'soros': {
                'name': 'George Soros',
                'style': 'Macro Reflexivity',
                'risk_tolerance': 0.8,
                'preferred_conditions': ['extremes', 'reversals', 'volatility'],
                'avoid_conditions': ['ranging', 'low_volume']
            },
            'livermore': {
                'name': 'Jesse Livermore',
                'style': 'Trend Following',
                'risk_tolerance': 0.6,
                'preferred_conditions': ['breakouts', 'momentum', 'volume'],
                'avoid_conditions': ['consolidation', 'unclear_trend']
            },
            'jones': {
                'name': 'Paul Tudor Jones',
                'style': 'Risk Management',
                'risk_tolerance': 0.4,
                'preferred_conditions': ['good_rr', 'clear_setup', 'hedge'],
                'avoid_conditions': ['bad_rr', 'unclear_stop']
            },
            'dalio': {
                'name': 'Ray Dalio',
                'style': 'Systematic',
                'risk_tolerance': 0.3,
                'preferred_conditions': ['system_signal', 'correlation', 'diversified'],
                'avoid_conditions': ['no_signal', 'concentrated_risk']
            },
            'graham': {
                'name': 'Benjamin Graham',
                'style': 'Fundamental Value',
                'risk_tolerance': 0.1,
                'preferred_conditions': ['deep_value', 'margin_safety', 'fundamentals'],
                'avoid_conditions': ['speculation', 'no_fundamentals', 'overvalued']
            }
        }
    
    async def get_market_data(self, symbol: str) -> Dict:
        """Obtener datos de mercado"""
        async with httpx.AsyncClient() as client:
            try:
                # Precio actual
                price_resp = await client.get(
                    f"{self.binance_url}/ticker/price",
                    params={"symbol": f"{symbol}USDT"}
                )
                
                # Stats 24h
                stats_resp = await client.get(
                    f"{self.binance_url}/ticker/24hr",
                    params={"symbol": f"{symbol}USDT"}
                )
                
                # Klines para análisis técnico
                klines_resp = await client.get(
                    f"{self.binance_url}/klines",
                    params={"symbol": f"{symbol}USDT", "interval": "1h", "limit": 50}
                )
                
                if all(r.status_code == 200 for r in [price_resp, stats_resp, klines_resp]):
                    price_data = price_resp.json()
                    stats_data = stats_resp.json()
                    klines_data = klines_resp.json()
                    
                    # Calcular RSI
                    closes = [float(k[4]) for k in klines_data]
                    rsi = self.calculate_rsi(closes)
                    
                    return {
                        'symbol': symbol,
                        'current_price': float(price_data['price']),
                        'high_24h': float(stats_data['highPrice']),
                        'low_24h': float(stats_data['lowPrice']),
                        'change_24h': float(stats_data['priceChangePercent']),
                        'volume': float(stats_data['volume']),
                        'rsi': rsi,
                        'closes': closes[-20:]  # Últimas 20 velas
                    }
            except Exception as e:
                print(f"Error obteniendo datos: {e}")
                return {}
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcular RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            return 100.0
        
        rs = up / down
        return 100 - (100 / (1 + rs))
    
    def analyze_market_conditions(self, market_data: Dict) -> Dict:
        """Analizar condiciones del mercado"""
        conditions = {
            'oversold': market_data.get('rsi', 50) < 30,
            'overbought': market_data.get('rsi', 50) > 70,
            'fear': market_data.get('change_24h', 0) < -5,
            'greed': market_data.get('change_24h', 0) > 5,
            'extremes': abs(market_data.get('change_24h', 0)) > 7,
            'volatility': abs(market_data.get('change_24h', 0)) > 5,
            'momentum': market_data.get('change_24h', 0) > 3,
            'breakout': False,  # Simplificado
            'good_rr': True,  # Simplificado
            'system_signal': market_data.get('rsi', 50) < 40,
            'deep_value': market_data.get('change_24h', 0) < -10,
            'ranging': abs(market_data.get('change_24h', 0)) < 2
        }
        return conditions
    
    def get_philosopher_opinion(self, philosopher: Dict, market_data: Dict, conditions: Dict, signal: Dict = None) -> Dict:
        """Obtener opinión de un filósofo específico"""
        score = 50  # Base neutral
        reasoning = []
        
        # Evaluar condiciones preferidas
        for condition in philosopher['preferred_conditions']:
            if conditions.get(condition, False):
                score += 15
                reasoning.append(f"✅ {condition.replace('_', ' ').title()}")
        
        # Evaluar condiciones a evitar
        for condition in philosopher['avoid_conditions']:
            if conditions.get(condition, False):
                score -= 20
                reasoning.append(f"❌ {condition.replace('_', ' ').title()}")
        
        # Análisis específico por filósofo
        if philosopher['name'] == 'Warren Buffett':
            if market_data.get('current_price', 0) > 190:
                score -= 30
                reasoning.append("❌ Precio muy alto, sin margen de seguridad")
            else:
                score += 20
                reasoning.append("✅ Precio razonable para acumular")
        
        elif philosopher['name'] == 'George Soros':
            if conditions.get('extremes'):
                score += 25
                reasoning.append("✅ Oportunidad en extremos del mercado")
        
        elif philosopher['name'] == 'Jesse Livermore':
            if market_data.get('change_24h', 0) > 0 and market_data.get('rsi', 50) > 60:
                score += 20
                reasoning.append("✅ Momentum alcista confirmado")
        
        # Determinar acción
        if score >= 70:
            action = "BUY"
            confidence = "HIGH"
        elif score >= 50:
            action = "WAIT"
            confidence = "MEDIUM"
        else:
            action = "AVOID"
            confidence = "LOW"
        
        # Recomendación específica
        if signal:
            if signal.get('action') == 'LONG' and score < 50:
                recommendation = "❌ NO TOMAR - Condiciones desfavorables"
            elif signal.get('action') == 'LONG' and score >= 70:
                recommendation = "✅ PROCEDER - Condiciones favorables"
            else:
                recommendation = "⚠️ ESPERAR - Necesita mejor setup"
        else:
            recommendation = f"{action} - {confidence} confidence"
        
        return {
            'philosopher': philosopher['name'],
            'style': philosopher['style'],
            'score': score,
            'action': action,
            'confidence': confidence,
            'reasoning': reasoning,
            'recommendation': recommendation
        }
    
    async def analyze_signal(self, symbol: str, signal: Dict = None) -> Dict:
        """Análisis completo del consejo filosófico"""
        # Obtener datos de mercado
        market_data = await self.get_market_data(symbol)
        if not market_data:
            return {'error': 'No se pudieron obtener datos de mercado'}
        
        # Analizar condiciones
        conditions = self.analyze_market_conditions(market_data)
        
        # Obtener opinión de cada filósofo
        opinions = {}
        for key, philosopher in self.philosophers.items():
            opinions[key] = self.get_philosopher_opinion(philosopher, market_data, conditions, signal)
        
        # Calcular consenso
        scores = [op['score'] for op in opinions.values()]
        avg_score = sum(scores) / len(scores)
        
        actions = [op['action'] for op in opinions.values()]
        consensus_action = max(set(actions), key=actions.count)
        
        # Generar análisis consolidado
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'market_data': {
                'price': market_data['current_price'],
                'change_24h': market_data['change_24h'],
                'rsi': market_data['rsi']
            },
            'philosophers': opinions,
            'consensus': {
                'average_score': round(avg_score, 1),
                'action': consensus_action,
                'confidence': 'HIGH' if avg_score > 70 else 'MEDIUM' if avg_score > 50 else 'LOW',
                'agreement': len(set(actions)) == 1
            },
            'key_insights': self._generate_insights(opinions, market_data),
            'recommended_action': self._generate_recommendation(avg_score, consensus_action, market_data)
        }
    
    def _generate_insights(self, opinions: Dict, market_data: Dict) -> List[str]:
        """Generar insights clave del análisis"""
        insights = []
        
        # Consenso fuerte
        scores = [op['score'] for op in opinions.values()]
        if all(s > 70 for s in scores):
            insights.append("💎 Consenso unánime BULLISH")
        elif all(s < 30 for s in scores):
            insights.append("🚨 Consenso unánime BEARISH")
        
        # Divergencias importantes
        if max(scores) - min(scores) > 50:
            insights.append("⚡ Alta divergencia entre filósofos")
        
        # Condiciones de mercado
        if market_data.get('rsi', 50) < 30:
            insights.append("📉 RSI oversold - Potencial rebote")
        elif market_data.get('rsi', 50) > 70:
            insights.append("📈 RSI overbought - Cuidado con corrección")
        
        if abs(market_data.get('change_24h', 0)) > 10:
            insights.append("🎢 Volatilidad extrema - Gestionar riesgo")
        
        return insights
    
    def _generate_recommendation(self, avg_score: float, consensus: str, market_data: Dict) -> Dict:
        """Generar recomendación accionable"""
        if avg_score >= 70 and consensus == 'BUY':
            return {
                'action': 'OPEN_LONG',
                'confidence': 'HIGH',
                'entry': market_data['current_price'],
                'stop_loss': market_data['current_price'] * 0.97,
                'take_profit': market_data['current_price'] * 1.03,
                'size': '5-10% portfolio',
                'notes': 'Condiciones favorables según el consejo'
            }
        elif avg_score <= 30:
            return {
                'action': 'AVOID_OR_SHORT',
                'confidence': 'HIGH',
                'notes': 'Condiciones muy desfavorables'
            }
        else:
            return {
                'action': 'WAIT',
                'confidence': 'MEDIUM',
                'notes': 'Esperar mejor setup o confirmación'
            }

# Instancia singleton
philosopher_council = PhilosopherCouncil()

async def monitor_step():
    """Función para compatibilidad con el sistema de monitores"""
    return await philosopher_council.analyze_signal('SOL')

async def monitor_continuous():
    """Monitor continuo para el sistema"""
    while True:
        try:
            analysis = await philosopher_council.analyze_signal('SOL')
            print(f"\n🎭 Análisis Filosófico: Score {analysis['consensus']['average_score']}")
            await asyncio.sleep(60)  # Cada minuto
        except Exception as e:
            print(f"Error en monitor filosófico: {e}")
            await asyncio.sleep(30)