#!/usr/bin/env python3
"""
PRECISION SIGNAL MONITOR - BotphIA
Monitor de alta precisión para señales confiables 24/7
Solo notifica señales con alta probabilidad de éxito
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import os

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.text import Text

# Componentes del sistema
from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import (
    PatternDetector, Signal, PatternStage, PatternType,
    TRADING_PAIRS, TIMEFRAMES
)
from signal_notification_system import SignalNotificationManager
from terminal_signal_display import TerminalSignalDisplay

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('precision_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SignalQuality:
    """Métricas de calidad de una señal"""
    confidence: float
    volume_confirmation: bool
    trend_alignment: bool
    multiple_timeframe_confirmation: bool
    risk_reward_ratio: float
    overall_score: float

class PrecisionSignalMonitor:
    """Monitor de precisión para señales de alta calidad"""
    
    def __init__(self):
        self.console = Console()
        self.connector = BinanceConnector(testnet=False)
        self.detector = PatternDetector()
        self.notifier = SignalNotificationManager()
        self.display = TerminalSignalDisplay()
        
        # Configuración de precisión
        self.min_confidence = 65  # Solo señales con alta confianza
        self.min_risk_reward = 1.5  # Mínimo R:R ratio
        self.require_volume_confirmation = True
        self.require_trend_alignment = True
        
        # Estado del monitor
        self.is_running = True
        self.active_signals = {}
        self.confirmed_signals = []
        self.signal_history = []
        
        # Estadísticas
        self.stats = {
            'uptime_start': datetime.now(),
            'total_scans': 0,
            'signals_detected': 0,
            'signals_confirmed': 0,
            'false_positives': 0,
            'successful_signals': 0,
            'patterns_distribution': {},
            'best_performing_pairs': {}
        }
        
        # Cache de análisis
        self.market_analysis_cache = {}
        self.last_market_update = None
        
    async def analyze_market_context(self) -> Dict:
        """Analiza el contexto general del mercado"""
        
        # Actualizar cada 15 minutos
        if self.last_market_update and \
           (datetime.now() - self.last_market_update) < timedelta(minutes=15):
            return self.market_analysis_cache
        
        try:
            # Analizar BTC como indicador principal
            btc_1h = self.connector.get_historical_data("BTCUSDT", "1h", limit=48)
            btc_4h = self.connector.get_historical_data("BTCUSDT", "4h", limit=24)
            
            if not btc_1h.empty and not btc_4h.empty:
                # Calcular tendencia
                sma_20 = btc_1h['close'].rolling(20).mean().iloc[-1]
                sma_50 = btc_4h['close'].rolling(12).mean().iloc[-1]
                current_price = btc_1h['close'].iloc[-1]
                
                # Determinar tendencia del mercado
                if current_price > sma_20 and current_price > sma_50:
                    market_trend = "BULLISH"
                elif current_price < sma_20 and current_price < sma_50:
                    market_trend = "BEARISH"
                else:
                    market_trend = "NEUTRAL"
                
                # Calcular volatilidad
                returns = btc_1h['close'].pct_change().dropna()
                volatility = returns.std() * 100
                
                # Volumen
                avg_volume = btc_1h['volume'].mean()
                current_volume = btc_1h['volume'].iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                self.market_analysis_cache = {
                    'trend': market_trend,
                    'volatility': volatility,
                    'volume_ratio': volume_ratio,
                    'btc_price': current_price,
                    'timestamp': datetime.now()
                }
                
                self.last_market_update = datetime.now()
                
        except Exception as e:
            logger.error(f"Error analizando contexto del mercado: {e}")
            
        return self.market_analysis_cache
    
    def evaluate_signal_quality(self, signal: Signal, market_context: Dict) -> SignalQuality:
        """Evalúa la calidad de una señal"""
        
        # Verificar confirmación de volumen
        volume_confirmation = False
        if signal.notes and 'volume_ratio' in signal.notes:
            volume_confirmation = signal.notes['volume_ratio'] > 1.2
        
        # Verificar alineación con tendencia
        trend_alignment = False
        if market_context.get('trend'):
            bullish_patterns = [
                PatternType.DOUBLE_BOTTOM,
                PatternType.SUPPORT_BOUNCE,
                PatternType.BREAKOUT,
                PatternType.HAMMER,
                PatternType.ENGULFING_BULL
            ]
            
            bearish_patterns = [
                PatternType.DOUBLE_TOP,
                PatternType.RESISTANCE_REJECTION,
                PatternType.BREAKDOWN,
                PatternType.SHOOTING_STAR,
                PatternType.ENGULFING_BEAR
            ]
            
            if market_context['trend'] == "BULLISH":
                trend_alignment = signal.pattern_type in bullish_patterns
            elif market_context['trend'] == "BEARISH":
                trend_alignment = signal.pattern_type in bearish_patterns
            else:
                trend_alignment = True  # Neutral acepta todos
        
        # Verificar confirmación multi-timeframe
        multi_tf_confirmation = signal.stage == PatternStage.CONFIRMED
        
        # Calcular score general
        overall_score = 0.0
        
        # Peso de cada factor
        weights = {
            'confidence': 0.35,
            'volume': 0.20,
            'trend': 0.20,
            'multi_tf': 0.15,
            'risk_reward': 0.10
        }
        
        if signal.confidence >= self.min_confidence:
            overall_score += weights['confidence'] * (signal.confidence / 100)
        
        if volume_confirmation:
            overall_score += weights['volume']
            
        if trend_alignment:
            overall_score += weights['trend']
            
        if multi_tf_confirmation:
            overall_score += weights['multi_tf']
            
        if signal.risk_reward_ratio >= self.min_risk_reward:
            overall_score += weights['risk_reward'] * min(signal.risk_reward_ratio / 3, 1)
        
        return SignalQuality(
            confidence=signal.confidence,
            volume_confirmation=volume_confirmation,
            trend_alignment=trend_alignment,
            multiple_timeframe_confirmation=multi_tf_confirmation,
            risk_reward_ratio=signal.risk_reward_ratio,
            overall_score=overall_score * 100
        )
    
    async def scan_pair(self, symbol: str) -> List[Signal]:
        """Escanea un par en todos los timeframes"""
        
        high_quality_signals = []
        market_context = await self.analyze_market_context()
        
        for timeframe in TIMEFRAMES.keys():
            try:
                # Obtener datos
                df = self.connector.get_historical_data(
                    symbol,
                    timeframe=timeframe,
                    limit=TIMEFRAMES[timeframe]['bars']
                )
                
                if df.empty or len(df) < 50:
                    continue
                
                # Detectar patrones
                signals = self.detector.detect_all_patterns(df, symbol, timeframe)
                
                # Filtrar por calidad
                for signal in signals:
                    # Evaluar calidad
                    quality = self.evaluate_signal_quality(signal, market_context)
                    
                    # Solo aceptar señales de alta calidad
                    if quality.overall_score >= 65:  # 65% de score mínimo
                        signal.quality_score = quality.overall_score
                        signal.quality_metrics = quality
                        high_quality_signals.append(signal)
                        
                        logger.info(
                            f"📊 Señal de alta calidad: {symbol} {timeframe} "
                            f"{signal.pattern_type.value} - Score: {quality.overall_score:.1f}%"
                        )
                
            except Exception as e:
                logger.debug(f"Error escaneando {symbol} {timeframe}: {e}")
        
        return high_quality_signals
    
    async def continuous_scan(self):
        """Escaneo continuo de todos los pares"""
        
        while self.is_running:
            try:
                scan_start = datetime.now()
                all_signals = []
                
                # Escanear todos los pares
                for symbol in TRADING_PAIRS:
                    signals = await self.scan_pair(symbol)
                    all_signals.extend(signals)
                    
                    # Pequeña pausa para no sobrecargar API
                    await asyncio.sleep(0.5)
                
                # Procesar señales encontradas
                if all_signals:
                    await self.process_high_quality_signals(all_signals)
                
                # Actualizar estadísticas
                self.stats['total_scans'] += 1
                scan_duration = (datetime.now() - scan_start).total_seconds()
                
                logger.info(
                    f"✅ Escaneo #{self.stats['total_scans']} completado en {scan_duration:.1f}s - "
                    f"{len(all_signals)} señales de alta calidad"
                )
                
                # Mostrar estado actual
                self.display_current_state()
                
                # Esperar antes del próximo escaneo
                # Ajustar según timeframe más corto monitoreado
                await asyncio.sleep(60)  # Escanear cada minuto
                
            except Exception as e:
                logger.error(f"Error en escaneo continuo: {e}")
                await asyncio.sleep(30)
    
    async def process_high_quality_signals(self, signals: List[Signal]):
        """Procesa y notifica señales de alta calidad"""
        
        for signal in signals:
            signal_key = f"{signal.symbol}_{signal.pattern_type.value}_{signal.timeframe}"
            
            # Verificar si es señal nueva o actualización
            if signal_key not in self.active_signals:
                # Nueva señal de alta calidad
                self.active_signals[signal_key] = signal
                self.stats['signals_detected'] += 1
                
                # Actualizar distribución de patrones
                pattern_name = signal.pattern_type.value
                if pattern_name not in self.stats['patterns_distribution']:
                    self.stats['patterns_distribution'][pattern_name] = 0
                self.stats['patterns_distribution'][pattern_name] += 1
                
                # Si está confirmada, notificar
                if signal.stage == PatternStage.CONFIRMED:
                    self.confirmed_signals.append(signal)
                    self.stats['signals_confirmed'] += 1
                    await self.notifier.process_signal(signal)
                    
                    logger.info(
                        f"🎯 SEÑAL CONFIRMADA: {signal.symbol} - "
                        f"{signal.pattern_type.value} - "
                        f"Entry: ${signal.entry_price:.4f} - "
                        f"R:R: {signal.risk_reward_ratio:.2f}:1"
                    )
            else:
                # Actualizar señal existente si mejoró
                existing = self.active_signals[signal_key]
                if signal.stage.value > existing.stage.value:
                    self.active_signals[signal_key] = signal
                    
                    if signal.stage == PatternStage.CONFIRMED:
                        self.confirmed_signals.append(signal)
                        self.stats['signals_confirmed'] += 1
                        await self.notifier.process_signal(signal)
    
    def display_current_state(self):
        """Muestra el estado actual del monitor"""
        
        # Usar el display mejorado
        if self.confirmed_signals or self.active_signals:
            signals = list(self.active_signals.values())
            self.display.display_signals(signals, self.stats)
    
    def create_status_layout(self) -> Layout:
        """Crea layout de estado para visualización continua"""
        
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="signals", ratio=2),
            Layout(name="stats", size=10),
            Layout(name="footer", size=2)
        )
        
        # Header
        uptime = datetime.now() - self.stats['uptime_start']
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        
        header = Panel(
            Align.center(
                Text(
                    f"🤖 BotphIA Precision Monitor | "
                    f"Uptime: {hours}h {minutes}m | "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    style="bold cyan"
                )
            ),
            border_style="cyan"
        )
        layout["header"].update(header)
        
        # Señales confirmadas
        if self.confirmed_signals:
            signals_text = "📊 SEÑALES CONFIRMADAS:\n\n"
            for sig in self.confirmed_signals[-5:]:  # Últimas 5
                signals_text += f"✅ {sig.symbol} - {sig.pattern_type.value}\n"
                signals_text += f"   Entry: ${sig.entry_price:.4f} | "
                signals_text += f"R:R: {sig.risk_reward_ratio:.2f}:1\n\n"
        else:
            signals_text = "🔍 Monitoreando mercados...\nSin señales confirmadas aún"
        
        layout["signals"].update(Panel(Text(signals_text), border_style="green"))
        
        # Estadísticas
        stats_text = f"""
