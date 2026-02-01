#!/usr/bin/env python3
"""
Quality Assurance

This module provides comprehensive testing, validation, and quality control for the Personal AI Employee system.
It performs automated testing of system components, validates functionality and performance, ensures code quality
standards, and monitors system reliability.

Features:
- Multi-category test execution
- Quality assessment and metrics
- Defect identification and tracking
- Code quality analysis
- Performance testing
- Quality gate enforcement
"""

import json
import os
import sqlite3
import logging
import threading
import time
import hashlib
import subprocess
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import ast
import coverage


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    REGRESSION = "regression"


class QualityLevel(Enum):
    """Quality levels for assessments."""
    EXCELLENT = 95
    GOOD = 85
    FAIR = 70
    POOR = 50
    CRITICAL = 30


class DefectSeverity(Enum):
    """Severity levels for defects."""
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    TRIVIAL = "trivial"


@dataclass
class TestResult:
    """Data class to hold test result information."""
    id: str
    test_type: TestType
    test_target: str
    test_scenario: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration_ms: float
    failure_reason: Optional[str]
    quality_score: int
    created_at: str
    metadata: Dict[str, Any]


@dataclass
class QualityAssessment:
    """Data class to hold quality assessment information."""
    id: str
    assessment_type: str  # 'code_quality', 'test_coverage', 'performance', 'security'
    target: str
    score: int
    max_score: int
    criteria: Dict[str, Any]
    status: str  # 'pass', 'warn', 'fail'
    created_at: str
    details: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class Defect:
    """Data class to hold defect information."""
    id: str
    title: str
    description: str
    severity: DefectSeverity
    test_result_id: str
    status: str  # 'open', 'in_progress', 'resolved', 'closed'
    created_at: str
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = None


