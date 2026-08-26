"""
Streamlit dashboard — Stock Trading System (MeLLeA-enhanced)
=============================================================
Run locally:
    cd stock-trading-system
    streamlit run dashboard/app.py

The dashboard reads data/pipeline_output.json written by daily_pipeline.py.
Run the pipeline first:
    python daily_pipeline.py --mock      # instant offline demo data
    python daily_pipeline.py             # full live MeLLeA run (needs API key)
"""

import sys
from pathlib import Path

# Ensure stock-trading-system/ is on the path so data_loader / charts import cleanly
sys.path.insert(0, str(Path(__file__).parent))   # dashboard/
sys.path.insert(0, str(Path(__file__).parent.parent))  # stock-trading-system/

import streamlit as st
import pandas as pd

from data_loader import (
    load_pipeline_output,
    load_forecast_series,
    load_forecast_metadata,
    load_backtest_raw,
    get_action_badge,
)
from charts import (
    forecast_chart,
    sharpe_bar_chart,
    mean_return_bar_chart,
    portfolio_performance_chart,
    risk_reward_chart,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load pipeline data ────────────────────────────────────────────────────────
data = load_pipeline_output()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 Trading Dashboard")
    st.caption("B. I. Parker Data Science")
    st.divider()

    mode_label = {"mock": "🟡 Mock (offline)", "live": "🟢 Live",
                  "no_data": "🔴 No data yet"}.get(data.get("mode", ""), "⚪ Unknown")
    st.metric("Pipeline Mode", mode_label)
    st.metric("Last Run",      data.get("date", "—"))
    st.metric("Budget",        f"${data.get('budget', 2500):.0f}")
    st.metric("Cash Remaining",f"${data.get('cash_remaining', 0):.2f}")
    st.divider()

    all_tickers = data.get("all_tickers", ["AMGN"])
    selected_ticker = st.selectbox("🔍 Ticker Detail View", all_tickers)
    st.divider()

    # Quick actions list
    st.subheader("Today's Actions")
    for t in data.get("tickers_to_buy", []):
        st.success(f"BUY  {t}")
    for t in data.get("tickers_to_sell", []):
        st.error(f"SELL  {t}")
    for t in data.get("tickers_to_hold", []):
        st.warning(f"HOLD  {t}")
    for t in data.get("tickers_to_monitor", []):
        st.info(f"WATCH  {t}")

    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    if data.get("mode") == "no_data":
        st.error(
            "No pipeline data found.\n\n"
            "Run this command in your terminal:\n\n"
            "```\ncd stock-trading-system\n"
            "python daily_pipeline.py --mock\n```"
        )

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Stock Trading System Dashboard")
st.caption(
    f"Daily Briefing — {data.get('date', '—')}  •  "
    f"B. I. Parker Data Science and Consulting LLC  •  "
    f"Pipeline: Stage 1 (Screen) → 2 (Forecast) → 3 (Sentiment) → 4 (Backtest) → 5 (Advise)"
)
st.divider()

# ── Row 1: MeLLeA Daily Advisor Briefing ─────────────────────────────────────
st.subheader("🤖 MeLLeA Daily Advisor")
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Positions to Buy",  len(data.get("tickers_to_buy",  [])))
col_b.metric("Positions Held",    len(data.get("tickers_to_hold", [])))
col_c.metric("Sell Signals",      len(data.get("tickers_to_sell", [])))
col_d.metric("Cash Remaining",    f"${data.get('cash_remaining', 0):.2f}",
             delta=f"of ${data.get('budget', 2500):.0f} budget")

user_prompt = data.get("user_prompt", "")
if user_prompt:
    st.info(f"**Daily Briefing:** {user_prompt}")
st.divider()

# ── Row 2: Portfolio Combined Scores ──────────────────────────────────────────
st.subheader("📊 MeLLeA Combined Scores — All Candidates")
combined_scores = data.get("combined_scores", {})
if combined_scores:
    st.plotly_chart(
        portfolio_performance_chart(combined_scores),
        use_container_width=True
    )

    # Score table
    score_rows = []
    for t, score in combined_scores.items():
        action = data.get("actions_by_ticker", {}).get(t, "monitor")
        label, _ = get_action_badge(action)
        bt = data.get("backtest", {}).get(t, {})
        fc = data.get("forecast", {}).get(t, {})
        se = data.get("sentiment", {}).get(t, {})
        score_rows.append({
            "Ticker":        t,
            "Action":        label,
            "Score":         f"{score:.1f}",
            "Forecast Trend":fc.get("forecast_trend", "—"),
            "Forecast Ret%": f"{fc.get('predicted_return_pct', 0):+.1f}%",
            "Sentiment":     f"{se.get('sentiment_score', 0):.0f}/100",
            "Sharpe":        f"{bt.get('sharpe_at_recommended', 0):.3f}",
            "Stop":          bt.get("recommended_stop_label", "—"),
        })
    st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)
else:
    st.info("Run `python daily_pipeline.py --mock` to generate score data.")

