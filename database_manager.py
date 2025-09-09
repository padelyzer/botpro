"""
BotPhia Database Transaction Manager
===================================

ACID-compliant database transaction management with connection pooling,
performance optimization, and safe transaction handling for trading operations.

Author: Senior Backend Developer
Phase: 1 - Days 11-14
"""

import sqlite3
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Iterator
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from pathlib import Path

# Import error handling and secret management
from error_handler import (
    ErrorHandler, DatabaseError, handle_errors, ErrorSeverity,
    handle_data_error, handle_critical_error
)
from secret_manager import secret_manager

# Configure logging
logger = logging.getLogger(__name__)

# Database Configuration
# =====================

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_type: DatabaseType
    connection_string: str
    pool_size: int = 10
    max_connections: int = 20
    connection_timeout: int = 30
    query_timeout: int = 60
    enable_wal: bool = True  # For SQLite
    enable_foreign_keys: bool = True

@dataclass
class TransactionContext:
    """Transaction context information"""
    transaction_id: str
    start_time: datetime
    connection: Any
    is_committed: bool = False
    is_rolled_back: bool = False
    operations: List[str] = field(default_factory=list)

# Connection Pool Management
# =========================

class ConnectionPool:
    """Thread-safe connection pool for database connections"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._lock = threading.RLock()
        self._connections: List[Any] = []
        self._used_connections: Dict[int, Any] = {}
        self._connection_stats = {
            'created': 0,
            'destroyed': 0,
            'acquired': 0,
            'released': 0,
            'errors': 0
        }
        
        # Initialize pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            for _ in range(self.config.pool_size):
                conn = self._create_connection()
                if conn:
                    self._connections.append(conn)
                    self._connection_stats['created'] += 1
            
            logger.info(f"Database pool initialized with {len(self._connections)} connections")
            
        except Exception as e:
            handle_critical_error(DatabaseError(
                message=f"Failed to initialize connection pool: {str(e)}",
                context={'config': str(self.config)}
            ))
            raise
    
    def _create_connection(self) -> Any:
        """Create a new database connection"""
        try:
            if self.config.db_type == DatabaseType.SQLITE:
                return self._create_sqlite_connection()
            elif self.config.db_type == DatabaseType.POSTGRESQL:
                return self._create_postgresql_connection()
            else:
                raise DatabaseError(f"Unsupported database type: {self.config.db_type}")
                
        except Exception as e:
            self._connection_stats['errors'] += 1
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def _create_sqlite_connection(self) -> sqlite3.Connection:
        """Create SQLite connection with optimization"""
        conn = sqlite3.connect(
            self.config.connection_string,
            timeout=self.config.connection_timeout,
            check_same_thread=False
        )
        
        # Enable optimizations
        if self.config.enable_wal:
            conn.execute("PRAGMA journal_mode=WAL")
        
        if self.config.enable_foreign_keys:
            conn.execute("PRAGMA foreign_keys=ON")
        
        # Performance optimizations
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=memory")
        
        # Set row factory for dict-like access
        conn.row_factory = sqlite3.Row
        
        return conn
    
    def _create_postgresql_connection(self) -> psycopg2.extensions.connection:
        """Create PostgreSQL connection"""
        conn = psycopg2.connect(
            self.config.connection_string,
            cursor_factory=RealDictCursor
        )
        conn.autocommit = False  # Ensure transactions work properly
        return conn
    
    def acquire(self) -> Any:
        """Acquire connection from pool"""
        with self._lock:
            if self._connections:
                conn = self._connections.pop()
                self._used_connections[id(conn)] = conn
                self._connection_stats['acquired'] += 1
                return conn
            
            # Pool empty, try to create new connection if under limit
            if len(self._used_connections) < self.config.max_connections:
                conn = self._create_connection()
                if conn:
                    self._used_connections[id(conn)] = conn
                    self._connection_stats['created'] += 1
                    self._connection_stats['acquired'] += 1
                    return conn
            
            raise DatabaseError(
                message="Connection pool exhausted",
                context={
                    'pool_size': len(self._connections),
                    'used_connections': len(self._used_connections),
                    'max_connections': self.config.max_connections
                }
            )
    
    def release(self, conn: Any, is_error: bool = False):
        """Release connection back to pool"""
        with self._lock:
            conn_id = id(conn)
            
            if conn_id not in self._used_connections:
                logger.warning("Attempting to release unknown connection")
                return
            
            del self._used_connections[conn_id]
            self._connection_stats['released'] += 1
            
            if is_error:
                # Close problematic connection
                try:
                    conn.close()
                    self._connection_stats['destroyed'] += 1
                except Exception:
                    pass
            else:
                # Return healthy connection to pool
                if len(self._connections) < self.config.pool_size:
                    self._connections.append(conn)
                else:
                    # Pool full, close excess connection
                    try:
                        conn.close()
                        self._connection_stats['destroyed'] += 1
                    except Exception:
                        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                'pool_size': len(self._connections),
                'used_connections': len(self._used_connections),
                'max_connections': self.config.max_connections,
                'stats': dict(self._connection_stats)
            }
    
    def close_all(self):
        """Close all connections in pool"""
        with self._lock:
            # Close available connections
            for conn in self._connections:
                try:
                    conn.close()
                    self._connection_stats['destroyed'] += 1
                except Exception:
                    pass
            self._connections.clear()
            
            # Close used connections
            for conn in self._used_connections.values():
                try:
                    conn.close()
                    self._connection_stats['destroyed'] += 1
                except Exception:
                    pass
            self._used_connections.clear()

# Transaction Manager
# ==================

class DatabaseManager:
    """
    ACID-compliant database transaction manager.
    
    Features:
    - Connection pooling
    - Transaction context management
    - Automatic rollback on errors
    - Query performance monitoring
    - Safe position operations
    - Database schema management
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager.
        
        Args:
            config: Database configuration or None for auto-detection
        """
        self.config = config or self._auto_detect_config()
        self.pool = ConnectionPool(self.config)
        
        # Transaction tracking
        self._active_transactions: Dict[str, TransactionContext] = {}
        self._transaction_lock = threading.RLock()
        
        # Performance metrics
        self._query_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_execution_time': 0.0,
            'slow_queries': 0
        }
        self._stats_lock = threading.Lock()
        
        # Error handler
        self.error_handler = ErrorHandler()
        
        # Initialize database schema
        self._initialize_schema()
        
        logger.info(f"DatabaseManager initialized with {self.config.db_type.value}")
    
    def _auto_detect_config(self) -> DatabaseConfig:
        """Auto-detect database configuration from environment"""
        try:
            # Try to get database URL from secret manager
            db_url = secret_manager.get_database_url()
            
            if db_url.startswith('postgresql://') or db_url.startswith('postgres://'):
                return DatabaseConfig(
                    db_type=DatabaseType.POSTGRESQL,
                    connection_string=db_url,
                    pool_size=5,
                    max_connections=10
                )
            else:
                # Assume SQLite
                db_path = db_url.replace('sqlite:///', '')
                return DatabaseConfig(
                    db_type=DatabaseType.SQLITE,
                    connection_string=db_path,
                    pool_size=3,
                    max_connections=5
                )
                
        except Exception as e:
            # Fallback to SQLite
            logger.warning(f"Failed to auto-detect DB config, using SQLite: {e}")
            return DatabaseConfig(
                db_type=DatabaseType.SQLITE,
                connection_string="trading_bot.db",
                pool_size=3,
                max_connections=5
            )
    
    @contextmanager
    def get_connection(self) -> Iterator[Any]:
        """
        Context manager for database connections.
        
        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM positions")
        """
        conn = None
        try:
            conn = self.pool.acquire()
            yield conn
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'database_connection'
            })
            raise
        finally:
            if conn:
                self.pool.release(conn, is_error=bool(e if 'e' in locals() else None))
    
    @contextmanager
    def get_transaction(self) -> Iterator[Tuple[Any, str]]:
        """
        Context manager for database transactions with ACID guarantees.
        
        Usage:
            with db_manager.get_transaction() as (conn, tx_id):
                cursor = conn.cursor()
                cursor.execute("INSERT INTO positions ...")
                # Transaction auto-commits on success, auto-rollback on error
        
        Returns:
            Tuple of (connection, transaction_id)
        """
        transaction_id = str(uuid.uuid4())
        conn = None
        tx_context = None
        
        try:
            # Acquire connection and start transaction
            conn = self.pool.acquire()
            
            if self.config.db_type == DatabaseType.SQLITE:
                conn.execute("BEGIN IMMEDIATE")
            else:  # PostgreSQL
                conn.autocommit = False
            
            # Create transaction context
            tx_context = TransactionContext(
                transaction_id=transaction_id,
                start_time=datetime.now(),
                connection=conn
            )
            
            # Track transaction
            with self._transaction_lock:
                self._active_transactions[transaction_id] = tx_context
            
            logger.debug(f"Transaction started: {transaction_id}")
            
            yield conn, transaction_id
            
            # Commit transaction if we reach here
            conn.commit()
            tx_context.is_committed = True
            logger.debug(f"Transaction committed: {transaction_id}")
            
        except Exception as e:
            # Rollback on any error
            if conn and not (tx_context and tx_context.is_committed):
                try:
                    conn.rollback()
                    if tx_context:
                        tx_context.is_rolled_back = True
                    logger.debug(f"Transaction rolled back: {transaction_id}")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed for {transaction_id}: {rollback_error}")
            
            # Handle the error
            self.error_handler.handle_error(e, {
                'operation': 'database_transaction',
                'transaction_id': transaction_id
            })
            raise
        
        finally:
            # Clean up transaction tracking
            with self._transaction_lock:
                if transaction_id in self._active_transactions:
                    del self._active_transactions[transaction_id]
            
            # Release connection
            if conn:
                self.pool.release(conn, is_error=not (tx_context and tx_context.is_committed))
    
    def execute_query(self, query: str, params: Tuple = None, 
                     fetch_one: bool = False, fetch_all: bool = False) -> Any:
        """
        Execute a query safely with performance monitoring.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Return single row
            fetch_all: Return all rows
            
        Returns:
            Query result or None
        """
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Handle different fetch modes
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                
                # Update stats
                execution_time = time.time() - start_time
                self._update_query_stats(True, execution_time)
                
                if execution_time > 1.0:  # Slow query threshold
                    logger.warning(f"Slow query detected ({execution_time:.2f}s): {query[:100]}...")
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_stats(False, execution_time)
            
            self.error_handler.handle_error(e, {
                'operation': 'execute_query',
                'query': query[:200],  # Limit query length in logs
                'execution_time': execution_time
            })
            raise
    
    def _update_query_stats(self, success: bool, execution_time: float):
        """Update query performance statistics"""
        with self._stats_lock:
            self._query_stats['total_queries'] += 1
            
            if success:
                self._query_stats['successful_queries'] += 1
            else:
                self._query_stats['failed_queries'] += 1
            
            # Update average execution time
            total = self._query_stats['total_queries']
            current_avg = self._query_stats['avg_execution_time']
            self._query_stats['avg_execution_time'] = (
                (current_avg * (total - 1) + execution_time) / total
            )
            
            if execution_time > 1.0:
                self._query_stats['slow_queries'] += 1
    
    def _initialize_schema(self):
        """Initialize database schema with proper indexes"""
        try:
            schema_sql = self._get_schema_sql()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for statement in schema_sql:
                    if statement.strip():
                        try:
                            cursor.execute(statement)
                        except Exception as e:
                            # Log but don't fail - table might already exist
                            logger.debug(f"Schema statement skipped: {e}")
                
                conn.commit()
                
            logger.info("Database schema initialized")
            
        except Exception as e:
            handle_critical_error(DatabaseError(
                message=f"Failed to initialize schema: {str(e)}",
                context={'db_type': self.config.db_type.value}
            ))
    
    def _get_schema_sql(self) -> List[str]:
        """Get database schema SQL statements"""
        if self.config.db_type == DatabaseType.SQLITE:
            return [
                """
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL,
                    quantity REAL NOT NULL,
                    pnl REAL DEFAULT 0,
                    pnl_percentage REAL DEFAULT 0,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT DEFAULT 'OPEN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON positions(user_id, symbol)",
                "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
                "CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at)",
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence REAL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    status TEXT DEFAULT 'PENDING'
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals(symbol, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)",
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    position_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(position_id) REFERENCES positions(id)
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_trades_position_id ON trades(position_id)",
                "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)"
            ]
        else:  # PostgreSQL
            return [
                """
                CREATE TABLE IF NOT EXISTS positions (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    type VARCHAR NOT NULL,
                    entry_price DECIMAL(20,8) NOT NULL,
                    current_price DECIMAL(20,8),
                    quantity DECIMAL(20,8) NOT NULL,
                    pnl DECIMAL(20,8) DEFAULT 0,
                    pnl_percentage DECIMAL(10,4) DEFAULT 0,
                    stop_loss DECIMAL(20,8),
                    take_profit DECIMAL(20,8),
                    status VARCHAR DEFAULT 'OPEN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON positions(user_id, symbol)",
                "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
                "CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at)",
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    signal_type VARCHAR NOT NULL,
                    action VARCHAR NOT NULL,
                    entry_price DECIMAL(20,8) NOT NULL,
                    stop_loss DECIMAL(20,8),
                    take_profit DECIMAL(20,8),
                    confidence DECIMAL(5,4),
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    status VARCHAR DEFAULT 'PENDING'
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals(symbol, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)",
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id VARCHAR PRIMARY KEY,
                    position_id VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    action VARCHAR NOT NULL,
                    quantity DECIMAL(20,8) NOT NULL,
                    price DECIMAL(20,8) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(position_id) REFERENCES positions(id)
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_trades_position_id ON trades(position_id)",
                "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)"
            ]
    
    # Safe Trading Operations
    # ======================
    
    def create_position_safe(self, position_data: Dict[str, Any]) -> str:
        """
        Create a new position with transaction safety.
        
        Args:
            position_data: Position data dictionary
            
        Returns:
            Position ID
        """
        position_id = str(uuid.uuid4())
        
        try:
            with self.get_transaction() as (conn, tx_id):
                cursor = conn.cursor()
                
                # Insert position
                if self.config.db_type == DatabaseType.SQLITE:
                    cursor.execute("""
                        INSERT INTO positions (
                            id, user_id, symbol, type, entry_price, quantity,
                            stop_loss, take_profit, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        position_id,
                        position_data['user_id'],
                        position_data['symbol'],
                        position_data['type'],
                        position_data['entry_price'],
                        position_data['quantity'],
                        position_data.get('stop_loss'),
                        position_data.get('take_profit'),
                        position_data.get('status', 'OPEN'),
                        datetime.now().isoformat()
                    ))
                else:  # PostgreSQL
                    cursor.execute("""
                        INSERT INTO positions (
                            id, user_id, symbol, type, entry_price, quantity,
                            stop_loss, take_profit, status, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        position_id,
                        position_data['user_id'],
                        position_data['symbol'],
                        position_data['type'],
                        position_data['entry_price'],
                        position_data['quantity'],
                        position_data.get('stop_loss'),
                        position_data.get('take_profit'),
                        position_data.get('status', 'OPEN'),
                        datetime.now()
                    ))
                
                logger.info(f"Position created: {position_id}")
                return position_id
                
        except Exception as e:
            handle_data_error(e, {
                'operation': 'create_position',
                'position_data': position_data
            })
            raise
    
    def close_position_safe(self, position_id: str, close_price: float, 
                           pnl: float, pnl_percentage: float) -> bool:
        """
        Close a position with transaction safety.
        
        Args:
            position_id: Position ID to close
            close_price: Final closing price
            pnl: Profit/Loss amount
            pnl_percentage: Profit/Loss percentage
            
        Returns:
            True if position was closed successfully
        """
        try:
            with self.get_transaction() as (conn, tx_id):
                cursor = conn.cursor()
                
                # Update position
                if self.config.db_type == DatabaseType.SQLITE:
                    cursor.execute("""
                        UPDATE positions 
                        SET current_price = ?, pnl = ?, pnl_percentage = ?,
                            status = 'CLOSED', closed_at = ?, updated_at = ?
                        WHERE id = ? AND status = 'OPEN'
                    """, (
                        close_price, pnl, pnl_percentage,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        position_id
                    ))
                else:  # PostgreSQL
                    cursor.execute("""
                        UPDATE positions 
                        SET current_price = %s, pnl = %s, pnl_percentage = %s,
                            status = 'CLOSED', closed_at = %s, updated_at = %s
                        WHERE id = %s AND status = 'OPEN'
                    """, (
                        close_price, pnl, pnl_percentage,
                        datetime.now(), datetime.now(), position_id
                    ))
                
                # Check if position was actually updated
                rows_affected = cursor.rowcount
                
                if rows_affected == 0:
                    raise DatabaseError(f"Position {position_id} not found or already closed")
                
                logger.info(f"Position closed: {position_id} (PnL: {pnl:.2f})")
                return True
                
        except Exception as e:
            handle_data_error(e, {
                'operation': 'close_position',
                'position_id': position_id,
                'close_price': close_price
            })
            raise
    
    def get_open_positions(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get all open positions, optionally filtered by user"""
        try:
            if user_id:
                query = "SELECT * FROM positions WHERE status = 'OPEN' AND user_id = ?"
                params = (user_id,) if self.config.db_type == DatabaseType.SQLITE else (user_id,)
            else:
                query = "SELECT * FROM positions WHERE status = 'OPEN'"
                params = None
            
            if self.config.db_type == DatabaseType.POSTGRESQL and user_id:
                query = query.replace('?', '%s')
            
            result = self.execute_query(query, params, fetch_all=True)
            
            # Convert to list of dictionaries
            if result:
                return [dict(row) for row in result]
            return []
            
        except Exception as e:
            handle_data_error(e, {
                'operation': 'get_open_positions',
                'user_id': user_id
            })
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database manager statistics"""
        with self._stats_lock:
            query_stats = dict(self._query_stats)
        
        with self._transaction_lock:
            transaction_stats = {
                'active_transactions': len(self._active_transactions),
                'transaction_ids': list(self._active_transactions.keys())
            }
        
        pool_stats = self.pool.get_stats()
        
        return {
            'database_type': self.config.db_type.value,
            'connection_string': self.config.connection_string,
            'pool_stats': pool_stats,
            'query_stats': query_stats,
            'transaction_stats': transaction_stats,
            'uptime': datetime.now().isoformat()
        }
    
    def shutdown(self):
        """Gracefully shutdown database manager"""
        logger.info("Shutting down database manager...")
        
        # Close all connections
        self.pool.close_all()
        
        logger.info("Database manager shutdown complete")

# Global instance
# ===============

_global_database_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get or create global database manager"""
    global _global_database_manager
    if _global_database_manager is None:
        _global_database_manager = DatabaseManager()
    return _global_database_manager

def set_database_manager(manager: DatabaseManager) -> None:
    """Set global database manager"""
    global _global_database_manager
    _global_database_manager = manager

# Convenience functions
# ====================

def execute_safe_query(query: str, params: Tuple = None, **kwargs) -> Any:
    """Execute query using global database manager"""
    manager = get_database_manager()
    return manager.execute_query(query, params, **kwargs)

def create_position(position_data: Dict[str, Any]) -> str:
    """Create position using global database manager"""
    manager = get_database_manager()
    return manager.create_position_safe(position_data)

def close_position(position_id: str, close_price: float, pnl: float, pnl_percentage: float) -> bool:
    """Close position using global database manager"""
    manager = get_database_manager()
    return manager.close_position_safe(position_id, close_price, pnl, pnl_percentage)

def get_open_positions(user_id: str = None) -> List[Dict[str, Any]]:
    """Get open positions using global database manager"""
    manager = get_database_manager()
    return manager.get_open_positions(user_id)