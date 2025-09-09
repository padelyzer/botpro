#!/usr/bin/env python3
"""
===========================================
SECURE SYSTEM RUNNER - BotPhia
===========================================

Secure replacement for run_system.py that eliminates all subprocess calls.
Uses native Python operations and secure system management.

SECURITY IMPROVEMENTS:
- No subprocess execution (eliminates command injection)
- Native Python system monitoring
- Secure process management
- Thread-safe operations
- Comprehensive error handling
- Security event logging

Author: Security Team
Date: 2025-01-22
Version: 2.0.0
"""

import asyncio
import threading
import time
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import importlib.util
import concurrent.futures
from dataclasses import dataclass

# Import secure operations
from .secure_operations import (
    SystemManager, SecureSystemOperations, SecureFileManager,
    OperationResult
)
from .secure_logging import (
    SecurityLoggerFactory, SecurityEventType, SecuritySeverity,
    trading_logger
)
from .validation_security import security_logger

# ===========================================
# SECURE SYSTEM CONFIGURATION
# ===========================================

@dataclass
class SecureServiceConfig:
    """Configuration for secure services"""
    name: str
    module_path: str
    function_name: str
    restart_limit: int = 5
    restart_delay: int = 5
    health_check_interval: int = 60
    enabled: bool = True

# Secure service configurations
SECURE_SERVICES = {
    'signal_generator': SecureServiceConfig(
        name='signal_generator',
        module_path='signal_generator',
        function_name='run_signal_generation',
        restart_limit=3,
        restart_delay=10
    ),
    'database_maintenance': SecureServiceConfig(
        name='database_maintenance',
        module_path='database_maintenance',
        function_name='run_maintenance_cycle',
        restart_limit=2,
        restart_delay=30,
        health_check_interval=3600  # 1 hour
    ),
    'quality_alerts': SecureServiceConfig(
        name='quality_alerts',
        module_path='quality_alert_system',
        function_name='monitor_quality_alerts',
        restart_limit=3,
        restart_delay=15,
        health_check_interval=30
    )
}

# ===========================================
# SECURE SERVICE MANAGER
# ===========================================

