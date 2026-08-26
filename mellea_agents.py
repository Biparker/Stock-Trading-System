"""
MeLLeA agent function definitions.

Each function is decorated with @mellea.function, which:
  1. Uses the docstring as the LLM prompt (with {variable} interpolation)
  2. Enforces the output_schema at generation time via Pydantic
  3. Applies IVR rules — if any rule is violated, MeLLeA automatically
     re-prompts the model to repair the output before returning it.

Backend is configured in daily_pipeline.py via mellea.configure().
"""

import mellea

from mellea_schemas import (
    CandidateList,
    ForecastDecision,
    SentimentSignal,
    BacktestSignal,
    DailyAction,
)


# ── Step 1: Candidate Selector ────────────────────────────────────────────────

@mellea.function(
    output_schema=CandidateList,
    rules=[
        "tickers list must contain between 3 and 5 items",
        "all tickers must be from the S&P500 Financial, Technology, or Healthcare sectors",
        "budget_per_position multiplied by the number of tickers must not exceed 2500",
        "sectors_represented must list every sector that appears in the tickers list",
    ]
)
def select_candidates(sector_screen_summary: str, budget: float = 2500.0) -> CandidateList:
    """
    You are a quantitative equity analyst selecting target stocks for a retail
    investor with a total budget of ${budget}.

    The following S&P500 equities have passed an initial stability screen across
    the Financial, Technology, and Healthcare sectors. Each entry shows the
    composite score, P/E ratio, profit margin, and current price:

    {sector_screen_summary}

    Your task:
    1. Select 3-5 equities or ETFs that are most likely to outperform their peers.
       Favour stocks with strong momentum, low debt, and positive profit margins.
    2. Allocate an equal dollar amount per position. The total invested
       (budget_per_position × number_of_tickers) must not exceed ${budget}.
    3. Include at least one stock from each of the Financial, Technology, and
       Healthcare sectors if candidates are available from all three.
    4. Provide a plain-English rationale for your selections.
    """


# ── Step 2: Forecast Interpreter ──────────────────────────────────────────────

@mellea.function(
    output_schema=ForecastDecision,
    rules=[
        "if predicted_return_pct > 5 then forecast_trend must be 'bullish' or 'strongly_bullish'",
        "if predicted_return_pct < -5 then forecast_trend must be 'bearish' or 'strongly_bearish'",
        "model_confidence must be derived from model_metrics: high confidence if mape < 1.0, "
        "medium if mape < 3.0, low otherwise",
        "recommendation must be 'include' if forecast_trend is bullish, strongly_bullish, "
        "or neutral AND model_confidence >= 0.5",
        "recommendation must be 'exclude' if forecast_trend is bearish or strongly_bearish",
    ]
)
def interpret_forecast(ticker: str, forecast_json: str) -> ForecastDecision:
    """
    You are a quantitative analyst interpreting a time-series price forecast
    for the stock {ticker}.

    The complete forecast data (JSON) is:
    {forecast_json}

    The JSON contains:
    - metadata: ticker, company name, forecast period dates
    - current_metrics: current_price, price_change_pct, volatility_pct
    - data_characteristics: trend direction, R-squared, stationarity
    - selected_method: the forecasting model used (xgboost, linear_regression, etc.)
    - forecast_results: list of daily {date, forecast, lower_bound, upper_bound}
    - forecast_summary: mean, min, max, change_pct over the forecast window
    - model_metrics: rmse, mae, mape

    Your task:
    1. Determine the overall forecast trend direction and strength.
    2. Set target_price to the final forecast value in forecast_results.
    3. Compute predicted_return_pct as (target_price - current_price) / current_price * 100.
    4. Assess model confidence from model_metrics.mape:
       - mape < 1.0  → confidence ≥ 0.8
       - mape < 3.0  → confidence ≈ 0.6
       - mape >= 3.0 → confidence ≤ 0.5
    5. Decide whether to include or exclude this stock based on trend and confidence.
    """


# ── Step 3: Sentiment Decision ────────────────────────────────────────────────

@mellea.function(
    output_schema=SentimentSignal,
    rules=[
        "if sentiment_score >= 70 then recommendation must be 'include'",
        "if sentiment_score <= 30 then recommendation must be 'exclude'",
        "if risk_level is 'high' or 'very_high' then position_multiplier must be <= 0.85",
        "key_risks must contain no more than 3 items",
        "analyst_rating must reflect the rating field in extracted_metrics if present",
    ],
    sampling="rejection"   # retry until all IVR rules pass
)
def interpret_sentiment(ticker: str, sentiment_report: str) -> SentimentSignal:
    """
    You are a financial NLP analyst interpreting a FinBERT sentiment analysis
    report for the stock {ticker}.

    The sentiment analysis output is:
    {sentiment_report}

    This data includes:
    - overall_sentiment: sentiment_score (0-100), sentiment_label, confidence, method
    - section_sentiments: per-section scores (executive summary, valuation, risks, etc.)
    - risk_assessment: risk_level (low/medium/high/very_high), risk_mentions, risk_adjustment
    - extracted_metrics: price_target, rating, eps_estimate (when available)

    Your task:
    1. Set sentiment_score and sentiment_label from overall_sentiment.
    2. Determine analyst_rating from extracted_metrics.rating if available, else 'unknown'.
    3. Set risk_level from risk_assessment.risk_level.
    4. Compute position_multiplier:
       - very_bullish: 1.3, bullish: 1.15, neutral: 1.0, bearish: 0.7, very_bearish: 0.5
       - Reduce further if risk_level is high (×0.8) or very_high (×0.6)
       - Clamp result between 0.3 and 1.5
    5. Extract up to 3 concrete risk factors from the report text.
    6. Recommend 'include' if score >= 40, 'exclude' if score < 40.
    """


