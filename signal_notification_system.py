#!/usr/bin/env python3
"""
SIGNAL NOTIFICATION SYSTEM - BotphIA
Sistema de notificaciones progresivas para señales de trading
Notifica desde la formación hasta la confirmación del patrón
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import sqlite3
from dataclasses import asdict
import os
from enum import Enum

from multi_timeframe_signal_detector import Signal, PatternStage, PatternType
from pinescript_generator import PineScriptGenerator

logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """Niveles de prioridad de notificación"""
    INFO = "info"           # Información general
    ALERT = "alert"         # Alerta importante
    WARNING = "warning"     # Advertencia
    CRITICAL = "critical"   # Crítico - acción inmediata

class NotificationChannel:
    """Canal base de notificación"""
    
    async def send(self, message: str, level: str = "info"):
        raise NotImplementedError

class ConsoleNotification(NotificationChannel):
    """Notificaciones en consola"""
    
    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich
        if use_rich:
            try:
                from rich.console import Console
                from rich.panel import Panel
                from rich.text import Text
                self.console = Console()
                self.rich_available = True
            except ImportError:
                self.rich_available = False
                self.use_rich = False
    
    async def send(self, message: str, level: str = "info"):
        if self.use_rich and self.rich_available:
            # Usar Rich para mejor visualización
            colors = {
                "info": "blue",
                "alert": "yellow",
                "warning": "orange1",
                "critical": "red"
            }
            
            emojis = {
                "info": "ℹ️",
                "alert": "⚠️",
                "warning": "🔴",
                "critical": "🚨"
            }
            
            color = colors.get(level, "white")
            emoji = emojis.get(level, "📊")
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Crear panel con formato mejorado
            from rich.panel import Panel
            from rich.markdown import Markdown
            
            # Convertir HTML a markdown para Rich
            clean_message = message.replace('<b>', '**').replace('</b>', '**')
            clean_message = clean_message.replace('<i>', '_').replace('</i>', '_')
            
            panel = Panel(
                clean_message,
                title=f"{emoji} [{timestamp}]",
                border_style=color,
                padding=(1, 2)
            )
            
            self.console.print(panel)
        else:
            # Fallback a colores ANSI básicos
            colors = {
                "info": "\033[94m",      # Azul
                "alert": "\033[93m",     # Amarillo
                "warning": "\033[91m",   # Rojo claro
                "critical": "\033[95m"   # Magenta
            }
            
            color = colors.get(level, "\033[0m")
            reset = "\033[0m"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{color}[{timestamp}] {message}{reset}")

class TelegramNotification(NotificationChannel):
    """Notificaciones por Telegram"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
    
    async def send(self, message: str, level: str = "info"):
        if not self.enabled:
            return
            
        try:
            import aiohttp
            
            # Agregar emojis según el nivel
            emojis = {
                "info": "ℹ️",
                "alert": "⚠️",
                "warning": "🔴",
                "critical": "🚨"
            }
            
            emoji = emojis.get(level, "📊")
            formatted_message = f"{emoji} {message}"
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": formatted_message,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        logger.error(f"Error enviando a Telegram: {await response.text()}")
        except Exception as e:
            logger.error(f"Error en Telegram: {e}")

