#!/usr/bin/env python3
"""
Scheduler Coordinator

This module provides centralized task scheduling and coordination for the Personal AI Employee system.
It manages task execution timing, dependencies, resource allocation, and ensures optimal scheduling
across all system components while maintaining system stability and performance.

Features:
- Centralized task scheduling and execution
- Dependency management and resolution
- Priority-based task execution
- Resource allocation and monitoring
- Retry mechanisms and circuit breakers
- Queue-based task processing
- Performance monitoring and alerting
"""

import json
import os
import sqlite3
import logging
import threading
import time
import queue
import subprocess
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import signal
import sys
import hashlib


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 100
    NORMAL = 50
    HIGH = 10
    CRITICAL = 1


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Data class to hold task information."""
    id: str
    name: str
    function: str
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: TaskPriority
    dependencies: List[str]
    execution_time: str
    timeout_seconds: int
    retry_policy: Dict[str, Any]
    resource_requirements: Dict[str, Any]
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None


class ResourceManager:
    """Manages system resources for task execution."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.system_limits = config.get('system_limits', {})
        self.task_resources = config.get('task_resources', {}).get('default', {})
        self.lock = threading.RLock()

    def check_resource_availability(self) -> Dict[str, bool]:
        """Check if system resources are available for task execution."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent

        cpu_available = cpu_percent < self.system_limits.get('cpu_threshold_percent', 80)
        memory_available = memory_percent < self.system_limits.get('memory_threshold_percent', 85)
        disk_available = disk_percent < self.system_limits.get('disk_threshold_percent', 90)

        return {
            'cpu': cpu_available,
            'memory': memory_available,
            'disk': disk_available,
            'overall': cpu_available and memory_available and disk_available
        }

    def get_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'memory_used_mb': psutil.virtual_memory().used / (1024 * 1024),
            'memory_total_mb': psutil.virtual_memory().total / (1024 * 1024)
        }


class TaskQueue:
    """Manages task queues based on priority."""

    def __init__(self, maxsize: int = 0):
        self.queues = {
            TaskPriority.CRITICAL: queue.PriorityQueue(maxsize=maxsize),
            TaskPriority.HIGH: queue.PriorityQueue(maxsize=maxsize),
            TaskPriority.NORMAL: queue.PriorityQueue(maxsize=maxsize),
            TaskPriority.LOW: queue.PriorityQueue(maxsize=maxsize)
        }
        self.lock = threading.Lock()

    def put(self, task: TaskInfo):
        """Add a task to the appropriate priority queue."""
        with self.lock:
            priority_value = task.priority.value
            # Lower value means higher priority
            self.queues[task.priority].put((priority_value, time.time(), task))

    def get(self) -> Optional[TaskInfo]:
        """Get the highest priority task from the queues."""
        with self.lock:
            # Check queues in priority order
            for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
                q = self.queues[priority]
                if not q.empty():
                    try:
                        _, _, task = q.get_nowait()
                        return task
                    except queue.Empty:
                        continue
            return None

    def empty(self) -> bool:
        """Check if all queues are empty."""
        with self.lock:
            return all(q.empty() for q in self.queues.values())

    def size(self) -> int:
        """Get total number of tasks in all queues."""
        with self.lock:
            return sum(q.qsize() for q in self.queues.values())


class CircuitBreaker:
    """Implementation of the circuit breaker pattern."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """Call a function with circuit breaker protection."""
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = "half_open"
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")

            try:
                result = func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise e

    def on_success(self):
        """Reset the circuit breaker on success."""
        self.failure_count = 0
        self.state = "closed"

    def on_failure(self):
        """Increment failure count and possibly open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class TaskRegistry:
    """Manages the task registry database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    function TEXT NOT NULL,
                    args TEXT,
                    kwargs TEXT,
                    priority TEXT NOT NULL,
                    dependencies TEXT,
                    execution_time TEXT NOT NULL,
                    timeout_seconds INTEGER,
                    retry_policy TEXT,
                    resource_requirements TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT,
                    worker_id TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    dependency_id TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks (id),
                    FOREIGN KEY (dependency_id) REFERENCES tasks (id)
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

    def add_task(self, task_info: TaskInfo):
        """Add a task to the registry."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO tasks
                (id, name, function, args, kwargs, priority, dependencies, execution_time,
                 timeout_seconds, retry_policy, resource_requirements, status, created_at,
                 started_at, completed_at, result, error, worker_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_info.id, task_info.name, task_info.function,
                json.dumps(task_info.args), json.dumps(task_info.kwargs),
                task_info.priority.name, json.dumps(task_info.dependencies),
                task_info.execution_time, task_info.timeout_seconds,
                json.dumps(task_info.retry_policy), json.dumps(task_info.resource_requirements),
                task_info.status.name, task_info.created_at, task_info.started_at,
                task_info.completed_at, json.dumps(task_info.result), task_info.error,
                task_info.worker_id
            ))

            # Add dependencies to the dependencies table
            for dep_id in task_info.dependencies:
                conn.execute('''
                    INSERT INTO task_dependencies (task_id, dependency_id)
                    VALUES (?, ?)
                ''', (task_info.id, dep_id))

    def update_task_status(self, task_id: str, status: TaskStatus, started_at: str = None, completed_at: str = None, result: Any = None, error: str = None):
        """Update task status in the registry."""
        with self.get_connection() as conn:
            update_fields = []
            params = []

            update_fields.append("status = ?")
            params.append(status.name)

            if started_at:
                update_fields.append("started_at = ?")
                params.append(started_at)

            if completed_at:
                update_fields.append("completed_at = ?")
                params.append(completed_at)

            if result is not None:
                update_fields.append("result = ?")
                params.append(json.dumps(result))

            if error:
                update_fields.append("error = ?")
                params.append(error)

            params.append(task_id)

            query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
            conn.execute(query, params)

    def get_task_by_id(self, task_id: str) -> Optional[TaskInfo]:
        """Get a task by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, function, args, kwargs, priority, dependencies,
                       execution_time, timeout_seconds, retry_policy, resource_requirements,
                       status, created_at, started_at, completed_at, result, error, worker_id
                FROM tasks WHERE id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            if row:
                return TaskInfo(
                    id=row[0], name=row[1], function=row[2],
                    args=json.loads(row[3]) if row[3] else [],
                    kwargs=json.loads(row[4]) if row[4] else {},
                    priority=TaskPriority[row[5]],
                    dependencies=json.loads(row[6]) if row[6] else [],
                    execution_time=row[7], timeout_seconds=row[8],
                    retry_policy=json.loads(row[9]) if row[9] else {},
                    resource_requirements=json.loads(row[10]) if row[10] else {},
                    status=TaskStatus[row[11]], created_at=row[12],
                    started_at=row[13], completed_at=row[14],
                    result=json.loads(row[15]) if row[15] else None,
                    error=row[16], worker_id=row[17]
                )
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[TaskInfo]:
        """Get tasks by status."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, function, args, kwargs, priority, dependencies,
                       execution_time, timeout_seconds, retry_policy, resource_requirements,
                       status, created_at, started_at, completed_at, result, error, worker_id
                FROM tasks WHERE status = ?
            ''', (status.name,))
            rows = cursor.fetchall()
            tasks = []
            for row in rows:
                tasks.append(TaskInfo(
                    id=row[0], name=row[1], function=row[2],
                    args=json.loads(row[3]) if row[3] else [],
                    kwargs=json.loads(row[4]) if row[4] else {},
                    priority=TaskPriority[row[5]],
                    dependencies=json.loads(row[6]) if row[6] else [],
                    execution_time=row[7], timeout_seconds=row[8],
                    retry_policy=json.loads(row[9]) if row[9] else {},
                    resource_requirements=json.loads(row[10]) if row[10] else {},
                    status=TaskStatus[row[11]], created_at=row[12],
                    started_at=row[13], completed_at=row[14],
                    result=json.loads(row[15]) if row[15] else None,
                    error=row[16], worker_id=row[17]
                ))
            return tasks

    def get_ready_tasks(self) -> List[TaskInfo]:
        """Get tasks that are ready to run (dependencies satisfied)."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT t.id, t.name, t.function, t.args, t.kwargs, t.priority, t.dependencies,
                       t.execution_time, t.timeout_seconds, t.retry_policy, t.resource_requirements,
                       t.status, t.created_at, t.started_at, t.completed_at, t.result, t.error, t.worker_id
                FROM tasks t
                WHERE t.status = 'PENDING'
                AND NOT EXISTS (
                    SELECT 1 FROM task_dependencies td
                    JOIN tasks dt ON td.dependency_id = dt.id
                    WHERE td.task_id = t.id AND dt.status != 'COMPLETED'
                )
            ''')
            rows = cursor.fetchall()
            tasks = []
            for row in rows:
                tasks.append(TaskInfo(
                    id=row[0], name=row[1], function=row[2],
                    args=json.loads(row[3]) if row[3] else [],
                    kwargs=json.loads(row[4]) if row[4] else {},
                    priority=TaskPriority[row[5]],
                    dependencies=json.loads(row[6]) if row[6] else [],
                    execution_time=row[7], timeout_seconds=row[8],
                    retry_policy=json.loads(row[9]) if row[9] else {},
                    resource_requirements=json.loads(row[10]) if row[10] else {},
                    status=TaskStatus[row[11]], created_at=row[12],
                    started_at=row[13], completed_at=row[14],
                    result=json.loads(row[15]) if row[15] else None,
                    error=row[16], worker_id=row[17]
                ))
            return tasks


