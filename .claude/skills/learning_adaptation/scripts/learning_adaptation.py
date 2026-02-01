#!/usr/bin/env python3
"""
Learning & Adaptation

This module provides continuous learning and behavioral adaptation for the Personal AI Employee system.
It analyzes user interactions, system performance, and environmental factors to improve system behavior,
optimize workflows, and personalize responses. This skill enables the AI to learn from experience
and adapt its behavior over time to better serve users.

Features:
- Continuous learning from user interactions
- Behavioral adaptation based on feedback
- Model training and evaluation
- Performance optimization
- Privacy-preserving learning
- Adaptive decision making
"""

import json
import os
import sqlite3
import logging
import threading
import time
import pickle
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import joblib


class LearningType(Enum):
    """Types of learning approaches."""
    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    TRANSFER = "transfer"


class ModelType(Enum):
    """Types of learning models."""
    NEURAL_NETWORK = "neural_network"
    DECISION_TREE = "decision_tree"
    SVM = "svm"
    ENSEMBLE = "ensemble"
    LOGISTIC_REGRESSION = "logistic_regression"


class AdaptationGoal(Enum):
    """Goals for adaptation."""
    EFFICIENCY = "efficiency"
    ACCURACY = "accuracy"
    PERSONALIZATION = "personalization"
    ROBUSTNESS = "robustness"


@dataclass
class LearningRecord:
    """Data class to hold learning record information."""
    id: str
    timestamp: str
    learning_type: LearningType
    model_type: ModelType
    data_source: str
    input_features: List[float]
    target_value: Optional[float]
    prediction: Optional[float]
    feedback_score: Optional[int]
    adaptation_goal: AdaptationGoal
    model_version: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any]


@dataclass
class AdaptationAction:
    """Data class to hold adaptation action information."""
    id: str
    timestamp: str
    action_type: str  # 'parameter_adjustment', 'model_update', 'behavior_change'
    target_component: str
    parameters: Dict[str, Any]
    reason: str
    confidence: float
    status: str  # 'proposed', 'approved', 'implemented', 'evaluated'


class DataManager:
    """Manages data collection and preprocessing for learning."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('DataManager')
        self.data_sources = config.get('data_sources', {})

    def collect_interaction_data(self) -> List[Dict[str, Any]]:
        """Collect interaction data from various sources."""
        interactions = []

        # Simulate collecting interaction data
        # In a real implementation, this would connect to actual data sources
        for i in range(5):  # Simulate 5 recent interactions
            interaction = {
                'timestamp': datetime.now().isoformat(),
                'user_id': f'user_{hash(f"user_{i}") % 1000}',
                'command': f'command_{i % 3}',
                'response_time': np.random.uniform(0.5, 3.0),
                'success': np.random.choice([True, False], p=[0.8, 0.2]),
                'user_satisfaction': np.random.randint(1, 6),  # 1-5 scale
                'context': {'time_of_day': 'morning', 'device': 'desktop', 'location': 'office'}
            }
            interactions.append(interaction)

        return interactions

    def collect_performance_data(self) -> List[Dict[str, Any]]:
        """Collect system performance data."""
        performance_data = []

        # Simulate collecting performance data
        for i in range(5):
            perf_data = {
                'timestamp': datetime.now().isoformat(),
                'component': f'component_{i % 3}',
                'response_time_ms': np.random.uniform(50, 500),
                'throughput_tps': np.random.uniform(1, 100),
                'error_rate': np.random.uniform(0, 0.1),
                'resource_utilization': {
                    'cpu_percent': np.random.uniform(10, 80),
                    'memory_percent': np.random.uniform(20, 70),
                    'disk_io_percent': np.random.uniform(5, 50)
                }
            }
            performance_data.append(perf_data)

        return performance_data

    def collect_feedback_data(self) -> List[Dict[str, Any]]:
        """Collect user feedback data."""
        feedback_data = []

        # Simulate collecting feedback data
        for i in range(3):
            feedback = {
                'timestamp': datetime.now().isoformat(),
                'user_id': f'user_{hash(f"user_{i}") % 1000}',
                'task_completed': np.random.choice([True, False]),
                'satisfaction_rating': np.random.randint(1, 6),
                'comments': f'Feedback comment {i}',
                'suggested_improvements': np.random.choice(['faster response', 'better accuracy', 'more features'], p=[0.5, 0.3, 0.2])
            }
            feedback_data.append(feedback)

        return feedback_data

    def preprocess_data(self, raw_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Preprocess raw data for model training."""
        if not raw_data:
            return np.array([]), None

        # Convert to DataFrame for easier processing
        df = pd.DataFrame(raw_data)

        # Extract features (this is a simplified example)
        feature_columns = []
        for col in df.columns:
            if col not in ['timestamp', 'user_id', 'command', 'comments', 'suggested_improvements', 'context']:
                feature_columns.append(col)

        # Handle categorical data by converting to numerical
        for col in df.select_dtypes(include=['object']).columns:
            if col not in ['timestamp', 'user_id', 'command', 'comments', 'suggested_improvements']:
                df[col] = pd.Categorical(df[col]).codes

        X = df[feature_columns].fillna(0).values

        # Try to extract target variable if available
        y = None
        if 'success' in df.columns:
            y = df['success'].astype(int).values
        elif 'satisfaction_rating' in df.columns:
            y = df['satisfaction_rating'].values
        elif 'task_completed' in df.columns:
            y = df['task_completed'].astype(int).values

        return X, y


