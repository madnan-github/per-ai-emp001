#!/usr/bin/env python3
"""
Dashboard Updater

This module maintains real-time dashboards with key metrics, ensuring stakeholders
have access to the most current business intelligence. The system automatically
refreshes data from various sources, updates visualizations, and provides alerts
when significant changes occur in key performance indicators.

Features:
- Real-time dashboard updates via WebSocket
- Scheduled data refresh from multiple sources
- Dynamic widget configuration and layout management
- Alert system for critical metric changes
- Responsive design for multiple device types
- Comprehensive security and access controls
"""

import json
import os
import sys
import asyncio
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import requests
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import redis
from redis import Redis
import schedule
import time
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
from functools import wraps
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import plotly.graph_objs as go
import plotly.utils
import secrets


class DashboardWidgetType:
    """Enum for different dashboard widget types."""
    CHART = "chart"
    METRIC = "metric"
    TABLE = "table"
    TEXT = "text"
    GAUGE = "gauge"
    PROGRESS = "progress"


class UpdateFrequency:
    """Enum for update frequency options."""
    REALTIME = "realtime"
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    id: str
    name: str
    type: str  # api, database, file, streaming
    connection: Dict[str, Any]
    schedule: Dict[str, Any]
    mapping: Dict[str, Any]
    enabled: bool = True


@dataclass
class DashboardWidget:
    """Configuration for a dashboard widget."""
    id: str
    type: DashboardWidgetType
    title: str
    position: Dict[str, int]  # x, y, w, h coordinates
    data_source: str
    refresh_interval: int  # seconds
    configuration: Dict[str, Any]


@dataclass
class DashboardConfig:
    """Configuration for a dashboard."""
    id: str
    name: str
    description: str
    layout: Dict[str, Any]
    widgets: List[DashboardWidget]
    permissions: Dict[str, List[str]]
    enabled: bool = True


@dataclass
class AlertConfig:
    """Configuration for an alert."""
    id: str
    name: str
    description: str
    data_source: str
    field: str
    operator: str  # gt, lt, eq, neq, gte, lte
    threshold: float
    severity: str  # low, medium, high, critical
    recipients: List[str]
    notification_methods: List[str]


@dataclass
class DashboardData:
    """Container for dashboard data."""
    dashboard_id: str
    widget_data: Dict[str, Any]
    last_updated: str
    status: str  # success, error, partial


