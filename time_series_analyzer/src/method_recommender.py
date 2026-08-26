"""Method recommender agent for selecting best forecasting approach."""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings

warnings.filterwarnings('ignore')


class MethodRecommenderAgent:
    """Agent that analyzes data and recommends best forecasting methods."""

    def __init__(self, data, feature_col='close'):
        self.data = data
        self.feature_col = feature_col
        self.analysis = {}
        self.recommendations = []

    def analyze_data_characteristics(self):
        """
        Comprehensive analysis of time-series characteristics.

        Returns:
            dict: Analysis results
        """
        series = self.data[self.feature_col].values

        # Stationarity test
        stationarity = self._test_stationarity(series)

        # Trend analysis
        trend = self._analyze_trend(series)

        # Seasonality analysis
        seasonality = self._analyze_seasonality(series)

        # Volatility analysis
        volatility = self._analyze_volatility(series)

        # Data characteristics
        characteristics = {
            'length': len(series),
            'mean': np.mean(series),
            'std': np.std(series),
            'min': np.min(series),
            'max': np.max(series),
            'has_missing': np.isnan(series).sum() > 0,
        }

        self.analysis = {
            'stationarity': stationarity,
            'trend': trend,
            'seasonality': seasonality,
            'volatility': volatility,
            'characteristics': characteristics
        }

        return self.analysis

    def _test_stationarity(self, series):
        """Test for stationarity using ADF test."""
        try:
            result = adfuller(series, autolag='AIC')
            is_stationary = result[1] < 0.05

            return {
                'is_stationary': is_stationary,
                'adf_statistic': result[0],
                'p_value': result[1],
                'critical_values': result[4],
                'interpretation': 'Stationary (differencing not needed)' if is_stationary else 'Non-stationary (differencing needed)'
            }
        except Exception as e:
            return {
                'is_stationary': False,
                'adf_statistic': None,
                'p_value': None,
                'critical_values': None,
                'interpretation': f'Test failed: {str(e)}'
            }

    def _analyze_trend(self, series):
        """Analyze trend strength."""
        x = np.arange(len(series))
        z = np.polyfit(x, series, 1)
        p = np.poly1d(z)
        residuals = series - p(x)

        # R-squared for trend fit
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((series - np.mean(series))**2)
        r_squared = 1 - (ss_res / ss_tot)

        # Slope interpretation
        slope = z[0]
        slope_interpretation = 'Uptrend' if slope > 0 else 'Downtrend'

        return {
            'slope': slope,
            'r_squared': r_squared,
            'strength': 'Strong' if r_squared > 0.5 else 'Moderate' if r_squared > 0.2 else 'Weak',
            'direction': slope_interpretation
        }

    def _analyze_seasonality(self, series):
        """Analyze seasonality using decomposition."""
        try:
            # Use 252 (business days) as period
            if len(series) < 100:
                period = len(series) // 4
            else:
                period = 252

            decomposition = seasonal_decompose(series, model='additive', period=period)
            seasonal = decomposition.seasonal
            residual = decomposition.resid

            # Seasonal strength
            var_seasonal = np.var(seasonal[~np.isnan(seasonal)])
            var_residual = np.var(residual[~np.isnan(residual)])
            seasonal_strength = var_seasonal / (var_seasonal + var_residual)

            return {
                'has_seasonality': seasonal_strength > 0.1,
                'seasonal_strength': seasonal_strength,
                'period': period,
                'interpretation': 'Strong seasonality' if seasonal_strength > 0.3 else 'Weak seasonality' if seasonal_strength > 0.1 else 'No clear seasonality'
            }
        except Exception as e:
            return {
                'has_seasonality': False,
                'seasonal_strength': 0,
                'period': None,
                'interpretation': f'Analysis inconclusive: {str(e)}'
            }

    def _analyze_volatility(self, series):
        """Analyze volatility of the series."""
        returns = np.diff(series) / series[:-1]
        volatility = np.std(returns)
        cv = volatility / np.mean(series)  # Coefficient of variation

        return {
            'volatility': volatility * 100,
            'coefficient_of_variation': cv,
            'level': 'High' if cv > 0.04 else 'Moderate' if cv > 0.01 else 'Low'
        }

    def recommend_methods(self):
        """
        Recommend best forecasting methods based on analysis.

        Returns:
            list: Recommended methods with scores
        """
        if not self.analysis:
            self.analyze_data_characteristics()

        scores = {
            'linear_regression': 0,
            'arima': 0,
            'exponential_smoothing': 0,
            'prophet': 0,
            'lstm': 0,
            'xgboost': 0,
        }

        data = self.analysis

        # Stationarity-based scoring
        if data['stationarity']['is_stationary']:
            scores['arima'] += 2
            scores['exponential_smoothing'] += 1
        else:
            scores['prophet'] += 2
            scores['linear_regression'] += 1
            scores['exponential_smoothing'] += 1

        # Trend-based scoring
        if data['trend']['strength'] == 'Strong':
            scores['linear_regression'] += 2
            scores['prophet'] += 2
            scores['exponential_smoothing'] += 1
        elif data['trend']['strength'] == 'Moderate':
            scores['arima'] += 1
            scores['prophet'] += 1

        # Seasonality-based scoring
        if data['seasonality']['has_seasonality']:
            scores['prophet'] += 3
            scores['exponential_smoothing'] += 2
            scores['lstm'] += 1
        else:
            scores['arima'] += 2
            scores['linear_regression'] += 1

        # Volatility-based scoring
        if data['volatility']['level'] == 'High':
            scores['xgboost'] += 2
            scores['prophet'] += 1
        elif data['volatility']['level'] == 'Moderate':
            scores['xgboost'] += 1
        else:
            scores['linear_regression'] += 1
            scores['arima'] += 1

        # Data length-based scoring
        if data['characteristics']['length'] < 100:
            scores['linear_regression'] += 1
            scores['exponential_smoothing'] += 1
        elif data['characteristics']['length'] > 500:
            scores['xgboost'] += 1

        # Sort by score
        recommendations = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return recommendations

    def get_detailed_recommendations(self):
        """Get detailed recommendations with explanations."""
        if not self.analysis:
            self.analyze_data_characteristics()

        recommendations = self.recommend_methods()
        top_3 = recommendations[:3]

        detailed = []
        for method, score in top_3:
            detailed.append({
                'method': method,
                'score': score,
                'explanation': self._get_method_explanation(method)
            })

        return detailed

    def _get_method_explanation(self, method):
        """Get explanation for why a method is recommended."""
        data = self.analysis
        explanations = {
            'linear_regression': {
                'description': 'Simple trend-based forecasting',
                'strengths': ['Fast training', 'Interpretable', 'Good for strong trends'],
                'weaknesses': ['Cannot capture complex patterns', 'Assumes linear relationship'],
                'best_for': 'Stable trends without seasonality'
            },
            'arima': {
                'description': 'Statistical time-series model',
                'strengths': ['Good for stationary data', 'Well-established', 'Fast'],
                'weaknesses': ['Requires stationarity', 'Cannot handle strong seasonality'],
                'best_for': 'Stationary series with autocorrelation'
            },
            'exponential_smoothing': {
                'description': 'Triple exponential smoothing (Holt-Winters)',
                'strengths': ['Handles trend and seasonality', 'Intuitive', 'Fast'],
                'weaknesses': ['Limited flexibility', 'Assumes constant patterns'],
                'best_for': 'Series with trend and/or light seasonality'
            },
            'prophet': {
                'description': "Meta's time-series forecasting tool",
                'strengths': ['Handles seasonality well', 'Robust to missing data', 'Flexible'],
                'weaknesses': ['Less interpretable', 'Can overfit'],
                'best_for': 'Non-stationary data with seasonality'
            },
            'lstm': {
                'description': 'Deep learning neural network',
                'strengths': ['Captures complex patterns', 'Good for volatile data', 'Flexible'],
                'weaknesses': ['Requires more data', 'Longer training time', 'Black box'],
                'best_for': 'Complex patterns and high volatility'
            },
            'xgboost': {
                'description': 'Gradient boosting machine learning',
                'strengths': ['Excellent with mixed patterns', 'Feature importance', 'Robust'],
                'weaknesses': ['Requires feature engineering', 'Longer training time'],
                'best_for': 'Complex non-linear patterns'
            }
        }

        return explanations.get(method, {})

    def print_analysis_report(self):
        """Print formatted analysis report."""
        if not self.analysis:
            self.analyze_data_characteristics()

        data = self.analysis

        print("\n" + "="*70)
        print("TIME-SERIES DATA ANALYSIS REPORT")
        print("="*70)

        # Data characteristics
        print("\nDATA CHARACTERISTICS:")
        print(f"  Records:       {data['characteristics']['length']}")
        print(f"  Mean:          ${data['characteristics']['mean']:.2f}")
        print(f"  Std Dev:       ${data['characteristics']['std']:.2f}")
        print(f"  Min:           ${data['characteristics']['min']:.2f}")
        print(f"  Max:           ${data['characteristics']['max']:.2f}")

        # Stationarity
        print("\nSTATIONARITY TEST (ADF):")
        print(f"  Status:        {'[OK] Stationary' if data['stationarity']['is_stationary'] else '[NO] Non-stationary'}")
        p_val = data['stationarity']['p_value']
        p_val_str = f"{p_val:.4f}" if p_val is not None else 'N/A'
        print(f"  p-value:       {p_val_str}")
        print(f"  Interpretation: {data['stationarity']['interpretation']}")

        # Trend
        print("\nTREND ANALYSIS:")
        print(f"  Direction:     {data['trend']['direction']}")
        print(f"  Strength:      {data['trend']['strength']}")
        print(f"  R-squared:     {data['trend']['r_squared']:.3f}")

        # Seasonality
        print("\nSEASONALITY:")
        print(f"  Detected:      {'Yes' if data['seasonality']['has_seasonality'] else 'No'}")
        print(f"  Strength:      {data['seasonality']['seasonal_strength']:.3f}")
        print(f"  Interpretation: {data['seasonality']['interpretation']}")

        # Volatility
        print("\nVOLATILITY:")
        print(f"  Level:         {data['volatility']['level']}")
        print(f"  Volatility %:  {data['volatility']['volatility']:.2f}%")
        print(f"  Coeff of Var:  {data['volatility']['coefficient_of_variation']:.4f}")

        # Recommendations
        print("\nMETHOD RECOMMENDATIONS:")
        recommendations = self.get_detailed_recommendations()

        for i, rec in enumerate(recommendations, 1):
            method = rec['method'].replace('_', ' ').title()
            print(f"\n  {i}. {method} (Score: {rec['score']}/10)")
            exp = rec['explanation']
            print(f"     Description: {exp.get('description', 'N/A')}")
            print(f"     Strengths:   {', '.join(exp.get('strengths', []))}")
            print(f"     Best for:    {exp.get('best_for', 'N/A')}")

        print("\n" + "="*70 + "\n")


def main():
    """Example usage of MethodRecommenderAgent."""
    # Example with sample data
    dates = pd.date_range('2023-01-01', periods=252)
    trend = np.linspace(100, 120, 252)
    noise = np.random.normal(0, 2, 252)
    data = pd.DataFrame({
        'date': dates,
        'close': trend + noise
    })

    agent = MethodRecommenderAgent(data)
    agent.analyze_data_characteristics()
    agent.print_analysis_report()


if __name__ == '__main__':
    main()
