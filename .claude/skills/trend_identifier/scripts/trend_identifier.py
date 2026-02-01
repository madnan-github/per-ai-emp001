#!/usr/bin/env python3
"""
Trend Identifier

This module identifies patterns in business metrics, customer interactions,
and market dynamics to uncover emerging trends and opportunities. The system
uses advanced analytics and machine learning techniques to detect subtle patterns
that may indicate significant shifts in business conditions, customer behavior,
or market dynamics.

Features:
- Advanced statistical trend detection
- Machine learning-based pattern recognition
- Time series analysis and forecasting
- Multiple data source integration
- Automated alerting for significant trends
- Comprehensive visualization capabilities
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
import sqlite3
from contextlib import contextmanager
import threading
import logging
from pathlib import Path
import requests
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, kpss
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False


class TrendType:
    """Enum for different trend types."""
    UPWARD = "upward"
    DOWNWARD = "downward"
    HORIZONTAL = "horizontal"
    CYCLICAL = "cyclical"
    SEASONAL = "seasonal"
    IRREGULAR = "irregular"


class TrendDuration:
    """Enum for different trend durations."""
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    EMERGING = "emerging"
    ESTABLISHED = "established"
    REVERSING = "reversing"


class TrendStrength:
    """Enum for different trend strengths."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NOISE = "noise"
    CONTRARIAN = "contrarian"
    CONVERGENT = "convergent"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    id: str
    name: str
    type: str  # database, api, file, streaming
    connection: Dict[str, Any]
    schedule: Dict[str, Any]
    metrics: List[Dict[str, Any]]
    enabled: bool = True


@dataclass
class TrendDetectionConfig:
    """Configuration for trend detection algorithms."""
    algorithm_name: str
    enabled: bool
    parameters: Dict[str, Any]
    weight: float = 1.0


@dataclass
class DetectedTrend:
    """Result of trend detection."""
    metric_name: str
    trend_type: TrendType
    start_date: str
    end_date: str
    strength: float  # Correlation coefficient or similar measure
    direction: float  # Slope of the trend line
    duration: int  # Number of time periods
    confidence: float
    significance: float  # P-value or similar
    forecast: Optional[List[float]] = None
    forecast_dates: Optional[List[str]] = None
    pattern_type: Optional[str] = None  # For pattern recognition
    validation_score: float = 0.0