st.divider()

# ── Row 3: Ticker Detail Tabs ─────────────────────────────────────────────────
st.subheader(f"🔬 Detail View — {selected_ticker}")

# Load raw data for selected ticker
forecast_series  = load_forecast_series(selected_ticker)
forecast_meta    = load_forecast_metadata(selected_ticker)
backtest_raw     = load_backtest_raw(selected_ticker)
forecast_signal  = data.get("forecast",  {}).get(selected_ticker, {})
sentiment_signal = data.get("sentiment", {}).get(selected_ticker, {})
backtest_signal  = data.get("backtest",  {}).get(selected_ticker, {})
action_str       = data.get("actions_by_ticker", {}).get(selected_ticker, "monitor")

# KPI strip for selected ticker
k1, k2, k3, k4 = st.columns(4)
current_price = forecast_signal.get("current_price") or \
                forecast_meta.get("current_metrics", {}).get("current_price", 0)
target_price  = forecast_signal.get("target_price", 0)
stop_price    = backtest_signal.get("stop_dollar_amount")
sentiment_sc  = sentiment_signal.get("sentiment_score", 0)

k1.metric("Current Price",   f"${current_price:.2f}")
k2.metric("30-Day Target",   f"${target_price:.2f}",
          delta=f"{forecast_signal.get('predicted_return_pct', 0):+.1f}%")
k3.metric("Trailing Stop",
          f"${stop_price:.2f}" if stop_price else "—",
          delta=f"-{backtest_signal.get('recommended_stop_pct', 0):.2f}%" if stop_price else None,
          delta_color="inverse")
k4.metric("Sentiment Score", f"{sentiment_sc:.1f} / 100")

# Action badge
action_label, action_color = get_action_badge(action_str)
badge_map = {"green": st.success, "red": st.error,
             "orange": st.warning, "blue": st.info}
badge_fn = badge_map.get(action_color, st.info)
badge_fn(f"**{selected_ticker} Recommendation: {action_label}**")

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Forecast", "📉 Backtest", "📰 Sentiment", "🎯 Strategy"
])

# ── Tab 1: Forecast ───────────────────────────────────────────────────────────
with tab1:
    st.markdown("#### XGBoost 30-Day Price Forecast")
    st.plotly_chart(
        forecast_chart(
            forecast_series,
            selected_ticker,
            stop_price=stop_price,
            entry_price=current_price if current_price else None,
        ),
        use_container_width=True,
    )
    if forecast_meta:
        cm = forecast_meta.get("current_metrics", {})
        dc = forecast_meta.get("data_characteristics", {})
        fs = forecast_meta.get("forecast_summary", {})
        mm = forecast_meta.get("model_metrics", {})
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Start Price",   f"${cm.get('current_price', 0):.2f}")
        c2.metric("Mean Forecast", f"${fs.get('mean', 0):.2f}")
        c3.metric("36-Day Target", f"${fs.get('max', 0):.2f}")
        c4.metric("Forecast Δ",    f"{fs.get('change_pct', 0):+.2f}%")
        c5.metric("MAPE",          f"{mm.get('mape', 0):.2f}%")
        trend = dc.get("trend", {})
        st.caption(
            f"**Trend:** {trend.get('direction','—')} "
            f"(R²={trend.get('r_squared',0):.3f})  •  "
            f"**Volatility:** {dc.get('volatility',{}).get('level','—')}  •  "
            f"**Model:** {forecast_meta.get('selected_method','—').upper()}"
        )
    if forecast_signal:
        st.markdown(
            f"**MeLLeA Interpretation:** {forecast_signal.get('reasoning','—')}"
        )