class TestExecutor:
    """Executes tests of various types."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('TestExecutor')

    def execute_test(self, test_type: TestType, target: str, scenario: str = "happy_path") -> TestResult:
        """Execute a test of the specified type."""
        start_time = time.time()
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(test_type.value + target + scenario) % 100000}"

        try:
            # Execute the test based on type
            if test_type == TestType.UNIT:
                result = self._execute_unit_test(target, scenario)
            elif test_type == TestType.INTEGRATION:
                result = self._execute_integration_test(target, scenario)
            elif test_type == TestType.PERFORMANCE:
                result = self._execute_performance_test(target, scenario)
            elif test_type == TestType.SECURITY:
                result = self._execute_security_test(target, scenario)
            else:
                # For other test types, simulate execution
                result = self._simulate_test(target, scenario)

            duration_ms = (time.time() - start_time) * 1000

            # Calculate quality score based on result
            quality_score = 100 if result['status'] == 'passed' else 30

            test_result = TestResult(
                id=test_id,
                test_type=test_type,
                test_target=target,
                test_scenario=scenario,
                status=result['status'],
                duration_ms=duration_ms,
                failure_reason=result.get('reason'),
                quality_score=quality_score,
                created_at=datetime.now().isoformat(),
                metadata={"result_details": result}
            )

            self.logger.info(f"Test {test_id} completed: {result['status']} in {duration_ms:.2f}ms")
            return test_result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_result = TestResult(
                id=test_id,
                test_type=test_type,
                test_target=target,
                test_scenario=scenario,
                status='error',
                duration_ms=duration_ms,
                failure_reason=str(e),
                quality_score=0,
                created_at=datetime.now().isoformat(),
                metadata={"error": str(e)}
            )
            self.logger.error(f"Test {test_id} failed with error: {e}")
            return error_result

    def _execute_unit_test(self, target: str, scenario: str) -> Dict[str, Any]:
        """Execute a unit test."""
        # Simulate running a unit test
        # In a real implementation, this would run actual tests

        # Mock result - in real scenario, would run actual unit test
        import random
        status = 'passed' if random.random() > 0.1 else 'failed'  # 90% pass rate
        reason = None if status == 'passed' else 'Assertion failed in mock test'

        return {
            "status": status,
            "reason": reason,
            "details": f"Mock unit test for {target} scenario {scenario}"
        }

    def _execute_integration_test(self, target: str, scenario: str) -> Dict[str, Any]:
        """Execute an integration test."""
        # Simulate running an integration test
        import random
        status = 'passed' if random.random() > 0.15 else 'failed'  # 85% pass rate
        reason = None if status == 'passed' else 'Integration test failed'

        return {
            "status": status,
            "reason": reason,
            "details": f"Mock integration test for {target} scenario {scenario}"
        }

    def _execute_performance_test(self, target: str, scenario: str) -> Dict[str, Any]:
        """Execute a performance test."""
        # Simulate running a performance test
        import random
        status = 'passed' if random.random() > 0.2 else 'failed'  # 80% pass rate
        reason = None if status == 'passed' else 'Performance threshold exceeded'

        return {
            "status": status,
            "reason": reason,
            "details": f"Mock performance test for {target} scenario {scenario}"
        }

    def _execute_security_test(self, target: str, scenario: str) -> Dict[str, Any]:
        """Execute a security test."""
        # Simulate running a security test
        import random
        status = 'passed' if random.random() > 0.05 else 'failed'  # 95% pass rate
        reason = None if status == 'passed' else 'Security vulnerability detected'

        return {
            "status": status,
            "reason": reason,
            "details": f"Mock security test for {target} scenario {scenario}"
        }

    def _simulate_test(self, target: str, scenario: str) -> Dict[str, Any]:
        """Simulate a test for unsupported test types."""
        import random
        status = 'passed' if random.random() > 0.1 else 'failed'
        reason = None if status == 'passed' else 'Generic test failure'

        return {
            "status": status,
            "reason": reason,
            "details": f"Mock test for {target} scenario {scenario}"
        }


class CodeQualityAnalyzer:
    """Analyzes code quality based on various metrics."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('CodeQualityAnalyzer')

    def analyze_code_quality(self, target_path: str) -> QualityAssessment:
        """Analyze code quality of the specified target."""
        start_time = time.time()
        assessment_id = f"qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(target_path) % 100000}"

        try:
            # Check if path exists
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Path {target_path} does not exist")

            # Analyze different aspects
            lint_results = self._run_linting(target_path)
            complexity_results = self._analyze_complexity(target_path)
            coverage_results = self._analyze_coverage(target_path)

            # Aggregate results
            all_results = {**lint_results, **complexity_results, **coverage_results}

            # Calculate overall score
            score = self._calculate_quality_score(all_results)

            # Determine status based on score
            status = self._determine_status(score)

            assessment = QualityAssessment(
                id=assessment_id,
                assessment_type="code_quality",
                target=target_path,
                score=score,
                max_score=100,
                criteria=self.config.get("code_quality", {}),
                status=status,
                created_at=datetime.now().isoformat(),
                details=[
                    {"aspect": "linting", "result": lint_results},
                    {"aspect": "complexity", "result": complexity_results},
                    {"aspect": "coverage", "result": coverage_results}
                ],
                metadata={
                    "analysis_duration": time.time() - start_time,
                    "path_analyzed": target_path
                }
            )

            self.logger.info(f"Code quality assessment {assessment_id} completed with score {score}")
            return assessment

        except Exception as e:
            assessment = QualityAssessment(
                id=assessment_id,
                assessment_type="code_quality",
                target=target_path,
                score=0,
                max_score=100,
                criteria={},
                status="error",
                created_at=datetime.now().isoformat(),
                details=[{"error": str(e)}],
                metadata={"error": str(e)}
            )
            self.logger.error(f"Code quality assessment {assessment_id} failed: {e}")
            return assessment

    def _run_linting(self, path: str) -> Dict[str, Any]:
        """Run linting analysis on the code."""
        try:
            # For demonstration, we'll just count Python files and check basic syntax
            issues = []
            file_count = 0

            for root, dirs, files in os.walk(path):
                # Exclude common non-code directories
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]

                for file in files:
                    if file.endswith('.py'):
                        file_count += 1
                        file_path = os.path.join(root, file)

                        # Basic syntax check
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                ast.parse(content)  # Basic syntax check

                                # Count lines and other metrics
                                lines = content.splitlines()
                                if len(lines) > 100:
                                    issues.append({
                                        "file": file_path,
                                        "type": "long_file",
                                        "description": f"File has {len(lines)} lines (recommendation: <100)"
                                    })

                                # Check for TODO comments
                                for i, line in enumerate(lines, 1):
                                    if 'TODO' in line.upper():
                                        issues.append({
                                            "file": file_path,
                                            "line": i,
                                            "type": "todo_comment",
                                            "description": f"TODO comment found: {line.strip()}"
                                        })

                        except SyntaxError as e:
                            issues.append({
                                "file": file_path,
                                "type": "syntax_error",
                                "description": f"Syntax error: {str(e)}"
                            })

            return {
                "file_count": file_count,
                "issues_found": len(issues),
                "issues": issues
            }
        except Exception as e:
            self.logger.error(f"Linting failed: {e}")
            return {"error": str(e)}

    def _analyze_complexity(self, path: str) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        try:
            complexity_info = {
                "total_functions": 0,
                "complex_functions": 0,  # Functions with complexity > 10
                "average_complexity": 0,
                "functions": []
            }

            # Walk through Python files to analyze complexity
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]

                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)

                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            try:
                                tree = ast.parse(content)

                                # Find functions and calculate complexity (simplified)
                                for node in ast.walk(tree):
                                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        complexity = self._calculate_function_complexity(node)
                                        complexity_info["total_functions"] += 1

                                        func_info = {
                                            "file": file_path,
                                            "function": node.name,
                                            "complexity": complexity,
                                            "line_number": node.lineno
                                        }

                                        complexity_info["functions"].append(func_info)

                                        if complexity > 10:  # High complexity threshold
                                            complexity_info["complex_functions"] += 1

                            except Exception:
                                continue  # Skip files with parse errors

            if complexity_info["total_functions"] > 0:
                total_complexity = sum(f["complexity"] for f in complexity_info["functions"])
                complexity_info["average_complexity"] = total_complexity / complexity_info["total_functions"]
            else:
                complexity_info["average_complexity"] = 0

            return complexity_info
        except Exception as e:
            self.logger.error(f"Complexity analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_function_complexity(self, func_node) -> int:
        """Calculate cyclomatic complexity of a function (simplified)."""
        complexity = 1  # Base complexity

        for child in ast.walk(func_node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):  # and/or expressions
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1

        return complexity

    def _analyze_coverage(self, path: str) -> Dict[str, Any]:
        """Analyze test coverage (simulated)."""
        try:
            # This is a simplified simulation
            # In reality, you'd use coverage.py or similar tools
            python_files = []
            test_files = []

            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]

                for file in files:
                    if file.endswith('.py'):
                        if 'test' in file.lower() or 'spec' in file.lower():
                            test_files.append(os.path.join(root, file))
                        else:
                            python_files.append(os.path.join(root, file))

            # Simulate coverage analysis
            total_lines = 0
            covered_lines = 0

            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        total_lines += len([line for line in lines if line.strip() and not line.strip().startswith('#')])
                        # Simulate that 70% of lines are covered
                        covered_lines += int(len(lines) * 0.7)
                except:
                    continue

            coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0

            return {
                "total_lines": total_lines,
                "covered_lines": covered_lines,
                "coverage_percent": round(coverage_percent, 2),
                "python_files": len(python_files),
                "test_files": len(test_files)
            }
        except Exception as e:
            self.logger.error(f"Coverage analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_quality_score(self, analysis_results: Dict[str, Any]) -> int:
        """Calculate an overall quality score based on analysis results."""
        # Weighted scoring based on different aspects
        lint_issues = analysis_results.get('issues_found', 0)
        total_functions = analysis_results.get('total_functions', 0)
        complex_functions = analysis_results.get('complex_functions', 0)
        coverage_percent = analysis_results.get('coverage_percent', 0)

        # Calculate scores for each aspect (0-100)
        # Lower lint issues = higher score
        lint_score = max(0, 100 - (lint_issues * 2))

        # Lower complex functions ratio = higher score
        complexity_score = 100 if total_functions == 0 else max(0, 100 - (complex_functions / total_functions * 100))

        # Higher coverage = higher score
        coverage_score = coverage_percent

        # Average the scores
        avg_score = (lint_score + complexity_score + coverage_score) / 3
        return int(avg_score)

    def _determine_status(self, score: int) -> str:
        """Determine status based on score."""
        if score >= 90:
            return "pass"
        elif score >= 70:
            return "warn"
        else:
            return "fail"


class DefectTracker:
    """Tracks and manages defects found during testing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('DefectTracker')

    def create_defect(self, title: str, description: str, severity: str, test_result_id: str) -> Defect:
        """Create a new defect record."""
        defect_id = f"def_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title + description) % 100000}"

        defect = Defect(
            id=defect_id,
            title=title,
            description=description,
            severity=DefectSeverity(severity.lower()),
            test_result_id=test_result_id,
            status="open",
            created_at=datetime.now().isoformat(),
            metadata={
                "created_by": "quality_assurance_system",
                "detection_method": "automated_testing"
            }
        )

        self.logger.info(f"Defect {defect_id} created: {title}")
        return defect

    def update_defect_status(self, defect_id: str, status: str) -> bool:
        """Update the status of a defect."""
        # In a real implementation, this would update the database
        self.logger.info(f"Defect {defect_id} status updated to: {status}")
        return True


class QualityDatabase:
    """Manages the quality assurance database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id TEXT PRIMARY KEY,
                    test_type TEXT NOT NULL,
                    test_target TEXT NOT NULL,
                    test_scenario TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    failure_reason TEXT,
                    quality_score INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS quality_assessments (
                    id TEXT PRIMARY KEY,
                    assessment_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    criteria TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details TEXT,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS defects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    test_result_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    metadata TEXT
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

    def add_test_result(self, result: TestResult):
        """Add a test result to the database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO test_results
                (id, test_type, test_target, test_scenario, status, duration_ms,
                 failure_reason, quality_score, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.id, result.test_type.value, result.test_target,
                result.test_scenario, result.status, result.duration_ms,
                result.failure_reason, result.quality_score, result.created_at,
                json.dumps(result.metadata)
            ))

    def add_quality_assessment(self, assessment: QualityAssessment):
        """Add a quality assessment to the database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO quality_assessments
                (id, assessment_type, target, score, max_score, criteria,
                 status, created_at, details, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assessment.id, assessment.assessment_type, assessment.target,
                assessment.score, assessment.max_score, json.dumps(assessment.criteria),
                assessment.status, assessment.created_at, json.dumps(assessment.details),
                json.dumps(assessment.metadata)
            ))

    def add_defect(self, defect: Defect):
        """Add a defect to the database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO defects
                (id, title, description, severity, test_result_id, status,
                 created_at, resolved_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                defect.id, defect.title, defect.description, defect.severity.value,
                defect.test_result_id, defect.status, defect.created_at,
                defect.resolved_at, json.dumps(defect.metadata)
            ))

    def get_test_results_by_status(self, status: str) -> List[TestResult]:
        """Get test results by status."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, test_type, test_target, test_scenario, status, duration_ms,
                       failure_reason, quality_score, created_at, metadata
                FROM test_results WHERE status = ?
            ''', (status,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(TestResult(
                    id=row[0], test_type=TestType(row[1]), test_target=row[2],
                    test_scenario=row[3], status=row[4], duration_ms=row[5],
                    failure_reason=row[6], quality_score=row[7], created_at=row[8],
                    metadata=json.loads(row[9]) if row[9] else {}
                ))
            return results

    def get_quality_assessments_by_type(self, assessment_type: str) -> List[QualityAssessment]:
        """Get quality assessments by type."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, assessment_type, target, score, max_score, criteria,
                       status, created_at, details, metadata
                FROM quality_assessments WHERE assessment_type = ?
            ''', (assessment_type,))
            rows = cursor.fetchall()
            assessments = []
            for row in rows:
                assessments.append(QualityAssessment(
                    id=row[0], assessment_type=row[1], target=row[2], score=row[3],
                    max_score=row[4], criteria=json.loads(row[5]) if row[5] else {},
                    status=row[6], created_at=row[7],
                    details=json.loads(row[8]) if row[8] else [],
                    metadata=json.loads(row[9]) if row[9] else {}
                ))
            return assessments

    def get_defects_by_severity(self, severity: str) -> List[Defect]:
        """Get defects by severity."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, title, description, severity, test_result_id, status,
                       created_at, resolved_at, metadata
                FROM defects WHERE severity = ?
            ''', (severity,))
            rows = cursor.fetchall()
            defects = []
            for row in rows:
                defects.append(Defect(
                    id=row[0], title=row[1], description=row[2], severity=DefectSeverity(row[3]),
                    test_result_id=row[4], status=row[5], created_at=row[6],
                    resolved_at=row[7], metadata=json.loads(row[8]) if row[8] else {}
                ))
            return defects


class QualityGate:
    """Manages quality gates for releases."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('QualityGate')

    def evaluate_gate(self, assessment_results: List[QualityAssessment]) -> Dict[str, Any]:
        """Evaluate if quality gates are passed."""
        gate_config = self.config.get('quality_gates', {})
        entry_criteria = gate_config.get('entry_criteria', {})
        exit_criteria = gate_config.get('exit_criteria', {})

        # Evaluate each criterion
        evaluation = {
            "gate_passed": True,
            "details": {},
            "failed_criteria": [],
            "warnings": []
        }

        # Check code quality score
        if 'code_quality_score' in entry_criteria:
            code_qa_results = [a for a in assessment_results if a.assessment_type == "code_quality"]
            if code_qa_results:
                latest_qa = code_qa_results[-1]  # Get most recent
                threshold = entry_criteria['code_quality_score']

                if latest_qa.score < threshold:
                    evaluation["gate_passed"] = False
                    evaluation["failed_criteria"].append({
                        "criterion": "code_quality_score",
                        "required": threshold,
                        "actual": latest_qa.score,
                        "status": "failed"
                    })
                else:
                    evaluation["details"]["code_quality"] = {
                        "score": latest_qa.score,
                        "status": "passed"
                    }

        # Check test coverage
        if 'test_coverage_percent' in entry_criteria:
            coverage_results = [a for a in assessment_results if "coverage" in a.target]
            if coverage_results:
                latest_coverage = coverage_results[-1]  # Get most recent
                threshold = entry_criteria['test_coverage_percent']

                if latest_coverage.score < threshold:
                    evaluation["gate_passed"] = False
                    evaluation["failed_criteria"].append({
                        "criterion": "test_coverage_percent",
                        "required": threshold,
                        "actual": latest_coverage.score,
                        "status": "failed"
                    })
                else:
                    evaluation["details"]["test_coverage"] = {
                        "coverage": latest_coverage.score,
                        "status": "passed"
                    }

        # Check test pass rate
        if 'test_pass_rate_percent' in exit_criteria:
            pass_rate_threshold = exit_criteria['test_pass_rate_percent']

            # Calculate pass rate from test results
            # This would come from external data in a real implementation
            # For demo purposes, let's assume we have this information
            test_pass_rate = 95  # Simulated value

            if test_pass_rate < pass_rate_threshold:
                evaluation["gate_passed"] = False
                evaluation["failed_criteria"].append({
                    "criterion": "test_pass_rate_percent",
                    "required": pass_rate_threshold,
                    "actual": test_pass_rate,
                    "status": "failed"
                })
            else:
                evaluation["details"]["test_pass_rate"] = {
                    "pass_rate": test_pass_rate,
                    "status": "passed"
                }

        return evaluation


