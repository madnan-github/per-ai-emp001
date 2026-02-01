#!/usr/bin/env python3
"""
Performance Analyzer

This module analyzes task completion times, identifies operational inefficiencies,
and provides actionable insights to improve productivity. The system monitors
various business processes and generates detailed performance reports to help
optimize operations and resource allocation.

Features:
- Automated data collection from multiple sources
- Advanced statistical analysis of performance metrics
- Anomaly detection and root cause analysis
- Performance trend identification
- Automated alerting for performance issues
- Comprehensive reporting and visualization
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.seasonal import seasonal_decompose
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import schedule
import time
import psutil
import warnings
warnings.filterwarnings('ignore')


class PerformanceMetric:
    """Enum for different performance metrics."""
    CYCLE_TIME = "cycle_time"
    TOUCH_TIME = "touch_time"
    WAIT_TIME = "wait_time"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    DEFECT_RATE = "defect_rate"
    RESOURCE_UTILIZATION = "resource_utilization"


class PerformanceCategory:
    """Enum for different performance categories."""
    TASK = "task"
    PROCESS = "process"
    SYSTEM = "system"
    TEAM = "team"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    id: str
    name: str
    type: str  # database, api, log_file, system_monitor, manual_input
    connection: Dict[str, Any]
    schedule: Dict[str, Any]
    metrics: List[Dict[str, Any]]
    enabled: bool = True


@dataclass
class PerformanceThreshold:
    """Configuration for performance thresholds."""
    metric_name: str
    optimal_range: List[float]
    warning_threshold: float
    critical_threshold: float
    weight: float = 1.0


@dataclass
class PerformanceInsight:
    """Result of performance analysis."""
    metric_name: str
    current_value: float
    baseline_value: float
    trend: str  # increasing, decreasing, stable
    severity: str  # low, medium, high, critical
    recommendation: str
    confidence: float


@dataclass
class PerformanceReport:
    """Complete performance analysis report."""
    insights: List[PerformanceInsight]
    metrics_summary: Dict[str, Any]
    trends: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    metadata: Dict[str, Any]


class DataCollector:
    """
    Handles data collection from various sources including databases, APIs, logs, and system metrics.
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
                elif source.type == 'log_file':
                    data = self._collect_from_log(source, start_date, end_date)
                elif source.type == 'system_monitor':
                    data = self._collect_from_system_monitor(source)
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
                k: v.replace('{{last_week_start}}', start_date).replace('{{last_week_end}}', end_date)
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

    def _collect_from_log(self, source: DataSourceConfig, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect data from log files."""
        file_path = source.connection['file_path']

        # For simplicity, assuming logs are in CSV format
        # In a real implementation, you'd parse various log formats
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            self.logger.error(f"Unsupported log format: {file_path}")
            return pd.DataFrame()

        # Apply date filters if specified
        date_column = source.connection.get('date_column', 'timestamp')
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
            df = df[mask]

        return df

    def _collect_from_system_monitor(self, source: DataSourceConfig) -> pd.DataFrame:
        """Collect system performance metrics."""
        # Get current system metrics
        metrics = {
            'timestamp': datetime.now(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_bytes_sent': psutil.net_io_counters().bytes_sent,
            'network_bytes_recv': psutil.net_io_counters().bytes_recv,
        }

        # Convert to DataFrame
        df = pd.DataFrame([metrics])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df


class PerformanceAnalyzer:
    """
    Performs statistical analysis on collected performance data to identify trends,
    anomalies, and inefficiencies. Uses various statistical and ML techniques.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for performance analysis."""
        logger = logging.getLogger('PerformanceAnalyzer')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def analyze_performance(self, raw_data: Dict[str, pd.DataFrame],
                           thresholds: List[PerformanceThreshold]) -> PerformanceReport:
        """Analyze performance data and generate insights."""
        insights = []
        metrics_summary = {}
        trends = {}
        anomalies = []
        recommendations = []

        for source_id, df in raw_data.items():
            if df.empty:
                continue

            # Calculate metrics for each configured metric
            for threshold in thresholds:
                if threshold.metric_name in df.columns:
                    current_value = df[threshold.metric_name].mean()
                    baseline_value = self._calculate_baseline(df, threshold.metric_name)

                    # Determine trend
                    trend = self._determine_trend(df, threshold.metric_name)

                    # Determine severity based on thresholds
                    severity = self._determine_severity(current_value, threshold)

                    # Generate recommendation
                    recommendation = self._generate_recommendation(threshold.metric_name, current_value, baseline_value, severity)

                    insight = PerformanceInsight(
                        metric_name=threshold.metric_name,
                        current_value=current_value,
                        baseline_value=baseline_value,
                        trend=trend,
                        severity=severity,
                        recommendation=recommendation,
                        confidence=self._calculate_confidence(df, threshold.metric_name)
                    )

                    insights.append(insight)

            # Perform deeper analysis
            source_insights = self._perform_deep_analysis(df, source_id)
            insights.extend(source_insights)

            # Detect anomalies
            source_anomalies = self._detect_anomalies(df)
            anomalies.extend(source_anomalies)

            # Calculate summary statistics
            metrics_summary[source_id] = df.describe().to_dict()

        # Generate overall recommendations
        recommendations = self._generate_overall_recommendations(insights)

        # Compile metadata
        metadata = {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_sources_analyzed': list(raw_data.keys()),
            'total_insights': len(insights),
            'total_anomalies': len(anomalies)
        }

        return PerformanceReport(
            insights=insights,
            metrics_summary=metrics_summary,
            trends=trends,
            anomalies=anomalies,
            recommendations=recommendations,
            metadata=metadata
        )

    def _calculate_baseline(self, df: pd.DataFrame, metric_name: str) -> float:
        """Calculate baseline value for a metric."""
        # Use median as baseline to reduce impact of outliers
        return df[metric_name].median()

    def _determine_trend(self, df: pd.DataFrame, metric_name: str) -> str:
        """Determine trend for a metric."""
        if len(df) < 2:
            return "stable"

        # Calculate slope using linear regression
        x = np.arange(len(df))
        y = df[metric_name].values

        # Handle case where we have constant values
        if np.all(y == y[0]):
            return "stable"

        # Calculate correlation coefficient
        slope, _, r_value, _, _ = stats.linregress(x, y)

        if abs(slope) < 1e-10:  # Very close to zero
            return "stable"
        elif slope > 0:
            return "increasing" if r_value > 0.1 else "volatile"
        else:
            return "decreasing" if r_value < -0.1 else "volatile"

    def _determine_severity(self, current_value: float, threshold: PerformanceThreshold) -> str:
        """Determine severity level based on thresholds."""
        if current_value <= threshold.optimal_range[1]:
            return "low"
        elif current_value <= threshold.warning_threshold:
            return "medium"
        elif current_value <= threshold.critical_threshold:
            return "high"
        else:
            return "critical"

    def _generate_recommendation(self, metric_name: str, current_value: float,
                                baseline_value: float, severity: str) -> str:
        """Generate recommendation based on metric analysis."""
        if severity == "critical":
            return f"URGENT: {metric_name} is critically high at {current_value:.2f}. Immediate action required."
        elif severity == "high":
            return f"WARNING: {metric_name} is high at {current_value:.2f}. Review required."
        elif severity == "medium":
            return f"MONITOR: {metric_name} is elevated at {current_value:.2f}. Consider optimization."
        else:
            return f"OK: {metric_name} is performing well at {current_value:.2f}."

    def _calculate_confidence(self, df: pd.DataFrame, metric_name: str) -> float:
        """Calculate confidence in the analysis."""
        if len(df) == 0:
            return 0.0

        # Confidence based on sample size and variance
        std_dev = df[metric_name].std()
        mean = df[metric_name].mean()

        if mean == 0:
            cv = float('inf')  # Coefficient of variation
        else:
            cv = std_dev / abs(mean) if std_dev != 0 else 0

        # Higher CV means less confidence
        confidence = max(0, min(1, 1 - cv))

        # Adjust based on sample size (larger samples get higher confidence)
        sample_size_factor = min(1, len(df) / 50)  # Cap at 1 after 50 samples
        confidence = (confidence + sample_size_factor) / 2

        return confidence

    def _perform_deep_analysis(self, df: pd.DataFrame, source_id: str) -> List[PerformanceInsight]:
        """Perform deeper statistical analysis."""
        insights = []

        # Only analyze numeric columns
        numeric_df = df.select_dtypes(include=[np.number])

        for col in numeric_df.columns:
            # Perform correlation analysis
            correlations = numeric_df.corr()[col].abs().sort_values(ascending=False)

            # Find highest correlation (excluding self)
            if len(correlations) > 1:
                top_corr = correlations.iloc[1]  # Skip self-correlation
                corr_feature = correlations.index[1]

                if top_corr > 0.5:  # Strong correlation
                    insight = PerformanceInsight(
                        metric_name=f"{col}_correlation_with_{corr_feature}",
                        current_value=top_corr,
                        baseline_value=0.0,
                        trend="stable",
                        severity="medium" if top_corr > 0.7 else "low",
                        recommendation=f"Strong correlation ({top_corr:.2f}) detected between {col} and {corr_feature}. Consider investigating causal relationship.",
                        confidence=top_corr
                    )
                    insights.append(insight)

        return insights

    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in the data using statistical methods."""
        anomalies = []

        # Only analyze numeric columns
        numeric_df = df.select_dtypes(include=[np.number])

        for col in numeric_df.columns:
            if len(df) < 10:  # Need sufficient data for anomaly detection
                continue

            # Use IQR method for anomaly detection
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_indices = df[outlier_mask].index.tolist()

            if len(outlier_indices) > 0:
                anomalies.append({
                    'column': col,
                    'outlier_indices': outlier_indices,
                    'outlier_values': df.loc[outlier_mask, col].tolist(),
                    'count': len(outlier_indices),
                    'severity': 'high' if len(outlier_indices) > len(df) * 0.05 else 'medium'  # More than 5% is high
                })

        return anomalies

    def _generate_overall_recommendations(self, insights: List[PerformanceInsight]) -> List[str]:
        """Generate overall recommendations based on all insights."""
        recommendations = []

        # Group insights by severity
        critical_insights = [i for i in insights if i.severity == 'critical']
        high_insights = [i for i in insights if i.severity == 'high']
        medium_insights = [i for i in insights if i.severity == 'medium']

        if critical_insights:
            recommendations.append(f"CRITICAL: Address {len(critical_insights)} critical performance issues immediately.")

        if high_insights:
            recommendations.append(f"HIGH: Review and address {len(high_insights)} high-severity performance issues.")

        if medium_insights:
            recommendations.append(f"MEDIUM: Monitor and consider optimizing {len(medium_insights)} areas of concern.")

        # Add specific recommendations for top issues
        sorted_insights = sorted(insights, key=lambda x: x.confidence * (-1 if x.current_value > x.baseline_value else 1), reverse=True)
        top_insights = sorted_insights[:3]  # Top 3 insights

        for insight in top_insights:
            if insight.current_value > insight.baseline_value:
                recommendations.append(f"Focus on: {insight.recommendation}")

        return recommendations


class VisualizationGenerator:
    """
    Generates visualizations for performance data including charts, graphs, and dashboards.
    Creates interactive and static visualizations for reporting.
    """

    def __init__(self, output_dir: str = "./performance_visuals"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for visualization generation."""
        logger = logging.getLogger('VisualizationGenerator')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def generate_visualizations(self, raw_data: Dict[str, pd.DataFrame],
                               analysis_results: PerformanceReport) -> Dict[str, str]:
        """Generate various visualizations from the data."""
        viz_paths = {}

        # Generate visualizations for each data source
        for source_id, df in raw_data.items():
            if df.empty:
                continue

            # Generate time series plots for numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                ts_path = self._generate_time_series_plots(df, source_id)
                if ts_path:
                    viz_paths[f'{source_id}_time_series'] = ts_path

            # Generate correlation heatmap if we have enough numeric columns
            if len(numeric_cols) > 1:
                heatmap_path = self._generate_correlation_heatmap(df, source_id)
                if heatmap_path:
                    viz_paths[f'{source_id}_correlation'] = heatmap_path

        # Generate summary dashboard
        dashboard_path = self._generate_summary_dashboard(analysis_results)
        if dashboard_path:
            viz_paths['summary_dashboard'] = dashboard_path

        # Generate trend analysis
        trend_path = self._generate_trend_analysis(raw_data)
        if trend_path:
            viz_paths['trend_analysis'] = trend_path

        return viz_paths

    def _generate_time_series_plots(self, df: pd.DataFrame, source_id: str) -> Optional[str]:
        """Generate time series plots for numeric columns."""
        # Look for a timestamp column
        date_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower() or 'timestamp' in col.lower()]

        if not date_cols:
            # If no timestamp column found, create one based on index
            df_with_time = df.copy()
            df_with_time['index'] = range(len(df_with_time))
            x_col = 'index'
        else:
            x_col = date_cols[0]
            df_with_time = df.sort_values(x_col)

        numeric_cols = df_with_time.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != x_col]  # Exclude the x-axis column

        if len(numeric_cols) == 0:
            return None

        # Create subplot for multiple metrics
        fig, axes = plt.subplots(len(numeric_cols), 1, figsize=(12, 4 * len(numeric_cols)))
        if len(numeric_cols) == 1:
            axes = [axes]

        for i, col in enumerate(numeric_cols):
            axes[i].plot(df_with_time[x_col], df_with_time[col], marker='o', linestyle='-')
            axes[i].set_title(f'{col} Over Time - {source_id}')
            axes[i].set_xlabel(x_col)
            axes[i].set_ylabel(col)
            axes[i].grid(True)

        plt.tight_layout()

        # Save the plot
        file_path = self.output_dir / f'{source_id}_time_series.png'
        plt.savefig(file_path)
        plt.close()

        return str(file_path)

    def _generate_correlation_heatmap(self, df: pd.DataFrame, source_id: str) -> Optional[str]:
        """Generate correlation heatmap for numeric columns."""
        numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.shape[1] < 2:
            return None

        plt.figure(figsize=(10, 8))
        correlation_matrix = numeric_df.corr()
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                    square=True, fmt='.2f')
        plt.title(f'Correlation Heatmap - {source_id}')

        # Save the plot
        file_path = self.output_dir / f'{source_id}_correlation_heatmap.png'
        plt.savefig(file_path)
        plt.close()

        return str(file_path)

    def _generate_summary_dashboard(self, analysis_results: PerformanceReport) -> Optional[str]:
        """Generate a summary dashboard of key insights."""
        if not analysis_results.insights:
            return None

        # Create a figure with multiple subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Performance Severity Distribution', 'Metric Values',
                          'Top Recommendations', 'Anomaly Summary'),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "indicator"}, {"type": "bar"}]]
        )

        # Severity distribution
        severities = [insight.severity for insight in analysis_results.insights]
        severity_counts = pd.Series(severities).value_counts()

        fig.add_trace(
            go.Bar(x=severity_counts.index, y=severity_counts.values, name="Severity Counts"),
            row=1, col=1
        )

        # Metric values
        metric_names = [insight.metric_name for insight in analysis_results.insights]
        current_values = [insight.current_value for insight in analysis_results.insights]

        fig.add_trace(
            go.Scatter(x=metric_names, y=current_values, mode='markers', name="Current Values"),
            row=1, col=2
        )

        # Anomaly summary
        if analysis_results.anomalies:
            anomaly_counts = [anomaly['count'] for anomaly in analysis_results.anomalies[:5]]  # Top 5
            anomaly_columns = [anomaly['column'] for anomaly in analysis_results.anomalies[:5]]

            fig.add_trace(
                go.Bar(x=anomaly_columns, y=anomaly_counts, name="Anomalies"),
                row=2, col=2
            )

        # Overall summary indicator
        total_critical = len([i for i in analysis_results.insights if i.severity == 'critical'])
        total_high = len([i for i in analysis_results.insights if i.severity == 'high'])

        fig.add_trace(
            go.Indicator(
                mode="number+gauge+delta",
                value=max(0, 100 - (total_critical * 25 + total_high * 10)),  # Lower score for more issues
                domain={'row': 2, 'column': 1},
                title={'text': "Health Score"},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkblue"},
                       'steps': [{'range': [0, 25], 'color': "lightgray"},
                                {'range': [25, 50], 'color': "gray"},
                                {'range': [50, 75], 'color': "lightyellow"},
                                {'range': [75, 100], 'color': "lightgreen"}],
                       'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 70}}
            ),
            row=2, col=1
        )

        fig.update_layout(height=800, showlegend=True, title_text="Performance Analysis Dashboard")

        # Save as HTML for interactivity
        file_path = self.output_dir / 'performance_dashboard.html'
        fig.write_html(str(file_path))

        return str(file_path)

    def _generate_trend_analysis(self, raw_data: Dict[str, pd.DataFrame]) -> Optional[str]:
        """Generate trend analysis visualizations."""
        all_trends = []

        for source_id, df in raw_data.items():
            if df.empty:
                continue

            # Look for timestamp column
            date_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower() or 'timestamp' in col.lower()]

            if not date_cols:
                continue

            date_col = date_cols[0]
            df_sorted = df.sort_values(date_col)

            # Analyze numeric columns
            numeric_cols = df_sorted.select_dtypes(include=[np.number]).columns

            for col in numeric_cols:
                if len(df_sorted) >= 4:  # Need at least 4 points for decomposition
                    try:
                        # Prepare data for seasonal decomposition
                        series = df_sorted[col].dropna()
                        if len(series) >= 4:
                            # Resample to daily frequency if needed
                            series.index = pd.to_datetime(df_sorted[date_col]).values

                            # Perform seasonal decomposition
                            decomposition = seasonal_decompose(series, model='additive', period=min(4, len(series)//2))

                            # Create trend plot
                            plt.figure(figsize=(12, 8))
                            plt.subplot(4, 1, 1)
                            plt.plot(decomposition.observed, label='Original')
                            plt.legend()
                            plt.subplot(4, 1, 2)
                            plt.plot(decomposition.trend, label='Trend', color='orange')
                            plt.legend()
                            plt.subplot(4, 1, 3)
                            plt.plot(decomposition.seasonal, label='Seasonal', color='green')
                            plt.legend()
                            plt.subplot(4, 1, 4)
                            plt.plot(decomposition.resid, label='Residual', color='red')
                            plt.legend()

                            plt.suptitle(f'Time Series Decomposition - {source_id} - {col}')
                            plt.tight_layout()

                            # Save the plot
                            file_path = self.output_dir / f'{source_id}_{col}_trend_analysis.png'
                            plt.savefig(file_path)
                            plt.close()

                            all_trends.append(str(file_path))
                    except Exception as e:
                        self.logger.warning(f"Could not perform trend analysis for {source_id}.{col}: {e}")

        if all_trends:
            return all_trends[0]  # Return path to first generated trend analysis
        return None


class PerformanceReporter:
    """
    Generates comprehensive performance reports in various formats including
    PDF, Excel, HTML, and JSON. Provides templates for different audience types.
    """

    def __init__(self, output_dir: str = "./performance_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for report generation."""
        logger = logging.getLogger('PerformanceReporter')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def generate_report(self, analysis_results: PerformanceReport,
                       format_type: str = 'json', filename_prefix: str = 'performance_report') -> str:
        """Generate a performance report in the specified format."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.{format_type}"
        filepath = self.output_dir / filename

        if format_type.lower() == 'json':
            with open(filepath, 'w') as f:
                # Convert the dataclass to dictionary recursively
                report_dict = self._convert_to_serializable(analysis_results)
                json.dump(report_dict, f, indent=2, default=str)
        elif format_type.lower() == 'txt':
            with open(filepath, 'w') as f:
                f.write(self._format_as_text(analysis_results))
        else:
            # Default to JSON if format not recognized
            with open(filepath, 'w') as f:
                report_dict = self._convert_to_serializable(analysis_results)
                json.dump(report_dict, f, indent=2, default=str)

        self.logger.info(f"Performance report generated: {filepath}")
        return str(filepath)

    def _convert_to_serializable(self, obj):
        """Convert dataclass objects to serializable dictionaries."""
        if hasattr(obj, '__dataclass_fields__'):
            # It's a dataclass
            result = {}
            for field_name, field_def in obj.__dataclass_fields__.items():
                field_value = getattr(obj, field_name)
                result[field_name] = self._convert_to_serializable(field_value)
            return result
        elif isinstance(obj, list):
            # It's a list
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            # It's a dict
            return {key: self._convert_to_serializable(value) for key, value in obj.items()}
        else:
            # It's a primitive or datetime
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            elif pd.isna(obj):
                return None
            else:
                return obj

    def _format_as_text(self, analysis_results: PerformanceReport) -> str:
        """Format analysis results as plain text report."""
        text = "PERFORMANCE ANALYSIS REPORT\n"
        text += "=" * 50 + "\n"
        text += f"Generated: {analysis_results.metadata['analysis_timestamp']}\n"
        text += f"Data Sources: {', '.join(analysis_results.metadata['data_sources_analyzed'])}\n"
        text += f"Total Insights: {analysis_results.metadata['total_insights']}\n"
        text += f"Total Anomalies: {analysis_results.metadata['total_anomalies']}\n\n"

        text += "KEY INSIGHTS\n"
        text += "-" * 20 + "\n"

        # Group insights by severity
        for severity in ['critical', 'high', 'medium', 'low']:
            severity_insights = [i for i in analysis_results.insights if i.severity == severity]
            if severity_insights:
                text += f"\n{severity.upper()} SEVERITY:\n"
                for insight in severity_insights[:5]:  # Show top 5 of each severity
                    text += f"  • {insight.metric_name}: {insight.current_value:.2f} "
                    text += f"(trend: {insight.trend}, confidence: {insight.confidence:.2f})\n"
                    text += f"    Recommendation: {insight.recommendation}\n\n"

        text += "\nRECOMMENDATIONS\n"
        text += "-" * 20 + "\n"
        for i, rec in enumerate(analysis_results.recommendations, 1):
            text += f"{i}. {rec}\n"

        if analysis_results.anomalies:
            text += "\nANOMALIES DETECTED\n"
            text += "-" * 20 + "\n"
            for anomaly in analysis_results.anomalies[:10]:  # Show top 10 anomalies
                text += f"  • Column '{anomaly['column']}': {anomaly['count']} anomalies detected "
                text += f"(severity: {anomaly['severity']})\n"

        return text


class AlertManager:
    """
    Manages performance alerts and notifications based on configured thresholds
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
                    configs = config.get('alerts', {}).get('alert_types', [])
            except Exception as e:
                self.logger.error(f"Failed to load alert configs: {e}")

        return configs

    def check_for_alerts(self, analysis_results: PerformanceReport) -> List[Dict[str, Any]]:
        """Check analysis results for conditions that trigger alerts."""
        triggered_alerts = []

        for alert_config in self.alert_configs:
            # Check if any insight matches the alert condition
            for insight in analysis_results.insights:
                should_trigger = self._evaluate_alert_condition(alert_config, insight)

                if should_trigger:
                    alert = {
                        'alert_name': alert_config['name'],
                        'severity': alert_config['severity'],
                        'metric_name': insight.metric_name,
                        'current_value': insight.current_value,
                        'recommendation': insight.recommendation,
                        'timestamp': datetime.now().isoformat()
                    }
                    triggered_alerts.append(alert)

        return triggered_alerts

    def _evaluate_alert_condition(self, alert_config: Dict[str, Any], insight: PerformanceInsight) -> bool:
        """Evaluate if an alert condition is met."""
        condition = alert_config['condition']

        # Simple condition evaluation
        if 'critical_threshold' in condition.lower():
            return insight.severity == 'critical'
        elif 'warning_threshold' in condition.lower():
            return insight.severity in ['critical', 'high']
        elif 'metric_value' in condition.lower():
            # This is a simplified evaluation - in a real system you'd have more sophisticated parsing
            if 'current_value' in condition.lower():
                threshold_match = 'critical_threshold' in condition.lower() or 'warning_threshold' in condition.lower()
                if threshold_match:
                    return insight.severity in ['critical', 'high']

        return False

    def send_alerts(self, alerts: List[Dict[str, Any]]):
        """Send alerts through configured channels."""
        for alert in alerts:
            for method in alert.get('notification_methods', ['log']):
                if method == 'email':
                    self._send_email_alert(alert)
                elif method == 'log':
                    self.logger.warning(f"ALERT: {alert['alert_name']} - {alert['recommendation']}")
                else:
                    self.logger.info(f"Alert method {method} not implemented: {alert}")

    def _send_email_alert(self, alert: Dict[str, Any]):
        """Send alert via email."""
        # This is a placeholder - in a real implementation you'd use smtplib
        self.logger.info(f"Email alert would be sent: {alert}")


class PerformanceAnalyzerEngine:
    """
    Main orchestrator that combines all components to provide end-to-end
    performance analysis capabilities.
    """

    def __init__(self, config_path: str = None, output_dir: str = "./performance_analysis"):
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.data_collector = DataCollector(config_path)
        self.analyzer = PerformanceAnalyzer()
        self.visualizer = VisualizationGenerator(str(self.output_dir / "visuals"))
        self.reporter = PerformanceReporter(str(self.output_dir / "reports"))
        self.alert_manager = AlertManager(config_path)

        self.logger = self._setup_logger()

        # Load thresholds from config
        self.thresholds = self._load_thresholds()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the performance analyzer engine."""
        logger = logging.getLogger('PerformanceAnalyzerEngine')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_thresholds(self) -> List[PerformanceThreshold]:
        """Load performance thresholds from config."""
        thresholds = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                    # Extract thresholds from the config structure
                    threshold_config = config.get('thresholds', {})

                    for category, metrics in threshold_config.items():
                        for metric_name, metric_config in metrics.items():
                            threshold = PerformanceThreshold(
                                metric_name=metric_name,
                                optimal_range=metric_config.get('optimal_range', [0, float('inf')]),
                                warning_threshold=metric_config.get('warning_threshold', float('inf')),
                                critical_threshold=metric_config.get('critical_threshold', float('inf')),
                                weight=metric_config.get('weight', 1.0)
                            )
                            thresholds.append(threshold)
            except Exception as e:
                self.logger.error(f"Failed to load thresholds: {e}")

        return thresholds

    def run_analysis(self, start_date: str = None, end_date: str = None) -> str:
        """Run a complete performance analysis cycle."""
        # Use last week's dates if not provided
        if not start_date or not end_date:
            end_date_obj = datetime.now() - timedelta(days=datetime.now().weekday() + 1)  # Last Sunday
            start_date_obj = end_date_obj - timedelta(days=6)  # Previous Monday
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')

        self.logger.info(f"Starting performance analysis for period: {start_date} to {end_date}")

        # Step 1: Collect data
        raw_data = self.data_collector.collect_data(start_date, end_date)

        if not raw_data:
            self.logger.warning("No data collected, generating empty analysis")
            return self._create_empty_analysis(start_date, end_date)

        # Step 2: Analyze performance
        analysis_results = self.analyzer.analyze_performance(raw_data, self.thresholds)

        # Step 3: Generate visualizations
        viz_paths = self.visualizer.generate_visualizations(raw_data, analysis_results)

        # Step 4: Generate report
        report_path = self.reporter.generate_report(analysis_results)

        # Step 5: Check for alerts
        alerts = self.alert_manager.check_for_alerts(analysis_results)
        if alerts:
            self.logger.info(f"Triggered {len(alerts)} alerts")
            self.alert_manager.send_alerts(alerts)

        # Step 6: Compile results
        results_summary = {
            'analysis_period': {'start': start_date, 'end': end_date},
            'data_sources': list(raw_data.keys()),
            'insights_count': len(analysis_results.insights),
            'anomalies_count': len(analysis_results.anomalies),
            'alerts_count': len(alerts),
            'report_path': report_path,
            'visualization_paths': viz_paths,
            'generated_at': datetime.now().isoformat()
        }

        # Save summary
        summary_path = self.output_dir / "analysis_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(results_summary, f, indent=2, default=str)

        self.logger.info(f"Performance analysis completed. Report saved to: {report_path}")
        return report_path

    def _create_empty_analysis(self, start_date: str, end_date: str) -> str:
        """Create an empty analysis when no data is available."""
        empty_results = PerformanceReport(
            insights=[],
            metrics_summary={},
            trends={},
            anomalies=[],
            recommendations=["No data available for the specified period. Please check data sources."],
            metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'data_sources_analyzed': [],
                'total_insights': 0,
                'total_anomalies': 0
            }
        )

        report_path = self.reporter.generate_report(empty_results, filename_prefix='empty_analysis')
        return report_path

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for the analyzer itself."""
        return {
            'running_since': getattr(self, '_start_time', datetime.now().isoformat()),
            'total_analyses_run': getattr(self, '_analysis_count', 0),
            'average_analysis_time': getattr(self, '_avg_analysis_time', 0),
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'active_threads': threading.active_count()
        }


def schedule_performance_analysis(config_path: str, output_dir: str = "./performance_analysis"):
    """Schedule the performance analysis to run automatically."""
    def job():
        print(f"Running scheduled performance analysis at {datetime.now()}")
        analyzer = PerformanceAnalyzerEngine(config_path, output_dir)
        analyzer.run_analysis()

    # Schedule for daily at 2 AM
    schedule.every().day.at("02:00").do(job)

    print("Performance analysis scheduler started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def main():
    """Main function for testing and demonstration."""
    print("Performance Analyzer")
    print("===================")

    # Initialize the performance analyzer
    config_path = os.getenv('PERFORMANCE_ANALYZER_CONFIG_PATH', './performance_config.json')
    analyzer = PerformanceAnalyzerEngine(config_path)

    print("\nRunning performance analysis...")

    # Run a sample analysis
    report_path = analyzer.run_analysis()

    print(f"Analysis completed successfully!")
    print(f"Report saved to: {report_path}")

    # Display some metrics
    metrics = analyzer.get_performance_metrics()
    print(f"\nSystem Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Demonstrate how to schedule the analyzer
    print(f"\nThe performance analyzer can be scheduled to run automatically.")
    print(f"To schedule daily execution, call: schedule_performance_analysis('{config_path}')")


if __name__ == "__main__":
    main()