class SecureService:
    """Secure service wrapper without subprocess"""
    
    def __init__(self, config: SecureServiceConfig):
        self.config = config
        self.is_running = False
        self.restart_count = 0
        self.last_restart = None
        self.thread = None
        self.executor = None
        self.task = None
        self.error_count = 0
        self.last_health_check = datetime.now()
        
    async def start(self) -> OperationResult:
        """Start service securely using native Python"""
        try:
            if self.is_running:
                return OperationResult(False, "Service already running")
            
            # Load module securely
            module_result = self._load_service_module()
            if not module_result.success:
                return module_result
            
            module = module_result.data
            
            # Get service function
            if not hasattr(module, self.config.function_name):
                return OperationResult(False, f"Function {self.config.function_name} not found in module")
            
            service_function = getattr(module, self.config.function_name)
            
            # Start service in thread pool
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            self.task = asyncio.create_task(self._run_service(service_function))
            
            self.is_running = True
            self.last_restart = datetime.now()
            
            # Log service start
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.LOW,
                f"Secure service started: {self.config.name}",
                context={'service': self.config.name, 'method': 'native_python'}
            )
            
            return OperationResult(True, f"Service {self.config.name} started successfully")
        
        except Exception as e:
            return OperationResult(False, f"Failed to start service: {str(e)}", error=str(e))
    
    async def stop(self) -> OperationResult:
        """Stop service gracefully"""
        try:
            if not self.is_running:
                return OperationResult(True, "Service already stopped")
            
            # Cancel task
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown executor
            if self.executor:
                self.executor.shutdown(wait=True)
            
            self.is_running = False
            self.task = None
            self.executor = None
            
            # Log service stop
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.LOW,
                f"Secure service stopped: {self.config.name}",
                context={'service': self.config.name}
            )
            
            return OperationResult(True, f"Service {self.config.name} stopped successfully")
        
        except Exception as e:
            return OperationResult(False, f"Failed to stop service: {str(e)}", error=str(e))
    
    async def restart(self) -> OperationResult:
        """Restart service with rate limiting"""
        if self.restart_count >= self.config.restart_limit:
            return OperationResult(False, "Maximum restart limit reached")
        
        # Check restart rate limiting
        if self.last_restart:
            time_since_restart = (datetime.now() - self.last_restart).total_seconds()
            if time_since_restart < self.config.restart_delay:
                return OperationResult(False, "Restart too soon, rate limited")
        
        # Stop service
        stop_result = await self.stop()
        if not stop_result.success:
            return stop_result
        
        # Wait before restart
        await asyncio.sleep(self.config.restart_delay)
        
        # Start service
        self.restart_count += 1
        start_result = await self.start()
        
        if start_result.success:
            # Log restart
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.MEDIUM,
                f"Service restarted: {self.config.name} (attempt {self.restart_count})",
                context={'service': self.config.name, 'restart_count': self.restart_count}
            )
        
        return start_result
    
    def _load_service_module(self) -> OperationResult:
        """Securely load service module"""
        try:
            # Validate module path
            module_path = Path(f"/Users/ja/saby/trading_api/{self.config.module_path}.py")
            if not module_path.exists():
                return OperationResult(False, f"Module file not found: {module_path}")
            
            # Load module spec
            spec = importlib.util.spec_from_file_location(
                self.config.module_path, 
                module_path
            )
            
            if not spec or not spec.loader:
                return OperationResult(False, "Failed to create module spec")
            
            # Create and execute module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return OperationResult(True, "Module loaded successfully", module)
        
        except Exception as e:
            return OperationResult(False, f"Failed to load module: {str(e)}", error=str(e))
    
    async def _run_service(self, service_function):
        """Run service function in executor"""
        try:
            loop = asyncio.get_event_loop()
            
            # Run service function in thread pool
            await loop.run_in_executor(self.executor, service_function)
            
        except Exception as e:
            self.error_count += 1
            trading_logger.log_security_event(
                SecurityEventType.ERROR_OCCURRED,
                SecuritySeverity.MEDIUM,
                f"Service error: {self.config.name} - {str(e)}",
                context={'service': self.config.name, 'error_count': self.error_count}
            )
            
            # Auto-restart on error if within limits
            if self.restart_count < self.config.restart_limit:
                await asyncio.sleep(self.config.restart_delay)
                restart_result = await self.restart()
                if not restart_result.success:
                    self.is_running = False
            else:
                self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'name': self.config.name,
            'running': self.is_running,
            'restart_count': self.restart_count,
            'error_count': self.error_count,
            'last_restart': self.last_restart.isoformat() if self.last_restart else None,
            'last_health_check': self.last_health_check.isoformat()
        }

# ===========================================
# SECURE TRADING SYSTEM MANAGER
# ===========================================