class TaskExecutor:
    """Executes tasks with resource management and timeout handling."""

    def __init__(self, task_registry: TaskRegistry, resource_manager: ResourceManager):
        self.task_registry = task_registry
        self.resource_manager = resource_manager
        self.logger = logging.getLogger('TaskExecutor')

    def execute_task(self, task_info: TaskInfo) -> bool:
        """Execute a single task with timeout and error handling."""
        try:
            # Update task status to running
            started_at = datetime.now().isoformat()
            self.task_registry.update_task_status(
                task_info.id, TaskStatus.RUNNING, started_at=started_at
            )

            # Execute the task function
            start_time = time.time()

            # Import and execute the function
            module_name, function_name = task_info.function.rsplit('.', 1)
            module = __import__(module_name, fromlist=[function_name])
            func = getattr(module, function_name)

            # Execute with timeout
            result = self._execute_with_timeout(func, task_info.args, task_info.kwargs, task_info.timeout_seconds)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Update task status to completed
            completed_at = datetime.now().isoformat()
            self.task_registry.update_task_status(
                task_info.id, TaskStatus.COMPLETED,
                completed_at=completed_at, result=result
            )

            self.logger.info(f"Task {task_info.id} completed successfully in {execution_time:.2f}s")
            return True

        except Exception as e:
            # Update task status to failed
            completed_at = datetime.now().isoformat()
            self.task_registry.update_task_status(
                task_info.id, TaskStatus.FAILED,
                completed_at=completed_at, error=str(e)
            )

            self.logger.error(f"Task {task_info.id} failed: {e}")
            return False

    def _execute_with_timeout(self, func: Callable, args: List[Any], kwargs: Dict[str, Any], timeout_seconds: int):
        """Execute a function with timeout."""
        def timeout_handler(signum, frame):
            raise TimeoutError("Task execution timed out")

        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Cancel the alarm
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class SchedulerCoordinator:
    """Main scheduler coordinator class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.task_registry = TaskRegistry(os.getenv('SCHEDULER_REGISTRY_DB_PATH', ':memory:'))
        self.resource_manager = ResourceManager({
            'system_limits': {
                'cpu_threshold_percent': int(os.getenv('SCHEDULER_CPU_THRESHOLD', '80')),
                'memory_threshold_percent': int(os.getenv('SCHEDULER_MEMORY_THRESHOLD', '85')),
                'disk_threshold_percent': int(os.getenv('SCHEDULER_DISK_THRESHOLD', '90'))
            }
        })
        self.task_queue = TaskQueue(maxsize=int(os.getenv('SCHEDULER_QUEUE_SIZE', '100')))
        self.executor = TaskExecutor(self.task_registry, self.resource_manager)
        self.workers = []
        self.running = False
        self.worker_count = int(os.getenv('SCHEDULER_WORKER_COUNT', '4'))
        self.heartbeat_interval = int(os.getenv('SCHEDULER_HEARTBEAT_INTERVAL', '30'))

        # Load configuration
        self.config = self.load_config()

        # Initialize circuit breaker
        cb_config = self.config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get('failure_threshold', 5),
            timeout=cb_config.get('timeout_seconds', 60)
        )

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the scheduler coordinator."""
        logger = logging.getLogger('SchedulerCoordinator')
        logger.setLevel(getattr(logging, os.getenv('SCHEDULER_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('SCHEDULER_LOG_FILE_PATH', '/tmp/scheduler_coordinator.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'scheduling': {
                'default_timezone': 'UTC',
                'max_concurrent_tasks': int(os.getenv('SCHEDULER_MAX_CONCURRENT', '5'))
            },
            'retry_policies': {
                'default': {
                    'strategy': 'exponential',
                    'max_attempts': 3,
                    'initial_delay_seconds': 1,
                    'backoff_factor': 2.0
                }
            },
            'resources': {
                'allocation_strategy': 'weighted_round_robin',
                'system_limits': {
                    'cpu_threshold_percent': 80,
                    'memory_threshold_percent': 85,
                    'disk_threshold_percent': 90
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

    def add_task(
        self,
        name: str,
        task_function: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: str = 'normal',
        dependencies: List[str] = None,
        execution_time: str = None,
        timeout_seconds: int = 3600,
        retry_policy: Dict[str, Any] = None,
        resource_requirements: Dict[str, Any] = None
    ) -> str:
        """Add a task to the scheduler."""
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        if dependencies is None:
            dependencies = []
        if retry_policy is None:
            retry_policy = self.config['retry_policies']['default']
        if resource_requirements is None:
            resource_requirements = self.config['resources'].get('task_resources', {}).get('default', {})

        # Generate task ID
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(name) % 10000}"

        # Create task info
        task_info = TaskInfo(
            id=task_id,
            name=name,
            function=task_function,
            args=args,
            kwargs=kwargs,
            priority=TaskPriority[priority.upper()],
            dependencies=dependencies,
            execution_time=execution_time or datetime.now().isoformat(),
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy,
            resource_requirements=resource_requirements,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )

        # Add task to registry
        self.task_registry.add_task(task_info)

        # Add to queue if dependencies are satisfied
        if not dependencies:
            self.task_queue.put(task_info)

        self.logger.info(f"Task {task_id} added to scheduler")
        return task_id

    def start_workers(self):
        """Start worker threads to process tasks."""
        if self.running:
            return

        self.running = True

        # Start worker threads
        for i in range(self.worker_count):
            worker = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        self.logger.info(f"Started {self.worker_count} worker threads")

    def stop_workers(self):
        """Stop worker threads."""
        self.running = False

        for worker in self.workers:
            worker.join(timeout=5)

        self.workers.clear()
        self.logger.info("Stopped all worker threads")

    def _worker_loop(self, worker_id: int):
        """Main loop for worker threads."""
        self.logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Check system resources
                resources = self.resource_manager.check_resource_availability()
                if not resources['overall']:
                    # System is under stress, wait a bit
                    time.sleep(5)
                    continue

                # Get a task from the queue
                task = self.task_queue.get()
                if task is None:
                    # No tasks available, wait a bit
                    time.sleep(1)
                    continue

                # Execute the task
                self.logger.info(f"Worker {worker_id} executing task {task.id}")
                success = self.executor.execute_task(task)

                if not success:
                    # Handle task failure based on retry policy
                    self._handle_task_failure(task)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                time.sleep(1)

        self.logger.info(f"Worker {worker_id} stopped")

    def _heartbeat_loop(self):
        """Heartbeat loop to monitor scheduler health."""
        while self.running:
            try:
                # Process ready tasks (those with satisfied dependencies)
                ready_tasks = self.task_registry.get_ready_tasks()
                for task in ready_tasks:
                    # Add to queue if not already queued
                    if task.status == TaskStatus.PENDING:
                        self.task_queue.put(task)
                        # Update status to queued
                        self.task_registry.update_task_status(task.id, TaskStatus.QUEUED)

                time.sleep(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                time.sleep(self.heartbeat_interval)

    def _handle_task_failure(self, task: TaskInfo):
        """Handle task failure according to retry policy."""
        retry_policy = task.retry_policy
        strategy = retry_policy.get('strategy', 'none')

        if strategy == 'none':
            # No retry, leave task as failed
            return

        # In a real implementation, we would implement retry logic here
        # For now, we'll just log the failure
        self.logger.warning(f"Task {task.id} failed, retry strategy: {strategy}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a specific task."""
        task_info = self.task_registry.get_task_by_id(task_id)
        if not task_info:
            return {'error': f'Task {task_id} not found'}

        result = asdict(task_info)
        result['priority'] = task_info.priority.name
        result['status'] = task_info.status.name
        return result

    def get_queue_status(self) -> Dict[str, Any]:
        """Get the status of the task queue."""
        return {
            'queue_size': self.task_queue.size(),
            'workers_running': len([w for w in self.workers if w.is_alive()]),
            'resource_usage': self.resource_manager.get_resource_usage(),
            'pending_tasks': len(self.task_registry.get_tasks_by_status(TaskStatus.PENDING)),
            'running_tasks': len(self.task_registry.get_tasks_by_status(TaskStatus.RUNNING)),
            'completed_tasks': len(self.task_registry.get_tasks_by_status(TaskStatus.COMPLETED)),
            'failed_tasks': len(self.task_registry.get_tasks_by_status(TaskStatus.FAILED))
        }


def example_task_function(name: str, duration: int = 2):
    """Example task function for testing."""
    print(f"Executing example task: {name}")
    time.sleep(duration)
    return f"Task {name} completed"


def main():
    """Main function for testing the Scheduler Coordinator."""
    print("Scheduler Coordinator Skill")
    print("===========================")

    # Initialize the scheduler
    config_path = os.getenv('SCHEDULER_CONFIG_PATH', './scheduler_config.json')
    scheduler = SchedulerCoordinator(config_path)

    print(f"Scheduler Coordinator initialized with config: {config_path}")

    # Start workers
    scheduler.start_workers()

    # Example: Add a test task
    print("\nAdding test task...")
    task_id = scheduler.add_task(
        name="test_task",
        task_function="__main__.example_task_function",
        args=["Test Task", 2],
        priority="normal",
        timeout_seconds=10
    )

    print(f"Test task added with ID: {task_id}")

    # Wait for task to complete
    print("Waiting for task to complete...")
    time.sleep(5)

    # Check task status
    status = scheduler.get_task_status(task_id)
    print(f"Task status: {status}")

    # Add multiple tasks with dependencies
    print("\nAdding tasks with dependencies...")

    task1_id = scheduler.add_task(
        name="task_1",
        task_function="__main__.example_task_function",
        args=["Task 1", 1],
        priority="high"
    )

    task2_id = scheduler.add_task(
        name="task_2",
        task_function="__main__.example_task_function",
        args=["Task 2", 1],
        priority="normal",
        dependencies=[task1_id]  # Task 2 depends on Task 1
    )

    task3_id = scheduler.add_task(
        name="task_3",
        task_function="__main__.example_task_function",
        args=["Task 3", 1],
        priority="low",
        dependencies=[task2_id]  # Task 3 depends on Task 2
    )

    print(f"Added tasks with dependencies:")
    print(f"  Task 1: {task1_id}")
    print(f"  Task 2: {task2_id} (depends on {task1_id})")
    print(f"  Task 3: {task3_id} (depends on {task2_id})")

    # Get queue status
    queue_status = scheduler.get_queue_status()
    print(f"\nQueue status: {queue_status}")

    # Wait for tasks to complete
    print("Waiting for all tasks to complete...")
    time.sleep(10)

    # Final queue status
    final_status = scheduler.get_queue_status()
    print(f"\nFinal queue status: {final_status}")

    # Stop workers
    scheduler.stop_workers()

    print("\nScheduler Coordinator is ready to coordinate tasks!")


if __name__ == "__main__":
    main()