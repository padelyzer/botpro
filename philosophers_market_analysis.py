#!/usr/bin/env python3
"""
PHILOSOPHERS MARKET ANALYSIS - Sistema Profesional de Análisis de Mercado
Cada filósofo tiene una estrategia única basada en su filosofía
"""

import asyncio
import httpx
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PhilosopherAnalyst:
    """Analista de mercado basado en filosofías únicas"""
    
    def __init__(self, name: str, philosophy: str):
        self.name = name
        self.philosophy = philosophy
        self.binance_url = "https://api.binance.com/api/v3"
        
    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> List:
        """Obtener velas japonesas de Binance"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_url}/klines",
                    params={"symbol": symbol, "interval": interval, "limit": limit}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Error getting klines: {e}")
        return []
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcular RSI (Relative Strength Index)"""
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
        
        for delta in deltas[period:]:
            if delta > 0:
                up = (up * (period - 1) + delta) / period
                down = (down * (period - 1)) / period
            else:
                up = (up * (period - 1)) / period
                down = (down * (period - 1) - delta) / period
            
            if down == 0:
                return 100.0
            
            rs = up / down
            rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices: List[float]) -> Tuple[float, float]:
        """Calcular MACD"""
        if len(prices) < 26:
            return 0.0, 0.0
        
        # EMA 12
        ema12 = self.calculate_ema(prices, 12)
        # EMA 26
        ema26 = self.calculate_ema(prices, 26)
        # MACD Line
        macd_line = ema12 - ema26
        # Signal Line (EMA 9 of MACD)
        signal_line = macd_line * 0.2  # Simplificado
        
        return macd_line, signal_line
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcular EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> Tuple[float, float, float]:
        """Calcular Bandas de Bollinger"""
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]
        
        sma = sum(prices[-period:]) / period
        std = np.std(prices[-period:])
        
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        
        return upper, sma, lower
    
    def calculate_volume_trend(self, volumes: List[float]) -> float:
        """Analizar tendencia de volumen"""
        if len(volumes) < 10:
            return 0.0
        
        recent_avg = sum(volumes[-5:]) / 5
        older_avg = sum(volumes[-10:-5]) / 5
        
        if older_avg == 0:
            return 0.0
        
        return ((recent_avg - older_avg) / older_avg) * 100


