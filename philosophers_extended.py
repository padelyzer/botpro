#!/usr/bin/env python3
"""
===========================================
FILÓSOFOS EXTENDIDOS - TRADING SYSTEM V3.0
===========================================

Extensión del sistema filosófico con 6 nuevos pensadores:

- PLATÓN: Busca patrones ideales perfectos, formas puras en el caos
- KANT: Imperativo categórico, reglas absolutas que siempre se cumplen
- DESCARTES: Duda metódica, confirma cada señal con múltiples validaciones
- SUN TZU: Arte de la guerra, estrategia y timing perfecto
- MAQUIAVELO: El fin justifica los medios, pragmático y oportunista
- HERÁCLITO: Todo fluye, adaptación constante al cambio
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from abc import ABC, abstractmethod

# Importar clases base del sistema principal
from philosophers import PhilosopherTrader, MarketPhilosophy, PhilosophicalSignal

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================
# PLATÓN: El Idealista (Pattern Perfection)
# ===========================================

class Platon(PhilosopherTrader):
    """
    Platón: "Las cosas visibles son sólo sombras de las formas ideales"
    
    Filosofía: Busca patrones perfectos, las formas ideales detrás del ruido.
    Solo opera cuando encuentra configuraciones que se acercan a la perfección.
    
    Estrategia: Pattern recognition con alta precisión
    """
    
    def __init__(self):
        super().__init__("Platon", MarketPhilosophy.PLATONIC)
        
        self.principles = [
            "Los patrones perfectos existen, solo hay que descubrirlos",
            "El mundo visible es imperfecto, pero refleja formas ideales",
            "La geometría del mercado revela verdades eternas",
            "Solo operar con configuraciones cercanas a la perfección"
        ]
        
        self.strengths = [
            "Alta precisión en entries",
            "Excelente ratio riesgo/beneficio",
            "Identifica patrones de alta probabilidad",
            "Disciplina extrema en selección"
        ]
        
        self.weaknesses = [
            "Pocas señales (espera perfección)",
            "Puede perder oportunidades buenas pero no perfectas",
            "Análisis complejo y lento"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis platónico - busca patrones ideales"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Detectar patrones geométricos perfectos
        pattern_score = 0
        patterns_found = []
        
        # 1. Triángulo áureo (Fibonacci)
        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        recent_high = df['high'].rolling(50).max().iloc[-1]
        recent_low = df['low'].rolling(50).min().iloc[-1]
        range_size = recent_high - recent_low
        
        for level in fib_levels:
            fib_price = recent_low + (range_size * level)
            if abs(current['close'] - fib_price) / fib_price < 0.01:  # 1% tolerancia
                pattern_score += 1
                patterns_found.append(f"Fibonacci {level}")
        
        # 2. Convergencia de medias móviles perfecta
        ema_9 = df['close'].ewm(span=9).mean().iloc[-1]
        ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
        ema_55 = df['close'].ewm(span=55).mean().iloc[-1]
        
        ema_alignment = abs(ema_9 - ema_21) / ema_21 < 0.002  # 0.2% proximidad
        if ema_alignment:
            pattern_score += 2
            patterns_found.append("EMA convergence perfecto")
        
        # 3. Patrón de velas ideal
        last_3_candles = df.tail(3)
        bullish_pattern = all(
            last_3_candles.iloc[i]['close'] > last_3_candles.iloc[i]['open']
            for i in range(3)
        )
        bearish_pattern = all(
            last_3_candles.iloc[i]['close'] < last_3_candles.iloc[i]['open']
            for i in range(3)
        )
        
        if bullish_pattern or bearish_pattern:
            pattern_score += 1
            patterns_found.append("Patrón de 3 velas perfecto")
        
        # 4. RSI en nivel clave
        rsi_key_levels = [30, 50, 70]
        for level in rsi_key_levels:
            if abs(current['RSI'] - level) < 2:
                pattern_score += 1
                patterns_found.append(f"RSI en nivel clave {level}")
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Necesita al menos 4 puntos de patrón para considerar "ideal"
        if pattern_score >= 4:
            # Determinar dirección basado en estructura
            if current['close'] > ema_21 and current['RSI'] > 50 and bullish_pattern:
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = recent_low
                analysis['take_profit'] = recent_high
                analysis['reasoning'] = [
                    "Patrón ideal alcista detectado",
                    f"Patrones encontrados: {', '.join(patterns_found)}",
                    "Geometría del mercado perfecta",
                    "La forma ideal se manifiesta"
                ]
                analysis['confidence'] = min(pattern_score / 6, 0.90)
                
            elif current['close'] < ema_21 and current['RSI'] < 50 and bearish_pattern:
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = recent_high
                analysis['take_profit'] = recent_low
                analysis['reasoning'] = [
                    "Patrón ideal bajista detectado",
                    f"Patrones encontrados: {', '.join(patterns_found)}",
                    "Simetría bearish perfecta",
                    "La sombra de la caída es clara"
                ]
                analysis['confidence'] = min(pattern_score / 6, 0.85)
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'pattern_score': pattern_score,
                'patterns_found': patterns_found,
                'geometric_perfection': pattern_score / 6
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "El patrón alcista ideal se ha manifestado, la forma perfecta de la subida es evidente"
        elif analysis['action'] == 'SELL':
            return "La geometría bajista perfecta se revela, el descenso sigue la forma ideal"
        return "No hay patrones suficientemente perfectos para operar"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "Incluso los patrones más perfectos pueden ser ilusiones en el mundo imperfecto del mercado"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Operaré siguiendo la forma ideal pero con stops que reconocen la imperfección del mundo material"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición platónica - proporcional a la perfección del patrón"""
        base_size = 0.015
        return base_size * confidence * 1.1  # Bonus por patrones ideales

