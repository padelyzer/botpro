#!/usr/bin/env python3
"""
SERVICE HEALTH CHECKER - BotphIA
Verificador de estado de todos los servicios del sistema
"""

import asyncio
import aiohttp
import psutil
import socket
from datetime import datetime
from typing import Dict, Any

# Import error handling system
try:
    from error_handler import handle_api_error, NetworkError
except ImportError:
    # Fallback if error_handler not available
    def handle_api_error(error, context=None):
        print(f"API Error: {error}")
    class NetworkError(Exception): pass

class ServiceHealthChecker:
    """Verifica el estado de todos los servicios del sistema"""
    
    def __init__(self):
        self.services = {
            'api_backend': {
                'name': 'API Backend',
                'url': 'http://localhost:8000/api/status',
                'port': 8000,
                'critical': True
            },
            'binance_api': {
                'name': 'Binance API',
                'url': 'https://api.binance.com/api/v3/ping',
                'port': None,
                'critical': False  # No crítico para operación local
            },
            'websocket': {
                'name': 'WebSocket',
                'url': None,
                'port': 8000,
                'critical': False
            },
            'signal_generator': {
                'name': 'Signal Generator',
                'process': 'signal_generator.py',
                'port': None,
                'critical': False  # No crítico si el bot está detenido
            },
            'database': {
                'name': 'SQLite Database',
                'file': 'trading_bot.db',
                'port': None,
                'critical': True
            }
        }
    
    async def check_http_service(self, url: str, timeout: int = 3) -> Dict[str, Any]:
        """Verifica un servicio HTTP"""
        try:
            # Para servicios externos, usar timeout más corto
            if 'binance.com' in url:
                timeout = 2
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout, ssl=False) as response:
                    return {
                        'status': 'online',
                        'response_time': 0,  # Podríamos medir esto
                        'status_code': response.status,
                        'healthy': response.status == 200
                    }
        except asyncio.TimeoutError:
            # Si es Binance y hay timeout, no es crítico
            if 'binance.com' in url:
                return {
                    'status': 'slow',
                    'response_time': timeout * 1000,
                    'healthy': True  # Considerarlo saludable aunque esté lento
                }
            return {
                'status': 'timeout',
                'response_time': timeout * 1000,
                'healthy': False
            }
        except Exception as e:
            # Si es un servicio externo, no marcar como no saludable
            if 'binance.com' in url or 'external' in str(e):
                return {
                    'status': 'unreachable',
                    'error': str(e),
                    'healthy': True  # No afecta salud local
                }
            return {
                'status': 'offline',
                'error': str(e),
                'healthy': False
            }
    
    def check_port(self, port: int, host: str = 'localhost') -> bool:
        """Verifica si un puerto está abierto"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result == 0
        except (OSError, socket.error, ConnectionError) as e:
            handle_api_error(NetworkError(
                message=f"Failed to check port {port} on {host}",
                context={'host': host, 'port': port}
            ))
            return False
    
    def check_process(self, process_name: str) -> Dict[str, Any]:
        """Verifica si un proceso está corriendo"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if process_name in cmdline:
                    # Obtener estadísticas del proceso
                    process = psutil.Process(proc.info['pid'])
                    return {
                        'status': 'running',
                        'pid': proc.info['pid'],
                        'cpu_percent': process.cpu_percent(),
                        'memory_mb': process.memory_info().rss / 1024 / 1024,
                        'healthy': True
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            'status': 'stopped',
            'healthy': False
        }
    
    def check_file(self, filepath: str) -> Dict[str, Any]:
        """Verifica si un archivo existe y es accesible"""
        import os
        try:
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                return {
                    'status': 'available',
                    'size_mb': stat.st_size / 1024 / 1024,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'healthy': True
                }
            else:
                return {
                    'status': 'missing',
                    'healthy': False
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'healthy': False
            }
    
    async def check_all_services(self) -> Dict[str, Any]:
        """Verifica todos los servicios"""
        results = {}
        
        for service_id, config in self.services.items():
            if config.get('url'):
                # Servicio HTTP
                results[service_id] = await self.check_http_service(config['url'])
            elif config.get('process'):
                # Proceso del sistema
                results[service_id] = self.check_process(config['process'])
            elif config.get('file'):
                # Archivo
                results[service_id] = self.check_file(config['file'])
            elif config.get('port'):
                # Solo puerto
                port_open = self.check_port(config['port'])
                results[service_id] = {
                    'status': 'online' if port_open else 'offline',
                    'healthy': port_open
                }
            
            # Agregar metadatos
            results[service_id]['name'] = config['name']
            results[service_id]['critical'] = config['critical']
        
        # Calcular estado general
        all_healthy = all(r.get('healthy', False) for r in results.values() if r.get('critical', False))
        critical_services = [k for k, v in results.items() if self.services[k]['critical'] and not v.get('healthy', False)]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'healthy' if all_healthy else 'degraded' if len(critical_services) < 2 else 'critical',
            'services': results,
            'critical_failures': critical_services,
            'healthy_count': sum(1 for r in results.values() if r.get('healthy', False)),
            'total_count': len(results)
        }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del sistema"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Contar procesos del sistema de trading
        trading_processes = 0
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(x in cmdline for x in ['signal_generator', 'fastapi', 'trading', 'botphia']):
                    trading_processes += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError) as e:
                # Expected errors when accessing process information
                continue
            except Exception as e:
                handle_api_error(e, {
                    'operation': 'get_system_metrics',
                    'function': 'process_iteration'
                })
                continue
        
        return {
            'cpu': {
                'usage_percent': cpu_percent,
                'cores': psutil.cpu_count(),
                'status': 'normal' if cpu_percent < 80 else 'high'
            },
            'memory': {
                'used_gb': memory.used / (1024**3),
                'total_gb': memory.total / (1024**3),
                'percent': memory.percent,
                'status': 'normal' if memory.percent < 85 else 'high'
            },
            'disk': {
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent': disk.percent,
                'status': 'normal' if disk.percent < 90 else 'low'
            },
            'processes': {
                'trading_system': trading_processes,
                'total': len(psutil.pids())
            }
        }

# Instancia singleton
_health_checker = None

def get_health_checker() -> ServiceHealthChecker:
    """Obtiene instancia singleton del health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = ServiceHealthChecker()
    return _health_checker