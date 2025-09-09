#!/usr/bin/env python3
"""
TELEGRAM SIGNAL NOTIFIER - BotphIA
Envía señales de trading a canal de Telegram con formato profesional
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
import json

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        
    async def send_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Envía señal formateada a Telegram"""
        try:
            message = self._format_signal_message(signal_data)
            return await self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending Telegram signal: {e}")
            return False
    
    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        """Formatea la señal para Telegram con emojis y estructura profesional"""
        
        # Emojis según el tipo de señal
        signal_emoji = "🟢" if signal.get('signal_type') == 'BUY' else "🔴"
        confidence_emoji = self._get_confidence_emoji(signal.get('confidence', 'MEDIUM'))
        
        message = f"""
{signal_emoji} **SEÑAL DE TRADING** {confidence_emoji}

**Par:** `{signal.get('symbol', 'N/A')}`
**Tipo:** {signal.get('signal_type', 'N/A')}
**Timeframe:** {signal.get('timeframe', 'N/A')}
**Patrón:** {signal.get('pattern_type', 'N/A')}

📊 **PRECIOS:**
• Entrada: `${signal.get('entry_price', 'N/A')}`
• Stop Loss: `${signal.get('stop_loss', 'N/A')}`
• TP1: `${signal.get('take_profit_1', 'N/A')}`
• TP2: `${signal.get('take_profit_2', 'N/A')}`

⚡ **CONFIGURACIÓN:**
• Leverage: `{signal.get('recommended_leverage', '1x')}`
• R:R Ratio: `{signal.get('risk_reward_ratio', 'N/A')}`
• Volatilidad ATR: `{signal.get('atr_volatility', 'N/A')}`

🔥 **Confianza:** {signal.get('confidence', 'MEDIUM')}

⏰ **{datetime.now().strftime('%H:%M:%S')}**
        """.strip()
        
        return message
    
    def _get_confidence_emoji(self, confidence: str) -> str:
        """Retorna emoji según nivel de confianza"""
        confidence_map = {
            'HIGH': '🔥',
            'MEDIUM': '⚡',
            'LOW': '⚠️'
        }
        return confidence_map.get(confidence.upper(), '⚡')
    
    async def _send_message(self, message: str) -> bool:
        """Envía mensaje a Telegram"""
        url = f"{self.api_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload) as response:
                    if response.status == 200:
                        logger.info("Señal enviada exitosamente a Telegram")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Error Telegram API: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error HTTP enviando a Telegram: {e}")
            return False

    async def send_status_update(self, message: str) -> bool:
        """Envía update de estado del sistema"""
        formatted_message = f"🤖 **BotphIA Status**\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return await self._send_message(formatted_message)

# Factory function
def create_telegram_notifier() -> Optional[TelegramNotifier]:
    """Crea notificador de Telegram desde variables de entorno"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.warning("Variables TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID no configuradas")
        return None
    
    return TelegramNotifier(bot_token, chat_id)

# Test function
async def test_telegram_notification():
    """Función de prueba para notificaciones"""
    notifier = create_telegram_notifier()
    if not notifier:
        print("❌ Configuración de Telegram no encontrada")
        return
    
    # Señal de prueba
    test_signal = {
        'symbol': 'BTCUSDT',
        'signal_type': 'BUY',
        'timeframe': '4h',
        'pattern_type': 'Double Bottom',
        'entry_price': '65420.50',
        'stop_loss': '64200.00',
        'take_profit_1': '67800.00',
        'take_profit_2': '69200.00',
        'recommended_leverage': '8x',
        'risk_reward_ratio': '2.1',
        'confidence': 'HIGH',
        'atr_volatility': '1.2%'
    }
    
    success = await notifier.send_signal(test_signal)
    if success:
        print("✅ Señal de prueba enviada exitosamente")
    else:
        print("❌ Error enviando señal de prueba")

if __name__ == "__main__":
    # Prueba directa
    asyncio.run(test_telegram_notification())