#!/usr/bin/env python3
"""
DATABASE MAINTENANCE - BotphIA
Limpieza periódica y optimización de la base de datos
"""

import sqlite3
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMaintenance:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.max_signals = 500  # Mantener últimas 500 señales
        self.max_signal_age_days = 7  # Eliminar señales más antiguas de 7 días
        self.max_positions_per_symbol = 1  # Solo 1 posición por símbolo
        
    def connect(self):
        """Conectar a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def clean_old_signals(self, conn: sqlite3.Connection) -> int:
        """Limpiar señales antiguas"""
        cursor = conn.cursor()
        
        # Contar señales antes de limpiar
        cursor.execute("SELECT COUNT(*) FROM signals")
        before_count = cursor.fetchone()[0]
        
        # Eliminar señales más antiguas de X días
        cutoff_date = (datetime.now() - timedelta(days=self.max_signal_age_days)).isoformat()
        cursor.execute("""
            DELETE FROM signals 
            WHERE timestamp < ? 
            AND id NOT IN (
                SELECT id FROM signals 
                ORDER BY timestamp DESC 
                LIMIT ?
            )
        """, (cutoff_date, self.max_signals))
        
        # Contar señales después
        cursor.execute("SELECT COUNT(*) FROM signals")
        after_count = cursor.fetchone()[0]
        
        deleted = before_count - after_count
        if deleted > 0:
            logger.info(f"✅ Eliminadas {deleted} señales antiguas")
            
        return deleted
    
    def remove_duplicate_positions(self, conn: sqlite3.Connection) -> int:
        """Eliminar posiciones duplicadas por símbolo"""
        cursor = conn.cursor()
        
        # Contar duplicados
        cursor.execute("""
            SELECT symbol, COUNT(*) as count 
            FROM positions 
            WHERE status = 'OPEN'
            GROUP BY symbol 
            HAVING count > ?
        """, (self.max_positions_per_symbol,))
        
        duplicates = cursor.fetchall()
        total_removed = 0
        
        for symbol, count in duplicates:
            excess = count - self.max_positions_per_symbol
            
            # Cerrar las posiciones más antiguas
            cursor.execute("""
                UPDATE positions 
                SET status = 'CLOSED', 
                    current_price = entry_price,
                    close_time = datetime('now'),
                    pnl = 0,
                    pnl_percentage = 0
                WHERE id IN (
                    SELECT id FROM positions 
                    WHERE symbol = ? AND status = 'OPEN'
                    ORDER BY open_time ASC
                    LIMIT ?
                )
            """, (symbol, excess))
            
            total_removed += excess
            logger.info(f"⚠️ Cerradas {excess} posiciones duplicadas de {symbol}")
        
        return total_removed
    
    def clean_closed_positions(self, conn: sqlite3.Connection, keep_days: int = 30) -> int:
        """Eliminar posiciones cerradas antiguas"""
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).isoformat()
        
        cursor.execute("""
            DELETE FROM positions 
            WHERE status = 'CLOSED' 
            AND close_time < ?
        """, (cutoff_date,))
        
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"🗑️ Eliminadas {deleted} posiciones cerradas antiguas")
            
        return deleted
    
    def optimize_database(self, conn: sqlite3.Connection):
        """Optimizar la base de datos"""
        cursor = conn.cursor()
        
        # Vacuum para recuperar espacio
        cursor.execute("VACUUM")
        
        # Analyze para actualizar estadísticas
        cursor.execute("ANALYZE")
        
        logger.info("🔧 Base de datos optimizada")
    
    def get_database_stats(self, conn: sqlite3.Connection) -> dict:
        """Obtener estadísticas de la base de datos"""
        cursor = conn.cursor()
        
        stats = {}
        
        # Contar registros
        for table in ['positions', 'signals', 'signal_analysis', 'philosopher_performance']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f'{table}_count'] = cursor.fetchone()[0]
        
        # Tamaño de la base de datos
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        stats['db_size_bytes'] = cursor.fetchone()[0]
        stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)
        
        return stats
    
    def run_maintenance(self):
        """Ejecutar mantenimiento completo"""
        logger.info("🚀 Iniciando mantenimiento de base de datos...")
        
        try:
            conn = self.connect()
            
            # Obtener stats iniciales
            stats_before = self.get_database_stats(conn)
            logger.info(f"📊 Estado inicial: {stats_before['db_size_mb']} MB")
            
            # Ejecutar limpieza
            self.clean_old_signals(conn)
            self.remove_duplicate_positions(conn)
            self.clean_closed_positions(conn)
            
            # Commit cambios
            conn.commit()
            
            # Optimizar
            self.optimize_database(conn)
            
            # Stats finales
            stats_after = self.get_database_stats(conn)
            logger.info(f"📊 Estado final: {stats_after['db_size_mb']} MB")
            
            # Resumen
            logger.info(f"""
            ========== RESUMEN MANTENIMIENTO ==========
            Señales: {stats_before['signals_count']} → {stats_after['signals_count']}
            Posiciones: {stats_before['positions_count']} → {stats_after['positions_count']}
            Tamaño DB: {stats_before['db_size_mb']} MB → {stats_after['db_size_mb']} MB
            Espacio liberado: {stats_before['db_size_mb'] - stats_after['db_size_mb']:.2f} MB
            ==========================================
            """)
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en mantenimiento: {e}")
            return False

async def periodic_maintenance(interval_hours: int = 1):
    """Ejecutar mantenimiento periódicamente"""
    maintenance = DatabaseMaintenance()
    
    while True:
        try:
            # Ejecutar mantenimiento
            maintenance.run_maintenance()
            
            # Esperar hasta la próxima ejecución
            await asyncio.sleep(interval_hours * 3600)
            
        except Exception as e:
            logger.error(f"Error en mantenimiento periódico: {e}")
            await asyncio.sleep(300)  # Reintentar en 5 minutos

if __name__ == "__main__":
    # Ejecutar mantenimiento inmediato
    maintenance = DatabaseMaintenance()
    maintenance.run_maintenance()
    
    # Si quieres ejecutar periódicamente, descomenta:
    # asyncio.run(periodic_maintenance(interval_hours=1))