@dataclass
class TrendReport:
    """Complete trend analysis report."""
    detected_trends: List[DetectedTrend]
    trend_metrics: Dict[str, Any]
    pattern_analysis: Dict[str, Any]
    forecasts: Dict[str, List[float]]
    alerts: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class DataCollector:
    """
    Handles data collection from various sources including databases, APIs, and files.
    Supports multiple data formats and provides data validation capabilities.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.sources = self._load_data_sources()
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for data collection."""
        logger = logging.getLogger('DataCollector')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_data_sources(self) -> List[DataSourceConfig]:
        """Load data source configurations."""
        sources = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    for source_data in config.get('data_sources', []):
                        source = DataSourceConfig(**source_data)
                        if source.enabled:
                            sources.append(source)
            except Exception as e:
                self.logger.error(f"Failed to load data sources: {e}")

        return sources

    def collect_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Collect data from all configured sources."""
        collected_data = {}

        for source in self.sources:
            try:
                if source.type == 'database':
                    data = self._collect_from_database(source, start_date, end_date)
                elif source.type == 'api':
                    data = self._collect_from_api(source, start_date, end_date)
                elif source.type == 'file':
                    data = self._collect_from_file(source, start_date, end_date)
                else:
                    self.logger.warning(f"Unsupported data source type: {source.type}")
                    continue

                if data is not None and not data.empty:
                    collected_data[source.id] = data
                    self.logger.info(f"Collected data from {source.name}: {len(data)} records")
            except Exception as e:
                self.logger.error(f"Error collecting data from {source.name}: {e}")

        return collected_data

    def _collect_from_database(self, source: DataSourceConfig, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect data from a database source."""
        connection_info = source.connection
        driver = connection_info.get('driver', 'sqlite')

        # Construct connection string
        if driver == 'sqlite':
            conn_str = f"sqlite:///{connection_info['database']}"
        else:
            username = os.getenv(connection_info.get('username_env_var', ''))
            password = os.getenv(connection_info.get('password_env_var', ''))
            host = connection_info.get('host', 'localhost')
            port = connection_info.get('port', 5432)
            database = connection_info.get('database', '')

            conn_str = f"{driver}://{username}:{password}@{host}:{port}/{database}"

        engine = create_engine(conn_str)

        # Execute queries
        all_data = []
        for query_config in source.connection.get('queries', []):
            sql = query_config['sql']
            # Replace date placeholders
            sql = sql.replace(':start_date', f"'{start_date}'")
            sql = sql.replace(':end_date', f"'{end_date}'")

            df = pd.read_sql(sql, engine)

            # Apply metrics mapping if specified
            metrics_mapping = query_config.get('metrics_mapping', {})
            for source_col, target_col in metrics_mapping.items():
                if source_col in df.columns:
                    df.rename(columns={source_col: target_col}, inplace=True)

            all_data.append(df)

        # Concatenate all query results
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()

    def _collect_from_api(self, source: DataSourceConfig, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect data from an API source."""
        url = source.connection['url']
        headers = source.connection.get('headers', {})

        # Replace placeholders in headers
        api_key = os.getenv(source.connection.get('api_key_env_var', ''))
        if '{{api_key}}' in str(headers):
            headers = {k: v.replace('{{api_key}}', api_key) for k, v in headers.items()}

        all_data = []
        for endpoint_config in source.connection.get('endpoints', []):
            endpoint_url = f"{url}{endpoint_config['endpoint']}"
            params = endpoint_config.get('params', {})

            # Replace date placeholders in params
            params = {
                k: v.replace('{{last_month_start}}', start_date).replace('{{last_month_end}}', end_date)
                for k, v in params.items()
            }

            try:
                response = requests.get(endpoint_url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Extract metrics based on configuration
                extracted_data = []
                for item in (data if isinstance(data, list) else [data]):
                    row_data = {}

                    for extraction_config in endpoint_config.get('metrics_extraction', []):
                        source_field = extraction_config['source_field']
                        metric_name = extraction_config['metric_name']

                        if source_field in item:
                            row_data[metric_name] = item[source_field]

                    if row_data:
                        extracted_data.append(row_data)

                if extracted_data:
                    df = pd.DataFrame(extracted_data)
                    all_data.append(df)
            except Exception as e:
                self.logger.error(f"API request failed for {endpoint_url}: {e}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()

    def _collect_from_file(self, source: DataSourceConfig, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect data from file sources."""
        file_path = source.connection['file_path']

        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            self.logger.error(f"Unsupported file format: {file_path}")
            return pd.DataFrame()

        # Apply date filters if specified
        date_column = source.connection.get('date_column', 'date')
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
            df = df[mask]

        return df


class StatisticalTrendDetector:
    """
    Implements statistical methods for trend detection including linear regression,
    moving averages, and seasonal decomposition.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for statistical analysis."""
        logger = logging.getLogger('StatisticalTrendDetector')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def detect_linear_trend(self, data: pd.Series, min_data_points: int = 10) -> Optional[Tuple[float, float, float]]:
        """
        Detect linear trend using linear regression.

        Returns:
            Tuple of (slope, r_squared, p_value) or None if insufficient data
        """
        if len(data) < min_data_points:
            return None

        # Prepare data for regression
        y = data.dropna().values
        x = np.arange(len(y)).reshape(-1, 1)

        if len(x) < min_data_points:
            return None

        # Fit linear regression
        model = LinearRegression()
        model.fit(x, y)

        # Calculate R-squared
        r_squared = model.score(x, y)

        # Calculate p-value for the slope
        n = len(y)
        deg_freedom = n - 2
        sse = np.sum((y - model.predict(x)) ** 2)
        if sse == 0:
            p_value = 0.0
        else:
            mse = sse / deg_freedom
            se_slope = np.sqrt(mse / np.sum((x.flatten() - np.mean(x)) ** 2))
            t_stat = model.coef_[0] / se_slope if se_slope != 0 else 0
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), deg_freedom))

        return model.coef_[0], r_squared, p_value

    def calculate_moving_average(self, data: pd.Series, window_sizes: List[int]) -> Dict[int, pd.Series]:
        """Calculate moving averages for different window sizes."""
        ma_data = {}
        for window in window_sizes:
            ma_data[window] = data.rolling(window=window).mean()
        return ma_data

    def detect_seasonal_trend(self, data: pd.Series, period: int = 7) -> Optional[Dict[str, Any]]:
        """Detect seasonal trends using seasonal decomposition."""
        if len(data) < period * 2:  # Need at least 2 full periods
            return None

        try:
            # Perform seasonal decomposition
            decomposition = seasonal_decompose(data.dropna(), model='additive', period=period)

            # Analyze trend component
            trend_slope, trend_r2, trend_p = self.detect_linear_trend(decomposition.trend)

            return {
                'trend_slope': trend_slope,
                'trend_r2': trend_r2,
                'trend_p_value': trend_p,
                'seasonal_amplitude': decomposition.seasonal.std(),
                'residual_std': decomposition.resid.std()
            }
        except Exception as e:
            self.logger.warning(f"Seasonal decomposition failed: {e}")
            return None

    def detect_statistical_trends(self, df: pd.DataFrame, config: TrendDetectionConfig) -> List[DetectedTrend]:
        """Detect trends using statistical methods."""
        trends = []

        # Only analyze numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()

            if config.algorithm_name == 'linear_regression':
                result = self.detect_linear_trend(series, config.parameters.get('min_data_points', 10))
                if result:
                    slope, r_squared, p_value = result
                    trend_type = self._classify_trend_type(slope)

                    trend = DetectedTrend(
                        metric_name=col,
                        trend_type=trend_type,
                        start_date=df.index.min().strftime('%Y-%m-%d') if not df.empty else '',
                        end_date=df.index.max().strftime('%Y-%m-%d') if not df.empty else '',
                        strength=r_squared,
                        direction=slope,
                        duration=len(series),
                        confidence=1 - p_value,
                        significance=p_value,
                        validation_score=0.0
                    )
                    trends.append(trend)

            elif config.algorithm_name == 'seasonal_decomposition':
                result = self.detect_seasonal_trend(series, config.parameters.get('period', 7))
                if result:
                    trend_type = self._classify_trend_type(result['trend_slope'])

                    trend = DetectedTrend(
                        metric_name=col,
                        trend_type=trend_type,
                        start_date=df.index.min().strftime('%Y-%m-%d') if not df.empty else '',
                        end_date=df.index.max().strftime('%Y-%m-%d') if not df.empty else '',
                        strength=result['trend_r2'],
                        direction=result['trend_slope'],
                        duration=len(series),
                        confidence=1 - result['trend_p_value'],
                        significance=result['trend_p_value'],
                        pattern_type='seasonal',
                        validation_score=0.0
                    )
                    trends.append(trend)

        return trends

    def _classify_trend_type(self, slope: float) -> TrendType:
        """Classify trend type based on slope value."""
        if slope > 0.01:
            return TrendType.UPWARD
        elif slope < -0.01:
            return TrendType.DOWNWARD
        else:
            return TrendType.HORIZONTAL


