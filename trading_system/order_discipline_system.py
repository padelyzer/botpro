#!/usr/bin/env python3
"""
SISTEMA DE DISCIPLINA DE ÓRDENES
Previene errores de ejecución y FOMO en entradas
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import os

class OrderDisciplineSystem:
    """Sistema para prevenir errores de ejecución como el del domingo"""
    
    def __init__(self):
        self.config_file = "order_rules.json"
        self.binance_url = "https://api.binance.com/api/v3"
        self.active_orders = {}
        self.rules = self.load_rules()
        
    def load_rules(self) -> Dict:
        """Cargar reglas de disciplina"""
        default_rules = {
            "max_deviation_from_plan": 1.0,  # % máximo de desviación del plan
            "require_confirmation": True,     # Requiere confirmación para cambios
            "alert_on_impulse": True,        # Alerta en decisiones impulsivas
            "max_fomo_indicator": 70,         # Máximo indicador FOMO permitido
            "cooling_period_minutes": 15,     # Período de enfriamiento antes de cambiar plan
            "strict_mode": True               # Modo estricto - no permite desviaciones
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return default_rules
    
    async def get_current_price(self, symbol: str) -> float:
        """Obtener precio actual"""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.binance_url}/ticker/price",
                    params={"symbol": f"{symbol}USDT"}
                )
                if resp.status_code == 200:
                    return float(resp.json()['price'])
            except:
                pass
        return 0
    
    def analyze_sunday_mistake(self) -> Dict:
        """Analizar el error del domingo específicamente"""
        return {
            "fecha": "Domingo",
            "plan_original": {
                "entrada_objetivo": 201.00,
                "segunda_entrada": 198.00,
                "instrucción": "ESPERAR $201 y aumentar en $198"
            },
            "lo_que_pasó": {
                "precio_visto": "Bajando de $213 a $206",
                "acción_tomada": "Entrada prematura en $198.20",
                "error": "NO ESPERÓ a $201, entró directo en $198"
            },
            "errores_identificados": [
                "❌ FOMO - Miedo a que no bajara más",
                "❌ No respetó el plan original",
                "❌ Interpretó mal la instrucción (aumentar ≠ entrar)",
                "❌ No usó órdenes límite",
                "❌ Decisión emocional vs sistemática"
            ],
            "costo_del_error": {
                "entrada_real": 198.20,
                "precio_actual": 188.00,
                "pérdida": -303.00,
                "pérdida_porcentual": -5.13
            }
        }
    
    def create_order_checklist(self, plan: Dict) -> Dict:
        """Crear checklist de verificación antes de ejecutar"""
        return {
            "pre_orden_checklist": [
                {
                    "pregunta": "¿El precio está EN o MUY CERCA del target?",
                    "respuesta_correcta": "SÍ",
                    "tu_caso_domingo": "NO - Estaba en $206, target era $201",
                    "acción": "ESPERAR"
                },
                {
                    "pregunta": "¿Estás siguiendo el plan EXACTO?",
                    "respuesta_correcta": "SÍ",
                    "tu_caso_domingo": "NO - Plan era esperar $201 primero",
                    "acción": "REVISAR PLAN"
                },
                {
                    "pregunta": "¿Estás actuando por FOMO?",
                    "respuesta_correcta": "NO",
                    "tu_caso_domingo": "SÍ - Miedo a que no bajara más",
                    "acción": "COOLING PERIOD 15 MIN"
                },
                {
                    "pregunta": "¿Tienes órdenes límite configuradas?",
                    "respuesta_correcta": "SÍ",
                    "tu_caso_domingo": "NO - Entrada manual impulsiva",
                    "acción": "CONFIGURAR LÍMITES"
                },
                {
                    "pregunta": "¿La instrucción dice ENTRAR o AUMENTAR?",
                    "respuesta_correcta": "CLARA",
                    "tu_caso_domingo": "AUMENTAR ≠ ENTRAR INICIAL",
                    "acción": "RELEER INSTRUCCIONES"
                }
            ],
            "debe_cumplir": "5/5 para proceder",
            "tu_score_domingo": "0/5 - NO DEBISTE ENTRAR"
        }
    
    def create_prevention_system(self) -> Dict:
        """Sistema de prevención para futuros trades"""
        return {
            "reglas_de_oro": {
                "1": "NUNCA entrar sin que el precio toque el target",
                "2": "SIEMPRE usar órdenes límite, NUNCA market",
                "3": "AUMENTAR significa ADD a posición existente",
                "4": "Si sientes FOMO, es señal de NO ENTRAR",
                "5": "Plan escrito > Decisiones en caliente"
            },
            
            "sistema_de_órdenes": {
                "paso_1": "Escribir plan en papel/digital",
                "paso_2": "Configurar órdenes límite en exchange",
                "paso_3": "Alejarse de la pantalla",
                "paso_4": "Dejar que las órdenes se ejecuten solas",
                "paso_5": "Revisar solo cada 4 horas"
            },
            
            "alertas_automáticas": {
                "precio_cerca_target": "Alerta cuando esté a 1% del target",
                "orden_ejecutada": "Notificación de ejecución",
                "stop_loss": "Configurar SL inmediatamente",
                "no_manual": "PROHIBIDO trading manual"
            },
            
            "protocolo_domingo": {
                "descripción": "Protocolo especial para días de baja liquidez",
                "reglas": [
                    "NO trading manual en domingos",
                    "Órdenes configuradas el viernes",
                    "Límites 1% más conservadores",
                    "No cambiar plan por 'corazonadas'"
                ]
            }
        }
    
    def calculate_fomo_index(self, market_data: Dict) -> float:
        """Calcular índice FOMO actual"""
        fomo_score = 0
        
        # Factores que aumentan FOMO
        if market_data.get('price_dropping', False):
            fomo_score += 20  # "Se está yendo sin mí"
        
        if market_data.get('volatility_high', False):
            fomo_score += 25  # "Movimientos grandes"
        
        if market_data.get('social_hype', False):
            fomo_score += 20  # "Todos están hablando"
        
        if market_data.get('near_target', False):
            fomo_score += 15  # "Casi llega"
        
        if market_data.get('sunday', False):
            fomo_score += 20  # "Baja liquidez, oportunidad"
        
        return min(fomo_score, 100)
    
    async def validate_order(self, order: Dict) -> Tuple[bool, List[str]]:
        """Validar orden contra las reglas"""
        warnings = []
        should_proceed = True
        
        # Verificar desviación del plan
        if abs(order['price'] - order['planned_price']) / order['planned_price'] > 0.01:
            warnings.append("⚠️ DESVIACIÓN DEL PLAN DETECTADA")
            if self.rules['strict_mode']:
                should_proceed = False
        
        # Verificar FOMO
        fomo_index = self.calculate_fomo_index(order.get('market_data', {}))
        if fomo_index > self.rules['max_fomo_indicator']:
            warnings.append(f"🚨 FOMO ALTO: {fomo_index}/100")
            should_proceed = False
        
        # Verificar cooling period
        if order.get('is_impulse_decision', False):
            warnings.append("⏰ REQUIERE COOLING PERIOD DE 15 MINUTOS")
            should_proceed = False
        
        return should_proceed, warnings
    
    async def generate_report(self):
        """Generar reporte completo"""
        print("\n" + "="*80)
        print("🎯 SISTEMA DE DISCIPLINA DE ÓRDENES")
        print("="*80)
        
        # Análisis del error del domingo
        sunday_analysis = self.analyze_sunday_mistake()
        
        print("\n📅 ANÁLISIS DEL ERROR DEL DOMINGO:")
        print("-"*80)
        print(f"Plan original: ESPERAR ${sunday_analysis['plan_original']['entrada_objetivo']}")
        print(f"Lo que hiciste: Entrar en ${sunday_analysis['lo_que_pasó']['acción_tomada']}")
        print(f"Costo del error: ${sunday_analysis['costo_del_error']['pérdida']:.2f}")
        
        print("\n❌ ERRORES IDENTIFICADOS:")
        for error in sunday_analysis['errores_identificados']:
            print(f"   {error}")
        
        # Checklist
        checklist = self.create_order_checklist({})
        print("\n✅ CHECKLIST PRE-ORDEN (Lo que debiste verificar):")
        print("-"*80)
        for item in checklist['pre_orden_checklist']:
            print(f"\n   ❓ {item['pregunta']}")
            print(f"   ✅ Respuesta correcta: {item['respuesta_correcta']}")
            print(f"   ❌ Tu caso: {item['tu_caso_domingo']}")
            print(f"   ➡️ Acción: {item['acción']}")
        
        # Sistema de prevención
        prevention = self.create_prevention_system()
        print("\n🛡️ SISTEMA DE PREVENCIÓN FUTURO:")
        print("-"*80)
        
        print("\n📜 REGLAS DE ORO:")
        for num, regla in prevention['reglas_de_oro'].items():
            print(f"   {num}. {regla}")
        
        print("\n🤖 SISTEMA DE ÓRDENES AUTOMÁTICO:")
        for paso, accion in prevention['sistema_de_órdenes'].items():
            print(f"   {paso}: {accion}")
        
        print("\n📱 CONFIGURACIÓN RECOMENDADA:")
        print("-"*80)
        print("   1. Configurar órdenes límite en Binance:")
        print(f"      • Orden 1: BUY LIMIT SOL @ $201.00")
        print(f"      • Orden 2: BUY LIMIT SOL @ $198.00")
        print("   2. Configurar Stop Loss inmediato:")
        print(f"      • SL: $195.00 (-2.5%)")
        print("   3. Alejarse de la pantalla")
        print("   4. Revisar cada 4 horas máximo")
        
        # Ejemplo actual
        current_sol = await self.get_current_price("SOL")
        print("\n📊 APLICACIÓN ACTUAL:")
        print("-"*80)
        print(f"   SOL actual: ${current_sol:.2f}")
        print("   Plan correcto para salir:")
        print("      1. Esperar rebote a $192-194")
        print("      2. Configurar SELL LIMIT @ $193")
        print("      3. NO salir en pánico ahora")
        print("      4. NO promediar pérdidas")
        
        print("\n⚡ COMANDOS PARA CONFIGURAR:")
        print("-"*80)
        print("   # En Binance (ejemplo):")
        print("   - Limit Sell Order: 29.82 SOL @ $193.00")
        print("   - Stop Loss: 29.82 SOL @ $185.00")
        print("   - OCO Order recomendada")
        
        print("\n" + "="*80)
        print("💡 RECORDATORIO FINAL:")
        print("   'El plan no es negociable. Si dudas, no entres.'")
        print("   'Las mejores oportunidades son las que dejas pasar en mal momento.'")
        print("="*80)

async def main():
    system = OrderDisciplineSystem()
    await system.generate_report()

if __name__ == "__main__":
    asyncio.run(main())