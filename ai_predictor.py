import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

N_LAGS = 10        # how many past hourly returns the models see
HORIZON = 24       # hours to forecast (the Predictions page shows 24h)


def _rsi(prices, window=14):
    delta = np.diff(prices[-(window + 1):])
    gain = delta[delta > 0].sum() / window
    loss = -delta[delta < 0].sum() / window
    if loss == 0:
        return 100.0 if gain > 0 else 50.0
    return 100 - 100 / (1 + gain / loss)


def _features(prices):
    """Features for predicting the NEXT hourly return, computed from prices up to now.

    Uses only returns / ratios (not raw prices), so it works the same whether
    the coin costs $0.1 or $100,000, and can be recomputed after each forecast step.
    """
    p = np.asarray(prices, dtype=float)
    rets = np.diff(p) / p[:-1]
    lags = rets[-N_LAGS:][::-1]                       # most recent first
    ma5 = p[-5:].mean()
    ma10 = p[-10:].mean()
    return np.concatenate([
        lags,
        [p[-1] / ma5 - 1, p[-1] / ma10 - 1, rets[-5:].std(), _rsi(p) / 100],
    ])


class AIPredictor:
    MIN_POINTS = N_LAGS + 20

    def _new_models(self):
        # Created per request: models/scalers are not shared between threads.
        return {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1),
            'linear_regression': LinearRegression(),
        }

    def predict_price(self, historical_data):
        """Forecast the next 12 hours with a time-ordered train/test split."""
        try:
            prices = [float(p[1]) for p in historical_data['prices']]
            if len(prices) < self.MIN_POINTS + 10:
                return {'error': 'Insufficient historical data for prediction'}

            # Training set: features at time t  ->  return from t to t+1
            start = max(N_LAGS + 1, 10)
            X, y, base = [], [], []
            for t in range(start, len(prices) - 1):
                X.append(_features(prices[:t + 1]))
                y.append(prices[t + 1] / prices[t] - 1)
                base.append(t)
            X, y, base = np.array(X), np.array(y), np.array(base)

            # Time-ordered split: train on the past, test on the most recent 20%
            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            price_now_test = np.array([prices[t] for t in base[split:]])
            actual_next = np.array([prices[t + 1] for t in base[split:]])

            scaler = StandardScaler().fit(X_train)
            Xtr, Xte = scaler.transform(X_train), scaler.transform(X_test)

            # Baseline: "price stays the same next hour"
            naive_mae = float(np.mean(np.abs(actual_next - price_now_test)))

            predictions, performance = {}, {}
            for name, model in self._new_models().items():
                model.fit(Xtr, y_train)

                pred_ret = model.predict(Xte)
                pred_next = price_now_test * (1 + pred_ret)
                mae = float(np.mean(np.abs(actual_next - pred_next)))
                rmse = float(np.sqrt(np.mean((actual_next - pred_next) ** 2)))
                mape = float(np.mean(np.abs(actual_next - pred_next) / actual_next) * 100)
                direction = float(np.mean(np.sign(pred_ret) == np.sign(y_test)) * 100)

                performance[name] = {
                    'mae': mae,
                    'rmse': rmse,
                    'accuracy': max(0.0, 100.0 - mape),   # 100 - average % error (1-hour ahead)
                    'directional_accuracy': direction,
                    'naive_mae': naive_mae,
                    'beats_naive': bool(mae < naive_mae),
                }

                # Recursive 12-hour forecast: each step appends the predicted
                # price and recomputes ALL features from the extended series.
                path = list(prices)
                future = []
                for _ in range(HORIZON):
                    r = float(model.predict(scaler.transform([_features(path)]))[0])
                    path.append(path[-1] * (1 + r))
                    future.append(float(path[-1]))
                predictions[name] = future

            last_ts = datetime.fromtimestamp(historical_data['prices'][-1][0] / 1000)
            timestamps = [(last_ts + timedelta(hours=i + 1)).isoformat() for i in range(HORIZON)]

            return {
                'predictions': predictions,
                'timestamps': timestamps,
                'model_performance': performance,
                'current_price': float(prices[-1]),
                'history': [float(x) for x in prices[-48:]],
                'confidence_level': self._calculate_confidence(performance),
                'recommendation': self._generate_recommendation(predictions, prices[-1]),
                'note': 'Experimental. Short-term crypto prices are very hard to predict; not financial advice.',
            }

        except Exception as e:
            logging.exception(f"Error in price prediction: {e}")
            return {'error': str(e)}

    def _calculate_confidence(self, performance):
        """Honest confidence: do the models actually beat the 'no change' baseline?"""
        beat = [p for p in performance.values() if p['beats_naive']]
        avg_dir = np.mean([p['directional_accuracy'] for p in performance.values()])
        if len(beat) == len(performance) and avg_dir >= 58:
            return 'High'
        if beat and avg_dir >= 52:
            return 'Medium'
        return 'Low'

    def _generate_recommendation(self, predictions, current_price):
        avg = np.mean(list(predictions.values()), axis=0)
        short = (avg[2] - current_price) / current_price * 100     # +3 hours
        medium = (avg[11] - current_price) / current_price * 100   # +12 hours

        if short > 2 and medium > 4:
            return {'action': 'Strong Buy', 'confidence': 'High'}
        if short > 0.5 and medium > 1:
            return {'action': 'Buy', 'confidence': 'Medium'}
        if short < -2 and medium < -4:
            return {'action': 'Strong Sell', 'confidence': 'High'}
        if short < -0.5 and medium < -1:
            return {'action': 'Sell', 'confidence': 'Medium'}
        return {'action': 'Hold', 'confidence': 'Medium'}