class ModelManager:
    """Manages machine learning models for learning and adaptation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('ModelManager')
        self.models = {}
        self.scalers = {}
        self.model_versions = {}

    def create_model(self, model_type: ModelType, model_params: Dict[str, Any] = None) -> Union[object, None]:
        """Create a model based on the specified type."""
        if model_params is None:
            model_params = {}

        if model_type == ModelType.DECISION_TREE:
            from sklearn.tree import DecisionTreeClassifier
            return DecisionTreeClassifier(**model_params)
        elif model_type == ModelType.SVM:
            from sklearn.svm import SVC
            return SVC(probability=True, **model_params)
        elif model_type == ModelType.ENSEMBLE:
            return RandomForestClassifier(**model_params)
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            return LogisticRegression(**model_params)
        elif model_type == ModelType.NEURAL_NETWORK:
            # For neural networks, we'd typically use TensorFlow/Keras
            # For this example, we'll use a simple sklearn MLP
            from sklearn.neural_network import MLPClassifier
            return MLPClassifier(**model_params)
        else:
            self.logger.warning(f"Unsupported model type: {model_type}")
            return None

    def train_model(
        self,
        model_type: ModelType,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None
    ) -> Tuple[object, Dict[str, float]]:
        """Train a model and return the trained model with metrics."""
        if X_train.size == 0 or y_train.size == 0:
            self.logger.warning("Insufficient data for training")
            return None, {}

        # Initialize model
        model_params = self.config.get('models', {}).get(model_type.value, {})
        model = self.create_model(model_type, model_params)

        if model is None:
            return None, {}

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)

        if X_val is not None and y_val is not None:
            X_val_scaled = scaler.transform(X_val)
        else:
            X_val_scaled, y_val = None, None

        # Train the model
        start_time = time.time()
        model.fit(X_train_scaled, y_train)
        training_time = time.time() - start_time

        # Evaluate the model
        metrics = {}
        if X_val_scaled is not None and y_val is not None:
            y_pred = model.predict(X_val_scaled)
            metrics = {
                'accuracy': accuracy_score(y_val, y_pred),
                'precision': precision_score(y_val, y_pred, average='weighted', zero_division=0),
                'recall': recall_score(y_val, y_pred, average='weighted', zero_division=0),
                'f1_score': f1_score(y_val, y_pred, average='weighted', zero_division=0),
                'training_time': training_time
            }
        else:
            # If no validation data, use training data for basic metrics
            y_pred = model.predict(X_train_scaled)
            metrics = {
                'accuracy': accuracy_score(y_train, y_pred),
                'training_time': training_time
            }

        # Store scaler with the model
        model_id = f"{model_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.models[model_id] = model
        self.scalers[model_id] = scaler
        self.model_versions[model_id] = datetime.now().isoformat()

        self.logger.info(f"Model {model_id} trained with metrics: {metrics}")
        return model, metrics

    def predict(self, model_id: str, X: np.ndarray) -> np.ndarray:
        """Make predictions using a trained model."""
        if model_id not in self.models or model_id not in self.scalers:
            raise ValueError(f"Model {model_id} not found or not properly initialized")

        model = self.models[model_id]
        scaler = self.scalers[model_id]

        X_scaled = scaler.transform(X)
        return model.predict(X_scaled)

    def save_model(self, model_id: str, filepath: str):
        """Save a trained model to disk."""
        if model_id not in self.models or model_id not in self.scalers:
            raise ValueError(f"Model {model_id} not found")

        model_data = {
            'model': self.models[model_id],
            'scaler': self.scalers[model_id],
            'version': self.model_versions.get(model_id, 'unknown'),
            'created_at': datetime.now().isoformat()
        }

        joblib.dump(model_data, filepath)
        self.logger.info(f"Model {model_id} saved to {filepath}")

    def load_model(self, filepath: str, model_id: str):
        """Load a trained model from disk."""
        model_data = joblib.load(filepath)

        self.models[model_id] = model_data['model']
        self.scalers[model_id] = model_data['scaler']
        self.model_versions[model_id] = model_data['version']

        self.logger.info(f"Model {model_id} loaded from {filepath}")


class AdaptationEngine:
    """Engine that determines adaptation actions based on learning outcomes."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('AdaptationEngine')
        self.adaptation_goals = config.get('adaptation', {}).get('goals', {})

    def evaluate_performance(self, metrics: Dict[str, float], goal: AdaptationGoal) -> Dict[str, Any]:
        """Evaluate performance against adaptation goals."""
        evaluation = {
            'goal': goal.value,
            'current_metrics': metrics,
            'improvement_needed': False,
            'suggested_actions': []
        }

        if goal == AdaptationGoal.EFFICIENCY:
            # Check if response time needs improvement
            if 'response_time' in metrics and metrics['response_time'] > 1.0:  # threshold example
                evaluation['improvement_needed'] = True
                evaluation['suggested_actions'].append({
                    'type': 'performance_optimization',
                    'target': 'response_time',
                    'suggestion': 'Consider caching or algorithm optimization'
                })

        elif goal == AdaptationGoal.ACCURACY:
            # Check if accuracy needs improvement
            if 'accuracy' in metrics and metrics['accuracy'] < 0.8:  # threshold example
                evaluation['improvement_needed'] = True
                evaluation['suggested_actions'].append({
                    'type': 'model_improvement',
                    'target': 'accuracy',
                    'suggestion': 'Retrain with more data or try different algorithm'
                })

        elif goal == AdaptationGoal.PERSONALIZATION:
            # Check if personalization metrics need improvement
            if 'user_satisfaction' in metrics and metrics['user_satisfaction'] < 4.0:  # threshold example
                evaluation['improvement_needed'] = True
                evaluation['suggested_actions'].append({
                    'type': 'behavior_adaptation',
                    'target': 'user_experience',
                    'suggestion': 'Adjust response style or personalization parameters'
                })

        elif goal == AdaptationGoal.ROBUSTNESS:
            # Check if error rate is too high
            if 'error_rate' in metrics and metrics['error_rate'] > 0.05:  # threshold example
                evaluation['improvement_needed'] = True
                evaluation['suggested_actions'].append({
                    'type': 'robustness_improvement',
                    'target': 'error_handling',
                    'suggestion': 'Implement better error handling or fallback mechanisms'
                })

        return evaluation

    def generate_adaptation_action(self, evaluation: Dict[str, Any]) -> Optional[AdaptationAction]:
        """Generate an adaptation action based on evaluation."""
        if not evaluation['improvement_needed'] or not evaluation['suggested_actions']:
            return None

        suggestion = evaluation['suggested_actions'][0]  # Take the first suggestion
        action_id = f"adapt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(suggestion)) % 10000}"

        adaptation_action = AdaptationAction(
            id=action_id,
            timestamp=datetime.now().isoformat(),
            action_type=suggestion['type'],
            target_component=suggestion['target'],
            parameters={},
            reason=suggestion['suggestion'],
            confidence=0.8,  # Default confidence
            status='proposed'
        )

        return adaptation_action

    def apply_adaptation(self, action: AdaptationAction) -> bool:
        """Apply an adaptation action to the system."""
        try:
            # In a real implementation, this would actually modify system parameters
            # For this example, we'll just log the action
            self.logger.info(f"Applying adaptation action {action.id}: {action.reason}")

            # Update action status
            action.status = 'implemented'
            action.timestamp = datetime.now().isoformat()

            return True
        except Exception as e:
            self.logger.error(f"Failed to apply adaptation action {action.id}: {e}")
            action.status = 'failed'
            return False


