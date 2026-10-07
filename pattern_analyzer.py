import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks
import logging
from datetime import datetime

class PatternAnalyzer:
    def __init__(self):
        self.patterns = {
            'support_resistance': self._find_support_resistance,
            'trend_analysis': self._analyze_trend,
            'volatility_analysis': self._analyze_volatility,
            'momentum_indicators': self._calculate_momentum,
            'candlestick_patterns': self._identify_candlestick_patterns
        }
    
    def analyze_patterns(self, historical_data):
        """Analyze various trading patterns in historical data"""
        try:
            prices = historical_data['prices']
            volumes = historical_data['total_volumes']
            
            if len(prices) < 20:
                return {'error': 'Insufficient data for pattern analysis'}
            
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['volume'] = [vol[1] for vol in volumes]
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp')
            
            results = {}
            
            # Run all pattern analyses
            for pattern_name, pattern_func in self.patterns.items():
                try:
                    results[pattern_name] = pattern_func(df)
                except Exception as e:
                    logging.error(f"Error in {pattern_name}: {e}")
                    results[pattern_name] = {'error': str(e)}
            
            # Generate overall pattern summary
            results['summary'] = self._generate_pattern_summary(results)
            results['timestamp'] = datetime.now().isoformat()
            
            return results
            
        except Exception as e:
            logging.error(f"Error in pattern analysis: {e}")
            return {'error': str(e)}
    
    def _find_support_resistance(self, df):
        """Identify support and resistance levels"""
        prices = df['price'].values

        # Find peaks (resistance) and valleys (support)
        peaks, _ = find_peaks(prices, distance=len(prices)//10)
        valleys, _ = find_peaks(-prices, distance=len(prices)//10)

        resistance_levels = prices[peaks] if len(peaks) > 0 else []
        support_levels = prices[valleys] if len(valleys) > 0 else []

        # Nearest resistance = lowest level ABOVE the current price,
        # nearest support = highest level BELOW the current price.
        current = float(prices[-1])
        above = [float(l) for l in resistance_levels if l > current]
        below = [float(l) for l in support_levels if l < current]
        nearest_resistance = min(above) if above else None
        nearest_support = max(below) if below else None

        return {
            'resistance_levels': [float(level) for level in resistance_levels[-3:]],
            'support_levels': [float(level) for level in support_levels[-3:]],
            'current_price': current,
            'nearest_resistance': nearest_resistance,
            'nearest_support': nearest_support
        }
        
    def _analyze_trend(self, df):
        """Analyze price trends using various methods"""
        prices = df['price'].values
        timestamps = np.arange(len(prices))
        
        # Linear regression for trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, prices)
        
        # Moving averages
        ma_short = df['price'].rolling(window=5).mean()
        ma_long = df['price'].rolling(window=20).mean()
        
        # Trend strength
        if abs(r_value) > 0.8:
            trend_strength = 'Strong'
        elif abs(r_value) > 0.5:
            trend_strength = 'Moderate'
        else:
            trend_strength = 'Weak'
        
        # Trend direction
        if slope > 0:
            trend_direction = 'Bullish'
        elif slope < 0:
            trend_direction = 'Bearish'
        else:
            trend_direction = 'Sideways'
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'slope': float(slope),
            'correlation': float(r_value),
            'ma_cross_signal': 'Bullish' if ma_short.iloc[-1] > ma_long.iloc[-1] else 'Bearish',
            'price_vs_ma': {
                'above_ma5': float(prices[-1]) > float(ma_short.iloc[-1]),
                'above_ma20': float(prices[-1]) > float(ma_long.iloc[-1])
            }
        }
    
    def _analyze_volatility(self, df):
        """Analyze price volatility patterns"""
        prices = df['price']
        returns = prices.pct_change().dropna()
        
        # Calculate various volatility metrics
        volatility_24h = returns.std() * np.sqrt(24)  # 24-hour volatility
        volatility_7d = returns.std() * np.sqrt(24 * 7)  # 7-day volatility
        
        # Rolling volatility
        rolling_vol = returns.rolling(window=24).std()
        
        # Volatility trend
        recent_vol = rolling_vol.tail(24).mean()
        historical_vol = rolling_vol.mean()
        
        vol_trend = 'Increasing' if recent_vol > historical_vol * 1.1 else 'Decreasing' if recent_vol < historical_vol * 0.9 else 'Stable'
        
        return {
            'volatility_24h': float(volatility_24h * 100),  # As percentage
            'volatility_7d': float(volatility_7d * 100),
            'volatility_trend': vol_trend,
            'volatility_level': 'High' if volatility_24h > 0.05 else 'Medium' if volatility_24h > 0.02 else 'Low',
            'recent_vs_historical': float((recent_vol / historical_vol - 1) * 100) if historical_vol > 0 else 0
        }
    
    def _calculate_momentum(self, df):
        """Calculate momentum indicators"""
        prices = df['price']
        
        # RSI calculation
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD calculation
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9).mean()
        macd_histogram = macd - macd_signal
        
        # Momentum interpretation
        rsi_signal = 'Overbought' if rsi.iloc[-1] > 70 else 'Oversold' if rsi.iloc[-1] < 30 else 'Neutral'
        macd_signal_interpretation = 'Bullish' if macd.iloc[-1] > macd_signal.iloc[-1] else 'Bearish'
        
        return {
            'rsi': float(rsi.iloc[-1]),
            'rsi_signal': rsi_signal,
            'macd': float(macd.iloc[-1]),
            'macd_signal': float(macd_signal.iloc[-1]),
            'macd_histogram': float(macd_histogram.iloc[-1]),
            'macd_signal_interpretation': macd_signal_interpretation,
            'momentum': 'Positive' if prices.iloc[-1] > prices.iloc[-5] else 'Negative'
        }
    
    def _identify_candlestick_patterns(self, df):
        """Identify basic candlestick patterns"""
        if len(df) < 3:
            return {'patterns': [], 'signal': 'Neutral'}
        
        prices = df['price'].values
        patterns_found = []
        
        # Simple pattern recognition based on price movements
        for i in range(2, len(prices)):
            prev2, prev1, current = prices[i-2], prices[i-1], prices[i]
            
            # Hammer pattern (simplified)
            if prev1 < prev2 and current > prev1 * 1.02:
                patterns_found.append('Bullish Reversal')
            
            # Shooting star pattern (simplified)
            elif prev1 > prev2 and current < prev1 * 0.98:
                patterns_found.append('Bearish Reversal')
            
            # Doji pattern (simplified)
            elif abs(current - prev1) / prev1 < 0.005:
                patterns_found.append('Doji')
        
        # Overall signal based on recent patterns
        recent_patterns = patterns_found[-3:] if len(patterns_found) >= 3 else patterns_found
        bullish_count = sum(1 for pattern in recent_patterns if 'Bullish' in pattern)
        bearish_count = sum(1 for pattern in recent_patterns if 'Bearish' in pattern)
        
        if bullish_count > bearish_count:
            overall_signal = 'Bullish'
        elif bearish_count > bullish_count:
            overall_signal = 'Bearish'
        else:
            overall_signal = 'Neutral'
        
        return {
            'recent_patterns': recent_patterns,
            'all_patterns': patterns_found,
            'overall_signal': overall_signal
        }
    
    def _generate_pattern_summary(self, results):
        """Generate an overall pattern summary"""
        signals = []
        
        # Collect signals from different analyses
        if 'trend_analysis' in results and 'error' not in results['trend_analysis']:
            signals.append(results['trend_analysis']['trend_direction'])
        
        if 'momentum_indicators' in results and 'error' not in results['momentum_indicators']:
            signals.append(results['momentum_indicators']['rsi_signal'])
            signals.append(results['momentum_indicators']['macd_signal_interpretation'])
        
        if 'candlestick_patterns' in results and 'error' not in results['candlestick_patterns']:
            signals.append(results['candlestick_patterns']['overall_signal'])
        
        # Count signal types
        bullish_signals = sum(1 for signal in signals if signal in ['Bullish', 'Strong Buy', 'Buy'])
        bearish_signals = sum(1 for signal in signals if signal in ['Bearish', 'Strong Sell', 'Sell'])
        neutral_signals = len(signals) - bullish_signals - bearish_signals
        
        # Determine overall sentiment
        if bullish_signals > bearish_signals + neutral_signals:
            overall_sentiment = 'Bullish'
            confidence = 'High' if bullish_signals >= 3 else 'Medium'
        elif bearish_signals > bullish_signals + neutral_signals:
            overall_sentiment = 'Bearish'
            confidence = 'High' if bearish_signals >= 3 else 'Medium'
        else:
            overall_sentiment = 'Neutral'
            confidence = 'Medium'
        
        return {
            'overall_sentiment': overall_sentiment,
            'confidence': confidence,
            'signal_breakdown': {
                'bullish': bullish_signals,
                'bearish': bearish_signals,
                'neutral': neutral_signals
            },
            'recommendation': self._get_recommendation(overall_sentiment, confidence)
        }
    
    def _get_recommendation(self, sentiment, confidence):
        """Get trading recommendation based on sentiment and confidence"""
        if sentiment == 'Bullish' and confidence == 'High':
            return 'Strong consideration for long positions'
        elif sentiment == 'Bullish':
            return 'Moderate bullish outlook, consider entry points'
        elif sentiment == 'Bearish' and confidence == 'High':
            return 'Strong bearish signals, consider exit strategy'
        elif sentiment == 'Bearish':
            return 'Moderate bearish outlook, exercise caution'
        else:
            return 'Mixed signals, wait for clearer direction'