# ===========================================
# KANT: El Categórico (Rule-Based Absolute)
# ===========================================

class Kant(PhilosopherTrader):
    """
    Kant: "Actúa solo según la máxima que puedas querer que se convierta en ley universal"
    
    Filosofía: Imperativo categórico aplicado al trading. Reglas absolutas,
    sin excepciones. Si una regla es buena, debe aplicarse SIEMPRE.
    
    Estrategia: Sistema de reglas estrictas sin excepciones
    """
    
    def __init__(self):
        super().__init__("Kant", MarketPhilosophy.KANTIAN)
        
        self.principles = [
            "Las reglas son absolutas, no hay excepciones",
            "Si algo es correcto, es correcto siempre",
            "El deber está por encima del deseo",
            "La disciplina es imperativo categórico"
        ]
        
        self.strengths = [
            "Disciplina perfecta",
            "Sistema 100% replicable",
            "Sin emociones ni dudas",
            "Consistencia absoluta"
        ]
        
        self.weaknesses = [
            "Inflexible ante cambios de mercado",
            "No se adapta a condiciones únicas",
            "Puede perder por rigidez"
        ]
        
        # Reglas categóricas inmutables
        self.categorical_rules = {
            'RSI_OVERSOLD': 30,
            'RSI_OVERBOUGHT': 70,
            'VOLUME_THRESHOLD': 1.5,
            'RISK_PER_TRADE': 0.01,
            'MIN_RR_RATIO': 2.0,
            'TREND_CONFIRMATION_PERIODS': 20
        }
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis kantiano - aplicación de reglas categóricas"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Verificar TODAS las reglas categóricas
        rules_passed = []
        rules_failed = []
        
        # Regla 1: RSI debe estar en extremo
        if current['RSI'] < self.categorical_rules['RSI_OVERSOLD']:
            rules_passed.append("RSI_OVERSOLD")
            signal_direction = 'BUY'
        elif current['RSI'] > self.categorical_rules['RSI_OVERBOUGHT']:
            rules_passed.append("RSI_OVERBOUGHT")
            signal_direction = 'SELL'
        else:
            rules_failed.append("RSI_NOT_EXTREME")
            signal_direction = None
        
        # Regla 2: Volumen debe superar threshold
        if current['Volume_Ratio'] > self.categorical_rules['VOLUME_THRESHOLD']:
            rules_passed.append("VOLUME_CONFIRMED")
        else:
            rules_failed.append("VOLUME_INSUFFICIENT")
        
        # Regla 3: Tendencia debe estar definida
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        trend_strength = abs(current['close'] - sma_20) / sma_20
        
        if trend_strength > 0.02:  # 2% desde la media
            rules_passed.append("TREND_DEFINED")
        else:
            rules_failed.append("TREND_UNCLEAR")
        
        # Regla 4: MACD debe confirmar
        if signal_direction == 'BUY' and current['MACD'] > current['MACD_Signal']:
            rules_passed.append("MACD_CONFIRMED")
        elif signal_direction == 'SELL' and current['MACD'] < current['MACD_Signal']:
            rules_passed.append("MACD_CONFIRMED")
        else:
            rules_failed.append("MACD_DIVERGENCE")
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # El imperativo categórico: TODAS las reglas deben cumplirse
        if len(rules_failed) == 0 and signal_direction:
            analysis['opportunity'] = True
            analysis['action'] = signal_direction
            analysis['entry_price'] = current['close']
            
            # Stop y target según reglas categóricas
            atr = current['ATR']
            if signal_direction == 'BUY':
                analysis['stop_loss'] = current['close'] - (atr * 2)
                analysis['take_profit'] = current['close'] + (atr * 4)  # RR 2:1
            else:
                analysis['stop_loss'] = current['close'] + (atr * 2)
                analysis['take_profit'] = current['close'] - (atr * 4)
            
            analysis['reasoning'] = [
                "Todas las reglas categóricas cumplidas",
                f"Reglas pasadas: {', '.join(rules_passed)}",
                "El imperativo de actuar es absoluto",
                "No hay excepciones cuando el deber llama"
            ]
            analysis['confidence'] = 0.80  # Alta confianza por cumplir todas las reglas
        
        else:
            analysis['reasoning'] = [
                "Reglas categóricas no cumplidas completamente",
                f"Fallos: {', '.join(rules_failed) if rules_failed else 'Dirección no clara'}"
            ]
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self.categorical_rules['RISK_PER_TRADE']
            
            analysis['metadata'] = {
                'rules_passed': rules_passed,
                'rules_failed': rules_failed,
                'categorical_imperative': len(rules_failed) == 0
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] in ['BUY', 'SELL']:
            return "El imperativo categórico dicta actuar, las reglas universales están alineadas"
        return "Las reglas absolutas no permiten actuar en estas condiciones"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "El mercado podría tener circunstancias excepcionales no contempladas en las reglas"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Seguiré el imperativo categórico sin excepción, pues la disciplina es ley universal"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición kantiana - siempre la misma según la regla"""
        return self.categorical_rules['RISK_PER_TRADE']  # Siempre 1%, sin excepciones