class LearningRegistry:
    """Manages the learning registry database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_records (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    learning_type TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    input_features TEXT NOT NULL,
                    target_value REAL,
                    prediction REAL,
                    feedback_score INTEGER,
                    adaptation_goal TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    metrics TEXT,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS adaptation_actions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_component TEXT NOT NULL,
                    parameters TEXT,
                    reason TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL
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

    def add_learning_record(self, record: LearningRecord):
        """Add a learning record to the registry."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO learning_records
                (id, timestamp, learning_type, model_type, data_source, input_features,
                 target_value, prediction, feedback_score, adaptation_goal,
                 model_version, metrics, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.id, record.timestamp, record.learning_type.value,
                record.model_type.value, record.data_source,
                json.dumps(record.input_features), record.target_value,
                record.prediction, record.feedback_score,
                record.adaptation_goal.value, record.model_version,
                json.dumps(record.metrics), json.dumps(record.metadata)
            ))

    def add_adaptation_action(self, action: AdaptationAction):
        """Add an adaptation action to the registry."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO adaptation_actions
                (id, timestamp, action_type, target_component, parameters, reason, confidence, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action.id, action.timestamp, action.action_type, action.target_component,
                json.dumps(action.parameters), action.reason, action.confidence, action.status
            ))

    def get_recent_learning_records(self, limit: int = 10) -> List[LearningRecord]:
        """Get recent learning records."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, timestamp, learning_type, model_type, data_source, input_features,
                       target_value, prediction, feedback_score, adaptation_goal,
                       model_version, metrics, metadata
                FROM learning_records
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            records = []
            for row in rows:
                records.append(LearningRecord(
                    id=row[0], timestamp=row[1], learning_type=LearningType(row[2]),
                    model_type=ModelType(row[3]), data_source=row[4],
                    input_features=json.loads(row[5]), target_value=row[6],
                    prediction=row[7], feedback_score=row[8],
                    adaptation_goal=AdaptationGoal(row[9]), model_version=row[10],
                    metrics=json.loads(row[11]) if row[11] else {},
                    metadata=json.loads(row[12]) if row[12] else {}
                ))
            return records

    def get_adaptation_actions_by_status(self, status: str) -> List[AdaptationAction]:
        """Get adaptation actions by status."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, timestamp, action_type, target_component, parameters, reason, confidence, status
                FROM adaptation_actions
                WHERE status = ?
                ORDER BY timestamp DESC
            ''', (status,))
            rows = cursor.fetchall()
            actions = []
            for row in rows:
                actions.append(AdaptationAction(
                    id=row[0], timestamp=row[1], action_type=row[2],
                    target_component=row[3], parameters=json.loads(row[4]) if row[4] else {},
                    reason=row[5], confidence=row[6], status=row[7]
                ))
            return actions


class LearningAdaptation:
    """Main learning and adaptation class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.learning_registry = LearningRegistry(os.getenv('LEARNING_REGISTRY_DB_PATH', ':memory:'))
        self.data_manager = DataManager({})
        self.model_manager = ModelManager({})
        self.adaptation_engine = AdaptationEngine({})

        # Load configuration
        self.config = self.load_config()

        # Reinitialize components with loaded config
        self.data_manager = DataManager(self.config)
        self.model_manager = ModelManager(self.config)
        self.adaptation_engine = AdaptationEngine(self.config)

        # Initialize default model
        self.current_model_id = None
        self.current_model_type = ModelType(self.config['learning'].get('model_type', 'random_forest'))

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the learning and adaptation system."""
        logger = logging.getLogger('LearningAdaptation')
        logger.setLevel(getattr(logging, os.getenv('LEARNING_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('LEARNING_LOG_FILE_PATH', '/tmp/learning_adaptation.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'learning': {
                'learning_type': 'reinforcement',
                'model_type': 'random_forest',
                'learning_rate': 0.01,
                'batch_size': 32,
                'epochs': 10,
                'validation_split': 0.2
            },
            'data_sources': {
                'interaction_data': {'enabled': True},
                'performance_data': {'enabled': True},
                'feedback_data': {'enabled': True}
            },
            'models': {
                'random_forest': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'random_state': 42
                }
            },
            'adaptation': {
                'goals': {
                    'efficiency': {'enabled': True, 'target_improvement_percent': 10},
                    'accuracy': {'enabled': True, 'target_improvement_percent': 5}
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

    def run_learning_cycle(self) -> Dict[str, Any]:
        """Run a complete learning cycle."""
        try:
            self.logger.info("Starting learning cycle")

            # Collect data from all sources
            all_data = []
            all_targets = []

            # Collect interaction data
            if self.config['data_sources']['interaction_data']['enabled']:
                interaction_data = self.data_manager.collect_interaction_data()
                if interaction_data:
                    X_int, y_int = self.data_manager.preprocess_data(interaction_data)
                    all_data.append(X_int)
                    if y_int is not None:
                        all_targets.extend(y_int)

            # Collect performance data
            if self.config['data_sources']['performance_data']['enabled']:
                performance_data = self.data_manager.collect_performance_data()
                if performance_data:
                    X_perf, y_perf = self.data_manager.preprocess_data(performance_data)
                    all_data.append(X_perf)
                    if y_perf is not None:
                        all_targets.extend(y_perf)

            # Collect feedback data
            if self.config['data_sources']['feedback_data']['enabled']:
                feedback_data = self.data_manager.collect_feedback_data()
                if feedback_data:
                    X_feed, y_feed = self.data_manager.preprocess_data(feedback_data)
                    all_data.append(X_feed)
                    if y_feed is not None:
                        all_targets.extend(y_feed)

            # Combine all data
            if not all_data or all(len(data) == 0 for data in all_data):
                self.logger.warning("No data collected for learning")
                return {"status": "no_data", "message": "No data available for learning"}

            # Concatenate all features
            X_combined = np.vstack([data for data in all_data if len(data) > 0])
            y_combined = np.array(all_targets) if all_targets else None

            # Split data for training and validation
            if y_combined is not None and len(X_combined) > 1:
                X_train, X_val, y_train, y_val = train_test_split(
                    X_combined, y_combined,
                    test_size=self.config['learning']['validation_split'],
                    random_state=42
                )

                # Train model
                model, metrics = self.model_manager.train_model(
                    self.current_model_type, X_train, y_train, X_val, y_val
                )

                # Update current model
                if model is not None:
                    # Get the last model ID from the model manager
                    model_ids = list(self.model_manager.models.keys())
                    if model_ids:
                        self.current_model_id = model_ids[-1]

                    # Create learning record
                    learning_record = LearningRecord(
                        id=f"learn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(metrics)) % 10000}",
                        timestamp=datetime.now().isoformat(),
                        learning_type=LearningType(self.config['learning']['learning_type']),
                        model_type=self.current_model_type,
                        data_source="combined",
                        input_features=X_train[0].tolist() if len(X_train) > 0 else [],
                        target_value=y_train[0] if len(y_train) > 0 else None,
                        prediction=None,  # Would be set if we made a prediction
                        feedback_score=None,
                        adaptation_goal=AdaptationGoal.PERSONALIZATION,  # Default
                        model_version=self.model_manager.model_versions.get(self.current_model_id, "unknown"),
                        metrics=metrics,
                        metadata={"data_points": len(X_train)}
                    )

                    self.learning_registry.add_learning_record(learning_record)

                    # Evaluate performance and suggest adaptations
                    for goal_name, goal_config in self.config['adaptation']['goals'].items():
                        if goal_config.get('enabled', False):
                            goal = AdaptationGoal(goal_name)
                            evaluation = self.adaptation_engine.evaluate_performance(metrics, goal)

                            if evaluation['improvement_needed']:
                                adaptation_action = self.adaptation_engine.generate_adaptation_action(evaluation)
                                if adaptation_action:
                                    self.learning_registry.add_adaptation_action(adaptation_action)
                                    self.logger.info(f"Generated adaptation action: {adaptation_action.reason}")

                return {
                    "status": "success",
                    "metrics": metrics,
                    "data_points": len(X_combined),
                    "model_id": self.current_model_id
                }
            else:
                self.logger.warning("Insufficient data for training after preprocessing")
                return {"status": "insufficient_data", "message": "Not enough data for training"}

        except Exception as e:
            self.logger.error(f"Error in learning cycle: {e}")
            return {"status": "error", "error": str(e)}

    def apply_adaptations(self) -> List[str]:
        """Apply pending adaptations."""
        try:
            # Get proposed adaptations
            proposed_actions = self.learning_registry.get_adaptation_actions_by_status('proposed')

            applied_actions = []
            for action in proposed_actions:
                success = self.adaptation_engine.apply_adaptation(action)
                if success:
                    applied_actions.append(action.id)
                    # Update status in registry
                    # In a real implementation, we'd have a method to update the status
                    self.logger.info(f"Applied adaptation: {action.reason}")
                else:
                    self.logger.error(f"Failed to apply adaptation: {action.reason}")

            return applied_actions
        except Exception as e:
            self.logger.error(f"Error applying adaptations: {e}")
            return []

    def get_learning_status(self) -> Dict[str, Any]:
        """Get the current learning and adaptation status."""
        recent_records = self.learning_registry.get_recent_learning_records(5)
        pending_adaptations = self.learning_registry.get_adaptation_actions_by_status('proposed')

        return {
            "recent_learning_cycles": len(recent_records),
            "pending_adaptations": len(pending_adaptations),
            "current_model_id": self.current_model_id,
            "last_learning_time": recent_records[0].timestamp if recent_records else None,
            "recent_metrics": recent_records[0].metrics if recent_records else {}
        }


def main():
    """Main function for testing the Learning & Adaptation system."""
    print("Learning & Adaptation Skill")
    print("===========================")

    # Initialize the learning system
    config_path = os.getenv('LEARNING_CONFIG_PATH', './learning_config.json')
    learner = LearningAdaptation(config_path)

    print(f"Learning & Adaptation system initialized with config: {config_path}")

    # Run an initial learning cycle
    print("\nRunning initial learning cycle...")
    result = learner.run_learning_cycle()
    print(f"Learning cycle result: {result}")

    # Get current status
    status = learner.get_learning_status()
    print(f"\nCurrent status: {status}")

    # Apply any pending adaptations
    print("\nApplying pending adaptations...")
    applied = learner.apply_adaptations()
    print(f"Applied adaptations: {len(applied)}")

    # Run another learning cycle to see improvements
    print("\nRunning second learning cycle...")
    result2 = learner.run_learning_cycle()
    print(f"Second learning cycle result: {result2}")

    # Get updated status
    updated_status = learner.get_learning_status()
    print(f"\nUpdated status: {updated_status}")

    print("\nLearning & Adaptation system is ready to learn and adapt!")


if __name__ == "__main__":
    main()