#!/usr/bin/env python3
"""
TaskScheduler: Schedules and manages recurring and one-time tasks.

This module provides intelligent task scheduling capabilities, including
recurring tasks, dependency management, resource allocation, and priority-based
task execution.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable, Any
import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import heapq
from collections import defaultdict


class Priority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class RecurrenceType(Enum):
    """Types of task recurrence."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class Task:
    """Represents a scheduled task."""
    id: str
    name: str
    description: str
    function: str  # Function name to execute
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    scheduled_time: datetime = field(default_factory=datetime.now)
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    recurrence_interval: Optional[int] = None  # For custom recurrence
    priority: Priority = Priority.MEDIUM
    dependencies: List[str] = field(default_factory=list)  # Task IDs this task depends on
    max_duration: Optional[timedelta] = None  # Maximum allowed execution time
    notify_on_completion: bool = False
    notify_on_failure: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.SCHEDULED
    result: Optional[Any] = None
    error_message: Optional[str] = None
    assigned_resources: List[str] = field(default_factory=list)
    estimated_duration: Optional[timedelta] = None


@dataclass
class ScheduledTask:
    """Task wrapper for scheduling queue."""
    scheduled_time: datetime
    priority: int
    task_id: str
    task: Task

    def __lt__(self, other):
        # Earlier times have higher priority
        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        # Higher priority numbers come first
        return self.priority > other.priority


