#!/usr/bin/env python3
"""
SISTEMA DE AUDITORÍA COMPLETA PARA PAPER TRADING
Registra todas las operaciones para análisis posterior
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AuditSystem:
    """Sistema de auditoría completa para paper trading"""
    
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.init_audit_tables()
    
    def init_audit_tables(self):
        """Crear tablas de auditoría si no existen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de auditoría de trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS paper_trading_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                symbol TEXT,
                action TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_percentage REAL,
                balance_before REAL,
                balance_after REAL,
                philosopher TEXT,
                confidence REAL,
                reasoning TEXT,
                market_conditions TEXT,
                signals_data TEXT,
                position_data TEXT,
                metadata TEXT
            )
        ''')
        
        # Tabla de snapshots del estado del bot
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_state_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                balance REAL,
                total_pnl REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                open_positions INTEGER,
                positions_data TEXT,
                market_summary TEXT,
                metadata TEXT
            )
        ''')
        
        # Tabla de señales evaluadas (incluso las no ejecutadas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT,
                action TEXT,
                philosopher TEXT,
                confidence REAL,
                validation_score REAL,
                executed BOOLEAN,
                reason_not_executed TEXT,
                market_data TEXT,
                signal_data TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Tablas de auditoría inicializadas")
    
    def log_trade_event(self, event_type: str, trade_data: Dict):
        """Registrar evento de trading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO paper_trading_audit (
                timestamp, event_type, symbol, action, entry_price, exit_price,
                quantity, pnl, pnl_percentage, balance_before, balance_after,
                philosopher, confidence, reasoning, market_conditions,
                signals_data, position_data, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            event_type,
            trade_data.get('symbol'),
            trade_data.get('action'),
            trade_data.get('entry_price'),
            trade_data.get('exit_price'),
            trade_data.get('quantity'),
            trade_data.get('pnl'),
            trade_data.get('pnl_percentage'),
            trade_data.get('balance_before'),
            trade_data.get('balance_after'),
            trade_data.get('philosopher'),
            trade_data.get('confidence'),
            trade_data.get('reasoning'),
            json.dumps(trade_data.get('market_conditions', {})),
            json.dumps(trade_data.get('signals_data', {})),
            json.dumps(trade_data.get('position_data', {})),
            json.dumps(trade_data.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📝 Evento auditado: {event_type} - {trade_data.get('symbol')}")
    
    def save_bot_snapshot(self, bot_state: Dict):
        """Guardar snapshot del estado del bot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bot_state_snapshots (
                timestamp, balance, total_pnl, total_trades, winning_trades,
                losing_trades, win_rate, open_positions, positions_data,
                market_summary, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            bot_state.get('balance'),
            bot_state.get('total_pnl'),
            bot_state.get('total_trades'),
            bot_state.get('winning_trades'),
            bot_state.get('losing_trades'),
            bot_state.get('win_rate'),
            bot_state.get('open_positions'),
            json.dumps(bot_state.get('positions', [])),
            json.dumps(bot_state.get('market_summary', {})),
            json.dumps(bot_state.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📸 Snapshot guardado: Balance ${bot_state.get('balance'):.2f}")
    
    def log_signal_evaluation(self, signal_data: Dict, executed: bool, reason: str = None):
        """Registrar evaluación de señal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals_audit (
                timestamp, symbol, action, philosopher, confidence,
                validation_score, executed, reason_not_executed,
                market_data, signal_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            signal_data.get('symbol'),
            signal_data.get('action'),
            signal_data.get('philosopher'),
            signal_data.get('confidence'),
            signal_data.get('validation_score'),
            executed,
            reason,
            json.dumps(signal_data.get('market_data', {})),
            json.dumps(signal_data)
        ))
        
        conn.commit()
        conn.close()
    
    def get_audit_summary(self, hours: int = 24) -> Dict:
        """Obtener resumen de auditoría"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtener estadísticas de las últimas X horas
        time_limit = datetime.now().isoformat()
        
        # Total de eventos
        cursor.execute('''
            SELECT COUNT(*), event_type
            FROM paper_trading_audit
            WHERE timestamp > datetime('now', '-{} hours')
            GROUP BY event_type
        '''.format(hours))
        events_by_type = cursor.fetchall()
        
        # Resumen de PnL
        cursor.execute('''
            SELECT SUM(pnl), COUNT(*), AVG(pnl_percentage)
            FROM paper_trading_audit
            WHERE event_type = 'CLOSE_POSITION'
            AND timestamp > datetime('now', '-{} hours')
        '''.format(hours))
        pnl_summary = cursor.fetchone()
        
        # Señales evaluadas vs ejecutadas
        cursor.execute('''
            SELECT COUNT(*), SUM(executed)
            FROM signals_audit
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours))
        signals_summary = cursor.fetchone()
        
        conn.close()
        
        return {
            'period_hours': hours,
            'events_by_type': dict(events_by_type) if events_by_type else {},
            'total_pnl': pnl_summary[0] if pnl_summary[0] else 0,
            'total_closed_trades': pnl_summary[1] if pnl_summary[1] else 0,
            'avg_pnl_percentage': pnl_summary[2] if pnl_summary[2] else 0,
            'signals_evaluated': signals_summary[0] if signals_summary else 0,
            'signals_executed': signals_summary[1] if signals_summary else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def export_audit_data(self, start_date: str = None, end_date: str = None) -> Dict:
        """Exportar datos de auditoría para análisis"""
        conn = sqlite3.connect(self.db_path)
        
        # Construir query con filtros de fecha opcionales
        query = "SELECT * FROM paper_trading_audit"
        params = []
        
        if start_date or end_date:
            query += " WHERE"
            if start_date:
                query += " timestamp >= ?"
                params.append(start_date)
            if start_date and end_date:
                query += " AND"
            if end_date:
                query += " timestamp <= ?"
                params.append(end_date)
        
        query += " ORDER BY timestamp DESC"
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'id': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'symbol': row[3],
                'action': row[4],
                'entry_price': row[5],
                'exit_price': row[6],
                'quantity': row[7],
                'pnl': row[8],
                'pnl_percentage': row[9],
                'balance_before': row[10],
                'balance_after': row[11],
                'philosopher': row[12],
                'confidence': row[13],
                'reasoning': row[14],
                'market_conditions': json.loads(row[15]) if row[15] else {},
                'signals_data': json.loads(row[16]) if row[16] else {},
                'position_data': json.loads(row[17]) if row[17] else {},
                'metadata': json.loads(row[18]) if row[18] else {}
            })
        
        conn.close()
        
        return {
            'trades': trades,
            'total_records': len(trades),
            'export_date': datetime.now().isoformat(),
            'filters': {
                'start_date': start_date,
                'end_date': end_date
            }
        }

# Instancia global del sistema de auditoría
audit_system = AuditSystem()