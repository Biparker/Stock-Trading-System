"""Forecasting methods for time-series prediction."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
import xgboost as xgb
import warnings
from config import (
    FORECAST_DAYS, ARIMA_MAX_P, ARIMA_MAX_D, ARIMA_MAX_Q,
    LSTM_LOOKBACK, LSTM_EPOCHS, LSTM_BATCH_SIZE,
    XGBOOST_LAG_FEATURES, XGBOOST_LEARNING_RATE, XGBOOST_N_ESTIMATORS
)

warnings.filterwarnings('ignore')

# Try to import TensorFlow, but make it optional
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except Exception as e:
    TENSORFLOW_AVAILABLE = False
    print(f"Warning: TensorFlow not available - LSTM method disabled. ({str(e)[:50]}...)")


class ForecastingBase:
    """Base class for all forecasting methods."""

    def __init__(self, data, feature_col='close', forecast_periods=FORECAST_DAYS):
        self.data = data.copy()
        self.feature_col = feature_col
        self.forecast_periods = forecast_periods
        self.model = None
        self.forecast = None
        self.confidence_interval = None
        self.metrics = {}

    def fit(self):
        """Fit the model (to be implemented by subclasses)."""
        raise NotImplementedError

    def predict(self):
        """Make predictions (to be implemented by subclasses)."""
        raise NotImplementedError

    def get_metrics(self):
        """Return model performance metrics."""
        return self.metrics

    def get_forecast(self):
        """Return forecast with confidence intervals."""
        return {
            'forecast': self.forecast,
            'confidence_interval': self.confidence_interval,
            'metrics': self.metrics
        }

    def _calculate_mape(self, y_true, y_pred):
        """Calculate Mean Absolute Percentage Error."""
        mask = y_true != 0
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


class LinearRegressionForecaster(ForecastingBase):
    """Linear regression with trend and MACD features."""

    def fit(self):
        data = self.data[self.feature_col].values

        # Calculate MACD
        macd_line, signal_line, histogram = self._calculate_macd(data)

        # Create features: time index + lagged prices + MACD
        X, y = self._create_features_with_macd(data, macd_line, signal_line, histogram)

        if len(X) < 10:
            raise ValueError("Insufficient data for Linear Regression training")

        self.model = LinearRegression()
        self.model.fit(X, y)

        # Store MACD data for prediction
        self.macd_line = macd_line
        self.signal_line = signal_line
        self.histogram = histogram
        self.n_features = X.shape[1]

        # Calculate validation metrics
        y_pred = self.model.predict(X)
        self.metrics['rmse'] = np.sqrt(mean_squared_error(y, y_pred))
        self.metrics['mae'] = mean_absolute_error(y, y_pred)
        self.metrics['mape'] = self._calculate_mape(y, y_pred)

    def _calculate_macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD line, signal line, and histogram."""
        df = pd.DataFrame({'close': data})

        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line.values, signal_line.values, histogram.values

    def _create_features_with_macd(self, data, macd_line, signal_line, histogram, lags=5):
        """Create features combining time index, lagged prices, and MACD."""
        X = []
        y = []

        for i in range(lags, len(data)):
            # Time feature
            time_feat = [i]

            # Lagged price features
            lag_feats = list(data[i-lags:i])

            # MACD features at current point
            macd_feats = [macd_line[i], signal_line[i], histogram[i]]

            # Combine all features
            features = time_feat + lag_feats + macd_feats
            X.append(features)
            y.append(data[i])

        return np.array(X), np.array(y)

    def predict(self):
        data = self.data[self.feature_col].values
        predictions = []

        # Initialize for forecasting
        lags = self.n_features - 4  # Number of lagged features (excluding time + 3 MACD)
        price_history = list(data[-lags:])
        current_macd = self.macd_line[-1]
        current_signal = self.signal_line[-1]
        current_histogram = self.histogram[-1]

        for step in range(self.forecast_periods):
            # Create feature vector: time index + lagged prices + MACD
            time_feat = [len(data) + step]
            macd_feats = [current_macd, current_signal, current_histogram]
            features = time_feat + price_history + macd_feats
            X = np.array(features).reshape(1, -1)

            # Predict next price
            next_pred = self.model.predict(X)[0]
            predictions.append(next_pred)

            # Update price history
            price_history = price_history[1:] + [next_pred]

            # Update MACD (approximate)
            extended_data = np.append(data, next_pred)
            new_macd, new_signal, new_histogram = self._calculate_macd(extended_data[-26:])
            current_macd = new_macd[-1]
            current_signal = new_signal[-1]
            current_histogram = new_histogram[-1]

        self.forecast = np.array(predictions)

        # Calculate confidence interval
        X, y = self._create_features_with_macd(data, self.macd_line, self.signal_line, self.histogram, lags)
        y_pred = self.model.predict(X)
        residuals = y - y_pred
        std_error = np.std(residuals)
        margin = 1.96 * std_error

        self.confidence_interval = {
            'lower': self.forecast - margin,
            'upper': self.forecast + margin
        }

        return self.forecast


