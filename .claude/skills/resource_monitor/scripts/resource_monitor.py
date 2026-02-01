#!/usr/bin/env python3
"""
Resource Monitor

This module provides continuous monitoring and management of system resources for the Personal AI Employee system.
It tracks CPU, memory, disk, network, and other resource utilization, provides alerts when thresholds are exceeded,
and enables proactive resource management to maintain system performance and availability.

Features:
- Real-time resource monitoring
- Threshold-based alerting
- Historical metric storage
- Performance trend analysis
- Resource optimization recommendations
- Alert correlation and noise reduction
"""

import json
import os
import sqlite3
import logging
import threading
import time
import psutil
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import socket
import ssl


class ResourceType(Enum):
    """Types of resources that can be monitored."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    TEMPERATURE = "temperature"


class AlertSeverity(Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Data class to hold metric values."""
    timestamp: str
    resource_type: ResourceType
    resource_id: str
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str]


@dataclass
class AlertInfo:
    """Data class to hold alert information."""
    id: str
    resource_type: ResourceType
    resource_id: str
    metric_name: str
    threshold_value: float
    current_value: float
    severity: AlertSeverity
    message: str
    timestamp: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None


class MetricsDatabase:
    """Manages the metrics database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    threshold_value REAL NOT NULL,
                    current_value REAL NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_by TEXT,
                    acknowledged_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS resource_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def store_metric(self, metric: MetricValue):
        """Store a metric value in the database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO metrics
                (timestamp, resource_type, resource_id, metric_name, value, unit, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.timestamp, metric.resource_type.value, metric.resource_id,
                metric.metric_name, metric.value, metric.unit, json.dumps(metric.tags)
            ))

    def store_alert(self, alert: AlertInfo):
        """Store an alert in the database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO alerts
                (id, resource_type, resource_id, metric_name, threshold_value,
                 current_value, severity, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id, alert.resource_type.value, alert.resource_id,
                alert.metric_name, alert.threshold_value, alert.current_value,
                alert.severity.value, alert.message, alert.timestamp
            ))

    def get_recent_metrics(self, resource_type: ResourceType, metric_name: str, hours: int = 1) -> List[MetricValue]:
        """Get recent metrics for a specific resource and metric."""
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT timestamp, resource_type, resource_id, metric_name, value, unit, tags
                FROM metrics
                WHERE resource_type = ? AND metric_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (resource_type.value, metric_name, start_time))

            metrics = []
            for row in cursor.fetchall():
                metrics.append(MetricValue(
                    timestamp=row[0],
                    resource_type=ResourceType(row[1]),
                    resource_id=row[2],
                    metric_name=row[3],
                    value=row[4],
                    unit=row[5],
                    tags=json.loads(row[6]) if row[6] else {}
                ))
            return metrics

    def get_active_alerts(self) -> List[AlertInfo]:
        """Get all active (non-acknowledged) alerts."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, resource_type, resource_id, metric_name, threshold_value,
                       current_value, severity, message, timestamp, acknowledged,
                       acknowledged_by, acknowledged_at
                FROM alerts
                WHERE acknowledged = FALSE
                ORDER BY timestamp DESC
            ''')

            alerts = []
            for row in cursor.fetchall():
                alerts.append(AlertInfo(
                    id=row[0],
                    resource_type=ResourceType(row[1]),
                    resource_id=row[2],
                    metric_name=row[3],
                    threshold_value=row[4],
                    current_value=row[5],
                    severity=AlertSeverity(row[6]),
                    message=row[7],
                    timestamp=row[8],
                    acknowledged=bool(row[9]),
                    acknowledged_by=row[10],
                    acknowledged_at=row[11]
                ))
            return alerts


class ResourceCollector:
    """Collects resource metrics from the system."""

    def __init__(self):
        self.logger = logging.getLogger('ResourceCollector')

    def collect_cpu_metrics(self) -> List[MetricValue]:
        """Collect CPU-related metrics."""
        metrics = []
        timestamp = datetime.now().isoformat()

        # Overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(MetricValue(
            timestamp=timestamp,
            resource_type=ResourceType.CPU,
            resource_id="overall",
            metric_name="usage_percent",
            value=cpu_percent,
            unit="%",
            tags={"type": "overall"}
        ))

        # Per-core CPU usage
        per_core_percent = psutil.cpu_percent(percpu=True, interval=1)
        for i, percent in enumerate(per_core_percent):
            metrics.append(MetricValue(
                timestamp=timestamp,
                resource_type=ResourceType.CPU,
                resource_id=f"core_{i}",
                metric_name="usage_percent",
                value=percent,
                unit="%",
                tags={"type": "core", "core_id": str(i)}
            ))

        # CPU load averages
        load_avg = psutil.getloadavg()
        for i, avg in enumerate(load_avg):
            period = ["1min", "5min", "15min"][i]
            metrics.append(MetricValue(
                timestamp=timestamp,
                resource_type=ResourceType.CPU,
                resource_id="load_average",
                metric_name=f"load_avg_{period}",
                value=avg,
                unit="",
                tags={"period": period}
            ))

        return metrics

    def collect_memory_metrics(self) -> List[MetricValue]:
        """Collect memory-related metrics."""
        metrics = []
        timestamp = datetime.now().isoformat()

        memory_info = psutil.virtual_memory()

        metrics.append(MetricValue(
            timestamp=timestamp,
            resource_type=ResourceType.MEMORY,
            resource_id="virtual",
            metric_name="usage_percent",
            value=memory_info.percent,
            unit="%",
            tags={"type": "virtual"}
        ))

        metrics.append(MetricValue(
            timestamp=timestamp,
            resource_type=ResourceType.MEMORY,
            resource_id="virtual",
            metric_name="available_mb",
            value=memory_info.available / (1024 * 1024),
            unit="MB",
            tags={"type": "available"}
        ))

        metrics.append(MetricValue(
            timestamp=timestamp,
            resource_type=ResourceType.MEMORY,
            resource_id="virtual",
            metric_name="used_mb",
            value=memory_info.used / (1024 * 1024),
            unit="MB",
            tags={"type": "used"}
        ))

        # Swap memory if available
        swap_info = psutil.swap_memory()
        if swap_info.total > 0:
            metrics.append(MetricValue(
                timestamp=timestamp,
                resource_type=ResourceType.MEMORY,
                resource_id="swap",
                metric_name="usage_percent",
                value=swap_info.percent,
                unit="%",
                tags={"type": "swap"}
            ))

        return metrics

    def collect_disk_metrics(self, paths: List[str] = None) -> List[MetricValue]:
        """Collect disk-related metrics."""
        if paths is None:
            paths = ["/"]

        metrics = []
        timestamp = datetime.now().isoformat()

        for path in paths:
            try:
                disk_usage = psutil.disk_usage(path)

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.DISK,
                    resource_id=path,
                    metric_name="usage_percent",
                    value=disk_usage.percent,
                    unit="%",
                    tags={"path": path, "type": "usage"}
                ))

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.DISK,
                    resource_id=path,
                    metric_name="free_gb",
                    value=disk_usage.free / (1024**3),
                    unit="GB",
                    tags={"path": path, "type": "free_space"}
                ))

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.DISK,
                    resource_id=path,
                    metric_name="total_gb",
                    value=disk_usage.total / (1024**3),
                    unit="GB",
                    tags={"path": path, "type": "total_space"}
                ))
            except Exception as e:
                self.logger.warning(f"Could not collect disk metrics for {path}: {e}")

        # Disk I/O stats
        disk_io = psutil.disk_io_counters()
        if disk_io:
            metrics.append(MetricValue(
                timestamp=timestamp,
                resource_type=ResourceType.DISK,
                resource_id="io",
                metric_name="read_bytes_per_sec",
                value=disk_io.read_bytes,
                unit="bytes",
                tags={"type": "read", "interval": "cumulative"}
            ))

            metrics.append(MetricValue(
                timestamp=timestamp,
                resource_type=ResourceType.DISK,
                resource_id="io",
                metric_name="write_bytes_per_sec",
                value=disk_io.write_bytes,
                unit="bytes",
                tags={"type": "write", "interval": "cumulative"}
            ))

        return metrics

    def collect_network_metrics(self, interfaces: List[str] = None) -> List[MetricValue]:
        """Collect network-related metrics."""
        if interfaces is None:
            interfaces = psutil.net_if_addrs().keys()

        metrics = []
        timestamp = datetime.now().isoformat()

        net_io = psutil.net_io_counters(pernic=True)

        for interface in interfaces:
            if interface in net_io:
                io_counters = net_io[interface]

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.NETWORK,
                    resource_id=interface,
                    metric_name="bytes_sent",
                    value=io_counters.bytes_sent,
                    unit="bytes",
                    tags={"interface": interface, "direction": "out", "interval": "cumulative"}
                ))

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.NETWORK,
                    resource_id=interface,
                    metric_name="bytes_recv",
                    value=io_counters.bytes_recv,
                    unit="bytes",
                    tags={"interface": interface, "direction": "in", "interval": "cumulative"}
                ))

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.NETWORK,
                    resource_id=interface,
                    metric_name="packets_sent",
                    value=io_counters.packets_sent,
                    unit="packets",
                    tags={"interface": interface, "direction": "out", "interval": "cumulative"}
                ))

                metrics.append(MetricValue(
                    timestamp=timestamp,
                    resource_type=ResourceType.NETWORK,
                    resource_id=interface,
                    metric_name="packets_recv",
                    value=io_counters.packets_recv,
                    unit="packets",
                    tags={"interface": interface, "direction": "in", "interval": "cumulative"}
                ))

        return metrics

    def collect_all_metrics(self, config: Dict[str, Any]) -> List[MetricValue]:
        """Collect all configured metrics."""
        metrics = []

        # CPU metrics
        if config.get('cpu', {}).get('enabled', True):
            cpu_interval = config.get('cpu', {}).get('collection_interval', 30)
            if int(time.time()) % cpu_interval == 0:  # Only collect periodically
                metrics.extend(self.collect_cpu_metrics())

        # Memory metrics
        if config.get('memory', {}).get('enabled', True):
            memory_interval = config.get('memory', {}).get('collection_interval', 30)
            if int(time.time()) % memory_interval == 0:  # Only collect periodically
                metrics.extend(self.collect_memory_metrics())

        # Disk metrics
        if config.get('disk', {}).get('enabled', True):
            disk_interval = config.get('disk', {}).get('collection_interval', 60)
            disk_paths = config.get('disk', {}).get('paths', ['/'])
            if int(time.time()) % disk_interval == 0:  # Only collect periodically
                metrics.extend(self.collect_disk_metrics(disk_paths))

        # Network metrics
        if config.get('network', {}).get('enabled', True):
            network_interval = config.get('network', {}).get('collection_interval', 30)
            network_interfaces = config.get('network', {}).get('interfaces', None)
            if int(time.time()) % network_interval == 0:  # Only collect periodically
                metrics.extend(self.collect_network_metrics(network_interfaces))

        return metrics


class AlertManager:
    """Manages alert generation and notifications."""

    def __init__(self, config: Dict[str, Any], metrics_db: MetricsDatabase):
        self.config = config
        self.metrics_db = metrics_db
        self.logger = logging.getLogger('AlertManager')
        self.active_alerts = {}  # Track active alerts to avoid duplicates

    def check_thresholds(self, metrics: List[MetricValue]) -> List[AlertInfo]:
        """Check metrics against configured thresholds and generate alerts."""
        alerts = []
        current_time = datetime.now().isoformat()

        for metric in metrics:
            # Get threshold configuration for this metric
            threshold_config = self._get_threshold_config(metric.resource_type, metric.metric_name)

            if threshold_config:
                alert = self._check_single_threshold(metric, threshold_config, current_time)
                if alert:
                    alerts.append(alert)

        return alerts

    def _get_threshold_config(self, resource_type: ResourceType, metric_name: str) -> Dict[str, Any]:
        """Get threshold configuration for a specific metric."""
        alerts_config = self.config.get('alerts', {}).get('thresholds', {})

        # Look for specific configuration
        if f"{resource_type.value}_{metric_name}" in alerts_config:
            return alerts_config[f"{resource_type.value}_{metric_name}"]

        # Look for general resource type configuration
        if f"{resource_type.value}_usage" in alerts_config:
            return alerts_config[f"{resource_type.value}_usage"]

        # Default thresholds
        defaults = {
            ResourceType.CPU: {"warning": 80, "critical": 90},
            ResourceType.MEMORY: {"warning": 85, "critical": 95},
            ResourceType.DISK: {"warning": 80, "critical": 95}
        }

        return defaults.get(resource_type, {})

    def _check_single_threshold(self, metric: MetricValue, threshold_config: Dict[str, Any], timestamp: str) -> Optional[AlertInfo]:
        """Check a single metric against its threshold."""
        warning_threshold = threshold_config.get('warning')
        critical_threshold = threshold_config.get('critical')

        if critical_threshold and metric.value >= critical_threshold:
            severity = AlertSeverity.CRITICAL
            threshold_value = critical_threshold
        elif warning_threshold and metric.value >= warning_threshold:
            severity = AlertSeverity.WARNING
            threshold_value = warning_threshold
        else:
            return None  # No threshold violation

        # Generate alert ID to prevent duplicates
        alert_id = f"alert_{hash(f'{metric.resource_type.value}_{metric.resource_id}_{metric.metric_name}_{timestamp}') % 1000000}"

        # Check if we already have an active alert for this metric
        existing_alert_key = f"{metric.resource_type.value}:{metric.resource_id}:{metric.metric_name}"
        if existing_alert_key in self.active_alerts:
            # If the new alert is the same or less severe, skip it
            existing_severity = self.active_alerts[existing_alert_key]['severity']
            if (severity == AlertSeverity.WARNING and existing_severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]) or \
               (severity == AlertSeverity.CRITICAL and existing_severity == AlertSeverity.CRITICAL):
                return None

        # Create alert message
        message = f"{metric.resource_type.value.upper()} {metric.resource_id} {metric.metric_name} is {metric.value}{metric.unit} (threshold: {threshold_value}{metric.unit})"

        alert = AlertInfo(
            id=alert_id,
            resource_type=metric.resource_type,
            resource_id=metric.resource_id,
            metric_name=metric.metric_name,
            threshold_value=threshold_value,
            current_value=metric.value,
            severity=severity,
            message=message,
            timestamp=timestamp
        )

        # Track this alert to prevent duplicates
        self.active_alerts[existing_alert_key] = {
            'severity': severity,
            'timestamp': timestamp
        }

        return alert

    def send_notifications(self, alerts: List[AlertInfo]):
        """Send notifications for generated alerts."""
        for alert in alerts:
            self._send_single_notification(alert)

    def _send_single_notification(self, alert: AlertInfo):
        """Send notification for a single alert."""
        try:
            # Determine recipients based on severity
            recipients_config = self.config.get('notifications', {}).get('recipients', {})
            if alert.severity == AlertSeverity.CRITICAL:
                recipients = recipients_config.get('critical', ['admin@example.com'])
            elif alert.severity == AlertSeverity.WARNING:
                recipients = recipients_config.get('warning', ['admin@example.com'])
            else:
                recipients = recipients_config.get('info', ['admin@example.com'])

            # Send email notification
            self._send_email_notification(alert, recipients)

            # Log the alert
            self.logger.info(f"Alert sent: {alert.message} (Severity: {alert.severity.value})")

        except Exception as e:
            self.logger.error(f"Failed to send notification for alert {alert.id}: {e}")

    def _send_email_notification(self, alert: AlertInfo, recipients: List[str]):
        """Send email notification for an alert."""
        try:
            smtp_server = os.getenv('MONITOR_SMTP_SERVER', 'localhost')
            smtp_port = int(os.getenv('MONITOR_SMTP_PORT', '587'))
            sender_email = os.getenv('MONITOR_SENDER_EMAIL', 'monitor@acme.com')
            sender_password = os.getenv('MONITOR_SENDER_PASSWORD', '')

            if not recipients:
                return

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)

            # Set subject based on severity
            if alert.severity == AlertSeverity.CRITICAL:
                msg['Subject'] = f"[CRITICAL] Resource Alert: {alert.message}"
            elif alert.severity == AlertSeverity.WARNING:
                msg['Subject'] = f"[WARNING] Resource Alert: {alert.message}"
            else:
                msg['Subject'] = f"[INFO] Resource Alert: {alert.message}"

            # Create message body
            body = f"""
Resource Alert

Severity: {alert.severity.value.upper()}
Resource: {alert.resource_type.value} - {alert.resource_id}
Metric: {alert.metric_name}
Current Value: {alert.current_value}
Threshold: {alert.threshold_value}
Message: {alert.message}
Time: {alert.timestamp}

Please investigate and take appropriate action.
"""

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email notification sent to {recipients}")

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")


class ResourceMonitor:
    """Main resource monitor class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.metrics_db = MetricsDatabase(os.getenv('RESOURCE_MONITOR_DATABASE_PATH', ':memory:'))
        self.collector = ResourceCollector()
        self.alert_manager = None
        self.running = False
        self.monitor_thread = None

        # Load configuration
        self.config = self.load_config()

        # Initialize alert manager after config is loaded
        self.alert_manager = AlertManager(self.config, self.metrics_db)

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the resource monitor."""
        logger = logging.getLogger('ResourceMonitor')
        logger.setLevel(getattr(logging, os.getenv('RESOURCE_MONITOR_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('RESOURCE_MONITOR_LOG_FILE_PATH', '/tmp/resource_monitor.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'monitoring': {
                'collection_interval_seconds': int(os.getenv('RESOURCE_MONITOR_COLLECTION_INTERVAL', '30')),
                'aggregation_window_seconds': 300,
                'retention_days': 30
            },
            'resources': {
                'cpu': {
                    'enabled': True,
                    'collection_interval': 10,
                    'thresholds': {'warning': 80, 'critical': 90}
                },
                'memory': {
                    'enabled': True,
                    'collection_interval': 15,
                    'thresholds': {'warning': 85, 'critical': 95}
                },
                'disk': {
                    'enabled': True,
                    'collection_interval': 60,
                    'paths': ['/'],
                    'thresholds': {'warning': 80, 'critical': 95}
                },
                'network': {
                    'enabled': True,
                    'collection_interval': 30,
                    'interfaces': None,  # Will use all interfaces
                    'thresholds': {'warning': 80, 'critical': 95}
                }
            },
            'alerts': {
                'thresholds': {
                    'cpu_usage': {'warning': 80, 'critical': 90},
                    'memory_usage': {'warning': 85, 'critical': 95},
                    'disk_usage': {'warning': 80, 'critical': 95}
                }
            }
        }

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    # Merge file config with defaults
                    for key, value in file_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
            except Exception as e:
                self.logger.warning(f"Failed to load config from {self.config_path}: {e}")

        return config

    def start_monitoring(self):
        """Start the monitoring process."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.logger.info("Resource monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring process."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        self.logger.info("Resource monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        self.logger.info("Monitoring loop started")

        while self.running:
            try:
                # Collect metrics
                metrics = self.collector.collect_all_metrics(self.config.get('resources', {}))

                # Store metrics in database
                for metric in metrics:
                    self.metrics_db.store_metric(metric)

                # Check thresholds and generate alerts
                alerts = self.alert_manager.check_thresholds(metrics)

                # Store alerts in database
                for alert in alerts:
                    self.metrics_db.store_alert(alert)

                # Send notifications for alerts
                if alerts:
                    self.alert_manager.send_notifications(alerts)

                # Sleep for the configured interval
                collection_interval = self.config['monitoring']['collection_interval_seconds']
                time.sleep(collection_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait a bit before retrying

    def get_current_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage summary."""
        # Collect current metrics
        resources_config = self.config.get('resources', {})
        metrics = self.collector.collect_all_metrics(resources_config)

        summary = {}
        for metric in metrics:
            resource_key = f"{metric.resource_type.value}:{metric.resource_id}"
            if resource_key not in summary:
                summary[resource_key] = {}

            summary[resource_key][metric.metric_name] = {
                'value': metric.value,
                'unit': metric.unit,
                'timestamp': metric.timestamp
            }

        return summary

    def get_historical_metrics(self, resource_type: str, metric_name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get historical metrics for a specific resource and metric."""
        try:
            rt = ResourceType(resource_type.lower())
            metrics = self.metrics_db.get_recent_metrics(rt, metric_name, hours)
            return [asdict(m) for m in metrics]
        except Exception:
            return []

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (non-acknowledged) alerts."""
        alerts = self.metrics_db.get_active_alerts()
        return [asdict(a) for a in alerts]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """Acknowledge an alert."""
        try:
            with self.metrics_db.get_connection() as conn:
                conn.execute('''
                    UPDATE alerts
                    SET acknowledged = TRUE, acknowledged_by = ?, acknowledged_at = ?
                    WHERE id = ?
                ''', (acknowledged_by, datetime.now().isoformat(), alert_id))

            # Remove from active alerts cache
            for key in list(self.alert_manager.active_alerts.keys()):
                if self.alert_manager.active_alerts[key]['alert_id'] == alert_id:
                    del self.alert_manager.active_alerts[key]
                    break

            self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False


def main():
    """Main function for testing the Resource Monitor."""
    print("Resource Monitor Skill")
    print("=====================")

    # Initialize the resource monitor
    config_path = os.getenv('MONITOR_CONFIG_PATH', './monitor_config.json')
    monitor = ResourceMonitor(config_path)

    print(f"Resource Monitor initialized with config: {config_path}")

    # Start monitoring
    monitor.start_monitoring()

    # Get initial resource usage
    print("\nGetting current resource usage...")
    usage = monitor.get_current_resource_usage()
    print(f"Current resource usage: {len(usage)} resources monitored")

    # Display some metrics
    for resource, metrics in list(usage.items())[:5]:  # Show first 5 resources
        print(f"  {resource}: {metrics}")

    # Get active alerts
    print("\nChecking for active alerts...")
    alerts = monitor.get_active_alerts()
    print(f"Active alerts: {len(alerts)}")

    if alerts:
        for alert in alerts[:3]:  # Show first 3 alerts
            print(f"  - {alert['severity']}: {alert['message']}")

    # Show how to get historical data
    print("\nExample: Getting CPU usage history (last hour)...")
    cpu_history = monitor.get_historical_metrics("cpu", "usage_percent", hours=1)
    print(f"Retrieved {len(cpu_history)} CPU usage data points")

    # Run for a short time to collect some data
    print("\nRunning for 10 seconds to collect metrics...")
    time.sleep(10)

    # Get updated resource usage
    print("\nUpdated resource usage:")
    updated_usage = monitor.get_current_resource_usage()
    for resource, metrics in list(updated_usage.items())[:5]:  # Show first 5 resources
        print(f"  {resource}: {metrics}")

    # Stop monitoring
    monitor.stop_monitoring()

    print("\nResource Monitor is ready to monitor system resources!")


if __name__ == "__main__":
    main()