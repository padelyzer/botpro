#!/usr/bin/env python3
"""
UI Web para Sistema de Trading de Futuros
Capital inicial: $220 USD
"""

import streamlit as st
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import numpy as np
from futures_trading_system import FuturesTradingSystem, FuturesPairFinder
import time

# Configuración de página
st.set_page_config(
    page_title="Futures Trading System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estado inicial - CAPITAL $220
if 'capital' not in st.session_state:
    st.session_state.capital = 220.0
if 'system' not in st.session_state:
    st.session_state.system = FuturesTradingSystem(initial_capital=220.0)
if 'positions' not in st.session_state:
    st.session_state.positions = {}
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'pnl_history' not in st.session_state:
    st.session_state.pnl_history = []

# CSS personalizado
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .signal-buy {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
    }
    .signal-sell {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
    }
    .position-card {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🚀 Futures Trading System</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Capital
    st.subheader("💰 Capital")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Inicial", f"${st.session_state.capital:.2f}")
    with col2:
        current_capital = st.session_state.capital + sum(st.session_state.pnl_history)
        st.metric("Actual", f"${current_capital:.2f}", 
                 f"{((current_capital/st.session_state.capital)-1)*100:.1f}%")
    
    st.divider()
    
    # Configuración de Trading
    st.subheader("📊 Parámetros")
    
    max_leverage = st.slider("Max Leverage", 1, 20, 10, 1)
    risk_per_trade = st.slider("Risk por Trade (%)", 1.0, 5.0, 2.0, 0.5)
    max_positions = st.slider("Max Posiciones", 1, 5, 3, 1)
    
    st.session_state.system.futures_config['max_leverage'] = max_leverage
    st.session_state.system.futures_config['risk_per_trade'] = risk_per_trade / 100
    st.session_state.system.futures_config['max_positions'] = max_positions
    
    st.divider()
    
    # Estrategia
    st.subheader("🎯 Estrategia")
    strategy = st.selectbox(
        "Tipo de Búsqueda",
        ["all", "momentum", "reversal", "volatility", "funding", "volume"]
    )
    
    min_confidence = st.slider("Confianza Mínima (%)", 50, 90, 70, 5)
    
    st.divider()
    
    # Acciones
    st.subheader("🎮 Controles")
    if st.button("🔍 Buscar Oportunidades", type="primary", use_container_width=True):
        st.session_state.scan_triggered = True
    
    if st.button("📈 Generar Señales", use_container_width=True):
        st.session_state.signals_triggered = True
    
    if st.button("🔄 Actualizar Posiciones", use_container_width=True):
        st.session_state.update_triggered = True
    
    if st.button("🗑️ Limpiar Todo", use_container_width=True):
        st.session_state.positions = {}
        st.session_state.signals = []
        st.rerun()

# Main content
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🔍 Buscador", "📈 Señales", "💼 Posiciones", "📉 Análisis"])

# Tab 1: Dashboard
with tab1:
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        daily_pnl = sum([p for p in st.session_state.pnl_history[-10:]])
        st.metric("PnL Diario", f"${daily_pnl:.2f}", 
                 f"{(daily_pnl/st.session_state.capital)*100:.1f}%")
    
    with col2:
        active_positions = len(st.session_state.positions)
        st.metric("Posiciones Activas", active_positions, 
                 f"/{st.session_state.system.futures_config['max_positions']}")
    
    with col3:
        if st.session_state.pnl_history:
            win_rate = len([p for p in st.session_state.pnl_history if p > 0]) / len(st.session_state.pnl_history) * 100
        else:
            win_rate = 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col4:
        total_signals = len(st.session_state.signals)
        st.metric("Señales Hoy", total_signals)
    
    st.divider()
    
    # Gráfico de PnL
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 Evolución del Capital")
        if st.session_state.pnl_history:
            capital_history = [st.session_state.capital]
            for pnl in st.session_state.pnl_history:
                capital_history.append(capital_history[-1] + pnl)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=capital_history,
                mode='lines+markers',
                name='Capital',
                line=dict(color='#1f77b4', width=2),
                fill='tozeroy'
            ))
            fig.add_hline(y=st.session_state.capital, line_dash="dash", 
                         line_color="gray", annotation_text="Capital Inicial")
            
            fig.update_layout(
                height=400,
                showlegend=False,
                xaxis_title="Trades",
                yaxis_title="Capital ($)",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay historial de trades aún")
    
    with col2:
        st.subheader("📊 Estadísticas")
        stats_df = pd.DataFrame({
            'Métrica': ['Total Trades', 'Ganadores', 'Perdedores', 'Mayor Ganancia', 'Mayor Pérdida', 'Promedio'],
            'Valor': [
                len(st.session_state.pnl_history),
                len([p for p in st.session_state.pnl_history if p > 0]),
                len([p for p in st.session_state.pnl_history if p < 0]),
                f"${max(st.session_state.pnl_history):.2f}" if st.session_state.pnl_history else "$0",
                f"${min(st.session_state.pnl_history):.2f}" if st.session_state.pnl_history else "$0",
                f"${np.mean(st.session_state.pnl_history):.2f}" if st.session_state.pnl_history else "$0"
            ]
        })
        st.dataframe(stats_df, hide_index=True, use_container_width=True)

# Tab 2: Buscador de Pares
with tab2:
    st.header("🔍 Buscador de Oportunidades")
    
    if 'scan_triggered' in st.session_state and st.session_state.scan_triggered:
        with st.spinner("Escaneando mercado de futuros..."):
            # Ejecutar búsqueda asíncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            finder = FuturesPairFinder()
            best_pairs = loop.run_until_complete(
                finder.find_best_opportunities(strategy=strategy, limit=10)
            )
            
            st.session_state.best_pairs = best_pairs
            st.session_state.scan_triggered = False
    
    if 'best_pairs' in st.session_state and st.session_state.best_pairs:
        st.success(f"✅ {len(st.session_state.best_pairs)} oportunidades encontradas")
        
        # Crear DataFrame
        pairs_data = []
        for pair in st.session_state.best_pairs:
            pairs_data.append({
                'Symbol': pair.symbol,
                'Price': f"${pair.mark_price:.4f}",
                'Change 24h': f"{pair.price_change_24h:.2f}%",
                'Volume': f"${pair.volume_24h_usd/1e6:.1f}M",
                'Volatility': f"{pair.volatility:.2f}%",
                'Funding': f"{pair.funding_rate*100:.3f}%",
                'Long/Short': f"{pair.long_ratio:.0f}/{pair.short_ratio:.0f}",
                'Spread': f"{pair.spread:.3f}%"
            })
        
        df_pairs = pd.DataFrame(pairs_data)
        
        # Mostrar tabla con selección
        selected_pairs = st.multiselect(
            "Selecciona pares para analizar:",
            options=df_pairs['Symbol'].tolist(),
            default=df_pairs['Symbol'].tolist()[:3]
        )
        
        st.dataframe(
            df_pairs,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Change 24h": st.column_config.TextColumn(
                    "24h %",
                    help="Cambio de precio en 24 horas"
                ),
                "Long/Short": st.column_config.TextColumn(
                    "L/S Ratio",
                    help="Ratio Long/Short"
                )
            }
        )
        
        # Gráfico de comparación
        if selected_pairs:
            col1, col2 = st.columns(2)
            
            with col1:
                # Volumen comparison
                fig_vol = px.bar(
                    df_pairs[df_pairs['Symbol'].isin(selected_pairs)],
                    x='Symbol',
                    y=[float(v.replace('$', '').replace('M', '')) for v in df_pairs[df_pairs['Symbol'].isin(selected_pairs)]['Volume']],
                    title="Volumen 24h (Millones USD)"
                )
                st.plotly_chart(fig_vol, use_container_width=True)
            
            with col2:
                # Volatility comparison
                fig_vol = px.bar(
                    df_pairs[df_pairs['Symbol'].isin(selected_pairs)],
                    x='Symbol',
                    y=[float(v.replace('%', '')) for v in df_pairs[df_pairs['Symbol'].isin(selected_pairs)]['Volatility']],
                    title="Volatilidad (%)",
                    color=[float(v.replace('%', '')) for v in df_pairs[df_pairs['Symbol'].isin(selected_pairs)]['Volatility']],
                    color_continuous_scale="RdYlGn_r"
                )
                st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.info("👆 Haz clic en 'Buscar Oportunidades' en la barra lateral")

