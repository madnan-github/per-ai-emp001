#!/usr/bin/env python3
"""
Anomaly Detector - Identifies unusual patterns and behaviors in business operations

This script implements an anomaly detection system that monitors various data sources
for unusual patterns using statistical analysis, machine learning algorithms, and
rule-based detection to identify deviations from established baselines.
"""

import os
import sys
import json
import yaml
import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from scipy import stats
from scipy.stats import zscore
import warnings
warnings.filterwarnings('ignore')


class AnomalySeverity(Enum):
    """Anomaly severity levels"""
    LOW = 4
    MEDIUM = 3
    HIGH = 2
    CRITICAL = 1


class AnomalyType(Enum):
    """Types of anomalies"""
    POINT_ANOMALY = "point_anomaly"
    CONTEXTUAL_ANOMALY = "contextual_anomaly"
    COLLECTIVE_ANOMALY = "collective_anomaly"
    STATISTICAL_OUTLIER = "statistical_outlier"
    ML_PREDICTED = "ml_predicted"


@dataclass
class Anomaly:
    """Represents an anomaly with all required fields"""
    id: str
    timestamp: float
    entity_id: str
    entity_type: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    score: float
    confidence: float
    description: str
    data_point: Dict[str, Any]
    detection_method: str
    metadata: Optional[Dict] = None
    acknowledged: bool = False

    def to_dict(self) -> Dict:
        """Convert anomaly to dictionary format"""
        result = asdict(self)
        result['anomaly_type'] = self.anomaly_type.value
        result['severity'] = self.severity.value
        return result


