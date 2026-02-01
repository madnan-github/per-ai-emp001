/**
 * TaskSchedulerJS: JavaScript module for scheduling and managing recurring and one-time tasks.
 *
 * This module provides intelligent task scheduling capabilities, including
 * recurring tasks, dependency management, resource allocation, and priority-based
 * task execution.
 */

const fs = require('fs').promises;
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const EventEmitter = require('events');

// Priority levels
const Priority = {
    LOW: 1,
    MEDIUM: 2,
    HIGH: 3,
    CRITICAL: 4
};

// Task status
const TaskStatus = {
    PENDING: "pending",
    RUNNING: "running",
    COMPLETED: "completed",
    FAILED: "failed",
    CANCELLED: "cancelled",
    SCHEDULED: "scheduled"
};

// Recurrence types
const RecurrenceType = {
    NONE: "none",
    DAILY: "daily",
    WEEKLY: "weekly",
    MONTHLY: "monthly",
    YEARLY: "yearly",
    CUSTOM: "custom"
};

class Task {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.name = options.name || 'Untitled Task';
        this.description = options.description || '';
        this.function = options.function || '';
        this.args = options.args || [];
        this.kwargs = options.kwargs || {};
        this.scheduledTime = options.scheduledTime || new Date();
        this.recurrenceType = options.recurrenceType || RecurrenceType.NONE;
        this.recurrenceInterval = options.recurrenceInterval || null;
        this.priority = options.priority || Priority.MEDIUM;
        this.dependencies = options.dependencies || []; // Task IDs this task depends on
        this.maxDuration = options.maxDuration || null; // Maximum allowed execution time in milliseconds
        this.notifyOnCompletion = options.notifyOnCompletion || false;
        this.notifyOnFailure = options.notifyOnFailure || true;
        this.createdAt = options.createdAt || new Date();
        this.updatedAt = options.updatedAt || new Date();
        this.status = options.status || TaskStatus.SCHEDULED;
        this.result = options.result || null;
        this.errorMessage = options.errorMessage || null;
        this.assignedResources = options.assignedResources || [];
        this.estimatedDuration = options.estimatedDuration || null;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class ScheduledTask {
    constructor(scheduledTime, priority, taskId, task) {
        this.scheduledTime = scheduledTime;
        this.priority = priority;
        this.taskId = taskId;
        this.task = task;
    }

    // Comparison for priority queue
    compareTo(other) {
        // Earlier times have higher priority
        if (this.scheduledTime.getTime() !== other.scheduledTime.getTime()) {
            return this.scheduledTime.getTime() - other.scheduledTime.getTime();
        }
        // Higher priority numbers come first
        return other.priority - this.priority;
    }
}

class TaskSchedulerJS extends EventEmitter {
    /**
     * Creates a new TaskSchedulerJS instance
     * @param {string} dbPath - Path to the SQLite database file
     * @param {number} maxWorkers - Maximum number of worker threads
     */
    constructor(dbPath = './tasks.db', maxWorkers = 4) {
        super();
        this.dbPath = dbPath;
        this.maxWorkers = maxWorkers;
        this.workersAvailable = maxWorkers;

        this.taskQueue = []; // Priority queue for scheduled tasks
        this.activeTasks = {}; // Currently running tasks
        this.completedTasks = {}; // Completed tasks
        this.failedTasks = {}; // Failed tasks

        this.running = false;
        this.schedulerThread = null;

        this.setupDatabase();

        // Configure logging
        this.logger = console;
    }

    /**
     * Sets up the database schema for task tracking
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create tasks table
        this.db.run(`
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
        `);

        // Create task execution logs table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                timestamp DATETIME,
                status TEXT,
                message TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        `);
    }

    /**
     * Adds a new task to the scheduler
     * @param {Task} task - The task to add
     * @returns {string} The ID of the added task
     */
    async addTask(task) {
        // Store task in database
        await this.saveTaskToDb(task);

        // Add to in-memory queue if it's scheduled for the future
        if (task.scheduledTime > new Date()) {
            const scheduledTask = new ScheduledTask(
                task.scheduledTime,
                task.priority,
                task.id,
                task
            );
            this.addToQueue(scheduledTask);

            this.logger.info(`Task '${task.name}' (ID: ${task.id}) scheduled for ${task.scheduledTime}`);
        } else {
            // Execute immediately if scheduled in the past
            this.executeTask(task);
        }

        return task.id;
    }

    /**
     * Adds a scheduled task to the priority queue
     * @param {ScheduledTask} scheduledTask - The scheduled task to add
     */
    addToQueue(scheduledTask) {
        this.taskQueue.push(scheduledTask);
        this.taskQueue.sort((a, b) => a.compareTo(b)); // Sort by priority
    }

