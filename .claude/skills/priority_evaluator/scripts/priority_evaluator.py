#!/usr/bin/env python3
"""
PriorityEvaluator: Evaluates and ranks tasks based on business rules and impact assessment.

This module provides sophisticated priority evaluation capabilities using multiple
scoring frameworks and contextual factors to determine the optimal priority order
for tasks, projects, and initiatives.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import math
import logging
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class PriorityLevel(Enum):
    """Priority levels for evaluated items."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


class ItemType(Enum):
    """Types of items that can be prioritized."""
    TASK = "task"
    PROJECT = "project"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    INCIDENT = "incident"
    OPPORTUNITY = "opportunity"


@dataclass
class PriorityItem:
    """Represents an item to be prioritized."""
    id: str
    name: str
    description: str
    item_type: ItemType
    created_at: datetime = field(default_factory=datetime.now)

    # Impact Assessment
    business_impact: float = 0.0  # 0.0-10.0 scale
    user_impact: float = 0.0      # 0.0-10.0 scale
    strategic_alignment: float = 0.0  # 0.0-10.0 scale

    # Effort Assessment
    implementation_complexity: float = 0.0  # 0.0-10.0 scale (inverse)
    resource_requirements: float = 0.0      # 0.0-10.0 scale (inverse)
    risk_factor: float = 0.0                # 0.0-10.0 scale (inverse)

    # Urgency Assessment
    time_sensitivity: float = 0.0           # 0.0-10.0 scale
    dependency_impact: float = 0.0          # 0.0-10.0 scale
    opportunity_window: float = 0.0         # 0.0-10.0 scale

    # Contextual factors
    stakeholder_importance: float = 0.0     # 0.0-10.0 scale
    resource_availability: float = 0.0      # 0.0-10.0 scale
    strategic_timing: float = 0.0           # 0.0-10.0 scale

    # Calculated values
    calculated_score: float = 0.0
    priority_level: PriorityLevel = PriorityLevel.MINIMAL
    evaluator_notes: Optional[str] = None
    evaluation_timestamp: Optional[datetime] = None


