"""Generate text and JSON reports for Time Series B forecasts."""

import json
import os
from datetime import datetime, timedelta
import pandas as pd
from config import OUTPUT_DIR, FORECAST_DAYS, MIN_FORECAST_RETURN

os.makedirs(OUTPUT_DIR, exist_ok=True)


class ReportGeneratorB:

    def __init__(self, ticker: str, company_name: str,
                 featured_df: pd.DataFrame,
                 train_result: dict,
                 prediction: dict,
                 feature_importance: dict):
        self.ticker             = ticker.upper()
        self.company_name       = company_name
        self.df                 = featured_df
        self.train_result       = train_result
        self.prediction         = prediction
        self.feature_importance = feature_importance

    # ── Public ────────────────────────────────────────────────────────────────

    def save_json(self) -> str:
        path = os.path.join(OUTPUT_DIR, f'{self.ticker}_tsB_report.json')
        data = self._build_json()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[OK] JSON report -> {path}")
        return path

    def save_text(self) -> str:
        path = os.path.join(OUTPUT_DIR, f'{self.ticker}_tsB_report.txt')
        text = self._build_text()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[OK] Text report -> {path}")
        return path

    def print_summary(self):
        p   = self.prediction
        tr  = self.train_result
        sep = "=" * 70

        print(f"\n{sep}")
        print(f"TIME SERIES B -- STAGE 1 RESULT: {self.ticker} ({self.company_name})")
        print(sep)
        print(f"  Method            : XGBoost -- 30-day relative return (direct)")
        print(f"  Data              : {FORECAST_DAYS * 12 // 12} yrs total  |  "
              f"Train yr1-2  |  Validate yr3")
        print(f"  Training rows     : {tr['train_rows']}  |  "
              f"Validation rows: {tr['val_rows']}")
        print()
        print(f"  Current Price     : ${p['current_price']:.2f}")
        print(f"  Forecast Return   : {p['forecast_return_pct']:+.2f}%  "
              f"(threshold: +{MIN_FORECAST_RETURN}%)")
        print(f"  Confidence Band   : [{p['lower_bound_return_pct']:+.2f}% , "
              f"{p['upper_bound_return_pct']:+.2f}%]")
        print(f"  Price Estimate    : ${p['forecast_price_mid']:.2f}  "
              f"[${p['forecast_price_low']:.2f} - ${p['forecast_price_high']:.2f}]")
        print()
        print(f"  Val RMSE          : {tr['val_metrics']['rmse']}")
        print(f"  Val Direction Acc : {tr['val_metrics']['direction_accuracy']*100:.1f}%")
        print()
        signal = p['signal']
        icon   = '[PASS]' if signal == 'PASS' else '[FAIL]'
        print(f"  STAGE 1 SIGNAL    : {icon} {signal}")
        print(sep)

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_json(self) -> dict:
        last_date       = pd.to_datetime(self.df['date'].iloc[-1])
        forecast_end    = last_date + timedelta(days=int(FORECAST_DAYS * 1.5))  # approx calendar
        return {
            'metadata': {
                'ticker'          : self.ticker,
                'company_name'    : self.company_name,
                'method'          : 'time_series_B_xgboost_relative_return',
                'generated_at'    : datetime.now().isoformat(),
                'data_start'      : self.df['date'].iloc[0].isoformat(),
                'data_end'        : last_date.isoformat(),
                'train_cutoff'    : self.train_result['cutoff_date'],
                'forecast_horizon_days': FORECAST_DAYS,
            },
            'data_summary': {
                'total_rows'      : len(self.df),
                'train_rows'      : self.train_result['train_rows'],
                'val_rows'        : self.train_result['val_rows'],
                'current_price'   : self.prediction['current_price'],
                'price_1yr_ago'   : round(float(self.df['close'].iloc[-252]) if len(self.df) >= 252 else float(self.df['close'].iloc[0]), 2),
                'volatility_daily_pct': round(float(self.df['close'].pct_change().std() * 100), 4),
            },
            'model_performance': {
                'train_metrics'   : self.train_result['train_metrics'],
                'val_metrics'     : self.train_result['val_metrics'],
                'feature_importance': self.feature_importance,
            },
            'prediction': self.prediction,
        }

    def _build_text(self) -> str:
        p   = self.prediction
        tr  = self.train_result
        fi  = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)
        sep = "=" * 70
        lines = [
            sep,
            "TIME SERIES B -- XGBoost 30-Day Relative Return Forecast",
            sep,
            f"Ticker          : {self.ticker}",
            f"Company         : {self.company_name}",
            f"Generated       : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "[TRAINING SETUP]",
            f"  Total data    : {len(self.df)} trading days (3 years)",
            f"  Train period  : years 1-2  ({tr['train_rows']} rows)",
            f"  Val period    : year 3     ({tr['val_rows']} rows, out-of-sample)",
            f"  Train cutoff  : {tr['cutoff_date']}",
            "",
            "[MODEL PERFORMANCE]",
            f"  Train RMSE    : {tr['train_metrics']['rmse']}",
            f"  Train Dir Acc : {tr['train_metrics']['direction_accuracy']*100:.1f}%",
            f"  Val   RMSE    : {tr['val_metrics']['rmse']}  (out-of-sample)",
            f"  Val   Dir Acc : {tr['val_metrics']['direction_accuracy']*100:.1f}%  (out-of-sample)",
            "",
            "[TOP FEATURES BY IMPORTANCE]",
        ]
        for name, imp in fi[:8]:
            lines.append(f"  {name:<20} {imp*100:.1f}%")

        lines += [
            "",
            "[PREDICTION]",
            f"  Current price          : ${p['current_price']:.2f}",
            f"  30-day forecast return : {p['forecast_return_pct']:+.2f}%",
            f"  Confidence band        : [{p['lower_bound_return_pct']:+.2f}% , {p['upper_bound_return_pct']:+.2f}%]",
            f"  Forecast price (mid)   : ${p['forecast_price_mid']:.2f}",
            f"  Forecast price range   : ${p['forecast_price_low']:.2f} - ${p['forecast_price_high']:.2f}",
            f"  Minimum threshold      : +{MIN_FORECAST_RETURN}%",
            "",
            f"  STAGE 1 SIGNAL : {'[PASS]' if p['signal']=='PASS' else '[FAIL]'} {p['signal']}",
            sep,
        ]
        return "\n".join(lines)