# ── Step 4: Backtest Decision ──────────────────────────────────────────────────

@mellea.function(
    output_schema=BacktestSignal,
    rules=[
        "stage2_pass must be True only if the best stop level has sharpe > 0.3 "
        "AND p_loss_gt5 < 5.0",
        "portfolio_action must be 'include_with_stop' when stage2_pass is True",
        "portfolio_action must be 'exclude_failed_backtest' when stage2_pass is False",
        "failure_reason must be set when stage2_pass is False",
        "stop_dollar_amount must be computed as (recommended_stop_pct / 100) * current_price "
        "when current_price is present in the data",
        "position_size_advice must reference the $2500 total portfolio budget",
    ]
)
def interpret_backtest(ticker: str, backtest_data: str) -> BacktestSignal:
    """
    You are a quantitative risk analyst reviewing a 3-year Monte Carlo backtest
    for the stock {ticker}.

    The backtest data (JSON) is:
    {backtest_data}

    The JSON contains:
    - stage2_pass: boolean pass/fail
    - recommended_stop: the best stop level label
    - results: dict of stop-level → {sharpe, mean_ret_pct, p_loss_gt5, p_profit, avg_stops_yr}
    - For ATR-based backtests: atr14, atr_pct_of_price, high_vol_stock, current_price
    - Acceptance criteria: Sharpe > 0.3 AND P(Loss > 5%) < 5.0%

    Your task:
    1. Confirm stage2_pass is correctly set per the acceptance criteria.
    2. Set recommended_stop_label and recommended_stop_pct from the recommended_stop field.
    3. Populate sharpe_at_recommended, mean_annual_return_pct, p_loss_gt5_pct,
       and avg_stops_per_year from the corresponding results entry.
    4. Set is_high_volatility from high_vol_stock if present, else False.
    5. Compute stop_dollar_amount = (recommended_stop_pct / 100) × current_price
       if current_price is available in the data.
    6. Write position_size_advice as plain English for a retail investor with $2500 total budget,
       mentioning how much to allocate to this position given its volatility profile.
    """


# ── Step 5: Daily Advisor (IVR + majority voting) ────────────────────────────

@mellea.function(
    output_schema=DailyAction,
    sampling="majority_vote",    # runs 3 samples, picks the most consistent result
    rules=[
        "cash_remaining must be >= 0",
        "total invested (sum of position sizes) plus cash_remaining must not exceed 2500",
        "tickers_to_buy must only contain tickers where both forecast and backtest "
        "recommend 'include'",
        "tickers_to_sell must not overlap with tickers_to_hold",
        "stop_loss_orders must contain an entry for every ticker in tickers_to_hold",
        "user_prompt must be written in plain English for a non-expert retail investor",
        "user_prompt must mention the total number of positions, cash remaining, "
        "and at least one specific action the user should take today",
    ]
)
def daily_advisor(
    portfolio_status: str,
    forecast_decisions: str,
    sentiment_signals: str,
    backtest_signals: str,
    cash_available: float,
    today_date: str,
) -> DailyAction:
    """
    You are a daily trading advisor for a retail investor with a ${cash_available}
    portfolio budget and a Merrill Lynch brokerage account.

    Today's date: {today_date}
    Total available cash: ${cash_available}

    Current portfolio positions:
    {portfolio_status}

    XGBoost price forecast decisions (one per candidate ticker):
    {forecast_decisions}

    Analyst sentiment signals (one per candidate ticker):
    {sentiment_signals}

    3-year backtest signals (one per candidate ticker):
    {backtest_signals}

    Your task — produce today's DailyAction:
    1. tickers_to_buy: new positions to open today. Only include tickers where
       both the forecast AND backtest recommend 'include'. Do not exceed
       cash_available when buying.
    2. tickers_to_sell: positions to close. Include if stop-loss has been hit
       or forecast has turned bearish.
    3. tickers_to_hold: existing positions to maintain. Must have a stop_loss_order entry.
    4. tickers_to_monitor: candidates not yet actioned but worth watching.
    5. stop_loss_orders: for every held position, provide the exact dollar stop price
       taken from the backtest signal's stop_dollar_amount.
    6. cash_remaining: ${cash_available} minus total value of new buy positions.
    7. combined_scores: weighted score per ticker:
       (forecast model_confidence × 60%) + (sentiment_score/100 × 40%) × 100
    8. user_prompt: a plain-English daily briefing (3-5 sentences) telling the user
       exactly what to do today — which stocks to buy or sell, where to set stops,
       and how much cash they have left.
    """

# Made with Bob