class ARIMAForecaster(ForecastingBase):
    """ARIMA forecasting with parameter selection."""

    def fit(self):
        from statsmodels.tsa.arima.model import ARIMA

        data = self.data[self.feature_col].values

        # Try different ARIMA orders and pick the best
        best_aic = np.inf
        best_order = (1, 1, 1)

        for p in range(ARIMA_MAX_P + 1):
            for d in range(ARIMA_MAX_D + 1):
                for q in range(ARIMA_MAX_Q + 1):
                    try:
                        model = ARIMA(data, order=(p, d, q))
                        fitted_model = model.fit()
                        if fitted_model.aic < best_aic:
                            best_aic = fitted_model.aic
                            best_order = (p, d, q)
                    except:
                        continue

        # Fit final model with best order
        self.model = ARIMA(data, order=best_order)
        self.model = self.model.fit()

        # Validation metrics
        fitted = self.model.fittedvalues
        y = data[len(data)-len(fitted):]
        self.metrics['rmse'] = np.sqrt(mean_squared_error(y, fitted))
        self.metrics['mae'] = mean_absolute_error(y, fitted)
        self.metrics['mape'] = self._calculate_mape(y, fitted)

    def predict(self):
        forecast_result = self.model.get_forecast(steps=self.forecast_periods)
        pred_mean = forecast_result.predicted_mean
        self.forecast = pred_mean.values if hasattr(pred_mean, 'values') else pred_mean

        conf_int = forecast_result.conf_int(alpha=0.05)
        if hasattr(conf_int, 'iloc'):
            lower = conf_int.iloc[:, 0].values
            upper = conf_int.iloc[:, 1].values
        else:
            lower = conf_int[:, 0]
            upper = conf_int[:, 1]

        self.confidence_interval = {
            'lower': lower,
            'upper': upper
        }

        return self.forecast


class ExponentialSmoothingForecaster(ForecastingBase):
    """Triple exponential smoothing (Holt-Winters)."""

    def fit(self):
        data = self.data[self.feature_col].values

        # Use additive model for trend
        self.model = ExponentialSmoothing(
            data,
            trend='add',
            seasonal=None,
            initialization_method='estimated'
        )
        self.model = self.model.fit(optimized=True, disp=False)

        fitted = self.model.fittedvalues
        self.metrics['rmse'] = np.sqrt(mean_squared_error(data, fitted))
        self.metrics['mae'] = mean_absolute_error(data, fitted)
        self.metrics['mape'] = self._calculate_mape(data, fitted)

    def predict(self):
        forecast_result = self.model.get_forecast(steps=self.forecast_periods)
        self.forecast = forecast_result.predicted_mean.values

        # Confidence intervals
        conf_int = forecast_result.conf_int(alpha=0.05)
        self.confidence_interval = {
            'lower': conf_int.iloc[:, 0].values,
            'upper': conf_int.iloc[:, 1].values
        }

        return self.forecast


