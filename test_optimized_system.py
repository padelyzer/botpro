#!/usr/bin/env python3
"""
Sistema de pruebas completo para validar la integración de API optimizada
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemTester:
    """Tester completo del sistema optimizado"""
    
    def __init__(self):
        self.results = {
            'api_tests': {},
            'performance_tests': {},
            'integration_tests': {},
            'continuous_operation_tests': {}
        }
        
    def test_api_functionality(self):
        """Prueba funcionalidad básica de la API"""
        logger.info("🧪 Iniciando pruebas de funcionalidad API...")
        
        try:
            from binance_integration import BinanceConnector
            
            # Test 1: Inicialización con API optimizada
            logger.info("📡 Test 1: Inicialización con API optimizada")
            connector_opt = BinanceConnector(use_optimized=True)
            self.results['api_tests']['initialization_optimized'] = True
            logger.info("✅ API optimizada inicializada correctamente")
            
            # Test 2: Inicialización con CCXT tradicional
            logger.info("📡 Test 2: Inicialización con CCXT tradicional")
            connector_ccxt = BinanceConnector(use_optimized=False)
            self.results['api_tests']['initialization_ccxt'] = True
            logger.info("✅ CCXT tradicional inicializado correctamente")
            
            # Test 3: Obtener datos históricos (API optimizada)
            logger.info("📊 Test 3: Datos históricos - API optimizada")
            start_time = time.time()
            df_opt = connector_opt.get_historical_data('BTCUSDT', '15m', limit=100)
            opt_time = time.time() - start_time
            
            self.results['api_tests']['historical_data_optimized'] = {
                'success': not df_opt.empty,
                'rows': len(df_opt),
                'time': opt_time,
                'last_close': float(df_opt['close'].iloc[-1]) if not df_opt.empty else 0
            }
            logger.info(f"✅ API optimizada: {len(df_opt)} velas en {opt_time:.3f}s")
            
            # Test 4: Obtener datos históricos (CCXT)
            logger.info("📊 Test 4: Datos históricos - CCXT")
            start_time = time.time()
            df_ccxt = connector_ccxt.get_historical_data('BTC/USDT', '15m', limit=100)
            ccxt_time = time.time() - start_time
            
            self.results['api_tests']['historical_data_ccxt'] = {
                'success': not df_ccxt.empty,
                'rows': len(df_ccxt),
                'time': ccxt_time,
                'last_close': float(df_ccxt['close'].iloc[-1]) if not df_ccxt.empty else 0
            }
            logger.info(f"✅ CCXT: {len(df_ccxt)} velas en {ccxt_time:.3f}s")
            
            # Test 5: Precio actual (ambas APIs)
            logger.info("💰 Test 5: Precios actuales")
            price_opt = connector_opt.get_current_price('BTCUSDT')
            price_ccxt = connector_ccxt.get_current_price('BTC/USDT')
            
            self.results['api_tests']['current_price'] = {
                'optimized': price_opt,
                'ccxt': price_ccxt,
                'difference': abs(price_opt - price_ccxt),
                'percentage_diff': abs(price_opt - price_ccxt) / price_ccxt * 100 if price_ccxt > 0 else 0
            }
            
            logger.info(f"✅ Precio optimizada: ${price_opt:,.2f}")
            logger.info(f"✅ Precio CCXT: ${price_ccxt:,.2f}")
            logger.info(f"📊 Diferencia: {abs(price_opt - price_ccxt):.2f} ({abs(price_opt - price_ccxt) / price_ccxt * 100:.4f}%)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en pruebas de API: {e}")
            self.results['api_tests']['error'] = str(e)
            return False
    
    def test_performance_comparison(self):
        """Compara performance entre ambas APIs"""
        logger.info("🚀 Iniciando pruebas de performance...")
        
        try:
            from binance_integration import BinanceConnector
            
            connector_opt = BinanceConnector(use_optimized=True)
            connector_ccxt = BinanceConnector(use_optimized=False)
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
            timeframes = ['5m', '15m', '1h']
            
            results_opt = []
            results_ccxt = []
            
            for symbol in symbols:
                for tf in timeframes:
                    # API Optimizada
                    start_time = time.time()
                    df_opt = connector_opt.get_historical_data(symbol, tf, limit=50)
                    opt_time = time.time() - start_time
                    results_opt.append(opt_time)
                    
                    # CCXT
                    start_time = time.time()
                    df_ccxt = connector_ccxt.get_historical_data(symbol.replace('USDT', '/USDT'), tf, limit=50)
                    ccxt_time = time.time() - start_time
                    results_ccxt.append(ccxt_time)
                    
                    logger.info(f"📊 {symbol} {tf}: Opt={opt_time:.3f}s, CCXT={ccxt_time:.3f}s")
                    
                    # Pequeña pausa para no saturar la API
                    time.sleep(0.1)
            
            avg_opt = sum(results_opt) / len(results_opt)
            avg_ccxt = sum(results_ccxt) / len(results_ccxt)
            
            self.results['performance_tests'] = {
                'optimized_avg': avg_opt,
                'ccxt_avg': avg_ccxt,
                'improvement_percentage': (avg_ccxt - avg_opt) / avg_ccxt * 100,
                'total_requests': len(results_opt),
                'optimized_times': results_opt,
                'ccxt_times': results_ccxt
            }
            
            logger.info(f"📊 Promedio API optimizada: {avg_opt:.3f}s")
            logger.info(f"📊 Promedio CCXT: {avg_ccxt:.3f}s")
            logger.info(f"🚀 Mejora de performance: {(avg_ccxt - avg_opt) / avg_ccxt * 100:.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en pruebas de performance: {e}")
            self.results['performance_tests']['error'] = str(e)
            return False
    
    def test_signal_analytics_integration(self):
        """Prueba integración con sistema de análisis de señales"""
        logger.info("🔬 Iniciando pruebas de integración con análisis de señales...")
        
        try:
            from signal_analytics import SignalAnalytics
            
            # Crear analizador
            analyzer = SignalAnalytics()
            
            # Crear señal de prueba
            test_signal = {
                'symbol': 'XRPUSDT',
                'action': 'BUY',
                'entry_price': 2.88,
                'confidence': 75,
                'philosopher': 'TestBot',
                'timestamp': datetime.now().isoformat()
            }
            
            # Analizar señal
            start_time = time.time()
            analysis = analyzer.analyze_signal(test_signal)
            analysis_time = time.time() - start_time
            
            self.results['integration_tests']['signal_analysis'] = {
                'success': analysis is not None,
                'analysis_time': analysis_time,
                'signal_score': analysis.get('total_score', 0) if analysis else 0,
                'has_technical_analysis': 'technical_analysis' in analysis if analysis else False,
                'has_risk_assessment': 'risk_assessment' in analysis if analysis else False
            }
            
            if analysis:
                logger.info(f"✅ Análisis completado en {analysis_time:.3f}s")
                logger.info(f"📊 Score total: {analysis.get('total_score', 'N/A')}")
                logger.info(f"🎯 Recomendación: {analysis.get('recommendation', 'N/A')}")
            else:
                logger.warning("⚠️ Análisis retornó None")
            
            return analysis is not None
            
        except Exception as e:
            logger.error(f"❌ Error en pruebas de integración: {e}")
            self.results['integration_tests']['error'] = str(e)
            return False
    
    def test_continuous_operation(self, duration_minutes: int = 2):
        """Prueba operación continua del sistema"""
        logger.info(f"⏰ Iniciando prueba de operación continua ({duration_minutes} minutos)...")
        
        try:
            from binance_integration import BinanceConnector
            
            connector = BinanceConnector(use_optimized=True)
            
            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)
            
            operations = []
            errors = []
            
            while time.time() < end_time:
                try:
                    # Operación 1: Obtener precio
                    op_start = time.time()
                    price = connector.get_current_price('BTCUSDT')
                    price_time = time.time() - op_start
                    
                    # Operación 2: Obtener datos históricos
                    op_start = time.time()
                    df = connector.get_historical_data('BTCUSDT', '15m', limit=10)
                    data_time = time.time() - op_start
                    
                    operations.append({
                        'timestamp': datetime.now().isoformat(),
                        'price': price,
                        'price_time': price_time,
                        'data_rows': len(df),
                        'data_time': data_time,
                        'total_time': price_time + data_time
                    })
                    
                    logger.info(f"✅ Operación OK - Precio: ${price:,.2f}, Datos: {len(df)} velas")
                    
                except Exception as e:
                    errors.append({
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e)
                    })
                    logger.error(f"❌ Error en operación: {e}")
                
                # Pausa de 10 segundos
                time.sleep(10)
            
            success_rate = len(operations) / (len(operations) + len(errors)) * 100 if (len(operations) + len(errors)) > 0 else 0
            avg_operation_time = sum(op['total_time'] for op in operations) / len(operations) if operations else 0
            
            self.results['continuous_operation_tests'] = {
                'duration_minutes': duration_minutes,
                'total_operations': len(operations),
                'total_errors': len(errors),
                'success_rate': success_rate,
                'avg_operation_time': avg_operation_time,
                'operations': operations[-5:],  # Últimas 5 operaciones
                'errors': errors
            }
            
            logger.info(f"📊 Operaciones completadas: {len(operations)}")
            logger.info(f"❌ Errores: {len(errors)}")
            logger.info(f"✅ Tasa de éxito: {success_rate:.1f}%")
            logger.info(f"⚡ Tiempo promedio: {avg_operation_time:.3f}s")
            
            return success_rate > 90
            
        except Exception as e:
            logger.error(f"❌ Error en pruebas de operación continua: {e}")
            self.results['continuous_operation_tests']['error'] = str(e)
            return False
    
    def generate_report(self) -> Dict:
        """Genera reporte completo de las pruebas"""
        
        report = {
            'test_summary': {
                'timestamp': datetime.now().isoformat(),
                'api_tests_passed': 'error' not in self.results['api_tests'],
                'performance_tests_passed': 'error' not in self.results['performance_tests'],
                'integration_tests_passed': 'error' not in self.results['integration_tests'],
                'continuous_tests_passed': 'error' not in self.results['continuous_operation_tests']
            },
            'detailed_results': self.results
        }
        
        # Calcular score general
        total_tests = 4
        passed_tests = sum([
            report['test_summary']['api_tests_passed'],
            report['test_summary']['performance_tests_passed'],
            report['test_summary']['integration_tests_passed'],
            report['test_summary']['continuous_tests_passed']
        ])
        
        report['overall_score'] = (passed_tests / total_tests) * 100
        
        return report
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        logger.info("🚀 Iniciando suite completa de pruebas del sistema optimizado...")
        
        # Ejecutar todas las pruebas
        test_results = []
        test_results.append(self.test_api_functionality())
        test_results.append(self.test_performance_comparison())
        test_results.append(self.test_signal_analytics_integration())
        test_results.append(self.test_continuous_operation(duration_minutes=1))  # 1 minuto para test rápido
        
        # Generar reporte
        report = self.generate_report()
        
        # Guardar reporte
        with open(f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Mostrar resumen
        logger.info("📊 RESUMEN DE PRUEBAS")
        logger.info("=" * 50)
        logger.info(f"✅ Pruebas de API: {'PASÓ' if report['test_summary']['api_tests_passed'] else 'FALLÓ'}")
        logger.info(f"🚀 Pruebas de Performance: {'PASÓ' if report['test_summary']['performance_tests_passed'] else 'FALLÓ'}")
        logger.info(f"🔬 Pruebas de Integración: {'PASÓ' if report['test_summary']['integration_tests_passed'] else 'FALLÓ'}")
        logger.info(f"⏰ Pruebas de Operación Continua: {'PASÓ' if report['test_summary']['continuous_tests_passed'] else 'FALLÓ'}")
        logger.info("=" * 50)
        logger.info(f"🎯 SCORE GENERAL: {report['overall_score']:.1f}%")
        
        if report['overall_score'] >= 75:
            logger.info("🎉 ¡SISTEMA LISTO PARA PRODUCCIÓN!")
        else:
            logger.warning("⚠️ Sistema necesita ajustes antes de producción")
        
        return report

if __name__ == "__main__":
    tester = SystemTester()
    report = tester.run_all_tests()