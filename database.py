"""
Sistema de Base de Datos para Trading Bot
Gestiona la persistencia de señales y posiciones

Updated to use the new DatabaseManager for ACID transactions and better error handling.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

# Import new database manager for enhanced functionality
from database_manager import (
    DatabaseManager, get_database_manager, create_position,
    close_position, get_open_positions, execute_safe_query
)
from error_handler import handle_data_error, DatabaseError

class TradingDatabase:
    def __init__(self, db_path: str = "trading_bot.db"):
        """
        Inicializa la conexión a la base de datos.
        
        Now uses the new DatabaseManager for enhanced functionality.
        """
        self.db_path = db_path
        
        # Initialize new database manager
        try:
            self.db_manager = get_database_manager()
            self.use_new_manager = True
        except Exception as e:
            handle_data_error(e, {'operation': 'init_database_manager'})
            self.use_new_manager = False
            # Fallback to old initialization
            self.init_database()
    
    def init_database(self):
        """Crea las tablas si no existen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de posiciones
        cursor.execute("""
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
        """)
        
        # Tabla de señales
        cursor.execute("""
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
                executed BOOLEAN DEFAULT 0
            )
        """)
        
        # Tabla de métricas de performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """)
        
        # Tabla de alertas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de análisis de señales (BI)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_analysis (
                id TEXT PRIMARY KEY,
                signal_id TEXT NOT NULL,
                quality_score REAL NOT NULL,
                confirmation_indicators TEXT,
                risk_assessment TEXT,
                market_conditions TEXT,
                historical_performance TEXT,
                recommendation TEXT,
                reasoning TEXT,
                confidence_level REAL,
                execution_priority INTEGER,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES signals (id)
            )
        """)
        
        # Tabla de trazabilidad de señales
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_trace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                philosopher TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES signals (id)
            )
        """)
        
        # Tabla de performance por filósofo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS philosopher_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                philosopher TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_id TEXT,
                entry_price REAL,
                exit_price REAL,
                profit_loss REAL,
                win BOOLEAN,
                hold_time_hours INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    # === POSICIONES ===
    
    def save_position(self, position: Dict) -> bool:
        """Guarda una nueva posición"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO positions 
                (id, user_id, symbol, type, entry_price, current_price, quantity, 
                 stop_loss, take_profit, pnl, pnl_percentage, status, strategy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position['id'],
                position['user_id'],
                position['symbol'],
                position['type'],
                position['entry_price'],
                position.get('current_price', position['entry_price']),
                position['quantity'],
                position.get('stop_loss'),
                position.get('take_profit'),
                position.get('pnl', 0),
                position.get('pnl_percentage', 0),
                position.get('status', 'OPEN'),
                position.get('strategy', 'Manual')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving position: {e}")
            return False
    
    def get_open_positions(self, user_id: str = None) -> List[Dict]:
        """Obtiene las posiciones abiertas (opcionalmente filtradas por usuario)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT * FROM positions 
                WHERE status = 'OPEN' AND user_id = ?
                ORDER BY opened_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM positions 
                WHERE status = 'OPEN'
                ORDER BY opened_at DESC
            """)
        
        columns = [col[0] for col in cursor.description]
        positions = []
        for row in cursor.fetchall():
            positions.append(dict(zip(columns, row)))
        
        conn.close()
        return positions
    
    def update_position(self, position_id: str, updates: Dict) -> bool:
        """Actualiza una posición existente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Construir la consulta dinámicamente
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [position_id]
            
            cursor.execute(f"""
                UPDATE positions 
                SET {set_clause}
                WHERE id = ?
            """, values)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating position: {e}")
            return False
    
    def close_position(self, position_id: str, pnl: float, pnl_percentage: float) -> bool:
        """
        Cierra una posición usando el nuevo DatabaseManager cuando esté disponible.
        
        Args:
            position_id: ID de la posición a cerrar
            pnl: Profit/Loss amount
            pnl_percentage: Profit/Loss percentage
            
        Returns:
            True if position was closed successfully
        """
        if self.use_new_manager:
            try:
                # Use new database manager with proper error handling
                return close_position(position_id, 0.0, pnl, pnl_percentage)  # close_price=0 for backward compatibility
            except Exception as e:
                handle_data_error(e, {
                    'operation': 'close_position_new',
                    'position_id': position_id,
                    'pnl': pnl
                })
                # Fallback to old method
                return self.update_position(position_id, {
                    'status': 'CLOSED',
                    'pnl': pnl,
                    'pnl_percentage': pnl_percentage,
                    'close_time': datetime.now().isoformat()
                })
        else:
            # Use legacy method
            return self.update_position(position_id, {
                'status': 'CLOSED',
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'close_time': datetime.now().isoformat()
            })
    
    # === SEÑALES ===
    
    def save_signal(self, signal: Dict) -> bool:
        """Guarda una nueva señal"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO signals 
                (id, user_id, symbol, action, confidence, entry_price, stop_loss, 
                 take_profit, philosopher, reasoning, market_trend, rsi, volume_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal['id'],
                signal['user_id'],
                signal['symbol'],
                signal['action'],
                signal['confidence'],
                signal.get('entry_price'),
                signal.get('stop_loss'),
                signal.get('take_profit'),
                signal.get('philosopher', 'System'),
                signal.get('reasoning', ''),
                signal.get('market_trend'),
                signal.get('rsi'),
                signal.get('volume_ratio')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving signal: {e}")
            return False
    
    def get_recent_signals(self, limit: int = 20, user_id: str = None) -> List[Dict]:
        """Obtiene las señales más recientes (opcionalmente filtradas por usuario)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT * FROM signals 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM signals 
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        columns = [col[0] for col in cursor.description]
        signals = []
        for row in cursor.fetchall():
            signals.append(dict(zip(columns, row)))
        
        conn.close()
        return signals
    
    def get_recent_signals_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Obtiene las señales más recientes para un símbolo específico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtener señales de las últimas 24 horas (más permisivo)
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        
        cursor.execute("""
            SELECT * FROM signals 
            WHERE symbol = ? 
            AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, cutoff_time, limit))
        
        columns = [col[0] for col in cursor.description]
        signals = []
        for row in cursor.fetchall():
            signals.append(dict(zip(columns, row)))
        
        conn.close()
        return signals
    
    def mark_signal_executed(self, signal_id: str) -> bool:
        """Marca una señal como ejecutada"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE signals 
                SET executed = 1
                WHERE id = ?
            """, (signal_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking signal as executed: {e}")
            return False
    
    # === PERFORMANCE ===
    
    def save_performance_metrics(self, metrics: Dict) -> bool:
        """Guarda métricas de performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO performance 
                (total_pnl, daily_pnl, win_rate, total_trades, 
                 winning_trades, losing_trades, open_positions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.get('total_pnl', 0),
                metrics.get('daily_pnl', 0),
                metrics.get('win_rate', 0),
                metrics.get('total_trades', 0),
                metrics.get('winning_trades', 0),
                metrics.get('losing_trades', 0),
                metrics.get('open_positions', 0)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving performance metrics: {e}")
            return False
    
    def get_latest_performance(self) -> Optional[Dict]:
        """Obtiene las métricas de performance más recientes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM performance 
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            performance = dict(zip(columns, row))
        else:
            performance = None
        
        conn.close()
        return performance
    
    # === ALERTAS ===
    
    def save_alert(self, alert_type: str, message: str, data: Dict = None) -> bool:
        """Guarda una alerta"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO alerts (type, message, data)
                VALUES (?, ?, ?)
            """, (
                alert_type,
                message,
                json.dumps(data) if data else None
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Obtiene las alertas más recientes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM alerts 
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        columns = [col[0] for col in cursor.description]
        alerts = []
        for row in cursor.fetchall():
            alert = dict(zip(columns, row))
            if alert['data']:
                alert['data'] = json.loads(alert['data'])
            alerts.append(alert)
        
        conn.close()
        return alerts
    
    # === ANÁLISIS BI ===
    
    def save_signal_analysis(self, analysis: Dict) -> bool:
        """Guarda análisis BI de una señal"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO signal_analysis 
                (id, signal_id, quality_score, confirmation_indicators, risk_assessment, 
                 market_conditions, historical_performance, recommendation, reasoning, 
                 confidence_level, execution_priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"analysis_{analysis['signal_id']}",
                analysis['signal_id'],
                analysis['quality_score'],
                analysis.get('confirmation_indicators'),
                analysis.get('risk_assessment'),
                analysis.get('market_conditions'),
                analysis.get('historical_performance'),
                analysis['recommendation'],
                analysis.get('reasoning'),
                analysis['confidence_level'],
                analysis['execution_priority']
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving signal analysis: {e}")
            return False
    
    def get_signal_analysis(self, signal_id: str) -> Optional[Dict]:
        """Obtiene análisis de una señal específica"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM signal_analysis 
            WHERE signal_id = ?
        """, (signal_id,))
        
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            analysis = dict(zip(columns, row))
        else:
            analysis = None
        
        conn.close()
        return analysis
    
    def save_signal_trace(self, signal_id: str, event_type: str, event_data: Dict, philosopher: str = None) -> bool:
        """Guarda evento de trazabilidad"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO signal_trace (signal_id, event_type, event_data, philosopher)
                VALUES (?, ?, ?, ?)
            """, (
                signal_id,
                event_type,
                json.dumps(event_data),
                philosopher
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving signal trace: {e}")
            return False
    
    def get_signal_trace(self, signal_id: str) -> List[Dict]:
        """Obtiene trazabilidad completa de una señal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM signal_trace 
            WHERE signal_id = ?
            ORDER BY timestamp ASC
        """, (signal_id,))
        
        columns = [col[0] for col in cursor.description]
        traces = []
        for row in cursor.fetchall():
            trace = dict(zip(columns, row))
            if trace['event_data']:
                trace['event_data'] = json.loads(trace['event_data'])
            traces.append(trace)
        
        conn.close()
        return traces
    
    def save_philosopher_performance(self, performance: Dict) -> bool:
        """Guarda performance de un filósofo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO philosopher_performance 
                (philosopher, symbol, signal_id, entry_price, exit_price, profit_loss, win, hold_time_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                performance['philosopher'],
                performance['symbol'],
                performance.get('signal_id'),
                performance['entry_price'],
                performance['exit_price'],
                performance['profit_loss'],
                performance['win'],
                performance.get('hold_time_hours', 0)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving philosopher performance: {e}")
            return False
    
    def get_philosopher_performance(self, philosopher: str, symbol: str = None, days: int = 30) -> List[Dict]:
        """Obtiene performance histórica de un filósofo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT * FROM philosopher_performance 
                WHERE philosopher = ? AND symbol = ? 
                AND created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            """.format(days), (philosopher, symbol))
        else:
            cursor.execute("""
                SELECT * FROM philosopher_performance 
                WHERE philosopher = ? 
                AND created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            """.format(days), (philosopher,))
        
        columns = [col[0] for col in cursor.description]
        performances = []
        for row in cursor.fetchall():
            performances.append(dict(zip(columns, row)))
        
        conn.close()
        return performances
    
    def get_high_quality_signals(self, min_score: float = 70.0, limit: int = 20) -> List[Dict]:
        """Obtiene señales de alta calidad basadas en análisis BI"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.*, sa.quality_score, sa.recommendation, sa.execution_priority
            FROM signals s
            JOIN signal_analysis sa ON s.id = sa.signal_id
            WHERE sa.quality_score >= ? AND s.executed = 0
            ORDER BY sa.execution_priority ASC, sa.quality_score DESC
            LIMIT ?
        """, (min_score, limit))
        
        columns = [col[0] for col in cursor.description]
        signals = []
        for row in cursor.fetchall():
            signals.append(dict(zip(columns, row)))
        
        conn.close()
        return signals
    
    # === ESTADÍSTICAS ===
    
    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas generales del sistema.
        Ahora incluye estadísticas del DatabaseManager cuando está disponible.
        """
        if self.use_new_manager:
            try:
                # Get enhanced statistics from DatabaseManager
                manager_stats = self.db_manager.get_statistics()
                
                # Get traditional stats for backward compatibility
                traditional_stats = self._get_traditional_stats()
                
                # Combine both
                return {
                    **traditional_stats,
                    'database_manager': manager_stats,
                    'enhanced_features': True
                }
            except Exception as e:
                handle_data_error(e, {'operation': 'get_enhanced_statistics'})
                # Fallback to traditional stats
        
        return self._get_traditional_stats()
    
    def _get_traditional_stats(self) -> Dict:
        """Get traditional database statistics for backward compatibility"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total de posiciones
        cursor.execute("SELECT COUNT(*) FROM positions")
        stats['total_positions'] = cursor.fetchone()[0]
        
        # Posiciones abiertas
        cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'OPEN'")
        stats['open_positions'] = cursor.fetchone()[0]
        
        # Total de señales
        cursor.execute("SELECT COUNT(*) FROM signals")
        stats['total_signals'] = cursor.fetchone()[0]
        
        # Señales ejecutadas
        cursor.execute("SELECT COUNT(*) FROM signals WHERE executed = 1")
        stats['executed_signals'] = cursor.fetchone()[0]
        
        # Señales de alta calidad
        cursor.execute("SELECT COUNT(*) FROM signal_analysis WHERE quality_score >= 70")
        stats['high_quality_signals'] = cursor.fetchone()[0] or 0
        
        # PnL total
        cursor.execute("SELECT SUM(pnl) FROM positions WHERE status = 'CLOSED'")
        result = cursor.fetchone()[0]
        stats['total_pnl'] = result if result else 0
        
        # Performance por filósofo
        cursor.execute("""
            SELECT philosopher, AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END) * 100 as win_rate
            FROM philosopher_performance 
            GROUP BY philosopher
        """)
        philosopher_stats = {}
        for row in cursor.fetchall():
            philosopher_stats[row[0]] = {'win_rate': round(row[1], 1)}
        stats['philosopher_performance'] = philosopher_stats
        
        conn.close()
        return stats

# Instancia global de la base de datos
db = TradingDatabase()