class SocratesAnalyst(PhilosopherAnalyst):
    """Sócrates: 'Solo sé que no sé nada' - Estrategia de preguntas y confirmación"""
    
    def __init__(self):
        super().__init__("Socrates", "Cuestionar todo, confirmar con múltiples indicadores")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis socrático: Cuestionar tendencias con múltiples confirmaciones"""
        klines = await self.get_klines(symbol, "1h", 100)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        # Sócrates busca confirmación múltiple
        rsi = self.calculate_rsi(closes)
        macd, signal = self.calculate_macd(closes)
        upper, middle, lower = self.calculate_bollinger_bands(closes)
        volume_trend = self.calculate_volume_trend(volumes)
        
        # Filosofía: Solo actuar cuando todos los indicadores coinciden
        buy_signals = 0
        sell_signals = 0
        
        if rsi < 30: buy_signals += 2  # Sobreventa fuerte
        elif rsi < 40: buy_signals += 1
        elif rsi > 70: sell_signals += 2  # Sobrecompra fuerte
        elif rsi > 60: sell_signals += 1
        
        if macd > signal: buy_signals += 1
        else: sell_signals += 1
        
        if current_price < lower: buy_signals += 2
        elif current_price > upper: sell_signals += 2
        
        if volume_trend > 20: buy_signals += 1
        elif volume_trend < -20: sell_signals += 1
        
        # Decisión socrática
        confidence = max(buy_signals, sell_signals) * 10 + 40
        
        if buy_signals > sell_signals + 2:
            action = "BUY"
            reasoning = f"RSI={rsi:.1f} indica sobreventa, precio cerca de banda inferior"
        elif sell_signals > buy_signals + 2:
            action = "SELL"
            reasoning = f"RSI={rsi:.1f} indica sobrecompra, precio cerca de banda superior"
        else:
            action = "HOLD"
            reasoning = "Indicadores no muestran consenso claro"
            confidence = 50
        
        return {
            "action": action,
            "confidence": min(confidence, 95),
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"Confirmaciones: Buy={buy_signals}, Sell={sell_signals}",
                f"Volume trend: {volume_trend:.1f}%"
            ],
            "indicators": {
                "rsi": rsi,
                "macd": macd,
                "bollinger_position": "lower" if current_price < lower else "upper" if current_price > upper else "middle"
            }
        }


class AristotelesAnalyst(PhilosopherAnalyst):
    """Aristóteles: 'La virtud está en el término medio' - Estrategia de equilibrio"""
    
    def __init__(self):
        super().__init__("Aristoteles", "Buscar el equilibrio y la media dorada")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis aristotélico: Buscar puntos de equilibrio"""
        klines = await self.get_klines(symbol, "4h", 50)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        
        # Aristóteles busca el término medio
        ema20 = self.calculate_ema(closes, 20)
        ema50 = self.calculate_ema(closes, 50) if len(closes) >= 50 else ema20
        
        # Distancia desde el equilibrio
        distance_from_mean = ((current_price - ema20) / ema20) * 100
        
        # Golden ratio application
        golden_ratio = 1.618
        support = ema20 / golden_ratio
        resistance = ema20 * golden_ratio
        
        confidence = 70
        
        if current_price < support:
            action = "BUY"
            reasoning = f"Precio {abs(distance_from_mean):.1f}% bajo el equilibrio"
            confidence = min(80 + abs(distance_from_mean), 95)
        elif current_price > resistance:
            action = "SELL"
            reasoning = f"Precio {distance_from_mean:.1f}% sobre el equilibrio"
            confidence = min(80 + distance_from_mean, 95)
        else:
            action = "HOLD"
            reasoning = "Precio en zona de equilibrio"
            confidence = 60
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"EMA20: ${ema20:.2f}, Distancia: {distance_from_mean:.1f}%",
                f"Zona dorada: ${support:.2f} - ${resistance:.2f}"
            ],
            "indicators": {
                "ema20": ema20,
                "distance_from_mean": distance_from_mean,
                "golden_zone": {"support": support, "resistance": resistance}
            }
        }


class NietzscheAnalyst(PhilosopherAnalyst):
    """Nietzsche: 'Lo que no te mata te hace más fuerte' - Estrategia contrarian agresiva"""
    
    def __init__(self):
        super().__init__("Nietzsche", "Voluntad de poder, estrategia contrarian")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis nietzscheano: Contrarian extremo"""
        klines = await self.get_klines(symbol, "15m", 100)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        
        # Nietzsche busca los extremos para actuar en contra
        rsi = self.calculate_rsi(closes, 7)  # RSI más agresivo
        
        # Calcular momentum
        momentum = ((closes[-1] - closes[-10]) / closes[-10]) * 100 if len(closes) > 10 else 0
        
        # Volatilidad
        volatility = np.std(closes[-20:]) / np.mean(closes[-20:]) * 100 if len(closes) >= 20 else 5
        
        confidence = 60
        
        # Estrategia ultra-contrarian
        if rsi < 20:  # Extremo oversold
            action = "BUY"
            reasoning = "Pánico extremo = oportunidad de poder"
            confidence = 90
        elif rsi > 80:  # Extremo overbought
            action = "SELL"
            reasoning = "Euforia extrema = momento de destruir"
            confidence = 90
        elif volatility > 10 and momentum < -5:
            action = "BUY"
            reasoning = "El caos es una escalera"
            confidence = 75
        elif volatility > 10 and momentum > 5:
            action = "SELL"
            reasoning = "La soberbia precede a la caída"
            confidence = 75
        else:
            action = "HOLD"
            reasoning = "Esperando el momento de poder supremo"
            confidence = 55
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"RSI extremo: {rsi:.1f}, Momentum: {momentum:.1f}%",
                f"Volatilidad: {volatility:.1f}% - {'Alta' if volatility > 10 else 'Normal'}"
            ],
            "indicators": {
                "rsi": rsi,
                "momentum": momentum,
                "volatility": volatility
            }
        }


class ConfucioAnalyst(PhilosopherAnalyst):
    """Confucio: 'El hombre superior es modesto en su discurso pero excede en sus acciones' - Estrategia paciente"""
    
    def __init__(self):
        super().__init__("Confucio", "Paciencia y armonía con la tendencia")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis confuciano: Paciencia y seguimiento de tendencia"""
        klines = await self.get_klines(symbol, "1d", 30)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        
        # Confucio sigue la tendencia con paciencia
        ema10 = self.calculate_ema(closes, 10)
        ema30 = self.calculate_ema(closes, 30) if len(closes) >= 30 else ema10
        
        # Tendencia a largo plazo
        trend_strength = ((ema10 - ema30) / ema30) * 100 if ema30 > 0 else 0
        
        # Análisis de estructura
        higher_highs = sum(1 for i in range(1, min(5, len(closes))) if closes[-i] > closes[-i-1])
        
        confidence = 65
        
        if trend_strength > 2 and higher_highs >= 3:
            action = "BUY"
            reasoning = "La tendencia es tu amiga, síguela con paciencia"
            confidence = 80
        elif trend_strength < -2 and higher_highs <= 1:
            action = "SELL"
            reasoning = "La tendencia bajista requiere protección"
            confidence = 80
        else:
            action = "HOLD"
            reasoning = "La paciencia es la mayor virtud del trader"
            confidence = 70
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"Fuerza de tendencia: {trend_strength:.1f}%",
                f"Estructura: {higher_highs}/4 máximos crecientes"
            ],
            "indicators": {
                "trend_strength": trend_strength,
                "ema10": ema10,
                "ema30": ema30
            }
        }


