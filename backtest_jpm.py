#!/usr/bin/env python3
"""
JPM Stock Backtesting with Sentiment & Time Series Integration
================================================================
Backtest JPM using the trading system strategy with:
1. Time series forecast signals
2. Sentiment analysis scores
3. ATR trailing stop (replaces fixed 2% stop):
   - Peak advances on daily High
   - Stop fires when daily Low <= Peak - (multiplier x ATR14)
   - High-vol cap: if ATR% > 5%, use 1x ATR; hard cap 8%
4. Time backstop: exit Day-5 close if position < +0.5%
5. Open price used for entry (not prior-day Close)
6. Profit target (3%)
7. Position sizing based on combined signals
"""
import math
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

TICKER = 'JPM'
INITIAL_CAPITAL = 1000
PROFIT_TARGET      = 0.03
POSITION_SIZE_BASE = 1.0

# ATR / time-backstop settings
ATR_PERIOD          = 14
ATR_MULTIPLIER      = 2.0
ATR_HIGHVOL_CAP_PCT = 5.0
ATR_HIGHVOL_MULT    = 1.0
MAX_STOP_PCT        = 0.08
BACKSTOP_DAYS       = 5
BACKSTOP_THRESHOLD  = 0.005

# Sentiment Analysis Results (from JPM_sentiment_report_20260611_092208.json)
SENTIMENT_SCORE = 66.5  # Neutral with positive bias
SENTIMENT_RATING = 'BUY'
SENTIMENT_CONFIDENCE = 0.629
POSITION_MULTIPLIER = 0.8  # From sentiment analysis

# Time Series Forecast Results
FORECAST_MEAN = 308.92
FORECAST_CHANGE_PCT = -0.17  # Slight consolidation expected
CURRENT_PRICE = 309.14
VOLATILITY = 0.0137  # 1.37% daily volatility

# Backtesting Period
BACKTEST_START = '2025-06-11'
BACKTEST_END = '2026-06-10'

# ============================================================================
# DATA LOADING
# ============================================================================

def load_stock_data(ticker, start_date, end_date):
    """Load historical OHLCV data and compute ATR(14)."""
    print(f"\n[STEP 1] Loading historical data for {ticker}...")
    print(f"  Period: {start_date} to {end_date}")

    start_dt = pd.Timestamp(start_date) - timedelta(days=ATR_PERIOD * 3)
    df = yf.Ticker(ticker).history(start=start_dt, end=end_date)
    df.index = pd.to_datetime(df.index).tz_localize(None)

    if df.empty:
        raise ValueError(f"No data retrieved for {ticker}")

    df['prev_close'] = df['Close'].shift(1)
    df['tr'] = df.apply(lambda r: max(
        r['High'] - r['Low'],
        abs(r['High'] - r['prev_close']) if not math.isnan(r['prev_close']) else 0,
        abs(r['Low']  - r['prev_close']) if not math.isnan(r['prev_close']) else 0
    ), axis=1)
    df['atr14'] = df['tr'].rolling(ATR_PERIOD).mean()
    df = df[df.index >= pd.Timestamp(start_date)]

    print(f"  [OK] Loaded {len(df)} trading days")
    print(f"  ATR(14) at start : ${df['atr14'].iloc[0]:.2f}")
    print(f"  ATR(14) latest   : ${df['atr14'].iloc[-1]:.2f}  "
          f"({df['atr14'].iloc[-1]/df['Close'].iloc[-1]*100:.2f}% of price)")
    return df

# ============================================================================
# TRADING STRATEGY
# ============================================================================

def calculate_position_size(sentiment_score, forecast_signal, base_size=1.0):
    """
    Calculate position size based on sentiment and forecast signals.
    
    Sentiment Score Adjustment:
    - 70-100 (Bullish): 1.0x - 1.2x
    - 60-70 (Neutral-Positive): 0.8x - 1.0x
    - 50-60 (Neutral): 0.6x - 0.8x
    - Below 50 (Bearish): 0.0x - 0.6x
    
    Forecast Signal Adjustment:
    - Positive forecast: +0.1x
    - Negative forecast: -0.1x
    """
    # Sentiment-based multiplier
    if sentiment_score >= 70:
        sentiment_mult = 1.0 + (sentiment_score - 70) / 100  # 1.0 to 1.3
    elif sentiment_score >= 60:
        sentiment_mult = 0.8 + (sentiment_score - 60) / 50  # 0.8 to 1.0
    elif sentiment_score >= 50:
        sentiment_mult = 0.6 + (sentiment_score - 50) / 50  # 0.6 to 0.8
    else:
        sentiment_mult = max(0.0, sentiment_score / 100)  # 0.0 to 0.5
    
    # Forecast-based adjustment
    forecast_mult = 1.0
    if forecast_signal > 0:
        forecast_mult = 1.1
    elif forecast_signal < 0:
        forecast_mult = 0.9
    
    # Combined position size
    position_size = base_size * sentiment_mult * forecast_mult
    
    # Cap at reasonable limits
    position_size = min(position_size, 1.2)  # Max 120%
    position_size = max(position_size, 0.0)  # Min 0%
    
    return position_size


