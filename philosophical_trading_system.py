#!/usr/bin/env python3
"""
Sistema de Trading Filosófico con Consenso
Versión 3.0 - Sin señales contradictorias
"""

import pandas as pd
import numpy as np
# Usar Binance en lugar de Yahoo Finance
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from binance_client import binance_client
from signal_validator import SignalValidator  # Importar el validador
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import logging
from collections import defaultdict
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PhilosophicalSignal:
    """Señal consensuada del sistema filosófico"""
    timestamp: datetime
    symbol: str
    action: str  # BUY o SELL únicamente
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    philosophers_agree: List[str]  # Filósofos que están de acuerdo
    philosophers_disagree: List[str]  # Filósofos en desacuerdo
    consensus_score: float
    market_regime: str
    reasoning: List[str]
    risk_reward: float

class SignalTracker:
    """Rastrea señales para evitar contradicciones"""
    
    def __init__(self):
        self.active_signals = {}  # symbol -> (action, timestamp)
        self.signal_history = defaultdict(list)
        self.lockout_period = 900  # 15 minutos entre señales opuestas
        self.lock = threading.Lock()
    
    def can_generate_signal(self, symbol: str, action: str) -> Tuple[bool, str]:
        """Verifica si se puede generar una nueva señal"""
        
        with self.lock:
            current_time = datetime.now()
            
            # Verificar si hay señal activa
            if symbol in self.active_signals:
                last_action, last_time = self.active_signals[symbol]
                time_diff = (current_time - last_time).total_seconds()
                
                # Si es la misma dirección, permitir después de 5 minutos
                if last_action == action:
                    if time_diff < 300:  # 5 minutos
                        return False, f"Señal {action} reciente, esperar {300-time_diff:.0f}s"
                    return True, "OK - Misma dirección"
                
                # Si es dirección opuesta, bloquear por 15 minutos
                else:
                    if time_diff < self.lockout_period:
                        remaining = self.lockout_period - time_diff
                        return False, f"Señal opuesta bloqueada por {remaining:.0f}s"
                    return True, "OK - Lockout expirado"
            
            return True, "OK - Sin señales previas"
    
    def register_signal(self, symbol: str, action: str):
        """Registra una nueva señal"""
        
        with self.lock:
            current_time = datetime.now()
            self.active_signals[symbol] = (action, current_time)
            self.signal_history[symbol].append({
                'action': action,
                'timestamp': current_time
            })
            
            # Limpiar historial antiguo (> 24 horas)
            cutoff_time = current_time - timedelta(hours=24)
            self.signal_history[symbol] = [
                s for s in self.signal_history[symbol]
                if s['timestamp'] > cutoff_time
            ]

