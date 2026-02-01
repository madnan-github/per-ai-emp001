#!/usr/bin/env python3
"""
Weekly Business Briefing Generator

This module generates comprehensive CEO-style briefings that summarize key business metrics,
identify bottlenecks, provide strategic insights, and offer actionable recommendations.
The system aggregates data from various business systems and presents it in a standardized,
easy-to-understand format.

Features:
- Automated data collection from multiple sources
- Comprehensive KPI analysis and trend identification
- Customizable briefing templates
- Multiple output formats (PDF, Excel, HTML)
- Automated distribution to stakeholders
- Advanced visualization capabilities
"""

import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from jinja2 import Template
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sqlite3
from contextlib import contextmanager
import threading
import logging
from pathlib import Path
import requests
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import base64


class BriefingSection:
    """Enum for different briefing sections."""
    EXECUTIVE_SUMMARY = "executive_summary"
    FINANCIAL_PERFORMANCE = "financial_performance"
    OPERATIONAL_METRICS = "operational_metrics"
    MARKET_ANALYSIS = "market_analysis"
    RECOMMENDATIONS = "recommendations"


class BriefingTemplate:
    """Enum for different briefing templates."""
    CEO_BRIEFING = "ceo_briefing"
    DEPARTMENT_HEAD = "department_head_briefing"
    BOARD_OF_DIRECTORS = "board_directors_briefing"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    id: str
    name: str
    type: str  # api, database, file, spreadsheet
    connection: Dict[str, Any]
    schedule: Dict[str, Any]
    mapping: Dict[str, Any]
    enabled: bool = True


@dataclass
class BriefingComponent:
    """Definition of a briefing component."""
    name: str
    title: str
    type: str  # metric_grid, time_series_chart, table, text
    data_source: str
    layout: Dict[str, Any]
    metrics: List[Dict[str, Any]]
    visualization_settings: Optional[Dict[str, Any]] = None


@dataclass
class Recipient:
    """Definition of a briefing recipient."""
    id: str
    name: str
    email: str
    template: str
    delivery_method: str  # email, dashboard, file
    delivery_schedule: str  # weekly, daily, monthly
    delivery_day: str
    delivery_time: str
    timezone: str
    department_filter: Optional[str] = None
    attachments: Optional[List[str]] = None


