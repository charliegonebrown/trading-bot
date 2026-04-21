import numpy as np
import pandas as pd

def run_monte_carlo(prices: list, tp_pct: float, sl_pct: float, steps: int = 50, sims: int = 1000):
    """
    Returns the probability of hitting Take Profit before Stop Loss.
    """
    df = pd.Series(prices)
    returns = df.pct_change().dropna()
    
    # Calculate drift (average return) and volatility (std dev)
    mu = returns.mean()
    sigma = returns.std()
    current_price = prices[-1]
    
    tp_price = current_price * (1 + (tp_pct / 100))
    sl_price = current_price * (1 - (sl_pct / 100))
    
    success_count = 0

    for _ in range(sims):
        # Generate random noise for the 'steps' into the future
        z = np.random.standard_normal(steps)
        # Calculate path based on GBM formula
        path_returns = np.exp((mu - 0.5 * sigma**2) + sigma * z)
        path = current_price * path_returns.cumprod()
        
        # Check what happens first: TP or SL?
        for price in path:
            if price >= tp_price:
                success_count += 1
                break
            if price <= sl_price:
                break # Hit SL, path failed
                
    return (success_count / sims) * 100 # Returns percentage