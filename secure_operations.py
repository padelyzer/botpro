#!/usr/bin/env python3
"""
===========================================
SECURE OPERATIONS SYSTEM - BotPhia
===========================================

Secure replacement for all subprocess and shell operations.
Eliminates command injection vulnerabilities by using native Python operations.

SECURITY FEATURES:
- No shell command execution
- Native Python implementations for system operations
- Secure file operations with path validation
- Process management without subprocess risks
- Safe disk space monitoring
- Secure log rotation and maintenance

Author: Security Team
Date: 2025-01-22
Version: 2.0.0
"""

import os
import sys
import psutil
import shutil
import threading
import time
import sqlite3
import gzip
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import tempfile
import hashlib

# Import security logging
from .validation_security import security_logger, mask_sensitive_fields

# ===========================================
# SECURITY CONSTANTS
# ===========================================

# Allowed paths for operations (whitelist approach)
ALLOWED_PATHS = {
    '/Users/ja/saby/trading_api',
    '/Users/ja/saby/trading_api/logs',
    '/Users/ja/saby/trading_api/backups',
    '/tmp/trading_api'
}

# Maximum file sizes for operations
MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
MAX_BACKUP_SIZE = 500 * 1024 * 1024  # 500MB

# Process monitoring patterns
TRADING_PROCESSES = {
    'fastapi_server.py',
    'signal_generator.py',
    'database_maintenance.py',
    'run_system.py'
}

# ===========================================
# SECURITY UTILITIES
# ===========================================

class SecurityError(Exception):
    """Custom security exception"""
    pass

class OperationResult:
    """Secure operation result wrapper"""
    def __init__(self, success: bool, message: str, data: Any = None, error: str = None):
        self.success = success
        self.message = message
        self.data = data
        self.error = error
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }

def validate_path_security(path: str) -> str:
    """Validate and normalize path for security"""
    try:
        # Resolve absolute path
        abs_path = os.path.abspath(path)
        
        # Check if path is within allowed directories
        path_allowed = False
        for allowed_path in ALLOWED_PATHS:
            if abs_path.startswith(allowed_path):
                path_allowed = True
                break
        
        if not path_allowed:
            raise SecurityError(f"Path not allowed: {abs_path}")
        
        # Check for path traversal attempts
        if '..' in path or '//' in path:
            raise SecurityError(f"Path traversal detected: {path}")
        
        return abs_path
    
    except Exception as e:
        raise SecurityError(f"Path validation failed: {str(e)}")

def secure_file_operation(operation: str, path: str, **kwargs) -> OperationResult:
    """Wrapper for secure file operations with validation"""
    try:
        validated_path = validate_path_security(path)
        
        # Log security event
        security_logger.info(f"Secure file operation: {operation} on {validated_path}")
        
        return OperationResult(True, f"Path validated: {validated_path}", validated_path)
    
    except SecurityError as e:
        security_logger.warning(f"Security error in file operation: {str(e)}")
        return OperationResult(False, "Security validation failed", error=str(e))

# ===========================================
# SECURE SYSTEM OPERATIONS
# ===========================================