def backtest_weekly_strategy(df, initial_capital, sentiment_score, forecast_change):
    """
    Weekly strategy with ATR trailing stop + time backstop.
    Entry at Monday Open. Peak tracked on High. Stop triggered on Low.
    """
    print("\n[STEP 2] Running backtest — ATR trailing stop + time backstop...")

    capital     = initial_capital
    position    = 0
    entry_price = 0
    peak_price  = 0
    stop_floor  = 0
    in_position = False
    days_held   = 0
    mult        = ATR_MULTIPLIER

    trades       = []
    equity_curve = []

    df['Week'] = df.index.to_period('W')
    weeks = df['Week'].unique()

    for week_idx, week in enumerate(weeks):
        week_data = df[df['Week'] == week].copy()
        if len(week_data) == 0:
            continue

        # Enter at Monday Open
        if not in_position:
            entry_price  = float(week_data.iloc[0]['Open'])
            atr_now      = float(week_data.iloc[0]['atr14'])
            atr_pct_now  = atr_now / entry_price
            mult         = ATR_HIGHVOL_MULT if atr_pct_now * 100 >= ATR_HIGHVOL_CAP_PCT else ATR_MULTIPLIER
            stop_distance = min(mult * atr_now, entry_price * MAX_STOP_PCT)
            peak_price   = entry_price
            stop_floor   = peak_price - stop_distance

            position_mult    = calculate_position_size(sentiment_score, forecast_change)
            position_capital = capital * position_mult
            position         = position_capital / entry_price
            in_position      = True
            entry_date       = week_data.index[0]
            days_held        = 0

            print(f"  Week {week_idx+1}: ENTER @ ${entry_price:.2f} (Open)  "
                  f"ATR={atr_pct_now*100:.2f}%  mult={mult}x  "
                  f"floor=${stop_floor:.2f}  shares={position:.2f}")

        exit_triggered  = False
        exit_reason     = None
        exit_price_val  = None
        exit_date       = None

        for date, row in week_data.iterrows():
            days_held += 1

            # Advance peak on High
            if float(row['High']) > peak_price:
                peak_price    = float(row['High'])
                atr_now       = float(row['atr14']) if not math.isnan(row['atr14']) else atr_now
                stop_distance = min(mult * atr_now, entry_price * MAX_STOP_PCT)
                stop_floor    = peak_price - stop_distance

            # ATR stop: Low touches floor
            if float(row['Low']) <= stop_floor:
                exit_price_val = stop_floor
                exit_reason    = 'ATR_STOP'
                exit_date      = date
                exit_triggered = True
                break

            # Profit target: High >= +3%
            if float(row['High']) >= entry_price * (1 + PROFIT_TARGET):
                exit_price_val = entry_price * (1 + PROFIT_TARGET)
                exit_reason    = 'PROFIT_TARGET'
                exit_date      = date
                exit_triggered = True
                break

            # Time backstop: Day 5 close — not up >= +0.5%?
            if days_held == BACKSTOP_DAYS:
                close_now = float(row['Close'])
                if (close_now - entry_price) / entry_price < BACKSTOP_THRESHOLD:
                    exit_price_val = close_now
                    exit_reason    = 'TIME_BACKSTOP'
                    exit_date      = date
                    exit_triggered = True
                    break

        if not exit_triggered:
            exit_price_val = float(week_data.iloc[-1]['Close'])
            exit_reason    = 'WEEK_END'
            exit_date      = week_data.index[-1]

        if in_position:
            pnl     = position * (exit_price_val - entry_price)
            pnl_pct = (exit_price_val - entry_price) / entry_price
            capital += pnl

            trades.append({
                'entry_date'  : entry_date,
                'entry_price' : entry_price,
                'exit_date'   : exit_date,
                'exit_price'  : exit_price_val,
                'exit_reason' : exit_reason,
                'shares'      : position,
                'pnl'         : pnl,
                'pnl_pct'     : pnl_pct * 100,
                'capital'     : capital,
                'peak_reached': peak_price,
                'stop_floor'  : stop_floor,
                'days_held'   : days_held,
            })

            print(f"    EXIT @ ${exit_price_val:.2f} ({exit_reason})  "
                  f"P&L ${pnl:+.2f} ({pnl_pct*100:+.2f}%)  "
                  f"Capital ${capital:.2f}  days={days_held}")

            in_position = False
            position    = 0
            days_held   = 0

        equity_curve.append({'date': exit_date, 'capital': capital})

    print(f"\n  [OK] Backtest complete: {len(trades)} trades executed")
    return trades, equity_curve, capital


