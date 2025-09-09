#!/usr/bin/env python3
"""
PINESCRIPT GENERATOR - BotphIA
Generador de scripts de Pine Script para visualizar señales en TradingView
"""

from typing import Dict, Optional
from datetime import datetime

class PineScriptGenerator:
    """Generador de scripts de Pine Script para señales de trading"""
    
    def __init__(self):
        self.version = 5  # Pine Script v5
        
    def generate_signal_script(self, signal: Dict) -> str:
        """
        Genera un script completo de Pine Script para visualizar una señal
        
        Args:
            signal: Diccionario con los datos de la señal
            
        Returns:
            String con el código Pine Script completo
        """
        # Extraer datos de la señal
        symbol = signal.get('symbol', 'BTCUSDT')
        action = signal.get('action', 'BUY')
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        confidence = signal.get('confidence', 0)
        philosopher = signal.get('philosopher', 'Unknown')
        timestamp = signal.get('timestamp', datetime.now().isoformat())
        reasoning = signal.get('reasoning', '')
        rsi = signal.get('rsi', 50)
        volume_ratio = signal.get('volume_ratio', 1.0)
        
        # Determinar colores según la acción
        signal_color = 'color.green' if action == 'BUY' else 'color.red'
        bg_color = 'color.new(color.green, 90)' if action == 'BUY' else 'color.new(color.red, 90)'
        
        # Generar el script
        script = f'''// This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0
// © BotphIA Trading System
//@version={self.version}
indicator("BotphIA Signal - {symbol}", overlay=true)

// ========================================
// SIGNAL INFORMATION
// ========================================
// Symbol: {symbol}
// Action: {action}
// Philosopher: {philosopher}
// Confidence: {confidence:.1f}%
// Generated: {timestamp}
// ========================================

// Input parameters
showSignal = input.bool(true, "Show Signal Arrow")
showLevels = input.bool(true, "Show Entry/SL/TP Levels")
showInfo = input.bool(true, "Show Info Box")
showRSI = input.bool(false, "Show RSI Panel")

// Signal levels
entryPrice = {entry_price}
stopLoss = {stop_loss}
takeProfit = {take_profit}

// Calculate risk/reward ratio
riskAmount = math.abs(entryPrice - stopLoss)
rewardAmount = math.abs(takeProfit - entryPrice)
rrRatio = rewardAmount / riskAmount

// ========================================
// SIGNAL VISUALIZATION
// ========================================

// Draw horizontal lines for levels
if showLevels
    // Entry line
    line.new(bar_index[10], entryPrice, bar_index, entryPrice, 
             color={signal_color}, width=2, style=line.style_solid,
             extend=extend.right)
    
    // Stop Loss line
    line.new(bar_index[10], stopLoss, bar_index, stopLoss, 
             color=color.red, width=1, style=line.style_dashed,
             extend=extend.right)
    
    // Take Profit line
    line.new(bar_index[10], takeProfit, bar_index, takeProfit, 
             color=color.green, width=1, style=line.style_dashed,
             extend=extend.right)

// Signal arrow at current price
if showSignal and barstate.islast
    if "{action}" == "BUY"
        label.new(bar_index, low * 0.995, "▲ BUY\\n" + str.tostring(confidence, "#.#") + "%", 
                  color=color.green, textcolor=color.white, 
                  style=label.style_label_up, size=size.normal)
    else
        label.new(bar_index, high * 1.005, "▼ SELL\\n" + str.tostring(confidence, "#.#") + "%", 
                  color=color.red, textcolor=color.white,
                  style=label.style_label_down, size=size.normal)

// ========================================
// INFORMATION BOX
// ========================================

if showInfo and barstate.islast
    // Create info table
    var table infoTable = table.new(position.top_right, 2, 8, 
                                    bgcolor=color.new(color.gray, 90),
                                    border_color=color.gray, border_width=1)
    
    // Header
    table.cell(infoTable, 0, 0, "BotphIA Signal", 
               bgcolor={signal_color}, text_color=color.white, text_size=size.normal)
    table.cell(infoTable, 1, 0, "{action}", 
               bgcolor={signal_color}, text_color=color.white, text_size=size.normal)
    
    // Signal details
    table.cell(infoTable, 0, 1, "Symbol:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 1, "{symbol}", text_color=color.white, text_size=size.small)
    
    table.cell(infoTable, 0, 2, "Entry:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 2, str.tostring(entryPrice, "#.####"), 
               text_color={signal_color}, text_size=size.small)
    
    table.cell(infoTable, 0, 3, "Stop Loss:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 3, str.tostring(stopLoss, "#.####"), 
               text_color=color.red, text_size=size.small)
    
    table.cell(infoTable, 0, 4, "Take Profit:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 4, str.tostring(takeProfit, "#.####"), 
               text_color=color.green, text_size=size.small)
    
    table.cell(infoTable, 0, 5, "R:R Ratio:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 5, str.tostring(rrRatio, "#.##") + ":1", 
               text_color=color.yellow, text_size=size.small)
    
    table.cell(infoTable, 0, 6, "Confidence:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 6, str.tostring(confidence, "#.#") + "%", 
               text_color=confidence > 70 ? color.green : confidence > 50 ? color.yellow : color.orange, 
               text_size=size.small)
    
    table.cell(infoTable, 0, 7, "Philosopher:", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 7, "{philosopher}", text_color=color.aqua, text_size=size.small)

// ========================================
// PRICE ACTION ZONES
// ========================================

// Mark potential support/resistance zones
if showLevels
    // Entry zone
    box.new(bar_index[5], entryPrice * 1.001, bar_index, entryPrice * 0.999,
            bgcolor={bg_color}, border_color={signal_color})

// ========================================
// RSI INDICATOR (Optional)
// ========================================

rsiLength = input.int(14, "RSI Length", minval=1)
rsiSource = input.source(close, "RSI Source")
rsiValue = ta.rsi(rsiSource, rsiLength)

// Plot RSI if enabled
plot(showRSI ? rsiValue : na, "RSI", color=color.purple, linewidth=2)

// RSI levels
hline(showRSI ? 73 : na, "RSI Overbought", color=color.red, linestyle=hline.style_dashed)
hline(showRSI ? 28 : na, "RSI Oversold", color=color.green, linestyle=hline.style_dashed)
hline(showRSI ? 50 : na, "RSI Middle", color=color.gray, linestyle=hline.style_dotted)

// ========================================
// ALERTS
// ========================================

// Alert conditions
buySignal = "{action}" == "BUY" and close <= entryPrice * 1.001
sellSignal = "{action}" == "SELL" and close >= entryPrice * 0.999

// Create alerts
alertcondition(buySignal, title="BotphIA Buy Signal", 
               message="BUY Signal for {symbol} at " + str.tostring(entryPrice))
alertcondition(sellSignal, title="BotphIA Sell Signal", 
               message="SELL Signal for {symbol} at " + str.tostring(entryPrice))

// Stop loss hit
slHit = ("{action}" == "BUY" and close <= stopLoss) or ("{action}" == "SELL" and close >= stopLoss)
alertcondition(slHit, title="Stop Loss Hit", 
               message="Stop Loss hit for {symbol}")

// Take profit hit  
tpHit = ("{action}" == "BUY" and close >= takeProfit) or ("{action}" == "SELL" and close <= takeProfit)
alertcondition(tpHit, title="Take Profit Hit",
               message="Take Profit hit for {symbol}")

// ========================================
// SIGNAL REASONING (as comment)
// ========================================
// {reasoning if reasoning else 'No specific reasoning provided'}
// RSI: {rsi:.1f}
// Volume Ratio: {volume_ratio:.2f}
'''
        
        return script
    
    def generate_multi_signal_script(self, signals: list) -> str:
        """
        Genera un script que muestra múltiples señales en el mismo gráfico
        
        Args:
            signals: Lista de señales
            
        Returns:
            String con el código Pine Script
        """
        if not signals:
            return self.generate_empty_script()
            
        # Usar la primera señal como base
        primary_signal = signals[0]
        symbol = primary_signal.get('symbol', 'BTCUSDT')
        
        script = f'''// This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0
// © BotphIA Trading System - Multi-Signal View
//@version={self.version}
indicator("BotphIA Multi-Signals - {symbol}", overlay=true)

// ========================================
// MULTIPLE SIGNALS VISUALIZATION
// Total Signals: {len(signals)}
// ========================================

// Input parameters
showAllSignals = input.bool(true, "Show All Signals")
showOnlyHighConfidence = input.bool(false, "Only High Confidence (>70%)")
minConfidence = input.float(50, "Minimum Confidence", minval=0, maxval=100)

'''
        
        # Agregar cada señal
        for i, signal in enumerate(signals):
            action = signal.get('action', 'BUY')
            entry = signal.get('entry_price', 0)
            sl = signal.get('stop_loss', 0)
            tp = signal.get('take_profit', 0)
            conf = signal.get('confidence', 0)
            phil = signal.get('philosopher', 'Unknown')
            
            color = 'color.green' if action == 'BUY' else 'color.red'
            
            script += f'''
// Signal {i+1}: {phil} - {action} @ {entry:.4f} (Conf: {conf:.1f}%)
signal{i}_show = showAllSignals and {conf} >= minConfidence
if signal{i}_show and barstate.islast
    line.new(bar_index[10], {entry}, bar_index, {entry}, 
             color={color}, width=1, style=line.style_solid,
             extend=extend.right)
    label.new(bar_index, {entry}, "{phil[:3]}: {action} ({conf:.0f}%)",
              color={color}, textcolor=color.white,
              style=label.style_label_left, size=size.tiny)
'''
        
        script += '''
// ========================================
// SUMMARY TABLE
// ========================================

if barstate.islast
    var table summaryTable = table.new(position.top_right, 5, ''' + str(len(signals) + 1) + ''',
                                       bgcolor=color.new(color.gray, 90),
                                       border_color=color.gray, border_width=1)
    
    // Headers
    table.cell(summaryTable, 0, 0, "Philosopher", bgcolor=color.gray, text_color=color.white)
    table.cell(summaryTable, 1, 0, "Action", bgcolor=color.gray, text_color=color.white)
    table.cell(summaryTable, 2, 0, "Entry", bgcolor=color.gray, text_color=color.white)
    table.cell(summaryTable, 3, 0, "Target", bgcolor=color.gray, text_color=color.white)
    table.cell(summaryTable, 4, 0, "Conf %", bgcolor=color.gray, text_color=color.white)
'''
        
        # Agregar filas de la tabla
        for i, signal in enumerate(signals):
            action = signal.get('action', 'BUY')
            entry = signal.get('entry_price', 0)
            tp = signal.get('take_profit', 0)
            conf = signal.get('confidence', 0)
            phil = signal.get('philosopher', 'Unknown')
            
            color = 'color.green' if action == 'BUY' else 'color.red'
            conf_color = 'color.green' if conf > 70 else 'color.yellow' if conf > 50 else 'color.orange'
            
            script += f'''
    // Signal {i+1}
    table.cell(summaryTable, 0, {i+1}, "{phil[:8]}", text_color=color.white, text_size=size.tiny)
    table.cell(summaryTable, 1, {i+1}, "{action}", bgcolor={color}, text_color=color.white, text_size=size.tiny)
    table.cell(summaryTable, 2, {i+1}, str.tostring({entry}, "#.####"), text_color=color.white, text_size=size.tiny)
    table.cell(summaryTable, 3, {i+1}, str.tostring({tp}, "#.####"), text_color=color.white, text_size=size.tiny)
    table.cell(summaryTable, 4, {i+1}, str.tostring({conf}, "#.#"), bgcolor={conf_color}, text_color=color.white, text_size=size.tiny)
'''
        
        return script
    
    def generate_empty_script(self) -> str:
        """Genera un script vacío cuando no hay señales"""
        return f'''// This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0
// © BotphIA Trading System
//@version={self.version}
indicator("BotphIA - No Active Signals", overlay=true)

// No active signals at this moment
if barstate.islast
    label.new(bar_index, high, "No Active Signals", 
              color=color.gray, textcolor=color.white,
              style=label.style_label_down, size=size.normal)
'''

    def save_to_file(self, script: str, filename: str = None) -> str:
        """
        Guarda el script en un archivo
        
        Args:
            script: Código Pine Script
            filename: Nombre del archivo (opcional)
            
        Returns:
            Path del archivo guardado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pinescript_signal_{timestamp}.pine"
        
        filepath = f"/tmp/{filename}"
        
        with open(filepath, 'w') as f:
            f.write(script)
            
        return filepath