class TaskScheduler:
    """
    Intelligent task scheduler with support for recurring tasks, dependencies, and resource management.

    Features:
    - Priority-based task execution
    - Recurring task scheduling
    - Task dependency management
    - Resource allocation and constraints
    - Failure recovery and retry mechanisms
    - Real-time task monitoring
    """

    def __init__(self, db_path: str = "./tasks.db", max_workers: int = 4):
        self.db_path = db_path
        self.max_workers = max_workers
        self.workers_available = max_workers
        self.worker_lock = threading.Lock()

        self.task_queue = []  # Priority queue for scheduled tasks
        self.active_tasks = {}  # Currently running tasks
        self.completed_tasks = {}  # Completed tasks
        self.failed_tasks = {}  # Failed tasks

        self.running = False
        self.scheduler_thread = None

        self.setup_database()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('task_scheduler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Initialize the database schema for task tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                function TEXT,
                args_json TEXT,
                kwargs_json TEXT,
                scheduled_time DATETIME,
                recurrence_type TEXT,
                recurrence_interval INTEGER,
                priority INTEGER,
                dependencies_json TEXT,
                max_duration_seconds INTEGER,
                notify_on_completion BOOLEAN,
                notify_on_failure BOOLEAN,
                created_at DATETIME,
                updated_at DATETIME,
                status TEXT,
                result_json TEXT,
                error_message TEXT,
                assigned_resources_json TEXT,
                estimated_duration_seconds INTEGER
            )
        ''')

        # Create task execution logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                timestamp DATETIME,
                status TEXT,
                message TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_task(self, task: Task) -> str:
        """Add a new task to the scheduler."""
        # Store task in database
        self._save_task_to_db(task)

        # Add to in-memory queue if it's scheduled for the future
        if task.scheduled_time > datetime.now():
            scheduled_task = ScheduledTask(
                scheduled_time=task.scheduled_time,
                priority=task.priority.value,
                task_id=task.id,
                task=task
            )
            heapq.heappush(self.task_queue, scheduled_task)

            self.logger.info(f"Task '{task.name}' (ID: {task.id}) scheduled for {task.scheduled_time}")
        else:
            # Execute immediately if scheduled in the past
            self._execute_task(task)

        return task.id

    def _save_task_to_db(self, task: Task) -> None:
        """Save task to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO tasks
            (id, name, description, function, args_json, kwargs_json,
             scheduled_time, recurrence_type, recurrence_interval, priority,
             dependencies_json, max_duration_seconds, notify_on_completion,
             notify_on_failure, created_at, updated_at, status,
             result_json, error_message, assigned_resources_json,
             estimated_duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id, task.name, task.description, task.function,
            json.dumps(list(task.args)), json.dumps(task.kwargs),
            task.scheduled_time.isoformat(), task.recurrence_type.value,
            task.recurrence_interval, task.priority.value,
            json.dumps(task.dependencies),
            task.max_duration.total_seconds() if task.max_duration else None,
            task.notify_on_completion, task.notify_on_failure,
            task.created_at.isoformat(), task.updated_at.isoformat(),
            task.status.value, json.dumps(task.result) if task.result else None,
            task.error_message, json.dumps(task.assigned_resources),
            task.estimated_duration.total_seconds() if task.estimated_duration else None
        ))

        conn.commit()
        conn.close()

    def _load_task_from_db(self, task_id: str) -> Optional[Task]:
        """Load a task from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, function, args_json, kwargs_json,
                   scheduled_time, recurrence_type, recurrence_interval, priority,
                   dependencies_json, max_duration_seconds, notify_on_completion,
                   notify_on_failure, created_at, updated_at, status,
                   result_json, error_message, assigned_resources_json,
                   estimated_duration_seconds
            FROM tasks WHERE id = ?
        ''', (task_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Task(
            id=row[0], name=row[1], description=row[2], function=row[3],
            args=tuple(json.loads(row[4])) if row[4] else (),
            kwargs=json.loads(row[5]) if row[5] else {},
            scheduled_time=datetime.fromisoformat(row[6]),
            recurrence_type=RecurrenceType(row[7]),
            recurrence_interval=row[8],
            priority=Priority(row[9]),
            dependencies=json.loads(row[10]) if row[10] else [],
            max_duration=timedelta(seconds=row[11]) if row[11] else None,
            notify_on_completion=bool(row[12]),
            notify_on_failure=bool(row[13]),
            created_at=datetime.fromisoformat(row[14]),
            updated_at=datetime.fromisoformat(row[15]),
            status=TaskStatus(row[16]),
            result=json.loads(row[17]) if row[17] else None,
            error_message=row[18],
            assigned_resources=json.loads(row[19]) if row[19] else [],
            estimated_duration=timedelta(seconds=row[20]) if row[20] else None
        )

    def _execute_task(self, task: Task) -> None:
        """Execute a task in a separate thread."""
        # Check dependencies
        if not self._dependencies_met(task):
            self.logger.warning(f"Dependencies not met for task '{task.name}', rescheduling.")
            # Reschedule task to check dependencies later
            reschedule_time = datetime.now() + timedelta(minutes=5)
            task.scheduled_time = reschedule_time
            task.status = TaskStatus.SCHEDULED

            scheduled_task = ScheduledTask(
                scheduled_time=reschedule_time,
                priority=task.priority.value,
                task_id=task.id,
                task=task
            )
            heapq.heappush(self.task_queue, scheduled_task)
            return

        # Acquire worker if available
        with self.worker_lock:
            if self.workers_available <= 0:
                # No workers available, reschedule slightly later
                reschedule_time = datetime.now() + timedelta(seconds=30)
                scheduled_task = ScheduledTask(
                    scheduled_time=reschedule_time,
                    priority=task.priority.value,
                    task_id=task.id,
                    task=task
                )
                heapq.heappush(self.task_queue, scheduled_task)
                return

            self.workers_available -= 1
            task.status = TaskStatus.RUNNING
            self.active_tasks[task.id] = task

        # Log task start
        self._log_task_status(task.id, TaskStatus.RUNNING, f"Task started execution")

        try:
            # Simulate task execution (in a real implementation, this would call the actual function)
            # Here we'll simulate execution based on the function name
            result = self._simulate_task_execution(task)

            # Update task status
            task.status = TaskStatus.COMPLETED
            task.result = result

            self.logger.info(f"Task '{task.name}' completed successfully")
            self._log_task_status(task.id, TaskStatus.COMPLETED, f"Task completed successfully")

            # Handle recurring tasks
            if task.recurrence_type != RecurrenceType.NONE:
                next_run = self._calculate_next_occurrence(task)
                if next_run:
                    new_task = Task(
                        id=str(uuid4()),
                        name=task.name,
                        description=task.description,
                        function=task.function,
                        args=task.args,
                        kwargs=task.kwargs,
                        scheduled_time=next_run,
                        recurrence_type=task.recurrence_type,
                        recurrence_interval=task.recurrence_interval,
                        priority=task.priority,
                        dependencies=task.dependencies,
                        max_duration=task.max_duration,
                        notify_on_completion=task.notify_on_completion,
                        notify_on_failure=task.notify_on_failure,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        status=TaskStatus.SCHEDULED,
                        result=None,
                        error_message=None,
                        assigned_resources=task.assigned_resources,
                        estimated_duration=task.estimated_duration
                    )
                    self.add_task(new_task)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)

            self.logger.error(f"Task '{task.name}' failed: {str(e)}")
            self._log_task_status(task.id, TaskStatus.FAILED, f"Task failed: {str(e)}")

            # Retry mechanism (for demonstration)
            if task.recurrence_type == RecurrenceType.NONE:  # Only for non-recurring tasks
                self._retry_task_if_needed(task)

        finally:
            # Update database
            self._save_task_to_db(task)

            # Update in-memory tracking
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]

            if task.status == TaskStatus.COMPLETED:
                self.completed_tasks[task.id] = task
            elif task.status == TaskStatus.FAILED:
                self.failed_tasks[task.id] = task

            # Release worker
            with self.worker_lock:
                self.workers_available += 1

    def _simulate_task_execution(self, task: Task) -> Any:
        """Simulate task execution based on function name."""
        # In a real implementation, this would dynamically call the function
        # For this simulation, we'll handle some common task types:

        if task.function == "send_email":
            # Simulate sending an email
            import random
            time.sleep(random.uniform(0.1, 0.5))  # Simulate network delay
            return {"success": True, "message": f"Email sent to {task.kwargs.get('recipient', 'unknown')}"}

        elif task.function == "generate_report":
            # Simulate report generation
            import random
            time.sleep(random.uniform(0.5, 1.5))  # Simulate processing time
            return {"success": True, "report_id": f"report_{uuid4()}"}

        elif task.function == "backup_data":
            # Simulate data backup
            import random
            time.sleep(random.uniform(1.0, 2.0))  # Simulate I/O operations
            return {"success": True, "backup_size": f"{random.randint(100, 1000)}MB"}

        elif task.function == "sync_files":
            # Simulate file synchronization
            import random
            time.sleep(random.uniform(0.5, 1.0))
            return {"success": True, "files_synced": random.randint(10, 50)}

        else:
            # Generic task simulation
            import random
            time.sleep(random.uniform(0.1, 1.0))
            return {"result": "Task completed", "execution_time": time.time()}

    def _dependencies_met(self, task: Task) -> bool:
        """Check if all task dependencies have been met."""
        for dep_id in task.dependencies:
            dep_task = self._load_task_from_db(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _calculate_next_occurrence(self, task: Task) -> Optional[datetime]:
        """Calculate the next occurrence of a recurring task."""
        current_time = datetime.now()

        if task.recurrence_type == RecurrenceType.DAILY:
            return task.scheduled_time + timedelta(days=1)
        elif task.recurrence_type == RecurrenceType.WEEKLY:
            return task.scheduled_time + timedelta(weeks=1)
        elif task.recurrence_type == RecurrenceType.MONTHLY:
            # Add one month (approximate)
            import calendar
            current_year = task.scheduled_time.year
            current_month = task.scheduled_time.month
            next_month = current_month + 1
            if next_month > 12:
                next_month = 1
                current_year += 1

            # Handle month with fewer days (e.g., Jan 31 -> Feb 28/29)
            max_day = calendar.monthrange(current_year, next_month)[1]
            day = min(task.scheduled_time.day, max_day)

            return task.scheduled_time.replace(year=current_year, month=next_month, day=day)
        elif task.recurrence_type == RecurrenceType.YEARLY:
            # Add one year
            next_year = task.scheduled_time.year + 1
            # Handle leap year edge case for Feb 29
            if task.scheduled_time.month == 2 and task.scheduled_time.day == 29:
                if not calendar.isleap(next_year):
                    return task.scheduled_time.replace(year=next_year, day=28)
            return task.scheduled_time.replace(year=next_year)
        elif task.recurrence_type == RecurrenceType.CUSTOM and task.recurrence_interval:
            return task.scheduled_time + timedelta(days=task.recurrence_interval)

        return None

    def _retry_task_if_needed(self, task: Task) -> None:
        """Implement retry logic for failed tasks."""
        # In a real implementation, you would check if the task should be retried
        # based on failure type, number of previous attempts, etc.
        # For now, we'll just log the failure
        self.logger.info(f"Not retrying failed task '{task.name}' (ID: {task.id})")

    def _log_task_status(self, task_id: str, status: TaskStatus, message: str) -> None:
        """Log task status changes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO task_logs (task_id, timestamp, status, message)
            VALUES (?, ?, ?, ?)
        ''', (task_id, datetime.now().isoformat(), status.value, message))

        conn.commit()
        conn.close()

    def start_scheduler(self) -> None:
        """Start the task scheduler."""
        if self.running:
            self.logger.warning("Scheduler already running")
            return

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        self.logger.info("Task scheduler started")

    def stop_scheduler(self) -> None:
        """Stop the task scheduler."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()

        self.logger.info("Task scheduler stopped")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop that executes tasks."""
        while self.running:
            current_time = datetime.now()

            # Check for tasks that are ready to execute
            ready_tasks = []
            temp_queue = []

            # Separate tasks that are ready to execute
            while self.task_queue:
                scheduled_task = heapq.heappop(self.task_queue)
                if scheduled_task.scheduled_time <= current_time:
                    ready_tasks.append(scheduled_task)
                else:
                    # Put back tasks that aren't ready yet
                    temp_queue.append(scheduled_task)

            # Restore the heap
            self.task_queue = temp_queue
            heapq.heapify(self.task_queue)

            # Execute ready tasks
            for scheduled_task in ready_tasks:
                # Load the latest task data from DB in case it changed
                task = self._load_task_from_db(scheduled_task.task_id)
                if task:
                    # Execute in a separate thread to avoid blocking the scheduler
                    execution_thread = threading.Thread(
                        target=self._execute_task,
                        args=(task,)
                    )
                    execution_thread.daemon = True
                    execution_thread.start()

            # Sleep briefly to prevent busy waiting
            time.sleep(1)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a specific task."""
        # Check in-memory first
        for tasks_dict in [self.active_tasks, self.completed_tasks, self.failed_tasks]:
            if task_id in tasks_dict:
                return tasks_dict[task_id].status

        # Check database
        task = self._load_task_from_db(task_id)
        return task.status if task else None

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        # Check if it's in the queue
        for i, scheduled_task in enumerate(self.task_queue):
            if scheduled_task.task_id == task_id:
                # Remove from queue
                del self.task_queue[i]
                heapq.heapify(self.task_queue)

                # Update task status in DB
                task = self._load_task_from_db(task_id)
                if task:
                    task.status = TaskStatus.CANCELLED
                    self._save_task_to_db(task)

                self.logger.info(f"Task '{task_id}' cancelled")
                return True

        # Check if it's running
        if task_id in self.active_tasks:
            self.logger.warning(f"Cannot cancel task '{task_id}' as it is already running")
            return False

        self.logger.warning(f"Task '{task_id}' not found in queue")
        return False

    def get_upcoming_tasks(self, hours: int = 24) -> List[Task]:
        """Get list of tasks scheduled in the next specified hours."""
        cutoff_time = datetime.now() + timedelta(hours=hours)
        upcoming = []

        # Check the queue
        for scheduled_task in self.task_queue:
            if scheduled_task.scheduled_time <= cutoff_time:
                upcoming.append(scheduled_task.task)

        # Sort by scheduled time
        upcoming.sort(key=lambda t: t.scheduled_time)
        return upcoming

    def get_task_statistics(self) -> Dict[str, int]:
        """Get statistics about tasks."""
        return {
            'queued': len(self.task_queue),
            'active': len(self.active_tasks),
            'completed': len(self.completed_tasks),
            'failed': len(self.failed_tasks),
            'workers_available': self.workers_available
        }


def main():
    """Main function for running the task scheduler."""
    import argparse

    parser = argparse.ArgumentParser(description='Task Scheduler')
    parser.add_argument('--db-path', default='./tasks.db', help='Path to database file')
    parser.add_argument('--workers', type=int, default=4, help='Number of worker threads')
    parser.add_argument('--demo', action='store_true', help='Run demonstration tasks')

    args = parser.parse_args()

    scheduler = TaskScheduler(db_path=args.db_path, max_workers=args.workers)

    if args.demo:
        # Add some demo tasks
        demo_tasks = [
            Task(
                id=str(uuid4()),
                name="Send Daily Report",
                description="Send daily status report to team",
                function="send_email",
                kwargs={"recipient": "team@example.com", "subject": "Daily Report"},
                scheduled_time=datetime.now() + timedelta(seconds=10),
                priority=Priority.HIGH
            ),
            Task(
                id=str(uuid4()),
                name="Backup Data",
                description="Perform daily data backup",
                function="backup_data",
                scheduled_time=datetime.now() + timedelta(seconds=20),
                recurrence_type=RecurrenceType.DAILY,
                priority=Priority.MEDIUM
            ),
            Task(
                id=str(uuid4()),
                name="Generate Analytics Report",
                description="Generate weekly analytics report",
                function="generate_report",
                scheduled_time=datetime.now() + timedelta(seconds=30),
                recurrence_type=RecurrenceType.WEEKLY,
                priority=Priority.LOW
            )
        ]

        print("Adding demo tasks...")
        for task in demo_tasks:
            scheduler.add_task(task)
            print(f"  Added: {task.name} (ID: {task.id}) - Scheduled for {task.scheduled_time}")

        # Start scheduler
        scheduler.start_scheduler()

        print("\nScheduler is running. Waiting for tasks to execute...")
        print("Press Ctrl+C to stop.")

        try:
            # Run for a while to let tasks execute
            for i in range(60):  # Run for 60 seconds
                time.sleep(1)
                if i % 10 == 0:  # Print stats every 10 seconds
                    stats = scheduler.get_task_statistics()
                    print(f"Stats - Queued: {stats['queued']}, Active: {stats['active']}, "
                          f"Completed: {stats['completed']}, Failed: {stats['failed']}")
        except KeyboardInterrupt:
            print("\nStopping scheduler...")

        scheduler.stop_scheduler()
        print("Scheduler stopped.")

    else:
        # Just start the scheduler
        scheduler.start_scheduler()
        print(f"Task scheduler started with {args.workers} workers. Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping scheduler...")
            scheduler.stop_scheduler()
            print("Scheduler stopped.")


if __name__ == "__main__":
    main()