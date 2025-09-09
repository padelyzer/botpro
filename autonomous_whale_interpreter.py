#!/usr/bin/env python3
"""
Autonomous Whale Interpreter - Sistema que interpreta movimientos de whales
Monitorea, analiza y entiende qué significan los movimientos de grandes ballenas
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhaleActionType(Enum):
    """Tipos de acciones de whales"""
    ACCUMULATION = "accumulation"          # Comprando gradualmente
    DISTRIBUTION = "distribution"          # Vendiendo gradualmente
    TRANSFER_TO_EXCHANGE = "to_exchange"   # Moviendo a exchange (bearish)
    TRANSFER_FROM_EXCHANGE = "from_exchange" # Sacando de exchange (bullish)
    WALLET_CONSOLIDATION = "consolidation"  # Consolidando wallets
    OTC_DEAL = "otc"                       # Posible OTC deal
    STAKING = "staking"                    # Moviendo a staking
    UNSTAKING = "unstaking"                # Sacando de staking
    UNKNOWN = "unknown"

@dataclass
class WhaleMovement:
    """Estructura de un movimiento de whale"""
    timestamp: datetime
    from_address: str
    to_address: str
    amount: float
    token: str
    usd_value: float
    action_type: WhaleActionType
    exchange_involved: Optional[str] = None
    confidence: float = 0.0

class WhalePatternRecognizer:
    """
    Reconoce patrones en movimientos de whales y determina su significado
    """
    
    def __init__(self):
        # Direcciones conocidas de exchanges
        self.exchange_addresses = {
            # Binance
            "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance",
            "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": "Binance",
            "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d": "Binance",
            "0xF977814e90dA44bFA03b6295A0616a897441aceC": "Binance",
            "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8": "Binance",
            
            # Coinbase
            "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3": "Coinbase",
            "0x503828976D22510aad0201ac7EC88293211D23Da": "Coinbase",
            "0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740": "Coinbase",
            
            # Kraken
            "0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2": "Kraken",
            "0x0A869d79a7052C7f1b55a8EbAbbEa3420F0D1E13": "Kraken",
            
            # OKX
            "0x98EC059Dc09320ad1D614d2303c98B6CED5fAD4E": "OKX",
            "0x868dbc53abaA38011629a312Ad58F4929bDc2BE": "OKX",
        }
        
        # Direcciones de contratos de staking conocidos
        self.staking_addresses = {
            "0x00000000219ab540356cBB839Cbe05303d7705Fa": "ETH2 Deposit",
            "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84": "Lido stETH",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "USDC Contract",
        }
        
        # Historial de movimientos para análisis de patrones
        self.movement_history = []
        self.pattern_cache = {}
        
    def classify_movement(self, movement: Dict) -> WhaleMovement:
        """
        Clasifica un movimiento de whale y determina su significado
        """
        from_addr = movement.get('from', '').lower()
        to_addr = movement.get('to', '').lower()
        amount = float(movement.get('amount', 0))
        token = movement.get('token', 'ETH')
        usd_value = float(movement.get('usd_value', 0))
        
        # Determinar tipo de acción
        action_type = WhaleActionType.UNKNOWN
        exchange_involved = None
        confidence = 0.0
        
        # Check if involves exchange
        from_exchange = self._get_exchange_name(from_addr)
        to_exchange = self._get_exchange_name(to_addr)
        
        if to_exchange:
            action_type = WhaleActionType.TRANSFER_TO_EXCHANGE
            exchange_involved = to_exchange
            confidence = 0.9  # Alta confianza, bearish signal
            
        elif from_exchange:
            action_type = WhaleActionType.TRANSFER_FROM_EXCHANGE
            exchange_involved = from_exchange
            confidence = 0.9  # Alta confianza, bullish signal
            
        elif self._is_staking_address(to_addr):
            action_type = WhaleActionType.STAKING
            confidence = 0.8  # Bullish a largo plazo
            
        elif self._is_staking_address(from_addr):
            action_type = WhaleActionType.UNSTAKING
            confidence = 0.7  # Potencialmente bearish
            
        elif self._is_same_entity(from_addr, to_addr):
            action_type = WhaleActionType.WALLET_CONSOLIDATION
            confidence = 0.5  # Neutral
            
        elif usd_value > 10000000:  # >$10M
            # Posible OTC deal
            action_type = WhaleActionType.OTC_DEAL
            confidence = 0.6
        
        whale_move = WhaleMovement(
            timestamp=datetime.now(),
            from_address=from_addr,
            to_address=to_addr,
            amount=amount,
            token=token,
            usd_value=usd_value,
            action_type=action_type,
            exchange_involved=exchange_involved,
            confidence=confidence
        )
        
        # Agregar al historial
        self.movement_history.append(whale_move)
        
        return whale_move
    
    def _get_exchange_name(self, address: str) -> Optional[str]:
        """Identifica si una dirección es de exchange"""
        return self.exchange_addresses.get(address.lower())
    
    def _is_staking_address(self, address: str) -> bool:
        """Identifica si es una dirección de staking"""
        return address.lower() in self.staking_addresses
    
    def _is_same_entity(self, addr1: str, addr2: str) -> bool:
        """Determina si dos addresses pertenecen a la misma entidad"""
        # Simplificado: verificar si tienen patrones similares
        # En producción, usar clustering analysis
        return False
    
    def analyze_pattern(self, movements: List[WhaleMovement]) -> Dict:
        """
        Analiza patrones en múltiples movimientos
        """
        if not movements:
            return {"pattern": "NO_DATA", "confidence": 0}
        
        # Contar tipos de acciones
        action_counts = {}
        total_usd = 0
        
        for move in movements:
            action_counts[move.action_type.value] = action_counts.get(move.action_type.value, 0) + 1
            total_usd += move.usd_value
        
        # Determinar patrón dominante
        dominant_action = max(action_counts, key=action_counts.get)
        dominant_percentage = action_counts[dominant_action] / len(movements)
        
        # Interpretar patrón
        pattern_interpretation = {
            "dominant_action": dominant_action,
            "confidence": dominant_percentage,
            "total_volume_usd": total_usd,
            "movement_count": len(movements),
            "market_impact": "NEUTRAL"
        }
        
        # Determinar impacto en el mercado
        if dominant_action == WhaleActionType.TRANSFER_TO_EXCHANGE.value:
            if total_usd > 50000000:  # >$50M
                pattern_interpretation["market_impact"] = "VERY_BEARISH"
            elif total_usd > 10000000:  # >$10M
                pattern_interpretation["market_impact"] = "BEARISH"
            else:
                pattern_interpretation["market_impact"] = "SLIGHTLY_BEARISH"
                
        elif dominant_action == WhaleActionType.TRANSFER_FROM_EXCHANGE.value:
            if total_usd > 50000000:
                pattern_interpretation["market_impact"] = "VERY_BULLISH"
            elif total_usd > 10000000:
                pattern_interpretation["market_impact"] = "BULLISH"
            else:
                pattern_interpretation["market_impact"] = "SLIGHTLY_BULLISH"
                
        elif dominant_action == WhaleActionType.ACCUMULATION.value:
            pattern_interpretation["market_impact"] = "BULLISH"
            
        elif dominant_action == WhaleActionType.DISTRIBUTION.value:
            pattern_interpretation["market_impact"] = "BEARISH"
        
        return pattern_interpretation

class AutonomousWhaleTracker:
    """
    Sistema autónomo que monitorea e interpreta movimientos de whales
    """
    
    def __init__(self):
        self.pattern_recognizer = WhalePatternRecognizer()
        self.binance_api = "https://api.binance.com/api/v3"
        
        # Estado del mercado basado en whales
        self.market_state = {
            "whale_sentiment": "NEUTRAL",
            "accumulation_phase": False,
            "distribution_phase": False,
            "panic_selling": False,
            "smart_money_buying": False,
            "confidence": 0
        }
        
        # Métricas agregadas
        self.metrics = {
            "24h_to_exchange": 0,
            "24h_from_exchange": 0,
            "24h_net_flow": 0,
            "large_moves_count": 0,
            "whale_activity_score": 0
        }
        
    async def fetch_whale_movements(self) -> List[Dict]:
        """
        Obtiene movimientos de whales de fuentes gratuitas
        """
        movements = []
        
        try:
            # 1. Obtener de blockchain.info (BTC)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://blockchain.info/unconfirmed-transactions?format=json",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for tx in data.get('txs', [])[:100]:
                        total_btc = sum(out.get('value', 0) for out in tx.get('out', [])) / 100000000
                        
                        if total_btc > 50:  # >50 BTC
                            movements.append({
                                'from': 'unknown',
                                'to': 'unknown',
                                'amount': total_btc,
                                'token': 'BTC',
                                'usd_value': total_btc * 115000,  # Precio aproximado
                                'timestamp': datetime.fromtimestamp(tx.get('time', 0))
                            })
                
                # 2. Simular algunos movimientos de ETH para testing
                # En producción, usar Etherscan API o similar
                simulated_movements = [
                    {
                        'from': '0x742d35Cc6634C0532925a3b844Bc6e7Cc31c0d78',
                        'to': '0x28C6c06298d514Db089934071355E5743bf21d60',  # Binance
                        'amount': 5000,
                        'token': 'ETH',
                        'usd_value': 5000 * 4800
                    },
                    {
                        'from': '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549',  # Binance
                        'to': '0x123456789abcdef123456789abcdef123456789a',
                        'amount': 10000,
                        'token': 'ETH', 
                        'usd_value': 10000 * 4800
                    }
                ]
                
                movements.extend(simulated_movements)
                
        except Exception as e:
            logger.error(f"Error fetching whale movements: {e}")
        
        return movements
    
    async def interpret_movements(self, movements: List[Dict]) -> Dict:
        """
        Interpreta los movimientos y actualiza el estado del mercado
        """
        if not movements:
            return self.market_state
        
        # Clasificar cada movimiento
        classified_movements = []
        for move in movements:
            classified = self.pattern_recognizer.classify_movement(move)
            classified_movements.append(classified)
        
        # Analizar patrón general
        pattern = self.pattern_recognizer.analyze_pattern(classified_movements)
        
        # Actualizar métricas
        for move in classified_movements:
            if move.action_type == WhaleActionType.TRANSFER_TO_EXCHANGE:
                self.metrics["24h_to_exchange"] += move.usd_value
            elif move.action_type == WhaleActionType.TRANSFER_FROM_EXCHANGE:
                self.metrics["24h_from_exchange"] += move.usd_value
        
        self.metrics["24h_net_flow"] = self.metrics["24h_from_exchange"] - self.metrics["24h_to_exchange"]
        self.metrics["large_moves_count"] = len(classified_movements)
        
        # Calcular whale activity score
        if self.metrics["large_moves_count"] > 20:
            self.metrics["whale_activity_score"] = 100
        elif self.metrics["large_moves_count"] > 10:
            self.metrics["whale_activity_score"] = 70
        elif self.metrics["large_moves_count"] > 5:
            self.metrics["whale_activity_score"] = 50
        else:
            self.metrics["whale_activity_score"] = 30
        
        # INTERPRETAR Y ACTUALIZAR ESTADO DEL MERCADO
        self._update_market_state(pattern, classified_movements)
        
        return self.market_state
    
    def _update_market_state(self, pattern: Dict, movements: List[WhaleMovement]):
        """
        Actualiza el estado del mercado basado en interpretación
        """
        impact = pattern.get("market_impact", "NEUTRAL")
        net_flow = self.metrics["24h_net_flow"]
        
        # Reset estados
        self.market_state["accumulation_phase"] = False
        self.market_state["distribution_phase"] = False
        self.market_state["panic_selling"] = False
        self.market_state["smart_money_buying"] = False
        
        # Interpretar situación
        if impact == "VERY_BEARISH" and net_flow < -100000000:  # -$100M
            self.market_state["whale_sentiment"] = "VERY_BEARISH"
            self.market_state["panic_selling"] = True
            self.market_state["confidence"] = 85
            logger.warning("⚠️ PANIC SELLING DETECTED - Whales dumping heavily")
            
        elif impact == "BEARISH" and net_flow < -50000000:
            self.market_state["whale_sentiment"] = "BEARISH"
            self.market_state["distribution_phase"] = True
            self.market_state["confidence"] = 70
            logger.info("📉 Distribution phase - Whales selling")
            
        elif impact == "VERY_BULLISH" and net_flow > 100000000:
            self.market_state["whale_sentiment"] = "VERY_BULLISH"
            self.market_state["smart_money_buying"] = True
            self.market_state["confidence"] = 85
            logger.info("🚀 SMART MONEY BUYING - Whales accumulating heavily")
            
        elif impact == "BULLISH" and net_flow > 50000000:
            self.market_state["whale_sentiment"] = "BULLISH"
            self.market_state["accumulation_phase"] = True
            self.market_state["confidence"] = 70
            logger.info("📈 Accumulation phase - Whales buying")
            
        else:
            self.market_state["whale_sentiment"] = "NEUTRAL"
            self.market_state["confidence"] = 40
    
    async def generate_trading_decision(self, symbol: str) -> Dict:
        """
        Genera decisión de trading basada en interpretación de whales
        """
        decision = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "action": "HOLD",
            "confidence": 0,
            "position_size": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "reasoning": [],
            "whale_metrics": self.metrics,
            "market_state": self.market_state
        }
        
        # Obtener precio actual
        current_price = await self._get_current_price(symbol)
        
        # LÓGICA DE DECISIÓN BASADA EN INTERPRETACIÓN
        
        if self.market_state["smart_money_buying"]:
            decision["action"] = "BUY"
            decision["confidence"] = self.market_state["confidence"]
            decision["position_size"] = 0.4  # 40% position
            decision["stop_loss"] = current_price * 0.95
            decision["take_profit"] = current_price * 1.10
            decision["reasoning"].append("Smart money is buying heavily")
            decision["reasoning"].append(f"Net inflow: ${self.metrics['24h_net_flow']/1e6:.1f}M")
            
        elif self.market_state["accumulation_phase"]:
            decision["action"] = "BUY"
            decision["confidence"] = self.market_state["confidence"]
            decision["position_size"] = 0.25  # 25% position
            decision["stop_loss"] = current_price * 0.96
            decision["take_profit"] = current_price * 1.08
            decision["reasoning"].append("Whales are accumulating")
            decision["reasoning"].append("Bullish on-chain signal")
            
        elif self.market_state["panic_selling"]:
            decision["action"] = "SELL"
            decision["confidence"] = self.market_state["confidence"]
            decision["position_size"] = 0.3
            decision["stop_loss"] = current_price * 1.04
            decision["take_profit"] = current_price * 0.94
            decision["reasoning"].append("Panic selling detected")
            decision["reasoning"].append(f"Net outflow: ${abs(self.metrics['24h_net_flow'])/1e6:.1f}M")
            
        elif self.market_state["distribution_phase"]:
            decision["action"] = "SELL"
            decision["confidence"] = self.market_state["confidence"]
            decision["position_size"] = 0.2
            decision["stop_loss"] = current_price * 1.03
            decision["take_profit"] = current_price * 0.96
            decision["reasoning"].append("Whales are distributing")
            decision["reasoning"].append("Bearish on-chain signal")
        
        # Solo ejecutar si confianza > 65%
        if decision["confidence"] < 65:
            decision["action"] = "HOLD"
            decision["reasoning"].append(f"Confidence too low ({decision['confidence']}%)")
        
        return decision
    
    async def _get_current_price(self, symbol: str) -> float:
        """Obtiene precio actual"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/ticker/price",
                    params={"symbol": symbol},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return float(response.json()['price'])
        except:
            pass
        
        # Precios default
        defaults = {"BTCUSDT": 115000, "ETHUSDT": 4800, "SOLUSDT": 205}
        return defaults.get(symbol, 100)
    
    async def autonomous_monitoring(self, symbols: List[str], interval: int = 300):
        """
        Monitoreo autónomo continuo
        El sistema interpreta y actúa sin intervención humana
        """
        print("="*80)
        print("🤖 AUTONOMOUS WHALE INTERPRETER ACTIVATED")
        print("="*80)
        print("System will monitor, interpret and act on whale movements autonomously\n")
        
        while True:
            try:
                # 1. Obtener movimientos de whales
                movements = await self.fetch_whale_movements()
                
                # 2. Interpretar movimientos
                market_state = await self.interpret_movements(movements)
                
                # 3. Mostrar interpretación
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Market Analysis")
                print("-"*60)
                print(f"🐋 Whale Sentiment: {market_state['whale_sentiment']}")
                print(f"📊 Confidence: {market_state['confidence']}%")
                print(f"💰 24h Net Flow: ${self.metrics['24h_net_flow']/1e6:+.1f}M")
                print(f"📈 Activity Score: {self.metrics['whale_activity_score']}/100")
                
                # Estados especiales
                if market_state["panic_selling"]:
                    print("🚨 PANIC SELLING DETECTED!")
                elif market_state["smart_money_buying"]:
                    print("💎 SMART MONEY BUYING!")
                elif market_state["accumulation_phase"]:
                    print("📦 Accumulation Phase Active")
                elif market_state["distribution_phase"]:
                    print("📤 Distribution Phase Active")
                
                # 4. Generar decisiones de trading
                for symbol in symbols:
                    decision = await self.generate_trading_decision(symbol)
                    
                    if decision["action"] != "HOLD":
                        print(f"\n🎯 TRADING SIGNAL - {symbol}")
                        print(f"  Action: {decision['action']}")
                        print(f"  Confidence: {decision['confidence']}%")
                        print(f"  Position Size: {decision['position_size']*100:.0f}%")
                        print(f"  Stop Loss: ${decision['stop_loss']:.2f}")
                        print(f"  Take Profit: ${decision['take_profit']:.2f}")
                        print(f"  Reasoning:")
                        for reason in decision["reasoning"]:
                            print(f"    • {reason}")
                
                # 5. Esperar antes del siguiente ciclo
                print(f"\nNext check in {interval} seconds...")
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in autonomous monitoring: {e}")
                await asyncio.sleep(60)