# ===========================================
# DESCARTES: El Metódico (Multi-Confirmation)
# ===========================================

class Descartes(PhilosopherTrader):
    """
    Descartes: "Cogito, ergo sum" - "Dudo, luego existo"
    
    Filosofía: Duda metódica. No acepta nada sin confirmación múltiple.
    Cada señal debe pasar por un proceso de validación exhaustivo.
    
    Estrategia: Multi-confirmación con validación exhaustiva
    """
    
    def __init__(self):
        super().__init__("Descartes", MarketPhilosophy.CARTESIAN)
        
        self.principles = [
            "Dudar de todo hasta tener certeza absoluta",
            "Dividir cada problema en partes manejables",
            "Proceder de lo simple a lo complejo",
            "Revisar exhaustivamente para no omitir nada"
        ]
        
        self.strengths = [
            "Muy pocas señales falsas",
            "Alta tasa de éxito",
            "Análisis profundo y completo",
            "Minimiza errores por impulso"
        ]
        
        self.weaknesses = [
            "Proceso lento de decisión",
            "Pierde entries rápidos",
            "Parálisis por análisis"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis cartesiano - duda metódica con confirmaciones múltiples"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Proceso de duda metódica - 4 niveles de confirmación
        confirmations = {
            'level_1_price': False,
            'level_2_momentum': False,
            'level_3_volume': False,
            'level_4_structure': False
        }
        
        signal_hypothesis = None
        
        # Nivel 1: Análisis de precio (lo más evidente)
        bb_position = (current['close'] - current['BB_Lower']) / (current['BB_Upper'] - current['BB_Lower'])
        if bb_position < 0.2:
            signal_hypothesis = 'BUY'
            confirmations['level_1_price'] = True
        elif bb_position > 0.8:
            signal_hypothesis = 'SELL'
            confirmations['level_1_price'] = True
        
        if signal_hypothesis:
            # Nivel 2: Confirmar con momentum
            if signal_hypothesis == 'BUY':
                if current['RSI'] < 40 and current['MACD'] < current['MACD_Signal']:
                    confirmations['level_2_momentum'] = True
            else:  # SELL
                if current['RSI'] > 60 and current['MACD'] > current['MACD_Signal']:
                    confirmations['level_2_momentum'] = True
            
            # Nivel 3: Validar con volumen
            if current['Volume_Ratio'] > 1.2:  # Volumen superior al promedio
                confirmations['level_3_volume'] = True
            
            # Nivel 4: Estructura de mercado
            ema_9 = df['close'].ewm(span=9).mean().iloc[-1]
            ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
            
            if signal_hypothesis == 'BUY':
                if current['close'] < ema_9 < ema_21:  # Pullback en tendencia
                    confirmations['level_4_structure'] = True
            else:  # SELL
                if current['close'] > ema_9 > ema_21:  # Rally en downtrend
                    confirmations['level_4_structure'] = True
        
        # Contar confirmaciones
        confirmation_count = sum(confirmations.values())
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Necesita al menos 3 de 4 confirmaciones para superar la duda
        if confirmation_count >= 3 and signal_hypothesis:
            analysis['opportunity'] = True
            analysis['action'] = signal_hypothesis
            analysis['entry_price'] = current['close']
            
            # Stops conservadores por la duda metódica
            atr = current['ATR']
            if signal_hypothesis == 'BUY':
                analysis['stop_loss'] = current['close'] - (atr * 1.5)
                analysis['take_profit'] = current['close'] + (atr * 3)
            else:
                analysis['stop_loss'] = current['close'] + (atr * 1.5)
                analysis['take_profit'] = current['close'] - (atr * 3)
            
            analysis['reasoning'] = [
                f"Duda metódica superada con {confirmation_count}/4 confirmaciones",
                f"Niveles confirmados: {[k for k, v in confirmations.items() if v]}",
                "La certeza es suficiente para actuar",
                "Pienso, luego opero"
            ]
            analysis['confidence'] = confirmation_count / 4
        
        else:
            analysis['reasoning'] = [
                "La duda persiste, no hay suficientes confirmaciones",
                f"Solo {confirmation_count}/4 niveles confirmados",
                "Mejor no actuar que actuar con dudas"
            ]
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'confirmations': confirmations,
                'confirmation_count': confirmation_count,
                'hypothesis': signal_hypothesis,
                'doubt_level': 1 - (confirmation_count / 4)
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] in ['BUY', 'SELL']:
            return f"Tras dudar metódicamente, la evidencia apunta a {analysis['action']}"
        return "La duda no ha sido resuelta, no hay base para actuar"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "Pero siempre existe la posibilidad de que mi análisis sea engañoso como un sueño"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Actuaré con la certeza disponible, pero con stops que reconocen la falibilidad del método"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición cartesiana - proporcional a la certeza"""
        base_size = 0.01
        return base_size * confidence * 0.9  # Reducido por prudencia metódica