class MachineLearningTrendDetector:
    """
    Implements machine learning methods for trend detection including neural networks,
    ensemble methods, and clustering algorithms.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for ML analysis."""
        logger = logging.getLogger('MLTrendDetector')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def detect_ml_trends(self, df: pd.DataFrame, config: TrendDetectionConfig) -> List[DetectedTrend]:
        """Detect trends using machine learning methods."""
        trends = []

        # Only analyze numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()

            if len(series) < 10:  # Need sufficient data for ML
                continue

            if config.algorithm_name == 'random_forest':
                trend = self._detect_rf_trend(series, col, config)
                if trend:
                    trends.append(trend)
            elif config.algorithm_name == 'neural_network' and TENSORFLOW_AVAILABLE:
                trend = self._detect_nn_trend(series, col, config)
                if trend:
                    trends.append(trend)
            elif config.algorithm_name == 'isolation_forest':
                anomalies = self._detect_anomalies(series, col, config)
                trends.extend(anomalies)

        return trends

    def _detect_rf_trend(self, series: pd.Series, metric_name: str, config: TrendDetectionConfig) -> Optional[DetectedTrend]:
        """Detect trends using Random Forest."""
        try:
            # Prepare features (using index as time feature)
            X = np.arange(len(series)).reshape(-1, 1)
            y = series.values

            # Train Random Forest
            rf = RandomForestRegressor(
                n_estimators=config.parameters.get('n_estimators', 100),
                max_depth=config.parameters.get('max_depth', 10),
                random_state=42
            )
            rf.fit(X, y)

            # Get feature importance (time trend)
            importance = rf.feature_importances_[0]

            # Predict to get trend direction
            y_pred = rf.predict(X)

            # Calculate trend metrics
            slope = np.polyfit(np.arange(len(y)), y, 1)[0]  # Linear approximation
            r_squared = r2_score(y, y_pred)

            trend_type = self._classify_trend_type(slope)

            return DetectedTrend(
                metric_name=metric_name,
                trend_type=trend_type,
                start_date=series.index.min().strftime('%Y-%m-%d') if hasattr(series.index, 'strftime') else '',
                end_date=series.index.max().strftime('%Y-%m-%d') if hasattr(series.index, 'strftime') else '',
                strength=r_squared,
                direction=slope,
                duration=len(series),
                confidence=min(1.0, importance),
                significance=0.05,  # Default significance
                validation_score=0.0
            )
        except Exception as e:
            self.logger.warning(f"Random Forest trend detection failed for {metric_name}: {e}")
            return None

    def _detect_nn_trend(self, series: pd.Series, metric_name: str, config: TrendDetectionConfig) -> Optional[DetectedTrend]:
        """Detect trends using Neural Network (LSTM)."""
        if not TENSORFLOW_AVAILABLE:
            return None

        try:
            # Normalize the data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

            # Prepare sequences for LSTM
            seq_length = config.parameters.get('sequence_length', 10)
            X, y = [], []

            for i in range(seq_length, len(scaled_data)):
                X.append(scaled_data[i-seq_length:i])
                y.append(scaled_data[i])

            if len(X) == 0:
                return None

            X, y = np.array(X), np.array(y)
            X = X.reshape((X.shape[0], X.shape[1], 1))

            # Build LSTM model
            model = Sequential([
                LSTM(config.parameters.get('hidden_units', 50), return_sequences=True),
                LSTM(config.parameters.get('hidden_units', 50)),
                Dense(1)
            ])

            model.compile(optimizer='adam', loss='mse')
            model.fit(X, y, epochs=config.parameters.get('epochs', 10), verbose=0)

            # Get predictions to assess trend
            predictions = model.predict(X)
            r_squared = r2_score(y, predictions.flatten())

            # Calculate trend direction from original data
            slope = np.polyfit(np.arange(len(series)), series.values, 1)[0]

            trend_type = self._classify_trend_type(slope)

            return DetectedTrend(
                metric_name=metric_name,
                trend_type=trend_type,
                start_date=series.index.min().strftime('%Y-%m-%d') if hasattr(series.index, 'strftime') else '',
                end_date=series.index.max().strftime('%Y-%m-%d') if hasattr(series.index, 'strftime') else '',
                strength=r_squared,
                direction=slope,
                duration=len(series),
                confidence=min(1.0, r_squared + 0.1),  # Add small buffer
                significance=0.05,
                validation_score=0.0
            )
        except Exception as e:
            self.logger.warning(f"LSTM trend detection failed for {metric_name}: {e}")
            return None

    def _detect_anomalies(self, series: pd.Series, metric_name: str, config: TrendDetectionConfig) -> List[DetectedTrend]:
        """Detect anomalies using Isolation Forest."""
        try:
            # Prepare data
            X = series.values.reshape(-1, 1)

            # Fit Isolation Forest
            iso_forest = IsolationForest(
                contamination=config.parameters.get('contamination', 0.1),
                n_estimators=config.parameters.get('n_estimators', 100),
                random_state=42
            )
            anomaly_labels = iso_forest.fit_predict(X)

            # Count anomalies
            n_anomalies = sum(anomaly_labels == -1)
            anomaly_ratio = n_anomalies / len(series)

            if n_anomalies > 0:
                # Calculate trend direction from original data
                slope = np.polyfit(np.arange(len(series)), series.values, 1)[0]

                trend = DetectedTrend(
                    metric_name=metric_name,
                    trend_type=TrendType.IRREGULAR,
                    start_date=series.index.min().strftime('%Y-%m-%d') if hasattr(series.index, 'strftime') else '',
                    end_date=series.index.max().strftime('%Y-%m-%d') if hasattr(series.index, 'strftime') else '',
                    strength=anomaly_ratio,
                    direction=slope,
                    duration=len(series),
                    confidence=anomaly_ratio,
                    significance=0.05,
                    pattern_type='anomaly',
                    validation_score=0.0
                )
                return [trend]
            else:
                return []
        except Exception as e:
            self.logger.warning(f"Anomaly detection failed for {metric_name}: {e}")
            return []

    def _classify_trend_type(self, slope: float) -> TrendType:
        """Classify trend type based on slope value."""
        if slope > 0.01:
            return TrendType.UPWARD
        elif slope < -0.01:
            return TrendType.DOWNWARD
        else:
            return TrendType.HORIZONTAL