# Tab 3: Señales
with tab3:
    st.header("📈 Señales de Trading")
    
    if 'signals_triggered' in st.session_state and st.session_state.signals_triggered:
        if 'best_pairs' in st.session_state and st.session_state.best_pairs:
            with st.spinner("Generando señales..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                signals = []
                for pair in st.session_state.best_pairs[:5]:
                    signal = loop.run_until_complete(
                        st.session_state.system.generate_futures_signal(pair)
                    )
                    if signal and signal.confidence >= min_confidence:
                        signals.append(signal)
                
                st.session_state.signals = signals
                st.session_state.signals_triggered = False
        else:
            st.warning("Primero debes buscar oportunidades")
    
    if st.session_state.signals:
        st.success(f"🎯 {len(st.session_state.signals)} señales generadas")
        
        # Mostrar señales
        for signal in st.session_state.signals:
            # Color según dirección
            if signal.direction == "LONG":
                st.markdown('<div class="signal-buy">', unsafe_allow_html=True)
                icon = "🟢"
            else:
                st.markdown('<div class="signal-sell">', unsafe_allow_html=True)
                icon = "🔴"
            
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.markdown(f"### {icon} {signal.pair.symbol}")
                st.markdown(f"**Dirección:** {signal.direction}")
                st.markdown(f"**Tipo:** {signal.signal_type.value}")
            
            with col2:
                st.markdown(f"**Entrada:** ${signal.entry_price:.4f}")
                st.markdown(f"**Stop Loss:** ${signal.stop_loss:.4f}")
                st.markdown(f"**Take Profit:** ${signal.take_profit_2:.4f}")
            
            with col3:
                st.markdown(f"**Leverage:** {signal.recommended_leverage}x")
                st.markdown(f"**R:R Ratio:** {signal.risk_reward_ratio:.2f}")
                st.markdown(f"**Confianza:** {signal.confidence:.0f}%")
            
            with col4:
                # Calcular tamaño de posición con capital de $220
                position_info = st.session_state.system.calculate_position_size(
                    signal, 
                    signal.recommended_leverage
                )
                
                if st.button(f"Ejecutar", key=f"exec_{signal.pair.symbol}"):
                    # Simular entrada
                    st.session_state.positions[signal.pair.symbol] = {
                        'signal': signal,
                        'entry_time': datetime.now(),
                        'quantity': position_info['quantity'],
                        'margin': position_info['margin_required'],
                        'pnl': 0
                    }
                    st.success(f"✅ Posición abierta en {signal.pair.symbol}")
                    st.rerun()
            
            # Razones
            with st.expander("Ver razones"):
                for reason in signal.reasons:
                    st.write(f"• {reason}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
    else:
        st.info("👆 Genera señales después de buscar oportunidades")

# Tab 4: Posiciones
with tab4:
    st.header("💼 Posiciones Activas")
    
    if st.session_state.positions:
        total_margin = 0
        total_pnl = 0
        
        for symbol, position in st.session_state.positions.items():
            st.markdown('<div class="position-card">', unsafe_allow_html=True)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            # Simular precio actual (en producción vendría de API)
            current_price = position['signal'].entry_price * (1 + np.random.uniform(-0.01, 0.01))
            
            # Calcular PnL
            if position['signal'].direction == "LONG":
                pnl = (current_price - position['signal'].entry_price) * position['quantity']
            else:
                pnl = (position['signal'].entry_price - current_price) * position['quantity']
            
            pnl_percent = (pnl / position['margin']) * 100
            
            with col1:
                st.markdown(f"### {symbol}")
                st.markdown(f"{position['signal'].direction} {position['signal'].recommended_leverage}x")
            
            with col2:
                st.metric("Entrada", f"${position['signal'].entry_price:.4f}")
                st.metric("Actual", f"${current_price:.4f}")
            
            with col3:
                st.metric("Cantidad", f"{position['quantity']:.4f}")
                st.metric("Margen", f"${position['margin']:.2f}")
            
            with col4:
                color = "green" if pnl > 0 else "red"
                st.metric("PnL", f"${pnl:.2f}", f"{pnl_percent:.1f}%")
            
            with col5:
                if st.button("Cerrar", key=f"close_{symbol}"):
                    # Guardar PnL
                    st.session_state.pnl_history.append(pnl)
                    del st.session_state.positions[symbol]
                    st.success(f"✅ Posición cerrada. PnL: ${pnl:.2f}")
                    st.rerun()
            
            # Progress bars para SL y TP
            st.markdown("##### Niveles")
            col1, col2 = st.columns(2)
            
            with col1:
                # Distancia a SL
                if position['signal'].direction == "LONG":
                    sl_distance = (current_price - position['signal'].stop_loss) / (position['signal'].entry_price - position['signal'].stop_loss)
                else:
                    sl_distance = (position['signal'].stop_loss - current_price) / (position['signal'].stop_loss - position['signal'].entry_price)
                
                sl_distance = max(0, min(1, sl_distance))
                st.progress(sl_distance, text=f"Distancia a SL: {sl_distance*100:.0f}%")
            
            with col2:
                # Progreso a TP
                if position['signal'].direction == "LONG":
                    tp_progress = (current_price - position['signal'].entry_price) / (position['signal'].take_profit_2 - position['signal'].entry_price)
                else:
                    tp_progress = (position['signal'].entry_price - current_price) / (position['signal'].entry_price - position['signal'].take_profit_2)
                
                tp_progress = max(0, min(1, tp_progress))
                st.progress(tp_progress, text=f"Progreso a TP: {tp_progress*100:.0f}%")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            total_margin += position['margin']
            total_pnl += pnl
        
        # Resumen
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Margen Total Usado", f"${total_margin:.2f}", 
                     f"{(total_margin/current_capital)*100:.1f}% del capital")
        with col2:
            st.metric("PnL Total Abierto", f"${total_pnl:.2f}",
                     f"{(total_pnl/st.session_state.capital)*100:.1f}%")
        with col3:
            free_margin = current_capital - total_margin
            st.metric("Margen Libre", f"${free_margin:.2f}")
    else:
        st.info("No hay posiciones activas")

# Tab 5: Análisis
with tab5:
    st.header("📉 Análisis y Backtesting")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribución de Resultados")
        if st.session_state.pnl_history:
            fig = px.histogram(
                st.session_state.pnl_history,
                nbins=20,
                title="Distribución de PnL",
                labels={'value': 'PnL ($)', 'count': 'Frecuencia'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes")
    
    with col2:
        st.subheader("🎯 Análisis de Risk/Reward")
        if st.session_state.signals:
            rr_data = [s.risk_reward_ratio for s in st.session_state.signals]
            fig = px.box(
                rr_data,
                title="Risk/Reward Ratios",
                labels={'value': 'R:R Ratio'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay señales para analizar")
    
    # Simulación de Monte Carlo
    st.divider()
    st.subheader("🎲 Simulación Monte Carlo")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        num_trades = st.number_input("Número de trades", 10, 1000, 100)
    with col2:
        win_rate_sim = st.slider("Win Rate (%)", 30, 70, 45)
    with col3:
        avg_rr = st.number_input("R:R Promedio", 1.0, 3.0, 2.0, 0.1)
    
    if st.button("Ejecutar Simulación"):
        # Simulación
        simulations = []
        for _ in range(100):
            capital = st.session_state.capital
            history = []
            
            for _ in range(num_trades):
                risk = capital * 0.02  # 2% risk
                
                if np.random.random() < win_rate_sim/100:
                    # Win
                    profit = risk * avg_rr
                else:
                    # Loss
                    profit = -risk
                
                capital += profit
                history.append(capital)
            
            simulations.append(history)
        
        # Graficar resultados
        fig = go.Figure()
        
        for sim in simulations:
            fig.add_trace(go.Scatter(
                y=sim,
                mode='lines',
                line=dict(width=0.5),
                opacity=0.1,
                showlegend=False
            ))
        
        # Promedio
        avg_sim = np.mean(simulations, axis=0)
        fig.add_trace(go.Scatter(
            y=avg_sim,
            mode='lines',
            name='Promedio',
            line=dict(color='red', width=2)
        ))
        
        fig.add_hline(y=st.session_state.capital, line_dash="dash", 
                     line_color="gray", annotation_text="Capital Inicial")
        
        fig.update_layout(
            title="Simulación Monte Carlo - 100 escenarios",
            xaxis_title="Trades",
            yaxis_title="Capital ($)",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Estadísticas
        final_capitals = [sim[-1] for sim in simulations]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Capital Final Promedio", f"${np.mean(final_capitals):.2f}")
        with col2:
            st.metric("Mejor Escenario", f"${max(final_capitals):.2f}")
        with col3:
            st.metric("Peor Escenario", f"${min(final_capitals):.2f}")
        with col4:
            profitable = len([c for c in final_capitals if c > st.session_state.capital])
            st.metric("Escenarios Rentables", f"{profitable}%")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray; padding: 1rem;'>
        <p>💼 Capital Inicial: $220 USD | 🚀 Sistema de Futuros v1.0</p>
        <p>⚠️ Opera con responsabilidad. El trading de futuros conlleva alto riesgo.</p>
    </div>
""", unsafe_allow_html=True)

# Auto-refresh
if st.checkbox("Auto-actualizar (cada 30s)", value=False):
    time.sleep(30)
    st.rerun()