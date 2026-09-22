# Plan: XGBoost Forecast Staleness Check

## Overview

The pipeline's `find_forecast_json()` function in `daily_pipeline.py` currently reuses
a cached XGBoost forecast JSON indefinitely — it only checks that the file exists and was
produced by XGBoost. There is no age check, so months-old forecasts are silently passed
to MeLLeA as if they were current.

The fix: treat any forecast JSON older than **5 calendar days** (one trading week) as
stale. This means a forecast generated on a Friday remains valid through the weekend and
into the following Monday, but will be regenerated on Tuesday. When stale,
`find_forecast_json()` returns `None`, which already triggers a fresh XGBoost run via
the existing pipeline logic — no other changes are needed.

---

## Sub-Task 1 — Add 5-day staleness check to `find_forecast_json`

**Intent**
Extend `find_forecast_json()` to reject cached forecast files whose filesystem
modification time is more than 5 calendar days in the past, causing the pipeline to
automatically re-run XGBoost for that ticker on the next pipeline run after the
threshold is crossed.

**Expected Outcomes**
- A forecast JSON older than 5 calendar days causes `find_forecast_json()` to return `None`
- The pipeline log emits a clear warning naming the ticker and the actual file age in days
- A forecast JSON within 5 calendar days continues to be reused as before
- A fresh XGBoost run is triggered automatically (existing pipeline behaviour,
  no additional changes required)

**Todo List**
1. In `daily_pipeline.py` line 27, extend the existing `datetime` import to also
   import `timedelta`: `from datetime import datetime, timedelta`
2. Near the other module-level constants, add: `MAX_FORECAST_AGE_DAYS = 5`
3. In `find_forecast_json()`, after the method check passes, compute the file age
   using `path.stat().st_mtime` and compare against `MAX_FORECAST_AGE_DAYS`
4. If the file is older than 5 days, log a warning that names the ticker and the
   actual age in days (rounded to one decimal), then return `None`
5. If within 5 days, return `path` as before

**Relevant Context**
- File: `stock-trading-system/daily_pipeline.py`
- Function to modify: `find_forecast_json()` — lines 212-242
- Only one caller: line 441 in the Stage 2 forecast loop — `None` already triggers a fresh run
- Pattern reference: `find_sentiment_report()` (lines 245-253) uses `path.stat().st_mtime`
  for sorting — same `.stat().st_mtime` approach should be used here
- `timedelta` is not yet imported — must be added to the import on line 27
- No changes needed to the caller or any other file

**Status** — [x] done
