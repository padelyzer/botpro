#!/usr/bin/env python3
"""Test de los filósofos extendidos"""

import pandas as pd
import numpy as np
import yfinance as yf
from philosophers_extended import *

print('='*60)
print('FILÓSOFOS EXTENDIDOS - TEST RÁPIDO')
print('='*60)

# Obtener datos y normalizar columnas
ticker = yf.Ticker('BTC-USD')
df = ticker.history(period='30d', interval='1h')

# Renombrar columnas a minúsculas
df.columns = [c.lower() for c in df.columns]
df = df[['open', 'high', 'low', 'close', 'volume']]

print(f'\nDatos obtenidos: {len(df)} velas')
print(f'Precio actual BTC: ${df["close"].iloc[-1]:,.2f}')

# Probar cada filósofo
philosophers = [
    ('PLATÓN', Platon()),
    ('KANT', Kant()),
    ('DESCARTES', Descartes()),
    ('SUN TZU', SunTzu()),
    ('MAQUIAVELO', Maquiavelo()),
    ('HERÁCLITO', Heraclito())
]

print('\n📊 SEÑALES GENERADAS:\n')

for name, philosopher in philosophers:
    try:
        signal = philosopher.generate_signal(df, 'BTC-USD')
        if signal:
            print(f'{name}: {signal.action} @ ${signal.entry_price:,.0f} (Confianza: {signal.confidence:.0%})')
            print(f'   Tesis: {signal.thesis[:60]}...')
        else:
            print(f'{name}: Sin señal')
            print(f'   Principio: {philosopher.principles[0]}')
    except Exception as e:
        print(f'{name}: Error - {str(e)[:100]}')

# Debate filosófico
print('\n' + '='*60)
print('DEBATE FILOSÓFICO')
print('='*60)

print('\n🎭 TEMA: "¿El mercado es racional?"\n')

debates = {
    'PLATÓN': 'El mercado real es solo una sombra del mercado ideal perfecto.',
    'KANT': 'Si el mercado fuera racional, seguiría reglas universales siempre.',
    'DESCARTES': 'Dudo de la racionalidad del mercado hasta tener pruebas absolutas.',
    'SUN TZU': 'La irracionalidad del enemigo es nuestra mayor ventaja táctica.',
    'MAQUIAVELO': 'Racional o no, lo único que importa es el profit.',
    'HERÁCLITO': 'El mercado fluye entre racionalidad e irracionalidad constantemente.'
}

for name, opinion in debates.items():
    print(f'{name}: "{opinion}"')

print('\n✅ Test completado')