class PriorityEvaluator:
    """
    Sophisticated priority evaluation system using multiple scoring frameworks.

    Features:
    - Multi-dimensional scoring across impact, effort, and urgency
    - Weighted scoring based on organizational context
    - Dynamic adjustment for situational factors
    - Historical performance tracking
    - Stakeholder influence modeling
    """

    def __init__(self, db_path: str = "./priorities.db"):
        self.db_path = db_path
        self.setup_database()

        # Default weights for scoring model
        self.weights = {
            'impact': 0.50,  # Business impact, user impact, strategic alignment
            'effort': 0.30,  # Inverse of complexity, resources, risk
            'urgency': 0.20  # Time sensitivity, dependencies, opportunity
        }

        # Impact sub-weights
        self.impact_weights = {
            'business_impact': 0.50,
            'user_impact': 0.30,
            'strategic_alignment': 0.20
        }

        # Effort sub-weights (inverted)
        self.effort_weights = {
            'implementation_complexity': 0.40,
            'resource_requirements': 0.35,
            'risk_factor': 0.25
        }

        # Urgency sub-weights
        self.urgency_weights = {
            'time_sensitivity': 0.50,
            'dependency_impact': 0.30,
            'opportunity_window': 0.20
        }

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('priority_evaluator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Initialize the database schema for priority tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create priority_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS priority_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                item_type TEXT,
                created_at DATETIME,

                -- Impact Assessment
                business_impact REAL,
                user_impact REAL,
                strategic_alignment REAL,

                -- Effort Assessment
                implementation_complexity REAL,
                resource_requirements REAL,
                risk_factor REAL,

                -- Urgency Assessment
                time_sensitivity REAL,
                dependency_impact REAL,
                opportunity_window REAL,

                -- Contextual factors
                stakeholder_importance REAL,
                resource_availability REAL,
                strategic_timing REAL,

                -- Calculated values
                calculated_score REAL,
                priority_level INTEGER,
                evaluator_notes TEXT,
                evaluation_timestamp DATETIME
            )
        ''')

        # Create evaluation_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                evaluation_data_json TEXT,
                calculated_score REAL,
                priority_level INTEGER,
                evaluator_notes TEXT,
                evaluation_timestamp DATETIME,
                FOREIGN KEY (item_id) REFERENCES priority_items (id)
            )
        ''')

        # Create priority_decisions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS priority_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item1_id TEXT,
                item2_id TEXT,
                preferred_item_id TEXT,
                reason TEXT,
                decision_maker TEXT,
                decision_timestamp DATETIME,
                FOREIGN KEY (item1_id) REFERENCES priority_items (id),
                FOREIGN KEY (item2_id) REFERENCES priority_items (id),
                FOREIGN KEY (preferred_item_id) REFERENCES priority_items (id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_item(self, item: PriorityItem) -> str:
        """Add an item to be evaluated."""
        self._save_item_to_db(item)
        self.logger.info(f"Added item '{item.name}' (ID: {item.id}) for evaluation")
        return item.id

    def _save_item_to_db(self, item: PriorityItem) -> None:
        """Save item to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO priority_items
            (id, name, description, item_type, created_at,
             business_impact, user_impact, strategic_alignment,
             implementation_complexity, resource_requirements, risk_factor,
             time_sensitivity, dependency_impact, opportunity_window,
             stakeholder_importance, resource_availability, strategic_timing,
             calculated_score, priority_level, evaluator_notes, evaluation_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id, item.name, item.description, item.item_type.value,
            item.created_at.isoformat(),
            item.business_impact, item.user_impact, item.strategic_alignment,
            item.implementation_complexity, item.resource_requirements, item.risk_factor,
            item.time_sensitivity, item.dependency_impact, item.opportunity_window,
            item.stakeholder_importance, item.resource_availability, item.strategic_timing,
            item.calculated_score, item.priority_level.value,
            item.evaluator_notes, item.evaluation_timestamp.isoformat() if item.evaluation_timestamp else None
        ))

        conn.commit()
        conn.close()

    def evaluate_item(self, item_id: str) -> PriorityItem:
        """Evaluate a single item and return the evaluated item."""
        item = self.get_item(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")

        # Calculate the priority score
        score = self._calculate_priority_score(item)

        # Determine priority level based on score
        priority_level = self._score_to_priority_level(score)

        # Update the item with calculated values
        item.calculated_score = score
        item.priority_level = priority_level
        item.evaluation_timestamp = datetime.now()

        # Save updated item
        self._save_item_to_db(item)

        # Save to evaluation history
        self._save_evaluation_to_history(item)

        self.logger.info(f"Evaluated item '{item.name}' (ID: {item.id}), Score: {score:.2f}, Priority: {priority_level.name}")
        return item

    def _calculate_priority_score(self, item: PriorityItem) -> float:
        """Calculate priority score using weighted formula."""
        # Calculate impact score
        impact_score = (
            item.business_impact * self.impact_weights['business_impact'] +
            item.user_impact * self.impact_weights['user_impact'] +
            item.strategic_alignment * self.impact_weights['strategic_alignment']
        )

        # Calculate effort score (inverted - lower effort = higher score)
        effort_score = (
            (10 - item.implementation_complexity) * self.effort_weights['implementation_complexity'] +
            (10 - item.resource_requirements) * self.effort_weights['resource_requirements'] +
            (10 - item.risk_factor) * self.effort_weights['risk_factor']
        )

        # Calculate urgency score
        urgency_score = (
            item.time_sensitivity * self.urgency_weights['time_sensitivity'] +
            item.dependency_impact * self.urgency_weights['dependency_impact'] +
            item.opportunity_window * self.urgency_weights['opportunity_window']
        )

        # Apply main weights
        total_score = (
            impact_score * self.weights['impact'] +
            effort_score * self.weights['effort'] +
            urgency_score * self.weights['urgency']
        )

        # Apply contextual adjustments
        context_multiplier = 1.0

        # Stakeholder importance adjustment
        if item.stakeholder_importance > 7.0:
            context_multiplier *= 1.2
        elif item.stakeholder_importance > 5.0:
            context_multiplier *= 1.1

        # Resource availability adjustment
        if item.resource_availability > 8.0:
            context_multiplier *= 1.15
        elif item.resource_availability < 4.0:
            context_multiplier *= 0.85

        # Strategic timing adjustment
        if item.strategic_timing > 8.0:
            context_multiplier *= 1.25
        elif item.strategic_timing < 3.0:
            context_multiplier *= 0.9

        final_score = total_score * context_multiplier

        # Ensure score is within bounds
        return max(0.0, min(10.0, final_score))

    def _score_to_priority_level(self, score: float) -> PriorityLevel:
        """Convert numeric score to priority level."""
        if score >= 8.5:
            return PriorityLevel.CRITICAL
        elif score >= 7.0:
            return PriorityLevel.HIGH
        elif score >= 5.0:
            return PriorityLevel.MEDIUM
        elif score >= 3.0:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.MINIMAL

    def _save_evaluation_to_history(self, item: PriorityItem) -> None:
        """Save evaluation results to history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO evaluation_history
            (item_id, evaluation_data_json, calculated_score, priority_level,
             evaluator_notes, evaluation_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            item.id,
            json.dumps({
                'business_impact': item.business_impact,
                'user_impact': item.user_impact,
                'strategic_alignment': item.strategic_alignment,
                'implementation_complexity': item.implementation_complexity,
                'resource_requirements': item.resource_requirements,
                'risk_factor': item.risk_factor,
                'time_sensitivity': item.time_sensitivity,
                'dependency_impact': item.dependency_impact,
                'opportunity_window': item.opportunity_window,
                'stakeholder_importance': item.stakeholder_importance,
                'resource_availability': item.resource_availability,
                'strategic_timing': item.strategic_timing,
            }),
            item.calculated_score,
            item.priority_level.value,
            item.evaluator_notes,
            item.evaluation_timestamp.isoformat() if item.evaluation_timestamp else None
        ))

        conn.commit()
        conn.close()

    def get_item(self, item_id: str) -> Optional[PriorityItem]:
        """Retrieve an item by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, item_type, created_at,
                   business_impact, user_impact, strategic_alignment,
                   implementation_complexity, resource_requirements, risk_factor,
                   time_sensitivity, dependency_impact, opportunity_window,
                   stakeholder_importance, resource_availability, strategic_timing,
                   calculated_score, priority_level, evaluator_notes, evaluation_timestamp
            FROM priority_items WHERE id = ?
        ''', (item_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return PriorityItem(
            id=row[0], name=row[1], description=row[2],
            item_type=ItemType(row[3]), created_at=datetime.fromisoformat(row[4]),
            business_impact=row[5], user_impact=row[6], strategic_alignment=row[7],
            implementation_complexity=row[8], resource_requirements=row[9], risk_factor=row[10],
            time_sensitivity=row[11], dependency_impact=row[12], opportunity_window=row[13],
            stakeholder_importance=row[14], resource_availability=row[15], strategic_timing=row[16],
            calculated_score=row[17], priority_level=PriorityLevel(row[18]),
            evaluator_notes=row[19],
            evaluation_timestamp=datetime.fromisoformat(row[20]) if row[20] else None
        )

    def evaluate_multiple_items(self, item_ids: List[str]) -> List[PriorityItem]:
        """Evaluate multiple items and return them sorted by priority."""
        evaluated_items = []

        for item_id in item_ids:
            evaluated_item = self.evaluate_item(item_id)
            evaluated_items.append(evaluated_item)

        # Sort by calculated score (descending)
        evaluated_items.sort(key=lambda x: x.calculated_score, reverse=True)

        return evaluated_items

    def get_top_priorities(self, count: int = 10) -> List[PriorityItem]:
        """Get the top N priority items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, item_type, created_at,
                   business_impact, user_impact, strategic_alignment,
                   implementation_complexity, resource_requirements, risk_factor,
                   time_sensitivity, dependency_impact, opportunity_window,
                   stakeholder_importance, resource_availability, strategic_timing,
                   calculated_score, priority_level, evaluator_notes, evaluation_timestamp
            FROM priority_items
            WHERE calculated_score IS NOT NULL
            ORDER BY calculated_score DESC
            LIMIT ?
        ''', (count,))

        items = []
        for row in cursor.fetchall():
            items.append(PriorityItem(
                id=row[0], name=row[1], description=row[2],
                item_type=ItemType(row[3]), created_at=datetime.fromisoformat(row[4]),
                business_impact=row[5], user_impact=row[6], strategic_alignment=row[7],
                implementation_complexity=row[8], resource_requirements=row[9], risk_factor=row[10],
                time_sensitivity=row[11], dependency_impact=row[12], opportunity_window=row[13],
                stakeholder_importance=row[14], resource_availability=row[15], strategic_timing=row[16],
                calculated_score=row[17], priority_level=PriorityLevel(row[18]),
                evaluator_notes=row[19],
                evaluation_timestamp=datetime.fromisoformat(row[20]) if row[20] else None
            ))

        conn.close()
        return items

    def compare_items(self, item1_id: str, item2_id: str,
                     preferred_item_id: str, reason: str,
                     decision_maker: str) -> None:
        """Record a manual comparison decision between two items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO priority_decisions
            (item1_id, item2_id, preferred_item_id, reason, decision_maker, decision_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (item1_id, item2_id, preferred_item_id, reason, decision_maker, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        self.logger.info(f"Recorded manual priority decision: {preferred_item_id} preferred over {item1_id if item1_id != preferred_item_id else item2_id}")

    def get_evaluation_history(self, item_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get evaluation history for an item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT evaluation_data_json, calculated_score, priority_level,
                   evaluator_notes, evaluation_timestamp
            FROM evaluation_history
            WHERE item_id = ?
            ORDER BY evaluation_timestamp DESC
            LIMIT ?
        ''', (item_id, limit))

        history = []
        for row in cursor.fetchall():
            history.append({
                'evaluation_data': json.loads(row[0]),
                'calculated_score': row[1],
                'priority_level': PriorityLevel(row[2]).name,
                'evaluator_notes': row[3],
                'evaluation_timestamp': datetime.fromisoformat(row[4])
            })

        conn.close()
        return history

    def adjust_weights(self, new_weights: Dict[str, float]) -> None:
        """Adjust the scoring weights."""
        # Validate weights sum to 1.0
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        self.weights = new_weights
        self.logger.info(f"Updated priority weights: {new_weights}")

    def get_priority_summary(self) -> Dict[str, Any]:
        """Get a summary of priority distribution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count items by priority level
        cursor.execute('''
            SELECT priority_level, COUNT(*)
            FROM priority_items
            WHERE calculated_score IS NOT NULL
            GROUP BY priority_level
        ''')

        priority_counts = {}
        for row in cursor.fetchall():
            priority_counts[PriorityLevel(row[0]).name] = row[1]

        # Get average scores by item type
        cursor.execute('''
            SELECT item_type, AVG(calculated_score), COUNT(*)
            FROM priority_items
            WHERE calculated_score IS NOT NULL
            GROUP BY item_type
        ''')

        type_scores = {}
        for row in cursor.fetchall():
            type_scores[row[0]] = {
                'avg_score': row[1],
                'count': row[2]
            }

        conn.close()

        return {
            'priority_distribution': priority_counts,
            'average_scores_by_type': type_scores,
            'total_evaluated_items': sum(priority_counts.values())
        }


def main():
    """Main function for running the priority evaluator."""
    import argparse

    parser = argparse.ArgumentParser(description='Priority Evaluator')
    parser.add_argument('--db-path', default='./priorities.db', help='Path to database file')
    parser.add_argument('--demo', action='store_true', help='Run demonstration')

    args = parser.parse_args()

    evaluator = PriorityEvaluator(db_path=args.db_path)

    if args.demo:
        # Create demo items
        demo_items = [
            PriorityItem(
                id=str(uuid4()),
                name="Fix Critical Security Bug",
                description="Address high-severity security vulnerability in authentication system",
                item_type=ItemType.BUG,
                business_impact=9.5,
                user_impact=9.0,
                strategic_alignment=8.0,
                implementation_complexity=7.0,
                resource_requirements=6.0,
                risk_factor=3.0,
                time_sensitivity=10.0,
                dependency_impact=9.0,
                opportunity_window=9.5,
                stakeholder_importance=9.0,
                resource_availability=7.0,
                strategic_timing=8.5
            ),
            PriorityItem(
                id=str(uuid4()),
                name="New Feature Request - Mobile App",
                description="Implement mobile app for customer portal",
                item_type=ItemType.FEATURE_REQUEST,
                business_impact=8.0,
                user_impact=8.5,
                strategic_alignment=9.0,
                implementation_complexity=8.0,
                resource_requirements=7.5,
                risk_factor=5.0,
                time_sensitivity=6.0,
                dependency_impact=4.0,
                opportunity_window=7.0,
                stakeholder_importance=7.5,
                resource_availability=6.0,
                strategic_timing=7.0
            ),
            PriorityItem(
                id=str(uuid4()),
                name="Performance Optimization",
                description="Optimize database queries to improve response times",
                item_type=ItemType.TASK,
                business_impact=7.0,
                user_impact=7.5,
                strategic_alignment=6.0,
                implementation_complexity=6.0,
                resource_requirements=5.0,
                risk_factor=2.0,
                time_sensitivity=5.0,
                dependency_impact=3.0,
                opportunity_window=4.0,
                stakeholder_importance=6.5,
                resource_availability=8.0,
                strategic_timing=5.5
            )
        ]

        print("Adding demo items...")
        item_ids = []
        for item in demo_items:
            item_id = evaluator.add_item(item)
            item_ids.append(item_id)
            print(f"  Added: {item.name} (ID: {item_id})")

        print("\nEvaluating items...")
        evaluated_items = evaluator.evaluate_multiple_items(item_ids)

        print("\nEvaluation Results (sorted by priority):")
        for i, item in enumerate(evaluated_items, 1):
            print(f"{i}. {item.name}")
            print(f"   Score: {item.calculated_score:.2f}")
            print(f"   Priority: {item.priority_level.name}")
            print(f"   Type: {item.item_type.value}")
            print(f"   Business Impact: {item.business_impact}")
            print(f"   User Impact: {item.user_impact}")
            print(f"   Urgency: {item.time_sensitivity}")
            print()

        # Get top priorities
        top_items = evaluator.get_top_priorities(count=5)
        print(f"Top {len(top_items)} Priority Items:")
        for i, item in enumerate(top_items, 1):
            print(f"{i}. {item.name} - Score: {item.calculated_score:.2f} ({item.priority_level.name})")

        # Get summary
        summary = evaluator.get_priority_summary()
        print(f"\nPriority Summary:")
        print(f"Total Evaluated Items: {summary['total_evaluated_items']}")
        print("Distribution by Priority:")
        for level, count in summary['priority_distribution'].items():
            print(f"  {level}: {count}")

    else:
        print("Priority evaluator initialized. Use the API to evaluate items.")


if __name__ == "__main__":
    main()