class PatternRecognizer:
    """
    Implements pattern recognition techniques to identify specific trend shapes
    and cyclical patterns in the data.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for pattern recognition."""
        logger = logging.getLogger('PatternRecognizer')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def recognize_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Recognize patterns in the data."""
        patterns = {}

        # Only analyze numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()

            if len(series) < 10:  # Need sufficient data
                continue

            # Detect peaks and valleys
            peaks, _ = find_peaks(series.values, height=np.mean(series))
            valleys, _ = find_peaks(-series.values, height=-np.mean(series))

            # Analyze cyclical patterns
            cycle_info = self._analyze_cycles(series)

            # Store pattern information
            patterns[col] = {
                'peaks': len(peaks),
                'valleys': len(valleys),
                'cycle_info': cycle_info,
                'volatility': series.std(),
                'trend_direction': 'up' if series.iloc[-1] > series.iloc[0] else 'down'
            }

        return patterns

    def _analyze_cycles(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze cyclical patterns in the data."""
        try:
            # Use FFT to identify dominant frequencies
            fft_vals = np.fft.fft(series.values)
            freqs = np.fft.fftfreq(len(series))

            # Find dominant frequency (excluding DC component)
            magnitudes = np.abs(fft_vals)
            dominant_idx = np.argmax(magnitudes[1:]) + 1  # Skip DC component
            dominant_freq = freqs[dominant_idx]

            # Calculate estimated cycle length
            if dominant_freq != 0:
                cycle_length = int(1 / abs(dominant_freq))
            else:
                cycle_length = 0

            return {
                'dominant_frequency': dominant_freq,
                'estimated_cycle_length': cycle_length,
                'power_at_dominant_freq': magnitudes[dominant_idx]
            }
        except Exception as e:
            self.logger.warning(f"Cycle analysis failed: {e}")
            return {'dominant_frequency': 0, 'estimated_cycle_length': 0, 'power_at_dominant_freq': 0}