class ProphetForecaster(ForecastingBase):
    """Meta's Prophet forecasting model."""

    def fit(self):
        df = pd.DataFrame({
            'ds': self.data['date'],
            'y': self.data[self.feature_col]
        })

        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95,
            growth='linear'
        )

        self.model.fit(df)

        # Validation metrics
        forecast_train = self.model.predict(df)
        y = df['y'].values
        y_pred = forecast_train['yhat'].values
        self.metrics['rmse'] = np.sqrt(mean_squared_error(y, y_pred))
        self.metrics['mae'] = mean_absolute_error(y, y_pred)
        self.metrics['mape'] = self._calculate_mape(y, y_pred)

    def predict(self):
        future = self.model.make_future_dataframe(periods=self.forecast_periods)
        forecast = self.model.predict(future)

        # Get only future forecasts
        future_forecast = forecast.tail(self.forecast_periods)
        self.forecast = future_forecast['yhat'].values

        self.confidence_interval = {
            'lower': future_forecast['yhat_lower'].values,
            'upper': future_forecast['yhat_upper'].values
        }

        return self.forecast


class LSTMForecaster(ForecastingBase):
    """LSTM neural network for time-series forecasting with MACD."""

    def __init__(self, *args, **kwargs):
        if not TENSORFLOW_AVAILABLE:
            raise RuntimeError("TensorFlow is not available. Please use another forecasting method (arima, prophet, xgboost, etc.)")
        super().__init__(*args, **kwargs)

    def fit(self):
        data = self.data[self.feature_col].values

        # Calculate MACD
        macd_line, signal_line, histogram = self._calculate_macd(data)

        # Normalize price data
        self.scaler = MinMaxScaler()
        data_scaled = self.scaler.fit_transform(data.reshape(-1, 1)).flatten()

        # Normalize MACD indicators
        self.macd_scaler = MinMaxScaler()
        macd_features = np.column_stack([macd_line, signal_line, histogram])
        macd_scaled = self.macd_scaler.fit_transform(macd_features)

        # Create sequences with price and MACD
        X, y = self._create_sequences_with_macd(data_scaled, macd_scaled, LSTM_LOOKBACK)

        if len(X) < 10:
            raise ValueError("Insufficient data for LSTM training")

        # Store MACD data for prediction
        self.macd_line = macd_line
        self.signal_line = signal_line
        self.histogram = histogram

        # Build model with multiple input features
        self.model = Sequential([
            LSTM(64, activation='relu', input_shape=(LSTM_LOOKBACK, 4)),
            Dropout(0.2),
            LSTM(32, activation='relu'),
            Dropout(0.2),
            Dense(1)
        ])

        self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        self.model.fit(
            X, y,
            epochs=LSTM_EPOCHS,
            batch_size=LSTM_BATCH_SIZE,
            validation_split=0.2,
            verbose=0
        )

        # Validation metrics
        y_pred = self.model.predict(X, verbose=0).flatten()
        y_actual = self.scaler.inverse_transform(y.reshape(-1, 1)).flatten()
        y_pred_actual = self.scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()
        self.metrics['rmse'] = np.sqrt(mean_squared_error(y_actual, y_pred_actual))
        self.metrics['mae'] = mean_absolute_error(y_actual, y_pred_actual)
        self.metrics['mape'] = self._calculate_mape(y_actual, y_pred_actual)

    def _calculate_macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD line, signal line, and histogram."""
        df = pd.DataFrame({'close': data})

        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line.values, signal_line.values, histogram.values

    def _create_sequences_with_macd(self, price_data, macd_data, lookback):
        """Create sequences combining price and MACD data."""
        X, y = [], []
        for i in range(len(price_data) - lookback):
            # Combine price and MACD features
            price_seq = price_data[i:i+lookback].reshape(-1, 1)
            macd_seq = macd_data[i:i+lookback]
            seq = np.column_stack([price_seq, macd_seq])
            X.append(seq)
            y.append(price_data[i+lookback])
        return np.array(X), np.array(y)

    def _create_sequences(self, data, lookback):
        """Create sequences for LSTM (legacy)."""
        X, y = [], []
        for i in range(len(data) - lookback):
            X.append(data[i:i+lookback])
            y.append(data[i+lookback])
        return np.array(X), np.array(y)

    def predict(self):
        data = self.data[self.feature_col].values
        data_scaled = self.scaler.transform(data.reshape(-1, 1)).flatten()

        predictions = []
        price_history = list(data_scaled[-LSTM_LOOKBACK:])
        current_macd = self.macd_line[-1]
        current_signal = self.signal_line[-1]
        current_histogram = self.histogram[-1]

        for _ in range(self.forecast_periods):
            # Normalize MACD for input
            macd_vals = np.array([[current_macd, current_signal, current_histogram]])
            macd_scaled = self.macd_scaler.transform(macd_vals)[0]

            # Build feature sequence (price + MACD)
            price_seq = np.array(price_history).reshape(-1, 1)
            macd_seq = np.tile(macd_scaled, (LSTM_LOOKBACK, 1))
            seq = np.column_stack([price_seq, macd_seq]).reshape(1, LSTM_LOOKBACK, 4)

            # Predict next price
            next_pred_scaled = self.model.predict(seq, verbose=0)[0, 0]
            next_pred = self.scaler.inverse_transform([[next_pred_scaled]])[0, 0]
            predictions.append(next_pred)

            # Update price history
            price_history = price_history[1:] + [next_pred_scaled]

            # Update MACD (approximate)
            extended_data = np.append(data, next_pred)
            new_macd, new_signal, new_histogram = self._calculate_macd(extended_data[-26:])
            current_macd = new_macd[-1]
            current_signal = new_signal[-1]
            current_histogram = new_histogram[-1]

        self.forecast = np.array(predictions)

        # Calculate confidence interval
        macd_features = np.column_stack([self.macd_line, self.signal_line, self.histogram])
        macd_scaled = self.macd_scaler.transform(macd_features)
        X, y = self._create_sequences_with_macd(data_scaled, macd_scaled, LSTM_LOOKBACK)
        y_pred = self.model.predict(X, verbose=0).flatten()
        residuals = self.scaler.inverse_transform(y.reshape(-1, 1)).flatten() - \
                    self.scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()
        residuals_std = np.std(residuals)
        margin = 1.96 * residuals_std

        self.confidence_interval = {
            'lower': self.forecast - margin,
            'upper': self.forecast + margin
        }

        return self.forecast


class XGBoostForecaster(ForecastingBase):
    """XGBoost gradient boosting for time-series forecasting with MACD."""

    def fit(self):
        data = self.data[self.feature_col].values

        # Calculate MACD
        macd_line, signal_line, histogram = self._calculate_macd(data)

        # Create features: lagged prices + MACD indicators
        X, y = self._create_features_with_macd(data, macd_line, signal_line, histogram, XGBOOST_LAG_FEATURES)

        if len(X) < 10:
            raise ValueError("Insufficient data for XGBoost training")

        self.model = xgb.XGBRegressor(
            n_estimators=XGBOOST_N_ESTIMATORS,
            learning_rate=XGBOOST_LEARNING_RATE,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X, y, verbose=0)

        # Store MACD data for prediction
        self.macd_line = macd_line
        self.signal_line = signal_line
        self.histogram = histogram

        # Validation metrics
        y_pred = self.model.predict(X)
        self.metrics['rmse'] = np.sqrt(mean_squared_error(y, y_pred))
        self.metrics['mae'] = mean_absolute_error(y, y_pred)
        self.metrics['mape'] = self._calculate_mape(y, y_pred)

        # Extra metrics for dashboard two-panel chart
        residuals = y - y_pred
        self.metrics['residual_std'] = float(np.std(residuals))
        direction_correct = int(np.sum(np.sign(np.diff(y)) == np.sign(np.diff(y_pred))))
        self.metrics['direction_accuracy'] = float(direction_correct / max(len(y) - 1, 1))
        split_idx = int(len(self.data) * 0.8)
        self.metrics['train_cutoff_date'] = (
            str(self.data['date'].iloc[split_idx])
            if 'date' in self.data.columns else None
        )

    def _calculate_macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD line, signal line, and histogram."""
        df = pd.DataFrame({'close': data})

        # Calculate EMAs
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        # Histogram
        histogram = macd_line - signal_line

        return macd_line.values, signal_line.values, histogram.values

    def _create_features_with_macd(self, data, macd_line, signal_line, histogram, lags):
        """Create features combining lagged prices and MACD indicators."""
        X, y = [], []

        for i in range(len(data) - lags):
            # Lagged price features
            lag_features = data[i:i+lags]

            # MACD features (using current MACD values)
            macd_features = [macd_line[i+lags-1], signal_line[i+lags-1], histogram[i+lags-1]]

            # Combine all features
            features = np.concatenate([lag_features, macd_features])
            X.append(features)
            y.append(data[i+lags])

        return np.array(X), np.array(y)

    def _create_lagged_features(self, data, lags):
        """Create lagged features (for compatibility)."""
        X, y = [], []
        for i in range(len(data) - lags):
            X.append(data[i:i+lags])
            y.append(data[i+lags])
        return np.array(X), np.array(y)

    def predict(self):
        data = self.data[self.feature_col].values
        predictions = []

        # Start with the last known price and MACD values
        price_history = list(data[-XGBOOST_LAG_FEATURES:])
        current_macd = self.macd_line[-1]
        current_signal = self.signal_line[-1]
        current_histogram = self.histogram[-1]

        for _ in range(self.forecast_periods):
            # Create feature vector: lagged prices + MACD
            features = np.array([*price_history, current_macd, current_signal, current_histogram]).reshape(1, -1)

            # Predict next price
            next_pred = self.model.predict(features)[0]
            predictions.append(next_pred)

            # Update price history
            price_history = price_history[1:] + [next_pred]

            # Update MACD values (approximate: using predicted price to estimate MACD)
            extended_data = np.append(data, next_pred)
            new_macd, new_signal, new_histogram = self._calculate_macd(extended_data[-26:])
            current_macd = new_macd[-1]
            current_signal = new_signal[-1]
            current_histogram = new_histogram[-1]

        self.forecast = np.array(predictions)

        # Calculate confidence interval
        X, y = self._create_features_with_macd(data, self.macd_line, self.signal_line, self.histogram, XGBOOST_LAG_FEATURES)
        y_pred = self.model.predict(X)
        residuals = y - y_pred
        std_error = np.std(residuals)
        margin = 1.96 * std_error

        self.confidence_interval = {
            'lower': self.forecast - margin,
            'upper': self.forecast + margin
        }

        return self.forecast


def get_forecaster(method_name, data, feature_col='close'):
    """Factory function to get forecaster by name."""
    forecasters = {
        'linear_regression': LinearRegressionForecaster,
        'arima': ARIMAForecaster,
        'exponential_smoothing': ExponentialSmoothingForecaster,
        'prophet': ProphetForecaster,
        'xgboost': XGBoostForecaster,
    }

    # Add LSTM only if TensorFlow is available
    if TENSORFLOW_AVAILABLE:
        forecasters['lstm'] = LSTMForecaster

    if method_name not in forecasters:
        available = list(forecasters.keys())
        raise ValueError(f"Unknown method: {method_name}. Available: {available}")

    return forecasters[method_name](data, feature_col=feature_col)
