#!/usr/bin/env python3
"""
Production startup script for botphIA
Handles database migration from SQLite to PostgreSQL
"""

import os
import sys
import logging
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Setup PostgreSQL database for production"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.error("DATABASE_URL not set - using SQLite (not recommended for production)")
        return
    
    # Render.com provides postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        os.environ["DATABASE_URL"] = database_url
    
    logger.info("Database configured for PostgreSQL")
    
    # Create tables if they don't exist
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        result = urlparse(database_url)
        connection = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        
        cursor = connection.cursor()
        
        # Create tables with user_id support
        tables = [
            """
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL,
                quantity REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                pnl REAL DEFAULT 0,
                pnl_percentage REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                close_time TIMESTAMP,
                strategy TEXT,
                created_by TEXT DEFAULT 'system'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                philosopher TEXT,
                reasoning TEXT,
                market_trend TEXT,
                rsi REAL,
                volume_ratio REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed BOOLEAN DEFAULT FALSE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS performance (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                total_pnl REAL DEFAULT 0,
                daily_pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_config (
                user_id TEXT PRIMARY KEY,
                initial_capital REAL,
                current_balance REAL,
                risk_level TEXT,
                risk_per_trade REAL,
                max_positions INTEGER,
                symbols TEXT,
                philosophers TEXT,
                setup_completed BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for table_sql in tables:
            try:
                cursor.execute(table_sql)
                connection.commit()
            except Exception as e:
                logger.warning(f"Table creation warning (may already exist): {e}")
                connection.rollback()
        
        # Create default users for demo
        if os.getenv("ENVIRONMENT") != "production":
            try:
                cursor.execute("""
                    INSERT INTO user_config (user_id, initial_capital, current_balance, risk_level, setup_completed)
                    VALUES 
                    ('user_1', 10000, 10000, 'balanced', TRUE),
                    ('user_2', 10000, 10000, 'balanced', TRUE)
                    ON CONFLICT (user_id) DO NOTHING
                """)
                connection.commit()
                logger.info("Demo users configured")
            except Exception as e:
                logger.warning(f"Demo user creation warning: {e}")
                connection.rollback()
        
        cursor.close()
        connection.close()
        logger.info("Database setup completed successfully")
        
    except Exception as e:
        logger.error(f"Database setup error: {e}")
        logger.info("Will fall back to SQLite if PostgreSQL fails")

def main():
    """Main startup function"""
    logger.info("🚀 Starting botphIA production server...")
    
    # Setup database
    setup_database()
    
    # Import FastAPI app and serve static files
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pathlib import Path
    import uvicorn
    from fastapi_server import app
    
    # Mount frontend static files
    frontend_path = Path(__file__).parent.parent / "botphia" / "dist"
    if frontend_path.exists():
        app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")
        
        # Serve index.html for all non-API routes
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("ws"):
                return {"error": "Not found"}
            return FileResponse(frontend_path / "index.html")
        
        logger.info(f"Frontend mounted from {frontend_path}")
    else:
        logger.warning("Frontend build not found - API only mode")
    
    port = int(os.getenv("PORT", 10000))
    
    logger.info(f"Starting server on port {port}")
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()