class TrendForecaster:
    """
    Implements forecasting techniques to predict future trend continuation
    using ARIMA models, exponential smoothing, and machine learning methods.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for forecasting."""
        logger = logging.getLogger('TrendForecaster')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def forecast_trends(self, df: pd.DataFrame, horizon: int = 30) -> Dict[str, List[float]]:
        """Forecast trends for the specified horizon."""
        forecasts = {}

        # Only analyze numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()

            if len(series) < 10:  # Need sufficient data for forecasting
                continue

            try:
                # Use ARIMA for forecasting
                forecast_values = self._arima_forecast(series, horizon)
                forecasts[col] = forecast_values
            except Exception as e:
                self.logger.warning(f"ARIMA forecasting failed for {col}: {e}")
                # Fallback to simple linear extrapolation
                forecasts[col] = self._linear_extrapolation(series, horizon)

        return forecasts

    def _arima_forecast(self, series: pd.Series, horizon: int) -> List[float]:
        """Generate ARIMA forecast."""
        # Determine ARIMA parameters using AIC
        best_aic = float('inf')
        best_order = (1, 1, 1)

        for p in range(3):
            for d in range(2):
                for q in range(3):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fitted_model = model.fit()

                        if fitted_model.aic < best_aic:
                            best_aic = fitted_model.aic
                            best_order = (p, d, q)
                    except:
                        continue

        # Fit model with best parameters
        model = ARIMA(series, order=best_order)
        fitted_model = model.fit()

        # Generate forecast
        forecast_result = fitted_model.forecast(steps=horizon)
        return forecast_result.tolist()

    def _linear_extrapolation(self, series: pd.Series, horizon: int) -> List[float]:
        """Simple linear extrapolation as fallback."""
        # Calculate linear trend
        x = np.arange(len(series))
        slope, intercept = np.polyfit(x, series.values, 1)

        # Extrapolate
        last_value_idx = len(series)
        forecast = [slope * (last_value_idx + i) + intercept for i in range(1, horizon + 1)]

        return forecast