# ============================================================================
# PERFORMANCE ANALYSIS
# ============================================================================

def analyze_performance(trades, final_capital, initial_capital):
    """Calculate comprehensive performance metrics."""
    print("\n[STEP 3] Analyzing performance...")
    
    if not trades:
        return None
    
    trades_df = pd.DataFrame(trades)
    
    # Basic metrics
    total_return = (final_capital - initial_capital) / initial_capital * 100
    num_trades = len(trades)
    winning_trades = len(trades_df[trades_df['pnl'] > 0])
    losing_trades = len(trades_df[trades_df['pnl'] < 0])
    win_rate = winning_trades / num_trades * 100 if num_trades > 0 else 0
    
    # P&L metrics
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
    largest_win = trades_df['pnl'].max()
    largest_loss = trades_df['pnl'].min()
    
    # Risk metrics
    returns = trades_df['pnl_pct'].values / 100
    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(52) if returns.std() > 0 else 0  # Annualized
    
    # Drawdown
    equity_values = trades_df['capital'].values
    running_max = np.maximum.accumulate(equity_values)
    drawdown = (equity_values - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Stop loss analysis
    stop_losses = len(trades_df[trades_df['exit_reason'] == 'STOP_LOSS'])
    profit_targets = len(trades_df[trades_df['exit_reason'] == 'PROFIT_TARGET'])
    week_ends = len(trades_df[trades_df['exit_reason'] == 'WEEK_END'])
    
    metrics = {
        'total_return_pct': total_return,
        'final_capital': final_capital,
        'num_trades': num_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate_pct': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown,
        'stop_losses': stop_losses,
        'profit_targets': profit_targets,
        'week_ends': week_ends,
        'avg_return_per_trade_pct': trades_df['pnl_pct'].mean(),
        'median_return_per_trade_pct': trades_df['pnl_pct'].median(),
    }
    
    print("  [OK] Performance analysis complete")
    return metrics


# ============================================================================
# VISUALIZATION
# ============================================================================

def plot_results(trades_df, equity_curve, ticker):
    """Create visualization of backtest results."""
    print("\n[STEP 4] Generating visualizations...")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Equity Curve
    equity_df = pd.DataFrame(equity_curve)
    axes[0, 0].plot(equity_df['date'], equity_df['capital'], linewidth=2, color='blue')
    axes[0, 0].axhline(y=INITIAL_CAPITAL, color='red', linestyle='--', label='Initial Capital')
    axes[0, 0].set_title(f'{ticker} Equity Curve', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Capital ($)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Trade P&L Distribution
    axes[0, 1].hist(trades_df['pnl'], bins=20, alpha=0.7, color='green', edgecolor='black')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=2)
    axes[0, 1].set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('P&L ($)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Cumulative Returns
    trades_df['cumulative_return'] = (1 + trades_df['pnl_pct']/100).cumprod() - 1
    axes[1, 0].plot(range(len(trades_df)), trades_df['cumulative_return'] * 100, 
                    linewidth=2, color='purple', marker='o', markersize=4)
    axes[1, 0].axhline(y=0, color='red', linestyle='--')
    axes[1, 0].set_title('Cumulative Returns', fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Trade Number')
    axes[1, 0].set_ylabel('Cumulative Return (%)')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Exit Reason Breakdown
    exit_reasons = trades_df['exit_reason'].value_counts()
    colors = {'STOP_LOSS': 'red', 'PROFIT_TARGET': 'green', 'WEEK_END': 'orange'}
    exit_colors = [colors.get(reason, 'gray') for reason in exit_reasons.index]
    axes[1, 1].bar(exit_reasons.index, exit_reasons.values, color=exit_colors, alpha=0.7)
    axes[1, 1].set_title('Exit Reason Breakdown', fontsize=14, fontweight='bold')
    axes[1, 1].set_xlabel('Exit Reason')
    axes[1, 1].set_ylabel('Count')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    filename = f'stock-trading-system/{ticker}_backtest_results.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved plot: {filename}")
    
    return fig


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report(ticker, metrics, trades_df, sentiment_score, forecast_change):
    """Generate comprehensive backtest report."""
    
    report = f"""# {ticker} Backtesting Report - Weekly Stop Loss Strategy

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Ticker**: {ticker}  
**Strategy**: Weekly Review with 2% Stop Loss & 3% Profit Target  
**Period**: {BACKTEST_START} to {BACKTEST_END}  
**Initial Capital**: ${INITIAL_CAPITAL:,}

---

## Strategy Parameters

**Position Sizing**:
- Base Position: {POSITION_SIZE_BASE*100:.0f}% of capital
- Sentiment Score: {sentiment_score:.1f}/100 ({SENTIMENT_RATING})
- Sentiment Multiplier: {POSITION_MULTIPLIER:.2f}x
- Forecast Signal: {forecast_change:+.2f}%

**Risk Management**:
- Stop Loss: {STOP_LOSS_PCT*100:.0f}%
- Profit Target: {PROFIT_TARGET*100:.0f}%
- Review Frequency: Weekly

**Signal Integration**:
- Sentiment Analysis: FinBERT model on analyst report
- Time Series Forecast: ARIMA model (36-day outlook)
- Combined Scoring: Sentiment-weighted position sizing

---

## Performance Summary

### Overall Results

| Metric | Value |
|--------|-------|
| **Total Return** | {metrics['total_return_pct']:+.2f}% |
| **Final Capital** | ${metrics['final_capital']:.2f} |
| **Profit/Loss** | ${metrics['final_capital'] - INITIAL_CAPITAL:+.2f} |
| **Number of Trades** | {metrics['num_trades']} |
| **Win Rate** | {metrics['win_rate_pct']:.1f}% |
| **Sharpe Ratio** | {metrics['sharpe_ratio']:.3f} |
| **Max Drawdown** | {metrics['max_drawdown_pct']:.2f}% |

### Trade Statistics

| Metric | Value |
|--------|-------|
| **Winning Trades** | {metrics['winning_trades']} ({metrics['winning_trades']/metrics['num_trades']*100:.1f}%) |
| **Losing Trades** | {metrics['losing_trades']} ({metrics['losing_trades']/metrics['num_trades']*100:.1f}%) |
| **Average Win** | ${metrics['avg_win']:.2f} |
| **Average Loss** | ${metrics['avg_loss']:.2f} |
| **Largest Win** | ${metrics['largest_win']:.2f} |
| **Largest Loss** | ${metrics['largest_loss']:.2f} |
| **Avg Return/Trade** | {metrics['avg_return_per_trade_pct']:.2f}% |
| **Median Return/Trade** | {metrics['median_return_per_trade_pct']:.2f}% |

### Exit Analysis

| Exit Reason | Count | Percentage |
|-------------|-------|------------|
| **Stop Loss Triggered** | {metrics['stop_losses']} | {metrics['stop_losses']/metrics['num_trades']*100:.1f}% |
| **Profit Target Hit** | {metrics['profit_targets']} | {metrics['profit_targets']/metrics['num_trades']*100:.1f}% |
| **Week End Exit** | {metrics['week_ends']} | {metrics['week_ends']/metrics['num_trades']*100:.1f}% |

---

## Trade-by-Trade Results

| # | Entry Date | Entry Price | Exit Date | Exit Price | Exit Reason | P&L | Return % | Capital |
|---|------------|-------------|-----------|------------|-------------|-----|----------|---------|
"""
    
    for idx, trade in trades_df.iterrows():
        report += f"| {idx+1} | {trade['entry_date'].strftime('%Y-%m-%d')} | ${trade['entry_price']:.2f} | {trade['exit_date'].strftime('%Y-%m-%d')} | ${trade['exit_price']:.2f} | {trade['exit_reason']} | ${trade['pnl']:+.2f} | {trade['pnl_pct']:+.2f}% | ${trade['capital']:.2f} |\n"
    
    report += f"""
---

## Analysis & Insights

### Strategy Effectiveness

**Stop Loss Protection**:
- {metrics['stop_losses']} trades ({metrics['stop_losses']/metrics['num_trades']*100:.1f}%) were stopped out at -2%
- This prevented larger losses and preserved capital
- Average loss when stopped: ${metrics['avg_loss']:.2f}

**Profit Taking**:
- {metrics['profit_targets']} trades ({metrics['profit_targets']/metrics['num_trades']*100:.1f}%) hit the 3% profit target
- Systematic profit-taking locked in gains
- Average win when target hit: ${metrics['avg_win']:.2f}

**Weekly Review**:
- {metrics['week_ends']} trades ({metrics['week_ends']/metrics['num_trades']*100:.1f}%) exited at week end
- Allows for regular portfolio rebalancing
- Prevents overexposure to single positions

### Risk-Adjusted Performance

**Sharpe Ratio**: {metrics['sharpe_ratio']:.3f}
- {'Excellent' if metrics['sharpe_ratio'] > 2 else 'Good' if metrics['sharpe_ratio'] > 1 else 'Moderate' if metrics['sharpe_ratio'] > 0.5 else 'Poor'} risk-adjusted returns
- Annualized metric accounting for volatility

**Maximum Drawdown**: {metrics['max_drawdown_pct']:.2f}%
- Largest peak-to-trough decline
- {'Low' if abs(metrics['max_drawdown_pct']) < 5 else 'Moderate' if abs(metrics['max_drawdown_pct']) < 10 else 'High'} drawdown risk

### Sentiment Integration Impact

**Sentiment Score**: {sentiment_score:.1f}/100
- Classification: {'Bullish' if sentiment_score >= 70 else 'Neutral-Positive' if sentiment_score >= 60 else 'Neutral' if sentiment_score >= 50 else 'Bearish'}
- Position Multiplier: {POSITION_MULTIPLIER:.2f}x
- Impact: {'Increased' if POSITION_MULTIPLIER > 1 else 'Reduced'} position sizing based on analyst sentiment

**Time Series Forecast**: {forecast_change:+.2f}%
- Signal: {'Bullish' if forecast_change > 0 else 'Bearish' if forecast_change < 0 else 'Neutral'}
- Impact: {'Slight increase' if forecast_change > 0 else 'Slight decrease' if forecast_change < 0 else 'No adjustment'} in position sizing

---

## Comparison to Buy-and-Hold

**Strategy Performance**: {metrics['total_return_pct']:+.2f}%  
**Buy-and-Hold (1-year)**: +17.53% (from time series analysis)

**Strategy Advantages**:
- Active risk management with stop losses
- Systematic profit-taking at 3% targets
- Weekly rebalancing opportunities
- Downside protection during volatility

**Buy-and-Hold Advantages**:
- Lower transaction costs
- Tax efficiency (long-term capital gains)
- Simpler execution
- Captures full upside in strong trends

---

## Recommendations

### For This Stock ({ticker})

**Overall Assessment**: {'FAVORABLE' if metrics['total_return_pct'] > 5 else 'NEUTRAL' if metrics['total_return_pct'] > 0 else 'UNFAVORABLE'}

**Strengths**:
- Win rate of {metrics['win_rate_pct']:.1f}% {'(above 50%)' if metrics['win_rate_pct'] > 50 else '(below 50%)'}
- {'Positive' if metrics['total_return_pct'] > 0 else 'Negative'} total return
- Stop loss effectively limited losses

**Areas for Improvement**:
- {'Consider tighter stop loss if drawdown is high' if abs(metrics['max_drawdown_pct']) > 10 else 'Stop loss level appears appropriate'}
- {'Consider higher profit target to capture more upside' if metrics['profit_targets'] < metrics['week_ends'] else 'Profit target level appears appropriate'}
- {'Increase position size if sentiment improves' if sentiment_score < 70 else 'Position sizing appears appropriate'}

### Strategy Adjustments

**If Continuing with {ticker}**:
1. {'Maintain' if metrics['win_rate_pct'] > 50 else 'Reduce'} position size
2. {'Keep' if abs(metrics['max_drawdown_pct']) < 5 else 'Tighten'} stop loss at {STOP_LOSS_PCT*100:.0f}%
3. {'Keep' if metrics['profit_targets'] > metrics['week_ends'] else 'Raise'} profit target at {PROFIT_TARGET*100:.0f}%
4. Monitor sentiment score updates from new analyst reports

---

## Disclaimers

⚠️ **Important Notice**:

- Past performance does not guarantee future results
- Backtesting uses historical data and may not reflect actual trading conditions
- Actual results may differ due to slippage, commissions, and market impact
- This analysis is for informational purposes only
- Not financial advice - consult a financial advisor before trading
- The authors assume no liability for trading losses

---

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Script**: backtest_jpm.py  
**Author**: B. I. Parker Data Science and Consulting LLC
"""
    
    return report


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run complete backtesting analysis for JPM."""
    
    print("="*80)
    print(f"JPM BACKTESTING - WEEKLY STOP LOSS STRATEGY")
    print("="*80)
    print(f"\nTicker: {TICKER}")
    print(f"Period: {BACKTEST_START} to {BACKTEST_END}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"Strategy: Weekly review with {STOP_LOSS_PCT*100:.0f}% stop loss, {PROFIT_TARGET*100:.0f}% profit target")
    print(f"\nSentiment Score: {SENTIMENT_SCORE:.1f}/100 ({SENTIMENT_RATING})")
    print(f"Forecast Change: {FORECAST_CHANGE_PCT:+.2f}%")
    print(f"Position Multiplier: {POSITION_MULTIPLIER:.2f}x")
    
    try:
        # Load data
        df = load_stock_data(TICKER, BACKTEST_START, BACKTEST_END)
        
        # Run backtest
        trades, equity_curve, final_capital = backtest_weekly_strategy(
            df, INITIAL_CAPITAL, SENTIMENT_SCORE, FORECAST_CHANGE_PCT
        )
        
        # Analyze performance
        metrics = analyze_performance(trades, final_capital, INITIAL_CAPITAL)
        
        if metrics is None:
            print("\n[ERROR] No trades executed - cannot analyze performance")
            return 1
        
        # Create visualizations
        trades_df = pd.DataFrame(trades)
        plot_results(trades_df, equity_curve, TICKER)
        
        # Generate report
        print("\n[STEP 5] Generating report...")
        report = generate_report(TICKER, metrics, trades_df, SENTIMENT_SCORE, FORECAST_CHANGE_PCT)
        
        # Save report
        report_filename = f'stock-trading-system/{TICKER}_BACKTEST_REPORT.md'
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"  [OK] Saved report: {report_filename}")
        
        # Save results to JSON
        results_data = {
            'ticker': TICKER,
            'backtest_period': {
                'start': BACKTEST_START,
                'end': BACKTEST_END
            },
            'strategy_parameters': {
                'initial_capital': INITIAL_CAPITAL,
                'stop_loss_pct': STOP_LOSS_PCT,
                'profit_target_pct': PROFIT_TARGET,
                'position_multiplier': POSITION_MULTIPLIER,
                'sentiment_score': SENTIMENT_SCORE,
                'forecast_change_pct': FORECAST_CHANGE_PCT
            },
            'performance_metrics': metrics,
            'trades': trades
        }
        
        json_filename = f'stock-trading-system/{TICKER}_backtest_results.json'
        with open(json_filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        print(f"  [OK] Saved results: {json_filename}")
        
        # Print summary
        print("\n" + "="*80)
        print("BACKTEST SUMMARY")
        print("="*80)
        print(f"\nTotal Return: {metrics['total_return_pct']:+.2f}%")
        print(f"Final Capital: ${metrics['final_capital']:.2f}")
        print(f"Number of Trades: {metrics['num_trades']}")
        print(f"Win Rate: {metrics['win_rate_pct']:.1f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
        print(f"\nStop Losses: {metrics['stop_losses']} ({metrics['stop_losses']/metrics['num_trades']*100:.1f}%)")
        print(f"Profit Targets: {metrics['profit_targets']} ({metrics['profit_targets']/metrics['num_trades']*100:.1f}%)")
        print(f"Week End Exits: {metrics['week_ends']} ({metrics['week_ends']/metrics['num_trades']*100:.1f}%)")
        
        print("\n" + "="*80)
        print("Analysis complete! Check the following files:")
        print(f"  - {report_filename} (detailed report)")
        print(f"  - {json_filename} (raw results)")
        print(f"  - stock-trading-system/{TICKER}_backtest_results.png (visualizations)")
        print("="*80)
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Backtesting failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

# Made with Bob