📊 Estadísticas:
  • Escaneos totales: {self.stats['total_scans']}
  • Señales detectadas: {self.stats['signals_detected']}
  • Señales confirmadas: {self.stats['signals_confirmed']}
  • Tasa de confirmación: {self.stats['signals_confirmed'] / max(self.stats['signals_detected'], 1) * 100:.1f}%
  
🎯 Configuración:
  • Confianza mínima: {self.min_confidence}%
  • R:R mínimo: {self.min_risk_reward}:1
  • Requiere volumen: {'Sí' if self.require_volume_confirmation else 'No'}
  • Requiere tendencia: {'Sí' if self.require_trend_alignment else 'No'}
"""
        
        layout["stats"].update(Panel(Text(stats_text.strip()), border_style="blue"))
        
        # Footer
        layout["footer"].update(
            Panel(
                Align.center(Text("Ctrl+C para detener", style="dim")),
                border_style="dim"
            )
        )
        
        return layout
    
    async def run(self):
        """Ejecuta el monitor de precisión"""
        
        self.console.print(Panel(
            "[bold cyan]🤖 BotphIA Precision Signal Monitor[/bold cyan]\n"
            "Monitor de alta precisión - Solo señales confiables\n"
            f"Confianza mínima: {self.min_confidence}% | R:R mínimo: {self.min_risk_reward}:1",
            expand=False,
            border_style="cyan"
        ))
        
        logger.info("🚀 Iniciando monitor de precisión...")
        
        # Crear tarea de escaneo
        scan_task = asyncio.create_task(self.continuous_scan())
        
        # Visualización en vivo
        try:
            with Live(self.create_status_layout(), refresh_per_second=1, console=self.console) as live:
                while self.is_running:
                    live.update(self.create_status_layout())
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.is_running = False
            scan_task.cancel()
            
        # Guardar estadísticas finales
        self.save_statistics()
        
        self.console.print("\n[bold green]Monitor detenido[/bold green]")
        self.console.print(f"Total señales confirmadas: {self.stats['signals_confirmed']}")
    
    def save_statistics(self):
        """Guarda estadísticas en archivo"""
        
        stats_file = f"precision_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(stats_file, 'w') as f:
            json.dump({
                'stats': self.stats,
                'confirmed_signals': [
                    {
                        'symbol': s.symbol,
                        'pattern': s.pattern_type.value,
                        'entry': s.entry_price,
                        'risk_reward': s.risk_reward_ratio,
                        'confidence': s.confidence
                    }
                    for s in self.confirmed_signals
                ]
            }, f, indent=2, default=str)
        
        logger.info(f"📁 Estadísticas guardadas en {stats_file}")

async def main():
    """Función principal"""
    
    monitor = PrecisionSignalMonitor()
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        print("\n⏹️ Monitor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    asyncio.run(main())