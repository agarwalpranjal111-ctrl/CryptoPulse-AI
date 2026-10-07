import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging
from datetime import datetime, timedelta

class AIPredictor:
    def __init__(self):
        
        self.models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'linear_regression': LinearRegression()
        }
        self.scaler = StandardScaler()
        
    def _prepare_features(self, prices):
        """Prepare features for ML models"""
        if len(prices) < 10:
            raise ValueError("Not enough data for prediction")
            
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp')
        
        # Calculate technical indicators
        df['price_change'] = df['price'].pct_change()
        df['ma_5'] = df['price'].rolling(window=5).mean()
        df['ma_10'] = df['price'].rolling(window=10).mean()
        df['volatility'] = df['price'].rolling(window=5).std()
        df['rsi'] = self._calculate_rsi(df['price'])
        
        # Create lag features
        for i in range(1, 6):
            df[f'price_lag_{i}'] = df['price'].shift(i)
            df[f'change_lag_{i}'] = df['price_change'].shift(i)
        
        # Time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        return df.dropna()
    
    def _calculate_rsi(self, prices, window=14):
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def predict_price(self, historical_data):
        """Generate price predictions using multiple models"""
        try:
            prices = historical_data['prices']
            if len(prices) < 10:  # Reduced minimum for faster processing
                return {'error': 'Insufficient historical data for prediction'}
            
            df = self._prepare_features(prices)
            
            # Prepare features and target
            feature_columns = [col for col in df.columns if col not in ['timestamp', 'price']]
            X = df[feature_columns].values
            y = df['price'].values
            
            if len(X) < 5:  # Reduced minimum for faster processing
                return {'error': 'Not enough clean data for prediction'}
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            predictions = {}
            model_performance = {}
            
            # Train and evaluate models
            for name, model in self.models.items():
                model.fit(X_train_scaled, y_train)
                y_pred = model.predict(X_test_scaled)
                
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                
                model_performance[name] = {
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'accuracy': float(max(0, 100 - (mae / np.mean(y_test)) * 100))
                }
                
                # Generate future predictions
                last_features = X_train_scaled[-1:] if len(X_train_scaled) > 0 else X_test_scaled[-1:]
                future_predictions = []
                
                for i in range(12):  # 12 hours ahead for faster processing
                    pred = model.predict(last_features)[0]
                    future_predictions.append(float(pred))
                    # Update features for next prediction (simplified)
                    if len(last_features[0]) > 0:
                        last_features = np.copy(last_features)
                        last_features[0, 0] = (pred - df['price'].iloc[-1]) / df['price'].iloc[-1]  # price_change
                
                predictions[name] = future_predictions
            
            # Generate timestamps for predictions
            last_timestamp = datetime.fromtimestamp(prices[-1][0] / 1000)
            prediction_timestamps = []
            for i in range(12):  # Match the reduced prediction horizon
                pred_time = last_timestamp + timedelta(hours=i+1)
                prediction_timestamps.append(pred_time.isoformat())
            
            return {
                'predictions': predictions,
                'timestamps': prediction_timestamps,
                'model_performance': model_performance,
                'current_price': float(prices[-1][1]),
                'confidence_level': self._calculate_confidence(model_performance),
                'recommendation': self._generate_recommendation(predictions, prices[-1][1])
            }
            
        except Exception as e:
            logging.error(f"Error in price prediction: {e}")
            return {'error': str(e)}
    
    def _calculate_confidence(self, performance):
        """Calculate overall confidence level based on model performance"""
        avg_accuracy = np.mean([perf['accuracy'] for perf in performance.values()])
        if avg_accuracy > 80:
            return 'High'
        elif avg_accuracy > 60:
            return 'Medium'
        else:
            return 'Low'
    
    def _generate_recommendation(self, predictions, current_price):
        """Generate trading recommendation based on predictions"""
        # Average predictions from all models
        avg_predictions = np.mean(list(predictions.values()), axis=0)
        
        # Calculate expected change
        short_term_change = (avg_predictions[2] - current_price) / current_price * 100
        medium_term_change = (avg_predictions[11] - current_price) / current_price * 100
        
        if short_term_change > 5 and medium_term_change > 10:
            return {'action': 'Strong Buy', 'confidence': 'High'}
        elif short_term_change > 2 and medium_term_change > 5:
            return {'action': 'Buy', 'confidence': 'Medium'}
        elif short_term_change < -5 and medium_term_change < -10:
            return {'action': 'Strong Sell', 'confidence': 'High'}
        elif short_term_change < -2 and medium_term_change < -5:
            return {'action': 'Sell', 'confidence': 'Medium'}
        else:
            return {'action': 'Hold', 'confidence': 'Medium'}