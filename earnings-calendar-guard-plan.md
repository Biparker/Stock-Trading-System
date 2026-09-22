# Earnings & Event Calendar Guard — Implementation Plan

## Top-Level Overview

**Goal**: Implement Feature 1 from ST-suggestions.txt — an Earnings & Event Calendar Guard that flags open and planned positions containing earnings, ex-dividend dates, or major macro events (Fed announcements) falling within a configurable look-ahead window (default: 10 days). Surface alerts in the daily pipeline output JSON, the user prompt, the Streamlit dashboard, and the pipeline log.

**Scope**: This is a post-Stage 5 guard layer added to the existing pipeline. It is deterministic logic — no LLM agent required. All data is fetched via `yfinance`, which is already installed. No new API keys are needed. The look-ahead window is read from the `EVENT_GUARD_WINDOW_DAYS` environment variable (already set in `.env`), defaulting to 10 if absent.

**Approach**: Build a self-contained `earnings_calendar_guard.py` module, extend the Pydantic schema in `mellea_schemas.py`, wire the guard into `daily_pipeline.py` after the `daily_advisor()` call, and surface results in the Streamlit dashboard.

**Non-goals**: FDA decision dates and macro economic calendar (FRED/Fed announcement) scraping are out of scope for this first pass — `yfinance` does not provide them natively, and they require external paid APIs. Earnings and ex-dividend dates are in scope (both available via `yfinance`).

---

## Sub-Tasks

---

### Sub-Task 1 — Add EventAlert Schema to mellea_schemas.py

**Intent**: Define a typed, validated Pydantic model for a single calendar event alert and add an `event_alerts` field to `DailyAction` so the pipeline output schema is complete before any logic is written.

**Expected Outcomes**:
- `EventAlert` Pydantic model exists in `mellea_schemas.py`
- `DailyAction` has an optional `event_alerts: List[EventAlert] = []` field
- All existing pipeline code continues to work (field is optional with default)

**Todo List**:
1. Open `mellea_schemas.py` and locate the `DailyAction` class
2. Define `EventAlert` model with fields:
   - `ticker: str`
   - `event_type: Literal["earnings", "ex_dividend"]`
   - `event_date: str` (ISO YYYY-MM-DD)
   - `days_until_event: int`
   - `position_context: Literal["hold", "buy", "monitor"]`
   - `severity: Literal["info", "warning", "critical"]` (critical = within 3 days, warning = 4–7 days, info = 8–10 days)
   - `recommendation: str` (plain-English one-liner)
3. Add `event_alerts: List[EventAlert] = []` to `DailyAction`

**Relevant Context**:
- `mellea_schemas.py` — all Pydantic models live here
- `DailyAction` is the output type of `daily_advisor()` in `mellea_agents.py`
- Existing fields like `stop_loss_orders: Dict[str, float] = {}` demonstrate the default-value pattern to use

**Status**: [x] done

---

### Sub-Task 2 — Build earnings_calendar_guard.py

**Intent**: Create a standalone module that accepts the `DailyAction` output (buy/hold/monitor ticker lists), fetches upcoming earnings and ex-dividend dates via `yfinance`, and returns a list of `EventAlert` objects for any events falling within the configured window.

**Expected Outcomes**:
- `earnings_calendar_guard.py` exists at the root of `stock-trading-system/`
- `EarningsCalendarGuard` class with `__init__(window_days=10)` and `get_alerts(action: DailyAction) -> List[EventAlert]`
- Earnings dates fetched via `yf.Ticker(ticker).calendar`
- Ex-dividend dates fetched via `yf.Ticker(ticker).info["exDividendDate"]` (Unix timestamp → date)
- Graceful handling when `yfinance` returns no data (log warning, skip ticker)
- A lightweight JSON cache at `data/earnings_cache.json` to avoid redundant API calls within the same run
- Unit-testable: the class does not import or call `daily_pipeline.py`

**Todo List**:
1. Create `earnings_calendar_guard.py`
2. Import: `yfinance`, `datetime`, `json`, `pathlib`, `logging`, `EventAlert` from `mellea_schemas`, `DailyAction` from `mellea_schemas`
3. Implement `EarningsCalendarGuard.__init__()` — reads `window_days` from `os.environ.get("EVENT_GUARD_WINDOW_DAYS", 10)`, defines `CACHE_PATH = Path("data/earnings_cache.json")`
4. Implement `_fetch_events(ticker: str) -> dict` — calls `yf.Ticker(ticker).calendar` and `.info["exDividendDate"]`, returns `{"earnings": date|None, "ex_dividend": date|None}`
5. Implement `_severity(days: int) -> Literal[...]` — returns "critical" if days <= 3, "warning" if 4–7, "info" if 8–10
6. Implement `_recommendation(event_type, days, context) -> str` — returns a plain-English one-liner (e.g., "Consider reducing position before earnings on {date}")
7. Implement `get_alerts(action: DailyAction) -> List[EventAlert]` — iterates over `tickers_to_hold + tickers_to_buy + tickers_to_monitor`, calls `_fetch_events`, filters to events within window, builds and returns `EventAlert` objects sorted by `days_until_event`

