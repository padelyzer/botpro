#!/usr/bin/env python3
"""
Monitor para salir de LONG en $199 y entrar en SHORT
"""

import asyncio
import httpx
from datetime import datetime
import time
from colorama import init, Fore, Style

init()

class SOLExitShortMonitor:
    def __init__(self):
        self.exit_target = 199.0  # Salir del LONG aquí
        self.short_entry_range = (198.5, 200.5)  # Rango para entrar SHORT
        self.api_url = "https://api.binance.com/api/v3/ticker/price"
        self.alert_sent = False
        
    async def get_price(self):
        """Get current SOL price"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.api_url,
                    params={"symbol": "SOLUSDT"}
                )
                if response.status_code == 200:
                    return float(response.json()["price"])
            except:
                pass
        return 0
    
    async def monitor(self):
        """Monitor price for exit and short entry"""
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🎯 SOL EXIT & SHORT ENTRY MONITOR{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"📊 Strategy:")
        print(f"  1. Exit LONG at: ${self.exit_target}")
        print(f"  2. Enter SHORT between: ${self.short_entry_range[0]} - ${self.short_entry_range[1]}")
        print(f"  3. SHORT Target: $190-192")
        print(f"  4. SHORT Stop Loss: $202")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        last_alert_time = 0
        highest_since_start = 0
        lowest_since_start = 999999
        
        while True:
            try:
                current_price = await self.get_price()
                
                if current_price > 0:
                    # Track high/low
                    highest_since_start = max(highest_since_start, current_price)
                    lowest_since_start = min(lowest_since_start, current_price)
                    
                    # Calculate distances
                    distance_to_exit = ((self.exit_target - current_price) / current_price) * 100
                    
                    # Clear previous line and print status
                    print(f"\r{' '*100}", end='')
                    
                    # Color based on price position
                    if current_price >= self.exit_target:
                        price_color = Fore.GREEN
                        status = "🟢 EXIT ZONE REACHED!"
                    elif current_price >= 198:
                        price_color = Fore.YELLOW
                        status = "🟡 APPROACHING EXIT"
                    else:
                        price_color = Fore.RED
                        status = "🔴 WAITING..."
                    
                    print(f"\r{price_color}SOL: ${current_price:.2f}{Style.RESET_ALL} | "
                          f"Distance to $199: {distance_to_exit:+.2f}% | "
                          f"High: ${highest_since_start:.2f} | "
                          f"Status: {status}", end='', flush=True)
                    
                    # Alert conditions
                    current_time = time.time()
                    
                    # Alert when approaching exit (within $1)
                    if 198 <= current_price < 199 and current_time - last_alert_time > 60:
                        print(f"\n{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}⚠️  APPROACHING EXIT ZONE!{Style.RESET_ALL}")
                        print(f"Current: ${current_price:.2f} | Target: ${self.exit_target}")
                        print(f"Prepare to:")
                        print(f"  1. Close LONG position")
                        print(f"  2. Wait for SHORT entry")
                        print(f"{Fore.YELLOW}{'='*60}{Style.RESET_ALL}\n")
                        last_alert_time = current_time
                    
                    # Alert when exit target hit
                    elif current_price >= self.exit_target:
                        print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}🎯 EXIT TARGET REACHED! ${current_price:.2f}{Style.RESET_ALL}")
                        print(f"{Style.BRIGHT}ACTION REQUIRED:{Style.RESET_ALL}")
                        print(f"  1. ✅ CLOSE LONG POSITION NOW")
                        print(f"  2. 📊 Prepare SHORT entry")
                        
                        # Analyze SHORT entry
                        if self.short_entry_range[0] <= current_price <= self.short_entry_range[1]:
                            print(f"\n{Fore.RED}🔴 SHORT ENTRY ZONE ACTIVE!{Style.RESET_ALL}")
                            print(f"  Entry: ${current_price:.2f}")
                            print(f"  Target 1: $192 ({((192-current_price)/current_price)*100:.1f}%)")
                            print(f"  Target 2: $190 ({((190-current_price)/current_price)*100:.1f}%)")
                            print(f"  Stop Loss: $202 ({((202-current_price)/current_price)*100:.1f}%)")
                            print(f"  Risk/Reward: 1:{abs(((190-current_price)/(202-current_price))):.1f}")
                        
                        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
                        
                        # Big alert sound
                        for _ in range(3):
                            print('\a', end='', flush=True)
                            await asyncio.sleep(0.5)
                        
                        last_alert_time = current_time
                    
                    # Alert if price goes above SHORT range (missed opportunity)
                    elif current_price > self.short_entry_range[1] and current_time - last_alert_time > 120:
                        print(f"\n{Fore.MAGENTA}⚠️  Price above SHORT range (${current_price:.2f}){Style.RESET_ALL}")
                        print(f"Consider waiting for pullback to $199-200 range")
                        last_alert_time = current_time
                
                await asyncio.sleep(2)
                
            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}Monitor stopped by user{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
                await asyncio.sleep(5)

async def main():
    monitor = SOLExitShortMonitor()
    await monitor.monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")