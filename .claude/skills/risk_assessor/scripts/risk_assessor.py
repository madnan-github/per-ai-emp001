#!/usr/bin/env python3
"""
Risk Assessor - Evaluates potential risks across business operations

This script implements a comprehensive risk assessment system that identifies,
analyzes, quantifies, and prioritizes risks to enable informed decision-making
and appropriate risk mitigation strategies.
"""

import os
import sys
import json
import yaml
import asyncio
import logging
import sqlite3
import hashlib
import hmac
import time
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from scipy import stats
import math


class RiskCategory(Enum):
    """Risk categories"""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    COMPLIANCE = "compliance"
    TECHNOLOGY = "technology"
    ENVIRONMENTAL = "environmental"


class RiskLevel(Enum):
    """Risk levels"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class RiskTreatment(Enum):
    """Risk treatment options"""
    ACCEPT = "accept"
    AVOID = "avoid"
    MITIGATE = "mitigate"
    TRANSFER = "transfer"
    SHARE = "share"


@dataclass
class RiskFactor:
    """Represents a risk factor contributing to an overall risk"""
    name: str
    description: str
    probability: float  # 0.0 to 1.0
    impact: float       # 0.0 to 1.0
    category: RiskCategory
    weight: float = 1.0
    data_source: Optional[str] = None
    last_updated: Optional[float] = None


@dataclass
class RiskAssessment:
    """Represents a risk assessment"""
    id: str
    name: str
    description: str
    category: RiskCategory
    level: RiskLevel
    probability: float  # 0.0 to 1.0
    impact: float       # 0.0 to 1.0
    score: float        # 0.0 to 1.0 (normalized risk score)
    factors: List[RiskFactor]
    treatment: RiskTreatment
    treatment_plan: str
    mitigation_actions: List[str]
    status: str  # "identified", "assessed", "mitigated", "monitored"
    created_at: float
    updated_at: float
    metadata: Optional[Dict] = None


@dataclass
class RiskControl:
    """Represents a control measure for mitigating risks"""
    id: str
    name: str
    description: str
    category: str  # "preventive", "detective", "corrective"
    effectiveness: float  # 0.0 to 1.0
    cost: float
    risk_reduction: float  # How much it reduces risk (0.0 to 1.0)
    implementation_status: str  # "planned", "in_progress", "implemented", "deprecated"
    created_at: float


class RiskStore:
    """Manages storage and retrieval of risk assessments and controls"""

    def __init__(self, db_path: str = "risks.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create risk_assessments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                category TEXT,
                level INTEGER,
                probability REAL,
                impact REAL,
                score REAL,
                factors TEXT,
                treatment TEXT,
                treatment_plan TEXT,
                mitigation_actions TEXT,
                status TEXT,
                created_at REAL,
                updated_at REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create risk_controls table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_controls (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                category TEXT,
                effectiveness REAL,
                cost REAL,
                risk_reduction REAL,
                implementation_status TEXT,
                created_at REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON risk_assessments(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_level ON risk_assessments(level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON risk_assessments(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON risk_assessments(score)')

        conn.commit()
        conn.close()

    def save_assessment(self, assessment: RiskAssessment):
        """Save a risk assessment to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO risk_assessments
            (id, name, description, category, level, probability, impact, score, factors, treatment, treatment_plan, mitigation_actions, status, created_at, updated_at, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            assessment.id,
            assessment.name,
            assessment.description,
            assessment.category.value,
            assessment.level.value,
            assessment.probability,
            assessment.impact,
            assessment.score,
            json.dumps([asdict(factor) for factor in assessment.factors]),
            assessment.treatment.value,
            assessment.treatment_plan,
            json.dumps(assessment.mitigation_actions),
            assessment.status,
            assessment.created_at,
            assessment.updated_at,
            json.dumps(assessment.metadata or {})
        ))

        conn.commit()
        conn.close()

    def save_control(self, control: RiskControl):
        """Save a risk control to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO risk_controls
            (id, name, description, category, effectiveness, cost, risk_reduction, implementation_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            control.id,
            control.name,
            control.description,
            control.category,
            control.effectiveness,
            control.cost,
            control.risk_reduction,
            control.implementation_status,
            control.created_at
        ))

        conn.commit()
        conn.close()

    def get_assessments_by_category(self, category: RiskCategory) -> List[RiskAssessment]:
        """Get risk assessments by category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, category, level, probability, impact, score, factors, treatment, treatment_plan, mitigation_actions, status, created_at, updated_at, metadata
            FROM risk_assessments
            WHERE category = ?
            ORDER BY score DESC
        ''', (category.value,))

        rows = cursor.fetchall()
        conn.close()

        assessments = []
        for row in rows:
            factors = [RiskFactor(**factor) for factor in json.loads(row[8])]
            mitigation_actions = json.loads(row[11]) if row[11] else []

            assessment = RiskAssessment(
                id=row[0],
                name=row[1],
                description=row[2],
                category=RiskCategory(row[3]),
                level=RiskLevel(row[4]),
                probability=row[5],
                impact=row[6],
                score=row[7],
                factors=factors,
                treatment=RiskTreatment(row[9]),
                treatment_plan=row[10],
                mitigation_actions=mitigation_actions,
                status=row[12],
                created_at=row[13],
                updated_at=row[14],
                metadata=json.loads(row[15]) if row[15] else {}
            )
            assessments.append(assessment)

        return assessments

    def get_assessment(self, assessment_id: str) -> Optional[RiskAssessment]:
        """Get a specific risk assessment by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, category, level, probability, impact, score, factors, treatment, treatment_plan, mitigation_actions, status, created_at, updated_at, metadata
            FROM risk_assessments
            WHERE id = ?
        ''', (assessment_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            factors = [RiskFactor(**factor) for factor in json.loads(row[8])] if row[8] else []
            mitigation_actions = json.loads(row[11]) if row[11] else []

            assessment = RiskAssessment(
                id=row[0],
                name=row[1],
                description=row[2],
                category=RiskCategory(row[3]),
                level=RiskLevel(row[4]),
                probability=row[5],
                impact=row[6],
                score=row[7],
                factors=factors,
                treatment=RiskTreatment(row[9]),
                treatment_plan=row[10],
                mitigation_actions=mitigation_actions,
                status=row[12],
                created_at=row[13],
                updated_at=row[14],
                metadata=json.loads(row[15]) if row[15] else {}
            )
            return assessment

        return None

    def get_all_assessments(self) -> List[RiskAssessment]:
        """Get all risk assessments"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, category, level, probability, impact, score, factors, treatment, treatment_plan, mitigation_actions, status, created_at, updated_at, metadata
            FROM risk_assessments
            ORDER BY score DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        assessments = []
        for row in rows:
            factors = [RiskFactor(**factor) for factor in json.loads(row[8])] if row[8] else []
            mitigation_actions = json.loads(row[11]) if row[11] else []

            assessment = RiskAssessment(
                id=row[0],
                name=row[1],
                description=row[2],
                category=RiskCategory(row[3]),
                level=RiskLevel(row[4]),
                probability=row[5],
                impact=row[6],
                score=row[7],
                factors=factors,
                treatment=RiskTreatment(row[9]),
                treatment_plan=row[10],
                mitigation_actions=mitigation_actions,
                status=row[12],
                created_at=row[13],
                updated_at=row[14],
                metadata=json.loads(row[15]) if row[15] else {}
            )
            assessments.append(assessment)

        return assessments


class RiskCalculator:
    """Calculates risk scores and probabilities"""

    def __init__(self, config: Dict):
        self.config = config

    def calculate_risk_score(self, probability: float, impact: float, factors: List[RiskFactor] = None) -> float:
        """Calculate overall risk score based on probability and impact"""
        if factors:
            # Calculate weighted average of factor scores
            weighted_score = 0.0
            total_weight = 0.0

            for factor in factors:
                factor_score = factor.probability * factor.impact
                weighted_score += factor_score * factor.weight
                total_weight += factor.weight

            if total_weight > 0:
                factor_based_score = weighted_score / total_weight
                # Blend factor-based score with direct probability/impact
                return 0.5 * (probability * impact) + 0.5 * factor_based_score

        return probability * impact

    def calculate_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level based on score"""
        if score <= 0.1:
            return RiskLevel.VERY_LOW
        elif score <= 0.3:
            return RiskLevel.LOW
        elif score <= 0.5:
            return RiskLevel.MEDIUM
        elif score <= 0.7:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def perform_monte_carlo_simulation(self, iterations: int, base_probability: float, base_impact: float,
                                      variance_factor: float = 0.1) -> Dict[str, float]:
        """Perform Monte Carlo simulation for risk assessment"""
        probabilities = np.random.normal(base_probability, variance_factor, iterations)
        impacts = np.random.normal(base_impact, variance_factor, iterations)

        # Ensure probabilities and impacts stay within bounds
        probabilities = np.clip(probabilities, 0.0, 1.0)
        impacts = np.clip(impacts, 0.0, 1.0)

        risk_scores = probabilities * impacts

        return {
            'mean': float(np.mean(risk_scores)),
            'std': float(np.std(risk_scores)),
            'percentiles': {
                5: float(np.percentile(risk_scores, 5)),
                25: float(np.percentile(risk_scores, 25)),
                50: float(np.percentile(risk_scores, 50)),
                75: float(np.percentile(risk_scores, 75)),
                95: float(np.percentile(risk_scores, 95))
            }
        }

    def sensitivity_analysis(self, base_prob: float, base_impact: float, variables: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Perform sensitivity analysis on risk variables"""
        base_score = base_prob * base_impact
        sensitivity_results = {}

        for var_name, var_range in variables.items():
            low_prob = var_range.get('prob_low', base_prob)
            low_impact = var_range.get('impact_low', base_impact)
            high_prob = var_range.get('prob_high', base_prob)
            high_impact = var_range.get('impact_high', base_impact)

            low_score = low_prob * low_impact
            high_score = high_prob * high_impact

            sensitivity_results[var_name] = {
                'low_score': low_score,
                'high_score': high_score,
                'sensitivity': abs(high_score - low_score) / base_score if base_score != 0 else 0
            }

        return sensitivity_results


class DataCollector:
    """Collects risk data from various sources"""

    def __init__(self, config: Dict):
        self.config = config

    def collect_internal_data(self) -> Dict[str, Any]:
        """Collect internal risk data"""
        # This would connect to internal systems in a real implementation
        # For demo purposes, we'll return mock data
        return {
            'financial_metrics': {
                'liquidity_ratio': random.uniform(0.5, 2.0),
                'debt_to_equity': random.uniform(0.1, 1.0),
                'interest_coverage': random.uniform(2.0, 10.0)
            },
            'operational_metrics': {
                'error_rate': random.uniform(0.01, 0.1),
                'uptime': random.uniform(0.95, 0.999),
                'cycle_time': random.uniform(1.0, 10.0)
            },
            'compliance_metrics': {
                'audit_findings': random.randint(0, 10),
                'regulatory_violations': random.randint(0, 3),
                'training_compliance': random.uniform(0.8, 1.0)
            }
        }

    def collect_external_data(self) -> Dict[str, Any]:
        """Collect external risk data"""
        # This would connect to external APIs in a real implementation
        # For demo purposes, we'll return mock data
        return {
            'market_data': {
                'volatility_index': random.uniform(10, 50),
                'credit_spreads': random.uniform(0.5, 5.0),
                'currencies': {'EUR_USD': random.uniform(1.05, 1.15)}
            },
            'regulatory_updates': {
                'new_regulations': random.randint(0, 5),
                'policy_changes': random.randint(0, 3)
            },
            'threat_intelligence': {
                'cyber_threats': random.randint(0, 100),
                'vulnerability_alerts': random.randint(0, 20)
            }
        }

    def calculate_derived_factors(self, internal_data: Dict, external_data: Dict) -> List[RiskFactor]:
        """Calculate risk factors from collected data"""
        factors = []

        # Financial risk factors
        liquidity_ratio = internal_data['financial_metrics']['liquidity_ratio']
        debt_to_equity = internal_data['financial_metrics']['debt_to_equity']

        factors.append(RiskFactor(
            name="liquidity_risk",
            description="Risk of not being able to meet short-term obligations",
            probability=min(liquidity_ratio * 0.3, 1.0),
            impact=1.0 - liquidity_ratio / 2.0 if liquidity_ratio < 2.0 else 0.1,
            category=RiskCategory.FINANCIAL,
            weight=1.0
        ))

        factors.append(RiskFactor(
            name="leverage_risk",
            description="Risk associated with high debt levels",
            probability=min(debt_to_equity * 0.5, 1.0),
            impact=min(debt_to_equity * 0.7, 1.0),
            category=RiskCategory.FINANCIAL,
            weight=1.0
        ))

        # Operational risk factors
        error_rate = internal_data['operational_metrics']['error_rate']
        uptime = internal_data['operational_metrics']['uptime']

        factors.append(RiskFactor(
            name="operational_efficiency",
            description="Risk from operational inefficiencies",
            probability=error_rate,
            impact=error_rate,
            category=RiskCategory.OPERATIONAL,
            weight=0.8
        ))

        factors.append(RiskFactor(
            name="system_availability",
            description="Risk from system downtime",
            probability=1.0 - uptime,
            impact=1.0 - uptime,
            category=RiskCategory.TECHNOLOGY,
            weight=0.9
        ))

        # Market risk factors
        volatility = external_data['market_data']['volatility_index']
        credit_spreads = external_data['market_data']['credit_spreads']

        factors.append(RiskFactor(
            name="market_volatility",
            description="Risk from market fluctuations",
            probability=min(volatility / 50.0, 1.0),
            impact=min(volatility / 30.0, 1.0),
            category=RiskCategory.FINANCIAL,
            weight=0.7
        ))

        factors.append(RiskFactor(
            name="credit_spread_widening",
            description="Risk from increased borrowing costs",
            probability=min(credit_spreads / 5.0, 1.0),
            impact=min(credit_spreads / 3.0, 1.0),
            category=RiskCategory.FINANCIAL,
            weight=0.8
        ))

        return factors


class RiskAssessor:
    """Main risk assessor class"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.store = RiskStore()
        self.calculator = RiskCalculator(self.config)
        self.data_collector = DataCollector(self.config)
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)

    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file"""
        default_config = {
            'processing': {
                'max_workers': 16,
                'timeout': 30000,  # milliseconds
                'max_concurrent_assessments': 100
            },
            'risk_matrices': {
                'default': {
                    'grid': [
                        [1, 1, 2, 3, 4],
                        [1, 2, 3, 4, 5],
                        [2, 3, 4, 5, 5],
                        [3, 4, 5, 5, 5],
                        [4, 5, 5, 5, 5]
                    ]
                }
            },
            'assessment_methods': {
                'monte_carlo_simulation': {
                    'enabled': True,
                    'iterations': 10000,
                    'confidence_level': 0.95
                },
                'sensitivity_analysis': {
                    'enabled': True,
                    'variables_to_test': []
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

    def perform_assessment(self, name: str, description: str, category: RiskCategory,
                          initial_probability: float = None, initial_impact: float = None,
                          additional_factors: List[RiskFactor] = None) -> RiskAssessment:
        """Perform a comprehensive risk assessment"""
        start_time = time.time()

        # Collect data
        internal_data = self.data_collector.collect_internal_data()
        external_data = self.data_collector.collect_external_data()

        # Calculate derived factors
        derived_factors = self.data_collector.calculate_derived_factors(internal_data, external_data)

        # Combine factors
        all_factors = derived_factors[:]
        if additional_factors:
            all_factors.extend(additional_factors)

        # Use provided values or calculate from factors
        if initial_probability is not None and initial_impact is not None:
            base_probability = initial_probability
            base_impact = initial_impact
        else:
            # Calculate from factors if no initial values provided
            if all_factors:
                prob_sum = sum(f.probability * f.weight for f in all_factors)
                impact_sum = sum(f.impact * f.weight for f in all_factors)
                total_weight = sum(f.weight for f in all_factors)

                base_probability = prob_sum / total_weight if total_weight > 0 else 0.1
                base_impact = impact_sum / total_weight if total_weight > 0 else 0.1
            else:
                base_probability = 0.1
                base_impact = 0.1

        # Calculate risk score
        score = self.calculator.calculate_risk_score(base_probability, base_impact, all_factors)
        level = self.calculator.calculate_risk_level(score)

        # Determine treatment based on level
        if level == RiskLevel.CRITICAL or level == RiskLevel.HIGH:
            treatment = RiskTreatment.MITIGATE
            treatment_plan = f"Implement comprehensive mitigation plan for high-risk {name}"
        elif level == RiskLevel.MEDIUM:
            treatment = RiskTreatment.MONITOR
            treatment_plan = f"Monitor risk {name} quarterly and implement controls if it increases"
        else:
            treatment = RiskTreatment.ACCEPT
            treatment_plan = f"Accept low-level risk {name} with routine monitoring"

        # Generate mitigation actions based on factors
        mitigation_actions = self._generate_mitigation_actions(all_factors, level)

        # Create assessment
        assessment = RiskAssessment(
            id=self._generate_assessment_id(name),
            name=name,
            description=description,
            category=category,
            level=level,
            probability=base_probability,
            impact=base_impact,
            score=score,
            factors=all_factors,
            treatment=treatment,
            treatment_plan=treatment_plan,
            mitigation_actions=mitigation_actions,
            status="assessed",
            created_at=time.time(),
            updated_at=time.time()
        )

        # Save to store
        self.store.save_assessment(assessment)

        print(f"Completed risk assessment for '{name}' (Level: {level.name}, Score: {score:.2f})")

        return assessment

    def _generate_mitigation_actions(self, factors: List[RiskFactor], level: RiskLevel) -> List[str]:
        """Generate appropriate mitigation actions based on risk factors and level"""
        actions = []

        # Financial risk actions
        financial_factors = [f for f in factors if f.category == RiskCategory.FINANCIAL]
        if financial_factors:
            avg_prob = sum(f.probability for f in financial_factors) / len(financial_factors)
            if avg_prob > 0.5:
                actions.append("Implement enhanced financial controls")
                actions.append("Establish stronger credit policies")

        # Technology risk actions
        tech_factors = [f for f in factors if f.category == RiskCategory.TECHNOLOGY]
        if tech_factors:
            avg_impact = sum(f.impact for f in tech_factors) / len(tech_factors)
            if avg_impact > 0.5:
                actions.append("Upgrade security infrastructure")
                actions.append("Implement multi-factor authentication")

        # Operational risk actions
        op_factors = [f for f in factors if f.category == RiskCategory.OPERATIONAL]
        if op_factors:
            avg_prob = sum(f.probability for f in op_factors) / len(op_factors)
            if avg_prob > 0.3:
                actions.append("Streamline operational processes")
                actions.append("Implement backup procedures")

        # Generic actions based on level
        if level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            actions.extend([
                "Develop detailed risk response plan",
                "Assign dedicated risk owner",
                "Increase monitoring frequency"
            ])
        elif level == RiskLevel.MEDIUM:
            actions.extend([
                "Document risk in register",
                "Review quarterly",
                "Consider control implementation"
            ])

        return actions

    def _generate_assessment_id(self, name: str) -> str:
        """Generate a unique assessment ID"""
        content = f"{name}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def update_assessment_status(self, assessment_id: str, status: str):
        """Update the status of an assessment"""
        assessment = self.store.get_assessment(assessment_id)
        if assessment:
            assessment.status = status
            assessment.updated_at = time.time()
            self.store.save_assessment(assessment)
            print(f"Updated assessment {assessment_id} status to {status}")

    def get_top_risks(self, limit: int = 10) -> List[RiskAssessment]:
        """Get the top risks by score"""
        all_assessments = self.store.get_all_assessments()
        return sorted(all_assessments, key=lambda x: x.score, reverse=True)[:limit]

    def perform_quantitative_analysis(self, assessment_id: str) -> Dict[str, Any]:
        """Perform quantitative analysis using Monte Carlo simulation"""
        assessment = self.store.get_assessment(assessment_id)
        if not assessment:
            return {}

        # Get config parameters
        mc_config = self.config.get('assessment_methods', {}).get('monte_carlo_simulation', {})
        if not mc_config.get('enabled', False):
            return {}

        iterations = mc_config.get('iterations', 10000)
        variance_factor = 0.1  # Fixed variance for demo

        results = self.calculator.perform_monte_carlo_simulation(
            iterations,
            assessment.probability,
            assessment.impact,
            variance_factor
        )

        print(f"Quantitative analysis for {assessment.name}:")
        print(f"  Mean Risk Score: {results['mean']:.3f}")
        print(f"  Std Deviation: {results['std']:.3f}")
        print(f"  5th Percentile: {results['percentiles'][5]:.3f}")
        print(f"  95th Percentile: {results['percentiles'][95]:.3f}")

        return results

    def get_risk_dashboard_data(self) -> Dict[str, Any]:
        """Get data for risk dashboard"""
        all_assessments = self.store.get_all_assessments()

        # Count by category
        category_counts = {}
        level_counts = {}
        total_score = 0

        for assessment in all_assessments:
            cat = assessment.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

            level = assessment.level.name
            level_counts[level] = level_counts.get(level, 0) + 1

            total_score += assessment.score

        avg_score = total_score / len(all_assessments) if all_assessments else 0

        # Top risks
        top_risks = self.get_top_risks(5)

        return {
            'total_assessments': len(all_assessments),
            'average_risk_score': avg_score,
            'by_category': category_counts,
            'by_level': level_counts,
            'top_risks': [asdict(risk) for risk in top_risks]
        }

    async def run_continuous(self):
        """Run the risk assessor continuously"""
        self.running = True
        print("Starting risk assessor...")

        while self.running:
            # Perform any periodic risk monitoring tasks
            # In a real implementation, this might check for new risk indicators
            await asyncio.sleep(3600)  # Check every hour

        print("Risk assessor stopped")

    def stop(self):
        """Stop the risk assessor"""
        self.running = False
        self.executor.shutdown(wait=True)


def main():
    """Main entry point for the risk assessor"""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Risk Assessment Service")
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with sample assessments')

    args = parser.parse_args()

    # Initialize risk assessor
    assessor = RiskAssessor(args.config)

    if args.test_mode:
        print("Creating sample risk assessments...")

        # Create a financial risk assessment
        financial_risk = assessor.perform_assessment(
            name="Market Volatility Risk",
            description="Risk of losses due to market price fluctuations",
            category=RiskCategory.FINANCIAL,
            initial_probability=0.3,
            initial_impact=0.6
        )

        # Create an operational risk assessment
        operational_risk = assessor.perform_assessment(
            name="System Downtime Risk",
            description="Risk of business disruption due to system failures",
            category=RiskCategory.OPERATIONAL,
            initial_probability=0.2,
            initial_impact=0.8
        )

        # Create a technology risk assessment
        tech_risk = assessor.perform_assessment(
            name="Cybersecurity Risk",
            description="Risk of data breaches and cyber attacks",
            category=RiskCategory.TECHNOLOGY,
            initial_probability=0.4,
            initial_impact=0.9
        )

        print(f"Created {financial_risk.name}, {operational_risk.name}, {tech_risk.name}")

        # Perform quantitative analysis on the highest risk
        top_risks = assessor.get_top_risks(1)
        if top_risks:
            analysis = assessor.perform_quantitative_analysis(top_risks[0].id)
            print(f"Quantitative analysis completed for {top_risks[0].name}")

        # Display dashboard data
        dashboard_data = assessor.get_risk_dashboard_data()
        print(f"\nRisk Dashboard:")
        print(f"Total Assessments: {dashboard_data['total_assessments']}")
        print(f"Average Risk Score: {dashboard_data['average_risk_score']:.2f}")
        print(f"By Category: {dashboard_data['by_category']}")
        print(f"By Level: {dashboard_data['by_level']}")
        print(f"Top Risk: {dashboard_data['top_risks'][0]['name'] if dashboard_data['top_risks'] else 'None'}")

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        assessor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the assessor
    try:
        asyncio.run(assessor.run_continuous())
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()