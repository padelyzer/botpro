"""
Configuration Management Module
Centralized configuration for the trading system
"""

import yaml
import os
from typing import Dict, Any, Optional

class Config:
    """Centralized configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(current_dir, 'config.yaml')
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Config file not found: {self.config_path}")
            return self._get_default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file is missing"""
        return {
            'trading': {
                'default_position_size': 50,
                'leverage': 10,
                'liquidation_buffer': 20
            },
            'monitoring': {
                'refresh_interval': 30,
                'enable_alerts': True
            },
            'targets': {
                'sol': {
                    'buy_zones': [
                        {'price': 180, 'position_size': 60, 'priority': 'primary'},
                        {'price': 183, 'position_size': 40, 'priority': 'secondary'},
                        {'price': 175, 'position_size': 80, 'priority': 'panic'}
                    ]
                },
                'btc': {
                    'recovery_level': 110000,
                    'critical_support': 108000
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update(self, key: str, value: Any) -> None:
        """Update configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save_config()
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as file:
                yaml.safe_dump(self.config, file, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.config = self._load_config()

# Global configuration instance
config = Config()