@dataclass
class BriefingData:
    """Container for briefing data."""
    executive_summary: Dict[str, Any]
    financial_performance: Dict[str, Any]
    operational_metrics: Dict[str, Any]
    market_analysis: Dict[str, Any]
    recommendations: Dict[str, Any]
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
                elif source.type in ['file', 'spreadsheet']:
                    data = self._collect_from_file(source, start_date, end_date)
                else:
                    self.logger.warning(f"Unsupported data source type: {source.type}")
                    continue

                if data is not None:
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
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame()

                all_data.append(df)
            except Exception as e:
                self.logger.error(f"API request failed for {endpoint_url}: {e}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()

    def _collect_from_file(self, source: DataSourceConfig, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect data from a file source."""
        file_path = source.connection['file_path']

        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path, sheet_name=source.connection.get('sheet_name', 0))
        else:
            self.logger.error(f"Unsupported file format: {file_path}")
            return pd.DataFrame()

        # Apply date filters if specified
        date_column = source.mapping.get('date_column', 'date')
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
            df = df[mask]

        return df


class DataProcessor:
    """
    Processes collected data to generate metrics, perform analysis, and prepare for visualization.
    Applies transformations, calculates derived metrics, and validates data quality.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for data processing."""
        logger = logging.getLogger('DataProcessor')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def process_data(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Process raw data to generate briefing components."""
        processed_data = {}

        for source_id, df in raw_data.items():
            if df.empty:
                continue

            # Calculate key metrics
            metrics = self._calculate_metrics(df)

            # Perform trend analysis
            trends = self._analyze_trends(df)

            # Identify anomalies
            anomalies = self._detect_anomalies(df)

            processed_data[source_id] = {
                'metrics': metrics,
                'trends': trends,
                'anomalies': anomalies,
                'summary_stats': df.describe().to_dict()
            }

        return processed_data

    def _calculate_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate key performance metrics from the data."""
        metrics = {}

        # Calculate numeric metrics
        numeric_columns = df.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            metrics[f'{col}_mean'] = df[col].mean()
            metrics[f'{col}_median'] = df[col].median()
            metrics[f'{col}_std'] = df[col].std()
            metrics[f'{col}_sum'] = df[col].sum()
            metrics[f'{col}_min'] = df[col].min()
            metrics[f'{col}_max'] = df[col].max()

        # Calculate derived metrics if common columns exist
        if 'revenue' in df.columns and 'expenses' in df.columns:
            metrics['profit'] = (df['revenue'] - df['expenses']).sum()
            metrics['profit_margin'] = ((df['revenue'] - df['expenses']) / df['revenue']).mean()

        if 'quantity' in df.columns and 'price' in df.columns:
            metrics['total_revenue'] = (df['quantity'] * df['price']).sum()

        return metrics

    def _analyze_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trends in the data."""
        trends = {}

        # Look for date column
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        if date_cols:
            date_col = date_cols[0]
            df_sorted = df.sort_values(date_col)

            # Calculate growth rates if numeric columns exist
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if len(df_sorted) > 1:
                    first_val = df_sorted[col].iloc[0]
                    last_val = df_sorted[col].iloc[-1]
                    if first_val != 0:
                        growth_rate = (last_val - first_val) / first_val * 100
                        trends[f'{col}_growth_rate'] = growth_rate

        return trends

    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in the data."""
        anomalies = []

        # Use IQR method for anomaly detection
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outlier_indices = df[(df[col] < lower_bound) | (df[col] > upper_bound)].index
            if len(outlier_indices) > 0:
                anomalies.append({
                    'column': col,
                    'outliers': outlier_indices.tolist(),
                    'count': len(outlier_indices)
                })

        return anomalies

    def generate_kpi_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate KPI summary from processed data."""
        kpi_summary = {
            'total_metrics_calculated': 0,
            'key_insights': [],
            'highlight_metrics': {}
        }

        for source_id, data in processed_data.items():
            metrics = data['metrics']
            trends = data['trends']

            # Add highlight metrics
            for key, value in metrics.items():
                if 'revenue' in key.lower():
                    kpi_summary['highlight_metrics']['total_revenue'] = value
                elif 'profit' in key.lower():
                    kpi_summary['highlight_metrics']['total_profit'] = value
                elif 'margin' in key.lower():
                    kpi_summary['highlight_metrics']['profit_margin'] = value

            # Generate insights from trends
            for key, value in trends.items():
                if abs(value) > 10:  # Significant trend (more than 10%)
                    insight = f"Significant {'increase' if value > 0 else 'decrease'} in {key.replace('_growth_rate', '')}: {value:.2f}%"
                    kpi_summary['key_insights'].append(insight)

            kpi_summary['total_metrics_calculated'] += len(metrics)

        return kpi_summary


class VisualizationGenerator:
    """
    Generates visualizations for the briefing including charts, graphs, and dashboards.
    Supports multiple visualization libraries and export formats.
    """

    def __init__(self):
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

    def generate_charts(self, processed_data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """Generate charts from processed data."""
        chart_paths = {}

        # Set style
        plt.style.use('seaborn-v0_8')

        for source_id, data in processed_data.items():
            metrics = data['metrics']
            trends = data['trends']

            # Generate metric grid visualization
            if metrics:
                chart_path = self._generate_metric_grid(metrics, output_dir, source_id)
                if chart_path:
                    chart_paths[f'{source_id}_metric_grid'] = chart_path

            # Generate trend visualization
            if trends:
                chart_path = self._generate_trend_chart(trends, output_dir, source_id)
                if chart_path:
                    chart_paths[f'{source_id}_trend_chart'] = chart_path

        return chart_paths

    def _generate_metric_grid(self, metrics: Dict[str, float], output_dir: str, source_id: str) -> Optional[str]:
        """Generate a metric grid visualization."""
        # Filter for revenue-related metrics to visualize
        revenue_metrics = {k: v for k, v in metrics.items() if 'revenue' in k.lower() or 'profit' in k.lower()}

        if not revenue_metrics:
            return None

        fig, ax = plt.subplots(figsize=(12, 8))

        # Create a bar chart for revenue metrics
        keys = list(revenue_metrics.keys())[:6]  # Limit to first 6 metrics
        values = [revenue_metrics[k] for k in keys]

        bars = ax.bar(keys, values)
        ax.set_title(f'Revenue & Profit Metrics - {source_id}')
        ax.set_ylabel('Amount ($)')

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'${height:,.0f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom')

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, f'{source_id}_metrics.png')
        plt.savefig(chart_path)
        plt.close()

        return chart_path

    def _generate_trend_chart(self, trends: Dict[str, float], output_dir: str, source_id: str) -> Optional[str]:
        """Generate a trend chart visualization."""
        if not trends:
            return None

        # Prepare data for plotting
        labels = []
        values = []

        for key, value in trends.items():
            if isinstance(value, (int, float)):
                labels.append(key.replace('_growth_rate', ''))
                values.append(value)

        if not labels:
            return None

        fig, ax = plt.subplots(figsize=(12, 8))

        colors = ['green' if v >= 0 else 'red' for v in values]
        bars = ax.bar(labels, values, color=colors)

        ax.set_title(f'Trend Analysis - {source_id}')
        ax.set_ylabel('Growth Rate (%)')

        # Add horizontal line at y=0
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.annotate(f'{value:.2f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3 if height >= 0 else -15),  # Offset based on bar direction
                       textcoords="offset points",
                       ha='center', va='bottom' if height >= 0 else 'top')

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, f'{source_id}_trends.png')
        plt.savefig(chart_path)
        plt.close()

        return chart_path

    def generate_plotly_charts(self, processed_data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """Generate interactive Plotly charts."""
        chart_paths = {}

        for source_id, data in processed_data.items():
            metrics = data['metrics']

            # Generate an interactive scatter plot if we have enough data
            numeric_cols = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}

            if len(numeric_cols) >= 2:
                # Take first two numeric metrics for scatter plot
                items = list(numeric_cols.items())[:2]
                x_label, x_val = items[0]
                y_label, y_val = items[1]

                fig = go.Figure(data=go.Scatter(x=[x_val], y=[y_val], mode='markers',
                                              marker=dict(size=10, color='blue'),
                                              text=[source_id]))
                fig.update_layout(title=f'Interactive Metric Comparison: {x_label} vs {y_label}',
                                xaxis_title=x_label,
                                yaxis_title=y_label)

                chart_path = os.path.join(output_dir, f'{source_id}_interactive.html')
                fig.write_html(chart_path)
                chart_paths[f'{source_id}_interactive'] = chart_path

        return chart_paths