# ===========================================
# SUN TZU: El Estratega (War Strategy)
# ===========================================

class SunTzu(PhilosopherTrader):
    """
    Sun Tzu: "La suprema excelencia es quebrar la resistencia del enemigo sin luchar"
    
    Filosofía: El trading es guerra. Conoce a tu enemigo (el mercado) y a ti mismo.
    Ataca cuando eres fuerte, retírate cuando eres débil. El timing lo es todo.
    
    Estrategia: Timing perfecto con gestión táctica
    """
    
    def __init__(self):
        super().__init__("SunTzu", MarketPhilosophy.SUNTZUAN)
        
        self.principles = [
            "Conoce al mercado y conócete a ti mismo",
            "Toda guerra se basa en el engaño",
            "Ataca donde no te esperan",
            "La mejor victoria es vencer sin combatir",
            "El timing decide la batalla"
        ]
        
        self.strengths = [
            "Timing excepcional",
            "Gestión de riesgo superior",
            "Adaptación táctica",
            "Aprovecha debilidades del mercado"
        ]
        
        self.weaknesses = [
            "Requiere paciencia extrema",
            "Puede perder movimientos mientras espera",
            "Complejidad en la ejecución"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis estratégico estilo Sun Tzu"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Evaluar el campo de batalla
        battlefield_assessment = self._assess_battlefield(df)
        
        # Identificar fortalezas y debilidades
        market_weakness = None
        our_strength = None
        
        # Buscar puntos débiles del enemigo (mercado)
        if current['RSI'] < 25:  # Mercado exhausto vendiendo
            market_weakness = 'SELLER_EXHAUSTION'
            our_strength = 'BUY_OPPORTUNITY'
        elif current['RSI'] > 75:  # Mercado exhausto comprando
            market_weakness = 'BUYER_EXHAUSTION'
            our_strength = 'SELL_OPPORTUNITY'
        
        # Evaluar el terreno (condiciones de mercado)
        terrain = self._evaluate_terrain(df, current)
        
        # Momento de ataque
        attack_timing = self._calculate_attack_timing(current, terrain)
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Decisión estratégica
        if market_weakness and attack_timing['favorable']:
            if our_strength == 'BUY_OPPORTUNITY':
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                
                # Estrategia de salida
                analysis['stop_loss'] = current['close'] * 0.97  # Retirada táctica
                analysis['take_profit'] = current['close'] * 1.04  # Victoria rápida
                
                analysis['reasoning'] = [
                    "El enemigo está exhausto, momento de atacar",
                    f"Debilidad detectada: {market_weakness}",
                    f"Terreno favorable: {terrain['type']}",
                    "Victoria sin lucha prolongada"
                ]
                
            elif our_strength == 'SELL_OPPORTUNITY':
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                
                analysis['stop_loss'] = current['close'] * 1.03
                analysis['take_profit'] = current['close'] * 0.96
                
                analysis['reasoning'] = [
                    "La fortaleza enemiga se convierte en debilidad",
                    f"Vulnerabilidad: {market_weakness}",
                    "Ataque cuando no lo esperan",
                    "Retirada planificada si es necesario"
                ]
            
            analysis['confidence'] = attack_timing['confidence']
        
        else:
            analysis['reasoning'] = [
                "No es momento de atacar",
                "Esperar mejor posición táctica",
                "La paciencia es una virtud estratégica"
            ]
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'battlefield': battlefield_assessment,
                'terrain': terrain,
                'market_weakness': market_weakness,
                'attack_timing': attack_timing
            }
        
        return analysis
    
    def _assess_battlefield(self, df: pd.DataFrame) -> Dict:
        """Evalúa el campo de batalla (mercado)"""
        volatility = df['close'].pct_change().std() * 100
        trend = 'UPTREND' if df['close'].iloc[-1] > df['close'].iloc[-20] else 'DOWNTREND'
        
        return {
            'volatility': volatility,
            'trend': trend,
            'battles_won': len(df[df['close'] > df['open']]),
            'battles_lost': len(df[df['close'] < df['open']])
        }
    
    def _evaluate_terrain(self, df: pd.DataFrame, current: pd.Series) -> Dict:
        """Evalúa el terreno de batalla"""
        if current['ATR'] > df['ATR'].mean() * 1.5:
            terrain_type = 'ROUGH'  # Terreno difícil
        elif current['Volume_Ratio'] < 0.5:
            terrain_type = 'DESERT'  # Poca actividad
        else:
            terrain_type = 'FAVORABLE'
        
        return {
            'type': terrain_type,
            'advantage': terrain_type == 'FAVORABLE'
        }
    
    def _calculate_attack_timing(self, current: pd.Series, terrain: Dict) -> Dict:
        """Calcula el momento óptimo de ataque"""
        timing_score = 0
        
        # Factores de timing
        if terrain['advantage']:
            timing_score += 2
        if current['Volume_Ratio'] > 1.5:
            timing_score += 1
        if 30 < current['RSI'] < 70:
            timing_score -= 1  # No es extremo
        
        return {
            'favorable': timing_score >= 2,
            'confidence': min(timing_score / 4, 0.85)
        }
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "El enemigo ha mostrado su debilidad, es momento de avanzar"
        elif analysis['action'] == 'SELL':
            return "La fortaleza aparente del enemigo es su mayor vulnerabilidad"
        return "El sabio general espera el momento perfecto para atacar"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "El enemigo podría estar fingiendo debilidad para tender una trampa"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Atacaré con decisión pero mantendré una línea de retirada clara"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición Sun Tzu - basada en ventaja táctica"""
        base_size = 0.012
        return base_size * confidence