    /**
     * Saves task to the database
     * @param {Task} task - The task to save
     */
    async saveTaskToDb(task) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT OR REPLACE INTO tasks
                (id, name, description, function, args_json, kwargs_json,
                 scheduled_time, recurrence_type, recurrence_interval, priority,
                 dependencies_json, max_duration_seconds, notify_on_completion,
                 notify_on_failure, created_at, updated_at, status,
                 result_json, error_message, assigned_resources_json,
                 estimated_duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                task.id, task.name, task.description, task.function,
                JSON.stringify(task.args), JSON.stringify(task.kwargs),
                task.scheduledTime.toISOString(), task.recurrenceType,
                task.recurrenceInterval, task.priority,
                JSON.stringify(task.dependencies),
                task.maxDuration ? task.maxDuration / 1000 : null, // Convert ms to seconds
                task.notifyOnCompletion, task.notifyOnFailure,
                task.createdAt.toISOString(), task.updatedAt.toISOString(),
                task.status, task.result ? JSON.stringify(task.result) : null,
                task.errorMessage, JSON.stringify(task.assignedResources),
                task.estimatedDuration ? task.estimatedDuration / 1000 : null // Convert ms to seconds
            ], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Loads a task from the database
     * @param {string} taskId - The ID of the task to load
     * @returns {Promise<Task|null>} The loaded task or null if not found
     */
    async loadTaskFromDb(taskId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, name, description, function, args_json, kwargs_json,
                       scheduled_time, recurrence_type, recurrence_interval, priority,
                       dependencies_json, max_duration_seconds, notify_on_completion,
                       notify_on_failure, created_at, updated_at, status,
                       result_json, error_message, assigned_resources_json,
                       estimated_duration_seconds
                FROM tasks WHERE id = ?
            `);

            stmt.get([taskId], (err, row) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (!row) {
                    resolve(null);
                    return;
                }

                resolve(new Task({
                    id: row.id,
                    name: row.name,
                    description: row.description,
                    function: row.function,
                    args: JSON.parse(row.args_json || '[]'),
                    kwargs: JSON.parse(row.kwargs_json || '{}'),
                    scheduledTime: new Date(row.scheduled_time),
                    recurrenceType: row.recurrence_type,
                    recurrenceInterval: row.recurrence_interval,
                    priority: row.priority,
                    dependencies: JSON.parse(row.dependencies_json || '[]'),
                    maxDuration: row.max_duration_seconds ? row.max_duration_seconds * 1000 : null, // Convert seconds to ms
                    notifyOnCompletion: !!row.notify_on_completion,
                    notifyOnFailure: !!row.notify_on_failure,
                    createdAt: new Date(row.created_at),
                    updatedAt: new Date(row.updated_at),
                    status: row.status,
                    result: row.result_json ? JSON.parse(row.result_json) : null,
                    errorMessage: row.error_message,
                    assignedResources: JSON.parse(row.assigned_resources_json || '[]'),
                    estimatedDuration: row.estimated_duration_seconds ? row.estimated_duration_seconds * 1000 : null // Convert seconds to ms
                }));
            });

            stmt.finalize();
        });
    }

    /**
     * Executes a task
     * @param {Task} task - The task to execute
     */
    async executeTask(task) {
        // Check dependencies
        if (!(await this.dependenciesMet(task))) {
            this.logger.warn(`Dependencies not met for task '${task.name}', rescheduling.`);
            // Reschedule task to check dependencies later
            const rescheduleTime = new Date(Date.now() + 5 * 60 * 1000); // 5 minutes
            task.scheduledTime = rescheduleTime;
            task.status = TaskStatus.SCHEDULED;

            const scheduledTask = new ScheduledTask(
                rescheduleTime,
                task.priority,
                task.id,
                task
            );
            this.addToQueue(scheduledTask);
            return;
        }

        // Acquire worker if available
        if (this.workersAvailable <= 0) {
            // No workers available, reschedule slightly later
            const rescheduleTime = new Date(Date.now() + 30 * 1000); // 30 seconds
            const scheduledTask = new ScheduledTask(
                rescheduleTime,
                task.priority,
                task.id,
                task
            );
            this.addToQueue(scheduledTask);
            return;
        }

        this.workersAvailable--;
        task.status = TaskStatus.RUNNING;
        this.activeTasks[task.id] = task;

        // Log task start
        await this.logTaskStatus(task.id, TaskStatus.RUNNING, `Task started execution`);

        try {
            // Simulate task execution (in a real implementation, this would call the actual function)
            const result = await this.simulateTaskExecution(task);

            // Update task status
            task.status = TaskStatus.COMPLETED;
            task.result = result;

            this.logger.info(`Task '${task.name}' completed successfully`);
            await this.logTaskStatus(task.id, TaskStatus.COMPLETED, `Task completed successfully`);

            // Handle recurring tasks
            if (task.recurrenceType !== RecurrenceType.NONE) {
                const nextRun = this.calculateNextOccurrence(task);
                if (nextRun) {
                    const newTask = new Task({
                        id: this.generateId(),
                        name: task.name,
                        description: task.description,
                        function: task.function,
                        args: task.args,
                        kwargs: task.kwargs,
                        scheduledTime: nextRun,
                        recurrenceType: task.recurrenceType,
                        recurrenceInterval: task.recurrenceInterval,
                        priority: task.priority,
                        dependencies: task.dependencies,
                        maxDuration: task.maxDuration,
                        notifyOnCompletion: task.notifyOnCompletion,
                        notifyOnFailure: task.notifyOnFailure,
                        createdAt: new Date(),
                        updatedAt: new Date(),
                        status: TaskStatus.SCHEDULED,
                        result: null,
                        errorMessage: null,
                        assignedResources: task.assignedResources,
                        estimatedDuration: task.estimatedDuration
                    });
                    await this.addTask(newTask);
                }
            }

            // Emit completion event
            this.emit('taskCompleted', { task, result });

        } catch (error) {
            task.status = TaskStatus.FAILED;
            task.errorMessage = error.message;

            this.logger.error(`Task '${task.name}' failed: ${error.message}`);
            await this.logTaskStatus(task.id, TaskStatus.FAILED, `Task failed: ${error.message}`);

            // Retry mechanism (for demonstration)
            if (task.recurrenceType === RecurrenceType.NONE) { // Only for non-recurring tasks
                await this.retryTaskIfNeeded(task);
            }

            // Emit failure event
            this.emit('taskFailed', { task, error });

        } finally {
            // Update database
            await this.saveTaskToDb(task);

            // Update in-memory tracking
            if (task.id in this.activeTasks) {
                delete this.activeTasks[task.id];
            }

            if (task.status === TaskStatus.COMPLETED) {
                this.completedTasks[task.id] = task;
            } else if (task.status === TaskStatus.FAILED) {
                this.failedTasks[task.id] = task;
            }

            // Release worker
            this.workersAvailable++;
        }
    }

    /**
     * Simulates task execution based on function name
     * @param {Task} task - The task to simulate
     * @returns {Promise<any>} The simulated result
     */
    async simulateTaskExecution(task) {
        // In a real implementation, this would dynamically call the function
        // For this simulation, we'll handle some common task types:

        if (task.function === "send_email") {
            // Simulate sending an email
            await this.delay(Math.random() * 400 + 100); // Simulate network delay (100-500ms)
            return {
                success: true,
                message: `Email sent to ${task.kwargs.recipient || 'unknown'}`
            };

        } else if (task.function === "generate_report") {
            // Simulate report generation
            await this.delay(Math.random() * 1000 + 500); // Simulate processing time (500-1500ms)
            return {
                success: true,
                reportId: `report_${this.generateId()}`
            };

        } else if (task.function === "backup_data") {
            // Simulate data backup
            await this.delay(Math.random() * 1000 + 1000); // Simulate I/O operations (1000-2000ms)
            return {
                success: true,
                backupSize: `${Math.floor(Math.random() * 900) + 100}MB`
            };

        } else if (task.function === "sync_files") {
            // Simulate file synchronization
            await this.delay(Math.random() * 500 + 500); // (500-1000ms)
            return {
                success: true,
                filesSynced: Math.floor(Math.random() * 40) + 10
            };

        } else {
            // Generic task simulation
            await this.delay(Math.random() * 900 + 100);
            return {
                result: "Task completed",
                executionTime: Date.now()
            };
        }
    }

    /**
     * Delays execution for specified milliseconds
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Checks if all task dependencies have been met
     * @param {Task} task - The task to check dependencies for
     * @returns {Promise<boolean>} Whether dependencies are met
     */
    async dependenciesMet(task) {
        for (const depId of task.dependencies) {
            const depTask = await this.loadTaskFromDb(depId);
            if (!depTask || depTask.status !== TaskStatus.COMPLETED) {
                return false;
            }
        }
        return true;
    }

    /**
     * Calculates the next occurrence of a recurring task
     * @param {Task} task - The recurring task
     * @returns {Date|null} The next occurrence time or null
     */
    calculateNextOccurrence(task) {
        const currentTime = new Date();

        switch (task.recurrenceType) {
            case RecurrenceType.DAILY:
                const nextDaily = new Date(task.scheduledTime);
                nextDaily.setDate(nextDaily.getDate() + 1);
                return nextDaily;

            case RecurrenceType.WEEKLY:
                const nextWeekly = new Date(task.scheduledTime);
                nextWeekly.setDate(nextWeekly.getDate() + 7);
                return nextWeekly;

            case RecurrenceType.MONTHLY:
                const nextMonthly = new Date(task.scheduledTime);
                nextMonthly.setMonth(nextMonthly.getMonth() + 1);
                return nextMonthly;

            case RecurrenceType.YEARLY:
                const nextYearly = new Date(task.scheduledTime);
                nextYearly.setFullYear(nextYearly.getFullYear() + 1);
                return nextYearly;

            case RecurrenceType.CUSTOM:
                if (task.recurrenceInterval) {
                    const nextCustom = new Date(task.scheduledTime);
                    nextCustom.setDate(nextCustom.getDate() + task.recurrenceInterval);
                    return nextCustom;
                }
                break;

            default:
                return null;
        }

        return null;
    }

    /**
     * Implements retry logic for failed tasks
     * @param {Task} task - The failed task
     */
    async retryTaskIfNeeded(task) {
        // In a real implementation, you would check if the task should be retried
        // based on failure type, number of previous attempts, etc.
        // For now, we'll just log the failure
        this.logger.info(`Not retrying failed task '${task.name}' (ID: ${task.id})`);
    }

    /**
     * Logs task status changes
     * @param {string} taskId - The task ID
     * @param {string} status - The status
     * @param {string} message - The message to log
     */
    async logTaskStatus(taskId, status, message) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO task_logs (task_id, timestamp, status, message)
                VALUES (?, ?, ?, ?)
            `);