class DatabaseNotification(NotificationChannel):
    """Guardar notificaciones en base de datos"""
    
    def __init__(self, db_path: str = "notifications.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Crear tabla de notificaciones si no existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                signal_id TEXT,
                symbol TEXT,
                pattern_type TEXT,
                stage TEXT,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def send(self, message: str, level: str = "info", metadata: Dict = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notifications (level, message, metadata)
            VALUES (?, ?, ?)
        """, (level, message, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        conn.close()

class SignalNotificationManager:
    """Gestor de notificaciones de señales"""
    
    def __init__(self):
        self.channels = [
            ConsoleNotification(),
            TelegramNotification(),
            DatabaseNotification()
        ]
        self.pine_generator = PineScriptGenerator()
        self.tracked_signals = {}  # Señales en seguimiento
        self.notification_history = {}  # Historial para evitar spam
        
    async def process_signal(self, signal: Signal):
        """Procesa una señal y envía notificaciones apropiadas"""
        
        signal_key = f"{signal.symbol}_{signal.pattern_type.value}"
        
        # Verificar si ya notificamos esta señal recientemente
        if self.should_notify(signal_key, signal.stage):
            
            # Generar mensaje según el stage
            message = self.create_notification_message(signal)
            level = self.get_notification_level(signal)
            
            # Generar Pine Script si es necesario
            if signal.stage in [PatternStage.NEARLY_COMPLETE, PatternStage.CONFIRMED]:
                signal.pine_script = self.generate_pine_script(signal)
            
            # Enviar a todos los canales
            for channel in self.channels:
                await channel.send(message, level)
            
            # Actualizar historial
            self.update_notification_history(signal_key, signal.stage)
            
            # Guardar señal en tracking si no está confirmada
            if signal.stage != PatternStage.CONFIRMED:
                self.tracked_signals[signal_key] = signal
    
    def should_notify(self, signal_key: str, stage: PatternStage) -> bool:
        """Determina si se debe notificar basado en el historial"""
        
        if signal_key not in self.notification_history:
            return True
        
        last_notification = self.notification_history[signal_key]
        time_diff = datetime.now() - last_notification['timestamp']
        
        # Reglas de notificación según stage
        if stage == PatternStage.POTENTIAL:
            return time_diff > timedelta(hours=1)
        elif stage == PatternStage.FORMING:
            return time_diff > timedelta(minutes=30)
        elif stage == PatternStage.NEARLY_COMPLETE:
            return time_diff > timedelta(minutes=15)
        elif stage == PatternStage.CONFIRMED:
            return time_diff > timedelta(minutes=5)
        else:
            return True
    
    def update_notification_history(self, signal_key: str, stage: PatternStage):
        """Actualiza el historial de notificaciones"""
        self.notification_history[signal_key] = {
            'timestamp': datetime.now(),
            'stage': stage
        }
    
    def get_notification_level(self, signal: Signal) -> str:
        """Determina el nivel de notificación según el stage y confidence"""
        
        if signal.stage == PatternStage.CONFIRMED and signal.confidence >= 80:
            return "critical"
        elif signal.stage == PatternStage.NEARLY_COMPLETE and signal.confidence >= 70:
            return "alert"
        elif signal.stage == PatternStage.FORMING:
            return "warning"
        else:
            return "info"
    
    def create_notification_message(self, signal: Signal) -> str:
        """Crea el mensaje de notificación según el stage"""
        
        stage_messages = {
            PatternStage.POTENTIAL: "🔍 Posible patrón detectado",
            PatternStage.FORMING: "📈 Patrón formándose",
            PatternStage.NEARLY_COMPLETE: "⏰ Patrón casi completo",
            PatternStage.CONFIRMED: "✅ PATRÓN CONFIRMADO",
            PatternStage.FAILED: "❌ Patrón invalidado"
        }
        
        stage_msg = stage_messages.get(signal.stage, "📊 Actualización de patrón")
        
        # Mensaje base
        message = f"""
<b>{stage_msg}</b>

📊 <b>Par:</b> {signal.symbol}
⏱ <b>Timeframe:</b> {signal.timeframe}
🎯 <b>Patrón:</b> {signal.pattern_type.value.replace('_', ' ').title()}
📊 <b>Confianza:</b> {signal.confidence:.1f}%

💰 <b>Entry:</b> ${signal.entry_price:.4f}
🛑 <b>Stop Loss:</b> ${signal.stop_loss:.4f}
🎯 <b>Target 1:</b> ${signal.take_profit_1:.4f}
🎯 <b>Target 2:</b> ${signal.take_profit_2:.4f}
📈 <b>R:R Ratio:</b> {signal.risk_reward_ratio:.2f}:1
"""
        
        # Agregar información adicional según el stage
        if signal.stage == PatternStage.POTENTIAL:
            message += "\n⚠️ <i>Monitorear para confirmación</i>"
        elif signal.stage == PatternStage.FORMING:
            message += "\n📊 <i>Preparar para posible entrada</i>"
        elif signal.stage == PatternStage.NEARLY_COMPLETE:
            message += "\n⏰ <i>Atención: Preparar orden</i>"
        elif signal.stage == PatternStage.CONFIRMED:
            message += "\n✅ <b>EJECUTAR ENTRADA AHORA</b>"
            
            # Agregar link al Pine Script si existe
            if signal.pine_script:
                message += f"\n\n📊 Pine Script generado: /pine_{signal.id[:8]}"
        
        # Agregar notas adicionales si existen
        if signal.notes:
            key_notes = []
            if 'volume_ratio' in signal.notes:
                key_notes.append(f"Vol: {signal.notes['volume_ratio']:.1f}x")
            if 'breakout_strength' in signal.notes:
                key_notes.append(f"Fuerza: {signal.notes['breakout_strength']:.1f}%")
            if 'support_level' in signal.notes:
                key_notes.append(f"Soporte: ${signal.notes['support_level']:.4f}")
            if 'resistance_level' in signal.notes:
                key_notes.append(f"Resistencia: ${signal.notes['resistance_level']:.4f}")
            
            if key_notes:
                message += f"\n\n📝 <i>{' | '.join(key_notes)}</i>"
        
        return message
    
    def generate_pine_script(self, signal: Signal) -> str:
        """Genera Pine Script para la señal"""
        
        signal_dict = {
            'symbol': signal.symbol,
            'action': 'BUY' if signal.pattern_type in [
                PatternType.DOUBLE_BOTTOM, 
                PatternType.SUPPORT_BOUNCE,
                PatternType.BREAKOUT,
                PatternType.HAMMER,
                PatternType.ENGULFING_BULL,
                PatternType.TRIANGLE_ASC
            ] else 'SELL',
            'confidence': signal.confidence,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit_1,
            'philosopher': signal.pattern_type.value,
            'timestamp': signal.current_timestamp.isoformat(),
            'reasoning': f"{signal.pattern_type.value} pattern detected",
            'market_trend': 'BULLISH' if 'BUY' in str(signal.pattern_type) else 'BEARISH',
            'rsi': 50,  # Default, actualizar con datos reales
            'volume_ratio': signal.notes.get('volume_ratio', 1.0) if signal.notes else 1.0
        }
        
        return self.pine_generator.generate_signal_script(signal_dict)
    
    async def check_tracked_signals(self):
        """Verifica el estado de las señales en seguimiento"""
        
        for signal_key, signal in list(self.tracked_signals.items()):
            # Aquí se puede actualizar el estado de la señal
            # Por ejemplo, verificar si el patrón se completó o falló
            
            # Si la señal cambió de estado, notificar
            # if signal_changed:
            #     await self.process_signal(updated_signal)
            
            # Eliminar señales antiguas (más de 24 horas)
            if datetime.now() - signal.current_timestamp > timedelta(hours=24):
                del self.tracked_signals[signal_key]