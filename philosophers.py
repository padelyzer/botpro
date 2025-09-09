#!/usr/bin/env python3
"""
===========================================
SISTEMA DE TRADING FILOSÓFICO V2.0
===========================================

Cada algoritmo representa la filosofía de un pensador aplicada al trading:

- SÓCRATES: Cuestiona el mercado, busca la verdad en los rangos
- ARISTÓTELES: Lógica pura, sigue la tendencia con razón
- NIETZSCHE: Contrarian, va contra la masa, abraza el caos
- CONFUCIO: Busca el equilibrio, la armonía del mean reversion
- PLATÓN: Idealista, busca patrones perfectos
- KANT: Imperativo categórico, reglas estrictas
- DESCARTES: Duda metódica, confirmaciones múltiples
- SUN TZU: Estrategia de guerra, timing perfecto
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

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================
# ESTRUCTURAS DE DATOS
# ===========================================

class MarketPhilosophy(Enum):
    """Filosofías de mercado"""
    SOCRATIC = "SOCRATES"  # Cuestionamiento constante
    ARISTOTELIAN = "ARISTOTELES"  # Lógica y razón
    NIETZSCHEAN = "NIETZSCHE"  # Contrarian
    CONFUCIAN = "CONFUCIO"  # Equilibrio y armonía
    PLATONIC = "PLATON"  # Patrones ideales
    KANTIAN = "KANT"  # Reglas absolutas
    CARTESIAN = "DESCARTES"  # Duda metódica
    SUNTZUAN = "SUNTZU"  # Arte de la guerra

@dataclass
class PhilosophicalSignal:
    """Señal generada por un filósofo"""
    timestamp: datetime
    philosopher: str
    philosophy: MarketPhilosophy
    symbol: str
    action: str  # BUY, SELL, HOLD
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    reasoning: List[str]  # Razonamiento filosófico
    thesis: str  # Tesis principal
    antithesis: str  # Consideración contraria
    synthesis: str  # Conclusión
    position_size: float
    risk_reward: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TradingProject:
    """Proyecto de trading con múltiples filósofos"""
    id: str
    name: str
    created_at: datetime
    philosophers: List[str]
    capital: float
    risk_per_trade: float
    symbols: List[str]
    timeframe: str
    status: str  # ACTIVE, PAUSED, COMPLETED
    performance: Dict[str, Any] = field(default_factory=dict)
    active_signals: List[PhilosophicalSignal] = field(default_factory=list)

# ===========================================
# CLASE BASE: PHILOSOPHER TRADER
# ===========================================

class PhilosopherTrader(ABC):
    """Clase base para todos los filósofos traders"""
    
    def __init__(self, name: str, philosophy: MarketPhilosophy):
        self.name = name
        self.philosophy = philosophy
        self.principles = []  # Principios filosóficos
        self.strengths = []  # Fortalezas
        self.weaknesses = []  # Debilidades
        self.favorite_conditions = []  # Condiciones favorables
        self.avoid_conditions = []  # Condiciones a evitar
        self.win_rate = 0.0
        self.avg_return = 0.0
        self.max_drawdown = 0.0
        
    @abstractmethod
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza el mercado según su filosofía"""
        pass
    
    @abstractmethod
    def generate_thesis(self, analysis: Dict) -> str:
        """Genera una tesis sobre el mercado"""
        pass
    
    @abstractmethod
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        """Encuentra la antítesis a su tesis"""
        pass
    
    @abstractmethod
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        """Crea una síntesis dialéctica"""
        pass
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[PhilosophicalSignal]:
        """Genera una señal filosófica completa"""
        
        # Análisis según filosofía
        analysis = self.analyze_market(df)
        
        if not analysis.get('opportunity'):
            return None
        
        # Proceso dialéctico
        thesis = self.generate_thesis(analysis)
        antithesis = self.find_antithesis(thesis, analysis)
        synthesis = self.create_synthesis(thesis, antithesis)
        
        # Generar señal
        return PhilosophicalSignal(
            timestamp=datetime.now(),
            philosopher=self.name,
            philosophy=self.philosophy,
            symbol=symbol,
            action=analysis['action'],
            entry_price=analysis['entry_price'],
            stop_loss=analysis['stop_loss'],
            take_profit=analysis['take_profit'],
            confidence=analysis['confidence'],
            reasoning=analysis['reasoning'],
            thesis=thesis,
            antithesis=antithesis,
            synthesis=synthesis,
            position_size=analysis.get('position_size', 0),
            risk_reward=analysis.get('risk_reward', 0),
            metadata=analysis.get('metadata', {})
        )
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos universales"""
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['EMA_12'] = df['close'].ewm(span=12).mean()
        df['EMA_26'] = df['close'].ewm(span=26).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['ATR'] = ranges.max(axis=1).rolling(14).mean()
        
        # Volume Profile
        df['Volume_SMA'] = df['volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_SMA']
        
        return df

# ===========================================
# SÓCRATES: El Cuestionador (Ranging Markets)
# ===========================================

class Socrates(PhilosopherTrader):
    """
    Sócrates: "Solo sé que no sé nada"
    
    Filosofía: Cuestiona constantemente el mercado, busca la verdad
    en los rangos. No asume tendencias, pregunta si el precio es justo.
    
    Estrategia: Mean Reversion en rangos definidos
    """
    
    def __init__(self):
        super().__init__("Socrates", MarketPhilosophy.SOCRATIC)
        
        self.principles = [
            "El mercado no sabe a dónde va",
            "Cuestiona cada movimiento",
            "La verdad está en el equilibrio",
            "Conoce los límites de tu conocimiento"
        ]
        
        self.strengths = [
            "Excelente en mercados laterales",
            "Identifica soporte/resistencia con precisión",
            "No se deja llevar por FOMO",
            "Risk management conservador"
        ]
        
        self.weaknesses = [
            "Pierde grandes tendencias",
            "Muchos stops en breakouts",
            "Puede ser demasiado escéptico"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis socrático del mercado"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Identificar rango
        high_range = df['high'].rolling(20).max().iloc[-1]
        low_range = df['low'].rolling(20).min().iloc[-1]
        mid_range = (high_range + low_range) / 2
        range_size = high_range - low_range
        
        # Posición en el rango
        position_in_range = (current['close'] - low_range) / range_size
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Cuestionamiento socrático
        questions = [
            ("Esta el precio en extremo?", position_in_range < 0.2 or position_in_range > 0.8),
            ("Es el volumen normal?", current['Volume_Ratio'] < 1.5),
            ("RSI confirma extremo?", current['RSI'] < 30 or current['RSI'] > 70),
            ("Bollinger confirma?", current['close'] <= current['BB_Lower'] or current['close'] >= current['BB_Upper'])
        ]
        
        true_answers = sum(1 for _, answer in questions if answer)
        
        if true_answers >= 3:
            if position_in_range < 0.2 and current['RSI'] < 30:
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = low_range * 0.98
                analysis['take_profit'] = mid_range
                analysis['reasoning'] = [
                    "Precio en zona de soporte",
                    "RSI oversold confirmado",
                    "Rango bien definido"
                ]
            elif position_in_range > 0.8 and current['RSI'] > 70:
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = high_range * 1.02
                analysis['take_profit'] = mid_range
                analysis['reasoning'] = [
                    "Precio en zona de resistencia",
                    "RSI overbought confirmado",
                    "Reversión probable"
                ]
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['confidence'] = min(true_answers / 4, 0.85)
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'range_high': high_range,
                'range_low': low_range,
                'position_in_range': position_in_range,
                'questions_passed': true_answers
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "El precio ha caído injustamente, el mercado está equivocado en el corto plazo"
        elif analysis['action'] == 'SELL':
            return "El precio ha subido demasiado rápido, la euforia es irracional"
        return "El mercado está en equilibrio, no hay oportunidad clara"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "Pero podría haber una razón fundamental para la caída que desconozco"
        elif analysis['action'] == 'SELL':
            return "Quizás hay noticias positivas que justifican el rally"
        return "Mi percepción de equilibrio podría ser errónea"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        if 'BUY' in str(thesis):
            return "Compraré con stop loss ajustado, aceptando mi ignorancia pero confiando en el rango histórico"
        elif 'SELL' in str(thesis):
            return "Venderé con prudencia, reconociendo que el mercado puede permanecer irracional más tiempo que yo solvente"
        return "Esperaré más confirmaciones antes de actuar"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Calcula tamaño de posición socrático (conservador)"""
        base_size = 0.01  # 1% base
        return base_size * confidence * 0.8  # Reduce por prudencia