class SecureSystemOperations:
    """Secure system operations without shell commands"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._process_cache = {}
        self._cache_timeout = 30  # seconds
    
    def get_disk_usage(self, path: str = "/") -> OperationResult:
        """Get disk usage information securely"""
        try:
            # Validate path
            validated_path = validate_path_security(path) if path != "/" else "/"
            
            # Use shutil for cross-platform disk usage
            total, used, free = shutil.disk_usage(validated_path)
            
            usage_data = {
                'total_bytes': total,
                'used_bytes': used,
                'free_bytes': free,
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'usage_percentage': round((used / total) * 100, 1)
            }
            
            return OperationResult(True, "Disk usage retrieved", usage_data)
        
        except Exception as e:
            return OperationResult(False, "Failed to get disk usage", error=str(e))
    
    def get_process_info(self, process_name: Optional[str] = None) -> OperationResult:
        """Get process information securely using psutil"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    pinfo = proc.info
                    
                    # Filter by process name if specified
                    if process_name and process_name not in pinfo['name']:
                        continue
                    
                    # Only include trading-related processes for security
                    if any(trading_proc in pinfo['name'] for trading_proc in TRADING_PROCESSES):
                        processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo['name'],
                            'cpu_percent': pinfo['cpu_percent'],
                            'memory_percent': pinfo['memory_percent'],
                            'status': pinfo['status']
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return OperationResult(True, f"Found {len(processes)} processes", processes)
        
        except Exception as e:
            return OperationResult(False, "Failed to get process info", error=str(e))
    
    def get_system_stats(self) -> OperationResult:
        """Get comprehensive system statistics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk_result = self.get_disk_usage()
            disk_data = disk_result.data if disk_result.success else {}
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'usage_percent': cpu_percent,
                    'core_count': cpu_count
                },
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'usage_percent': memory.percent
                },
                'disk': disk_data,
                'uptime_hours': round((time.time() - psutil.boot_time()) / 3600, 1)
            }
            
            return OperationResult(True, "System stats collected", stats)
        
        except Exception as e:
            return OperationResult(False, "Failed to collect system stats", error=str(e))
    
    def monitor_trading_processes(self) -> OperationResult:
        """Monitor trading-related processes"""
        try:
            process_status = {}
            
            for proc_name in TRADING_PROCESSES:
                found_processes = []
                
                for proc in psutil.process_iter(['pid', 'name', 'create_time', 'status']):
                    try:
                        if proc_name in proc.info['name']:
                            found_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'status': proc.info['status'],
                                'uptime_minutes': round((time.time() - proc.info['create_time']) / 60, 1)
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                process_status[proc_name] = {
                    'running': len(found_processes) > 0,
                    'count': len(found_processes),
                    'processes': found_processes
                }
            
            return OperationResult(True, "Process monitoring completed", process_status)
        
        except Exception as e:
            return OperationResult(False, "Process monitoring failed", error=str(e))

# ===========================================
# SECURE FILE MANAGER
# ===========================================

class SecureFileManager:
    """Secure file operations manager"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def rotate_log_files(self, log_dir: str, max_files: int = 10) -> OperationResult:
        """Rotate log files securely without shell commands"""
        try:
            # Validate log directory
            validated_dir = validate_path_security(log_dir)
            log_path = Path(validated_dir)
            
            if not log_path.exists():
                return OperationResult(False, "Log directory does not exist")
            
            rotated_files = []
            
            # Find log files
            for log_file in log_path.glob("*.log"):
                try:
                    # Check file size
                    if log_file.stat().st_size > MAX_LOG_SIZE:
                        # Create compressed backup
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_name = f"{log_file.stem}_{timestamp}.log.gz"
                        backup_path = log_path / backup_name
                        
                        # Compress and backup
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(backup_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Clear original log file
                        with open(log_file, 'w') as f:
                            f.write(f"# Log rotated at {datetime.now().isoformat()}\n")
                        
                        rotated_files.append(str(backup_path))
                
                except Exception as e:
                    self.logger.warning(f"Failed to rotate {log_file}: {e}")
            
            # Clean old backups
            self._clean_old_backups(log_path, max_files)
            
            return OperationResult(True, f"Rotated {len(rotated_files)} log files", rotated_files)
        
        except Exception as e:
            return OperationResult(False, "Log rotation failed", error=str(e))
    
    def _clean_old_backups(self, log_path: Path, max_files: int):
        """Clean old backup files"""
        try:
            # Find compressed log files
            backup_files = list(log_path.glob("*.log.gz"))
            
            # Sort by modification time
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove old files
            for old_file in backup_files[max_files:]:
                old_file.unlink()
                self.logger.info(f"Removed old backup: {old_file}")
        
        except Exception as e:
            self.logger.warning(f"Failed to clean old backups: {e}")
    
    def create_secure_backup(self, source_file: str, backup_dir: str) -> OperationResult:
        """Create secure backup with integrity check"""
        try:
            # Validate paths
            source_path = Path(validate_path_security(source_file))
            backup_path = Path(validate_path_security(backup_dir))
            
            if not source_path.exists():
                return OperationResult(False, "Source file does not exist")
            
            # Create backup directory if needed
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{source_path.stem}_backup_{timestamp}{source_path.suffix}"
            backup_file = backup_path / backup_filename
            
            # Copy file
            shutil.copy2(source_path, backup_file)
            
            # Verify integrity
            source_hash = self._calculate_file_hash(source_path)
            backup_hash = self._calculate_file_hash(backup_file)
            
            if source_hash != backup_hash:
                backup_file.unlink()  # Remove corrupted backup
                return OperationResult(False, "Backup integrity check failed")
            
            backup_info = {
                'source_file': str(source_path),
                'backup_file': str(backup_file),
                'file_hash': source_hash,
                'backup_size': backup_file.stat().st_size,
                'timestamp': timestamp
            }
            
            return OperationResult(True, "Secure backup created", backup_info)
        
        except Exception as e:
            return OperationResult(False, "Backup creation failed", error=str(e))
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

# ===========================================
# SECURE DATABASE MANAGER
# ===========================================

class SecureDatabaseManager:
    """Secure database operations without shell commands"""
    
    def __init__(self, db_path: str):
        self.db_path = validate_path_security(db_path)
        self.logger = logging.getLogger(__name__)
    
    def vacuum_database(self) -> OperationResult:
        """Vacuum database to optimize performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get size before vacuum
                size_before = Path(self.db_path).stat().st_size
                
                # Vacuum database
                conn.execute("VACUUM")
                conn.commit()
                
                # Get size after vacuum
                size_after = Path(self.db_path).stat().st_size
                space_saved = size_before - size_after
                
                result_data = {
                    'size_before_mb': round(size_before / (1024**2), 2),
                    'size_after_mb': round(size_after / (1024**2), 2),
                    'space_saved_mb': round(space_saved / (1024**2), 2)
                }
                
                return OperationResult(True, "Database vacuum completed", result_data)
        
        except Exception as e:
            return OperationResult(False, "Database vacuum failed", error=str(e))
    
    def analyze_database(self) -> OperationResult:
        """Analyze database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get table information
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                table_stats = {}
                for (table_name,) in tables:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    table_stats[table_name] = {
                        'row_count': row_count
                    }
                
                # Get database size
                db_size = Path(self.db_path).stat().st_size
                
                analysis_data = {
                    'database_size_mb': round(db_size / (1024**2), 2),
                    'table_count': len(tables),
                    'tables': table_stats,
                    'analysis_timestamp': datetime.now().isoformat()
                }
                
                return OperationResult(True, "Database analysis completed", analysis_data)
        
        except Exception as e:
            return OperationResult(False, "Database analysis failed", error=str(e))
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> OperationResult:
        """Clean up old records from database"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                deleted_counts = {}
                
                # Clean old signals
                cursor.execute(
                    "DELETE FROM signals WHERE timestamp < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_counts['signals'] = cursor.rowcount
                
                # Clean old closed positions
                cursor.execute(
                    "DELETE FROM positions WHERE status = 'CLOSED' AND close_time < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_counts['positions'] = cursor.rowcount
                
                # Clean old performance records
                cursor.execute(
                    "DELETE FROM performance WHERE date < ?",
                    (cutoff_date.date().isoformat(),)
                )
                deleted_counts['performance'] = cursor.rowcount
                
                conn.commit()
                
                cleanup_data = {
                    'cutoff_date': cutoff_date.isoformat(),
                    'days_kept': days_to_keep,
                    'deleted_records': deleted_counts,
                    'total_deleted': sum(deleted_counts.values())
                }
                
                return OperationResult(True, "Database cleanup completed", cleanup_data)
        
        except Exception as e:
            return OperationResult(False, "Database cleanup failed", error=str(e))

# ===========================================
# SYSTEM MANAGER
# ===========================================

class SystemManager:
    """Comprehensive system management without shell commands"""
    
    def __init__(self):
        self.system_ops = SecureSystemOperations()
        self.file_manager = SecureFileManager()
        self.logger = logging.getLogger(__name__)
        self._maintenance_lock = threading.Lock()
    
    def run_maintenance(self) -> OperationResult:
        """Run comprehensive system maintenance"""
        with self._maintenance_lock:
            try:
                maintenance_results = {}
                
                # System statistics
                stats_result = self.system_ops.get_system_stats()
                maintenance_results['system_stats'] = stats_result.to_dict()
                
                # Process monitoring
                process_result = self.system_ops.monitor_trading_processes()
                maintenance_results['process_monitor'] = process_result.to_dict()
                
                # Log rotation
                log_rotation_result = self.file_manager.rotate_log_files(
                    '/Users/ja/saby/trading_api/logs'
                )
                maintenance_results['log_rotation'] = log_rotation_result.to_dict()
                
                # Database maintenance
                db_path = '/Users/ja/saby/trading_api/trading_bot.db'
                if Path(db_path).exists():
                    db_manager = SecureDatabaseManager(db_path)
                    
                    # Vacuum database
                    vacuum_result = db_manager.vacuum_database()
                    maintenance_results['database_vacuum'] = vacuum_result.to_dict()
                    
                    # Cleanup old records
                    cleanup_result = db_manager.cleanup_old_records()
                    maintenance_results['database_cleanup'] = cleanup_result.to_dict()
                
                # Create maintenance report
                report = {
                    'maintenance_timestamp': datetime.now().isoformat(),
                    'results': maintenance_results,
                    'overall_success': all(
                        result.get('success', False) 
                        for result in maintenance_results.values()
                    )
                }
                
                # Save maintenance report
                report_path = f'/Users/ja/saby/trading_api/logs/maintenance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)
                
                return OperationResult(True, "System maintenance completed", report)
            
            except Exception as e:
                return OperationResult(False, "System maintenance failed", error=str(e))
    
    def health_check(self) -> OperationResult:
        """Comprehensive system health check"""
        try:
            health_data = {}
            
            # System resources
            stats_result = self.system_ops.get_system_stats()
            if stats_result.success:
                stats = stats_result.data
                health_data['resources'] = {
                    'cpu_healthy': stats['cpu']['usage_percent'] < 80,
                    'memory_healthy': stats['memory']['usage_percent'] < 80,
                    'disk_healthy': stats['disk'].get('usage_percentage', 0) < 90
                }
            
            # Process monitoring
            process_result = self.system_ops.monitor_trading_processes()
            if process_result.success:
                processes = process_result.data
                health_data['processes'] = {
                    name: status['running']
                    for name, status in processes.items()
                }
            
            # Database health
            db_path = '/Users/ja/saby/trading_api/trading_bot.db'
            if Path(db_path).exists():
                try:
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("SELECT 1").fetchone()
                    health_data['database'] = {'healthy': True}
                except:
                    health_data['database'] = {'healthy': False}
            
            # Overall health score
            all_checks = []
            for category, checks in health_data.items():
                if isinstance(checks, dict):
                    all_checks.extend(checks.values())
            
            health_score = sum(1 for check in all_checks if check) / len(all_checks) if all_checks else 0
            
            health_data['overall'] = {
                'healthy': health_score >= 0.8,
                'health_score': round(health_score * 100, 1)
            }
            
            return OperationResult(True, "Health check completed", health_data)
        
        except Exception as e:
            return OperationResult(False, "Health check failed", error=str(e))

# ===========================================
# GLOBAL INSTANCES
# ===========================================

# Global system manager instance
system_manager = SystemManager()

# Global secure operations instance
secure_ops = SecureSystemOperations()

# Global file manager instance
file_manager = SecureFileManager()

# Log initialization
security_logger.info("Secure operations system initialized")