# ===========================================
# MAQUIAVELO: El Pragmático (Opportunistic)
# ===========================================

class Maquiavelo(PhilosopherTrader):
    """
    Maquiavelo: "El fin justifica los medios"
    
    Filosofía: Pragmatismo puro. No hay bien o mal en el trading, solo ganancias y pérdidas.
    Usa cualquier estrategia que funcione, cambia de táctica sin dudarlo.
    
    Estrategia: Oportunista adaptativo
    """
    
    def __init__(self):
        super().__init__("Maquiavelo", MarketPhilosophy.PLATONIC)  # Reutilizamos enum
        
        self.principles = [
            "El fin justifica los medios",
            "Es mejor ser temido que amado por el mercado",
            "La fortuna favorece a los audaces",
            "Adaptarse o morir",
            "El poder (profit) es el único objetivo"
        ]
        
        self.strengths = [
            "Extremadamente adaptable",
            "Sin prejuicios sobre estrategias",
            "Aprovecha cualquier oportunidad",
            "Pragmático y efectivo"
        ]
        
        self.weaknesses = [
            "Puede ser inconsistente",
            "Riesgo de sobre-trading",
            "Sin lealtad a ningún método"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis maquiavélico - el fin justifica los medios"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Buscar CUALQUIER oportunidad de profit
        opportunities = []
        
        # Oportunidad 1: Momentum fuerte (seguir la masa cuando conviene)
        if abs(current['MACD']) > df['MACD'].std() * 2:
            if current['MACD'] > 0:
                opportunities.append(('MOMENTUM_BUY', 0.7))
            else:
                opportunities.append(('MOMENTUM_SELL', 0.7))
        
        # Oportunidad 2: Contrarian en extremos (traicionar a la masa)
        if current['RSI'] < 20:
            opportunities.append(('CONTRARIAN_BUY', 0.8))
        elif current['RSI'] > 80:
            opportunities.append(('CONTRARIAN_SELL', 0.8))
        
        # Oportunidad 3: Breakout (unirse al ganador)
        if current['close'] > current['BB_Upper']:
            opportunities.append(('BREAKOUT_BUY', 0.6))
        elif current['close'] < current['BB_Lower']:
            opportunities.append(('BREAKOUT_SELL', 0.6))
        
        # Oportunidad 4: Mean reversion (explotar la debilidad)
        bb_middle = current['BB_Middle']
        if abs(current['close'] - bb_middle) / bb_middle > 0.02:
            if current['close'] > bb_middle:
                opportunities.append(('MEAN_REVERT_SELL', 0.65))
            else:
                opportunities.append(('MEAN_REVERT_BUY', 0.65))
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Elegir la mejor oportunidad (la más profitable)
        if opportunities:
            best_opp = max(opportunities, key=lambda x: x[1])
            strategy, confidence = best_opp
            
            analysis['opportunity'] = True
            
            if 'BUY' in strategy:
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = current['close'] * 0.97
                analysis['take_profit'] = current['close'] * 1.03
            else:
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = current['close'] * 1.03
                analysis['take_profit'] = current['close'] * 0.97
            
            analysis['reasoning'] = [
                f"Estrategia elegida: {strategy}",
                "El fin (profit) justifica los medios",
                f"Oportunidades detectadas: {len(opportunities)}",
                "Sin lealtad a ningún método, solo a las ganancias"
            ]
            analysis['confidence'] = confidence
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'opportunities_found': opportunities,
                'strategy_used': strategy if opportunities else None,
                'pragmatism_level': 'MAXIMUM'
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] in ['BUY', 'SELL']:
            return f"La oportunidad de profit justifica cualquier estrategia"
        return "No hay oportunidad suficientemente lucrativa ahora"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "La inconsistencia metodológica podría llevar a pérdidas sistemáticas"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Usaré cualquier medio para obtener ganancias, pero con gestión de riesgo pragmática"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición maquiavélica - agresiva cuando hay oportunidad"""
        base_size = 0.015
        return base_size * confidence * 1.2  # Más agresivo

