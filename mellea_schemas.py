"""
Pydantic output schemas for all MeLLeA LLM function calls.

MeLLeA enforces these schemas at generation time — every decorated
function is guaranteed to return a valid, typed Python object that
matches the schema below, or MeLLeA's IVR repair loop corrects it.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Literal, List, Optional, Dict


class CandidateList(BaseModel):
    """Output schema for equity candidate selection (Step 1)."""

    tickers: List[str] = Field(
        description="3-5 tickers from S&P500 Financial, Tech, or Healthcare sectors"
    )
    rationale: str = Field(
        description="Plain-English explanation of why these tickers were selected"
    )
    budget_per_position: float = Field(
        description="Dollar allocation per position. All positions combined must not exceed $2500.",
        gt=0.0,
        le=2500.0
    )
    sectors_represented: List[str] = Field(
        description="List of sectors covered by the selected tickers"
    )

    @model_validator(mode='after')
    def total_budget_check(self):
        total = self.budget_per_position * len(self.tickers)
        if total > 2500.0:
            raise ValueError(
                f"Total budget ${total:.2f} exceeds $2500 limit. "
                f"Reduce budget_per_position or number of tickers."
            )
        return self


class ForecastDecision(BaseModel):
    """Output schema for XGBoost 30-day forecast interpretation (Step 2)."""

    ticker: str
    forecast_trend: Literal[
        "strongly_bullish", "bullish", "neutral", "bearish", "strongly_bearish"
    ]
    current_price: float
    target_price: float = Field(description="End-of-forecast-period price target")
    predicted_return_pct: float = Field(
        description="Expected percentage return over forecast period"
    )
    model_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Model accuracy confidence based on MAPE and RMSE"
    )
    trend_strength: Literal["strong", "moderate", "weak"]
    recommendation: Literal["include", "exclude"] = Field(
        description="include if forecast is bullish/neutral with confidence >= 0.5"
    )
    reasoning: str = Field(
        description="One-sentence explanation of the forecast decision"
    )


class SentimentSignal(BaseModel):
    """Output schema for analyst report sentiment interpretation (Step 3)."""

    ticker: str
    sentiment_score: float = Field(ge=0.0, le=100.0)
    sentiment_label: Literal[
        "very_bullish", "bullish", "neutral", "bearish", "very_bearish"
    ]
    analyst_rating: Literal[
        "strong_buy", "buy", "hold", "sell", "strong_sell", "unknown"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high", "very_high"]
    position_multiplier: float = Field(
        ge=0.3, le=1.5,
        description="Sizing multiplier applied to base position. 1.0 = full size."
    )
    key_risks: List[str] = Field(
        description="Up to 3 key risk factors identified in the analyst report"
    )
    recommendation: Literal["include", "exclude"] = Field(
        description="include if sentiment_score >= 40, exclude if score < 40"
    )

    @model_validator(mode='after')
    def sentiment_recommendation_consistent(self):
        if self.sentiment_score < 40 and self.recommendation == "include":
            raise ValueError(
                f"sentiment_score={self.sentiment_score:.1f} is below 40 — "
                "recommendation must be 'exclude'"
            )
        return self


class BacktestSignal(BaseModel):
    """Output schema for 3-year ATR backtest interpretation (Step 4)."""

    ticker: str
    stage2_pass: bool
    failure_reason: Optional[str] = Field(
        default=None,
        description="Required when stage2_pass is False — explain which criterion failed"
    )
    recommended_stop_label: str = Field(
        description="Exact key from results dict, e.g. '2.5xATR (7.21%)' or '4.0%'"
    )
    recommended_stop_pct: float = Field(gt=0.0, lt=15.0)
    sharpe_at_recommended: float
    mean_annual_return_pct: float
    p_loss_gt5_pct: float
    avg_stops_per_year: float
    is_high_volatility: bool
    stop_dollar_amount: Optional[float] = Field(
        default=None,
        description="Stop distance in dollars = (stop_pct/100) * current_price"
    )
    portfolio_action: Literal["include_with_stop", "exclude_failed_backtest"]
    position_size_advice: str = Field(
        description="Plain-English sizing advice referencing the $2500 total budget"
    )

    @model_validator(mode='after')
    def action_matches_pass(self):
        if self.stage2_pass and self.portfolio_action != "include_with_stop":
            raise ValueError("stage2_pass=True requires portfolio_action='include_with_stop'")
        if not self.stage2_pass and self.portfolio_action != "exclude_failed_backtest":
            raise ValueError("stage2_pass=False requires portfolio_action='exclude_failed_backtest'")
        if not self.stage2_pass and not self.failure_reason:
            raise ValueError("failure_reason required when stage2_pass=False")
        return self


class DailyAction(BaseModel):
    """Output schema for the MeLLeA daily advisor (Step 5). IVR-enforced."""

    date: str = Field(description="ISO date string for today's briefing")
    tickers_to_buy: List[str]
    tickers_to_sell: List[str]
    tickers_to_hold: List[str]
    tickers_to_monitor: List[str] = Field(
        description="Candidates under watch but not yet actioned"
    )
    stop_loss_orders: Dict[str, float] = Field(
        description="Mapping of ticker -> stop price in dollars for each held position"
    )
    cash_remaining: float = Field(
        ge=0.0,
        description="Uninvested cash. Total of all positions plus cash_remaining must not exceed $2500."
    )
    user_prompt: str = Field(
        description="Plain-English daily briefing written for a retail investor. "
                    "Must mention today's top action, any stop-loss updates, and budget status."
    )
    combined_scores: Dict[str, float] = Field(
        description="Mapping of ticker -> combined score (0-100) used for decisions"
    )

# Made with Bob
