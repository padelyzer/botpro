#!/usr/bin/env python3
"""
Script para actualizar la tabla de señales con campos de Pine Script
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_signals_table(db_path: str = "trading_bot.db"):
    """Actualiza la tabla signals para incluir campos de Pine Script"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(signals)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Agregar columna pinescript si no existe
        if 'pinescript' not in columns:
            cursor.execute("""
                ALTER TABLE signals 
                ADD COLUMN pinescript TEXT
            """)
            logger.info("✅ Columna 'pinescript' agregada a la tabla signals")
        else:
            logger.info("ℹ️ Columna 'pinescript' ya existe")
            
        # Agregar columna pinescript_file si no existe
        if 'pinescript_file' not in columns:
            cursor.execute("""
                ALTER TABLE signals 
                ADD COLUMN pinescript_file TEXT
            """)
            logger.info("✅ Columna 'pinescript_file' agregada a la tabla signals")
        else:
            logger.info("ℹ️ Columna 'pinescript_file' ya existe")
            
        conn.commit()
        logger.info("✅ Tabla signals actualizada correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error actualizando tabla: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_signals_table()