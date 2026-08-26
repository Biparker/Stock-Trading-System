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
                   entry_price: float | None = None) -> go.Figure:
    """
    30-day price forecast line chart with confidence band, stop-loss line,
    and entry price marker.

    Args:
        forecast_series: list of {date, forecast, lower_bound, upper_bound}
        ticker:          stock symbol for title
        stop_price:      trailing stop dollar level (optional red dashed line)
        entry_price:     entry price marker (optional amber line)
    """
    if not forecast_series:
        fig = go.Figure()
        fig.add_annotation(text="No forecast data available",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color=C_GRAY))
        fig.update_layout(height=320, paper_bgcolor=C_BG, plot_bgcolor=C_BG)
        return fig

    dates       = [r["date"][:10] for r in forecast_series]
    forecasts   = [r["forecast"]  for r in forecast_series]
    lowers      = [r["lower_bound"] for r in forecast_series]
    uppers      = [r["upper_bound"] for r in forecast_series]

    fig = go.Figure()

    # Confidence band
    fig.add_trace(go.Scatter(
        x=dates + dates[::-1],
        y=uppers + lowers[::-1],
        fill="toself",
        fillcolor="rgba(59,130,212,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="95% CI",
        hoverinfo="skip",
    ))

    # Forecast line
    fig.add_trace(go.Scatter(
        x=dates, y=forecasts,
        mode="lines+markers",
        line=dict(color=C_BLUE, width=2.5),
        marker=dict(size=4, color=C_BLUE),
        name="Forecast",
    ))

    # Stop-loss floor
    if stop_price is not None:
        fig.add_hline(
            y=stop_price,
            line=dict(color=C_RED, width=1.5, dash="dash"),
            annotation_text=f"Stop ${stop_price:.2f}",
            annotation_font_color=C_RED,
        )

    # Entry price
    if entry_price is not None:
        fig.add_hline(
            y=entry_price,
            line=dict(color=C_AMBER, width=1, dash="dot"),
            annotation_text=f"Entry ${entry_price:.2f}",
            annotation_font_color=C_AMBER,
        )

    fig.update_layout(
        title=dict(text=f"{ticker} — 30-Day Price Forecast",
                   font=dict(size=15)),
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=340,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        hovermode="x unified",
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
