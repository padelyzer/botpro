#!/usr/bin/env python3
"""
REALTIME SIGNAL MONITOR - BotphIA
Monitor en tiempo real de señales multi-timeframe con notificaciones progresivas
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set
import pandas as pd
import json
from enum import Enum

# Importar componentes del sistema
from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import (
    TRADING_PAIRS, TIMEFRAMES, 
    PatternDetector, Signal, PatternStage
)
from signal_notification_system import SignalNotificationManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitorMode(Enum):
    """Modos de operación del monitor"""
    AGGRESSIVE = "aggressive"    # Notifica todo
    BALANCED = "balanced"        # Balance entre señales
    CONSERVATIVE = "conservative" # Solo alta confianza
    CUSTOM = "custom"            # Personalizado

class RealTimeSignalMonitor:
    """Monitor principal de señales en tiempo real"""
    
    def __init__(self, mode: MonitorMode = MonitorMode.BALANCED):
        # Componentes principales
        self.connector = BinanceConnector(testnet=False)
        self.detector = PatternDetector()
        self.notifier = SignalNotificationManager()
        
        # Configuración
        self.mode = mode
        self.trading_pairs = TRADING_PAIRS
        self.timeframes = TIMEFRAMES
        self.scan_interval = self.get_scan_interval()
        
        # Estado del monitor
        self.is_running = False
        self.last_scan = {}
        self.active_signals = {}
        self.signal_history = []
        self.statistics = {
            'scans_completed': 0,
            'signals_detected': 0,
            'signals_confirmed': 0,
            'patterns_by_type': {},
            'best_performers': {}
        }
        
        # Configurar umbrales según modo
        self.configure_thresholds()
    
    def get_scan_interval(self) -> Dict[str, int]:
        """Define intervalos de escaneo por timeframe"""
        return {
            '5m': 60,      # Cada minuto
            '15m': 180,    # Cada 3 minutos
            '1h': 300,     # Cada 5 minutos
            '4h': 600      # Cada 10 minutos
        }
    
    def configure_thresholds(self):
        """Configura umbrales según el modo"""
        
        if self.mode == MonitorMode.AGGRESSIVE:
            self.min_confidence = 40
            self.notify_potential = True
            self.notify_forming = True
            self.max_signals_per_pair = 5
            
        elif self.mode == MonitorMode.CONSERVATIVE:
            self.min_confidence = 70
            self.notify_potential = False
            self.notify_forming = False
            self.max_signals_per_pair = 2
            
        else:  # BALANCED
            self.min_confidence = 50
            self.notify_potential = False
            self.notify_forming = True
            self.max_signals_per_pair = 3
    
    async def scan_symbol_timeframe(self, symbol: str, timeframe: str) -> List[Signal]:
        """Escanea un símbolo en un timeframe específico"""
        
        try:
            # Obtener datos históricos
            df = self.connector.get_historical_data(
                symbol, 
                timeframe=timeframe, 
                limit=TIMEFRAMES[timeframe]['bars']
            )
            
            if df.empty or len(df) < 50:
                return []
            
            # Detectar patrones
            signals = self.detector.detect_all_patterns(df, symbol, timeframe)
            
            # Filtrar según configuración
            filtered_signals = self.filter_signals(signals)
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error escaneando {symbol} {timeframe}: {e}")
            return []
    
    def filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """Filtra señales según configuración del modo"""
        
        filtered = []
        
        for signal in signals:
            # Filtrar por confianza mínima
            if signal.confidence < self.min_confidence:
                continue
            
            # Filtrar por stage según modo
            if not self.notify_potential and signal.stage == PatternStage.POTENTIAL:
                continue
            if not self.notify_forming and signal.stage == PatternStage.FORMING:
                continue
            
            # Verificar límite por par
            pair_signals = len([s for s in filtered if s.symbol == signal.symbol])
            if pair_signals >= self.max_signals_per_pair:
                continue
            
            filtered.append(signal)
        
        return filtered
    
    async def scan_all_pairs(self):
        """Escanea todos los pares en todos los timeframes"""
        
        logger.info("🔍 Iniciando escaneo completo...")
        scan_start = datetime.now()
        all_signals = []
        
        # Crear tareas para escaneo paralelo
        tasks = []
        for symbol in self.trading_pairs:
            for timeframe in self.timeframes.keys():
                # Verificar si es tiempo de escanear este timeframe
                if self.should_scan(symbol, timeframe):
                    tasks.append(self.scan_symbol_timeframe(symbol, timeframe))
        
        # Ejecutar escaneos en paralelo
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_signals.extend(result)
        
        # Procesar señales detectadas
        await self.process_signals(all_signals)
        
        # Actualizar estadísticas
        self.statistics['scans_completed'] += 1
        scan_time = (datetime.now() - scan_start).total_seconds()
        
        logger.info(f"✅ Escaneo completado en {scan_time:.1f}s - {len(all_signals)} señales detectadas")
        
        return all_signals
    
    def should_scan(self, symbol: str, timeframe: str) -> bool:
        """Determina si es tiempo de escanear un par/timeframe"""
        
        key = f"{symbol}_{timeframe}"
        
        if key not in self.last_scan:
            self.last_scan[key] = datetime.now()
            return True
        
        time_diff = (datetime.now() - self.last_scan[key]).total_seconds()
        
        if time_diff >= self.scan_interval[timeframe]:
            self.last_scan[key] = datetime.now()
            return True
        
        return False
    
    async def process_signals(self, signals: List[Signal]):
        """Procesa y notifica las señales detectadas"""
        
        for signal in signals:
            signal_key = f"{signal.symbol}_{signal.pattern_type.value}_{signal.timeframe}"
            
            # Verificar si es una señal nueva o actualización
            if signal_key in self.active_signals:
                old_signal = self.active_signals[signal_key]
                
                # Verificar si cambió de stage
                if old_signal.stage != signal.stage:
                    logger.info(f"📊 Actualización: {signal.symbol} {signal.pattern_type.value} - {old_signal.stage.value} → {signal.stage.value}")
                    await self.notifier.process_signal(signal)
            else:
                # Nueva señal
                logger.info(f"🆕 Nueva señal: {signal.symbol} {signal.pattern_type.value} - {signal.stage.value}")
                await self.notifier.process_signal(signal)
            
            # Actualizar señal activa
            self.active_signals[signal_key] = signal
            
            # Actualizar estadísticas
            self.update_statistics(signal)
            
            # Guardar en historial
            self.signal_history.append(signal)
    
    def update_statistics(self, signal: Signal):
        """Actualiza estadísticas del monitor"""
        
        self.statistics['signals_detected'] += 1
        
        if signal.stage == PatternStage.CONFIRMED:
            self.statistics['signals_confirmed'] += 1
        
        # Contar por tipo de patrón
        pattern_name = signal.pattern_type.value
        if pattern_name not in self.statistics['patterns_by_type']:
            self.statistics['patterns_by_type'][pattern_name] = 0
        self.statistics['patterns_by_type'][pattern_name] += 1
        
        # Actualizar mejores performers
        if signal.confidence >= 80:
            if signal.symbol not in self.statistics['best_performers']:
                self.statistics['best_performers'][signal.symbol] = 0
            self.statistics['best_performers'][signal.symbol] += 1
    
    async def cleanup_old_signals(self):
        """Limpia señales antiguas"""
        
        current_time = datetime.now()
        
        # Limpiar señales activas más antiguas de 24 horas
        for key in list(self.active_signals.keys()):
            signal = self.active_signals[key]
            if current_time - signal.current_timestamp > timedelta(hours=24):
                del self.active_signals[key]
        
        # Limpiar historial más antiguo de 7 días
        self.signal_history = [
            s for s in self.signal_history 
            if current_time - s.current_timestamp <= timedelta(days=7)
        ]
    
    def print_statistics(self):
        """Imprime estadísticas del monitor"""
        
        try:
            # Intentar usar display mejorado
            from terminal_signal_display import TerminalSignalDisplay
            display = TerminalSignalDisplay()
            signals = list(self.active_signals.values())
            display.display_signals(signals, self.statistics)
        except ImportError:
            # Fallback a impresión básica
            print("\n" + "="*60)
            print("📊 ESTADÍSTICAS DEL MONITOR")
            print("="*60)
            print(f"✅ Escaneos completados: {self.statistics['scans_completed']}")
            print(f"📊 Señales detectadas: {self.statistics['signals_detected']}")
            print(f"✅ Señales confirmadas: {self.statistics['signals_confirmed']}")
            
            if self.statistics['patterns_by_type']:
                print("\n🎯 Patrones por tipo:")
                for pattern, count in sorted(self.statistics['patterns_by_type'].items(), key=lambda x: x[1], reverse=True):
                    print(f"   {pattern}: {count}")
            
            if self.statistics['best_performers']:
                print("\n⭐ Mejores pares:")
                for symbol, count in sorted(self.statistics['best_performers'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"   {symbol}: {count} señales de alta confianza")
            
            print("\n🔄 Señales activas:")
            for key, signal in self.active_signals.items():
                print(f"   {signal.symbol} - {signal.pattern_type.value} - {signal.stage.value} ({signal.confidence:.1f}%)")
            
            print("="*60)
    
    async def run(self):
        """Ejecuta el monitor continuamente"""
        
        self.is_running = True
        logger.info(f"🚀 Iniciando monitor en modo {self.mode.value}")
        logger.info(f"📊 Monitoreando {len(self.trading_pairs)} pares en {len(self.timeframes)} timeframes")
        
        # Contador para estadísticas
        stats_counter = 0
        cleanup_counter = 0
        
        try:
            while self.is_running:
                # Escanear todos los pares
                await self.scan_all_pairs()
                
                # Mostrar estadísticas cada 10 escaneos
                stats_counter += 1
                if stats_counter >= 10:
                    self.print_statistics()
                    stats_counter = 0
                
                # Limpiar señales antiguas cada hora
                cleanup_counter += 1
                if cleanup_counter >= 60:
                    await self.cleanup_old_signals()
                    cleanup_counter = 0
                
                # Esperar antes del próximo escaneo
                await asyncio.sleep(60)  # Esperar 1 minuto base
                
        except KeyboardInterrupt:
            logger.info("⏹️ Deteniendo monitor...")
        except Exception as e:
            logger.error(f"❌ Error en monitor: {e}")
        finally:
            self.is_running = False
            self.print_statistics()
            logger.info("👋 Monitor detenido")
    
    def stop(self):
        """Detiene el monitor"""
        self.is_running = False
    
    async def get_active_signals(self) -> List[Signal]:
        """Obtiene las señales activas actuales"""
        return list(self.active_signals.values())
    
    def export_signals(self, filename: str = None):
        """Exporta señales a archivo JSON"""
        
        if not filename:
            filename = f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode.value,
            'statistics': self.statistics,
            'active_signals': [
                {
                    'symbol': s.symbol,
                    'timeframe': s.timeframe,
                    'pattern': s.pattern_type.value,
                    'stage': s.stage.value,
                    'confidence': s.confidence,
                    'entry': s.entry_price,
                    'stop_loss': s.stop_loss,
                    'take_profit_1': s.take_profit_1,
                    'take_profit_2': s.take_profit_2,
                    'risk_reward': s.risk_reward_ratio
                }
                for s in self.active_signals.values()
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"📁 Señales exportadas a {filename}")

async def main():
    """Función principal"""
    
    # Solicitar modo al usuario
    print("\n🤖 BotphIA - Monitor de Señales Multi-Timeframe")
    print("="*50)
    print("Selecciona el modo de operación:")
    print("1. Agresivo - Notifica todas las señales")
    print("2. Balanceado - Balance entre cantidad y calidad")
    print("3. Conservador - Solo señales de alta confianza")
    print("="*50)
    
    choice = input("Selección (1-3) [2]: ").strip() or "2"
    
    modes = {
        "1": MonitorMode.AGGRESSIVE,
        "2": MonitorMode.BALANCED,
        "3": MonitorMode.CONSERVATIVE
    }
    
    mode = modes.get(choice, MonitorMode.BALANCED)
    
    # Crear y ejecutar monitor
    monitor = RealTimeSignalMonitor(mode=mode)
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo monitor...")
        monitor.stop()
        
        # Preguntar si exportar señales
        export = input("\n¿Exportar señales detectadas? (s/n): ").strip().lower()
        if export == 's':
            monitor.export_signals()

if __name__ == "__main__":
    asyncio.run(main())