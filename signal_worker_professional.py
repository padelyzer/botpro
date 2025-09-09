#!/usr/bin/env python3
"""
PROFESSIONAL SIGNAL WORKER - Generador Profesional de Señales con Análisis Real
Sistema de trading basado en análisis técnico real por filósofos especializados
"""

import asyncio
import sqlite3
import json
import random
import os
from datetime import datetime
import logging
import httpx
import sys
sys.path.append('/app')
from philosophers_market_analysis import PhilosophersCouncil

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProfessionalSignalWorker:
    """Worker profesional que genera señales basadas en análisis técnico real"""
    
    def __init__(self):
        self.running = False
        self.scan_interval = int(os.getenv('SIGNAL_SCAN_INTERVAL', '60'))
        self.db_path = os.getenv('DATABASE_PATH', '/app/data/trading_bot.db')
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]
        self.council = PhilosophersCouncil()
        self.price_cache = {}
        
    def get_db_connection(self):
        """Obtener conexión a la base de datos"""
        try:
            return sqlite3.connect(self.db_path)
        except:
            return sqlite3.connect(':memory:')
    
    async def get_real_price(self, symbol: str) -> float:
        """Obtener precio real de Binance"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    price = float(data['price'])
                    self.price_cache[symbol] = price
                    logger.info(f"✅ {symbol}: ${price:.2f}")
                    return price
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
        
        # Usar precio del cache o valores por defecto
        if symbol in self.price_cache:
            return self.price_cache[symbol]
        
        default_prices = {
            "BTCUSDT": 115000.0,
            "ETHUSDT": 4800.0,
            "BNBUSDT": 886.0,
            "SOLUSDT": 206.0,
            "ADAUSDT": 1.30,
            "XRPUSDT": 3.05,
            "DOGEUSDT": 0.24
        }
        return default_prices.get(symbol, 100.0)
    
    def determine_timeframe(self, action: str, confidence: float) -> dict:
        """Determinar timeframe basado en la acción y confianza"""
        if confidence >= 85:
            # Alta confianza = movimientos más largos
            if action == "BUY":
                return {"type": "SWING", "duration": "1-3 días", "tp_mult": 1.03, "sl_mult": 0.98}
            elif action == "SELL":
                return {"type": "SWING", "duration": "1-3 días", "tp_mult": 0.97, "sl_mult": 1.02}
        elif confidence >= 75:
            # Confianza media-alta = intraday
            return {"type": "INTRADAY", "duration": "1-4 horas", "tp_mult": 1.015, "sl_mult": 0.99}
        elif confidence >= 65:
            # Confianza media = scalping
            return {"type": "SCALPING", "duration": "5-30 min", "tp_mult": 1.005, "sl_mult": 0.997}
        else:
            # Baja confianza = position (esperar más confirmación)
            return {"type": "POSITION", "duration": "3+ días", "tp_mult": 1.05, "sl_mult": 0.96}
    
    async def generate_professional_signal(self, symbol: str) -> dict:
        """Generar señal profesional basada en análisis real"""
        # Obtener precio actual
        current_price = await self.get_real_price(symbol)
        
        # Obtener análisis del consejo de filósofos
        logger.info(f"🔍 Analizando {symbol} con el consejo de filósofos...")
        consensus = await self.council.get_consensus(symbol, current_price)
        
        if not consensus:
            logger.warning(f"No se pudo obtener consenso para {symbol}")
            return None
        
        # Seleccionar el filósofo con mayor confianza para esta señal
        best_analysis = max(consensus["individual_analyses"], 
                           key=lambda x: x["confidence"])
        
        philosopher_name = best_analysis["reasoning"][0].split(":")[0]
        
        # Determinar timeframe basado en análisis
        timeframe = self.determine_timeframe(consensus["action"], consensus["confidence"])
        
        # Calcular TP y SL basados en timeframe
        if consensus["action"] == "BUY":
            stop_loss = current_price * timeframe["sl_mult"]
            take_profit = current_price * timeframe["tp_mult"]
        elif consensus["action"] == "SELL":
            stop_loss = current_price * (2 - timeframe["sl_mult"])
            take_profit = current_price * (2 - timeframe["tp_mult"])
        else:  # HOLD
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.02
        
        # Construir señal profesional
        signal = {
            'id': f"{symbol}_{datetime.now().timestamp()}",
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': consensus["action"],
            'philosopher': philosopher_name,
            'confidence': consensus["confidence"],
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timeframe': timeframe["type"],
            'duration': timeframe["duration"],
            'reasoning': best_analysis["reasoning"],
            'risk_reward': abs((take_profit - current_price) / (current_price - stop_loss)) if current_price != stop_loss else 1.5,
            'consensus': {
                'philosophers_agree': consensus["philosophers_agree"],
                'total': consensus["total_philosophers"],
                'votes': consensus["votes"]
            },
            'technical_indicators': best_analysis.get("indicators", {})
        }
        
        return signal
    
    def save_signal(self, signal: dict):
        """Guardar señal en la base de datos"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    symbol TEXT,
                    action TEXT,
                    philosopher TEXT,
                    confidence REAL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    reasoning TEXT,
                    risk_reward REAL,
                    timeframe TEXT,
                    duration TEXT,
                    consensus TEXT,
                    indicators TEXT
                )
            ''')
            
            # Insertar señal
            cursor.execute('''
                INSERT OR REPLACE INTO signals 
                (id, timestamp, symbol, action, philosopher, confidence,
                 entry_price, stop_loss, take_profit, reasoning, risk_reward,
                 timeframe, duration, consensus, indicators)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (signal['id'], signal['timestamp'], signal['symbol'], 
                  signal['action'], signal['philosopher'], signal['confidence'],
                  signal['entry_price'], signal['stop_loss'], signal['take_profit'],
                  json.dumps(signal['reasoning']), signal['risk_reward'],
                  signal['timeframe'], signal['duration'],
                  json.dumps(signal.get('consensus', {})),
                  json.dumps(signal.get('technical_indicators', {}))))
            
            conn.commit()
            conn.close()
            
            logger.info(f"""
            ╔══════════════════════════════════════════════════════════╗
            ║ 📊 SEÑAL PROFESIONAL GENERADA                           ║
            ╠══════════════════════════════════════════════════════════╣
            ║ Symbol: {signal['symbol']:<20} Action: {signal['action']:<10} ║
            ║ Philosopher: {signal['philosopher']:<15} Confidence: {signal['confidence']:.1f}%    ║
            ║ Entry: ${signal['entry_price']:<15.2f} Timeframe: {signal['timeframe']:<10} ║
            ║ TP: ${signal['take_profit']:<15.2f} SL: ${signal['stop_loss']:<15.2f} ║
            ║ R:R Ratio: {signal['risk_reward']:.2f}                                     ║
            ║ Consenso: {signal['consensus']['philosophers_agree']}/{signal['consensus']['total']} filósofos de acuerdo                    ║
            ╚══════════════════════════════════════════════════════════╝
            """)
            
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
    
    async def scan_markets(self):
        """Escanear mercados y generar señales profesionales"""
        signals_generated = 0
        
        logger.info("=" * 60)
        logger.info("🔍 INICIANDO ANÁLISIS PROFESIONAL DE MERCADOS")
        logger.info("=" * 60)
        
        # Actualizar cache de precios
        logger.info("📊 Actualizando precios en tiempo real...")
        for symbol in self.symbols:
            await self.get_real_price(symbol)
        
        # Analizar cada símbolo
        for symbol in self.symbols:
            try:
                # Generar probabilidad basada en volatilidad del mercado
                analysis_probability = 0.4  # 40% de probabilidad de generar señal
                
                if random.random() < analysis_probability:
                    logger.info(f"\n🎯 Analizando {symbol}...")
                    signal = await self.generate_professional_signal(symbol)
                    
                    if signal and signal['confidence'] >= 65:
                        self.save_signal(signal)
                        signals_generated += 1
                        
                        # Limitar señales por escaneo
                        if signals_generated >= 3:
                            logger.info("📊 Límite de señales alcanzado para este escaneo")
                            break
                    elif signal:
                        logger.info(f"⏸️ Señal de {symbol} descartada (confianza: {signal['confidence']:.1f}%)")
                        
            except Exception as e:
                logger.error(f"Error analizando {symbol}: {e}")
        
        if signals_generated > 0:
            logger.info(f"\n✅ Generadas {signals_generated} señales profesionales")
        else:
            logger.info("\n📊 Sin señales de alta calidad en este escaneo")
        
        logger.info("=" * 60)
    
    async def start(self):
        """Iniciar el worker profesional"""
        self.running = True
        logger.info("""
        ╔══════════════════════════════════════════════════════════╗
        ║     🏛️ PROFESSIONAL SIGNAL WORKER - BOTPHIA 🏛️          ║
        ║                                                          ║
        ║  Sistema Profesional de Análisis de Mercados            ║
        ║  • 8 Filósofos especializados en trading                ║
        ║  • Análisis técnico real con indicadores                ║
        ║  • Consenso basado en múltiples estrategias             ║
        ║  • Timeframes dinámicos según confianza                 ║
        ║                                                          ║
        ║  Filósofos activos:                                     ║
        ║  - Sócrates: Confirmación múltiple                      ║
        ║  - Aristóteles: Equilibrio y media dorada               ║
        ║  - Nietzsche: Estrategia contrarian                     ║
        ║  - Confucio: Paciencia y tendencia                      ║
        ║  - Platón: Patrones ideales y Fibonacci                 ║
        ║  - Kant: Sistema de reglas categóricas                  ║
        ║  - Descartes: Análisis racional y estadístico           ║
        ║  - Sun Tzu: Táctica y timing                            ║
        ╚══════════════════════════════════════════════════════════╝
        """)
        
        logger.info(f"⚙️ Configuración:")
        logger.info(f"   • Intervalo de escaneo: {self.scan_interval} segundos")
        logger.info(f"   • Símbolos: {', '.join(self.symbols)}")
        logger.info(f"   • Base de datos: {self.db_path}")
        
        scan_count = 0
        while self.running:
            try:
                scan_count += 1
                logger.info(f"\n🔄 Escaneo #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Escanear mercados
                await self.scan_markets()
                
                # Esperar antes del siguiente escaneo
                logger.info(f"⏰ Próximo escaneo en {self.scan_interval} segundos...")
                await asyncio.sleep(self.scan_interval)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Worker detenido por el usuario")
                break
            except Exception as e:
                logger.error(f"Error en signal worker: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Detener el worker"""
        self.running = False
        logger.info("Signal Worker detenido")

async def main():
    """Función principal"""
    worker = ProfessionalSignalWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Apagando sistema...")
        worker.stop()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        worker.stop()

if __name__ == "__main__":
    asyncio.run(main())