# ===========================================
# HERÁCLITO: El Adaptativo (Constant Change)
# ===========================================

class Heraclito(PhilosopherTrader):
    """
    Heráclito: "Nadie se baña dos veces en el mismo río"
    
    Filosofía: Todo fluye, nada permanece. El cambio es la única constante.
    El mercado nunca es el mismo, adaptación continua es esencial.
    
    Estrategia: Adaptación dinámica continua
    """
    
    def __init__(self):
        super().__init__("Heraclito", MarketPhilosophy.PLATONIC)  # Reutilizamos enum
        
        self.principles = [
            "Todo fluye, nada permanece",
            "El cambio es la única constante",
            "Los opuestos son complementarios",
            "El conflicto genera armonía",
            "No puedes pisar el mismo mercado dos veces"
        ]
        
        self.strengths = [
            "Máxima adaptabilidad",
            "Nunca obsoleto",
            "Abraza la volatilidad",
            "Evolución constante"
        ]
        
        self.weaknesses = [
            "Difícil de backtest",
            "Requiere monitoreo constante",
            "Puede ser errático"
        ]
        
        self.market_state = 'UNKNOWN'  # Estado cambiante
        self.adaptation_count = 0
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis heraclíteo - adaptación al flujo constante"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Detectar el estado actual del río (mercado)
        current_flow = self._detect_market_flow(df)
        
        # Si el estado cambió, adaptarse
        if current_flow != self.market_state:
            self.market_state = current_flow
            self.adaptation_count += 1
        
        # Estrategia según el flujo actual
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        if current_flow == 'RAPIDS':  # Mercado volátil
            # Estrategia de volatilidad
            if current['ATR'] > df['ATR'].mean() * 1.5:
                if current['RSI'] < 35:
                    analysis['opportunity'] = True
                    analysis['action'] = 'BUY'
                    analysis['entry_price'] = current['close']
                    analysis['stop_loss'] = current['close'] - current['ATR']
                    analysis['take_profit'] = current['close'] + (current['ATR'] * 2)
                    analysis['reasoning'] = [
                        "El río está turbulento, oportunidad en el caos",
                        "Adaptación a condiciones de alta volatilidad",
                        "El cambio rápido trae oportunidades"
                    ]
                elif current['RSI'] > 65:
                    analysis['opportunity'] = True
                    analysis['action'] = 'SELL'
                    analysis['entry_price'] = current['close']
                    analysis['stop_loss'] = current['close'] + current['ATR']
                    analysis['take_profit'] = current['close'] - (current['ATR'] * 2)
                    analysis['reasoning'] = [
                        "Los rápidos cambian de dirección",
                        "Fluir con el cambio violento"
                    ]
        
        elif current_flow == 'CALM':  # Mercado tranquilo
            # Estrategia de rango
            if current['close'] < current['BB_Lower']:
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = current['BB_Lower'] * 0.98
                analysis['take_profit'] = current['BB_Middle']
                analysis['reasoning'] = [
                    "Aguas tranquilas, retorno al centro",
                    "En la calma, los extremos vuelven"
                ]
            elif current['close'] > current['BB_Upper']:
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = current['BB_Upper'] * 1.02
                analysis['take_profit'] = current['BB_Middle']
                analysis['reasoning'] = [
                    "El río tranquilo busca su nivel",
                    "Todo fluye hacia el equilibrio"
                ]
        
        elif current_flow == 'WATERFALL':  # Tendencia fuerte
            # Seguir la corriente
            ema_9 = df['close'].ewm(span=9).mean().iloc[-1]
            ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
            
            if ema_9 > ema_21 and current['MACD'] > current['MACD_Signal']:
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = ema_21
                analysis['take_profit'] = current['close'] * 1.05
                analysis['reasoning'] = [
                    "La cascada fluye hacia arriba",
                    "Seguir el flujo imparable",
                    "No luchar contra la corriente"
                ]
            elif ema_9 < ema_21 and current['MACD'] < current['MACD_Signal']:
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = ema_21
                analysis['take_profit'] = current['close'] * 0.95
                analysis['reasoning'] = [
                    "La cascada cae inexorablemente",
                    "Fluir con la gravedad del mercado"
                ]
        
        if analysis['opportunity']:
            analysis['confidence'] = 0.70 + (self.adaptation_count * 0.02)  # Más confianza con más adaptaciones
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'market_flow': current_flow,
                'adaptations': self.adaptation_count,
                'flux_level': 'HIGH',
                'river_state': self.market_state
            }
        
        return analysis
    
    def _detect_market_flow(self, df: pd.DataFrame) -> str:
        """Detecta el flujo actual del mercado"""
        current = df.iloc[-1]
        
        # Volatilidad
        volatility = df['close'].pct_change().rolling(20).std().iloc[-1]
        
        # Tendencia
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1]
        
        if volatility > df['close'].pct_change().rolling(20).std().mean() * 1.5:
            return 'RAPIDS'
        elif abs(sma_20 - sma_50) / sma_50 > 0.03:
            return 'WATERFALL'
        else:
            return 'CALM'
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] in ['BUY', 'SELL']:
            return f"El río del mercado fluye hacia {analysis['action']}, me adapto a su corriente"
        return "El flujo no está claro, espero a que el río muestre su dirección"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "Pero el río puede cambiar su curso en cualquier momento"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Fluiré con el mercado presente, listo para adaptarme cuando cambie"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición heraclítea - fluida y adaptativa"""
        base_size = 0.012
        # Ajustar según el flujo del mercado
        if self.market_state == 'RAPIDS':
            return base_size * confidence * 0.8  # Más conservador en volatilidad
        elif self.market_state == 'WATERFALL':
            return base_size * confidence * 1.2  # Más agresivo en tendencia
        else:
            return base_size * confidence

