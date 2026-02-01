#!/usr/bin/env python3
"""
ProjectTracker: Tracks project progress, milestones, and key metrics.

This module provides comprehensive project tracking capabilities, including
milestone tracking, progress monitoring, resource allocation, and performance
analytics.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import threading
import logging
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class ProjectStatus(Enum):
    """Project status values."""
    PLANNING = "planning"
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    DELAYED = "delayed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MilestoneStatus(Enum):
    """Milestone status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Task status values."""
    NOT_STARTED = "not_started"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Project:
    """Represents a project."""
    id: str
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    status: ProjectStatus = ProjectStatus.PLANNING
    owner: str = ""
    team_members: List[str] = field(default_factory=list)
    budget: float = 0.0
    spent_budget: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None


@dataclass
class Milestone:
    """Represents a project milestone."""
    id: str
    project_id: str
    name: str
    description: str
    due_date: datetime
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    completed_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None


@dataclass
class Task:
    """Represents a project task."""
    id: str
    project_id: str
    milestone_id: Optional[str] = None
    name: str = ""
    description: str = ""
    assignee: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: int = 2  # 1=low, 2=medium, 3=high, 4=critical
    estimated_effort: Optional[int] = None  # in hours
    actual_effort: Optional[int] = None  # in hours
    dependencies: List[str] = field(default_factory=list)  # Task IDs this task depends on
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None


@dataclass
class ProjectMetric:
    """Represents a project metric."""
    id: str
    project_id: str
    metric_name: str
    metric_value: float
    unit: str
    recorded_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None


class ProjectTracker:
    """
    Comprehensive project tracking system with milestone, task, and metric tracking.

    Features:
    - Project lifecycle management
    - Milestone tracking and monitoring
    - Task assignment and progress tracking
    - Resource allocation and budget tracking
    - Performance metrics and analytics
    - Team collaboration and communication
    """

    def __init__(self, db_path: str = "./projects.db"):
        self.db_path = db_path
        self.setup_database()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('project_tracker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Initialize the database schema for project tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                start_date DATETIME,
                end_date DATETIME,
                status TEXT,
                owner TEXT,
                team_members_json TEXT,
                budget REAL,
                spent_budget REAL,
                created_at DATETIME,
                updated_at DATETIME,
                notes TEXT
            )
        ''')

        # Create milestones table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS milestones (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                due_date DATETIME,
                status TEXT,
                completed_date DATETIME,
                created_at DATETIME,
                updated_at DATETIME,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')

        # Create tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                milestone_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                assignee TEXT,
                start_date DATETIME,
                due_date DATETIME,
                status TEXT,
                priority INTEGER,
                estimated_effort INTEGER,
                actual_effort INTEGER,
                dependencies_json TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (milestone_id) REFERENCES milestones (id)
            )
        ''')

        # Create metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                unit TEXT,
                recorded_at DATETIME,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')

        # Create project updates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                update_text TEXT,
                author TEXT,
                created_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_project(self, name: str, description: str, start_date: datetime,
                      end_date: datetime, owner: str = "", budget: float = 0.0) -> str:
        """Create a new project."""
        project = Project(
            id=str(uuid4()),
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            owner=owner,
            budget=budget
        )

        self._save_project_to_db(project)
        self.logger.info(f"Created project '{name}' (ID: {project.id})")
        return project.id

    def _save_project_to_db(self, project: Project) -> None:
        """Save project to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO projects
            (id, name, description, start_date, end_date, status, owner,
             team_members_json, budget, spent_budget, created_at, updated_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project.id, project.name, project.description,
            project.start_date.isoformat(), project.end_date.isoformat(),
            project.status.value, project.owner,
            json.dumps(project.team_members), project.budget,
            project.spent_budget, project.created_at.isoformat(),
            project.updated_at.isoformat(), project.notes
        ))

        conn.commit()
        conn.close()

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a project by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, start_date, end_date, status, owner,
                   team_members_json, budget, spent_budget, created_at, updated_at, notes
            FROM projects WHERE id = ?
        ''', (project_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Project(
            id=row[0], name=row[1], description=row[2],
            start_date=datetime.fromisoformat(row[3]),
            end_date=datetime.fromisoformat(row[4]),
            status=ProjectStatus(row[5]), owner=row[6],
            team_members=json.loads(row[7]) if row[7] else [],
            budget=row[8], spent_budget=row[9],
            created_at=datetime.fromisoformat(row[10]),
            updated_at=datetime.fromisoformat(row[11]),
            notes=row[12]
        )

    def update_project(self, project_id: str, **kwargs) -> bool:
        """Update project attributes."""
        project = self.get_project(project_id)
        if not project:
            return False

        # Update project attributes based on provided kwargs
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)

        project.updated_at = datetime.now()
        self._save_project_to_db(project)
        return True

    def add_team_member(self, project_id: str, member_email: str) -> bool:
        """Add a team member to a project."""
        project = self.get_project(project_id)
        if not project:
            return False

        if member_email not in project.team_members:
            project.team_members.append(member_email)
            project.updated_at = datetime.now()
            self._save_project_to_db(project)
            self.logger.info(f"Added team member '{member_email}' to project '{project.name}'")

        return True

    def create_milestone(self, project_id: str, name: str, description: str,
                         due_date: datetime) -> str:
        """Create a new milestone for a project."""
        milestone = Milestone(
            id=str(uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            due_date=due_date
        )

        self._save_milestone_to_db(milestone)
        self.logger.info(f"Created milestone '{name}' for project '{project_id}'")
        return milestone.id

    def _save_milestone_to_db(self, milestone: Milestone) -> None:
        """Save milestone to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO milestones
            (id, project_id, name, description, due_date, status,
             completed_date, created_at, updated_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            milestone.id, milestone.project_id, milestone.name,
            milestone.description, milestone.due_date.isoformat(),
            milestone.status.value,
            milestone.completed_date.isoformat() if milestone.completed_date else None,
            milestone.created_at.isoformat(), milestone.updated_at.isoformat(),
            milestone.notes
        ))

        conn.commit()
        conn.close()

    def get_milestones(self, project_id: str) -> List[Milestone]:
        """Get all milestones for a project."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, project_id, name, description, due_date, status,
                   completed_date, created_at, updated_at, notes
            FROM milestones WHERE project_id = ?
            ORDER BY due_date
        ''', (project_id,))

        milestones = []
        for row in cursor.fetchall():
            milestones.append(Milestone(
                id=row[0], project_id=row[1], name=row[2], description=row[3],
                due_date=datetime.fromisoformat(row[4]),
                status=MilestoneStatus(row[5]),
                completed_date=datetime.fromisoformat(row[6]) if row[6] else None,
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
                notes=row[9]
            ))

        conn.close()
        return milestones

    def create_task(self, project_id: str, name: str, description: str = "",
                    assignee: Optional[str] = None, due_date: Optional[datetime] = None,
                    priority: int = 2, estimated_effort: Optional[int] = None,
                    milestone_id: Optional[str] = None) -> str:
        """Create a new task for a project."""
        task = Task(
            id=str(uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            assignee=assignee,
            due_date=due_date,
            priority=priority,
            estimated_effort=estimated_effort,
            milestone_id=milestone_id
        )

        self._save_task_to_db(task)
        self.logger.info(f"Created task '{name}' for project '{project_id}'")
        return task.id

    def _save_task_to_db(self, task: Task) -> None:
        """Save task to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tasks
            (id, project_id, milestone_id, name, description, assignee,
             start_date, due_date, status, priority, estimated_effort,
             actual_effort, dependencies_json, created_at, updated_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id, task.project_id, task.milestone_id, task.name,
            task.description, task.assignee,
            task.start_date.isoformat() if task.start_date else None,
            task.due_date.isoformat() if task.due_date else None,
            task.status.value, task.priority, task.estimated_effort,
            task.actual_effort, json.dumps(task.dependencies),
            task.created_at.isoformat(), task.updated_at.isoformat(),
            task.notes
        ))

        conn.commit()
        conn.close()

    def get_tasks(self, project_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks for a project, optionally filtered by status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT id, project_id, milestone_id, name, description, assignee,
                   start_date, due_date, status, priority, estimated_effort,
                   actual_effort, dependencies_json, created_at, updated_at, notes
            FROM tasks WHERE project_id = ?
        '''

        params = [project_id]
        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY priority DESC, due_date"

        cursor.execute(query, params)

        tasks = []
        for row in cursor.fetchall():
            tasks.append(Task(
                id=row[0], project_id=row[1], milestone_id=row[2],
                name=row[3], description=row[4], assignee=row[5],
                start_date=datetime.fromisoformat(row[6]) if row[6] else None,
                due_date=datetime.fromisoformat(row[7]) if row[7] else None,
                status=TaskStatus(row[8]), priority=row[9],
                estimated_effort=row[10], actual_effort=row[11],
                dependencies=json.loads(row[12]) if row[12] else [],
                created_at=datetime.fromisoformat(row[13]),
                updated_at=datetime.fromisoformat(row[14]),
                notes=row[15]
            ))

        conn.close()
        return tasks

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update the status of a task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tasks SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (status.value, datetime.now().isoformat(), task_id))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            self.logger.info(f"Updated task '{task_id}' status to {status.value}")

            # If task is completed, update the milestone if needed
            if status == TaskStatus.COMPLETED:
                self._update_milestone_progress(task_id)

        return rows_affected > 0

    def _update_milestone_progress(self, task_id: str) -> None:
        """Update milestone progress based on task completion."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the milestone ID for this task
        cursor.execute('SELECT milestone_id FROM tasks WHERE id = ?', (task_id,))
        result = cursor.fetchone()

        if result and result[0]:
            milestone_id = result[0]

            # Count total and completed tasks for this milestone
            cursor.execute('''
                SELECT COUNT(*) FROM tasks
                WHERE milestone_id = ? AND status != ?
            ''', (milestone_id, TaskStatus.COMPLETED.value))

            incomplete_count = cursor.fetchone()[0]

            if incomplete_count == 0:
                # All tasks for this milestone are completed
                cursor.execute('''
                    UPDATE milestones
                    SET status = ?, completed_date = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    MilestoneStatus.COMPLETED.value,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    milestone_id
                ))

                conn.commit()
                self.logger.info(f"Milestone '{milestone_id}' marked as completed")

        conn.close()

    def record_metric(self, project_id: str, metric_name: str, metric_value: float,
                      unit: str = "", notes: Optional[str] = None) -> str:
        """Record a project metric."""
        metric = ProjectMetric(
            id=str(uuid4()),
            project_id=project_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit,
            notes=notes
        )

        self._save_metric_to_db(metric)
        self.logger.info(f"Recorded metric '{metric_name}' ({metric_value}{unit}) for project '{project_id}'")
        return metric.id

    def _save_metric_to_db(self, metric: ProjectMetric) -> None:
        """Save metric to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO metrics
            (id, project_id, metric_name, metric_value, unit, recorded_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.id, metric.project_id, metric.metric_name,
            metric.metric_value, metric.unit,
            metric.recorded_at.isoformat(), metric.notes
        ))

        conn.commit()
        conn.close()

    def get_project_metrics(self, project_id: str, metric_name: Optional[str] = None) -> List[ProjectMetric]:
        """Get metrics for a project, optionally filtered by name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT id, project_id, metric_name, metric_value, unit, recorded_at, notes FROM metrics WHERE project_id = ?"
        params = [project_id]

        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)

        query += " ORDER BY recorded_at DESC"

        cursor.execute(query, params)

        metrics = []
        for row in cursor.fetchall():
            metrics.append(ProjectMetric(
                id=row[0], project_id=row[1], metric_name=row[2],
                metric_value=row[3], unit=row[4],
                recorded_at=datetime.fromisoformat(row[5]),
                notes=row[6]
            ))

        conn.close()
        return metrics

    def get_project_health_score(self, project_id: str) -> Dict[str, Any]:
        """Calculate and return project health score based on various metrics."""
        project = self.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        # Calculate health factors
        milestones = self.get_milestones(project_id)
        tasks = self.get_tasks(project_id)

        # Calculate milestone health (0-100 scale)
        milestone_count = len(milestones)
        completed_milestones = len([m for m in milestones if m.status == MilestoneStatus.COMPLETED])
        milestone_health = (completed_milestones / milestone_count * 100) if milestone_count > 0 else 100

        # Calculate task health (0-100 scale)
        task_count = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        task_health = (completed_tasks / task_count * 100) if task_count > 0 else 100

        # Calculate schedule health (0-100 scale)
        days_total = (project.end_date - project.start_date).days
        days_elapsed = (datetime.now() - project.start_date).days
        expected_progress = (days_elapsed / days_total * 100) if days_total > 0 else 0
        actual_progress = task_health  # Using task completion as proxy for progress
        schedule_variance = actual_progress - expected_progress
        schedule_health = max(0, min(100, 100 - abs(schedule_variance)))

        # Calculate budget health (0-100 scale)
        budget_utilization = (project.spent_budget / project.budget * 100) if project.budget > 0 else 0
        budget_health = max(0, min(100, 100 - (budget_utilization - 100) * 2))  # Extra penalty for exceeding budget

        # Overall health score (weighted average)
        overall_health = (
            milestone_health * 0.3 +
            task_health * 0.3 +
            schedule_health * 0.2 +
            budget_health * 0.2
        )

        return {
            "overall_health": round(overall_health, 2),
            "milestone_health": round(milestone_health, 2),
            "task_health": round(task_health, 2),
            "schedule_health": round(schedule_health, 2),
            "budget_health": round(budget_health, 2),
            "metrics": {
                "total_milestones": milestone_count,
                "completed_milestones": completed_milestones,
                "total_tasks": task_count,
                "completed_tasks": completed_tasks,
                "budget_utilization": f"{budget_utilization:.2f}%",
                "project_duration": f"{days_total} days",
                "days_elapsed": days_elapsed
            }
        }

    def add_project_update(self, project_id: str, update_text: str, author: str) -> bool:
        """Add a project update/status report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO project_updates
            (project_id, update_text, author, created_at)
            VALUES (?, ?, ?, ?)
        ''', (project_id, update_text, author, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        self.logger.info(f"Added project update for project '{project_id}' by '{author}'")
        return True

    def get_project_updates(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent project updates."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT update_text, author, created_at
            FROM project_updates
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (project_id, limit))

        updates = []
        for row in cursor.fetchall():
            updates.append({
                "update_text": row[0],
                "author": row[1],
                "created_at": datetime.fromisoformat(row[2])
            })

        conn.close()
        return updates

    def get_overdue_items(self) -> List[Dict[str, Any]]:
        """Get all overdue milestones and tasks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get overdue milestones
        cursor.execute('''
            SELECT m.name, m.project_id, p.name as project_name, m.due_date
            FROM milestones m
            JOIN projects p ON m.project_id = p.id
            WHERE m.status != ? AND m.due_date < ?
        ''', (MilestoneStatus.COMPLETED.value, datetime.now().isoformat()))

        overdue_milestones = []
        for row in cursor.fetchall():
            overdue_milestones.append({
                "type": "milestone",
                "name": row[0],
                "project_id": row[1],
                "project_name": row[2],
                "due_date": datetime.fromisoformat(row[3])
            })

        # Get overdue tasks
        cursor.execute('''
            SELECT t.name, t.project_id, p.name as project_name, t.due_date, t.assignee
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.status NOT IN (?, ?, ?) AND t.due_date IS NOT NULL AND t.due_date < ?
        ''', (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value, TaskStatus.BLOCKED.value,
              datetime.now().isoformat()))

        overdue_tasks = []
        for row in cursor.fetchall():
            overdue_tasks.append({
                "type": "task",
                "name": row[0],
                "project_id": row[1],
                "project_name": row[2],
                "due_date": datetime.fromisoformat(row[3]),
                "assignee": row[4]
            })

        conn.close()
        return overdue_milestones + overdue_tasks


def main():
    """Main function for running the project tracker."""
    import argparse

    parser = argparse.ArgumentParser(description='Project Tracker')
    parser.add_argument('--db-path', default='./projects.db', help='Path to database file')
    parser.add_argument('--demo', action='store_true', help='Run demonstration')

    args = parser.parse_args()

    tracker = ProjectTracker(db_path=args.db_path)

    if args.demo:
        # Create a demo project
        project_id = tracker.create_project(
            name="Website Redesign Project",
            description="Complete redesign of company website",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=90),
            owner="project.manager@company.com",
            budget=50000.0
        )

        print(f"Created project: Website Redesign (ID: {project_id})")

        # Add team members
        tracker.add_team_member(project_id, "designer@company.com")
        tracker.add_team_member(project_id, "developer@company.com")
        tracker.add_team_member(project_id, "qa@company.com")

        # Create milestones
        milestone1_id = tracker.create_milestone(
            project_id=project_id,
            name="Design Phase Complete",
            description="Complete wireframes and mockups",
            due_date=datetime.now() + timedelta(days=20)
        )

        milestone2_id = tracker.create_milestone(
            project_id=project_id,
            name="Development Complete",
            description="Complete front-end and back-end development",
            due_date=datetime.now() + timedelta(days=60)
        )

        milestone3_id = tracker.create_milestone(
            project_id=project_id,
            name="Launch Ready",
            description="Site ready for production launch",
            due_date=datetime.now() + timedelta(days=85)
        )

        print(f"Created 3 milestones for project")

        # Create tasks
        tracker.create_task(
            project_id=project_id,
            name="Create homepage mockup",
            description="Design homepage layout and user flow",
            assignee="designer@company.com",
            due_date=datetime.now() + timedelta(days=10),
            priority=3,
            estimated_effort=16,
            milestone_id=milestone1_id
        )

        tracker.create_task(
            project_id=project_id,
            name="Implement homepage",
            description="Develop homepage HTML/CSS/JS",
            assignee="developer@company.com",
            due_date=datetime.now() + timedelta(days=25),
            priority=3,
            estimated_effort=24,
            milestone_id=milestone2_id
        )

        tracker.create_task(
            project_id=project_id,
            name="QA Testing",
            description="Test all website functionality",
            assignee="qa@company.com",
            due_date=datetime.now() + timedelta(days=75),
            priority=4,
            estimated_effort=40,
            milestone_id=milestone3_id
        )

        print(f"Created 3 tasks for project")

        # Record some metrics
        tracker.record_metric(project_id, "tasks_completed", 1, "count", "Initial task completed")
        tracker.record_metric(project_id, "budget_spent", 15000, "USD", "Initial development costs")

        # Add a project update
        tracker.add_project_update(
            project_id,
            "Project initiated successfully. Design phase underway.",
            "project.manager@company.com"
        )

        # Get project health
        health = tracker.get_project_health_score(project_id)
        print(f"\nProject Health Score: {health['overall_health']}/100")
        print(f"Milestones: {health['metrics']['completed_milestones']}/{health['metrics']['total_milestones']} completed")
        print(f"Tasks: {health['metrics']['completed_tasks']}/{health['metrics']['total_tasks']} completed")

        # Show overdue items (should be none in this example)
        overdue = tracker.get_overdue_items()
        print(f"\nOverdue items: {len(overdue)}")

    else:
        print("Project tracker initialized. Use the API to track projects.")


if __name__ == "__main__":
    main()