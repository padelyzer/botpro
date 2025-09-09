#!/usr/bin/env python3
"""
SYSTEM STATS - BotphIA
Contador de estadísticas del sistema de trading
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import os

# Import error handling system
try:
    from error_handler import handle_data_error, CorruptedDataError
except ImportError:
    # Fallback if error_handler not available
    def handle_data_error(error, context=None):
        print(f"Data Error: {error}")
    class CorruptedDataError(Exception): pass

class SystemStats:
    """Gestiona las estadísticas del sistema de trading"""
    
    def __init__(self):
        self.stats_file = "system_stats.json"
        self.stats = self.load_stats()
        self.session_start = datetime.now()
        
    def load_stats(self) -> Dict[str, Any]:
        """Carga estadísticas guardadas o crea nuevas"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    stats = json.load(f)
                    # Resetear contadores de sesión
                    stats['session'] = {
                        'start_time': datetime.now().isoformat(),
                        'analyses_count': 0,
                        'signals_generated': 0,
                        'data_points_processed': 0
                    }
                    return stats
            except (json.JSONDecodeError, KeyError) as e:
                handle_data_error(CorruptedDataError(
                    message=f"Corrupted stats file: {self.stats_file}",
                    context={'file_path': str(self.stats_file), 'error': str(e)}
                ))
            except Exception as e:
                handle_data_error(e, {
                    'operation': 'load_stats',
                    'file_path': str(self.stats_file)
                })
        
        # Crear nuevas estadísticas
        return {
            'total': {
                'analyses_count': 0,
                'signals_generated': 0,
                'data_points_processed': 0,
                'symbols_tracked': 0,
                'high_quality_signals': 0,
                'start_date': datetime.now().isoformat()
            },
            'session': {
                'start_time': datetime.now().isoformat(),
                'analyses_count': 0,
                'signals_generated': 0,
                'data_points_processed': 0
            },
            'last_24h': {
                'analyses_count': 0,
                'signals_generated': 0,
                'data_points_processed': 0
            },
            'philosophers': {
                'socrates': {'analyses': 0, 'signals': 0, 'last_active': None},
                'plato': {'analyses': 0, 'signals': 0, 'last_active': None},
                'aristotle': {'analyses': 0, 'signals': 0, 'last_active': None},
                'sun_tzu': {'analyses': 0, 'signals': 0, 'last_active': None},
                'confucius': {'analyses': 0, 'signals': 0, 'last_active': None},
                'nietzsche': {'analyses': 0, 'signals': 0, 'last_active': None}
            },
            'symbols_analysis': {},
            'last_update': datetime.now().isoformat()
        }
    
    def increment_analysis(self, symbol: str = None, philosopher: str = None, data_points: int = 0):
        """Incrementa contador de análisis"""
        # Contadores totales
        self.stats['total']['analyses_count'] += 1
        self.stats['session']['analyses_count'] += 1
        self.stats['last_24h']['analyses_count'] += 1
        
        # Data points procesados
        if data_points > 0:
            self.stats['total']['data_points_processed'] += data_points
            self.stats['session']['data_points_processed'] += data_points
            self.stats['last_24h']['data_points_processed'] += data_points
        
        # Por filósofo
        if philosopher and philosopher.lower() in self.stats['philosophers']:
            self.stats['philosophers'][philosopher.lower()]['analyses'] += 1
            self.stats['philosophers'][philosopher.lower()]['last_active'] = datetime.now().isoformat()
        
        # Por símbolo
        if symbol:
            if symbol not in self.stats['symbols_analysis']:
                self.stats['symbols_analysis'][symbol] = {
                    'analyses': 0,
                    'last_analysis': None
                }
            self.stats['symbols_analysis'][symbol]['analyses'] += 1
            self.stats['symbols_analysis'][symbol]['last_analysis'] = datetime.now().isoformat()
            
            # Actualizar contador de símbolos únicos
            self.stats['total']['symbols_tracked'] = len(self.stats['symbols_analysis'])
        
        self.stats['last_update'] = datetime.now().isoformat()
        self.save_stats()
    
    def increment_signal(self, symbol: str = None, philosopher: str = None, is_high_quality: bool = False):
        """Incrementa contador de señales generadas"""
        self.stats['total']['signals_generated'] += 1
        self.stats['session']['signals_generated'] += 1
        self.stats['last_24h']['signals_generated'] += 1
        
        if is_high_quality:
            self.stats['total']['high_quality_signals'] += 1
        
        # Por filósofo
        if philosopher and philosopher.lower() in self.stats['philosophers']:
            self.stats['philosophers'][philosopher.lower()]['signals'] += 1
        
        self.stats['last_update'] = datetime.now().isoformat()
        self.save_stats()
    
    def get_session_uptime(self) -> str:
        """Calcula el tiempo de actividad de la sesión actual"""
        delta = datetime.now() - datetime.fromisoformat(self.stats['session']['start_time'])
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_analysis_rate(self) -> float:
        """Calcula análisis por minuto"""
        delta = datetime.now() - datetime.fromisoformat(self.stats['session']['start_time'])
        minutes = max(delta.total_seconds() / 60, 1)
        return round(self.stats['session']['analyses_count'] / minutes, 2)
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de estadísticas"""
        return {
            'uptime': self.get_session_uptime(),
            'analysis_rate': self.get_analysis_rate(),
            'total_analyses': self.stats['total']['analyses_count'],
            'session_analyses': self.stats['session']['analyses_count'],
            'total_signals': self.stats['total']['signals_generated'],
            'session_signals': self.stats['session']['signals_generated'],
            'data_points_today': self.stats['session']['data_points_processed'],
            'symbols_tracked': self.stats['total']['symbols_tracked'],
            'high_quality_signals': self.stats['total']['high_quality_signals'],
            'philosophers_status': {
                name: {
                    'analyses': data['analyses'],
                    'signals': data['signals'],
                    'status': 'active' if data['last_active'] and 
                             (datetime.now() - datetime.fromisoformat(data['last_active'])).seconds < 300
                             else 'waiting'
                }
                for name, data in self.stats['philosophers'].items()
            },
            'last_update': self.stats['last_update']
        }
    
    def save_stats(self):
        """Guarda estadísticas en archivo"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Error guardando estadísticas: {e}")
    
    def reset_24h_stats(self):
        """Resetea contadores de 24 horas"""
        self.stats['last_24h'] = {
            'analyses_count': 0,
            'signals_generated': 0,
            'data_points_processed': 0
        }
        self.save_stats()

# Instancia global
_system_stats = None

def get_system_stats() -> SystemStats:
    """Obtiene instancia singleton de estadísticas"""
    global _system_stats
    if _system_stats is None:
        _system_stats = SystemStats()
    return _system_stats