class SecureTradingSystemManager:
    """Secure trading system manager without subprocess risks"""
    
    def __init__(self):
        self.services: Dict[str, SecureService] = {}
        self.system_manager = SystemManager()
        self.system_ops = SecureSystemOperations()
        self.file_manager = SecureFileManager()
        self.running = False
        self.health_monitor_task = None
        self.maintenance_task = None
        
        # Initialize services
        for service_name, config in SECURE_SERVICES.items():
            if config.enabled:
                self.services[service_name] = SecureService(config)
    
    async def start_system(self) -> OperationResult:
        """Start the entire trading system securely"""
        try:
            if self.running:
                return OperationResult(False, "System already running")
            
            self.running = True
            
            # Log system startup
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.LOW,
                "Secure trading system starting up",
                context={'method': 'native_python', 'subprocess_free': True}
            )
            
            # Start all services
            startup_results = {}
            for service_name, service in self.services.items():
                result = await service.start()
                startup_results[service_name] = result.success
                
                if not result.success:
                    trading_logger.log_security_event(
                        SecurityEventType.ERROR_OCCURRED,
                        SecuritySeverity.MEDIUM,
                        f"Failed to start service: {service_name} - {result.error}",
                        context={'service': service_name}
                    )
            
            # Start monitoring tasks
            self.health_monitor_task = asyncio.create_task(self._health_monitor())
            self.maintenance_task = asyncio.create_task(self._maintenance_cycle())
            
            success_count = sum(startup_results.values())
            total_count = len(startup_results)
            
            if success_count == 0:
                return OperationResult(False, "No services started successfully")
            
            # Log system startup completion
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.LOW,
                f"Secure trading system started: {success_count}/{total_count} services running",
                context={
                    'services_started': success_count,
                    'total_services': total_count,
                    'startup_results': startup_results
                }
            )
            
            return OperationResult(
                True, 
                f"System started: {success_count}/{total_count} services running",
                startup_results
            )
        
        except Exception as e:
            return OperationResult(False, f"System startup failed: {str(e)}", error=str(e))
    
    async def stop_system(self) -> OperationResult:
        """Stop the trading system gracefully"""
        try:
            if not self.running:
                return OperationResult(True, "System already stopped")
            
            # Log system shutdown
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.LOW,
                "Secure trading system shutting down",
                context={'method': 'graceful_shutdown'}
            )
            
            self.running = False
            
            # Cancel monitoring tasks
            if self.health_monitor_task:
                self.health_monitor_task.cancel()
            if self.maintenance_task:
                self.maintenance_task.cancel()
            
            # Stop all services
            shutdown_results = {}
            for service_name, service in self.services.items():
                result = await service.stop()
                shutdown_results[service_name] = result.success
            
            success_count = sum(shutdown_results.values())
            total_count = len(shutdown_results)
            
            # Log system shutdown completion
            trading_logger.log_security_event(
                SecurityEventType.SYSTEM_OPERATION,
                SecuritySeverity.LOW,
                f"Secure trading system stopped: {success_count}/{total_count} services stopped",
                context={'shutdown_results': shutdown_results}
            )
            
            return OperationResult(
                True,
                f"System stopped: {success_count}/{total_count} services stopped",
                shutdown_results
            )
        
        except Exception as e:
            return OperationResult(False, f"System shutdown failed: {str(e)}", error=str(e))
    
    async def restart_service(self, service_name: str) -> OperationResult:
        """Restart specific service"""
        if service_name not in self.services:
            return OperationResult(False, f"Service not found: {service_name}")
        
        service = self.services[service_name]
        return await service.restart()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        # Get service statuses
        service_statuses = {}
        for service_name, service in self.services.items():
            service_statuses[service_name] = service.get_status()
        
        # Get system statistics
        system_stats_result = self.system_ops.get_system_stats()
        system_stats = system_stats_result.data if system_stats_result.success else {}
        
        # Get process monitoring
        process_result = self.system_ops.monitor_trading_processes()
        process_data = process_result.data if process_result.success else {}
        
        return {
            'system_running': self.running,
            'timestamp': datetime.now().isoformat(),
            'services': service_statuses,
            'system_stats': system_stats,
            'processes': process_data,
            'total_services': len(self.services),
            'running_services': sum(1 for s in self.services.values() if s.is_running)
        }
    
    async def _health_monitor(self):
        """Continuous health monitoring"""
        while self.running:
            try:
                # Perform health checks
                health_result = self.system_manager.health_check()
                
                if health_result.success:
                    health_data = health_result.data
                    
                    # Check for unhealthy conditions
                    if not health_data.get('overall', {}).get('healthy', True):
                        trading_logger.log_security_event(
                            SecurityEventType.PERFORMANCE_ALERT,
                            SecuritySeverity.MEDIUM,
                            "System health check failed",
                            context=health_data
                        )
                
                # Check service health
                for service_name, service in self.services.items():
                    if not service.is_running and service.restart_count < service.config.restart_limit:
                        # Attempt to restart failed service
                        restart_result = await service.restart()
                        if restart_result.success:
                            trading_logger.log_security_event(
                                SecurityEventType.SYSTEM_OPERATION,
                                SecuritySeverity.MEDIUM,
                                f"Auto-restarted failed service: {service_name}",
                                context={'service': service_name}
                            )
                
                await asyncio.sleep(60)  # Health check every minute
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                trading_logger.log_security_event(
                    SecurityEventType.ERROR_OCCURRED,
                    SecuritySeverity.MEDIUM,
                    f"Health monitor error: {str(e)}",
                    context={'component': 'health_monitor'}
                )
                await asyncio.sleep(60)
    
    async def _maintenance_cycle(self):
        """Automated maintenance cycle"""
        while self.running:
            try:
                # Run maintenance every hour
                await asyncio.sleep(3600)
                
                if self.running:
                    maintenance_result = self.system_manager.run_maintenance()
                    
                    if maintenance_result.success:
                        trading_logger.log_security_event(
                            SecurityEventType.SYSTEM_OPERATION,
                            SecuritySeverity.LOW,
                            "Automated maintenance completed successfully",
                            context=maintenance_result.data
                        )
                    else:
                        trading_logger.log_security_event(
                            SecurityEventType.ERROR_OCCURRED,
                            SecuritySeverity.MEDIUM,
                            f"Automated maintenance failed: {maintenance_result.error}",
                            context={'component': 'maintenance_cycle'}
                        )
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                trading_logger.log_security_event(
                    SecurityEventType.ERROR_OCCURRED,
                    SecuritySeverity.MEDIUM,
                    f"Maintenance cycle error: {str(e)}",
                    context={'component': 'maintenance_cycle'}
                )

