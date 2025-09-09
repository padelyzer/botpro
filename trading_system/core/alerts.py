"""
Unified Alert System
Centralized alert management with multiple notification channels
"""

import subprocess
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

class AlertType(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"

class AlertChannel(Enum):
    """Available notification channels"""
    SOUND = "sound"
    NOTIFICATION = "notification"
    TERMINAL = "terminal"
    LOG = "log"

class AlertManager:
    """Centralized alert management"""
    
    def __init__(self):
        self.last_alerts = {}
        self.cooldown_minutes = 5
        
    def send_alert(
        self, 
        message: str, 
        alert_type: AlertType = AlertType.INFO,
        channels: list = None,
        title: str = "Trading System Alert",
        cooldown_key: Optional[str] = None
    ) -> bool:
        """Send alert through specified channels"""
        
        # Check cooldown
        if cooldown_key and self._is_in_cooldown(cooldown_key):
            return False
        
        # Default channels
        if channels is None:
            channels = [AlertChannel.TERMINAL, AlertChannel.SOUND]
        
        success = True
        
        # Send through each channel
        for channel in channels:
            try:
                if channel == AlertChannel.TERMINAL:
                    self._send_terminal_alert(message, alert_type, title)
                elif channel == AlertChannel.SOUND:
                    self._play_alert_sound(alert_type)
                elif channel == AlertChannel.NOTIFICATION:
                    self._send_notification(title, message)
                elif channel == AlertChannel.LOG:
                    self._log_alert(message, alert_type)
            except Exception as e:
                print(f"Error sending alert via {channel.value}: {e}")
                success = False
        
        # Update cooldown
        if cooldown_key:
            self.last_alerts[cooldown_key] = datetime.now()
        
        return success
    
    def _is_in_cooldown(self, key: str) -> bool:
        """Check if alert is in cooldown period"""
        if key not in self.last_alerts:
            return False
        
        last_alert = self.last_alerts[key]
        cooldown_end = last_alert + timedelta(minutes=self.cooldown_minutes)
        
        return datetime.now() < cooldown_end
    
    def _send_terminal_alert(self, message: str, alert_type: AlertType, title: str):
        """Send terminal alert with colors and formatting"""
        
        # Color mapping
        colors = {
            AlertType.INFO: '\033[94m',      # Blue
            AlertType.WARNING: '\033[93m',   # Yellow
            AlertType.CRITICAL: '\033[91m',  # Red
            AlertType.SUCCESS: '\033[92m'    # Green
        }
        
        # Icon mapping
        icons = {
            AlertType.INFO: 'ℹ️',
            AlertType.WARNING: '⚠️',
            AlertType.CRITICAL: '🚨',
            AlertType.SUCCESS: '✅'
        }
        
        color = colors.get(alert_type, '\033[0m')
        icon = icons.get(alert_type, '📢')
        reset = '\033[0m'
        
        # Format alert
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        print(f"\n{color}{'='*60}")
        print(f"{icon} {title.upper()}")
        print(f"{'='*60}")
        print(f"Time: {timestamp}")
        print(f"Type: {alert_type.value.upper()}")
        print(f"Message: {message}")
        print(f"{'='*60}{reset}\n")
        
        # Flash terminal for critical alerts
        if alert_type == AlertType.CRITICAL:
            print('\a' * 3)  # Terminal bell
    
    def _play_alert_sound(self, alert_type: AlertType):
        """Play system alert sound"""
        try:
            if alert_type == AlertType.CRITICAL:
                # Play Glass sound twice for critical alerts
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], 
                             check=False, capture_output=True)
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], 
                             check=False, capture_output=True)
            elif alert_type == AlertType.WARNING:
                # Play Sosumi for warnings
                subprocess.run(["afplay", "/System/Library/Sounds/Sosumi.aiff"], 
                             check=False, capture_output=True)
            else:
                # Play Ping for info/success
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], 
                             check=False, capture_output=True)
        except Exception:
            # Fallback to terminal bell
            print('\a')
    
    def _send_notification(self, title: str, message: str):
        """Send macOS notification"""
        try:
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            subprocess.run(["osascript", "-e", script], 
                         check=False, capture_output=True)
        except Exception as e:
            print(f"Notification failed: {e}")
    
    def _log_alert(self, message: str, alert_type: AlertType):
        """Log alert to file"""
        try:
            log_file = "trading_alerts.log"
            timestamp = datetime.now().isoformat()
            
            with open(log_file, 'a') as f:
                f.write(f"{timestamp} [{alert_type.value.upper()}] {message}\n")
        except Exception as e:
            print(f"Logging failed: {e}")
    
    def clear_cooldowns(self):
        """Clear all alert cooldowns"""
        self.last_alerts.clear()

class TradingAlerts:
    """Pre-configured trading alerts"""
    
    def __init__(self, alert_manager: AlertManager = None):
        self.alert_manager = alert_manager or AlertManager()
    
    def price_target_hit(self, symbol: str, price: float, target_type: str):
        """Alert when price target is hit"""
        message = f"{symbol} hit {target_type} target: ${price:.2f}"
        self.alert_manager.send_alert(
            message,
            AlertType.CRITICAL,
            [AlertChannel.TERMINAL, AlertChannel.SOUND, AlertChannel.NOTIFICATION],
            f"{symbol} Price Alert",
            f"price_target_{symbol}_{target_type}"
        )
    
    def entry_signal(self, symbol: str, price: float, score: int, confidence: str):
        """Alert for entry signals"""
        message = f"{symbol} ENTRY SIGNAL at ${price:.2f} (Score: {score}/100, {confidence})"
        alert_type = AlertType.CRITICAL if score >= 70 else AlertType.WARNING
        
        self.alert_manager.send_alert(
            message,
            alert_type,
            [AlertChannel.TERMINAL, AlertChannel.SOUND, AlertChannel.NOTIFICATION],
            f"{symbol} Entry Signal",
            f"entry_signal_{symbol}"
        )
    
    def liquidation_warning(self, symbol: str, current_price: float, liq_price: float, distance_pct: float):
        """Alert for liquidation warnings"""
        message = f"⚠️ {symbol} approaching liquidation! Current: ${current_price:.2f}, Liq: ${liq_price:.2f} ({distance_pct:.1f}% away)"
        
        alert_type = AlertType.CRITICAL if distance_pct < 10 else AlertType.WARNING
        
        self.alert_manager.send_alert(
            message,
            alert_type,
            [AlertChannel.TERMINAL, AlertChannel.SOUND, AlertChannel.NOTIFICATION],
            f"{symbol} Liquidation Warning",
            f"liquidation_{symbol}"
        )
    
    def market_condition_change(self, condition: str, details: str):
        """Alert for market condition changes"""
        message = f"Market condition: {condition} - {details}"
        self.alert_manager.send_alert(
            message,
            AlertType.INFO,
            [AlertChannel.TERMINAL],
            "Market Update"
        )
    
    def system_status(self, status: str, details: str = ""):
        """Alert for system status changes"""
        message = f"System status: {status}"
        if details:
            message += f" - {details}"
        
        alert_type = AlertType.SUCCESS if "started" in status.lower() else AlertType.INFO
        
        self.alert_manager.send_alert(
            message,
            alert_type,
            [AlertChannel.TERMINAL],
            "System Status"
        )

# Global instances
alert_manager = AlertManager()
trading_alerts = TradingAlerts(alert_manager)