            stmt.run([taskId, new Date().toISOString(), status, message], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Starts the task scheduler
     */
    async startScheduler() {
        if (this.running) {
            this.logger.warn("Scheduler already running");
            return;
        }

        this.running = true;
        this.schedulerThread = setInterval(() => {
            this.schedulerLoop();
        }, 1000); // Check every second

        this.logger.info("Task scheduler started");
    }

    /**
     * Stops the task scheduler
     */
    async stopScheduler() {
        this.running = false;
        if (this.schedulerThread) {
            clearInterval(this.schedulerThread);
        }

        this.logger.info("Task scheduler stopped");
    }

    /**
     * Main scheduler loop that executes tasks
     */
    async schedulerLoop() {
        if (!this.running) return;

        const currentTime = new Date();

        // Check for tasks that are ready to execute
        const readyTasks = [];
        const remainingQueue = [];

        // Separate tasks that are ready to execute
        for (const scheduledTask of this.taskQueue) {
            if (scheduledTask.scheduledTime <= currentTime) {
                readyTasks.push(scheduledTask);
            } else {
                // Keep tasks that aren't ready yet
                remainingQueue.push(scheduledTask);
            }
        }

        // Update the queue
        this.taskQueue = remainingQueue;

        // Execute ready tasks
        for (const scheduledTask of readyTasks) {
            // Load the latest task data from DB in case it changed
            const task = await this.loadTaskFromDb(scheduledTask.taskId);
            if (task) {
                // Execute in a separate promise to avoid blocking the scheduler
                this.executeTask(task).catch(err => {
                    this.logger.error(`Error executing task: ${err.message}`);
                });
            }
        }
    }

    /**
     * Gets the status of a specific task
     * @param {string} taskId - The task ID
     * @returns {Promise<string|null>} The task status or null
     */
    async getTaskStatus(taskId) {
        // Check in-memory first
        for (const tasksDict of [this.activeTasks, this.completedTasks, this.failedTasks]) {
            if (taskId in tasksDict) {
                return tasksDict[taskId].status;
            }
        }

        // Check database
        const task = await this.loadTaskFromDb(taskId);
        return task ? task.status : null;
    }

    /**
     * Cancels a scheduled task
     * @param {string} taskId - The task ID to cancel
     * @returns {Promise<boolean>} Whether the task was cancelled
     */
    async cancelTask(taskId) {
        // Check if it's in the queue
        const queueIndex = this.taskQueue.findIndex(st => st.taskId === taskId);
        if (queueIndex !== -1) {
            // Remove from queue
            this.taskQueue.splice(queueIndex, 1);

            // Update task status in DB
            const task = await this.loadTaskFromDb(taskId);
            if (task) {
                task.status = TaskStatus.CANCELLED;
                await this.saveTaskToDb(task);
            }

            this.logger.info(`Task '${taskId}' cancelled`);
            return true;
        }

        // Check if it's running
        if (taskId in this.activeTasks) {
            this.logger.warn(`Cannot cancel task '${taskId}' as it is already running`);
            return false;
        }

        this.logger.warn(`Task '${taskId}' not found in queue`);
        return false;
    }

    /**
     * Gets tasks scheduled in the next specified hours
     * @param {number} hours - Number of hours to look ahead
     * @returns {Promise<Array>} Array of upcoming tasks
     */
    async getUpcomingTasks(hours = 24) {
        const cutoffTime = new Date(Date.now() + hours * 60 * 60 * 1000);
        const upcoming = [];

        // Check the queue
        for (const scheduledTask of this.taskQueue) {
            if (scheduledTask.scheduledTime <= cutoffTime) {
                upcoming.push(scheduledTask.task);
            }
        }

        // Sort by scheduled time
        upcoming.sort((a, b) => a.scheduledTime - b.scheduledTime);
        return upcoming;
    }

    /**
     * Gets statistics about tasks
     * @returns {Promise<Object>} Task statistics
     */
    async getTaskStatistics() {
        return {
            queued: this.taskQueue.length,
            active: Object.keys(this.activeTasks).length,
            completed: Object.keys(this.completedTasks).length,
            failed: Object.keys(this.failedTasks).length,
            workersAvailable: this.workersAvailable
        };
    }

    /**
     * Generates a unique ID
     * @returns {string} Unique ID
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

module.exports = TaskSchedulerJS;

// If running as a standalone script
if (require.main === module) {
    const args = process.argv.slice(2);

    async function main() {
        const scheduler = new TaskSchedulerJS();

        if (args.includes('--demo')) {
            // Add some demo tasks
            const demoTasks = [
                new Task({
                    id: scheduler.generateId(),
                    name: "Send Daily Report",
                    description: "Send daily status report to team",
                    function: "send_email",
                    kwargs: { recipient: "team@example.com", subject: "Daily Report" },
                    scheduledTime: new Date(Date.now() + 10000), // 10 seconds from now
                    priority: Priority.HIGH
                }),
                new Task({
                    id: scheduler.generateId(),
                    name: "Backup Data",
                    description: "Perform daily data backup",
                    function: "backup_data",
                    scheduledTime: new Date(Date.now() + 20000), // 20 seconds from now
                    recurrenceType: RecurrenceType.DAILY,
                    priority: Priority.MEDIUM
                }),
                new Task({
                    id: scheduler.generateId(),
                    name: "Generate Analytics Report",
                    description: "Generate weekly analytics report",
                    function: "generate_report",
                    scheduledTime: new Date(Date.now() + 30000), // 30 seconds from now
                    recurrenceType: RecurrenceType.WEEKLY,
                    priority: Priority.LOW
                })
            ];

            console.log("Adding demo tasks...");
            for (const task of demoTasks) {
                await scheduler.addTask(task);
                console.log(`  Added: ${task.name} (ID: ${task.id}) - Scheduled for ${task.scheduledTime}`);
            }

            // Subscribe to events
            scheduler.on('taskCompleted', ({ task, result }) => {
                console.log(`Task completed: ${task.name} - ${JSON.stringify(result)}`);
            });

            scheduler.on('taskFailed', ({ task, error }) => {
                console.log(`Task failed: ${task.name} - ${error.message}`);
            });

            // Start scheduler
            await scheduler.startScheduler();

            console.log("\nScheduler is running. Waiting for tasks to execute...");
            console.log("Press Ctrl+C to stop.");

            // Run for a while to let tasks execute
            const startTime = Date.now();
            while (Date.now() - startTime < 60000) { // Run for 60 seconds
                await scheduler.delay(1000);

                if ((Date.now() - startTime) % 10000 < 1000) { // Print stats every 10 seconds
                    const stats = await scheduler.getTaskStatistics();
                    console.log(`Stats - Queued: ${stats.queued}, Active: ${stats.active}, ` +
                               `Completed: ${stats.completed}, Failed: ${stats.failed}`);
                }
            }

            await scheduler.stopScheduler();
            console.log("Scheduler stopped.");

        } else {
            // Just start the scheduler
            await scheduler.startScheduler();
            console.log("Task scheduler started. Press Ctrl+C to stop.");

            // Keep the process running
            await new Promise(() => {});
        }
    }

    main().catch(console.error);
}