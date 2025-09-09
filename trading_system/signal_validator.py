#!/usr/bin/env python3
"""
VALIDADOR UNIVERSAL DE SEÑALES
Sistema que valida CUALQUIER señal antes de ejecutarla
Previene errores de interpretación y FOMO
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import re

class SignalValidator:
    """Validador que analiza y corrige señales antes de ejecución"""
    
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.validation_history = []
        
    async def get_market_data(self, symbol: str) -> Dict:
        """Obtener datos de mercado actuales"""
        async with httpx.AsyncClient() as client:
            try:
                # Precio actual
                price_resp = await client.get(
                    f"{self.binance_url}/ticker/price",
                    params={"symbol": f"{symbol}USDT"}
                )
                
                # Datos 24h
                stats_resp = await client.get(
                    f"{self.binance_url}/ticker/24hr",
                    params={"symbol": f"{symbol}USDT"}
                )
                
                if price_resp.status_code == 200 and stats_resp.status_code == 200:
                    price_data = price_resp.json()
                    stats_data = stats_resp.json()
                    
                    return {
                        'current_price': float(price_data['price']),
                        'high_24h': float(stats_data['highPrice']),
                        'low_24h': float(stats_data['lowPrice']),
                        'change_24h': float(stats_data['priceChangePercent']),
                        'volume': float(stats_data['volume'])
                    }
            except Exception as e:
                print(f"Error obteniendo datos: {e}")
        return {}
    
    def parse_signal(self, signal_text: str) -> Dict:
        """Parsear cualquier formato de señal"""
        signal_data = {
            'symbol': None,
            'action': None,
            'entries': [],
            'targets': [],
            'stop_loss': None,
            'leverage': None,
            'notes': [],
            'raw_text': signal_text
        }
        
        # Detectar símbolo (SOL, BTC, ETH, etc.)
        symbols = re.findall(r'\b(BTC|ETH|SOL|BNB|ADA|DOT|AVAX|MATIC|LINK)\b', signal_text.upper())
        if symbols:
            signal_data['symbol'] = symbols[0]
        
        # Detectar acción (LONG, SHORT, BUY, SELL)
        if any(word in signal_text.upper() for word in ['LONG', 'BUY', 'COMPRA', 'ENTRADA']):
            signal_data['action'] = 'LONG'
        elif any(word in signal_text.upper() for word in ['SHORT', 'SELL', 'VENTA']):
            signal_data['action'] = 'SHORT'
        
        # Detectar precios (números con $ o seguidos de USDT)
        prices = re.findall(r'\$?([\d,]+\.?\d*)', signal_text)
        prices = [float(p.replace(',', '')) for p in prices if float(p.replace(',', '')) > 1]
        
        # Detectar palabras clave para clasificar precios
        for i, price in enumerate(prices):
            text_before = signal_text[:signal_text.find(str(price))].lower()
            if any(word in text_before for word in ['entrada', 'entry', 'compra', 'buy', 'esperar']):
                signal_data['entries'].append(price)
            elif any(word in text_before for word in ['target', 'objetivo', 'tp', 'salida']):
                signal_data['targets'].append(price)
            elif any(word in text_before for word in ['stop', 'sl', 'liquidación']):
                signal_data['stop_loss'] = price
        
        # Si no clasificó los precios, asumir por orden
        if not signal_data['entries'] and prices:
            signal_data['entries'] = prices[:2]  # Primeros 2 son entradas
            if len(prices) > 2:
                signal_data['targets'] = prices[2:]  # Resto son targets
        
        # Detectar "aumentar" vs "entrar"
        if 'AUMENTAR' in signal_text.upper() or 'ADD' in signal_text.upper():
            signal_data['notes'].append("⚠️ AUMENTAR significa añadir a posición existente, NO entrada inicial")
        
        return signal_data
    
    async def validate_signal(self, signal_text: str, current_position: Dict = None) -> Dict:
        """Validar señal completa"""
        # Parsear señal
        signal = self.parse_signal(signal_text)
        
        # Obtener datos de mercado
        if signal['symbol']:
            market_data = await self.get_market_data(signal['symbol'])
        else:
            market_data = {}
        
        validation_result = {
            'signal': signal,
            'market_data': market_data,
            'validations': [],
            'warnings': [],
            'errors': [],
            'score': 0,
            'recommendation': '',
            'corrected_signal': {}
        }
        
        # VALIDACIONES CRÍTICAS
        
        # 1. Validar si el precio actual está cerca de la entrada
        if signal['entries'] and market_data.get('current_price'):
            current = market_data['current_price']
            for entry in signal['entries']:
                distance_pct = abs(current - entry) / current * 100
                
                if distance_pct < 1:
                    validation_result['validations'].append(f"✅ Entrada ${entry} está cerca del precio actual ${current:.2f}")
                    validation_result['score'] += 20
                elif distance_pct < 3:
                    validation_result['warnings'].append(f"⚠️ Entrada ${entry} está a {distance_pct:.1f}% del precio actual")
                    validation_result['score'] += 10
                else:
                    validation_result['errors'].append(f"❌ Entrada ${entry} está muy lejos ({distance_pct:.1f}%) del precio actual ${current:.2f}")
                    validation_result['score'] -= 20
        
        # 2. Validar si es "AUMENTAR" sin posición existente
        if 'AUMENTAR' in signal_text.upper():
            if not current_position or current_position.get('size', 0) == 0:
                validation_result['errors'].append("❌ CRÍTICO: Dice AUMENTAR pero NO hay posición existente")
                validation_result['errors'].append("❌ AUMENTAR ≠ ENTRADA INICIAL")
                validation_result['score'] -= 50
            else:
                validation_result['validations'].append("✅ AUMENTAR es válido, hay posición existente")
                validation_result['score'] += 20
        
        # 3. Validar riesgo/recompensa
        if signal['entries'] and signal['targets'] and signal['stop_loss']:
            entry = signal['entries'][0]
            target = signal['targets'][0] if signal['targets'] else entry * 1.02
            stop = signal['stop_loss']
            
            risk = abs(entry - stop)
            reward = abs(target - entry)
            
            if risk > 0:
                rr_ratio = reward / risk
                if rr_ratio >= 2:
                    validation_result['validations'].append(f"✅ R:R ratio bueno: {rr_ratio:.1f}:1")
                    validation_result['score'] += 20
                elif rr_ratio >= 1.5:
                    validation_result['warnings'].append(f"⚠️ R:R ratio aceptable: {rr_ratio:.1f}:1")
                    validation_result['score'] += 10
                else:
                    validation_result['errors'].append(f"❌ R:R ratio malo: {rr_ratio:.1f}:1")
                    validation_result['score'] -= 20
        
        # 4. Validar condiciones de mercado
        if market_data:
            # RSI aproximado basado en cambio 24h
            change = market_data.get('change_24h', 0)
            
            if signal['action'] == 'LONG':
                if change < -5:
                    validation_result['validations'].append("✅ Buen momento para LONG (oversold)")
                    validation_result['score'] += 15
                elif change > 5:
                    validation_result['warnings'].append("⚠️ Cuidado: LONG en zona de sobrecompra")
                    validation_result['score'] -= 10
            
            elif signal['action'] == 'SHORT':
                if change > 5:
                    validation_result['validations'].append("✅ Buen momento para SHORT (overbought)")
                    validation_result['score'] += 15
                elif change < -5:
                    validation_result['warnings'].append("⚠️ Cuidado: SHORT en zona de sobreventa")
                    validation_result['score'] -= 10
        
        # 5. Detectar FOMO
        fomo_indicators = 0
        if 'URGENTE' in signal_text.upper():
            fomo_indicators += 1
        if 'AHORA' in signal_text.upper() or 'NOW' in signal_text.upper():
            fomo_indicators += 1
        if 'NO TE LO PIERDAS' in signal_text.upper():
            fomo_indicators += 1
        if '🚀🚀🚀' in signal_text:
            fomo_indicators += 1
        
        if fomo_indicators >= 2:
            validation_result['warnings'].append("⚠️ ALERTA FOMO: Señal parece urgente/emocional")
            validation_result['score'] -= 15
        
        # 6. Validar día y hora
        now = datetime.now()
        if now.weekday() == 6:  # Domingo
            validation_result['warnings'].append("⚠️ DOMINGO: Baja liquidez, mayor riesgo")
            validation_result['score'] -= 10
        
        # GENERAR RECOMENDACIÓN
        if validation_result['score'] >= 50:
            validation_result['recommendation'] = "✅ SEÑAL VÁLIDA - Proceder con precaución"
        elif validation_result['score'] >= 20:
            validation_result['recommendation'] = "⚠️ SEÑAL DUDOSA - Revisar warnings antes de ejecutar"
        else:
            validation_result['recommendation'] = "❌ NO EJECUTAR - Demasiados problemas detectados"
        
        # SEÑAL CORREGIDA
        if signal['entries'] and market_data.get('current_price'):
            current = market_data['current_price']
            
            # Ajustar entradas si están muy lejos
            corrected_entries = []
            for entry in signal['entries']:
                if abs(current - entry) / current > 0.03:  # Más de 3% de distancia
                    # Ajustar a un nivel más cercano
                    if entry > current:  # Entrada por encima
                        corrected_entries.append(round(current * 1.01, 2))
                    else:  # Entrada por debajo
                        corrected_entries.append(round(current * 0.99, 2))
                else:
                    corrected_entries.append(entry)
            
            validation_result['corrected_signal'] = {
                'symbol': signal['symbol'],
                'action': signal['action'],
                'entries': corrected_entries,
                'current_price': current,
                'stop_loss': signal['stop_loss'] or round(current * 0.97, 2),  # -3% si no hay SL
                'targets': signal['targets'] or [round(current * 1.02, 2), round(current * 1.03, 2)],
                'max_position_size': '10% del portafolio máximo',
                'orders_to_place': []
            }
            
            # Generar órdenes específicas
            for i, entry in enumerate(corrected_entries):
                validation_result['corrected_signal']['orders_to_place'].append({
                    'type': 'LIMIT BUY' if signal['action'] == 'LONG' else 'LIMIT SELL',
                    'price': entry,
                    'size': '50%' if i == 0 else '50%',  # Split en 2 entradas
                    'note': f"Entrada {i+1}"
                })
        
        return validation_result
    
    async def validate_and_report(self, signal_text: str, current_position: Dict = None):
        """Validar señal y generar reporte detallado"""
        print("\n" + "="*80)
        print("🔍 VALIDADOR UNIVERSAL DE SEÑALES")
        print("="*80)
        
        print("\n📝 SEÑAL RECIBIDA:")
        print("-"*80)
        print(signal_text)
        
        # Validar
        result = await self.validate_signal(signal_text, current_position)
        
        print("\n📊 ANÁLISIS DE LA SEÑAL:")
        print("-"*80)
        signal = result['signal']
        print(f"   Símbolo: {signal['symbol'] or 'NO DETECTADO'}")
        print(f"   Acción: {signal['action'] or 'NO DETECTADA'}")
        print(f"   Entradas: {signal['entries'] or 'NO DETECTADAS'}")
        print(f"   Targets: {signal['targets'] or 'NO DETECTADOS'}")
        print(f"   Stop Loss: {signal['stop_loss'] or 'NO DETECTADO'}")
        
        if result['market_data']:
            print(f"\n📈 MERCADO ACTUAL:")
            print(f"   Precio: ${result['market_data']['current_price']:.2f}")
            print(f"   Cambio 24h: {result['market_data']['change_24h']:.2f}%")
            print(f"   Rango 24h: ${result['market_data']['low_24h']:.2f} - ${result['market_data']['high_24h']:.2f}")
        
        print("\n✅ VALIDACIONES PASADAS:")
        for validation in result['validations']:
            print(f"   {validation}")
        
        if result['warnings']:
            print("\n⚠️ ADVERTENCIAS:")
            for warning in result['warnings']:
                print(f"   {warning}")
        
        if result['errors']:
            print("\n❌ ERRORES CRÍTICOS:")
            for error in result['errors']:
                print(f"   {error}")
        
        print(f"\n📊 SCORE FINAL: {result['score']}/100")
        print(f"🎯 RECOMENDACIÓN: {result['recommendation']}")
        
        if result['corrected_signal'] and result['corrected_signal'].get('orders_to_place'):
            print("\n💡 SEÑAL CORREGIDA Y ÓRDENES SUGERIDAS:")
            print("-"*80)
            cs = result['corrected_signal']
            print(f"   Precio actual: ${cs['current_price']:.2f}")
            print(f"   Entradas ajustadas: {cs['entries']}")
            print(f"   Stop Loss: ${cs['stop_loss']}")
            print(f"   Targets: {cs['targets']}")
            
            print("\n📋 ÓRDENES A COLOCAR:")
            for order in cs['orders_to_place']:
                print(f"   • {order['type']} @ ${order['price']} ({order['size']}) - {order['note']}")
        
        print("\n" + "="*80)
        print("⚡ PROTOCOLO DE EJECUCIÓN:")
        print("-"*80)
        
        if result['score'] >= 50:
            print("   1. ✅ Configurar órdenes límite como se indica arriba")
            print("   2. ✅ Configurar stop loss INMEDIATAMENTE")
            print("   3. ✅ No usar más del 10% del portafolio")
            print("   4. ✅ Alejarse de la pantalla después de configurar")
        else:
            print("   1. ❌ NO EJECUTAR esta señal")
            print("   2. ⏰ Esperar mejor oportunidad")
            print("   3. 📊 Revisar los errores identificados")
            print("   4. 🎯 Buscar señales con score > 50")
        
        print("="*80)
        
        return result

async def main():
    """Ejemplo de uso del validador"""
    validator = SignalValidator()
    
    # Ejemplo 1: Tu señal del domingo
    print("\n🔍 EJEMPLO 1: Tu señal del domingo")
    signal_domingo = """
    SOL bajando de $213 a $206
    ESPERAR $201 para entrada
    AUMENTAR posición en $198
    Stop loss: $195
    """
    
    # Sin posición existente (tu error)
    await validator.validate_and_report(signal_domingo, current_position={'size': 0})
    
    # Ejemplo 2: Una señal típica de grupo
    print("\n🔍 EJEMPLO 2: Señal típica de grupo")
    signal_grupo = """
    🚀🚀🚀 URGENTE!!!
    LONG SOL AHORA!
    Entrada: $188-190
    Targets: $195, $200, $210
    SL: $185
    Leverage: 10x
    NO TE LO PIERDAS! 🚀
    """
    
    await validator.validate_and_report(signal_grupo)
    
    # Ejemplo 3: Señal bien estructurada
    print("\n🔍 EJEMPLO 3: Señal profesional")
    signal_pro = """
    BTC/USDT - LONG
    Entrada 1: $110,500
    Entrada 2: $109,800
    Target 1: $112,000
    Target 2: $113,500
    Stop Loss: $108,500
    Risk: 2% del portafolio
    """
    
    await validator.validate_and_report(signal_pro)

if __name__ == "__main__":
    asyncio.run(main())