# ── Tab 2: Backtest ───────────────────────────────────────────────────────────
with tab2:
    st.markdown("#### 3-Year ATR Trailing Stop Backtest")

    if backtest_raw:
        # Methodology note
        st.caption(backtest_raw.get("methodology", ""))

        # Stats strip
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("ATR(14)",       f"${backtest_raw.get('atr14', 0):.2f}"
                                    if "atr14" in backtest_raw else "—")
        b2.metric("ATR % Price",   f"{backtest_raw.get('atr_pct_of_price', 0):.2f}%"
                                    if "atr_pct_of_price" in backtest_raw else "—")
        b3.metric("Parkinson Vol", f"{backtest_raw.get('parkinson_sigma_pct', 0):.3f}%"
                                    if "parkinson_sigma_pct" in backtest_raw else "—")
        b4.metric("Stage 2",       "✅ PASS" if backtest_raw.get("stage2_pass") else "❌ FAIL")

        # Results table
        results = backtest_raw.get("results", {})
        recommended = backtest_raw.get("recommended_stop", "")
        if results:
            rows = []
            for label, m in results.items():
                rows.append({
                    "Stop Level":   label + (" ★" if label == recommended else ""),
                    "Sharpe":       f"{m['sharpe']:.3f}",
                    "Mean Ret%":    f"{m['mean_ret_pct']:+.2f}%",
                    "Median Ret%":  f"{m['median_ret_pct']:+.2f}%",
                    "P(Loss>5%)":   f"{m['p_loss_gt5']:.2f}%",
                    "P(Profit)":    f"{m['p_profit']:.1f}%",
                    "Stops/Yr":     m['avg_stops_yr'],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(
                sharpe_bar_chart(backtest_raw, selected_ticker),
                use_container_width=True,
            )
        with col_r:
            st.plotly_chart(
                mean_return_bar_chart(backtest_raw, selected_ticker),
                use_container_width=True,
            )
    else:
        st.info(f"No backtest data found for {selected_ticker}. "
                f"Run: `python stage2_backtest.py --ticker {selected_ticker}`")

    if backtest_signal:
        st.markdown(
            f"**MeLLeA Advice:** {backtest_signal.get('position_size_advice','—')}"
        )

# ── Tab 3: Sentiment ──────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Analyst Sentiment — FinBERT NLP")
    if sentiment_signal:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Sentiment Score",    f"{sentiment_signal.get('sentiment_score',0):.1f}/100")
        s2.metric("Analyst Rating",     sentiment_signal.get("analyst_rating","—").upper())
        s3.metric("Risk Level",         sentiment_signal.get("risk_level","—").upper())
        s4.metric("Position Multiplier",f"{sentiment_signal.get('position_multiplier',1.0):.2f}×")

        score = sentiment_signal.get("sentiment_score", 50)
        label = sentiment_signal.get("sentiment_label", "neutral")
        st.progress(
            min(int(score), 100),
            text=f"FinBERT Sentiment: {score:.1f}/100 — {label.upper().replace('_',' ')}"
        )

        key_risks = sentiment_signal.get("key_risks", [])
        if key_risks:
            st.markdown("**Key Risks Identified:**")
            for risk in key_risks:
                st.markdown(f"- {risk}")

        confidence = sentiment_signal.get("confidence", 0)
        st.caption(f"Model confidence: {confidence:.1%}  •  "
                   f"Method: FinBERT  •  "
                   f"Recommendation: {sentiment_signal.get('recommendation','—').upper()}")
    else:
        st.info(f"No sentiment data for {selected_ticker}. "
                f"Add analyst PDF to `sentiment_analyzer/Analyst_reports/` and re-run pipeline.")

# ── Tab 4: Strategy ───────────────────────────────────────────────────────────
with tab4:
    st.markdown("#### Trading Strategy Advice")

    # Combined score
    cs = data.get("combined_scores", {}).get(selected_ticker)
    if cs:
        if cs >= 70:
            st.success(f"Combined MeLLeA Score: **{cs:.1f} / 100** — STRONG BUY signal")
        elif cs >= 60:
            st.success(f"Combined MeLLeA Score: **{cs:.1f} / 100** — BUY signal")
        elif cs >= 50:
            st.warning(f"Combined MeLLeA Score: **{cs:.1f} / 100** — HOLD / WATCH")
        else:
            st.error(f"Combined MeLLeA Score: **{cs:.1f} / 100** — DO NOT BUY")

    # Strategy grid
    sg1, sg2, sg3, sg4 = st.columns(4)
    sg1.metric("Action",        action_label)
    sg2.metric("Entry Price",   f"${current_price:.2f}" if current_price else "—")
    sg3.metric("Price Target",  f"${target_price:.2f}"  if target_price  else "—")
    sg4.metric("Stop Loss",     f"${stop_price:.2f}"    if stop_price    else "—")

    sg5, sg6, sg7, sg8 = st.columns(4)
    sg5.metric("Stop %",
               f"{backtest_signal.get('recommended_stop_pct',0):.2f}%"
               if backtest_signal else "—")
    sg6.metric("Sharpe Ratio",
               f"{backtest_signal.get('sharpe_at_recommended',0):.3f}"
               if backtest_signal else "—")
    sg7.metric("P(Profit)",
               f"{backtest_signal.get('mean_annual_return_pct',0):+.2f}%"
               if backtest_signal else "—")
    sg8.metric("Sentiment Mult",
               f"{sentiment_signal.get('position_multiplier',1.0):.2f}×"
               if sentiment_signal else "—")

    # Risk/reward chart
    if current_price and stop_price and target_price:
        st.plotly_chart(
            risk_reward_chart(current_price, stop_price, target_price,
                              selected_ticker),
            use_container_width=True,
        )

    # Merrill caution note
    st.warning(
        "⚠️ **Merrill Lynch Order Reminder:** After purchasing, wait at least one "
        "full trading day (next business day) before placing the trailing stop "
        "sell order. Same-day stop orders risk a Free Ride Violation."
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**Disclaimer:** This dashboard is for informational purposes only and does not "
    "constitute financial advice. All analysis is based on historical data and "
    "quantitative models. Past performance does not guarantee future results. "
    "Always conduct your own due diligence.  |  B. I. Parker Data Science and Consulting LLC  "
    "|  Made with IBM Bob"
)

# Made with Bob