# ===========================================
# REGISTRO DE FILÓSOFOS EXTENDIDOS
# ===========================================

def register_extended_philosophers():
    """Registra los filósofos extendidos en el sistema principal"""
    
    from philosophers import get_trading_system
    
    # Obtener instancia global del sistema
    system = get_trading_system()
    
    # Registrar nuevos filósofos
    extended = {
        'PLATON': Platon(),
        'KANT': Kant(),
        'DESCARTES': Descartes(),
        'SUNTZU': SunTzu(),
        'MAQUIAVELO': Maquiavelo(),
        'HERACLITO': Heraclito()
    }
    
    # Añadir al sistema global
    system.philosophers.update(extended)
    
    logger.info(f"✅ {len(extended)} filósofos extendidos registrados")
    
    return system

# ===========================================
# TESTING Y DEMOSTRACIÓN
# ===========================================

def test_extended_philosophers():
    """Prueba los filósofos extendidos"""
    
    print("\n" + "="*60)
    print("FILÓSOFOS EXTENDIDOS - SISTEMA V3.0")
    print("="*60)
    
    # Crear datos de prueba
    import yfinance as yf
    
    # Obtener datos reales
    ticker = yf.Ticker("BTC-USD")
    df = ticker.history(period="30d", interval="1h")
    
    if df.empty:
        print("❌ No se pudieron obtener datos de mercado")
        return
    
    # Probar cada filósofo
    philosophers = [
        Platon(),
        Kant(),
        Descartes(),
        SunTzu(),
        Maquiavelo(),
        Heraclito()
    ]
    
    print("\n📊 ANÁLISIS DE MERCADO POR FILÓSOFO:\n")
    
    for philosopher in philosophers:
        print(f"\n{'='*40}")
        print(f"🏛️ {philosopher.name.upper()}")
        print(f"{'='*40}")
        
        # Generar señal
        signal = philosopher.generate_signal(df, "BTC-USD")
        
        if signal:
            print(f"📍 Acción: {signal.action}")
            print(f"💰 Precio entrada: ${signal.entry_price:,.2f}")
            print(f"🛑 Stop Loss: ${signal.stop_loss:,.2f}")
            print(f"🎯 Take Profit: ${signal.take_profit:,.2f}")
            print(f"📊 Confianza: {signal.confidence:.1%}")
            print(f"⚖️ Risk/Reward: {signal.risk_reward:.2f}")
            print(f"\n💭 Tesis: {signal.thesis}")
            print(f"🔄 Antítesis: {signal.antithesis}")
            print(f"✨ Síntesis: {signal.synthesis}")
            print(f"\n📝 Razonamiento:")
            for reason in signal.reasoning:
                print(f"   • {reason}")
        else:
            print("🔸 No hay señal en este momento")
            print(f"   Principio: {philosopher.principles[0]}")
    
    print("\n" + "="*60)
    print("✅ Análisis filosófico completado")