**Relevant Context**:
- `yfinance` is listed in `requirements.txt` (version >= 0.2.0)
- `data/positions.json` format: `{"open_positions": {"CVS": {...}}, ...}`
- `generate_candidates.py` demonstrates the `yf.Ticker(ticker)` pattern already in use
- `mellea_schemas.py` `DailyAction` has `tickers_to_buy`, `tickers_to_hold`, `tickers_to_monitor` as `List[str]`

**Status**: [x] done

---

### Sub-Task 3 — Wire the Guard into daily_pipeline.py

**Intent**: Call `EarningsCalendarGuard.get_alerts()` after `daily_advisor()` returns and before `save_positions()`, attach the alert list to the output dict, and append a formatted alert summary to the `user_prompt`.

**Expected Outcomes**:
- Guard runs automatically on every pipeline execution
- `pipeline_output.json` contains an `event_alerts` array
- `user_prompt` is extended with a `⚠️ Event Calendar Alerts:` section when alerts exist
- Any critical or warning severity alerts are logged at `[WARNING]` level to `data/pipeline.log`

**Todo List**:
1. Open `daily_pipeline.py` and locate the section after `daily_advisor()` is called (around the `save_positions()` call)
2. Import `EarningsCalendarGuard` at the top of the file
3. After the advisor call, instantiate `guard = EarningsCalendarGuard()` (reads window from env) and call `event_alerts = guard.get_alerts(action)`
4. Attach alerts to the output dict: `output["event_alerts"] = [a.model_dump() for a in event_alerts]`
5. If any alerts exist, append a formatted block to `action.user_prompt`:
   - Header: `"\n\n⚠️ EVENT CALENDAR ALERTS (next {window_days} days):\n"`
   - One line per alert: `"  • {ticker} [{severity.upper()}]: {event_type} on {event_date} ({days_until_event}d) — {recommendation}"`
6. Log each warning/critical alert: `logger.warning(f"[EventGuard] {ticker}: {event_type} in {days_until_event} days ({severity})")`

**Relevant Context**:
- `daily_pipeline.py` — the `save_positions()` call and `embed_data_in_dashboard()` call are the reference anchor points
- Existing logging pattern: `logger = logging.getLogger("mellea_pipeline")` is already set up
- `output` dict is the dict written to `pipeline_output.json`

**Status**: [x] done

---

### Sub-Task 4 — Surface Alerts in the Streamlit Dashboard

**Intent**: Add an "Event Calendar Alerts" section to the Streamlit dashboard that reads `event_alerts` from `pipeline_output.json` and renders them as colour-coded alert boxes (red = critical, orange = warning, blue = info).

**Expected Outcomes**:
- Dashboard shows a clearly labelled "⚠️ Upcoming Events" section
- Critical alerts render in `st.error()`, warnings in `st.warning()`, info in `st.info()`
- Section is collapsed/empty when no alerts exist (no visual noise on clean days)
- Dashboard continues to load and render normally when `event_alerts` key is absent (backward compatibility)

**Todo List**:
1. Open `dashboard/data_loader.py` and verify `pipeline_output.json` is loaded into a dict; confirm the loader passes the raw dict to the dashboard
2. Open the Streamlit dashboard app file in `dashboard/` and locate the appropriate section to add the new widget (after the main buy/sell/hold action summary)
3. Add a guard: `alerts = data.get("event_alerts", [])`
4. If alerts is non-empty, render `st.subheader("⚠️ Upcoming Events (next 10 days)")`
5. For each alert, render the appropriate Streamlit call based on `severity` field
6. Format each alert display: `"{ticker} — {event_type.replace('_',' ').title()} on {event_date} ({days_until_event} days) — {recommendation}"`

**Relevant Context**:
- `dashboard/data_loader.py` — loads and parses `pipeline_output.json`
- `dashboard/app.py` — the main Streamlit application file
- Existing dashboard uses `st.info()`, `st.warning()` patterns already for other sections

**Status**: [x] done

---

## Implementation Notes

### yfinance Earnings Data Behaviour
`yf.Ticker(ticker).calendar` returns a dict that may include `"Earnings Date"` as a list of timestamps (yfinance >= 0.2.x). The guard must handle:
- `None` return (no earnings data available)
- List with one or two dates (use the earliest future date)
- Dates in the past (skip)

`yf.Ticker(ticker).info["exDividendDate"]` returns a Unix timestamp integer or `None`.

### Cache Strategy
To avoid rate-limiting across multi-ticker runs, cache fetched event dates to `data/earnings_cache.json` keyed by ticker + fetch date (e.g., `"AAPL_2026-09-16"`). Cache expires after 24 hours.

### Existing Files Modified
| File | Change |
|------|--------|
| `mellea_schemas.py` | Add `EventAlert` model + `event_alerts` field to `DailyAction` |
| `daily_pipeline.py` | Import guard, call after `daily_advisor()`, attach to output + prompt |
| `dashboard/data_loader.py` | Verify `event_alerts` passthrough (likely no change needed) |
| `dashboard/<app>.py` | Add new alerts UI section |

### New Files Created
| File | Purpose |
|------|---------|
| `earnings_calendar_guard.py` | Self-contained guard module |
| `data/earnings_cache.json` | Runtime cache (git-ignored) |
