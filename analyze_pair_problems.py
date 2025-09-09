#!/usr/bin/env python3
"""
Análisis de problemas específicos por par
Identifica por qué algunos pares tienen mal rendimiento
"""

import pandas as pd
import numpy as np

def analyze_problems():
    """Analiza los resultados y identifica problemas específicos"""
    
    # Cargar resultados del backtest completo
    try:
        df = pd.read_csv('complete_pair_backtest_results.csv')
    except:
        print("❌ No se encontró complete_pair_backtest_results.csv")
        return
    
    print("="*60)
    print("ANÁLISIS DE PROBLEMAS POR PAR")
    print("="*60)
    
    # Agrupar por par
    pairs = df.groupby('symbol')
    
    for symbol, group in pairs:
        print(f"\n🔍 {symbol}:")
        print("-" * 40)
        
        strategy = group.iloc[0]['strategy']
        print(f"Estrategia: {strategy}")
        
        # Analizar cada timeframe
        problems = []
        solutions = []
        
        for _, row in group.iterrows():
            tf = row['interval']
            trades = row['total_trades']
            wr = row['win_rate']
            ret = row['total_return']
            
            print(f"  {tf}: {trades} trades, {wr:.1f}% WR, {ret:.2f}% return")
            
            # Identificar problemas específicos
            if trades == 0:
                problems.append(f"{tf}: No genera trades (filtros muy estrictos)")
                solutions.append(f"{tf}: Relajar filtros - RSI, change_pct, confidence")
            
            elif wr < 30:
                problems.append(f"{tf}: Win rate muy bajo ({wr:.1f}%)")
                if strategy == "MEAN_REVERSION":
                    solutions.append(f"{tf}: ATR más amplio, RSI más extremo")
                elif strategy == "TREND_FOLLOWING":
                    solutions.append(f"{tf}: Mejores filtros de tendencia, MACD más estricto")
                elif strategy == "MOMENTUM":
                    solutions.append(f"{tf}: Volumen más alto, breakouts más fuertes")
            
            elif trades > 0 and ret < -5:
                problems.append(f"{tf}: Demasiadas pérdidas ({ret:.1f}%)")
                solutions.append(f"{tf}: Stops más amplios, mejor entry timing")
        
        # Mostrar problemas y soluciones
        if problems:
            print("\n  ❌ PROBLEMAS IDENTIFICADOS:")
            for problem in problems:
                print(f"    • {problem}")
            
            print("\n  💡 SOLUCIONES PROPUESTAS:")
            for solution in solutions:
                print(f"    ✓ {solution}")
        else:
            print("\n  ✅ Par funcionando bien")
    
    print("\n" + "="*60)
    print("RECOMENDACIONES GENERALES")
    print("="*60)
    
    # Análisis por estrategia
    strategy_analysis = df.groupby('strategy').agg({
        'total_trades': 'mean',
        'win_rate': 'mean', 
        'total_return': 'mean'
    }).round(2)
    
    print("\nRendimiento promedio por estrategia:")
    for strategy, stats in strategy_analysis.iterrows():
        print(f"{strategy}: {stats['total_trades']} trades, {stats['win_rate']}% WR, {stats['total_return']}% return")
    
    # Problemas más comunes
    print("\n🔧 AJUSTES ESPECÍFICOS REQUERIDOS:")
    
    # ETH - Mean Reversion problems
    eth_data = df[df['symbol'] == 'ETHUSDT']
    if eth_data['total_return'].mean() < 0:
        print("\n1. ETH MEAN REVERSION - Problema: Stops muy ajustados")
        print("   Solución: ATR 3.0x (en lugar de 2.0-2.5x)")
        print("   Solución: RSI más extremo (25/75 en lugar de 30/70)")
        print("   Solución: Confirmación BB más estricta (<0.15 y >0.85)")
    
    # BTC - Lower timeframes
    btc_data = df[df['symbol'] == 'BTCUSDT']
    btc_problems = btc_data[btc_data['total_return'] < 0]
    if len(btc_problems) > 0:
        print("\n2. BTC TREND FOLLOWING 15m/1h - Problema: Demasiado ruido")
        print("   Solución: Filtro MACD más estricto (histogram > 0.1)")
        print("   Solución: Tendencia más fuerte (EMA20-EMA50 > 2%)")
        print("   Solución: Solo operar con volumen excepcional (>1.5x)")
    
    # SOL - No trades in 15m
    sol_data = df[df['symbol'] == 'SOLUSDT']
    sol_no_trades = sol_data[sol_data['total_trades'] == 0]
    if len(sol_no_trades) > 0:
        print("\n3. SOL MOMENTUM 15m - Problema: 0 trades generados")
        print("   Solución: Reducir min_change_pct de 2.5% a 2.0%")
        print("   Solución: RSI menos extremo (35/65 en lugar de 32/68)")
        print("   Solución: Volumen mínimo reducir a 0.9x")
    
    # ADA - Mixed results
    ada_data = df[df['symbol'] == 'ADAUSDT']
    ada_problems = ada_data[ada_data['total_return'] < 0]
    if len(ada_problems) > 0:
        print("\n4. ADA MEAN REVERSION 15m/1h - Problema: Win rate bajo")
        print("   Solución: Similar a ETH, ATR más amplio")
        print("   Solución: Mejor timing de entrada (esperar confirmación)")

if __name__ == "__main__":
    analyze_problems()