class PhilosophicalConsensusSystem:
    """Sistema principal con consenso filosófico"""
    
    def __init__(self):
        self.signal_tracker = SignalTracker()
        self.signal_validator = SignalValidator(consensus_threshold=0.65)  # Usar el validador
        self.min_consensus = 0.65  # 65% de consenso mínimo
        self.min_philosophers = 3  # Mínimo 3 filósofos de acuerdo
        
        # Configuración de filósofos
        self.philosophers = {
            'Socrates': {'specialty': 'RANGING', 'weight': 1.0},
            'Aristoteles': {'specialty': 'TRENDING', 'weight': 1.1},
            'Platon': {'specialty': 'PATTERNS', 'weight': 1.0},
            'Nietzsche': {'specialty': 'CONTRARIAN', 'weight': 0.9},
            'Kant': {'specialty': 'RULES', 'weight': 1.0},
            'Descartes': {'specialty': 'CONFIRMATION', 'weight': 1.1},
            'Confucio': {'specialty': 'BALANCE', 'weight': 1.0},
            'SunTzu': {'specialty': 'TIMING', 'weight': 1.2}
        }
        
        # Pesos por régimen de mercado
        self.regime_weights = {
            'TRENDING': {
                'Aristoteles': 1.3,
                'Descartes': 1.2,
                'SunTzu': 1.1,
                'Kant': 1.0,
                'Platon': 0.9,
                'Nietzsche': 0.8,
                'Socrates': 0.6,
                'Confucio': 0.7
            },
            'RANGING': {
                'Socrates': 1.4,
                'Confucio': 1.3,
                'Platon': 1.0,
                'Kant': 1.0,
                'Descartes': 0.9,
                'Aristoteles': 0.7,
                'Nietzsche': 0.8,
                'SunTzu': 0.9
            },
            'VOLATILE': {
                'SunTzu': 1.4,
                'Nietzsche': 1.3,
                'Descartes': 1.2,
                'Kant': 1.1,
                'Aristoteles': 0.8,
                'Platon': 0.7,
                'Socrates': 0.6,
                'Confucio': 0.5
            }
        }
    
    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detecta el régimen actual del mercado"""
        
        # ATR para volatilidad
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        atr = ranges.max(axis=1).rolling(14).mean()
        
        current_atr = atr.iloc[-1]
        avg_atr = atr.rolling(50).mean().iloc[-1]
        volatility_ratio = current_atr / avg_atr if avg_atr > 0 else 1
        
        # EMAs para tendencia
        ema_20 = df['Close'].ewm(span=20).mean()
        ema_50 = df['Close'].ewm(span=50).mean()
        
        # ADX para fuerza de tendencia
        plus_dm = df['High'].diff()
        minus_dm = -df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = ranges.max(axis=1)
        atr14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr14)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr14)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(14).mean().iloc[-1]
        
        # Determinar régimen
        if volatility_ratio > 1.5:
            return 'VOLATILE'
        elif adx > 25 and abs(ema_20.iloc[-1] - ema_50.iloc[-1]) / ema_50.iloc[-1] > 0.01:
            return 'TRENDING'
        else:
            return 'RANGING'
    
    def get_philosopher_opinion(self, philosopher: str, df: pd.DataFrame, 
                               market_regime: str) -> Dict:
        """Obtiene la opinión de un filósofo específico"""
        
        current_price = df['Close'].iloc[-1]
        
        # Calcular indicadores
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # EMAs
        ema_9 = df['Close'].ewm(span=9).mean().iloc[-1]
        ema_21 = df['Close'].ewm(span=21).mean().iloc[-1]
        
        # Bollinger Bands
        bb_middle = df['Close'].rolling(20).mean().iloc[-1]
        bb_std = df['Close'].rolling(20).std().iloc[-1]
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        
        # Lógica específica por filósofo
        opinion = {'philosopher': philosopher, 'vote': None, 'confidence': 0}
        
        if philosopher == 'Socrates':
            # Experto en rangos - mean reversion
            if current_price <= bb_lower and rsi < 35:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.7 + (30 - rsi) / 100
            elif current_price >= bb_upper and rsi > 65:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.7 + (rsi - 70) / 100
                
        elif philosopher == 'Aristoteles':
            # Sigue tendencias con lógica
            if ema_9 > ema_21 and rsi < 70:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.65 + (ema_9 - ema_21) / ema_21
            elif ema_9 < ema_21 and rsi > 30:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.65 + (ema_21 - ema_9) / ema_21
                
        elif philosopher == 'Nietzsche':
            # Contrarian extremo
            if rsi < 25:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.8
            elif rsi > 75:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.8
                
        elif philosopher == 'Platon':
            # Busca patrones ideales
            support = df['Low'].rolling(20).min().iloc[-1]
            resistance = df['High'].rolling(20).max().iloc[-1]
            
            if abs(current_price - support) / support < 0.02:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.75
            elif abs(current_price - resistance) / resistance < 0.02:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.75
                
        elif philosopher == 'Kant':
            # Reglas estrictas
            if rsi < 30 and current_price < bb_lower:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.85
            elif rsi > 70 and current_price > bb_upper:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.85
                
        elif philosopher == 'Descartes':
            # Múltiples confirmaciones
            buy_signals = sum([
                rsi < 40,
                current_price < bb_middle,
                ema_9 > ema_21,
                df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]
            ])
            sell_signals = sum([
                rsi > 60,
                current_price > bb_middle,
                ema_9 < ema_21,
                df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]
            ])
            
            if buy_signals >= 3:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.5 + buy_signals * 0.15
            elif sell_signals >= 3:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.5 + sell_signals * 0.15
                
        elif philosopher == 'Confucio':
            # Balance y equilibrio
            distance_from_middle = (current_price - bb_middle) / bb_middle
            
            if distance_from_middle < -0.02 and rsi < 45:
                opinion['vote'] = 'BUY'
                opinion['confidence'] = 0.7
            elif distance_from_middle > 0.02 and rsi > 55:
                opinion['vote'] = 'SELL'
                opinion['confidence'] = 0.7
                
        elif philosopher == 'SunTzu':
            # Timing estratégico
            volume_surge = df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5
            
            if volume_surge:
                if rsi < 40 and ema_9 > ema_21:
                    opinion['vote'] = 'BUY'
                    opinion['confidence'] = 0.8
                elif rsi > 60 and ema_9 < ema_21:
                    opinion['vote'] = 'SELL'
                    opinion['confidence'] = 0.8
        
        # Aplicar peso según régimen de mercado
        if opinion['vote']:
            weight = self.regime_weights[market_regime].get(philosopher, 1.0)
            opinion['confidence'] *= weight
            opinion['confidence'] = min(opinion['confidence'], 0.95)
        
        return opinion
    
    def get_consensus(self, symbol: str, df: pd.DataFrame) -> Optional[PhilosophicalSignal]:
        """Obtiene el consenso de todos los filósofos"""
        
        market_regime = self.detect_market_regime(df)
        logger.info(f"Régimen de mercado para {symbol}: {market_regime}")
        
        # Obtener opiniones de todos los filósofos
        opinions = []
        for philosopher in self.philosophers:
            opinion = self.get_philosopher_opinion(philosopher, df, market_regime)
            if opinion['vote']:
                opinions.append(opinion)
                logger.debug(f"{philosopher}: {opinion['vote']} ({opinion['confidence']:.2f})")
        
        if not opinions:
            logger.info("No hay opiniones de los filósofos")
            return None
        
        # VALIDAR CON EL NUEVO SISTEMA PARA EVITAR CONTRADICCIONES
        validated_signal = self.signal_validator.validate_philosopher_signals(opinions, symbol)
        
        if not validated_signal:
            logger.info("❌ Señal rechazada por el validador (contradicciones o falta de consenso)")
            return None
        
        # Extraer datos del validador
        action = validated_signal['action']
        confidence = validated_signal['consensus_percentage']
        philosophers_agree = validated_signal['supporting_philosophers']
        philosophers_disagree = validated_signal['opposing_philosophers']
        
        # Verificar coherencia con el historial
        if not self.signal_validator.check_signal_coherence(validated_signal):
            logger.warning(f"❌ Señal rechazada por incoherencia con el historial")
            return None
        
        # Calcular niveles de entrada y salida
        current_price = df['Close'].iloc[-1]
        atr = self._calculate_atr(df)
        
        if action == 'BUY':
            stop_loss = current_price - (atr * 2)
            take_profit = current_price + (atr * 3)
        else:
            stop_loss = current_price + (atr * 2)
            take_profit = current_price - (atr * 3)
        
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        # Registrar la señal
        self.signal_tracker.register_signal(symbol, action)
        
        # Crear señal consensuada
        signal = PhilosophicalSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            philosophers_agree=philosophers_agree,
            philosophers_disagree=philosophers_disagree,
            consensus_score=confidence,
            market_regime=market_regime,
            reasoning=[
                f"Consenso {action}: {confidence:.1%}",
                f"{len(philosophers_agree)} filósofos de acuerdo",
                f"Régimen: {market_regime}",
                f"R/R: {risk_reward:.2f}"
            ],
            risk_reward=risk_reward
        )
        
        return signal
    
    def _calculate_atr(self, df: pd.DataFrame) -> float:
        """Calcula el Average True Range"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        return atr
    
    def scan_symbols(self, symbols: List[str], period: str = '7d', 
                    interval: str = '1h') -> List[PhilosophicalSignal]:
        """Escanea múltiples símbolos en busca de señales"""
        
        signals = []
        
        for symbol in symbols:
            logger.info(f"\n{'='*50}")
            logger.info(f"Analizando {symbol}")
            logger.info(f"{'='*50}")
            
            try:
                # Obtener datos desde Binance
                # Convertir período a número de velas
                limit = 168 if period == '7d' else 100  # 7d = 168 horas
                df = binance_client.get_klines(symbol, interval, limit)
                
                if len(df) < 20:
                    logger.warning(f"Datos insuficientes para {symbol}")
                    continue
                
                # Obtener consenso
                signal = self.get_consensus(symbol, df)
                
                if signal:
                    signals.append(signal)
                    logger.info(f"✅ SEÑAL GENERADA: {signal.action} @ ${signal.entry_price:.4f}")
                    logger.info(f"   Confianza: {signal.confidence:.1%}")
                    logger.info(f"   A favor: {', '.join(signal.philosophers_agree)}")
                    if signal.philosophers_disagree:
                        logger.info(f"   En contra: {', '.join(signal.philosophers_disagree)}")
                else:
                    logger.info("❌ Sin consenso - No se genera señal")
                    
            except Exception as e:
                logger.error(f"Error analizando {symbol}: {e}")
        
        return signals
    
    def save_signals(self, signals: List[PhilosophicalSignal], filename: str = None):
        """Guarda las señales en un archivo JSON"""
        
        if not filename:
            filename = f"philosophical_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        signals_dict = []
        for signal in signals:
            signals_dict.append({
                'timestamp': signal.timestamp.isoformat(),
                'symbol': signal.symbol,
                'action': signal.action,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'confidence': signal.confidence,
                'consensus_score': signal.consensus_score,
                'philosophers_agree': signal.philosophers_agree,
                'philosophers_disagree': signal.philosophers_disagree,
                'market_regime': signal.market_regime,
                'risk_reward': signal.risk_reward,
                'reasoning': signal.reasoning
            })
        
        with open(filename, 'w') as f:
            json.dump(signals_dict, f, indent=2)
        
        logger.info(f"💾 Señales guardadas en {filename}")
        return filename


