"""
Plotly chart builders for the Streamlit dashboard.

Each function accepts pre-loaded data dicts and returns a
go.Figure ready for st.plotly_chart(fig, use_container_width=True).
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Colour palette (matches amgn-trading-dashboard.html) ────────────────────
C_BLUE    = "#3b82d4"
C_PURPLE  = "#7c5cd8"
C_GREEN   = "#059669"
C_RED     = "#ef4444"
C_AMBER   = "#f59e0b"
C_GRAY    = "#57606a"
C_BG      = "#f7f8fa"
C_BORDER  = "#e5e7eb"


def forecast_chart(forecast_series: list, ticker: str,
                   stop_price: float | None = None,
                   entry_price: float | None = None,
                   price_history: list | None = None,
                   model_metrics: dict | None = None,
                   forecast_signal: dict | None = None) -> go.Figure:
    """
    Two-panel XGBoost forecast chart matching time_series_B/visualizer.py style.

    Panel 1 (top): Full 1-year price history with train (steelblue) / val
                   (darkorange) split, vertical cutoff line, 30-day forecast
                   with confidence band, current-price annotation box, and
                   optional stop / entry lines.

    Panel 2 (bottom): Validation residual normal distribution with ±1σ fill
                      and direction-accuracy annotation.

    Falls back to a single-panel forecast-only chart when price_history is
    absent (e.g. older cached forecast JSONs that predate this change).

    Args:
        forecast_series:  list of {date, forecast, lower_bound, upper_bound}
        ticker:           stock symbol
        stop_price:       trailing stop $ level (optional red dashed line)
        entry_price:      current/entry price (optional amber line)
        price_history:    list of {date, close, split} from forecast JSON
        model_metrics:    dict with residual_std, direction_accuracy, mape, etc.
        forecast_signal:  MeLLeA ForecastDecision dict for PASS/FAIL signal
    """
    import numpy as np
    from scipy.stats import norm as scipy_norm

    has_history = bool(price_history)

    if not forecast_series and not has_history:
        fig = go.Figure()
        fig.add_annotation(text="No forecast data available",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color=C_GRAY))
        fig.update_layout(height=320, paper_bgcolor=C_BG, plot_bgcolor=C_BG)
        return fig

    # ── Build subplots ────────────────────────────────────────────────────────
    from plotly.subplots import make_subplots as _make_subplots
    fig = _make_subplots(
        rows=2, cols=1,
        row_heights=[0.62, 0.38],
        subplot_titles=("", ""),   # set via annotations below
        vertical_spacing=0.12,
    )

    # ── Panel 1: Price history + forecast ────────────────────────────────────
    if has_history:
        train_dates  = [r["date"] for r in price_history if r.get("split") == "train"]
        train_prices = [r["close"] for r in price_history if r.get("split") == "train"]
        val_dates    = [r["date"] for r in price_history if r.get("split") == "val"]
        val_prices   = [r["close"] for r in price_history if r.get("split") == "val"]

        # Train segment
        fig.add_trace(go.Scatter(
            x=train_dates, y=train_prices,
            mode="lines",
            line=dict(color="steelblue", width=1.4),
            name="Train (80%)",
        ), row=1, col=1)

        # Validation segment
        fig.add_trace(go.Scatter(
            x=val_dates, y=val_prices,
            mode="lines",
            line=dict(color="darkorange", width=1.4),
            name="Validation (20%)",
        ), row=1, col=1)

        # Cutoff vertical line (first val date)
        if val_dates:
            fig.add_vline(x=val_dates[0], line=dict(color=C_GRAY, width=1, dash="dash"),
                          row=1, col=1)

    # Forecast dates / values
    if forecast_series:
        f_dates  = [r["date"][:10] for r in forecast_series]
        f_prices = [r["forecast"]  for r in forecast_series]
        f_lows   = [r["lower_bound"] for r in forecast_series]
        f_highs  = [r["upper_bound"] for r in forecast_series]

        # Confidence band
        fig.add_trace(go.Scatter(
            x=f_dates + f_dates[::-1],
            y=f_highs + f_lows[::-1],
            fill="toself",
            fillcolor="rgba(59,130,212,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="95% CI",
            hoverinfo="skip",
        ), row=1, col=1)

        # Forecast line
        fig.add_trace(go.Scatter(
            x=f_dates, y=f_prices,
            mode="lines+markers",
            line=dict(color=C_BLUE, width=2.0),
            marker=dict(size=3, color=C_BLUE),
            name="Forecast",
        ), row=1, col=1)

        # Current price dot at forecast start
        cur_price = entry_price or (price_history[-1]["close"] if has_history else f_prices[0])
        last_hist_date = (price_history[-1]["date"] if has_history else f_dates[0])
        fig.add_trace(go.Scatter(
            x=[last_hist_date], y=[cur_price],
            mode="markers",
            marker=dict(size=9, color="black", symbol="circle"),
            name="Current price",
            hovertemplate=f"Now ${cur_price:.2f}<extra></extra>",
        ), row=1, col=1)

        # Annotation box: "Now $X → +Y%  $lo–$hi"
        pred_return = forecast_signal.get("predicted_return_pct", 0) if forecast_signal else (
            (f_prices[-1] - cur_price) / cur_price * 100 if cur_price else 0
        )
        pass_fail   = "PASS" if (forecast_signal or {}).get("recommendation") == "include" else "FAIL"
        pf_color    = C_GREEN if pass_fail == "PASS" else C_RED
        lo_p = f_lows[0] if f_lows else cur_price
        hi_p = f_highs[0] if f_highs else cur_price
        annotation_text = (
            f"Now ${cur_price:.0f}<br>"
            f"→ {pred_return:+.1f}%<br>"
            f"${lo_p:.0f} – ${hi_p:.0f}"
        )
        fig.add_annotation(
            x=0.78, y=0.18, xref="paper", yref="paper",
            text=annotation_text,
            showarrow=False,
            font=dict(size=10, color="#1f2328"),
            bgcolor="lightyellow",
            bordercolor=C_GRAY,
            borderwidth=1,
        )

    # Stop-loss line
    if stop_price is not None:
        fig.add_hline(
            y=stop_price,
            line=dict(color=C_RED, width=1.5, dash="dash"),
            annotation_text=f"Stop ${stop_price:.2f}",
            annotation_font_color=C_RED,
            row=1, col=1,
        )

    # Panel 1 title with PASS/FAIL signal
    pass_fail  = "PASS" if (forecast_signal or {}).get("recommendation") == "include" else "FAIL"
    pf_color   = C_GREEN if pass_fail == "PASS" else C_RED
    pred_return = forecast_signal.get("predicted_return_pct", 0) if forecast_signal else 0
    p1_title = (
        f"<b>{ticker} — Price History &amp; 30-Day Forecast</b>  "
        f"<span style='color:{pf_color}'>Signal: {pass_fail} ({pred_return:+.1f}%)</span>"
    )

    # ── Panel 2: Residual distribution ───────────────────────────────────────
    res_std   = (model_metrics or {}).get("residual_std", None)
    dir_acc   = (model_metrics or {}).get("direction_accuracy", None)

    if res_std and res_std > 0:
        x_range = np.linspace(-4 * res_std, 4 * res_std, 300)
        y_norm  = scipy_norm.pdf(x_range, loc=0, scale=res_std)
        sigma_mask = (x_range >= -res_std) & (x_range <= res_std)

        # Full distribution curve
        fig.add_trace(go.Scatter(
            x=x_range.tolist(), y=y_norm.tolist(),
            mode="lines",
            line=dict(color="darkorange", width=2),
            name=f"Residuals (σ={res_std:.2f})",
        ), row=2, col=1)

        # ±1σ fill
        fig.add_trace(go.Scatter(
            x=x_range[sigma_mask].tolist() + x_range[sigma_mask][::-1].tolist(),
            y=y_norm[sigma_mask].tolist() + [0] * sigma_mask.sum(),
            fill="toself",
            fillcolor="rgba(245,158,11,0.20)",
            line=dict(color="rgba(0,0,0,0)"),
            name="±1σ",
            hoverinfo="skip",
        ), row=2, col=1)

        # Zero line
        fig.add_vline(x=0, line=dict(color=C_GRAY, width=1, dash="dash"), row=2, col=1)

        dir_label = f"Direction Accuracy: {dir_acc*100:.1f}%" if dir_acc is not None else ""
        p2_title  = f"Validation Residual Distribution  |  {dir_label}"
    else:
        p2_title = "Residual distribution not available (re-run forecast to generate)"
        fig.add_annotation(
            text="Re-run the pipeline to generate residual data",
            xref="x2", yref="paper", x=0, y=0.18,
            showarrow=False, font=dict(size=11, color=C_GRAY),
        )

    # ── Layout ────────────────────────────────────────────────────────────────
    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
        title=dict(text=p1_title, font=dict(size=14), x=0, xref="paper"),
    )

    # Per-panel axis styling
    fig.update_xaxes(title_text="Date", gridcolor=C_BORDER, row=1, col=1)
    fig.update_yaxes(title_text="Price (USD)", gridcolor=C_BORDER, row=1, col=1)
    fig.update_xaxes(title_text="Residual (actual − predicted)", gridcolor=C_BORDER, row=2, col=1)
    fig.update_yaxes(title_text="Density", gridcolor=C_BORDER, row=2, col=1)

    # Panel 2 subtitle via annotation
    fig.add_annotation(
        text=p2_title, xref="paper", yref="paper",
        x=0.0, y=0.355,
        showarrow=False,
        font=dict(size=11, color="#57606a"),
        xanchor="left",
    )

    return fig


def sharpe_bar_chart(backtest_raw: dict, ticker: str) -> go.Figure:
    """
    Bar chart of Sharpe ratio by stop level, highlighting the recommended stop.
    Mirrors the Sharpe bar SVG in amgn-trading-dashboard.html.
    """
    results = backtest_raw.get("results", {})
    if not results:
        fig = go.Figure()
        fig.add_annotation(text="No backtest data", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=280, paper_bgcolor=C_BG, plot_bgcolor=C_BG)
        return fig

    recommended = backtest_raw.get("recommended_stop", "")
    labels  = list(results.keys())
    sharpes = [results[l]["sharpe"] for l in labels]
    colors  = [C_BLUE if l == recommended else "#93c5fd" for l in labels]

    fig = go.Figure(go.Bar(
        x=labels, y=sharpes,
        marker_color=colors,
        text=[f"{s:.3f}" for s in sharpes],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text=f"{ticker} — Sharpe Ratio by Stop Level",
                   font=dict(size=14)),
        yaxis_title="Sharpe Ratio",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        yaxis=dict(gridcolor=C_BORDER),
        xaxis=dict(tickangle=-20),
        showlegend=False,
    )
    return fig


def mean_return_bar_chart(backtest_raw: dict, ticker: str) -> go.Figure:
    """Bar chart of mean annual return (%) by stop level."""
    results = backtest_raw.get("results", {})
    if not results:
        return go.Figure()

    recommended = backtest_raw.get("recommended_stop", "")
    labels  = list(results.keys())
    returns = [results[l]["mean_ret_pct"] for l in labels]
    colors  = [C_GREEN if l == recommended else "#a7f3d0" for l in labels]

    fig = go.Figure(go.Bar(
        x=labels, y=returns,
        marker_color=colors,
        text=[f"{r:+.2f}%" for r in returns],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text=f"{ticker} — Mean Annual Return by Stop Level",
                   font=dict(size=14)),
        yaxis_title="Mean Return (%)",
        height=280,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        yaxis=dict(gridcolor=C_BORDER),
        xaxis=dict(tickangle=-20),
        showlegend=False,
    )
    return fig


def portfolio_performance_chart(combined_scores: dict) -> go.Figure:
    """
    Horizontal bar chart of combined MeLLeA scores for all tickers.
    Color-codes by score: green ≥ 70, amber 50-70, red < 50.
    """
    if not combined_scores:
        fig = go.Figure()
        fig.add_annotation(text="No score data yet", xref="paper",
                           yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=250, paper_bgcolor="white")
        return fig

    tickers = list(combined_scores.keys())
    scores  = [combined_scores[t] for t in tickers]
    colors  = [
        C_GREEN if s >= 70 else (C_AMBER if s >= 50 else C_RED)
        for s in scores
    ]

    fig = go.Figure(go.Bar(
        x=scores, y=tickers,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="MeLLeA Combined Scores (0–100)", font=dict(size=14)),
        xaxis=dict(range=[0, 105], title="Combined Score"),
        height=max(220, len(tickers) * 42),
        margin=dict(l=10, r=40, t=50, b=10),
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        xaxis_gridcolor=C_BORDER,
        showlegend=False,
    )
    # Add threshold line at 60 (minimum buy score)
    fig.add_vline(x=60, line=dict(color=C_GRAY, width=1, dash="dot"),
                  annotation_text="Buy threshold",
                  annotation_font_color=C_GRAY)
    return fig


def risk_reward_chart(entry: float, stop: float, target: float,
                      ticker: str) -> go.Figure:
    """
    Horizontal risk/reward bar — mirrors the SVG in amgn-trading-dashboard.html.
    """
    fig = go.Figure()

    # Risk zone (stop → entry)
    fig.add_trace(go.Bar(
        x=[entry - stop], base=[stop],
        y=[ticker], orientation="h",
        marker_color="rgba(239,68,68,0.4)",
        name=f"Risk  ${entry - stop:.2f}",
        width=0.4,
    ))
    # Reward zone (entry → target)
    fig.add_trace(go.Bar(
        x=[target - entry], base=[entry],
        y=[ticker], orientation="h",
        marker_color="rgba(5,150,105,0.4)",
        name=f"Reward  ${target - entry:.2f}",
        width=0.4,
    ))

    rr = (target - entry) / (entry - stop) if entry > stop else 0
    fig.update_layout(
        title=dict(text=f"{ticker}  R:R ≈ {rr:.1f}:1  |  "
                        f"Stop ${stop:.2f}  →  Entry ${entry:.2f}  →  Target ${target:.2f}",
                   font=dict(size=13)),
        barmode="overlay",
        height=160,
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        legend=dict(orientation="h", yanchor="bottom", y=1.05),
        xaxis_title="Price (USD)",
        yaxis_visible=False,
    )
    return fig

# Made with Bob