# ===========================================
# ARISTÓTELES: El Lógico (Trend Following)
# ===========================================

class Aristoteles(PhilosopherTrader):
    """
    Aristóteles: "La excelencia es un hábito"
    
    Filosofía: Lógica pura, causa y efecto. Si A entonces B.
    Las tendencias persisten por razones lógicas.
    
    Estrategia: Trend Following sistemático
    """
    
    def __init__(self):
        super().__init__("Aristoteles", MarketPhilosophy.ARISTOTELIAN)
        
        self.principles = [
            "Todo efecto tiene una causa",
            "La tendencia es tu amiga hasta que termina",
            "La lógica gobierna los mercados a largo plazo",
            "Los patrones se repiten por razones fundamentales"
        ]
        
        self.strengths = [
            "Captura grandes movimientos",
            "Sistema lógico y replicable",
            "Excelente en mercados trending",
            "Disciplina absoluta"
        ]
        
        self.weaknesses = [
            "Sufre en mercados laterales",
            "Entradas tardías",
            "No detecta reversiones rápidas"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis aristotélico (lógico) del mercado"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Lógica de tendencia
        ema_short = df['close'].ewm(span=20).mean().iloc[-1]
        ema_long = df['close'].ewm(span=50).mean().iloc[-1]
        
        # Condiciones lógicas
        bullish_structure = (
            current['close'] > ema_short and
            ema_short > ema_long and
            current['MACD'] > current['MACD_Signal']
        )
        
        bearish_structure = (
            current['close'] < ema_short and
            ema_short < ema_long and
            current['MACD'] < current['MACD_Signal']
        )
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        if bullish_structure:
            # Lógica de entrada en tendencia alcista
            if current['RSI'] > 50 and current['RSI'] < 70:
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = ema_short * 0.98
                analysis['take_profit'] = current['close'] * 1.05  # 5% objetivo
                analysis['reasoning'] = [
                    "Estructura alcista confirmada",
                    "EMAs alineadas positivamente",
                    "MACD bullish",
                    "RSI en zona de fuerza"
                ]
                analysis['confidence'] = 0.75
                
        elif bearish_structure:
            # Lógica de entrada en tendencia bajista
            if current['RSI'] < 50 and current['RSI'] > 30:
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = ema_short * 1.02
                analysis['take_profit'] = current['close'] * 0.95
                analysis['reasoning'] = [
                    "Estructura bajista confirmada",
                    "EMAs alineadas negativamente",
                    "MACD bearish",
                    "RSI en zona de debilidad"
                ]
                analysis['confidence'] = 0.70
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'ema_short': ema_short,
                'ema_long': ema_long,
                'trend_strength': abs(ema_short - ema_long) / ema_long
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "La tendencia alcista continuará porque las causas fundamentales persisten"
        elif analysis['action'] == 'SELL':
            return "La tendencia bajista es lógica dadas las condiciones actuales del mercado"
        return "No hay suficiente evidencia lógica para actuar"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "Las tendencias pueden revertir sin previo aviso por eventos impredecibles"
        elif analysis['action'] == 'SELL':
            return "Los mercados pueden permanecer ilógicos más tiempo del esperado"
        return "La falta de acción también es una decisión con consecuencias"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Seguiré la lógica del mercado con stops ajustados para protegerme de lo ilógico"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Tamaño de posición aristotélico (proporcional a la lógica)"""
        base_size = 0.015  # 1.5% base para tendencias
        return base_size * confidence

# ===========================================
# NIETZSCHE: El Contrarian (Counter-trend)
# ===========================================

class Nietzsche(PhilosopherTrader):
    """
    Nietzsche: "Hay que tener caos dentro de sí para dar a luz una estrella danzante"
    
    Filosofía: Va contra la masa, abraza el caos, busca la verdad en lo opuesto.
    Cuando todos compran, él vende. El superhombre del trading.
    
    Estrategia: Contrarian extremo, fade the crowd
    """
    
    def __init__(self):
        super().__init__("Nietzsche", MarketPhilosophy.NIETZSCHEAN)
        
        self.principles = [
            "La masa siempre se equivoca en los extremos",
            "Del caos nace el orden",
            "Lo que no te mata te hace más fuerte",
            "Transvalorar todos los valores del mercado"
        ]
        
        self.strengths = [
            "Captura reversiones explosivas",
            "Excelente en pánicos y euforias",
            "Entries en los mejores precios",
            "Gran ratio riesgo/beneficio"
        ]
        
        self.weaknesses = [
            "Muchos stops en tendencias fuertes",
            "Psicológicamente difícil",
            "Timing crucial",
            "Alto riesgo"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis nietzscheano (contrarian) del mercado"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Detectar extremos de sentimiento
        rsi_extreme = current['RSI'] < 20 or current['RSI'] > 80
        volume_extreme = current['Volume_Ratio'] > 2.5
        
        # Distancia de Bollinger Bands
        bb_distance_upper = (current['close'] - current['BB_Upper']) / current['BB_Upper']
        bb_distance_lower = (current['BB_Lower'] - current['close']) / current['BB_Lower']
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Buscar oportunidades contrarian
        if current['RSI'] < 20 and volume_extreme and bb_distance_lower > 0.02:
            # Pánico extremo - oportunidad de compra
            analysis['opportunity'] = True
            analysis['action'] = 'BUY'
            analysis['entry_price'] = current['close']
            analysis['stop_loss'] = current['close'] * 0.97  # Stop ajustado
            analysis['take_profit'] = current['BB_Middle']  # Target al medio
            analysis['reasoning'] = [
                "Pánico extremo detectado",
                "RSI en oversold histórico",
                "Volumen de capitulación",
                "La masa está equivocada"
            ]
            analysis['confidence'] = 0.80
            
        elif current['RSI'] > 80 and volume_extreme and bb_distance_upper > 0.02:
            # Euforia extrema - oportunidad de venta
            analysis['opportunity'] = True
            analysis['action'] = 'SELL'
            analysis['entry_price'] = current['close']
            analysis['stop_loss'] = current['close'] * 1.03
            analysis['take_profit'] = current['BB_Middle']
            analysis['reasoning'] = [
                "Euforia irracional detectada",
                "RSI en overbought extremo",
                "Volumen de FOMO",
                "El rebaño va al matadero"
            ]
            analysis['confidence'] = 0.75
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'rsi': current['RSI'],
                'volume_ratio': current['Volume_Ratio'],
                'bb_distance': bb_distance_upper if analysis['action'] == 'SELL' else bb_distance_lower,
                'chaos_level': 'EXTREME'
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "El miedo ha alcanzado su máximo, el rebaño huye cuando debería comprar"
        elif analysis['action'] == 'SELL':
            return "La codicia ciega a las masas, el precipicio está cerca"
        return "Aún no hay suficiente caos para actuar"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "Quizás el pánico esté justificado esta vez"
        elif analysis['action'] == 'SELL':
            return "La euforia podría continuar más de lo racional"
        return "El caos podría intensificarse antes de resolverse"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Abrazo el caos y actúo contra la masa, pero con la disciplina del superhombre trader"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición nietzscheana (agresiva en extremos)"""
        base_size = 0.02  # 2% base para contrarian
        return base_size * confidence * 1.2  # Boost por convicción

# ===========================================
# CONFUCIO: El Equilibrado (Mean Reversion)
# ===========================================

class Confucio(PhilosopherTrader):
    """
    Confucio: "En todo, el camino medio es el mejor"
    
    Filosofía: Busca el equilibrio y la armonía. Todo vuelve a su centro.
    Paciencia y disciplina. El mercado siempre regresa al balance.
    
    Estrategia: Mean Reversion con paciencia oriental
    """
    
    def __init__(self):
        super().__init__("Confucio", MarketPhilosophy.CONFUCIAN)
        
        self.principles = [
            "El equilibrio es el estado natural",
            "La paciencia es la mayor virtud",
            "Los extremos siempre regresan al centro",
            "La armonía genera prosperidad"
        ]
        
        self.strengths = [
            "Alta tasa de éxito",
            "Riesgo controlado",
            "Consistencia en resultados",
            "Funciona en la mayoría de condiciones"
        ]
        
        self.weaknesses = [
            "Ganancias moderadas",
            "Pierde grandes tendencias",
            "Requiere mucha paciencia"
        ]
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis confuciano del mercado"""
        
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        
        # Calcular el centro de equilibrio
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1]
        equilibrium = (sma_20 + sma_50) / 2
        
        # Distancia del equilibrio
        distance_from_equilibrium = (current['close'] - equilibrium) / equilibrium
        
        analysis = {
            'opportunity': False,
            'action': 'HOLD',
            'reasoning': []
        }
        
        # Buscar desequilibrios para restaurar
        if abs(distance_from_equilibrium) > 0.03:  # 3% del equilibrio
            
            if distance_from_equilibrium < -0.03 and current['RSI'] < 40:
                # Por debajo del equilibrio
                analysis['opportunity'] = True
                analysis['action'] = 'BUY'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = current['close'] * 0.98
                analysis['take_profit'] = equilibrium
                analysis['reasoning'] = [
                    "Precio debajo del equilibrio",
                    "El balance debe restaurarse",
                    "RSI confirma sobreventa",
                    "La paciencia será recompensada"
                ]
                analysis['confidence'] = 0.70
                
            elif distance_from_equilibrium > 0.03 and current['RSI'] > 60:
                # Por encima del equilibrio
                analysis['opportunity'] = True
                analysis['action'] = 'SELL'
                analysis['entry_price'] = current['close']
                analysis['stop_loss'] = current['close'] * 1.02
                analysis['take_profit'] = equilibrium
                analysis['reasoning'] = [
                    "Precio sobre el equilibrio",
                    "La gravedad del mercado actuará",
                    "RSI confirma sobrecompra",
                    "Todo exceso se corrige"
                ]
                analysis['confidence'] = 0.70
        
        if analysis['opportunity']:
            risk = abs(analysis['entry_price'] - analysis['stop_loss'])
            reward = abs(analysis['take_profit'] - analysis['entry_price'])
            analysis['risk_reward'] = reward / risk if risk > 0 else 0
            analysis['position_size'] = self._calculate_position_size(analysis['confidence'])
            
            analysis['metadata'] = {
                'equilibrium': equilibrium,
                'distance': distance_from_equilibrium,
                'harmony_level': 1 - abs(distance_from_equilibrium)
            }
        
        return analysis
    
    def generate_thesis(self, analysis: Dict) -> str:
        if analysis['action'] == 'BUY':
            return "El Yin ha dominado demasiado, el Yang debe restaurar el balance"
        elif analysis['action'] == 'SELL':
            return "El Yang es excesivo, el Yin traerá equilibrio"
        return "El mercado está en armonía, no hay que perturbarlo"
    
    def find_antithesis(self, thesis: str, analysis: Dict) -> str:
        return "Los desequilibrios pueden persistir más de lo esperado en tiempos de cambio"
    
    def create_synthesis(self, thesis: str, antithesis: str) -> str:
        return "Actuaré con paciencia y disciplina, confiando en que el equilibrio siempre prevalece"
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Posición confuciana (equilibrada)"""
        base_size = 0.01  # 1% base conservador
        return base_size * confidence

# ===========================================
# GESTOR DE FILÓSOFOS
# ===========================================

class PhilosophicalTradingSystem:
    """Sistema que gestiona múltiples filósofos traders"""
    
    def __init__(self):
        self.philosophers = {
            'SOCRATES': Socrates(),
            'ARISTOTELES': Aristoteles(),
            'NIETZSCHE': Nietzsche(),
            'CONFUCIO': Confucio()
        }
        
        self.active_projects = {}  # Proyectos activos
        self.historical_signals = []  # Histórico de señales
        self.performance_metrics = {}  # Métricas de performance
        
    def create_project(self, name: str, philosophers: List[str], 
                      symbols: List[str], capital: float) -> TradingProject:
        """Crea un nuevo proyecto de trading"""
        
        project_id = f"PROJ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        project = TradingProject(
            id=project_id,
            name=name,
            created_at=datetime.now(),
            philosophers=philosophers,
            capital=capital,
            risk_per_trade=0.01,
            symbols=symbols,
            timeframe='1h',
            status='ACTIVE'
        )
        
        self.active_projects[project_id] = project
        
        logger.info(f"Proyecto creado: {name} con filósofos: {philosophers}")
        
        return project
    
    def analyze_with_philosophers(self, df: pd.DataFrame, symbol: str, 
                                 philosophers: List[str]) -> List[PhilosophicalSignal]:
        """Analiza con múltiples filósofos"""
        
        signals = []
        
        for philosopher_name in philosophers:
            if philosopher_name in self.philosophers:
                philosopher = self.philosophers[philosopher_name]
                signal = philosopher.generate_signal(df, symbol)
                
                if signal:
                    signals.append(signal)
                    logger.info(f"{philosopher_name} generó señal: {signal.action} para {symbol}")
        
        return signals
    
    def get_consensus(self, signals: List[PhilosophicalSignal]) -> Optional[Dict]:
        """Obtiene consenso entre filósofos"""
        
        if not signals:
            return None
        
        # Contar votos
        actions = {}
        for signal in signals:
            if signal.action not in actions:
                actions[signal.action] = []
            actions[signal.action].append(signal)
        
        # Acción más votada
        majority_action = max(actions.items(), key=lambda x: len(x[1]))
        
        if len(majority_action[1]) >= 2:  # Al menos 2 filósofos de acuerdo
            # Promediar parámetros
            avg_entry = np.mean([s.entry_price for s in majority_action[1]])
            avg_stop = np.mean([s.stop_loss for s in majority_action[1]])
            avg_target = np.mean([s.take_profit for s in majority_action[1]])
            avg_confidence = np.mean([s.confidence for s in majority_action[1]])
            
            return {
                'action': majority_action[0],
                'entry_price': avg_entry,
                'stop_loss': avg_stop,
                'take_profit': avg_target,
                'confidence': avg_confidence,
                'philosophers_agreed': [s.philosopher for s in majority_action[1]],
                'signals': majority_action[1]
            }
        
        return None
    
    def execute_project_cycle(self, project_id: str, market_data: Dict[str, pd.DataFrame]):
        """Ejecuta un ciclo de análisis para un proyecto"""
        
        if project_id not in self.active_projects:
            logger.error(f"Proyecto {project_id} no encontrado")
            return
        
        project = self.active_projects[project_id]
        
        if project.status != 'ACTIVE':
            return
        
        all_signals = []
        
        # Analizar cada símbolo con los filósofos del proyecto
        for symbol in project.symbols:
            if symbol in market_data:
                df = market_data[symbol]
                signals = self.analyze_with_philosophers(df, symbol, project.philosophers)
                
                if signals:
                    # Buscar consenso
                    consensus = self.get_consensus(signals)
                    
                    if consensus:
                        logger.info(f"Consenso alcanzado para {symbol}: {consensus['action']}")
                        logger.info(f"Filósofos de acuerdo: {consensus['philosophers_agreed']}")
                        
                        # Agregar a señales activas del proyecto
                        for signal in consensus['signals']:
                            project.active_signals.append(signal)
                            self.historical_signals.append(signal)
        
        # Actualizar métricas del proyecto
        self._update_project_metrics(project)
    
    def _update_project_metrics(self, project: TradingProject):
        """Actualiza métricas de performance del proyecto"""
        
        if project.active_signals:
            project.performance['total_signals'] = len(project.active_signals)
            project.performance['last_update'] = datetime.now()
            
            # Calcular consenso promedio
            avg_confidence = np.mean([s.confidence for s in project.active_signals])
            project.performance['avg_confidence'] = avg_confidence
    
    def get_philosophical_summary(self) -> Dict:
        """Obtiene resumen de todos los filósofos"""
        
        summary = {}
        
        for name, philosopher in self.philosophers.items():
            summary[name] = {
                'philosophy': philosopher.philosophy.value,
                'principles': philosopher.principles,
                'strengths': philosopher.strengths,
                'weaknesses': philosopher.weaknesses
            }
        
        return summary

# ===========================================
# FUNCIONES DE UTILIDAD
# ===========================================

def philosophical_debate(philosophers: List[str], topic: str = "market_direction"):
    """Simula un debate filosófico sobre el mercado"""
    
    print(f"\n{'='*60}")
    print(f"DEBATE FILOSÓFICO: {topic}")
    print(f"{'='*60}\n")
    
    system = PhilosophicalTradingSystem()
    
    for name in philosophers:
        if name in system.philosophers:
            philosopher = system.philosophers[name]
            print(f"\n🏛️ {name}:")
            print(f"Filosofía: {philosopher.philosophy.value}")
            print(f"Principio principal: {philosopher.principles[0]}")
            print(f"Fortaleza clave: {philosopher.strengths[0]}")

def test_philosophical_system():
    """Prueba el sistema filosófico"""
    
    print("\n" + "="*60)
    print("SISTEMA DE TRADING FILOSÓFICO V2.0")
    print("="*60)
    
    system = PhilosophicalTradingSystem()
    
    # Mostrar filósofos disponibles
    print("\n🏛️ FILÓSOFOS DISPONIBLES:")
    for name, philosopher in system.philosophers.items():
        print(f"\n{name}:")
        print(f"  Filosofía: {philosopher.philosophy.value}")
        print(f"  Principio: {philosopher.principles[0]}")
    
    # Crear proyecto de ejemplo
    project = system.create_project(
        name="Proyecto Síntesis Dialéctica",
        philosophers=['SOCRATES', 'ARISTOTELES', 'NIETZSCHE'],
        symbols=['BTC-USD', 'ETH-USD'],
        capital=10000
    )
    
    print(f"\n✅ Proyecto creado: {project.name}")
    print(f"   ID: {project.id}")
    print(f"   Filósofos: {project.philosophers}")
    print(f"   Capital: ${project.capital}")
    
    # Simular debate
    philosophical_debate(['SOCRATES', 'NIETZSCHE'], "Bitcoin dirección")

# Instancia global singleton
_global_system = None

def get_trading_system() -> PhilosophicalTradingSystem:
    """Obtiene la instancia global del sistema de trading"""
    global _global_system
    if _global_system is None:
        _global_system = PhilosophicalTradingSystem()
    return _global_system

if __name__ == "__main__":
    test_philosophical_system()