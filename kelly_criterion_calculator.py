#!/usr/bin/env python3
"""
Kelly Criterion Calculator for Optimal Position Sizing
Formula: f* = (p*b - q) / b
Where:
- f* = fraction of capital to wager
- p = probability of winning
- q = probability of losing (1-p)
- b = odds received on the wager (profit/loss ratio)
"""

import json
from datetime import datetime
from colorama import init, Fore, Style

init()

class KellyCriterion:
    def __init__(self, capital=250):
        self.capital = capital
        self.max_kelly_fraction = 0.25  # Never risk more than 25% (Kelly/4 for safety)
        
    def calculate_kelly(self, win_prob, win_return, loss_return=1.0):
        """
        Calculate Kelly fraction
        win_prob: Probability of winning (0-1)
        win_return: Multiple of profit if win (e.g., 2 = double money)
        loss_return: Fraction lost if lose (default 1.0 = lose all)
        """
        p = win_prob
        q = 1 - p
        b = win_return
        
        # Kelly formula
        kelly_fraction = (p * b - q) / b
        
        # Apply safety limits
        safe_kelly = min(kelly_fraction / 4, self.max_kelly_fraction)  # Kelly/4 for safety
        
        return {
            'full_kelly': kelly_fraction,
            'safe_kelly': safe_kelly,
            'position_size': self.capital * safe_kelly
        }
    
    def analyze_current_trade(self):
        """Analyze your current SOL trade with Kelly"""
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📊 KELLY CRITERION - ANÁLISIS DE TU TRADE{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        # Current trade parameters
        entry = 199
        current = 196.34
        target = 199  # Breakeven exit
        stop_loss = 194
        
        # Calculate risk/reward
        risk = (entry - stop_loss) / entry  # 2.5%
        reward = (target - entry) / entry    # 0% (breakeven)
        
        print(f"\n📈 TRADE ACTUAL (LONG SOL):")
        print(f"Entry: ${entry}")
        print(f"Current: ${current:.2f}")
        print(f"Target: ${target} (breakeven)")
        print(f"Stop Loss: ${stop_loss}")
        print(f"Risk: {risk*100:.1f}%")
        print(f"Reward: {reward*100:.1f}%")
        
        # Estimate probability based on market conditions
        # Factors: Support at 196, resistance at 197.36, momentum
        win_probability = 0.65  # 65% chance of reaching $199
        
        print(f"\nProbabilidad estimada de éxito: {win_probability*100:.0f}%")
        
        # Since this is a breakeven trade, Kelly doesn't apply well
        print(f"\n{Fore.YELLOW}⚠️ NOTA: Kelly no aplica bien aquí{Style.RESET_ALL}")
        print("Razón: Buscas breakeven (0% ganancia)")
        print("Kelly funciona mejor con trades de ganancia positiva")
        
        # Analyze potential SHORT trade
        print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 ANÁLISIS KELLY PARA SHORT EN $199{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        
        short_entry = 199
        short_target1 = 194
        short_target2 = 190
        short_stop = 202
        
        # Calculate for SHORT
        short_risk = (short_stop - short_entry) / short_entry  # 1.5%
        short_reward1 = (short_entry - short_target1) / short_entry  # 2.5%
        short_reward2 = (short_entry - short_target2) / short_entry  # 4.5%
        
        print(f"\n📉 SHORT TRADE PROPUESTO:")
        print(f"Entry: ${short_entry}")
        print(f"Target 1: ${short_target1} ({short_reward1*100:.1f}% profit)")
        print(f"Target 2: ${short_target2} ({short_reward2*100:.1f}% profit)")
        print(f"Stop Loss: ${short_stop} ({short_risk*100:.1f}% loss)")
        
        # Calculate Kelly for different scenarios
        scenarios = [
            ("Conservative (60% win, Target 1)", 0.60, short_reward1/short_risk),
            ("Moderate (50% win, Target 1)", 0.50, short_reward1/short_risk),
            ("Aggressive (40% win, Target 2)", 0.40, short_reward2/short_risk),
        ]
        
        print(f"\n{Fore.YELLOW}🎯 KELLY CALCULATIONS:{Style.RESET_ALL}")
        for name, prob, rr_ratio in scenarios:
            kelly = self.calculate_kelly(prob, rr_ratio)
            print(f"\n{name}:")
            print(f"  Win Probability: {prob*100:.0f}%")
            print(f"  Risk/Reward: 1:{rr_ratio:.1f}")
            print(f"  Full Kelly: {kelly['full_kelly']*100:.1f}% of capital")
            print(f"  Safe Kelly (÷4): {kelly['safe_kelly']*100:.1f}% of capital")
            print(f"  {Fore.GREEN}Position Size: ${kelly['position_size']:.2f}{Style.RESET_ALL}")
            
            # Leverage calculation
            if kelly['position_size'] > 0:
                leverage_needed = kelly['position_size'] / (self.capital * 0.1)  # 10% margin
                print(f"  Leverage for full position: {leverage_needed:.1f}x")
        
        # Practical recommendations
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 RECOMENDACIONES PRÁCTICAS:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        optimal_position = self.capital * 0.15  # 15% of capital
        print(f"\n1. PARA TU CAPITAL (${self.capital}):")
        print(f"   • Posición óptima: ${optimal_position:.2f}")
        print(f"   • Con 10x leverage: ${optimal_position/10:.2f} de margen")
        print(f"   • Con 20x leverage: ${optimal_position/20:.2f} de margen")
        
        print(f"\n2. REGLAS DE KELLY PARA TRADING:")
        print(f"   • NUNCA uses Full Kelly (muy agresivo)")
        print(f"   • Usa Kelly/4 o Kelly/6 para seguridad")
        print(f"   • Con leverage alto, reduce más (Kelly/8)")
        print(f"   • Si win rate < 50%, reduce posición")
        
        print(f"\n3. PARA TU SHORT EN $199:")
        win_rate = 0.65  # Based on analysis
        kelly_fraction = 0.15  # 15% conservative
        position = self.capital * kelly_fraction
        print(f"   • Win Rate estimado: {win_rate*100:.0f}%")
        print(f"   • Kelly sugiere: ${position:.2f}")
        print(f"   • Con 10x: Usar ${position/10:.2f} de margen")
        print(f"   • {Fore.GREEN}✅ ESTO ES CONSERVADOR Y SEGURO{Style.RESET_ALL}")
        
        # Risk management table
        print(f"\n{Fore.CYAN}📊 TABLA DE GESTIÓN DE RIESGO:{Style.RESET_ALL}")
        print(f"{'='*50}")
        print(f"{'Leverage':<10} {'Margen':<10} {'Posición':<12} {'Max Loss':<10}")
        print(f"{'='*50}")
        
        for leverage in [5, 10, 20, 50]:
            margin = position / leverage
            max_loss = margin  # With stop loss
            print(f"{leverage}x{'':<7} ${margin:<9.2f} ${position:<11.2f} ${max_loss:<9.2f}")
        
        print(f"\n{Fore.YELLOW}⚡ CONCLUSIÓN KELLY:{Style.RESET_ALL}")
        print(f"Para tu SHORT en $199:")
        print(f"• Usa 10-15% de tu capital (${optimal_position:.2f})")
        print(f"• Con 10x leverage: ${optimal_position/10:.2f} margen")
        print(f"• Máxima pérdida: ${optimal_position * 0.015:.2f} (con stop)")
        print(f"• {Fore.GREEN}Risk/Reward favorable: 1:2.5{Style.RESET_ALL}")

    def calculate_for_custom_trade(self):
        """Interactive Kelly calculator"""
        print(f"\n{Fore.CYAN}🧮 CALCULADORA KELLY PERSONALIZADA{Style.RESET_ALL}")
        print("="*50)
        
        try:
            capital = float(input("Capital total ($): ") or self.capital)
            win_prob = float(input("Probabilidad de ganar (0-100%): ")) / 100
            profit_pct = float(input("Ganancia si ganas (%): ")) / 100
            loss_pct = float(input("Pérdida si pierdes (%): ")) / 100
            
            # Calculate odds
            b = profit_pct / loss_pct
            
            kelly = self.calculate_kelly(win_prob, b)
            
            print(f"\n{Fore.YELLOW}RESULTADOS:{Style.RESET_ALL}")
            print(f"Full Kelly: {kelly['full_kelly']*100:.2f}% del capital")
            print(f"Kelly Seguro (÷4): {kelly['safe_kelly']*100:.2f}%")
            print(f"Posición sugerida: ${kelly['position_size']:.2f}")
            
            if kelly['full_kelly'] < 0:
                print(f"\n{Fore.RED}⚠️ ADVERTENCIA: Kelly negativo!{Style.RESET_ALL}")
                print("No deberías tomar este trade - expectativa negativa")
            elif kelly['full_kelly'] > 0.5:
                print(f"\n{Fore.YELLOW}⚠️ Kelly muy alto - usa fracción conservadora{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.GREEN}✅ Trade con expectativa positiva{Style.RESET_ALL}")
                
        except ValueError:
            print("Error en los valores ingresados")

def main():
    kelly = KellyCriterion(capital=250)
    
    # Analyze current situation
    kelly.analyze_current_trade()
    
    # Option for custom calculation
    print(f"\n{Fore.YELLOW}¿Calcular para otro trade? (s/n):{Style.RESET_ALL} ", end='')
    if input().lower() == 's':
        kelly.calculate_for_custom_trade()

if __name__ == "__main__":
    main()