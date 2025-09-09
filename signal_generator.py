#!/usr/bin/env python3
"""
SIGNAL GENERATOR - BotphIA
Generación continua y optimizada de señales de trading
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import random

from philosophers import get_trading_system
from philosophers_extended import register_extended_philosophers
from binance_integration import BinanceConnector
from database_maintenance import DatabaseMaintenance
from pinescript_generator import PineScriptGenerator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.connector = BinanceConnector(testnet=True)
        # Obtener sistema global y registrar filósofos extendidos
        register_extended_philosophers()
        self.trading_system = get_trading_system()
        self.maintenance = DatabaseMaintenance(db_path)
        self.pinescript_generator = PineScriptGenerator()
        
        # Configuración mejorada
        from enhanced_trading_config import get_enhanced_config
        from quality_alert_system import get_quality_alert_system
        
        self.config = get_enhanced_config()
        self.alert_system = get_quality_alert_system()
        
        self.symbols = self.config.get_active_symbols(15)  # Top 15 símbolos activos
        self.signal_interval = 60  # Generar señales cada 60 segundos
        self.maintenance_interval = 3600  # Mantenimiento cada hora
        self.max_positions_per_symbol = 1
        self.min_confidence_threshold = 45  # Sincronizado con market analyzer
        self.high_quality_threshold = 80  # Para alertas especiales
        
        # Estado
        self.last_signal_time = {}
        self.last_maintenance = datetime.now()
        
    def connect_db(self):
        """Conectar a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def check_existing_position(self, symbol: str) -> bool:
        """Verificar si ya existe una posición abierta para el símbolo"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM positions 
            WHERE symbol = ? AND status = 'OPEN'
        """, (symbol,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count >= self.max_positions_per_symbol
    
    def check_recent_signal(self, symbol: str, philosopher: str, minutes: int = 5) -> bool:
        """Verificar si ya existe una señal reciente del mismo filósofo"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*) FROM signals 
            WHERE symbol = ? 
            AND philosopher = ? 
            AND timestamp > ?
        """, (symbol, philosopher, cutoff_time))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def save_signal(self, signal: Dict):
        """Guardar señal en la base de datos"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO signals (
                    id, symbol, action, confidence, entry_price,
                    stop_loss, take_profit, philosopher, timestamp,
                    reasoning, market_trend, rsi, volume_ratio,
                    pinescript, pinescript_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal['id'],
                signal['symbol'],
                signal['action'],
                signal['confidence'],
                signal['entry_price'],
                signal.get('stop_loss', 0),
                signal.get('take_profit', 0),
                signal['philosopher'],
                signal['timestamp'],
                # Convert reasoning list to string if necessary
                ' '.join(signal.get('reasoning', [])) if isinstance(signal.get('reasoning'), list) else signal.get('reasoning', ''),
                signal.get('market_trend', ''),
                signal.get('rsi', 0),
                signal.get('volume_ratio', 0),
                signal.get('pinescript', ''),
                signal.get('pinescript_file', '')
            ))
            
            conn.commit()
            logger.info(f"✅ Señal guardada: {signal['symbol']} - {signal['action']} - {signal['philosopher']} ({signal['confidence']}%)")
            
        except sqlite3.IntegrityError:
            logger.warning(f"⚠️ Señal duplicada ignorada: {signal['id']}")
        except Exception as e:
            logger.error(f"❌ Error guardando señal: {e}")
        finally:
            conn.close()
    
    async def generate_signals_for_symbol(self, symbol: str):
        """Generar señales para un símbolo específico"""
        try:
            # Incrementar contador de análisis
            from system_stats import get_system_stats
            from signal_pipeline import get_signal_pipeline
            stats = get_system_stats()
            pipeline = get_signal_pipeline()
            
            # Verificar si ya hay posición abierta
            if self.check_existing_position(symbol):
                logger.debug(f"⏭️ {symbol}: Ya existe posición abierta")
                return
            
            # Obtener datos del mercado usando API optimizada
            df = self.connector.get_historical_data(symbol, timeframe='15m', limit=100)
            if df.empty or len(df) < 50:
                logger.warning(f"⚠️ Datos insuficientes para {symbol}")
                return
            
            # Contar puntos de datos procesados
            data_points = len(df) * 6  # 6 columnas típicas: OHLCV + timestamp
            stats.increment_analysis(symbol=symbol, data_points=data_points)
            
            # Convertir DataFrame a formato klines para compatibilidad
            klines = []
            for _, row in df.iterrows():
                klines.append([
                    int(row.name.timestamp() * 1000) if hasattr(row.name, 'timestamp') else 0,  # timestamp
                    float(row['open']),     # open
                    float(row['high']),     # high  
                    float(row['low']),      # low
                    float(row['close']),    # close
                    float(row['volume']),   # volume
                ])
            
            current_price = float(df['close'].iloc[-1])
            
            # Generar señales de cada filósofo
            philosophers = list(self.trading_system.philosophers.keys())
            random.shuffle(philosophers)  # Aleatorizar orden
            
            for philosopher_name in philosophers[:3]:  # Solo top 3 filósofos por símbolo
                # Verificar señal reciente
                if self.check_recent_signal(symbol, philosopher_name):
                    continue
                
                philosopher = self.trading_system.philosophers[philosopher_name]
                
                # Generar análisis usando DataFrame
                analysis = philosopher.analyze_market(df)
                
                if analysis and analysis.get('opportunity', False) and analysis.get('confidence', 0) * 100 >= self.min_confidence_threshold:
                    # Calcular SL y TP
                    if analysis['action'] == 'BUY':
                        stop_loss = current_price * 0.98
                        take_profit = current_price * 1.03
                    else:
                        stop_loss = current_price * 1.02
                        take_profit = current_price * 0.97
                    
                    # Crear señal
                    signal = {
                        'id': f"{philosopher_name}_{symbol}_{datetime.now().timestamp()}",
                        'symbol': symbol,
                        'action': analysis['action'],
                        'confidence': analysis['confidence'] * 100,  # Convert to percentage
                        'entry_price': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'philosopher': philosopher_name,
                        'timestamp': datetime.now().isoformat(),
                        'reasoning': analysis.get('reasoning', ''),
                        'market_trend': analysis.get('trend', 'NEUTRAL'),
                        'rsi': analysis.get('rsi', 50),
                        'volume_ratio': analysis.get('volume_ratio', 1.0)
                    }
                    
                    # PIPELINE DE VALIDACIÓN
                    # Preparar datos para validación
                    prices = df['close'].tolist()
                    high = df['high'].tolist()
                    low = df['low'].tolist()
                    volume = df['volume'].tolist()
                    
                    # Ejecutar pipeline de validación
                    evaluation = pipeline.validate_signal(signal, prices, high, low, volume)
                    
                    # Solo procesar si la señal es válida
                    if not evaluation.is_valid:
                        logger.warning(f"🚫 Señal rechazada por pipeline: {symbol} - {philosopher_name}")
                        logger.debug(f"   Razón: {', '.join(evaluation.recommendations)}")
                        stats.increment_analysis(philosopher=philosopher_name)
                        continue
                    
                    # Actualizar confianza basada en el score del pipeline
                    signal['confidence'] = min(signal['confidence'], evaluation.final_score)
                    signal['validation_score'] = evaluation.final_score
                    signal['execution_priority'] = evaluation.execution_priority
                    
                    # Generar Pine Script para la señal
                    try:
                        pinescript_code = self.pinescript_generator.generate_signal_script(signal)
                        signal['pinescript'] = pinescript_code
                        
                        # Guardar el script en un archivo temporal
                        script_filename = f"{symbol}_{philosopher_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
                        script_path = self.pinescript_generator.save_to_file(pinescript_code, script_filename)
                        signal['pinescript_file'] = script_path
                        
                        logger.info(f"📊 Pine Script generado: {script_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo generar Pine Script: {e}")
                        signal['pinescript'] = None
                        signal['pinescript_file'] = None
                    
                    # Procesar alerta de calidad ANTES de guardar
                    alert_generated = self.alert_system.process_signal(signal)
                    
                    # Guardar señal validada
                    self.save_signal(signal)
                    
                    # Incrementar contador de señales
                    stats.increment_signal(
                        symbol=symbol,
                        philosopher=philosopher_name,
                        is_high_quality=(analysis['confidence'] >= 80)
                    )
                    stats.increment_analysis(philosopher=philosopher_name)
                    
                    # Log de señal con indicador de alerta
                    alert_indicator = "🚨" if alert_generated else "📊"
                    logger.info(f"{alert_indicator} Señal: {symbol} - {philosopher_name} - {analysis['action']} - {analysis['confidence']}%")
                    
                    # Esperar un poco entre filósofos
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"❌ Error generando señales para {symbol}: {e}")
    
    async def generate_signals_batch(self):
        """Generar señales para todos los símbolos"""
        logger.info("🔄 Generando nuevas señales...")
        
        tasks = []
        for symbol in self.symbols:
            tasks.append(self.generate_signals_for_symbol(symbol))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Actualizar timestamp
        self.last_signal_time = {symbol: datetime.now() for symbol in self.symbols}
    
    async def run_maintenance(self):
        """Ejecutar mantenimiento de base de datos"""
        logger.info("🧹 Ejecutando mantenimiento...")
        
        try:
            # Ejecutar en thread separado para no bloquear
            await asyncio.get_event_loop().run_in_executor(
                None, self.maintenance.run_maintenance
            )
            self.last_maintenance = datetime.now()
        except Exception as e:
            logger.error(f"❌ Error en mantenimiento: {e}")
    
    async def run_forever(self):
        """Ejecutar generador de señales continuamente"""
        logger.info("🚀 Iniciando generador de señales continuo...")
        
        while True:
            try:
                # Generar señales
                await self.generate_signals_batch()
                
                # Verificar si es hora de mantenimiento
                if (datetime.now() - self.last_maintenance).seconds >= self.maintenance_interval:
                    await self.run_maintenance()
                
                # Esperar hasta el próximo ciclo
                await asyncio.sleep(self.signal_interval)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Deteniendo generador de señales...")
                break
            except Exception as e:
                logger.error(f"❌ Error en bucle principal: {e}")
                await asyncio.sleep(10)  # Esperar antes de reintentar

def main():
    """Función principal"""
    generator = SignalGenerator()
    
    try:
        # Ejecutar generador
        asyncio.run(generator.run_forever())
    except KeyboardInterrupt:
        logger.info("👋 Generador de señales detenido")

if __name__ == "__main__":
    main()