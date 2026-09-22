"""XGBoost model for 30-day relative return prediction (Time Series B).

Train / Validation split
─────────────────────────
  Training   : first TRAIN_YEARS of data  (rows where date < cutoff)
  Validation : remaining year             (rows where date >= cutoff)

This is a DIRECT forecast -- the model predicts the 30-day forward return
in a single shot, avoiding the iterative error-compounding of Method A.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error
from datetime import timedelta
from config import (TRAIN_YEARS, LOOKBACK_YEARS,
                    XGB_N_ESTIMATORS, XGB_LEARNING_RATE, XGB_MAX_DEPTH,
                    XGB_SUBSAMPLE, XGB_COLSAMPLE, XGB_MIN_CHILD_WEIGHT,
                    XGB_RANDOM_STATE)
from feature_engineer import FEATURE_COLS, TARGET_COL


class ReturnForecaster:
    """Predicts 30-day forward log return using XGBoost."""

    def __init__(self):
        self.model      = None
        self.train_metrics = {}
        self.val_metrics   = {}
        self.feature_importance = None
        self._cutoff    = None

    # ── Public API ────────────────────────────────────────────────────────────

    def train(self, featured_df: pd.DataFrame) -> dict:
        """
        Split data, train on years 1-2, validate on year 3.

        Args:
            featured_df: output of feature_engineer.build_features()

        Returns:
            dict with train/val metrics and split info
        """
        df = featured_df.copy()

        # Compute train/val cutoff date
        first_date  = df['date'].iloc[0]
        self._cutoff = first_date + timedelta(days=int(TRAIN_YEARS * 365.25))

        train = df[df['date'] <  self._cutoff].copy()
        val   = df[df['date'] >= self._cutoff].copy()

        print(f"\n  Training split  : {train['date'].iloc[0].date()} -> "
              f"{train['date'].iloc[-1].date()} ({len(train)} rows)")
        print(f"  Validation split: {val['date'].iloc[0].date()} -> "
              f"{val['date'].iloc[-1].date()} ({len(val)} rows)")

        if len(train) < 50:
            raise ValueError("Insufficient training data -- need at least 50 rows.")
        if len(val) < 10:
            raise ValueError("Insufficient validation data -- need at least 10 rows.")

        X_train = train[FEATURE_COLS].values
        y_train = train[TARGET_COL].values
        X_val   = val[FEATURE_COLS].values
        y_val   = val[TARGET_COL].values

        # Train with val-set monitoring -- stop when val MAE stops improving
        self.model = xgb.XGBRegressor(
            n_estimators      = XGB_N_ESTIMATORS,
            learning_rate     = XGB_LEARNING_RATE,
            max_depth         = XGB_MAX_DEPTH,
            subsample         = XGB_SUBSAMPLE,
            colsample_bytree  = XGB_COLSAMPLE,
            min_child_weight  = XGB_MIN_CHILD_WEIGHT,
            random_state      = XGB_RANDOM_STATE,
            verbosity         = 0,
        )
        # Fit without early stopping -- use fixed n_estimators with regularisation
        # Early stopping on raw return MAE fires too early (target variance ~36%)
        self.model.fit(X_train, y_train, verbose=False)

        # Report val MAE manually for transparency
        y_val_check = self.model.predict(X_val)
        val_mae_check = float(np.mean(np.abs(y_val - y_val_check)))
        print(f"  Trees built     : {XGB_N_ESTIMATORS}  |  Val MAE: {val_mae_check:.2f}%")

        # Metrics on training set
        y_train_pred = self.model.predict(X_train)
        self.train_metrics = _metrics(y_train, y_train_pred, label='train')

        # Metrics on validation set (out-of-sample -- year 3)
        y_val_pred = self.model.predict(X_val)
        self.val_metrics = _metrics(y_val, y_val_pred, label='val')

        # Feature importance
        self.feature_importance = dict(zip(
            FEATURE_COLS,
            self.model.feature_importances_.tolist()
        ))

        return {
            'train_rows'    : len(train),
            'val_rows'      : len(val),
            'cutoff_date'   : self._cutoff.date().isoformat(),
            'train_metrics' : self.train_metrics,
            'val_metrics'   : self.val_metrics,
        }

    def predict_latest(self, featured_df: pd.DataFrame) -> dict:
        """
        Predict the 30-day forward return from the MOST RECENT row.

        The most recent row contains today's technical snapshot -- the model
        produces a single point estimate plus a confidence band derived from
        the validation-set residual distribution.

        Returns:
            dict: forecast_return_pct, lower_bound, upper_bound,
                  current_price, forecast_price_estimate,
                  signal (PASS/FAIL), feature_snapshot
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        latest = featured_df.iloc[-1]
        X      = latest[FEATURE_COLS].values.reshape(1, -1)
        pred   = float(self.model.predict(X)[0])

        # Confidence band: +/-1.96 x std of val residuals
        conf   = 1.96 * self.val_metrics.get('residual_std', abs(pred) * 0.5)

        current_price          = float(featured_df['close'].iloc[-1])
        forecast_price_low     = current_price * np.exp((pred - conf) / 100)
        forecast_price_mid     = current_price * np.exp(pred / 100)
        forecast_price_high    = current_price * np.exp((pred + conf) / 100)

        from config import MIN_FORECAST_RETURN
        signal = 'PASS' if pred >= MIN_FORECAST_RETURN else 'FAIL'

        return {
            'current_price'         : current_price,
            'forecast_return_pct'   : round(pred,  4),
            'lower_bound_return_pct': round(pred - conf, 4),
            'upper_bound_return_pct': round(pred + conf, 4),
            'forecast_price_mid'    : round(forecast_price_mid,  2),
            'forecast_price_low'    : round(forecast_price_low,  2),
            'forecast_price_high'   : round(forecast_price_high, 2),
            'signal'                : signal,
            'min_threshold_pct'     : MIN_FORECAST_RETURN,
            'feature_snapshot'      : {k: round(float(v), 6)
                                       for k, v in zip(FEATURE_COLS, X[0])},
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _metrics(y_true, y_pred, label='') -> dict:
    residuals  = y_true - y_pred
    rmse       = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae        = float(mean_absolute_error(y_true, y_pred))
    res_std    = float(np.std(residuals))
    # Direction accuracy: did model get the sign of the return right?
    dir_acc    = float(np.mean(np.sign(y_true) == np.sign(y_pred)))
    return {
        'rmse'         : round(rmse,    4),
        'mae'          : round(mae,     4),
        'residual_std' : round(res_std, 4),
        'direction_accuracy': round(dir_acc, 4),
    }