class BriefingGenerator:
    """
    Main class that orchestrates the briefing generation process.
    Combines data collection, processing, visualization, and report generation.
    """

    def __init__(self, config_path: str = None, output_dir: str = "./briefings"):
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.data_collector = DataCollector(config_path)
        self.data_processor = DataProcessor()
        self.visualization_generator = VisualizationGenerator()
        self.logger = self._setup_logger()

        # Load recipients
        self.recipients = self._load_recipients()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the briefing generator."""
        logger = logging.getLogger('BriefingGenerator')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_recipients(self) -> List[Recipient]:
        """Load recipient configurations."""
        recipients = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    for recipient_data in config.get('distribution', {}).get('recipients', []):
                        recipient = Recipient(**recipient_data)
                        recipients.append(recipient)
            except Exception as e:
                self.logger.error(f"Failed to load recipients: {e}")

        return recipients

    def generate_briefing(self, start_date: str = None, end_date: str = None) -> BriefingData:
        """Generate a complete briefing."""
        # Use last week's dates if not provided
        if not start_date or not end_date:
            end_date_obj = datetime.now() - timedelta(days=datetime.now().weekday() + 1)  # Last Sunday
            start_date_obj = end_date_obj - timedelta(days=6)  # Previous Monday
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')

        self.logger.info(f"Generating briefing for period: {start_date} to {end_date}")

        # Collect data
        raw_data = self.data_collector.collect_data(start_date, end_date)

        if not raw_data:
            self.logger.warning("No data collected, generating empty briefing")
            return self._create_empty_briefing(start_date, end_date)

        # Process data
        processed_data = self.data_processor.process_data(raw_data)

        # Generate visualizations
        chart_paths = self.visualization_generator.generate_charts(processed_data, str(self.output_dir))
        plotly_charts = self.visualization_generator.generate_plotly_charts(processed_data, str(self.output_dir))

        # Create briefing sections
        executive_summary = self._generate_executive_summary(processed_data)
        financial_performance = self._generate_financial_section(processed_data)
        operational_metrics = self._generate_operational_section(processed_data)
        market_analysis = self._generate_market_analysis(processed_data)
        recommendations = self._generate_recommendations(processed_data)

        # Compile metadata
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'period_start': start_date,
            'period_end': end_date,
            'data_sources_used': list(raw_data.keys()),
            'charts_generated': list(chart_paths.values()),
            'plotly_charts': list(plotly_charts.values())
        }

        return BriefingData(
            executive_summary=executive_summary,
            financial_performance=financial_performance,
            operational_metrics=operational_metrics,
            market_analysis=market_analysis,
            recommendations=recommendations,
            metadata=metadata
        )

    def _create_empty_briefing(self, start_date: str, end_date: str) -> BriefingData:
        """Create an empty briefing when no data is available."""
        empty_data = {
            'metrics': {},
            'trends': {},
            'anomalies': [],
            'summary_stats': {}
        }

        return BriefingData(
            executive_summary={'message': 'No data available for the specified period'},
            financial_performance={'message': 'No financial data available'},
            operational_metrics={'message': 'No operational data available'},
            market_analysis={'message': 'No market data available'},
            recommendations={'message': 'No recommendations available - insufficient data'},
            metadata={
                'generated_at': datetime.now().isoformat(),
                'period_start': start_date,
                'period_end': end_date,
                'data_sources_used': [],
                'charts_generated': [],
                'plotly_charts': []
            }
        )

    def _generate_executive_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the executive summary section."""
        kpi_summary = self.data_processor.generate_kpi_summary(processed_data)

        # Identify top insights
        all_insights = []
        for source_id, data in processed_data.items():
            trends = data['trends']
            anomalies = data['anomalies']

            # Add trend insights
            for key, value in trends.items():
                if abs(value) > 10:  # Significant trend
                    insight = {
                        'type': 'trend',
                        'description': f"Significant {'increase' if value > 0 else 'decrease'} in {key.replace('_growth_rate', '')}: {value:.2f}%",
                        'severity': 'high' if abs(value) > 20 else 'medium',
                        'source': source_id
                    }
                    all_insights.append(insight)

            # Add anomaly insights
            for anomaly in anomalies:
                insight = {
                    'type': 'anomaly',
                    'description': f"Detected {anomaly['count']} outliers in {anomaly['column']}",
                    'severity': 'high' if anomaly['count'] > 5 else 'medium',
                    'source': source_id
                }
                all_insights.append(insight)

        return {
            'kpi_summary': kpi_summary,
            'top_insights': sorted(all_insights, key=lambda x: x['severity'], reverse=True)[:5],
            'key_metrics': kpi_summary['highlight_metrics'],
            'overall_assessment': 'Positive' if any(i['severity'] == 'high' and 'increase' in i['description'] for i in all_insights) else 'Mixed'
        }

    def _generate_financial_section(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the financial performance section."""
        financial_metrics = {}
        for source_id, data in processed_data.items():
            metrics = data['metrics']
            for key, value in metrics.items():
                if 'revenue' in key.lower() or 'profit' in key.lower() or 'margin' in key.lower():
                    financial_metrics[f"{source_id}_{key}"] = value

        return {
            'revenue_metrics': {k: v for k, v in financial_metrics.items() if 'revenue' in k},
            'profit_metrics': {k: v for k, v in financial_metrics.items() if 'profit' in k},
            'margin_metrics': {k: v for k, v in financial_metrics.items() if 'margin' in k},
            'summary': f"Analyzed financial data from {len(processed_data)} sources"
        }

    def _generate_operational_section(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the operational metrics section."""
        operational_metrics = {}
        for source_id, data in processed_data.items():
            metrics = data['metrics']
            for key, value in metrics.items():
                if any(op_word in key.lower() for op_word in ['efficiency', 'productivity', 'capacity', 'utilization', 'turnover']):
                    operational_metrics[f"{source_id}_{key}"] = value

        return {
            'operational_metrics': operational_metrics,
            'summary': f"Analyzed operational data from {len(processed_data)} sources"
        }

    def _generate_market_analysis(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the market analysis section."""
        # Placeholder for market analysis - would typically integrate with external market data sources
        return {
            'competitor_analysis': 'No competitor data integrated',
            'market_trends': 'No market trend data available',
            'customer_insights': 'No customer insight data available',
            'external_factors': 'No external factor analysis performed'
        }

    def _generate_recommendations(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategic recommendations."""
        recommendations = []

        for source_id, data in processed_data.items():
            metrics = data['metrics']
            trends = data['trends']
            anomalies = data['anomalies']

            # Generate recommendations based on trends
            for key, value in trends.items():
                if value < -10:  # Significant decrease
                    rec = {
                        'type': 'improvement',
                        'title': f'Address Decline in {key.replace("_growth_rate", "").title()}',
                        'description': f'Significant negative trend detected ({value:.2f}%). Investigate root causes.',
                        'priority': 'high',
                        'source': source_id
                    }
                    recommendations.append(rec)
                elif value > 10:  # Significant increase
                    rec = {
                        'type': 'capitalization',
                        'title': f'Continue Positive Trend in {key.replace("_growth_rate", "").title()}',
                        'description': f'Strong positive trend ({value:.2f}%). Consider scaling successful initiatives.',
                        'priority': 'medium',
                        'source': source_id
                    }
                    recommendations.append(rec)

            # Generate recommendations based on anomalies
            for anomaly in anomalies:
                if anomaly['count'] > 5:  # Significant number of outliers
                    rec = {
                        'type': 'investigation',
                        'title': f'Investigate Outliers in {anomaly["column"].title()}',
                        'description': f'Detected {anomaly["count"]} outliers. Review data collection and business processes.',
                        'priority': 'high',
                        'source': source_id
                    }
                    recommendations.append(rec)

        return {
            'strategic_recommendations': recommendations,
            'action_items': [rec for rec in recommendations if rec['priority'] in ['high', 'medium']],
            'opportunities': [rec for rec in recommendations if rec['type'] == 'capitalization'],
            'risks': [rec for rec in recommendations if rec['type'] == 'investigation']
        }

    def export_briefing(self, briefing_data: BriefingData, format_type: str = 'pdf', filename_prefix: str = 'briefing') -> str:
        """Export the briefing in the specified format."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.{format_type}"
        filepath = self.output_dir / filename

        if format_type.lower() == 'json':
            with open(filepath, 'w') as f:
                json.dump(asdict(briefing_data), f, indent=2, default=str)
        elif format_type.lower() == 'txt':
            with open(filepath, 'w') as f:
                f.write(self._format_as_text(briefing_data))
        else:
            # Default to JSON if format not recognized
            with open(filepath, 'w') as f:
                json.dump(asdict(briefing_data), f, indent=2, default=str)

        self.logger.info(f"Briefing exported to: {filepath}")
        return str(filepath)

    def _format_as_text(self, briefing_data: BriefingData) -> str:
        """Format briefing data as plain text."""
        text = f"WEEKLY BUSINESS BRIEFING\n"
        text += f"Generated: {briefing_data.metadata['generated_at']}\n"
        text += f"Period: {briefing_data.metadata['period_start']} to {briefing_data.metadata['period_end']}\n\n"

        text += "EXECUTIVE SUMMARY\n"
        text += "=" * 20 + "\n"
        text += f"Overall Assessment: {briefing_data.executive_summary['overall_assessment']}\n"
        text += f"Key Metrics: {briefing_data.executive_summary['key_metrics']}\n\n"

        text += "FINANCIAL PERFORMANCE\n"
        text += "=" * 20 + "\n"
        text += f"Revenue Metrics: {briefing_data.financial_performance['revenue_metrics']}\n"
        text += f"Profit Metrics: {briefing_data.financial_performance['profit_metrics']}\n\n"

        text += "RECOMMENDATIONS\n"
        text += "=" * 20 + "\n"
        for rec in briefing_data.recommendations['action_items'][:3]:  # Top 3
            text += f"- {rec['title']}: {rec['description']}\n"

        return text

    def distribute_briefing(self, briefing_path: str, recipient_ids: List[str] = None):
        """Distribute the briefing to configured recipients."""
        if not recipient_ids:
            # Send to all configured recipients
            target_recipients = self.recipients
        else:
            # Filter to specific recipients
            target_recipients = [r for r in self.recipients if r.id in recipient_ids]

        for recipient in target_recipients:
            try:
                self._send_briefing_email(briefing_path, recipient)
                self.logger.info(f"Briefing sent to {recipient.email}")
            except Exception as e:
                self.logger.error(f"Failed to send briefing to {recipient.email}: {e}")

    def _send_briefing_email(self, briefing_path: str, recipient: Recipient):
        """Send the briefing via email."""
        smtp_server = os.getenv('BRIEFING_SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('BRIEFING_SMTP_PORT', '587'))
        sender_email = os.getenv('BRIEFING_EMAIL_USER', 'briefings@company.com')
        sender_password = os.getenv(os.getenv('BRIEFING_EMAIL_PASSWORD_ENV_VAR', 'SMTP_PASSWORD'), '')

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient.email
        msg['Subject'] = f"Weekly Business Briefing - {datetime.now().strftime('%B %d, %Y')}"

        body = f"""Dear {recipient.name},

Please find attached the weekly business briefing for the period ending {datetime.now().strftime('%B %d, %Y')}.

This briefing contains:
- Executive summary with key insights
- Financial performance metrics
- Operational metrics and trends
- Strategic recommendations

Please let me know if you have any questions.

Best regards,
Weekly Business Briefing System
"""
        msg.attach(MIMEText(body, 'plain'))

        # Attach the briefing file
        with open(briefing_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f"attachment; filename= {os.path.basename(briefing_path)}"
        )
        msg.attach(part)

        # Send the email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()


def schedule_weekly_briefing(config_path: str, output_dir: str = "./briefings"):
    """Schedule the weekly briefing generation."""
    def job():
        print(f"Running scheduled briefing generation at {datetime.now()}")
        generator = BriefingGenerator(config_path, output_dir)
        briefing_data = generator.generate_briefing()
        filepath = generator.export_briefing(briefing_data)
        generator.distribute_briefing(filepath)

    # Schedule for Sunday at 11 PM UTC (so it's ready for Monday morning)
    schedule.every().sunday.at("23:00").do(job)

    print("Weekly briefing scheduler started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def main():
    """Main function for testing and demonstration."""
    print("Weekly Business Briefing Generator")
    print("==================================")

    # Initialize the briefing generator
    config_path = os.getenv('BRIEFING_CONFIG_PATH', './briefing_config.json')
    generator = BriefingGenerator(config_path)

    print("\nGenerating weekly briefing...")

    # Generate a briefing for the last week
    briefing_data = generator.generate_briefing()

    print(f"Briefing generated successfully!")
    print(f"Period: {briefing_data.metadata['period_start']} to {briefing_data.metadata['period_end']}")
    print(f"Data sources used: {len(briefing_data.metadata['data_sources_used'])}")

    print(f"\nExecutive Summary:")
    print(f"  Overall Assessment: {briefing_data.executive_summary['overall_assessment']}")
    print(f"  Top Insights: {len(briefing_data.executive_summary['top_insights'])}")
    print(f"  Key Metrics: {briefing_data.executive_summary['key_metrics']}")

    print(f"\nFinancial Performance:")
    print(f"  Revenue Metrics Found: {len(briefing_data.financial_performance['revenue_metrics'])}")
    print(f"  Profit Metrics Found: {len(briefing_data.financial_performance['profit_metrics'])}")

    print(f"\nRecommendations:")
    print(f"  Total Recommendations: {len(briefing_data.recommendations['strategic_recommendations'])}")
    print(f"  Action Items: {len(briefing_data.recommendations['action_items'])}")

    # Export the briefing
    filepath = generator.export_briefing(briefing_data, 'json', 'weekly_briefing')
    print(f"\nBriefing exported to: {filepath}")

    # Demonstrate how to schedule the briefing
    print(f"\nThe briefing generator can be scheduled to run automatically.")
    print(f"To schedule weekly execution, call: schedule_weekly_briefing('{config_path}')")


if __name__ == "__main__":
    main()