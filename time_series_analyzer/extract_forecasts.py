#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import numpy as np
from data_fetcher import DataFetcherAgent
from method_recommender import MethodRecommenderAgent
from forecasting_methods import get_forecaster

STOCKS = {
    'ETN': 425.27,
    'CAT': 1067.32,
}
METHODS = ['xgboost', 'arima', 'linear_regression']

print("ticker,method,current_price,day1_forecast,day36_forecast,mean_forecast,change_pct,rmse,mae,mape,signal")
print("-" * 110)

for ticker, current_price in STOCKS.items():
    fetcher = DataFetcherAgent()
    res = fetcher.fetch_stock_data(ticker)
    if res['status'] != 'success':
        print(f"ERROR: could not fetch {ticker}")
        continue
    data = res['data']

    for method in METHODS:
        try:
            forecaster = get_forecaster(method, data, feature_col='close')
            forecaster.fit()
            forecaster.predict()
            fc = forecaster.get_forecast()

            arr = np.array(fc['forecast'])
            metrics = fc.get('metrics') or {}
            rmse  = metrics.get('rmse',  0)
            mae   = metrics.get('mae',   0)
            mape  = metrics.get('mape',  0)
            day1  = arr[0]
            day36 = arr[-1]
            mean  = arr.mean()
            chg   = (day36 - current_price) / current_price * 100
            signal = "UPTREND" if chg > 1 else ("DOWNTREND" if chg < -1 else "FLAT")

            print(f"{ticker},{method},{current_price:.2f},{day1:.2f},{day36:.2f},{mean:.2f},{chg:.2f}%,{rmse:.2f},{mae:.2f},{mape:.4f},{signal}")
        except Exception as e:
            print(f"{ticker},{method},{current_price:.2f},ERROR,ERROR,ERROR,ERROR,ERROR,ERROR,ERROR,ERROR -- {e}")