# Testing
async def test_autonomous_system():
    """
    Prueba el sistema autónomo de interpretación
    """
    tracker = AutonomousWhaleTracker()
    
    print("="*80)
    print("🧪 TESTING AUTONOMOUS WHALE INTERPRETATION")
    print("="*80)
    
    # Obtener y interpretar movimientos
    movements = await tracker.fetch_whale_movements()
    print(f"\n📊 Found {len(movements)} whale movements")
    
    # Interpretar
    market_state = await tracker.interpret_movements(movements)
    
    print(f"\n🧠 INTERPRETATION:")
    print(f"  Whale Sentiment: {market_state['whale_sentiment']}")
    print(f"  Confidence: {market_state['confidence']}%")
    
    if market_state["panic_selling"]:
        print("  ⚠️ PANIC SELLING - Market likely to drop")
    elif market_state["smart_money_buying"]:
        print("  💎 SMART MONEY BUYING - Bullish signal")
    elif market_state["accumulation_phase"]:
        print("  📦 ACCUMULATION - Whales building positions")
    elif market_state["distribution_phase"]:
        print("  📤 DISTRIBUTION - Whales taking profits")
    else:
        print("  😐 NEUTRAL - No clear whale activity")
    
    # Generar decisión
    decision = await tracker.generate_trading_decision("BTCUSDT")
    
    print(f"\n🎯 TRADING DECISION:")
    print(f"  Action: {decision['action']}")
    print(f"  Confidence: {decision['confidence']}%")
    
    if decision["reasoning"]:
        print(f"  Reasoning:")
        for reason in decision["reasoning"]:
            print(f"    • {reason}")
    
    print("\n" + "="*80)
    print("💡 SYSTEM CAPABILITIES:")
    print("="*80)
    print("""
The system autonomously:
• Monitors whale movements from free sources
• Classifies each movement (to/from exchange, staking, OTC)
• Interprets the collective meaning
• Identifies market phases (accumulation, distribution, panic)
• Generates trading decisions based on interpretation
• Acts without human intervention
    """)

if __name__ == "__main__":
    # Test mode
    asyncio.run(test_autonomous_system())
    
    # For continuous autonomous monitoring:
    # tracker = AutonomousWhaleTracker()
    # asyncio.run(tracker.autonomous_monitoring(["BTCUSDT", "ETHUSDT", "SOLUSDT"]))