class AnomalyStore:
    """Manages storage and retrieval of anomalies"""

    def __init__(self, db_path: str = "anomalies.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create anomalies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                entity_id TEXT,
                entity_type TEXT,
                anomaly_type TEXT,
                severity INTEGER,
                score REAL,
                confidence REAL,
                description TEXT,
                data_point TEXT,
                detection_method TEXT,
                metadata TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON anomalies(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_severity ON anomalies(severity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity ON anomalies(entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON anomalies(anomaly_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_acknowledged ON anomalies(acknowledged)')

        conn.commit()
        conn.close()

    def save_anomaly(self, anomaly: Anomaly):
        """Save an anomaly to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO anomalies
            (id, timestamp, entity_id, entity_type, anomaly_type, severity, score, confidence, description, data_point, detection_method, metadata, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            anomaly.id,
            anomaly.timestamp,
            anomaly.entity_id,
            anomaly.entity_type,
            anomaly.anomaly_type.value,
            anomaly.severity.value,
            anomaly.score,
            anomaly.confidence,
            anomaly.description,
            json.dumps(anomaly.data_point),
            anomaly.detection_method,
            json.dumps(anomaly.metadata or {}),
            anomaly.acknowledged
        ))

        conn.commit()
        conn.close()

    def get_unacknowledged_anomalies(self, limit: int = 100) -> List[Anomaly]:
        """Get unacknowledged anomalies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, timestamp, entity_id, entity_type, anomaly_type, severity, score, confidence, description, data_point, detection_method, metadata
            FROM anomalies
            WHERE acknowledged = 0
            ORDER BY severity ASC, timestamp DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        anomalies = []
        for row in rows:
            metadata = json.loads(row[11]) if row[11] else {}
            anomaly = Anomaly(
                id=row[0],
                timestamp=row[1],
                entity_id=row[2],
                entity_type=row[3],
                anomaly_type=AnomalyType(row[4]),
                severity=AnomalySeverity(row[5]),
                score=row[6],
                confidence=row[7],
                description=row[8],
                data_point=json.loads(row[9]),
                detection_method=row[10],
                metadata=metadata
            )
            anomalies.append(anomaly)

        return anomalies

    def acknowledge_anomaly(self, anomaly_id: str):
        """Mark an anomaly as acknowledged"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('UPDATE anomalies SET acknowledged = 1 WHERE id = ?', (anomaly_id,))
        conn.commit()
        conn.close()


class StatisticalAnomalyDetector:
    """Statistical methods for anomaly detection"""

    def __init__(self, config: Dict):
        self.config = config
        self.z_score_config = config.get('z_score', {})
        self.grubbs_config = config.get('grubbs_test', {})
        self.iqr_config = config.get('iqr_method', {})

    def detect_z_score(self, data: List[float], threshold: float = 3.0) -> List[Tuple[int, float]]:
        """Detect anomalies using Z-score method"""
        if len(data) < 3:  # Need at least 3 points for meaningful z-score
            return []

        # Calculate z-scores
        z_scores = np.abs(zscore(data))

        anomalies = []
        for i, z_score in enumerate(z_scores):
            if z_score > threshold:
                anomalies.append((i, z_score))

        return anomalies

    def detect_modified_z_score(self, data: List[float], threshold: float = 3.5) -> List[Tuple[int, float]]:
        """Detect anomalies using modified Z-score (using median absolute deviation)"""
        if len(data) < 3:
            return []

        median = np.median(data)
        mad = np.median(np.abs(data - median))

        if mad == 0:
            return []  # Avoid division by zero

        modified_z_scores = 0.6745 * (np.array(data) - median) / mad

        anomalies = []
        for i, mz_score in enumerate(modified_z_scores):
            if abs(mz_score) > threshold:
                anomalies.append((i, abs(mz_score)))

        return anomalies

    def detect_iqr(self, data: List[float], multiplier: float = 1.5) -> List[Tuple[int, float]]:
        """Detect anomalies using Interquartile Range method"""
        if len(data) < 4:  # Need at least 4 points for quartiles
            return []

        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        anomalies = []
        for i, value in enumerate(data):
            if value < lower_bound or value > upper_bound:
                # Calculate how far out of bounds the value is
                distance = max(abs(value - lower_bound), abs(value - upper_bound))
                anomalies.append((i, distance))

        return anomalies

    def detect_grubbs_test(self, data: List[float], significance_level: float = 0.05) -> List[Tuple[int, float]]:
        """Detect anomalies using Grubbs' test"""
        if len(data) < 3:
            return []

        n = len(data)
        data_array = np.array(data)

        # Calculate test statistic
        mean = np.mean(data_array)
        std = np.std(data_array, ddof=1)

        if std == 0:
            return []  # Avoid division by zero

        # Find the point furthest from the mean
        residuals = np.abs(data_array - mean)
        max_residual_idx = np.argmax(residuals)
        max_residual = residuals[max_residual_idx]

        # Calculate Grubbs' test statistic
        g_statistic = max_residual / std

        # Calculate critical value
        t_value = stats.t.ppf(1 - significance_level / (2 * n), n - 2)
        critical_value = ((n - 1) / np.sqrt(n)) * np.sqrt(t_value ** 2 / (n - 2 + t_value ** 2))

        anomalies = []
        if g_statistic > critical_value:
            anomalies.append((max_residual_idx, g_statistic))

        return anomalies


class MachineLearningAnomalyDetector:
    """Machine learning methods for anomaly detection"""

    def __init__(self, config: Dict):
        self.config = config
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models based on configuration"""
        # Isolation Forest
        if self.config.get('isolation_forest', {}).get('enabled', True):
            iso_params = self.config.get('isolation_forest', {})
            self.models['isolation_forest'] = IsolationForest(
                contamination=iso_params.get('contamination', 0.1),
                max_samples=iso_params.get('max_samples', 256),
                max_features=iso_params.get('max_features', 1.0),
                bootstrap=iso_params.get('bootstrap', False),
                n_estimators=iso_params.get('n_estimators', 100),
                random_state=42
            )

        # Local Outlier Factor
        if self.config.get('local_outlier_factor', {}).get('enabled', True):
            lof_params = self.config.get('local_outlier_factor', {})
            self.models['local_outlier_factor'] = LocalOutlierFactor(
                n_neighbors=lof_params.get('n_neighbors', 20),
                algorithm=lof_params.get('algorithm', 'auto'),
                leaf_size=lof_params.get('leaf_size', 30),
                metric=lof_params.get('metric', 'minkowski'),
                p=lof_params.get('p', 2),
                novelty=True  # For use on new data
            )

        # One-Class SVM
        if self.config.get('one_class_svm', {}).get('enabled', True):
            svm_params = self.config.get('one_class_svm', {})
            self.models['one_class_svm'] = OneClassSVM(
                kernel=svm_params.get('kernel', 'rbf'),
                degree=svm_params.get('degree', 3),
                gamma=svm_params.get('gamma', 'scale'),
                nu=svm_params.get('nu', 0.1),
                cache_size=svm_params.get('cache_size', 200)
            )

    def train_model(self, model_name: str, training_data: np.ndarray):
        """Train a specific model with the provided data"""
        if model_name in self.models:
            # Fit the model
            self.models[model_name].fit(training_data)
            return True
        return False

    def predict_anomalies(self, model_name: str, data: np.ndarray) -> List[Tuple[int, float]]:
        """Predict anomalies using the specified model"""
        if model_name not in self.models:
            return []

        model = self.models[model_name]

        try:
            if model_name == 'isolation_forest':
                predictions = model.predict(data)
                scores = model.decision_function(data)

                anomalies = []
                for i, (pred, score) in enumerate(zip(predictions, scores)):
                    if pred == -1:  # Anomaly detected
                        anomalies.append((i, abs(score)))

                return anomalies

            elif model_name == 'local_outlier_factor':
                predictions = model.fit_predict(data)
                scores = model.negative_outlier_factor_

                anomalies = []
                for i, (pred, score) in enumerate(zip(predictions, scores)):
                    if pred == -1:  # Anomaly detected
                        anomalies.append((i, abs(score)))

                return anomalies

            elif model_name == 'one_class_svm':
                predictions = model.predict(data)
                scores = model.decision_function(data)

                anomalies = []
                for i, (pred, score) in enumerate(zip(predictions, scores)):
                    if pred == -1:  # Anomaly detected
                        anomalies.append((i, abs(score)))

                return anomalies
        except Exception as e:
            print(f"Error predicting anomalies with {model_name}: {e}")
            return []

        return []


class BusinessRuleEngine:
    """Evaluates custom business rules for anomaly detection"""

    def __init__(self, config: Dict):
        self.config = config
        self.rules = config.get('rules', [])
        self.compound_rules = config.get('compound_rules', [])

    def evaluate_rules(self, data_point: Dict[str, Any]) -> List[Dict]:
        """Evaluate business rules against a data point"""
        triggered_rules = []

        for rule in self.rules:
            if self._evaluate_single_rule(rule, data_point):
                triggered_rules.append(rule)

        return triggered_rules

    def _evaluate_single_rule(self, rule: Dict, data_point: Dict[str, Any]) -> bool:
        """Evaluate a single business rule against a data point"""
        conditions = rule.get('conditions', [])

        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')

            if field not in data_point:
                return False

            actual_value = data_point[field]

            # Evaluate condition based on operator
            if operator == '>':
                if not (actual_value > value):
                    return False
            elif operator == '<':
                if not (actual_value < value):
                    return False
            elif operator == '>=':
                if not (actual_value >= value):
                    return False
            elif operator == '<=':
                if not (actual_value <= value):
                    return False
            elif operator == '=' or operator == '==':
                if actual_value != value:
                    return False
            elif operator == '!=':
                if actual_value == value:
                    return False
            elif operator == 'in':
                if actual_value not in value:
                    return False
            elif operator == 'not_in':
                if actual_value in value:
                    return False
            elif operator == 'contains':
                if isinstance(actual_value, str) and value not in actual_value:
                    return False
            elif operator == 'starts_with':
                if not str(actual_value).startswith(str(value)):
                    return False
            elif operator == 'ends_with':
                if not str(actual_value).endswith(str(value)):
                    return False
            else:
                # Unsupported operator
                return False

        # All conditions passed
        return True


class AnomalyDetector:
    """Main anomaly detector class"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.store = AnomalyStore()
        self.statistical_detector = StatisticalAnomalyDetector(
            self.config.get('detection_algorithms', {}).get('statistical', {})
        )
        self.ml_detector = MachineLearningAnomalyDetector(
            self.config.get('detection_algorithms', {}).get('machine_learning', {})
        )
        self.rule_engine = BusinessRuleEngine(
            self.config.get('business_rules', {})
        )
        self.data_sources = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.model_training_needed = {}  # Track which models need training

    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file"""
        default_config = {
            'processing': {
                'batch_size': 1000,
                'batch_interval': 30000,  # milliseconds
                'max_workers': 8
            },
            'storage': {
                'retention_days': 90
            },
            'detection_algorithms': {
                'statistical': {
                    'z_score': {
                        'enabled': True,
                        'threshold': 3.0,
                        'use_modified_z_score': False,
                        'mad_threshold': 3.5
                    },
                    'grubbs_test': {
                        'enabled': True,
                        'significance_level': 0.05
                    },
                    'iqr_method': {
                        'enabled': True,
                        'multiplier': 1.5
                    }
                },
                'machine_learning': {
                    'isolation_forest': {
                        'enabled': True,
                        'contamination': 0.1
                    },
                    'local_outlier_factor': {
                        'enabled': True,
                        'n_neighbors': 20
                    },
                    'one_class_svm': {
                        'enabled': True,
                        'nu': 0.1
                    }
                }
            },
            'business_rules': {
                'enabled': True,
                'rules': [],
                'compound_rules': []
            },
            'alerts': {
                'thresholds': {
                    'critical': {'min_confidence': 0.95, 'min_magnitude': 3.0},
                    'high': {'min_confidence': 0.80, 'min_magnitude': 2.0},
                    'medium': {'min_confidence': 0.60, 'min_magnitude': 1.5},
                    'low': {'min_confidence': 0.40, 'min_magnitude': 1.0}
                }
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    # Deep merge configs
                    self._deep_merge(default_config, loaded_config)
            except Exception as e:
                print(f"Warning: Could not load config {config_path}: {e}")

        return default_config

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge two dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def register_data_source(self, name: str, source_func: Callable):
        """Register a data source"""
        self.data_sources[name] = source_func

    def detect_statistical_anomalies(self, data_points: List[Dict], field_name: str) -> List[Anomaly]:
        """Detect anomalies using statistical methods"""
        anomalies = []

        # Extract values for the specified field
        values = []
        indices_to_data = {}
        for i, dp in enumerate(data_points):
            if field_name in dp:
                val = dp[field_name]
                # Only include numeric values
                if isinstance(val, (int, float)):
                    values.append(val)
                    indices_to_data[len(values) - 1] = (i, dp)

        if len(values) < 3:  # Need at least 3 points for statistical analysis
            return anomalies

        # Apply statistical detection methods
        config = self.config.get('detection_algorithms', {}).get('statistical', {})

        # Z-score detection
        if config.get('z_score', {}).get('enabled', True):
            threshold = config['z_score'].get('threshold', 3.0)
            z_anomalies = self.statistical_detector.detect_z_score(values, threshold)

            for idx, score in z_anomalies:
                orig_idx, orig_dp = indices_to_data[idx]
                anomaly = self._create_anomaly(
                    orig_dp, field_name, values[idx], 'z_score', score, AnomalyType.STATISTICAL_OUTLIER
                )
                anomalies.append(anomaly)

        # Modified Z-score detection
        if config.get('z_score', {}).get('use_modified_z_score', False):
            threshold = config['z_score'].get('mad_threshold', 3.5)
            mz_anomalies = self.statistical_detector.detect_modified_z_score(values, threshold)

            for idx, score in mz_anomalies:
                orig_idx, orig_dp = indices_to_data[idx]
                anomaly = self._create_anomaly(
                    orig_dp, field_name, values[idx], 'modified_z_score', score, AnomalyType.STATISTICAL_OUTLIER
                )
                anomalies.append(anomaly)

        # IQR detection
        if config.get('iqr_method', {}).get('enabled', True):
            multiplier = config['iqr_method'].get('multiplier', 1.5)
            iqr_anomalies = self.statistical_detector.detect_iqr(values, multiplier)

            for idx, score in iqr_anomalies:
                orig_idx, orig_dp = indices_to_data[idx]
                anomaly = self._create_anomaly(
                    orig_dp, field_name, values[idx], 'iqr_method', score, AnomalyType.STATISTICAL_OUTLIER
                )
                anomalies.append(anomaly)

        # Grubbs' test
        if config.get('grubbs_test', {}).get('enabled', True):
            sig_level = config['grubbs_test'].get('significance_level', 0.05)
            grubbs_anomalies = self.statistical_detector.detect_grubbs_test(values, sig_level)

            for idx, score in grubbs_anomalies:
                orig_idx, orig_dp = indices_to_data[idx]
                anomaly = self._create_anomaly(
                    orig_dp, field_name, values[idx], 'grubbs_test', score, AnomalyType.STATISTICAL_OUTLIER
                )
                anomalies.append(anomaly)

        return anomalies

    def detect_ml_anomalies(self, data_points: List[Dict], feature_fields: List[str]) -> List[Anomaly]:
        """Detect anomalies using machine learning methods"""
        anomalies = []

        # Prepare feature matrix
        feature_matrix = []
        valid_indices = []

        for i, dp in enumerate(data_points):
            features = []
            valid = True

            for field in feature_fields:
                if field in dp and isinstance(dp[field], (int, float)):
                    features.append(dp[field])
                else:
                    valid = False
                    break

            if valid and len(features) > 0:
                feature_matrix.append(features)
                valid_indices.append(i)

        if len(feature_matrix) < 10:  # Need sufficient data for ML
            return anomalies

        feature_array = np.array(feature_matrix)

        # Apply ML detection methods
        config = self.config.get('detection_algorithms', {}).get('machine_learning', {})

        # Isolation Forest
        if config.get('isolation_forest', {}).get('enabled', True):
            # Train the model if needed
            if 'isolation_forest' not in self.model_training_needed or self.model_training_needed['isolation_forest']:
                self.ml_detector.train_model('isolation_forest', feature_array)
                self.model_training_needed['isolation_forest'] = False

            iso_anomalies = self.ml_detector.predict_anomalies('isolation_forest', feature_array)

            for idx, score in iso_anomalies:
                orig_idx = valid_indices[idx]
                orig_dp = data_points[orig_idx]
                anomaly = self._create_anomaly(
                    orig_dp, ', '.join(feature_fields), feature_array[idx].mean(), 'isolation_forest', score, AnomalyType.ML_PREDICTED
                )
                anomalies.append(anomaly)

        # Local Outlier Factor
        if config.get('local_outlier_factor', {}).get('enabled', True):
            # LOF needs to be fit on the current data since it's used for novelty detection
            lof_result = self.ml_detector.predict_anomalies('local_outlier_factor', feature_array)

            for idx, score in lof_result:
                orig_idx = valid_indices[idx]
                orig_dp = data_points[orig_idx]
                anomaly = self._create_anomaly(
                    orig_dp, ', '.join(feature_fields), feature_array[idx].mean(), 'local_outlier_factor', score, AnomalyType.ML_PREDICTED
                )
                anomalies.append(anomaly)

        return anomalies

    def detect_rule_based_anomalies(self, data_points: List[Dict]) -> List[Anomaly]:
        """Detect anomalies using business rules"""
        anomalies = []

        for dp in data_points:
            triggered_rules = self.rule_engine.evaluate_rules(dp)

            for rule in triggered_rules:
                severity_str = rule.get('severity', 'medium')
                severity_map = {
                    'critical': AnomalySeverity.CRITICAL,
                    'high': AnomalySeverity.HIGH,
                    'medium': AnomalySeverity.MEDIUM,
                    'low': AnomalySeverity.LOW
                }
                severity = severity_map.get(severity_str, AnomalySeverity.MEDIUM)

                anomaly = Anomaly(
                    id=self._generate_anomaly_id(dp, rule['name']),
                    timestamp=time.time(),
                    entity_id=dp.get('id', dp.get('entity_id', 'unknown')),
                    entity_type=dp.get('entity_type', 'generic'),
                    anomaly_type=AnomalyType.POINT_ANOMALY,
                    severity=severity,
                    score=1.0,  # Rules have binary outcome
                    confidence=0.9,  # High confidence in rule-based detection
                    description=f"Business rule '{rule['name']}' triggered: {rule.get('description', '')}",
                    data_point=dp,
                    detection_method='business_rule',
                    metadata={'rule_name': rule['name'], 'rule_description': rule.get('description', '')}
                )
                anomalies.append(anomaly)

        return anomalies

    def _create_anomaly(self, data_point: Dict, field_name: str, value: float, method: str, score: float, anomaly_type: AnomalyType) -> Anomaly:
        """Create an anomaly object"""
        # Determine severity based on score
        if score > 3.0:
            severity = AnomalySeverity.CRITICAL
            confidence = min(0.95, score / 5.0)  # Cap confidence
        elif score > 2.0:
            severity = AnomalySeverity.HIGH
            confidence = min(0.85, score / 4.0)
        elif score > 1.5:
            severity = AnomalySeverity.MEDIUM
            confidence = min(0.70, score / 3.0)
        else:
            severity = AnomalySeverity.LOW
            confidence = min(0.50, score / 2.0)

        return Anomaly(
            id=self._generate_anomaly_id(data_point, method),
            timestamp=time.time(),
            entity_id=data_point.get('id', data_point.get('entity_id', 'unknown')),
            entity_type=data_point.get('entity_type', 'generic'),
            anomaly_type=anomaly_type,
            severity=severity,
            score=score,
            confidence=confidence,
            description=f"Anomaly detected in field '{field_name}' with value {value} using {method}",
            data_point=data_point,
            detection_method=method,
            metadata={'field_name': field_name, 'field_value': value}
        )

    def _generate_anomaly_id(self, data_point: Dict, method: str) -> str:
        """Generate a unique ID for the anomaly"""
        content = f"{data_point.get('id', '')}:{method}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def process_data_batch(self, data_points: List[Dict]):
        """Process a batch of data points for anomalies"""
        all_anomalies = []

        # Detect statistical anomalies for each numeric field
        numeric_fields = set()
        for dp in data_points:
            for key, value in dp.items():
                if isinstance(value, (int, float)):
                    numeric_fields.add(key)

        for field in numeric_fields:
            stat_anomalies = self.detect_statistical_anomalies(data_points, field)
            all_anomalies.extend(stat_anomalies)

        # Detect ML anomalies using all numeric fields
        if len(numeric_fields) >= 2:  # Need at least 2 features for ML
            ml_anomalies = self.detect_ml_anomalies(data_points, list(numeric_fields))
            all_anomalies.extend(ml_anomalies)

        # Detect rule-based anomalies
        rule_anomalies = self.detect_rule_based_anomalies(data_points)
        all_anomalies.extend(rule_anomalies)

        # Remove duplicates based on data point and detection method
        unique_anomalies = {}
        for anomaly in all_anomalies:
            key = f"{anomaly.entity_id}:{anomaly.detection_method}:{anomaly.description}"
            if key not in unique_anomalies or unique_anomalies[key].confidence < anomaly.confidence:
                unique_anomalies[key] = anomaly

        # Save anomalies to store
        for anomaly in unique_anomalies.values():
            self.store.save_anomaly(anomaly)

        print(f"Detected and saved {len(unique_anomalies)} unique anomalies from {len(data_points)} data points")

    async def ingest_data(self):
        """Ingest data from all registered sources"""
        all_data_points = []

        for source_name, source_func in self.data_sources.items():
            try:
                # Call source function (could be sync or async)
                if asyncio.iscoroutinefunction(source_func):
                    source_data = await source_func()
                else:
                    source_data = await asyncio.get_event_loop().run_in_executor(
                        self.executor, source_func
                    )

                if source_data:
                    all_data_points.extend(source_data)
                    print(f"Ingested {len(source_data)} data points from {source_name}")
            except Exception as e:
                print(f"Error ingesting data from {source_name}: {e}")

        return all_data_points

    async def run_pipeline(self):
        """Run the complete anomaly detection pipeline"""
        # Ingest data from all sources
        data_points = await self.ingest_data()

        if data_points:
            # Process through anomaly detection
            await self.process_data_batch(data_points)
            print(f"Completed anomaly detection for {len(data_points)} data points")
        else:
            print("No new data to process")

    async def run_continuous(self):
        """Run the anomaly detector continuously"""
        self.running = True
        print("Starting anomaly detector...")

        while self.running:
            try:
                await self.run_pipeline()

                # Wait before next iteration
                batch_interval = self.config['processing']['batch_interval'] / 1000.0  # Convert to seconds
                await asyncio.sleep(batch_interval)

            except KeyboardInterrupt:
                print("Received interrupt signal")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

        print("Anomaly detector stopped")

    def stop(self):
        """Stop the anomaly detector"""
        self.running = False
        self.executor.shutdown(wait=True)


def main():
    """Main entry point for the anomaly detector"""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Anomaly Detection Service")
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with mock data')

    args = parser.parse_args()

    # Initialize anomaly detector
    detector = AnomalyDetector(args.config)

    # Register sample data source for testing
    if args.test_mode:
        import random

        def mock_data_source():
            # Generate mock data points with occasional anomalies
            data_points = []
            for i in range(random.randint(50, 100)):
                # Normal data
                base_value = random.normalvariate(100, 15)  # mean=100, std=15

                # Occasionally inject anomalies
                if random.random() < 0.05:  # 5% chance of anomaly
                    base_value = random.uniform(150, 200)  # Higher than normal

                data_points.append({
                    'id': f'mock_{i}',
                    'timestamp': time.time() - random.randint(0, 3600),  # Within last hour
                    'entity_type': 'test_metric',
                    'value': base_value,
                    'category': 'performance' if random.random() > 0.5 else 'financial'
                })

            return data_points

        detector.register_data_source('mock_source', mock_data_source)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        detector.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the detector
    try:
        asyncio.run(detector.run_continuous())
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()