# ===========================================
# SIGNAL HANDLERS
# ===========================================

def setup_signal_handlers(system_manager: SecureTradingSystemManager):
    """Setup secure signal handlers"""
    
    def signal_handler(signum, frame):
        """Handle system signals gracefully"""
        trading_logger.log_security_event(
            SecurityEventType.SYSTEM_OPERATION,
            SecuritySeverity.MEDIUM,
            f"System signal received: {signum}",
            context={'signal': signum, 'method': 'graceful_shutdown'}
        )
        
        # Create a new event loop for shutdown if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run shutdown
        loop.run_until_complete(system_manager.stop_system())
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# ===========================================
# MAIN EXECUTION
# ===========================================

async def main():
    """Main secure system execution"""
    try:
        # Create secure system manager
        system_manager = SecureTradingSystemManager()
        
        # Setup signal handlers
        setup_signal_handlers(system_manager)
        
        # Log system initialization
        trading_logger.log_security_event(
            SecurityEventType.SYSTEM_OPERATION,
            SecuritySeverity.LOW,
            "Secure trading system initialized",
            context={
                'subprocess_free': True,
                'security_enabled': True,
                'services_count': len(system_manager.services)
            }
        )
        
        # Start system
        start_result = await system_manager.start_system()
        
        if not start_result.success:
            trading_logger.log_security_event(
                SecurityEventType.ERROR_OCCURRED,
                SecuritySeverity.HIGH,
                f"Failed to start secure trading system: {start_result.error}",
                context={'startup_error': start_result.error}
            )
            return
        
        print("="*60)
        print("🔒 SECURE TRADING SYSTEM STARTED")
        print("="*60)
        print(f"✅ Status: {start_result.message}")
        print("🛡️  Security: Command injection protection enabled")
        print("🔍 Monitoring: Real-time health checks active")
        print("📝 Logging: Security event logging enabled")
        print("="*60)
        
        # Keep system running
        try:
            while system_manager.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Graceful shutdown initiated...")
            await system_manager.stop_system()
    
    except Exception as e:
        trading_logger.log_security_event(
            SecurityEventType.ERROR_OCCURRED,
            SecuritySeverity.CRITICAL,
            f"Critical system error: {str(e)}",
            context={'error': str(e), 'component': 'main_execution'}
        )
        print(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run secure system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Secure trading system stopped")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)