class TrendValidator:
    """
    Validates detected trends using statistical tests and business logic
    to ensure reliability and relevance.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for validation."""
        logger = logging.getLogger('TrendValidator')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def validate_trends(self, trends: List[DetectedTrend], df: pd.DataFrame) -> List[DetectedTrend]:
        """Validate detected trends."""
        validated_trends = []

        for trend in trends:
            # Validate statistical significance
            is_statistically_significant = self._validate_statistical_significance(trend)

            # Validate business relevance
            is_business_relevant = self._validate_business_relevance(trend, df)

            # Calculate validation score
            validation_score = self._calculate_validation_score(
                trend, is_statistically_significant, is_business_relevant
            )

            # Update trend with validation score
            validated_trend = DetectedTrend(
                metric_name=trend.metric_name,
                trend_type=trend.trend_type,
                start_date=trend.start_date,
                end_date=trend.end_date,
                strength=trend.strength,
                direction=trend.direction,
                duration=trend.duration,
                confidence=trend.confidence,
                significance=trend.significance,
                forecast=trend.forecast,
                forecast_dates=trend.forecast_dates,
                pattern_type=trend.pattern_type,
                validation_score=validation_score
            )

            validated_trends.append(validated_trend)

        return validated_trends

    def _validate_statistical_significance(self, trend: DetectedTrend) -> bool:
        """Validate statistical significance of trend."""
        # Check if p-value indicates significance (typically < 0.05)
        return trend.significance < 0.05

    def _validate_business_relevance(self, trend: DetectedTrend, df: pd.DataFrame) -> bool:
        """Validate business relevance of trend."""
        # Check if trend is strong enough to be relevant
        # This is a simplified check - in practice, business relevance would depend on domain-specific thresholds
        return trend.strength > 0.3 or abs(trend.direction) > 0.01

    def _calculate_validation_score(self, trend: DetectedTrend, stat_sig: bool, bus_rel: bool) -> float:
        """Calculate overall validation score."""
        score = 0.0

        # Base score from strength and confidence
        score += trend.strength * 0.4
        score += trend.confidence * 0.3

        # Bonus for statistical significance
        if stat_sig:
            score += 0.2

        # Bonus for business relevance
        if bus_rel:
            score += 0.1

        return min(1.0, score)  # Cap at 1.0


class AlertManager:
    """
    Manages trend alerts and notifications based on configured thresholds
    and business rules. Sends notifications through various channels.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.alert_configs = self._load_alert_configs()
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for alert management."""
        logger = logging.getLogger('AlertManager')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_alert_configs(self) -> List[Dict[str, Any]]:
        """Load alert configurations."""
        configs = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    configs = config.get('alerts', {}).get('trend_emergence', {}).get('conditions', [])
            except Exception as e:
                self.logger.error(f"Failed to load alert configs: {e}")

        return configs

    def check_for_alerts(self, validated_trends: List[DetectedTrend]) -> List[Dict[str, Any]]:
        """Check validated trends for conditions that trigger alerts."""
        triggered_alerts = []

        for alert_config in self.alert_configs:
            for trend in validated_trends:
                # Evaluate condition - simplified for this example
                # In a real implementation, you'd have more sophisticated condition parsing
                if self._evaluate_alert_condition(alert_config, trend):
                    alert = {
                        'alert_name': 'trend_emergence',
                        'severity': alert_config.get('severity', 'medium'),
                        'metric_name': trend.metric_name,
                        'trend_type': trend.trend_type.value,
                        'strength': trend.strength,
                        'direction': trend.direction,
                        'confidence': trend.confidence,
                        'validation_score': trend.validation_score,
                        'timestamp': datetime.now().isoformat(),
                        'recipients': alert_config.get('recipients', [])
                    }
                    triggered_alerts.append(alert)

        return triggered_alerts

    def _evaluate_alert_condition(self, alert_config: Dict[str, Any], trend: DetectedTrend) -> bool:
        """Evaluate if an alert condition is met."""
        # Simplified condition evaluation
        condition_str = alert_config.get('condition', '')

        # Check for strength condition
        if 'trend_strength' in condition_str and 'strong' in condition_str:
            return trend.strength >= 0.7 and trend.validation_score >= 0.8

        # Check for confidence condition
        if 'confidence' in condition_str:
            return trend.confidence >= 0.8

        # Default: return true if trend is strong and validated
        return trend.strength >= 0.7 and trend.validation_score >= 0.7


