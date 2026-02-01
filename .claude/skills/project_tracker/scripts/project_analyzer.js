/**
 * ProjectTrackerJS: JavaScript module for tracking project progress, milestones, and key metrics.
 *
 * This module provides comprehensive project tracking capabilities, including
 * milestone tracking, progress monitoring, resource allocation, and performance
 * analytics.
 */

const fs = require('fs').promises;
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

// Project status values
const ProjectStatus = {
    PLANNING: "planning",
    INITIATED: "initiated",
    IN_PROGRESS: "in_progress",
    ON_HOLD: "on_hold",
    DELAYED: "delayed",
    COMPLETED: "completed",
    CANCELLED: "cancelled"
};

// Milestone status values
const MilestoneStatus = {
    NOT_STARTED: "not_started",
    IN_PROGRESS: "in_progress",
    COMPLETED: "completed",
    DELAYED: "delayed",
    CANCELLED: "cancelled"
};

// Task status values
const TaskStatus = {
    NOT_STARTED: "not_started",
    ASSIGNED: "assigned",
    IN_PROGRESS: "in_progress",
    BLOCKED: "blocked",
    COMPLETED: "completed",
    CANCELLED: "cancelled"
};

class Project {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.name = options.name || 'Untitled Project';
        this.description = options.description || '';
        this.startDate = options.startDate || new Date();
        this.endDate = options.endDate || new Date(Date.now() + 90 * 24 * 60 * 60 * 1000); // Default 90 days
        this.status = options.status || ProjectStatus.PLANNING;
        this.owner = options.owner || '';
        this.teamMembers = options.teamMembers || [];
        this.budget = options.budget || 0;
        this.spentBudget = options.spentBudget || 0;
        this.createdAt = options.createdAt || new Date();
        this.updatedAt = options.updatedAt || new Date();
        this.notes = options.notes || null;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class Milestone {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.projectId = options.projectId;
        this.name = options.name || 'Untitled Milestone';
        this.description = options.description || '';
        this.dueDate = options.dueDate || new Date();
        this.status = options.status || MilestoneStatus.NOT_STARTED;
        this.completedDate = options.completedDate || null;
        this.createdAt = options.createdAt || new Date();
        this.updatedAt = options.updatedAt || new Date();
        this.notes = options.notes || null;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class Task {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.projectId = options.projectId;
        this.milestoneId = options.milestoneId || null;
        this.name = options.name || 'Untitled Task';
        this.description = options.description || '';
        this.assignee = options.assignee || null;
        this.startDate = options.startDate || null;
        this.dueDate = options.dueDate || null;
        this.status = options.status || TaskStatus.NOT_STARTED;
        this.priority = options.priority || 2; // 1=low, 2=medium, 3=high, 4=critical
        this.estimatedEffort = options.estimatedEffort || null; // in hours
        this.actualEffort = options.actualEffort || null; // in hours
        this.dependencies = options.dependencies || []; // Task IDs this task depends on
        this.createdAt = options.createdAt || new Date();
        this.updatedAt = options.updatedAt || new Date();
        this.notes = options.notes || null;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class ProjectMetric {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.projectId = options.projectId;
        this.metricName = options.metricName || '';
        this.metricValue = options.metricValue || 0;
        this.unit = options.unit || '';
        this.recordedAt = options.recordedAt || new Date();
        this.notes = options.notes || null;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class ProjectTrackerJS {
    /**
     * Creates a new ProjectTrackerJS instance
     * @param {string} dbPath - Path to the SQLite database file
     */
    constructor(dbPath = './projects.db') {
        this.dbPath = dbPath;
        this.db = null;
        this.setupDatabase();

        // Configure logging
        this.logger = console;
    }

    /**
     * Sets up the database schema for project tracking
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create projects table
        this.db.run(`
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
        `);

        // Create milestones table
        this.db.run(`
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
        `);

        // Create tasks table
        this.db.run(`
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
        `);

        // Create metrics table
        this.db.run(`
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
        `);

        // Create project updates table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS project_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                update_text TEXT,
                author TEXT,
                created_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        `);
    }

    /**
     * Creates a new project
     * @param {string} name - Project name
     * @param {string} description - Project description
     * @param {Date} startDate - Project start date
     * @param {Date} endDate - Project end date
     * @param {string} owner - Project owner
     * @param {number} budget - Project budget
     * @returns {Promise<string>} The ID of the created project
     */
    async createProject(name, description, startDate, endDate, owner = '', budget = 0) {
        const project = new Project({
            name,
            description,
            startDate,
            endDate,
            owner,
            budget
        });

        await this.saveProjectToDb(project);
        this.logger.info(`Created project '${name}' (ID: ${project.id})`);
        return project.id;
    }

    /**
     * Saves a project to the database
     * @param {Project} project - The project to save
     * @returns {Promise<void>}
     */
    async saveProjectToDb(project) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO projects
                (id, name, description, start_date, end_date, status, owner,
                 team_members_json, budget, spent_budget, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                project.id, project.name, project.description,
                project.startDate.toISOString(), project.endDate.toISOString(),
                project.status, project.owner,
                JSON.stringify(project.teamMembers), project.budget,
                project.spentBudget, project.createdAt.toISOString(),
                project.updatedAt.toISOString(), project.notes
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
     * Retrieves a project by ID
     * @param {string} projectId - The project ID
     * @returns {Promise<Project|null>} The project or null if not found
     */
    async getProject(projectId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, name, description, start_date, end_date, status, owner,
                       team_members_json, budget, spent_budget, created_at, updated_at, notes
                FROM projects WHERE id = ?
            `);

            stmt.get([projectId], (err, row) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (!row) {
                    resolve(null);
                    return;
                }

                resolve(new Project({
                    id: row.id,
                    name: row.name,
                    description: row.description,
                    startDate: new Date(row.start_date),
                    endDate: new Date(row.end_date),
                    status: row.status,
                    owner: row.owner,
                    teamMembers: JSON.parse(row.team_members_json || '[]'),
                    budget: row.budget,
                    spentBudget: row.spent_budget,
                    createdAt: new Date(row.created_at),
                    updatedAt: new Date(row.updated_at),
                    notes: row.notes
                }));
            });

            stmt.finalize();
        });
    }

    /**
     * Updates project attributes
     * @param {string} projectId - The project ID
     * @param {Object} updates - Object with attributes to update
     * @returns {Promise<boolean>} Whether the update was successful
     */
    async updateProject(projectId, updates) {
        const project = await this.getProject(projectId);
        if (!project) {
            return false;
        }

        // Update project attributes based on provided updates
        for (const [key, value] of Object.entries(updates)) {
            if (project.hasOwnProperty(key)) {
                project[key] = value;
            }
        }

        project.updatedAt = new Date();
        await this.saveProjectToDb(project);
        return true;
    }

    /**
     * Adds a team member to a project
     * @param {string} projectId - The project ID
     * @param {string} memberEmail - The team member's email
     * @returns {Promise<boolean>} Whether the member was added
     */
    async addTeamMember(projectId, memberEmail) {
        const project = await this.getProject(projectId);
        if (!project) {
            return false;
        }

        if (!project.teamMembers.includes(memberEmail)) {
            project.teamMembers.push(memberEmail);
            project.updatedAt = new Date();
            await this.saveProjectToDb(project);
            this.logger.info(`Added team member '${memberEmail}' to project '${project.name}'`);
        }

        return true;
    }

    /**
     * Creates a new milestone for a project
     * @param {string} projectId - The project ID
     * @param {string} name - Milestone name
     * @param {string} description - Milestone description
     * @param {Date} dueDate - Milestone due date
     * @returns {Promise<string>} The ID of the created milestone
     */
    async createMilestone(projectId, name, description, dueDate) {
        const milestone = new Milestone({
            projectId,
            name,
            description,
            dueDate
        });

        await this.saveMilestoneToDb(milestone);
        this.logger.info(`Created milestone '${name}' for project '${projectId}'`);
        return milestone.id;
    }

    /**
     * Saves a milestone to the database
     * @param {Milestone} milestone - The milestone to save
     * @returns {Promise<void>}
     */
    async saveMilestoneToDb(milestone) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO milestones
                (id, project_id, name, description, due_date, status,
                 completed_date, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                milestone.id, milestone.projectId, milestone.name,
                milestone.description, milestone.dueDate.toISOString(),
                milestone.status,
                milestone.completedDate ? milestone.completedDate.toISOString() : null,
                milestone.createdAt.toISOString(), milestone.updatedAt.toISOString(),
                milestone.notes
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
     * Gets all milestones for a project
     * @param {string} projectId - The project ID
     * @returns {Promise<Milestone[]>} Array of milestones
     */
    async getMilestones(projectId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, project_id, name, description, due_date, status,
                       completed_date, created_at, updated_at, notes
                FROM milestones WHERE project_id = ?
                ORDER BY due_date
            `);

            stmt.all([projectId], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const milestones = rows.map(row => new Milestone({
                    id: row.id,
                    projectId: row.project_id,
                    name: row.name,
                    description: row.description,
                    dueDate: new Date(row.due_date),
                    status: row.status,
                    completedDate: row.completed_date ? new Date(row.completed_date) : null,
                    createdAt: new Date(row.created_at),
                    updatedAt: new Date(row.updated_at),
                    notes: row.notes
                }));

                resolve(milestones);
            });

            stmt.finalize();
        });
    }

    /**
     * Creates a new task for a project
     * @param {string} projectId - The project ID
     * @param {string} name - Task name
     * @param {string} description - Task description
     * @param {string} [assignee=null] - Task assignee
     * @param {Date} [dueDate=null] - Task due date
     * @param {number} [priority=2] - Task priority (1-4)
     * @param {number} [estimatedEffort=null] - Estimated effort in hours
     * @param {string} [milestoneId=null] - Associated milestone ID
     * @returns {Promise<string>} The ID of the created task
     */
    async createTask(projectId, name, description = '', assignee = null,
                    dueDate = null, priority = 2, estimatedEffort = null, milestoneId = null) {
        const task = new Task({
            projectId,
            name,
            description,
            assignee,
            dueDate,
            priority,
            estimatedEffort,
            milestoneId
        });

        await this.saveTaskToDb(task);
        this.logger.info(`Created task '${name}' for project '${projectId}'`);
        return task.id;
    }

    /**
     * Saves a task to the database
     * @param {Task} task - The task to save
     * @returns {Promise<void>}
     */
    async saveTaskToDb(task) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO tasks
                (id, project_id, milestone_id, name, description, assignee,
                 start_date, due_date, status, priority, estimated_effort,
                 actual_effort, dependencies_json, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                task.id, task.projectId, task.milestoneId, task.name,
                task.description, task.assignee,
                task.startDate ? task.startDate.toISOString() : null,
                task.dueDate ? task.dueDate.toISOString() : null,
                task.status, task.priority, task.estimatedEffort,
                task.actualEffort, JSON.stringify(task.dependencies),
                task.createdAt.toISOString(), task.updatedAt.toISOString(),
                task.notes
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
     * Gets all tasks for a project, optionally filtered by status
     * @param {string} projectId - The project ID
     * @param {TaskStatus} [status=null] - Optional status filter
     * @returns {Promise<Task[]>} Array of tasks
     */
    async getTasks(projectId, status = null) {
        return new Promise((resolve, reject) => {
            let query = `
                SELECT id, project_id, milestone_id, name, description, assignee,
                       start_date, due_date, status, priority, estimated_effort,
                       actual_effort, dependencies_json, created_at, updated_at, notes
                FROM tasks WHERE project_id = ?
            `;

            const params = [projectId];

            if (status) {
                query += " AND status = ?";
                params.push(status);
            }

            query += " ORDER BY priority DESC, due_date";

            const stmt = this.db.prepare(query);

            stmt.all(params, (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const tasks = rows.map(row => new Task({
                    id: row.id,
                    projectId: row.project_id,
                    milestoneId: row.milestone_id,
                    name: row.name,
                    description: row.description,
                    assignee: row.assignee,
                    startDate: row.start_date ? new Date(row.start_date) : null,
                    dueDate: row.due_date ? new Date(row.due_date) : null,
                    status: row.status,
                    priority: row.priority,
                    estimatedEffort: row.estimated_effort,
                    actualEffort: row.actual_effort,
                    dependencies: JSON.parse(row.dependencies_json || '[]'),
                    createdAt: new Date(row.created_at),
                    updatedAt: new Date(row.updated_at),
                    notes: row.notes
                }));

                resolve(tasks);
            });

            stmt.finalize();
        });
    }

    /**
     * Updates the status of a task
     * @param {string} taskId - The task ID
     * @param {TaskStatus} status - The new status
     * @returns {Promise<boolean>} Whether the update was successful
     */
    async updateTaskStatus(taskId, status) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                UPDATE tasks SET status = ?, updated_at = ?
                WHERE id = ?
            `);

            stmt.run([status, new Date().toISOString(), taskId], function(err) {
                if (err) {
                    reject(err);
                    return;
                }

                const rowsAffected = this.changes;

                if (rowsAffected > 0) {
                    console.info(`Updated task '${taskId}' status to ${status}`);

                    // If task is completed, update the milestone if needed
                    if (status === TaskStatus.COMPLETED) {
                        this.updateMilestoneProgress(taskId)
                            .then(() => resolve(rowsAffected > 0))
                            .catch(reject);
                        return;
                    }
                }

                resolve(rowsAffected > 0);
            });

            stmt.finalize();
        });
    }

    /**
     * Updates milestone progress based on task completion
     * @param {string} taskId - The completed task ID
     * @returns {Promise<void>}
     */
    async updateMilestoneProgress(taskId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare('SELECT milestone_id FROM tasks WHERE id = ?');

            stmt.get([taskId], async (err, result) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (result && result.milestone_id) {
                    const milestoneId = result.milestone_id;

                    // Count total and completed tasks for this milestone
                    const countStmt = this.db.prepare(`
                        SELECT COUNT(*) as count FROM tasks
                        WHERE milestone_id = ? AND status != ?
                    `);

                    countStmt.get([milestoneId, TaskStatus.COMPLETED], (err, row) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        if (row.count === 0) {
                            // All tasks for this milestone are completed
                            const updateStmt = this.db.prepare(`
                                UPDATE milestones
                                SET status = ?, completed_date = ?, updated_at = ?
                                WHERE id = ?
                            `);

                            updateStmt.run([
                                MilestoneStatus.COMPLETED,
                                new Date().toISOString(),
                                new Date().toISOString(),
                                milestoneId
                            ], function(err) {
                                if (err) {
                                    reject(err);
                                    return;
                                }

                                console.info(`Milestone '${milestoneId}' marked as completed`);
                                resolve();
                            });

                            updateStmt.finalize();
                        } else {
                            resolve();
                        }
                    });

                    countStmt.finalize();
                } else {
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Records a project metric
     * @param {string} projectId - The project ID
     * @param {string} metricName - Name of the metric
     * @param {number} metricValue - Value of the metric
     * @param {string} [unit=""] - Unit of measurement
     * @param {string} [notes=null] - Optional notes
     * @returns {Promise<string>} The ID of the recorded metric
     */
    async recordMetric(projectId, metricName, metricValue, unit = '', notes = null) {
        const metric = new ProjectMetric({
            projectId,
            metricName,
            metricValue,
            unit,
            notes
        });

        await this.saveMetricToDb(metric);
        this.logger.info(`Recorded metric '${metricName}' (${metricValue}${unit}) for project '${projectId}'`);
        return metric.id;
    }

    /**
     * Saves a metric to the database
     * @param {ProjectMetric} metric - The metric to save
     * @returns {Promise<void>}
     */
    async saveMetricToDb(metric) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO metrics
                (id, project_id, metric_name, metric_value, unit, recorded_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                metric.id, metric.projectId, metric.metricName,
                metric.metricValue, metric.unit,
                metric.recordedAt.toISOString(), metric.notes
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
     * Gets metrics for a project, optionally filtered by name
     * @param {string} projectId - The project ID
     * @param {string} [metricName=null] - Optional metric name filter
     * @returns {Promise<ProjectMetric[]>} Array of metrics
     */
    async getProjectMetrics(projectId, metricName = null) {
        return new Promise((resolve, reject) => {
            let query = "SELECT id, project_id, metric_name, metric_value, unit, recorded_at, notes FROM metrics WHERE project_id = ?";
            const params = [projectId];

            if (metricName) {
                query += " AND metric_name = ?";
                params.push(metricName);
            }

            query += " ORDER BY recorded_at DESC";

            const stmt = this.db.prepare(query);

            stmt.all(params, (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const metrics = rows.map(row => new ProjectMetric({
                    id: row.id,
                    projectId: row.project_id,
                    metricName: row.metric_name,
                    metricValue: row.metric_value,
                    unit: row.unit,
                    recordedAt: new Date(row.recorded_at),
                    notes: row.notes
                }));

                resolve(metrics);
            });

            stmt.finalize();
        });
    }

    /**
     * Calculates and returns project health score based on various metrics
     * @param {string} projectId - The project ID
     * @returns {Promise<Object>} Project health score and metrics
     */
    async getProjectHealthScore(projectId) {
        const project = await this.getProject(projectId);
        if (!project) {
            return { error: "Project not found" };
        }

        // Get milestones and tasks
        const milestones = await this.getMilestones(projectId);
        const tasks = await this.getTasks(projectId);

        // Calculate milestone health (0-100 scale)
        const milestoneCount = milestones.length;
        const completedMilestones = milestones.filter(m => m.status === MilestoneStatus.COMPLETED).length;
        const milestoneHealth = milestoneCount > 0 ? (completedMilestones / milestoneCount * 100) : 100;

        // Calculate task health (0-100 scale)
        const taskCount = tasks.length;
        const completedTasks = tasks.filter(t => t.status === TaskStatus.COMPLETED).length;
        const taskHealth = taskCount > 0 ? (completedTasks / taskCount * 100) : 100;

        // Calculate schedule health (0-100 scale)
        const daysTotal = (project.endDate - project.startDate) / (1000 * 60 * 60 * 24);
        const daysElapsed = (new Date() - project.startDate) / (1000 * 60 * 60 * 24);
        const expectedProgress = daysTotal > 0 ? (daysElapsed / daysTotal * 100) : 0;
        const actualProgress = taskHealth; // Using task completion as proxy for progress
        const scheduleVariance = actualProgress - expectedProgress;
        const scheduleHealth = Math.max(0, Math.min(100, 100 - Math.abs(scheduleVariance)));

        // Calculate budget health (0-100 scale)
        const budgetUtilization = project.budget > 0 ? (project.spentBudget / project.budget * 100) : 0;
        // Extra penalty for exceeding budget
        const budgetHealth = Math.max(0, Math.min(100, 100 - (budgetUtilization - 100) * 2));

        // Overall health score (weighted average)
        const overallHealth = (
            milestoneHealth * 0.3 +
            taskHealth * 0.3 +
            scheduleHealth * 0.2 +
            budgetHealth * 0.2
        );

        return {
            overallHealth: Math.round(overallHealth * 100) / 100,
            milestoneHealth: Math.round(milestoneHealth * 100) / 100,
            taskHealth: Math.round(taskHealth * 100) / 100,
            scheduleHealth: Math.round(scheduleHealth * 100) / 100,
            budgetHealth: Math.round(budgetHealth * 100) / 100,
            metrics: {
                totalMilestones: milestoneCount,
                completedMilestones: completedMilestones,
                totalTasks: taskCount,
                completedTasks: completedTasks,
                budgetUtilization: `${budgetUtilization.toFixed(2)}%`,
                projectDuration: `${Math.round(daysTotal)} days`,
                daysElapsed: Math.round(daysElapsed)
            }
        };
    }

    /**
     * Adds a project update/status report
     * @param {string} projectId - The project ID
     * @param {string} updateText - The update text
     * @param {string} author - The author of the update
     * @returns {Promise<boolean>} Whether the update was added
     */
    async addProjectUpdate(projectId, updateText, author) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO project_updates
                (project_id, update_text, author, created_at)
                VALUES (?, ?, ?, ?)
            `);

            stmt.run([projectId, updateText, author, new Date().toISOString()], function(err) {
                if (err) {
                    reject(err);
                } else {
                    console.info(`Added project update for project '${projectId}' by '${author}'`);
                    resolve(true);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Gets recent project updates
     * @param {string} projectId - The project ID
     * @param {number} [limit=10] - Maximum number of updates to return
     * @returns {Promise<Object[]>} Array of project updates
     */
    async getProjectUpdates(projectId, limit = 10) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT update_text, author, created_at
                FROM project_updates
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            `);

            stmt.all([projectId, limit], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const updates = rows.map(row => ({
                    updateText: row.update_text,
                    author: row.author,
                    createdAt: new Date(row.created_at)
                }));

                resolve(updates);
            });

            stmt.finalize();
        });
    }

    /**
     * Gets all overdue milestones and tasks
     * @returns {Promise<Object[]>} Array of overdue items
     */
    async getOverdueItems() {
        return new Promise(async (resolve, reject) => {
            try {
                // Get overdue milestones
                const milestoneStmt = this.db.prepare(`
                    SELECT m.name, m.project_id, p.name as project_name, m.due_date
                    FROM milestones m
                    JOIN projects p ON m.project_id = p.id
                    WHERE m.status != ? AND m.due_date < ?
                `);

                const overdueMilestones = await new Promise((resolve, reject) => {
                    milestoneStmt.all([
                        MilestoneStatus.COMPLETED,
                        new Date().toISOString()
                    ], (err, rows) => {
                        if (err) reject(err);
                        else {
                            resolve(rows.map(row => ({
                                type: "milestone",
                                name: row.name,
                                projectId: row.project_id,
                                projectName: row.project_name,
                                dueDate: new Date(row.due_date)
                            })));
                        }
                    });
                });

                // Get overdue tasks
                const taskStmt = this.db.prepare(`
                    SELECT t.name, t.project_id, p.name as project_name, t.due_date, t.assignee
                    FROM tasks t
                    JOIN projects p ON t.project_id = p.id
                    WHERE t.status NOT IN (?, ?, ?) AND t.due_date IS NOT NULL AND t.due_date < ?
                `);

                const overdueTasks = await new Promise((resolve, reject) => {
                    taskStmt.all([
                        TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.BLOCKED,
                        new Date().toISOString()
                    ], (err, rows) => {
                        if (err) reject(err);
                        else {
                            resolve(rows.map(row => ({
                                type: "task",
                                name: row.name,
                                projectId: row.project_id,
                                projectName: row.project_name,
                                dueDate: new Date(row.due_date),
                                assignee: row.assignee
                            })));
                        }
                    });
                });

                milestoneStmt.finalize();
                taskStmt.finalize();

                resolve([...overdueMilestones, ...overdueTasks]);
            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Closes the database connection
     */
    close() {
        if (this.db) {
            this.db.close();
        }
    }
}

module.exports = ProjectTrackerJS;

// If running as a standalone script
if (require.main === module) {
    const args = process.argv.slice(2);

    async function main() {
        const tracker = new ProjectTrackerJS();

        if (args.includes('--demo')) {
            // Create a demo project
            const projectId = await tracker.createProject(
                "Website Redesign Project",
                "Complete redesign of company website",
                new Date(),
                new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), // 90 days from now
                "project.manager@company.com",
                50000
            );

            console.log(`Created project: Website Redesign (ID: ${projectId})`);

            // Add team members
            await tracker.addTeamMember(projectId, "designer@company.com");
            await tracker.addTeamMember(projectId, "developer@company.com");
            await tracker.addTeamMember(projectId, "qa@company.com");

            // Create milestones
            const milestone1Id = await tracker.createMilestone(
                projectId,
                "Design Phase Complete",
                "Complete wireframes and mockups",
                new Date(Date.now() + 20 * 24 * 60 * 60 * 1000) // 20 days from now
            );

            const milestone2Id = await tracker.createMilestone(
                projectId,
                "Development Complete",
                "Complete front-end and back-end development",
                new Date(Date.now() + 60 * 24 * 60 * 60 * 1000) // 60 days from now
            );

            const milestone3Id = await tracker.createMilestone(
                projectId,
                "Launch Ready",
                "Site ready for production launch",
                new Date(Date.now() + 85 * 24 * 60 * 60 * 1000) // 85 days from now
            );

            console.log("Created 3 milestones for project");

            // Create tasks
            await tracker.createTask(
                projectId,
                "Create homepage mockup",
                "Design homepage layout and user flow",
                "designer@company.com",
                new Date(Date.now() + 10 * 24 * 60 * 60 * 1000), // 10 days from now
                3, // High priority
                16, // 16 hours
                milestone1Id
            );

            await tracker.createTask(
                projectId,
                "Implement homepage",
                "Develop homepage HTML/CSS/JS",
                "developer@company.com",
                new Date(Date.now() + 25 * 24 * 60 * 60 * 1000), // 25 days from now
                3, // High priority
                24, // 24 hours
                milestone2Id
            );

            await tracker.createTask(
                projectId,
                "QA Testing",
                "Test all website functionality",
                "qa@company.com",
                new Date(Date.now() + 75 * 24 * 60 * 60 * 1000), // 75 days from now
                4, // Critical priority
                40, // 40 hours
                milestone3Id
            );

            console.log("Created 3 tasks for project");

            // Record some metrics
            await tracker.recordMetric(projectId, "tasks_completed", 1, "count", "Initial task completed");
            await tracker.recordMetric(projectId, "budget_spent", 15000, "USD", "Initial development costs");

            // Add a project update
            await tracker.addProjectUpdate(
                projectId,
                "Project initiated successfully. Design phase underway.",
                "project.manager@company.com"
            );

            // Get project health
            const health = await tracker.getProjectHealthScore(projectId);
            console.log(`\\nProject Health Score: ${health.overallHealth}/100`);
            console.log(`Milestones: ${health.metrics.completedMilestones}/${health.metrics.totalMilestones} completed`);
            console.log(`Tasks: ${health.metrics.completedTasks}/${health.metrics.totalTasks} completed`);

            // Show overdue items (should be none in this example)
            const overdue = await tracker.getOverdueItems();
            console.log(`\\nOverdue items: ${overdue.length}`);

        } else {
            console.log("Project tracker initialized. Use the API to track projects.");
        }

        tracker.close();
    }

    main().catch(console.error);
}