class PlatonAnalyst(PhilosopherAnalyst):
    """Platón: 'La realidad es solo una sombra' - Estrategia de patrones ideales"""
    
    def __init__(self):
        super().__init__("Platon", "Buscar patrones ideales y formas perfectas")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis platónico: Buscar patrones ideales"""
        klines = await self.get_klines(symbol, "2h", 60)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # Platón busca patrones geométricos perfectos
        # Detectar triángulos, banderas, etc.
        
        # Soporte y resistencia
        recent_high = max(highs[-20:]) if len(highs) >= 20 else current_price
        recent_low = min(lows[-20:]) if len(lows) >= 20 else current_price
        
        # Fibonacci levels
        fib_0382 = recent_low + (recent_high - recent_low) * 0.382
        fib_0618 = recent_low + (recent_high - recent_low) * 0.618
        
        # Distancia a niveles ideales
        distance_to_support = ((current_price - recent_low) / recent_low) * 100
        distance_to_resistance = ((recent_high - current_price) / current_price) * 100
        
        confidence = 70
        
        if current_price <= fib_0382:
            action = "BUY"
            reasoning = "Precio en nivel Fibonacci ideal de compra"
            confidence = 85
        elif current_price >= fib_0618:
            action = "SELL"
            reasoning = "Precio en nivel Fibonacci ideal de venta"
            confidence = 85
        elif distance_to_support < 5:
            action = "BUY"
            reasoning = "Cerca del soporte ideal"
            confidence = 75
        elif distance_to_resistance < 5:
            action = "SELL"
            reasoning = "Cerca de la resistencia ideal"
            confidence = 75
        else:
            action = "HOLD"
            reasoning = "Sin patrones ideales claros"
            confidence = 60
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"Fibonacci 38.2%: ${fib_0382:.2f}, 61.8%: ${fib_0618:.2f}",
                f"Rango: ${recent_low:.2f} - ${recent_high:.2f}"
            ],
            "indicators": {
                "fibonacci_levels": {"0.382": fib_0382, "0.618": fib_0618},
                "support": recent_low,
                "resistance": recent_high
            }
        }


class KantAnalyst(PhilosopherAnalyst):
    """Kant: 'Actúa solo según aquella máxima que puedas querer que se convierta en ley universal' - Estrategia sistemática"""
    
    def __init__(self):
        super().__init__("Kant", "Reglas universales y sistemas categóricos")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis kantiano: Sistema de reglas categóricas"""
        klines = await self.get_klines(symbol, "1h", 72)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        # Kant sigue reglas estrictas y universales
        rsi = self.calculate_rsi(closes)
        macd, signal = self.calculate_macd(closes)
        volume_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1] if volumes else 0
        
        # Sistema de reglas categóricas
        rules_met = []
        buy_rules = 0
        sell_rules = 0
        
        # Regla 1: RSI
        if rsi < 35:
            buy_rules += 1
            rules_met.append("RSI oversold")
        elif rsi > 65:
            sell_rules += 1
            rules_met.append("RSI overbought")
        
        # Regla 2: MACD
        if macd > signal and macd > 0:
            buy_rules += 1
            rules_met.append("MACD bullish")
        elif macd < signal and macd < 0:
            sell_rules += 1
            rules_met.append("MACD bearish")
        
        # Regla 3: Volumen
        if current_volume > volume_avg * 1.5:
            if closes[-1] > closes[-2]:
                buy_rules += 1
                rules_met.append("Volume surge bullish")
            else:
                sell_rules += 1
                rules_met.append("Volume surge bearish")
        
        # Imperativo categórico: Actuar solo si hay mayoría absoluta
        confidence = 60
        
        if buy_rules >= 2:
            action = "BUY"
            reasoning = "Imperativo categórico de compra"
            confidence = 60 + (buy_rules * 15)
        elif sell_rules >= 2:
            action = "SELL"
            reasoning = "Imperativo categórico de venta"
            confidence = 60 + (sell_rules * 15)
        else:
            action = "HOLD"
            reasoning = "Sin imperativo categórico claro"
            confidence = 65
        
        return {
            "action": action,
            "confidence": min(confidence, 90),
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"Reglas cumplidas: {', '.join(rules_met) if rules_met else 'Ninguna'}",
                f"Sistema: Buy={buy_rules}/3, Sell={sell_rules}/3"
            ],
            "indicators": {
                "rsi": rsi,
                "macd": macd,
                "rules_score": {"buy": buy_rules, "sell": sell_rules}
            }
        }


