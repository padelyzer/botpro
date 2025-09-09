#!/usr/bin/env python3
"""
SISTEMA DE TRADING CONTINUO - BotphIA
Ejecutor principal para operación 24/7
"""

import asyncio
import aiohttp
import subprocess
import signal
import sys
import time
import logging
from datetime import datetime
import os
from pathlib import Path

# Import error handling system
from .error_handler import handle_api_error, NetworkError

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_operation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSystemManager:
    """Gestor principal del sistema de trading continuo"""
    
    def __init__(self):
        self.processes = {}
        self.running = False
        self.restart_count = {}
        self.max_restarts = 5
        
    async def start_signal_generator(self):
        """Inicia el generador de señales"""
        try:
            logger.info("🚀 Iniciando generador de señales...")
            process = await asyncio.create_subprocess_exec(
                sys.executable, 'signal_generator.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.processes['signal_generator'] = process
            
            # Monitor output
            asyncio.create_task(self.monitor_process('signal_generator', process))
            
            logger.info("✅ Generador de señales iniciado (PID: %d)", process.pid)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando generador de señales: {e}")
            return False
    
    async def start_database_maintenance(self):
        """Inicia el mantenimiento automático de base de datos"""
        while self.running:
            try:
                logger.info("🧹 Ejecutando mantenimiento de base de datos...")
                
                # Ejecutar mantenimiento
                process = await asyncio.create_subprocess_exec(
                    sys.executable, '-c',
                    """
from database_maintenance import DatabaseMaintenance
maintenance = DatabaseMaintenance()
maintenance.run_maintenance()
print('✅ Mantenimiento completado')
                    """,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.wait()
                
                # Esperar 1 hora hasta el próximo mantenimiento
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"❌ Error en mantenimiento: {e}")
                await asyncio.sleep(60)  # Reintentar en 1 minuto
    
    async def start_alert_monitor(self):
        """Monitor de alertas de alta calidad"""
        while self.running:
            try:
                # Verificar alertas cada 30 segundos
                process = await asyncio.create_subprocess_exec(
                    sys.executable, '-c',
                    """
import sys
sys.path.append('/Users/ja/saby/trading_api')
from quality_alert_system import get_quality_alert_system
alert_system = get_quality_alert_system()
stats = alert_system.get_alert_stats()
if stats['total_alerts_24h'] > 0:
    print(f"🚨 {stats['total_alerts_24h']} alertas de calidad en 24h")
                    """,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                if stdout:
                    logger.info(stdout.decode().strip())
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error en monitor de alertas: {e}")
                await asyncio.sleep(30)
    
    async def monitor_process(self, name: str, process: asyncio.subprocess.Process):
        """Monitorea un proceso y lo reinicia si falla"""
        while self.running:
            try:
                # Leer output del proceso
                stdout = await process.stdout.readline()
                if stdout:
                    logger.info(f"[{name}] {stdout.decode().strip()}")
                
                # Verificar si el proceso sigue vivo
                if process.returncode is not None:
                    logger.warning(f"⚠️ Proceso {name} terminado con código {process.returncode}")
                    
                    # Intentar reiniciar
                    if self.restart_count.get(name, 0) < self.max_restarts:
                        self.restart_count[name] = self.restart_count.get(name, 0) + 1
                        logger.info(f"🔄 Reiniciando {name} (intento {self.restart_count[name]})")
                        
                        await asyncio.sleep(5)  # Esperar antes de reiniciar
                        
                        if name == 'signal_generator':
                            await self.start_signal_generator()
                    else:
                        logger.error(f"❌ {name} falló demasiadas veces. Deteniendo monitoreo.")
                        break
                        
            except Exception as e:
                logger.error(f"Error monitoreando {name}: {e}")
                await asyncio.sleep(1)
    
    async def health_check(self):
        """Verificación periódica de salud del sistema"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check cada minuto
                
                logger.info("🏥 Health Check:")
                
                # Verificar procesos
                for name, process in self.processes.items():
                    if process.returncode is None:
                        logger.info(f"  ✅ {name}: Activo (PID: {process.pid})")
                    else:
                        logger.warning(f"  ❌ {name}: Inactivo")
                
                # Verificar APIs
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get('http://localhost:8000/api/signals/BTCUSDT', timeout=5) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                logger.info(f"  ✅ API: Respondiendo (BTCUSDT: {data['consensus']['action']})")
                            else:
                                logger.warning(f"  ⚠️ API: Status {resp.status}")
                    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                        handle_api_error(NetworkError(
                            message="API health check failed",
                            context={'endpoint': 'http://localhost:8000/api/signals/BTCUSDT'}
                        ))
                        logger.warning("  ⚠️ API: No responde")
                    except Exception as e:
                        handle_api_error(e, {
                            'operation': 'api_health_check',
                            'endpoint': 'http://localhost:8000/api/signals/BTCUSDT'
                        })
                        logger.warning("  ⚠️ API: Error inesperado")
                
                # Verificar espacio en disco
                import shutil
                total, used, free = shutil.disk_usage("/")
                free_gb = free // (2**30)
                if free_gb < 1:
                    logger.warning(f"  ⚠️ Espacio en disco bajo: {free_gb}GB")
                else:
                    logger.info(f"  ✅ Espacio en disco: {free_gb}GB libres")
                    
            except Exception as e:
                logger.error(f"Error en health check: {e}")
    
    async def run(self):
        """Ejecuta el sistema completo"""
        self.running = True
        
        logger.info("="*60)
        logger.info("🚀 INICIANDO SISTEMA DE TRADING CONTINUO")
        logger.info("="*60)
        
        # Iniciar componentes
        tasks = [
            self.start_signal_generator(),
            self.start_database_maintenance(),
            self.start_alert_monitor(),
            self.health_check()
        ]
        
        try:
            # Ejecutar todas las tareas concurrentemente
            await asyncio.gather(*[asyncio.create_task(task) for task in tasks])
            
        except KeyboardInterrupt:
            logger.info("⏹️ Deteniendo sistema...")
            await self.shutdown()
        except Exception as e:
            logger.error(f"❌ Error crítico: {e}")
            await self.shutdown()
    
    async def shutdown(self):
        """Apaga el sistema ordenadamente"""
        logger.info("🛑 Iniciando apagado ordenado...")
        self.running = False
        
        # Terminar procesos
        for name, process in self.processes.items():
            if process.returncode is None:
                logger.info(f"Terminando {name}...")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Forzando terminación de {name}")
                    process.kill()
        
        logger.info("✅ Sistema detenido correctamente")

def signal_handler(signum, frame):
    """Maneja señales del sistema"""
    logger.info(f"📡 Señal recibida: {signum}")
    sys.exit(0)

if __name__ == "__main__":
    # Configurar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Crear y ejecutar el gestor
    manager = TradingSystemManager()
    
    try:
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        logger.info("👋 Sistema detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)