def main():
    """Función principal de demostración"""
    
    print("\n" + "="*70)
    print(" SISTEMA DE TRADING FILOSÓFICO CON CONSENSO V3.0 ".center(70))
    print("="*70)
    print("\n✅ Sin señales contradictorias")
    print("✅ Consenso mínimo 65% requerido")
    print("✅ Mínimo 3 filósofos de acuerdo")
    print("✅ Bloqueo de 15 minutos entre señales opuestas\n")
    
    # Crear sistema
    system = PhilosophicalConsensusSystem()
    
    # Símbolos a analizar
    symbols = [
        'BTC-USD',
        'ETH-USD', 
        'DOGE-USD',
        'SOL-USD',
        'ADA-USD'
    ]
    
    # Escanear símbolos
    signals = system.scan_symbols(symbols)
    
    # Mostrar resumen
    print("\n" + "="*70)
    print(" RESUMEN DE SEÑALES ".center(70))
    print("="*70)
    
    if signals:
        print(f"\n📊 Total de señales generadas: {len(signals)}\n")
        
        for signal in signals:
            print(f"\n{'='*50}")
            print(f"📍 {signal.symbol} - {signal.action}")
            print(f"{'='*50}")
            print(f"Precio entrada: ${signal.entry_price:.4f}")
            print(f"Stop Loss: ${signal.stop_loss:.4f}")
            print(f"Take Profit: ${signal.take_profit:.4f}")
            print(f"Confianza: {signal.confidence:.1%}")
            print(f"R/R: {signal.risk_reward:.2f}")
            print(f"Filósofos a favor: {', '.join(signal.philosophers_agree)}")
            if signal.philosophers_disagree:
                print(f"Filósofos en contra: {', '.join(signal.philosophers_disagree)}")
        
        # Guardar señales
        system.save_signals(signals)
    else:
        print("\n❌ No se generaron señales con consenso suficiente")
    
    print("\n" + "="*70)
    print(" Sistema ejecutado correctamente ".center(70))
    print("="*70)


if __name__ == "__main__":
    main()