class DescartesAnalyst(PhilosopherAnalyst):
    """Descartes: 'Pienso, luego existo' - Estrategia racional y metódica"""
    
    def __init__(self):
        super().__init__("Descartes", "Duda metódica y análisis racional")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis cartesiano: Duda metódica y confirmación racional"""
        klines = await self.get_klines(symbol, "30m", 96)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        
        # Descartes duda de todo y busca certeza matemática
        ema12 = self.calculate_ema(closes, 12)
        ema26 = self.calculate_ema(closes, 26)
        
        # Análisis de pendiente (derivada)
        price_changes = [closes[i] - closes[i-1] for i in range(1, min(10, len(closes)))]
        avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # Aceleración (segunda derivada)
        acceleration = price_changes[-1] - price_changes[0] if len(price_changes) > 1 else 0
        
        # Análisis estadístico
        std_dev = np.std(closes[-20:]) if len(closes) >= 20 else 1
        z_score = (current_price - ema26) / std_dev if std_dev > 0 else 0
        
        confidence = 65
        
        if z_score < -2 and acceleration > 0:
            action = "BUY"
            reasoning = "Reversión estadística confirmada matemáticamente"
            confidence = 85
        elif z_score > 2 and acceleration < 0:
            action = "SELL"
            reasoning = "Extremo estadístico con momentum negativo"
            confidence = 85
        elif ema12 > ema26 and avg_change > 0:
            action = "BUY"
            reasoning = "Tendencia alcista confirmada racionalmente"
            confidence = 75
        elif ema12 < ema26 and avg_change < 0:
            action = "SELL"
            reasoning = "Tendencia bajista confirmada racionalmente"
            confidence = 75
        else:
            action = "HOLD"
            reasoning = "Duda metódica: evidencia insuficiente"
            confidence = 60
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"Z-Score: {z_score:.2f}, Aceleración: {acceleration:.4f}",
                f"Pendiente promedio: {avg_change:.4f}"
            ],
            "indicators": {
                "z_score": z_score,
                "acceleration": acceleration,
                "trend_slope": avg_change
            }
        }


class SunTzuAnalyst(PhilosopherAnalyst):
    """Sun Tzu: 'Toda guerra se basa en el engaño' - Estrategia táctica y timing"""
    
    def __init__(self):
        super().__init__("Sun Tzu", "Arte de la guerra aplicado al trading")
    
    async def analyze(self, symbol: str, current_price: float) -> Dict:
        """Análisis Sun Tzu: Estrategia y táctica"""
        klines = await self.get_klines(symbol, "5m", 100)
        if not klines:
            return None
        
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # Sun Tzu analiza el campo de batalla
        rsi = self.calculate_rsi(closes, 9)  # RSI táctico rápido
        
        # Detectar trampas del mercado
        bull_trap = highs[-1] > max(highs[-10:-1]) and closes[-1] < highs[-1] * 0.995
        bear_trap = lows[-1] < min(lows[-10:-1]) and closes[-1] > lows[-1] * 1.005
        
        # Análisis de volumen (detectar movimientos institucionales)
        volume_spike = volumes[-1] > sum(volumes[-10:]) / 10 * 2
        
        # Momentum táctico
        tactical_momentum = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if len(closes) > 5 else 0
        
        confidence = 65
        
        if bear_trap and volume_spike:
            action = "BUY"
            reasoning = "Trampa bajista detectada - momento de atacar"
            confidence = 88
        elif bull_trap and volume_spike:
            action = "SELL"
            reasoning = "Trampa alcista detectada - retirada táctica"
            confidence = 88
        elif rsi < 25 and tactical_momentum < -2:
            action = "BUY"
            reasoning = "El enemigo está exhausto - contraataque"
            confidence = 80
        elif rsi > 75 and tactical_momentum > 2:
            action = "SELL"
            reasoning = "El enemigo sobreextendido - emboscada"
            confidence = 80
        else:
            action = "HOLD"
            reasoning = "Observar y esperar el momento óptimo"
            confidence = 70
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": [
                f"{self.name}: {reasoning}",
                f"RSI táctico: {rsi:.1f}, Momentum: {tactical_momentum:.1f}%",
                f"{'⚠️ Trampa detectada!' if bull_trap or bear_trap else 'Campo despejado'}"
            ],
            "indicators": {
                "rsi": rsi,
                "tactical_momentum": tactical_momentum,
                "traps": {"bull": bull_trap, "bear": bear_trap}
            }
        }


class PhilosophersCouncil:
    """Consejo de filósofos para generar señales de consenso"""
    
    def __init__(self):
        self.philosophers = [
            SocratesAnalyst(),
            AristotelesAnalyst(),
            NietzscheAnalyst(),
            ConfucioAnalyst(),
            PlatonAnalyst(),
            KantAnalyst(),
            DescartesAnalyst(),
            SunTzuAnalyst()
        ]
    
    async def get_consensus(self, symbol: str, current_price: float) -> Dict:
        """Obtener consenso de todos los filósofos"""
        analyses = []
        
        # Obtener análisis de cada filósofo
        for philosopher in self.philosophers:
            try:
                analysis = await philosopher.analyze(symbol, current_price)
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error in {philosopher.name} analysis: {e}")
        
        if not analyses:
            return None
        
        # Calcular consenso
        buy_votes = sum(1 for a in analyses if a["action"] == "BUY")
        sell_votes = sum(1 for a in analyses if a["action"] == "SELL")
        hold_votes = sum(1 for a in analyses if a["action"] == "HOLD")
        
        # Confidence promedio ponderado
        total_confidence = sum(a["confidence"] for a in analyses)
        avg_confidence = total_confidence / len(analyses)
        
        # Determinar acción de consenso
        if buy_votes > sell_votes and buy_votes > hold_votes:
            consensus_action = "BUY"
            agreement = buy_votes
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            consensus_action = "SELL"
            agreement = sell_votes
        else:
            consensus_action = "HOLD"
            agreement = hold_votes
        
        return {
            "action": consensus_action,
            "confidence": avg_confidence,
            "philosophers_agree": agreement,
            "total_philosophers": len(analyses),
            "votes": {
                "BUY": buy_votes,
                "SELL": sell_votes,
                "HOLD": hold_votes
            },
            "individual_analyses": analyses
        }