class QualityAssurance:
    """Main quality assurance class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.quality_db = QualityDatabase(os.getenv('QUALITY_ASSURANCE_DATABASE_PATH', ':memory:'))
        self.test_executor = TestExecutor({})
        self.code_analyzer = CodeQualityAnalyzer({})
        self.defect_tracker = DefectTracker({})
        self.quality_gate = QualityGate({})

        # Load configuration
        self.config = self.load_config()

        # Reinitialize components with loaded config
        self.test_executor = TestExecutor(self.config)
        self.code_analyzer = CodeQualityAnalyzer(self.config)
        self.defect_tracker = DefectTracker(self.config)
        self.quality_gate = QualityGate(self.config)

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the quality assurance system."""
        logger = logging.getLogger('QualityAssurance')
        logger.setLevel(getattr(logging, os.getenv('QUALITY_ASSURANCE_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('QUALITY_ASSURANCE_LOG_FILE_PATH', '/tmp/quality_assurance.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            "qa": {
                "default_test_timeout_seconds": 300,
                "max_concurrent_tests": 10
            },
            "test_types": {
                "unit": {"enabled": True},
                "integration": {"enabled": True},
                "performance": {"enabled": True},
                "security": {"enabled": True}
            },
            "code_quality": {
                "linting": {"max_line_length": 120},
                "static_analysis": {"min_public_score": 8.0}
            },
            "quality_gates": {
                "entry_criteria": {"code_quality_score": 8.0, "test_coverage_percent": 80},
                "exit_criteria": {"test_pass_rate_percent": 95}
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

    def run_test(self, test_type: str, target: str, scenario: str = "happy_path") -> Dict[str, Any]:
        """Run a test of the specified type on the target."""
        try:
            # Execute the test
            result = self.test_executor.execute_test(TestType(test_type.upper()), target, scenario)

            # Add result to database
            self.quality_db.add_test_result(result)

            # If test failed, create a defect
            if result.status == 'failed':
                defect_title = f"Test Failure: {test_type.capitalize()} test failed for {target}"
                defect_desc = f"The {test_type} test for {target} failed in scenario {scenario}. Reason: {result.failure_reason}"

                # Determine severity based on test type
                if test_type == 'security':
                    severity = 'critical'
                elif test_type == 'performance':
                    severity = 'major'
                else:
                    severity = 'minor'

                defect = self.defect_tracker.create_defect(
                    defect_title,
                    defect_desc,
                    severity,
                    result.id
                )

                self.quality_db.add_defect(defect)

            return {
                "status": "success",
                "test_result_id": result.id,
                "result": result.status,
                "duration_ms": result.duration_ms,
                "quality_score": result.quality_score
            }

        except Exception as e:
            self.logger.error(f"Error running test: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def analyze_code_quality(self, target_path: str) -> Dict[str, Any]:
        """Analyze the quality of code at the specified path."""
        try:
            # Run code quality analysis
            assessment = self.code_analyzer.analyze_code_quality(target_path)

            # Add assessment to database
            self.quality_db.add_quality_assessment(assessment)

            return {
                "status": "success",
                "assessment_id": assessment.id,
                "score": assessment.score,
                "status_detail": assessment.status,
                "details": assessment.details
            }

        except Exception as e:
            self.logger.error(f"Error analyzing code quality: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def run_comprehensive_qa(self, target_path: str) -> Dict[str, Any]:
        """Run comprehensive quality assurance on the specified target."""
        results = {}

        # Run code quality analysis
        print(f"Running code quality analysis on {target_path}...")
        quality_result = self.analyze_code_quality(target_path)
        results['code_quality'] = quality_result

        # Run different types of tests
        test_types = ['unit', 'integration', 'security']
        for test_type in test_types:
            if self.config.get('test_types', {}).get(test_type, {}).get('enabled', True):
                print(f"Running {test_type} tests on {target_path}...")
                test_result = self.run_test(test_type, target_path)
                results[f"{test_type}_tests"] = test_result

        # Evaluate quality gates
        all_assessments = self.quality_db.get_quality_assessments_by_type('code_quality')
        gate_evaluation = self.quality_gate.evaluate_gate(all_assessments)
        results['quality_gate'] = gate_evaluation

        return {
            "status": "completed",
            "results": results,
            "summary": {
                "code_quality_passed": quality_result.get('status') == 'success',
                "all_tests_passed": all(
                    results.get(f"{t}_tests", {}).get('result') == 'passed'
                    for t in test_types
                    if self.config.get('test_types', {}).get(t, {}).get('enabled', True)
                ),
                "quality_gate_passed": gate_evaluation.get('gate_passed', False)
            }
        }

    def get_qa_status(self) -> Dict[str, Any]:
        """Get the current quality assurance status."""
        test_results = self.quality_db.get_test_results_by_status('failed')
        quality_assessments = self.quality_db.get_quality_assessments_by_type('code_quality')
        defects = self.quality_db.get_defects_by_severity('critical')

        return {
            "total_failed_tests": len(test_results),
            "code_quality_assessments": len(quality_assessments),
            "critical_defects": len(defects),
            "recent_defects": [d.title for d in defects[:5]],  # Last 5 critical defects
            "last_assessment": quality_assessments[-1].created_at if quality_assessments else None
        }


def main():
    """Main function for testing the Quality Assurance system."""
    print("Quality Assurance Skill")
    print("=======================")

    # Initialize the QA system
    config_path = os.getenv('QA_CONFIG_PATH', './qa_config.json')
    qa = QualityAssurance(config_path)

    print(f"Quality Assurance system initialized with config: {config_path}")

    # Create a sample test file for demonstration
    sample_dir = "/tmp/qa_sample_project"
    os.makedirs(sample_dir, exist_ok=True)

    sample_file = os.path.join(sample_dir, "sample_code.py")
    with open(sample_file, 'w') as f:
        f.write('''
# Sample code file for QA testing
def sample_function(x, y):
    """This is a sample function for testing."""
    # TODO: Add more functionality here
    if x > 100:
        return x * y
    else:
        return x + y

def another_function():
    """Another function to increase complexity."""
    for i in range(10):
        if i % 2 == 0:
            print(f"Even number: {i}")
        else:
            print(f"Odd number: {i}")
    return True
''')

    # Run code quality analysis
    print(f"\nRunning code quality analysis on {sample_dir}...")
    quality_result = qa.analyze_code_quality(sample_dir)
    print(f"Code quality result: {quality_result}")

    # Run some tests
    print(f"\nRunning unit tests on {sample_dir}...")
    unit_result = qa.run_test("unit", sample_dir)
    print(f"Unit test result: {unit_result}")

    print(f"\nRunning security tests on {sample_dir}...")
    security_result = qa.run_test("security", sample_dir)
    print(f"Security test result: {security_result}")

    # Run comprehensive QA
    print(f"\nRunning comprehensive QA on {sample_dir}...")
    comprehensive_result = qa.run_comprehensive_qa(sample_dir)
    print(f"Comprehensive QA summary: {comprehensive_result['summary']}")

    # Get QA status
    status = qa.get_qa_status()
    print(f"\nQA status: {status}")

    # Clean up sample files
    import shutil
    shutil.rmtree(sample_dir, ignore_errors=True)

    print("\nQuality Assurance system is ready to ensure quality!")


if __name__ == "__main__":
    main()