class DataCollector:
    """
    Handles data collection from various sources including databases, APIs, and files.
    Supports multiple data formats and provides data validation capabilities.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.sources = self._load_data_sources()
        self.logger = self._setup_logger()
        self.redis_client = self._setup_redis()

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

    def _setup_redis(self) -> Redis:
        """Setup Redis connection for caching."""
        redis_url = os.getenv('DASHBOARD_REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)

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

    def collect_data(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Collect data from a specific source."""
        source = next((s for s in self.sources if s.id == source_id), None)
        if not source:
            self.logger.error(f"Data source not found: {source_id}")
            return None

        try:
            if source.type == 'database':
                data = self._collect_from_database(source)
            elif source.type == 'api':
                data = self._collect_from_api(source)
            elif source.type in ['file', 'csv']:
                data = self._collect_from_file(source)
            else:
                self.logger.warning(f"Unsupported data source type: {source.type}")
                return None

            # Cache the data
            cache_key = f"dashboard:data:{source.id}"
            self.redis_client.setex(cache_key, 300, json.dumps(data))  # Cache for 5 minutes

            return data
        except Exception as e:
            self.logger.error(f"Error collecting data from {source.name}: {e}")
            return None

    def _collect_from_database(self, source: DataSourceConfig) -> Dict[str, Any]:
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
        all_data = {}
        for query_config in source.connection.get('queries', []):
            sql = query_config['sql']

            # Replace date placeholders
            now = datetime.now()
            start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
            sql = sql.replace(':start_date', f"'{start_date}'")

            df = pd.read_sql(sql, engine)

            # Apply field mapping if specified
            field_mapping = query_config.get('field_mapping', {})
            for source_col, target_col in field_mapping.items():
                if source_col in df.columns:
                    df.rename(columns={source_col: target_col}, inplace=True)

            all_data[query_config['name']] = df.to_dict('records')

        return all_data

    def _collect_from_api(self, source: DataSourceConfig) -> Dict[str, Any]:
        """Collect data from an API source."""
        url = source.connection['url']
        headers = source.connection.get('headers', {})

        # Replace placeholders in headers
        api_key = os.getenv(source.connection.get('api_key_env_var', ''))
        if '{{api_key}}' in str(headers):
            headers = {k: v.replace('{{api_key}}', api_key) for k, v in headers.items()}

        all_data = {}
        for endpoint_config in source.connection.get('endpoints', []):
            endpoint_url = f"{url}{endpoint_config['endpoint']}"
            params = endpoint_config.get('params', {})

            try:
                response = requests.get(endpoint_url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Apply response mapping if specified
                response_mapping = endpoint_config.get('response_mapping', {})
                data_path = response_mapping.get('data_path', '$.')

                # Simplified path extraction (in real implementation, use jsonpath-ng)
                if data_path == '$.opportunities':
                    if isinstance(data, dict) and 'opportunities' in data:
                        data = data['opportunities']
                    elif isinstance(data, list):
                        # Assume it's already the opportunities list
                        pass

                all_data[endpoint_config['endpoint'].strip('/')] = data
            except Exception as e:
                self.logger.error(f"API request failed for {endpoint_url}: {e}")

        return all_data

    def _collect_from_file(self, source: DataSourceConfig) -> Dict[str, Any]:
        """Collect data from file sources."""
        file_path = source.connection['file_path']

        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            self.logger.error(f"Unsupported file format: {file_path}")
            return {}

        # Apply date filters if specified
        date_column = source.connection.get('date_column', 'date')
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            # Filter to last 30 days
            cutoff = datetime.now() - timedelta(days=30)
            df = df[df[date_column] >= cutoff]

        return {"file_data": df.to_dict('records')}

    def get_cached_data(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a source."""
        cache_key = f"dashboard:data:{source_id}"
        cached_data = self.redis_client.get(cache_key)

        if cached_data:
            try:
                return json.loads(cached_data.decode('utf-8'))
            except:
                return None

        return None


class DashboardRenderer:
    """
    Renders dashboard widgets with appropriate visualizations based on data.
    Supports multiple chart types and responsive layouts.
    """

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for dashboard rendering."""
        logger = logging.getLogger('DashboardRenderer')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def render_widget(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render a specific widget with its data."""
        try:
            if widget.type == DashboardWidgetType.CHART:
                return self._render_chart(widget, data)
            elif widget.type == DashboardWidgetType.METRIC:
                return self._render_metric(widget, data)
            elif widget.type == DashboardWidgetType.TABLE:
                return self._render_table(widget, data)
            elif widget.type == DashboardWidgetType.TEXT:
                return self._render_text(widget, data)
            elif widget.type == DashboardWidgetType.GAUGE:
                return self._render_gauge(widget, data)
            elif widget.type == DashboardWidgetType.PROGRESS:
                return self._render_progress(widget, data)
            else:
                self.logger.warning(f"Unsupported widget type: {widget.type}")
                return {"error": f"Unsupported widget type: {widget.type}"}
        except Exception as e:
            self.logger.error(f"Error rendering widget {widget.id}: {e}")
            return {"error": str(e)}

    def _render_chart(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render chart widgets."""
        # Extract chart configuration
        chart_type = widget.configuration.get('chart_type', 'line')
        x_axis = widget.configuration.get('x_axis', 'date')
        y_axis = widget.configuration.get('y_axis', 'value')
        title = widget.configuration.get('title', widget.title)

        # Prepare data for chart
        if not data:
            return {"chart_data": None, "message": "No data available"}

        # Convert data to appropriate format
        x_values = []
        y_values = []

        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict):
                if x_axis in item and y_axis in item:
                    x_values.append(item[x_axis])
                    y_values.append(item[y_axis])

        if not x_values or not y_values:
            return {"chart_data": None, "message": "No valid data points found"}

        # Create chart based on type
        if chart_type == 'line':
            trace = go.Scatter(x=x_values, y=y_values, mode='lines+markers', name=title)
        elif chart_type == 'bar':
            trace = go.Bar(x=x_values, y=y_values, name=title)
        elif chart_type == 'pie':
            trace = go.Pie(labels=x_values, values=y_values, name=title)
        elif chart_type == 'area':
            trace = go.Scatter(x=x_values, y=y_values, fill='tonexty', name=title)
        else:
            trace = go.Scatter(x=x_values, y=y_values, mode='lines+markers', name=title)

        layout = go.Layout(
            title=title,
            xaxis={'title': x_axis.replace('_', ' ').title()},
            yaxis={'title': y_axis.replace('_', ' ').title()},
            showlegend=False
        )

        fig = go.Figure(data=[trace], layout=layout)

        # Convert to JSON for frontend
        chart_json = json.loads(plotly.utils.to_json(fig))

        return {
            "widget_type": "chart",
            "chart_data": chart_json,
            "title": title
        }

    def _render_metric(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render metric widgets."""
        metric_type = widget.configuration.get('metric_type', 'counter')
        format_type = widget.configuration.get('format', 'number')

        # Extract value from data
        value = None
        if isinstance(data, list) and data:
            value = data[0] if isinstance(data[0], (int, float)) else data[0].get('value', 0)
        elif isinstance(data, dict):
            value = data.get('value', 0)
        elif isinstance(data, (int, float)):
            value = data

        if value is None:
            value = 0

        # Format the value based on format_type
        if format_type == 'currency':
            formatted_value = f"${value:,.2f}"
        elif format_type == 'percentage':
            formatted_value = f"{value:.2%}"
        elif format_type == 'time':
            formatted_value = str(timedelta(seconds=value))
        else:
            formatted_value = f"{value:,}" if isinstance(value, int) else f"{value:.2f}"

        # Determine status based on thresholds
        status = "normal"
        thresholds = widget.configuration.get('thresholds', {})
        if value > thresholds.get('critical', float('inf')):
            status = "critical"
        elif value > thresholds.get('warning', float('inf')):
            status = "warning"

        return {
            "widget_type": "metric",
            "value": value,
            "formatted_value": formatted_value,
            "status": status,
            "title": widget.title,
            "metric_type": metric_type
        }

    def _render_table(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render table widgets."""
        if not data:
            return {"widget_type": "table", "rows": [], "columns": [], "message": "No data available"}

        # Convert data to table format
        rows = []
        columns = []

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                # Extract columns from first row
                columns = list(data[0].keys())
                rows = [list(row.values()) for row in data]
            else:
                # Single dimension data
                columns = ["Value"]
                rows = [[item] for item in data]
        elif isinstance(data, dict):
            columns = list(data.keys())
            rows = [list(data.values())]

        return {
            "widget_type": "table",
            "rows": rows,
            "columns": columns,
            "title": widget.title
        }

    def _render_text(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render text widgets."""
        content = widget.configuration.get('content', '')

        # If data is provided, try to inject it into the content
        if data and isinstance(data, dict):
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                content = content.replace(placeholder, str(value))

        return {
            "widget_type": "text",
            "content": content,
            "title": widget.title
        }

    def _render_gauge(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render gauge widgets."""
        value = 0
        if isinstance(data, list) and data:
            value = data[0] if isinstance(data[0], (int, float)) else data[0].get('value', 0)
        elif isinstance(data, dict):
            value = data.get('value', 0)
        elif isinstance(data, (int, float)):
            value = data

        # Determine gauge range
        min_val = widget.configuration.get('min', 0)
        max_val = widget.configuration.get('max', 100)
        value = max(min_val, min(max_val, value))  # Clamp value to range

        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': widget.title},
            gauge={
                'axis': {'range': [min_val, max_val]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [min_val, max_val * 0.3], 'color': "lightgray"},
                    {'range': [max_val * 0.3, max_val * 0.7], 'color': "gray"},
                    {'range': [max_val * 0.7, max_val], 'color': "lightgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': max_val * 0.8
                }
            }
        ))

        chart_json = json.loads(plotly.utils.to_json(fig))

        return {
            "widget_type": "gauge",
            "chart_data": chart_json,
            "value": value,
            "title": widget.title
        }

    def _render_progress(self, widget: DashboardWidget, data: Dict[str, Any]) -> Dict[str, Any]:
        """Render progress widgets."""
        value = 0
        if isinstance(data, list) and data:
            value = data[0] if isinstance(data[0], (int, float)) else data[0].get('value', 0)
        elif isinstance(data, dict):
            value = data.get('value', 0)
        elif isinstance(data, (int, float)):
            value = data

        # Clamp value to 0-100 range
        value = max(0, min(100, value))

        return {
            "widget_type": "progress",
            "value": value,
            "title": widget.title
        }


class AlertManager:
    """
    Manages dashboard alerts and notifications based on configured thresholds
    and business rules. Sends notifications through various channels.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.alerts = self._load_alert_configs()
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

    def _load_alert_configs(self) -> List[AlertConfig]:
        """Load alert configurations."""
        alerts = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    for alert_data in config.get('alerts', {}).get('threshold_alerts', []):
                        alert = AlertConfig(**alert_data)
                        alerts.append(alert)
            except Exception as e:
                self.logger.error(f"Failed to load alert configs: {e}")

        return alerts

    def check_for_alerts(self, dashboard_data: DashboardData) -> List[Dict[str, Any]]:
        """Check dashboard data for conditions that trigger alerts."""
        triggered_alerts = []

        for alert in self.alerts:
            # Get data for the alert's data source
            source_data = dashboard_data.widget_data.get(alert.data_source)

            if source_data:
                # Extract the field value
                field_value = self._extract_field_value(source_data, alert.field)

                if field_value is not None:
                    # Check if condition is met
                    if self._evaluate_condition(field_value, alert.operator, alert.threshold):
                        triggered_alert = {
                            "alert_id": alert.id,
                            "name": alert.name,
                            "severity": alert.severity,
                            "message": f"{alert.name}: {alert.field} is {field_value} (threshold: {alert.threshold})",
                            "timestamp": datetime.now().isoformat(),
                            "recipients": alert.recipients,
                            "notification_methods": alert.notification_methods
                        }
                        triggered_alerts.append(triggered_alert)

        return triggered_alerts

    def _extract_field_value(self, data: Any, field: str) -> Optional[float]:
        """Extract a field value from data."""
        if isinstance(data, list) and data:
            if isinstance(data[0], dict):
                return data[0].get(field)
            else:
                return data[0] if isinstance(data[0]) else None
        elif isinstance(data, dict):
            return data.get(field)
        elif isinstance(data, (int, float)):
            return data
        return None

    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate if a condition is met."""
        if operator == 'gt':
            return value > threshold
        elif operator == 'lt':
            return value < threshold
        elif operator == 'eq':
            return value == threshold
        elif operator == 'neq':
            return value != threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'lte':
            return value <= threshold
        else:
            return False

    def send_alerts(self, alerts: List[Dict[str, Any]]):
        """Send alerts through configured channels."""
        for alert in alerts:
            for method in alert.get('notification_methods', []):
                if method == 'email':
                    self._send_email_alert(alert)
                elif method == 'dashboard_banner':
                    self._send_dashboard_alert(alert)
                else:
                    self.logger.info(f"Alert method {method} not implemented: {alert}")

    def _send_email_alert(self, alert: Dict[str, Any]):
        """Send alert via email."""
        # This would integrate with an email service in a real implementation
        self.logger.info(f"Email alert would be sent: {alert}")

    def _send_dashboard_alert(self, alert: Dict[str, Any]):
        """Send alert to dashboard users."""
        # This would emit a WebSocket event in a real implementation
        self.logger.info(f"Dashboard alert would be shown: {alert}")


class DashboardUpdater:
    """
    Main orchestrator that manages dashboard updates, handles real-time
    communication, and coordinates with other components.
    """

    def __init__(self, config_path: str = None, host: str = '0.0.0.0', port: int = 5000):
        self.config_path = config_path
        self.host = host
        self.port = port

        self.data_collector = DataCollector(config_path)
        self.renderer = DashboardRenderer()
        self.alert_manager = AlertManager(config_path)

        self.logger = self._setup_logger()
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Load dashboard configurations
        self.dashboards = self._load_dashboard_configs()

        # Initialize Flask app and SocketIO
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.getenv('DASHBOARD_SECRET_KEY', 'dev-key-change-in-production')
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            ping_interval=25,
            ping_timeout=60
        )

        self._setup_routes()
        self._setup_socket_handlers()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the dashboard updater."""
        logger = logging.getLogger('DashboardUpdater')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_dashboard_configs(self) -> Dict[str, DashboardConfig]:
        """Load dashboard configurations."""
        dashboards = {}
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                    for dashboard_data in config.get('dashboards', []):
                        widgets = []
                        for widget_data in dashboard_data.get('layout', {}).get('widgets', []):
                            widget = DashboardWidget(
                                id=widget_data['id'],
                                type=widget_data['type'],
                                title=widget_data['title'],
                                position=widget_data['position'],
                                data_source=widget_data['data_source'],
                                refresh_interval=widget_data.get('refresh_interval', 300),
                                configuration=widget_data.get('configuration', {})
                            )
                            widgets.append(widget)

                        dashboard = DashboardConfig(
                            id=dashboard_data['id'],
                            name=dashboard_data['name'],
                            description=dashboard_data['description'],
                            layout=dashboard_data['layout'],
                            widgets=widgets,
                            permissions=dashboard_data.get('permissions', {}),
                            enabled=dashboard_data.get('enabled', True)
                        )

                        if dashboard.enabled:
                            dashboards[dashboard.id] = dashboard
            except Exception as e:
                self.logger.error(f"Failed to load dashboard configs: {e}")

        return dashboards

    def _setup_routes(self):
        """Setup Flask routes."""
        @self.app.route('/')
        def index():
            return render_template('dashboard.html', dashboards=list(self.dashboards.values()))

        @self.app.route('/dashboard/<dashboard_id>')
        def dashboard(dashboard_id):
            if dashboard_id not in self.dashboards:
                return "Dashboard not found", 404

            dashboard_config = self.dashboards[dashboard_id]
            return render_template('dashboard.html', dashboard=dashboard_config)

        @self.app.route('/api/dashboard/<dashboard_id>/data')
        def get_dashboard_data(dashboard_id):
            if dashboard_id not in self.dashboards:
                return jsonify({"error": "Dashboard not found"}), 404

            dashboard_config = self.dashboards[dashboard_id]
            data = self._get_dashboard_data(dashboard_config)

            return jsonify(asdict(data))

    def _setup_socket_handlers(self):
        """Setup SocketIO event handlers."""
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info(f"Client connected: {request.sid}")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info(f"Client disconnected: {request.sid}")

        @self.socketio.on('request_dashboard_data')
        def handle_dashboard_request(data):
            dashboard_id = data.get('dashboard_id')

            if dashboard_id not in self.dashboards:
                emit('dashboard_error', {'error': 'Dashboard not found'})
                return

            dashboard_config = self.dashboards[dashboard_id]
            dashboard_data = self._get_dashboard_data(dashboard_config)

            emit('dashboard_update', {
                'dashboard_id': dashboard_id,
                'data': dashboard_data.widget_data,
                'last_updated': dashboard_data.last_updated,
                'status': dashboard_data.status
            })

    def _get_dashboard_data(self, dashboard_config: DashboardConfig) -> DashboardData:
        """Get data for a specific dashboard."""
        widget_data = {}
        errors = []

        for widget in dashboard_config.widgets:
            # Get data from collector
            data = self.data_collector.collect_data(widget.data_source)

            if data is not None:
                # Render the widget with its data
                rendered_widget = self.renderer.render_widget(widget, data)
                widget_data[widget.id] = rendered_widget
            else:
                error_msg = f"Failed to get data for widget {widget.id} from source {widget.data_source}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        # Check for alerts
        dashboard_data_obj = DashboardData(
            dashboard_id=dashboard_config.id,
            widget_data=widget_data,
            last_updated=datetime.now().isoformat(),
            status="error" if errors else "success"
        )

        alerts = self.alert_manager.check_for_alerts(dashboard_data_obj)
        if alerts:
            self.alert_manager.send_alerts(alerts)
            # Add alerts to the dashboard data
            widget_data['alerts'] = alerts

        return dashboard_data_obj

    def _scheduled_update(self, dashboard_id: str):
        """Perform a scheduled update for a dashboard."""
        if dashboard_id not in self.dashboards:
            return

        dashboard_config = self.dashboards[dashboard_id]
        dashboard_data = self._get_dashboard_data(dashboard_config)

        # Broadcast update to all connected clients
        self.socketio.emit('dashboard_update', {
            'dashboard_id': dashboard_id,
            'data': dashboard_data.widget_data,
            'last_updated': dashboard_data.last_updated,
            'status': dashboard_data.status
        })

        self.logger.info(f"Scheduled update completed for dashboard: {dashboard_id}")

    def schedule_dashboard_updates(self):
        """Schedule dashboard updates based on widget refresh intervals."""
        for dashboard_id, dashboard_config in self.dashboards.items():
            # Find the minimum refresh interval for this dashboard
            min_interval = min([w.refresh_interval for w in dashboard_config.widgets], default=300)

            # Schedule updates using the minimum interval
            schedule.every(min_interval).seconds.do(
                lambda d_id=dashboard_id: self._scheduled_update(d_id)
            )

        self.logger.info(f"Scheduled updates for {len(self.dashboards)} dashboards")

    def run_scheduler(self):
        """Run the scheduler in a separate thread."""
        def run_continuously():
            while True:
                schedule.run_pending()
                time.sleep(1)

        scheduler_thread = threading.Thread(target=run_continuously, daemon=True)
        scheduler_thread.start()

    def run(self, debug: bool = False):
        """Start the dashboard server."""
        # Schedule dashboard updates
        self.schedule_dashboard_updates()

        # Start scheduler
        self.run_scheduler()

        self.logger.info(f"Starting dashboard server on {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)


def main():
    """Main function for running the dashboard updater."""
    print("Dashboard Updater")
    print("=================")

    # Initialize the dashboard updater
    config_path = os.getenv('DASHBOARD_CONFIG_PATH', './dashboard_config.json')

    # Check if running with --serve flag
    serve_mode = '--serve' in sys.argv

    dashboard_updater = DashboardUpdater(config_path)

    if serve_mode:
        print("Starting dashboard server...")
        dashboard_updater.run(debug=True)
    else:
        print("Dashboard updater initialized. Use --serve to start the server.")
        print("Example: python dashboard_updater.py --serve")


if __name__ == "__main__":
    main()