class TrendIdentifierEngine:
    """
    Main orchestrator that combines all components to provide end-to-end
    trend identification capabilities.
    """

    def __init__(self, config_path: str = None, output_dir: str = "./trend_analysis"):
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.data_collector = DataCollector(config_path)
        self.stat_detector = StatisticalTrendDetector()
        self.ml_detector = MachineLearningTrendDetector()
        self.pattern_recognizer = PatternRecognizer()
        self.forecaster = TrendForecaster()
        self.validator = TrendValidator()
        self.alert_manager = AlertManager(config_path)

        self.logger = self._setup_logger()

        # Load algorithm configurations
        self.algorithms = self._load_algorithm_configs()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the trend identifier engine."""
        logger = logging.getLogger('TrendIdentifierEngine')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_algorithm_configs(self) -> List[TrendDetectionConfig]:
        """Load trend detection algorithm configurations."""
        configs = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                    # Extract algorithm configurations
                    stat_methods = config.get('trend_detection_algorithms', {}).get('statistical_methods', {}).get('methods', [])
                    ml_methods = config.get('trend_detection_algorithms', {}).get('machine_learning_methods', {}).get('methods', [])

                    for method in stat_methods:
                        if method.get('enabled', False):
                            config_obj = TrendDetectionConfig(
                                algorithm_name=method['name'],
                                enabled=method['enabled'],
                                parameters=method.get('parameters', {}),
                                weight=method.get('weight', 1.0)
                            )
                            configs.append(config_obj)

                    for method in ml_methods:
                        if method.get('enabled', False):
                            config_obj = TrendDetectionConfig(
                                algorithm_name=method['name'],
                                enabled=method['enabled'],
                                parameters=method.get('parameters', {}),
                                weight=method.get('weight', 1.0)
                            )
                            configs.append(config_obj)

            except Exception as e:
                self.logger.error(f"Failed to load algorithm configs: {e}")

        return configs

    def identify_trends(self, start_date: str = None, end_date: str = None) -> TrendReport:
        """Run a complete trend identification cycle."""
        # Use last month's dates if not provided
        if not start_date or not end_date:
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=30)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')

        self.logger.info(f"Starting trend identification for period: {start_date} to {end_date}")

        # Step 1: Collect data
        raw_data = self.data_collector.collect_data(start_date, end_date)

        if not raw_data:
            self.logger.warning("No data collected, returning empty analysis")
            return self._create_empty_report(start_date, end_date)

        # Step 2: Detect trends using various methods
        all_detected_trends = []
        trend_metrics = {}
        pattern_analysis = {}
        forecasts = {}
        alerts = []

        for source_id, df in raw_data.items():
            if df.empty:
                continue

            # Store basic metrics
            trend_metrics[source_id] = df.describe().to_dict()

            # Detect trends using statistical methods
            for config in self.algorithms:
                if config.algorithm_name in ['linear_regression', 'seasonal_decomposition']:
                    trends = self.stat_detector.detect_statistical_trends(df, config)
                    all_detected_trends.extend(trends)

            # Detect trends using ML methods
            for config in self.algorithms:
                if config.algorithm_name in ['random_forest', 'neural_network', 'isolation_forest']:
                    trends = self.ml_detector.detect_ml_trends(df, config)
                    all_detected_trends.extend(trends)

            # Perform pattern recognition
            patterns = self.pattern_recognizer.recognize_patterns(df)
            pattern_analysis[source_id] = patterns

            # Generate forecasts
            forecasts.update(self.forecaster.forecast_trends(df, horizon=30))

        # Step 3: Validate trends
        validated_trends = self.validator.validate_trends(all_detected_trends,
                                                        pd.concat(raw_data.values(), sort=False) if raw_data else pd.DataFrame())

        # Step 4: Check for alerts
        alerts = self.alert_manager.check_for_alerts(validated_trends)

        # Step 5: Compile report
        metadata = {
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_period': {'start': start_date, 'end': end_date},
            'data_sources_analyzed': list(raw_data.keys()),
            'total_trends_detected': len(validated_trends),
            'total_alerts_generated': len(alerts)
        }

        return TrendReport(
            detected_trends=validated_trends,
            trend_metrics=trend_metrics,
            pattern_analysis=pattern_analysis,
            forecasts=forecasts,
            alerts=alerts,
            metadata=metadata
        )

    def _create_empty_report(self, start_date: str, end_date: str) -> TrendReport:
        """Create an empty report when no data is available."""
        return TrendReport(
            detected_trends=[],
            trend_metrics={},
            pattern_analysis={},
            forecasts={},
            alerts=[],
            metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'analysis_period': {'start': start_date, 'end': end_date},
                'data_sources_analyzed': [],
                'total_trends_detected': 0,
                'total_alerts_generated': 0
            }
        )

    def get_trend_summary(self, report: TrendReport) -> Dict[str, Any]:
        """Get a summary of the trend analysis."""
        if not report.detected_trends:
            return {'message': 'No trends detected in the analyzed data.'}

        # Count trends by type
        trend_counts = {}
        for trend in report.detected_trends:
            trend_type = trend.trend_type.value
            if trend_type in trend_counts:
                trend_counts[trend_type] += 1
            else:
                trend_counts[trend_type] = 1

        # Calculate average metrics
        avg_strength = np.mean([t.strength for t in report.detected_trends]) if report.detected_trends else 0
        avg_confidence = np.mean([t.confidence for t in report.detected_trends]) if report.detected_trends else 0
        avg_validation = np.mean([t.validation_score for t in report.detected_trends]) if report.detected_trends else 0

        return {
            'total_trends': len(report.detected_trends),
            'trend_distribution': trend_counts,
            'average_strength': avg_strength,
            'average_confidence': avg_confidence,
            'average_validation_score': avg_validation,
            'strong_trends': len([t for t in report.detected_trends if t.strength > 0.7]),
            'high_confidence_trends': len([t for t in report.detected_trends if t.confidence > 0.8])
        }


def main():
    """Main function for testing and demonstration."""
    print("Trend Identifier")
    print("================")

    # Initialize the trend identifier
    config_path = os.getenv('TREND_IDENTIFIER_CONFIG_PATH', './trend_config.json')
    trend_identifier = TrendIdentifierEngine(config_path)

    print("\nRunning trend identification...")

    # Run a sample analysis
    report = trend_identifier.identify_trends()

    print(f"Trend identification completed!")
    print(f"Period: {report.metadata['analysis_period']['start']} to {report.metadata['analysis_period']['end']}")
    print(f"Data sources analyzed: {len(report.metadata['data_sources_analyzed'])}")
    print(f"Total trends detected: {report.metadata['total_trends_detected']}")
    print(f"Total alerts generated: {report.metadata['total_alerts_generated']}")

    # Display trend summary
    summary = trend_identifier.get_trend_summary(report)
    print(f"\nTrend Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Show top 5 strongest trends
    if report.detected_trends:
        print(f"\nTop 5 Strongest Trends:")
        sorted_trends = sorted(report.detected_trends, key=lambda x: x.strength, reverse=True)[:5]
        for i, trend in enumerate(sorted_trends, 1):
            print(f"  {i}. {trend.metric_name}: {trend.trend_type.value} (strength: {trend.strength:.3f}, confidence: {trend.confidence:.3f})")

    # Show alerts if any
    if report.alerts:
        print(f"\nAlerts Generated:")
        for alert in report.alerts:
            print(f"  - {alert['alert_name']}: {alert['metric_name']} ({alert['severity']} severity)")


if __name__ == "__main__":
    main()