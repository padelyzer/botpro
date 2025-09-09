#!/usr/bin/env python3
"""
Sistema de alertas para señales de alta calidad
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import sqlite3
from enhanced_trading_config import get_enhanced_config

logger = logging.getLogger(__name__)

@dataclass
class QualityAlert:
    """Estructura para alertas de calidad"""
    alert_id: str
    symbol: str
    signal_score: float
    philosopher: str
    action: str
    price: float
    alert_type: str  # 'high_quality', 'excellent', 'multi_agreement'
    timestamp: str
    reasoning: List[str] = None
    confidence_factors: Dict = None

class QualityAlertSystem:
    """Sistema de alertas para señales de alta calidad"""
    
    def __init__(self, db_path: str = "signal_haven.db"):
        self.db_path = db_path
        self.config = get_enhanced_config()
        self.alert_history: List[QualityAlert] = []
        self.philosopher_votes: Dict[str, List[Dict]] = {}  # Para rastrear acuerdos
        self.last_alert_time: Dict[str, datetime] = {}
        
        self.setup_alert_database()
        logger.info("🚨 Sistema de alertas de calidad inicializado")
    
    def setup_alert_database(self):
        """Configura tabla de alertas en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE,
                    symbol TEXT,
                    signal_score REAL,
                    philosopher TEXT,
                    action TEXT,
                    price REAL,
                    alert_type TEXT,
                    timestamp TEXT,
                    reasoning TEXT,
                    confidence_factors TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("✅ Tabla de alertas creada correctamente")
            
        except Exception as e:
            logger.error(f"Error configurando base de datos de alertas: {e}")
    
    def evaluate_signal_quality(self, signal: Dict) -> Optional[QualityAlert]:
        """Evalúa si una señal merece alerta de calidad"""
        
        symbol = signal.get('symbol', '')
        score = signal.get('confidence', 0)
        philosopher = signal.get('philosopher', '')
        action = signal.get('action', '')
        price = signal.get('entry_price', 0)
        
        # Obtener configuración específica del símbolo
        symbol_config = self.config.get_symbol_config(symbol)
        
        alert_type = None
        reasoning = []
        
        # 1. Señal excelente (score >= 90)
        if score >= self.config.alert_configs['excellent_threshold']:
            alert_type = 'excellent'
            reasoning.append(f"🌟 Score excelente: {score}%")
        
        # 2. Señal de alta calidad (score >= 80)
        elif score >= self.config.alert_configs['high_quality_threshold']:
            alert_type = 'high_quality'
            reasoning.append(f"🔥 Score alto: {score}%")
        
        # 3. Señal de prioridad (símbolo prioritario con score >= 75)
        elif (symbol in self.config.high_priority_symbols and 
              score >= self.config.alert_configs['priority_symbol_threshold']):
            alert_type = 'priority_symbol'
            reasoning.append(f"💎 Símbolo prioritario: {symbol}")
            reasoning.append(f"📊 Score bueno: {score}%")
        
        # 4. Verificar acuerdo entre filósofos
        if self.check_philosopher_agreement(symbol, action):
            if alert_type is None:
                alert_type = 'multi_agreement'
            reasoning.append("🤝 Múltiples filósofos en acuerdo")
        
        # Crear alerta si cumple criterios
        if alert_type:
            # Evitar spam de alertas (máximo 1 por símbolo cada 5 minutos)
            if self.should_create_alert(symbol):
                alert_id = f"{symbol}_{philosopher}_{int(datetime.now().timestamp())}"
                
                alert = QualityAlert(
                    alert_id=alert_id,
                    symbol=symbol,
                    signal_score=score,
                    philosopher=philosopher,
                    action=action,
                    price=price,
                    alert_type=alert_type,
                    timestamp=datetime.now().isoformat(),
                    reasoning=reasoning,
                    confidence_factors=self.extract_confidence_factors(signal)
                )
                
                return alert
        
        return None
    
    def check_philosopher_agreement(self, symbol: str, action: str) -> bool:
        """Verifica si múltiples filósofos están de acuerdo"""
        # Obtener votos recientes (últimos 5 minutos)
        recent_time = datetime.now() - timedelta(minutes=5)
        
        if symbol not in self.philosopher_votes:
            self.philosopher_votes[symbol] = []
        
        # Limpiar votos antiguos
        self.philosopher_votes[symbol] = [
            vote for vote in self.philosopher_votes[symbol]
            if datetime.fromisoformat(vote['timestamp']) > recent_time
        ]
        
        # Contar votos para la misma acción
        matching_votes = [
            vote for vote in self.philosopher_votes[symbol]
            if vote['action'] == action
        ]
        
        return len(matching_votes) >= self.config.alert_configs['multi_philosopher_agreement']
    
    def should_create_alert(self, symbol: str) -> bool:
        """Determina si debe crear alerta (evita spam)"""
        if symbol not in self.last_alert_time:
            return True
        
        time_since_last = datetime.now() - self.last_alert_time[symbol]
        return time_since_last.total_seconds() > 300  # 5 minutos
    
    def extract_confidence_factors(self, signal: Dict) -> Dict:
        """Extrae factores que contribuyen a la confianza"""
        factors = {}
        
        # Factores técnicos
        if 'technical_score' in signal:
            factors['technical_analysis'] = signal['technical_score']
        
        if 'volume_confirmation' in signal:
            factors['volume_strength'] = signal['volume_confirmation']
        
        if 'trend_alignment' in signal:
            factors['trend_alignment'] = signal['trend_alignment']
        
        # Factores de mercado
        if 'market_conditions' in signal:
            factors['market_conditions'] = signal['market_conditions']
        
        # Factores de riesgo
        if 'risk_reward_ratio' in signal:
            factors['risk_reward'] = signal['risk_reward_ratio']
        
        return factors
    
    def process_signal(self, signal: Dict) -> bool:
        """Procesa señal y genera alerta si corresponde"""
        # Registrar voto del filósofo
        self.record_philosopher_vote(signal)
        
        # Evaluar calidad
        alert = self.evaluate_signal_quality(signal)
        
        if alert:
            return self.trigger_alert(alert)
        
        return False
    
    def record_philosopher_vote(self, signal: Dict):
        """Registra voto de filósofo para análisis de consenso"""
        symbol = signal.get('symbol', '')
        
        if symbol not in self.philosopher_votes:
            self.philosopher_votes[symbol] = []
        
        vote = {
            'philosopher': signal.get('philosopher', ''),
            'action': signal.get('action', ''),
            'confidence': signal.get('confidence', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        self.philosopher_votes[symbol].append(vote)
        
        # Mantener solo votos recientes (últimos 10 minutos)
        cutoff_time = datetime.now() - timedelta(minutes=10)
        self.philosopher_votes[symbol] = [
            v for v in self.philosopher_votes[symbol]
            if datetime.fromisoformat(v['timestamp']) > cutoff_time
        ]
    
    def trigger_alert(self, alert: QualityAlert) -> bool:
        """Dispara alerta de alta calidad"""
        try:
            # Guardar en historial
            self.alert_history.append(alert)
            self.last_alert_time[alert.symbol] = datetime.now()
            
            # Guardar en base de datos
            self.save_alert_to_db(alert)
            
            # Generar notificaciones
            self.send_notifications(alert)
            
            logger.info(f"🚨 ALERTA DE CALIDAD: {alert.symbol} - {alert.alert_type} - Score: {alert.signal_score}%")
            return True
            
        except Exception as e:
            logger.error(f"Error disparando alerta: {e}")
            return False
    
    def save_alert_to_db(self, alert: QualityAlert):
        """Guarda alerta en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO quality_alerts 
                (alert_id, symbol, signal_score, philosopher, action, price, 
                 alert_type, timestamp, reasoning, confidence_factors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.symbol,
                alert.signal_score,
                alert.philosopher,
                alert.action,
                alert.price,
                alert.alert_type,
                alert.timestamp,
                json.dumps(alert.reasoning),
                json.dumps(alert.confidence_factors)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando alerta en BD: {e}")
    
    def send_notifications(self, alert: QualityAlert):
        """Envía notificaciones según configuración"""
        
        # Notificación en consola
        if self.config.notification_configs['console_alerts']:
            self.print_console_alert(alert)
        
        # Log detallado
        if self.config.notification_configs['log_alerts']:
            self.log_detailed_alert(alert)
        
        # Futuras integraciones: webhook, email, etc.
    
    def print_console_alert(self, alert: QualityAlert):
        """Imprime alerta en consola con formato llamativo"""
        print("\n" + "="*60)
        print(f"🚨 ALERTA DE ALTA CALIDAD - {alert.alert_type.upper()}")
        print("="*60)
        print(f"💰 Símbolo: {alert.symbol}")
        print(f"📊 Score: {alert.signal_score}% por {alert.philosopher}")
        print(f"🎯 Acción: {alert.action} @ ${alert.price}")
        print(f"⏰ Tiempo: {alert.timestamp}")
        
        if alert.reasoning:
            print("\n📋 Razones:")
            for reason in alert.reasoning:
                print(f"  {reason}")
        
        if alert.confidence_factors:
            print("\n🔍 Factores de confianza:")
            for factor, value in alert.confidence_factors.items():
                print(f"  • {factor}: {value}")
        
        print("="*60 + "\n")
    
    def log_detailed_alert(self, alert: QualityAlert):
        """Log detallado de la alerta"""
        logger.info(f"🚨 QUALITY_ALERT: {alert.symbol} | {alert.alert_type} | "
                   f"Score: {alert.signal_score}% | Action: {alert.action} | "
                   f"Price: ${alert.price} | Philosopher: {alert.philosopher}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[QualityAlert]:
        """Obtiene alertas recientes"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [alert for alert in self.alert_history 
                if datetime.fromisoformat(alert.timestamp) > cutoff_time]
    
    def get_alert_stats(self) -> Dict:
        """Obtiene estadísticas de alertas"""
        recent_alerts = self.get_recent_alerts(24)
        
        stats = {
            'total_alerts_24h': len(recent_alerts),
            'alerts_by_type': {},
            'alerts_by_symbol': {},
            'alerts_by_philosopher': {},
            'avg_score': 0
        }
        
        if recent_alerts:
            # Por tipo
            for alert in recent_alerts:
                stats['alerts_by_type'][alert.alert_type] = stats['alerts_by_type'].get(alert.alert_type, 0) + 1
                stats['alerts_by_symbol'][alert.symbol] = stats['alerts_by_symbol'].get(alert.symbol, 0) + 1
                stats['alerts_by_philosopher'][alert.philosopher] = stats['alerts_by_philosopher'].get(alert.philosopher, 0) + 1
            
            # Score promedio
            stats['avg_score'] = sum(alert.signal_score for alert in recent_alerts) / len(recent_alerts)
        
        return stats

# Instancia global del sistema de alertas
quality_alert_system = QualityAlertSystem()

def get_quality_alert_system() -> QualityAlertSystem:
    """Obtiene instancia del sistema de alertas"""
    return quality_alert_system

if __name__ == "__main__":
    # Test del sistema de alertas
    alert_system = get_quality_alert_system()
    
    # Simular señal de alta calidad
    test_signal = {
        'symbol': 'BTCUSDT',
        'confidence': 85,
        'philosopher': 'Sócrates',
        'action': 'BUY',
        'entry_price': 112000,
        'technical_score': 82,
        'volume_confirmation': 88,
        'trend_alignment': 90
    }
    
    print("🧪 Probando sistema de alertas...")
    result = alert_system.process_signal(test_signal)
    print(f"Resultado: {'✅ Alerta generada' if result else '❌ No se generó alerta'}")
    
    # Mostrar estadísticas
    stats = alert_system.get_alert_stats()
    print(f"\n📊 Estadísticas: {stats}")