def philosophical_extended_debate():
    """Debate entre los nuevos filósofos"""
    
    print("\n" + "="*60)
    print("DEBATE FILOSÓFICO EXTENDIDO")
    print("="*60)
    
    philosophers = {
        'PLATÓN': "Los patrones perfectos existen, solo hay que descubrirlos",
        'KANT': "Las reglas son absolutas, no hay excepciones",
        'DESCARTES': "Dudar de todo hasta tener certeza absoluta",
        'SUN TZU': "Conoce al mercado y conócete a ti mismo",
        'MAQUIAVELO': "El fin justifica los medios",
        'HERÁCLITO': "Todo fluye, nada permanece"
    }
    
    print("\n🎭 TEMA: '¿Existe la estrategia perfecta de trading?'\n")
    
    for name, philosophy in philosophers.items():
        print(f"\n🏛️ {name}:")
        print(f"   '{philosophy}'")
        
        if name == 'PLATÓN':
            print("   'Sí, existe la estrategia perfecta como forma ideal.'")
            print("   'Los traders solo ven sombras de ella en sus gráficos.'")
        elif name == 'KANT':
            print("   'La estrategia perfecta es aquella con reglas universales.'")
            print("   'Si funciona, debe funcionar siempre, sin excepción.'")
        elif name == 'DESCARTES':
            print("   'Dudo que exista hasta que se demuestre con certeza.'")
            print("   'Cada estrategia debe ser cuestionada metódicamente.'")
        elif name == 'SUN TZU':
            print("   'La estrategia perfecta es la ausencia de estrategia fija.'")
            print("   'Adaptarse al enemigo es la victoria suprema.'")
        elif name == 'MAQUIAVELO':
            print("   'La estrategia perfecta es la que genera profit.'")
            print("   'No importa el método, solo el resultado.'")
        elif name == 'HERÁCLITO':
            print("   'No existe estrategia perfecta permanente.'")
            print("   'El mercado de hoy no es el de ayer ni será el de mañana.'")
    
    print("\n" + "="*60)
    print("🎭 Fin del debate filosófico")

if __name__ == "__main__":
    # Ejecutar pruebas
    test_extended_philosophers()
    philosophical_extended_debate()