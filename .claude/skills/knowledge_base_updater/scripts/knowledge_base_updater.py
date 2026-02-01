#!/usr/bin/env python3
"""
Knowledge Base Updater

This module provides automated updating and maintenance of the knowledge base for the Personal AI Employee system.
It ingests new information from various sources, validates content quality, integrates new knowledge with existing
information, and ensures the knowledge base remains current, accurate, and relevant.

Features:
- Multi-source information retrieval
- Content validation and quality assessment
- Knowledge integration and merging
- Quality assurance and fact-checking
- Search index maintenance
- Security and privacy controls
"""

import json
import os
import sqlite3
import logging
import threading
import time
import hashlib
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
from urllib.parse import urlparse
import re
import bs4
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document


class SourceType(Enum):
    """Types of information sources."""
    DOCUMENT = "document"
    WEB_PAGE = "web_page"
    API = "api"
    DATABASE = "database"
    USER_INPUT = "user_input"


class ContentType(Enum):
    """Types of content."""
    TEXT = "text"
    STRUCTURED_DATA = "structured_data"
    MULTIMEDIA = "multimedia"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class UpdateFrequency(Enum):
    """Frequency of updates."""
    REAL_TIME = "real_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


class QualityAssessment(Enum):
    """Quality levels for content."""
    EXCELLENT = 90
    GOOD = 75
    FAIR = 60
    POOR = 40


@dataclass
class KnowledgeEntry:
    """Data class to hold knowledge entry information."""
    id: str
    source_type: SourceType
    source_url: str
    content_type: ContentType
    title: str
    content: str
    entities: List[str]
    relationships: List[Dict[str, str]]
    quality_score: int
    relevance_score: int
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    tags: List[str]
    source_reliability: float


@dataclass
class UpdateRecord:
    """Data class to hold update record information."""
    id: str
    timestamp: str
    source_type: SourceType
    source_url: str
    status: str  # 'success', 'failed', 'skipped'
    quality_score: int
    error_message: Optional[str]
    metadata: Dict[str, Any]


class ContentExtractor:
    """Extracts content from various sources."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('ContentExtractor')

    def extract_from_source(self, source_type: SourceType, source_url: str) -> Optional[Dict[str, Any]]:
        """Extract content from the specified source."""
        try:
            if source_type == SourceType.WEB_PAGE:
                return self._extract_from_web_page(source_url)
            elif source_type == SourceType.DOCUMENT:
                return self._extract_from_document(source_url)
            elif source_type == SourceType.API:
                return self._extract_from_api(source_url)
            elif source_type == SourceType.USER_INPUT:
                # For user input, we assume the source_url contains the content
                return {
                    'title': 'User Input',
                    'content': source_url,
                    'entities': [],
                    'relationships': []
                }
            else:
                self.logger.error(f"Unsupported source type: {source_type}")
                return None
        except Exception as e:
            self.logger.error(f"Error extracting content from {source_type} at {source_url}: {e}")
            return None

    def _extract_from_web_page(self, url: str) -> Dict[str, Any]:
        """Extract content from a web page."""
        try:
            # Check if URL is allowed
            parsed_url = urlparse(url)
            allowed_domains = self.config.get('sources', {}).get('web_pages', {}).get('allowed_domains', [])

            domain_allowed = False
            for allowed_domain in allowed_domains:
                if allowed_domain.startswith('*'):
                    # Wildcard domain match
                    wildcard = allowed_domain[1:]  # Remove '*'
                    if parsed_url.netloc.endswith(wildcard):
                        domain_allowed = True
                        break
                elif parsed_url.netloc == allowed_domain:
                    domain_allowed = True
                    break

            if not domain_allowed:
                self.logger.warning(f"Domain not allowed: {parsed_url.netloc}")
                return None

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted tags
            for tag in soup(['script', 'style', 'nav', 'aside']):
                tag.decompose()

            title = soup.find('title')
            title_text = title.get_text() if title else 'Untitled'

            content = soup.get_text(separator=' ')
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content).strip()

            return {
                'title': title_text,
                'content': content,
                'entities': self._extract_entities(content),
                'relationships': []
            }
        except Exception as e:
            self.logger.error(f"Error extracting from web page {url}: {e}")
            return None

    def _extract_from_document(self, file_path: str) -> Dict[str, Any]:
        """Extract content from a document."""
        try:
            # Determine file type
            if file_path.lower().endswith('.pdf'):
                return self._extract_from_pdf(file_path)
            elif file_path.lower().endswith('.docx'):
                return self._extract_from_docx(file_path)
            elif file_path.lower().endswith('.txt'):
                return self._extract_from_txt(file_path)
            else:
                self.logger.error(f"Unsupported document format: {file_path}")
                return None
        except Exception as e:
            self.logger.error(f"Error extracting from document {file_path}: {e}")
            return None

    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract content from a PDF file."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"

            # Simple title extraction (first line or filename)
            title = os.path.basename(file_path).replace('.pdf', '').replace('_', ' ').title()

            return {
                'title': title,
                'content': content,
                'entities': self._extract_entities(content),
                'relationships': []
            }
        except Exception as e:
            self.logger.error(f"Error extracting from PDF {file_path}: {e}")
            return None

    def _extract_from_docx(self, file_path: str) -> Dict[str, Any]:
        """Extract content from a DOCX file."""
        try:
            doc = Document(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"

            title = os.path.basename(file_path).replace('.docx', '').replace('_', ' ').title()

            return {
                'title': title,
                'content': content,
                'entities': self._extract_entities(content),
                'relationships': []
            }
        except Exception as e:
            self.logger.error(f"Error extracting from DOCX {file_path}: {e}")
            return None

    def _extract_from_txt(self, file_path: str) -> Dict[str, Any]:
        """Extract content from a TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            title = os.path.basename(file_path).replace('.txt', '').replace('_', ' ').title()

            return {
                'title': title,
                'content': content,
                'entities': self._extract_entities(content),
                'relationships': []
            }
        except Exception as e:
            self.logger.error(f"Error extracting from TXT {file_path}: {e}")
            return None

    def _extract_from_api(self, api_endpoint: str) -> Dict[str, Any]:
        """Extract content from an API endpoint."""
        try:
            response = requests.get(api_endpoint, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Convert JSON data to text representation
            content = json.dumps(data, indent=2)

            # Try to extract meaningful title
            title = data.get('title', data.get('name', 'API Response'))

            return {
                'title': title,
                'content': content,
                'entities': self._extract_entities(content),
                'relationships': []
            }
        except Exception as e:
            self.logger.error(f"Error extracting from API {api_endpoint}: {e}")
            return None

    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction using regex patterns."""
        # This is a simplified entity extraction
        # In a real implementation, we would use NLP libraries like spaCy
        entities = []

        # Extract email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities.extend(emails)

        # Extract phone numbers
        phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        entities.extend(phones)

        # Extract capitalized words (potential entities)
        caps = re.findall(r'\b[A-Z][A-Z]+\b|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.extend([c for c in caps if len(c) > 2])  # Filter out short words

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)

        return unique_entities


class QualityAssessor:
    """Assesses the quality of content."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('QualityAssessor')

    def assess_quality(self, content: str, title: str = "", source_url: str = "") -> Tuple[int, Dict[str, float]]:
        """Assess the quality of content."""
        scores = {}

        # Word count score (0-100 based on min/max thresholds)
        word_count = len(content.split())
        min_words = self.config.get('validation', {}).get('content_quality', {}).get('minimum_word_count', 50)
        max_words = self.config.get('validation', {}).get('content_quality', {}).get('maximum_word_count', 10000)

        if word_count < min_words:
            scores['word_count'] = 0
        elif word_count > max_words:
            scores['word_count'] = 0
        else:
            # Normalize to 0-100 scale
            scores['word_count'] = min(100, max(0, ((word_count - min_words) / (max_words - min_words)) * 100))

        # Title relevance (if title exists)
        if title and content:
            title_words = set(title.lower().split())
            content_words = set(content.lower().split())
            common_words = title_words.intersection(content_words)
            scores['title_relevance'] = (len(common_words) / len(title_words)) * 100 if title_words else 0
        else:
            scores['title_relevance'] = 100  # No penalty if no title provided

        # Check for forbidden entities
        forbidden_entities = self.config.get('validation', {}).get('content_quality', {}).get('forbidden_entities', [])
        forbidden_found = 0
        content_lower = content.lower()
        for entity in forbidden_entities:
            if entity.lower() in content_lower:
                forbidden_found += 1

        scores['forbidden_content'] = max(0, 100 - (forbidden_found * 25))  # 25 points per forbidden term

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) if scores else 50

        # Apply threshold
        threshold = self.config.get('quality_thresholds', {}).get('overall_score', 75)
        final_score = max(0, min(100, overall_score))

        return int(final_score), scores

    def check_source_credibility(self, source_url: str) -> float:
        """Check the credibility of a source."""
        try:
            parsed_url = urlparse(source_url)
            domain = parsed_url.netloc

            # Check whitelist/blacklist
            whitelist = self.config.get('validation', {}).get('source_credibility', {}).get('whitelist_domains', [])
            blacklist = self.config.get('validation', {}).get('source_credibility', {}).get('blacklist_domains', [])

            # Check if domain is blacklisted
            for black_domain in blacklist:
                if black_domain in domain:
                    return 0.0

            # Check if domain is whitelisted
            for white_domain in whitelist:
                if white_domain in domain:
                    return 1.0

            # Default credibility based on domain type
            if domain.endswith(('.gov', '.edu', '.org')):
                return 0.9
            elif domain.endswith(('.com', '.net', '.co')):
                return 0.6
            else:
                return 0.5

        except Exception as e:
            self.logger.error(f"Error checking source credibility for {source_url}: {e}")
            return 0.5  # Default medium credibility


class KnowledgeIntegrator:
    """Integrates new knowledge with existing knowledge base."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('KnowledgeIntegrator')

    def integrate_knowledge(self, new_entry: KnowledgeEntry, existing_entries: List[KnowledgeEntry]) -> KnowledgeEntry:
        """Integrate new knowledge with existing knowledge."""
        # Check for duplicates or similar content
        similar_entry = self._find_similar_entry(new_entry, existing_entries)

        if similar_entry:
            # Merge or update existing entry
            merged_entry = self._merge_entries(similar_entry, new_entry)
            self.logger.info(f"Merged new content with existing entry: {similar_entry.id}")
            return merged_entry
        else:
            # New entry, return as is
            self.logger.info(f"Added new knowledge entry: {new_entry.id}")
            return new_entry

    def _find_similar_entry(self, new_entry: KnowledgeEntry, existing_entries: List[KnowledgeEntry]) -> Optional[KnowledgeEntry]:
        """Find a similar existing entry."""
        similarity_threshold = self.config.get('integration_strategies', {}).get('append', {}).get('similarity_threshold', 0.9)

        for existing in existing_entries:
            similarity = self._calculate_similarity(new_entry.content, existing.content)
            if similarity >= similarity_threshold:
                return existing

        return None

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        # Simple similarity calculation using common words
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _merge_entries(self, existing: KnowledgeEntry, new: KnowledgeEntry) -> KnowledgeEntry:
        """Merge two knowledge entries."""
        # Use newer content if conflict resolution is "newer_wins"
        conflict_resolution = self.config.get('integration_strategies', {}).get('merge', {}).get('conflict_resolution', 'newer_wins')

        if conflict_resolution == 'newer_wins':
            # Update existing entry with new information
            existing.updated_at = new.updated_at
            existing.content = new.content if len(new.content) > len(existing.content) else existing.content
            existing.entities = list(set(existing.entities + new.entities))
            existing.tags = list(set(existing.tags + new.tags))
            existing.quality_score = max(existing.quality_score, new.quality_score)
            existing.relevance_score = max(existing.relevance_score, new.relevance_score)
        elif conflict_resolution == 'combine':
            # Combine content
            existing.content = f"{existing.content}\n\nAlso:\n{new.content}"
            existing.entities = list(set(existing.entities + new.entities))
            existing.tags = list(set(existing.tags + new.tags))
            existing.quality_score = (existing.quality_score + new.quality_score) / 2
            existing.relevance_score = (existing.relevance_score + new.relevance_score) / 2

        return existing


class KnowledgeBaseRegistry:
    """Manages the knowledge base registry database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    entities TEXT,
                    relationships TEXT,
                    quality_score INTEGER,
                    relevance_score INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    source_reliability REAL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS update_records (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    quality_score INTEGER,
                    error_message TEXT,
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

    def add_knowledge_entry(self, entry: KnowledgeEntry):
        """Add a knowledge entry to the registry."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO knowledge_entries
                (id, source_type, source_url, content_type, title, content, entities,
                 relationships, quality_score, relevance_score, created_at, updated_at,
                 metadata, tags, source_reliability)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id, entry.source_type.value, entry.source_url,
                entry.content_type.value, entry.title, entry.content,
                json.dumps(entry.entities), json.dumps(entry.relationships),
                entry.quality_score, entry.relevance_score, entry.created_at,
                entry.updated_at, json.dumps(entry.metadata),
                json.dumps(entry.tags), entry.source_reliability
            ))

    def add_update_record(self, record: UpdateRecord):
        """Add an update record to the registry."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO update_records
                (id, timestamp, source_type, source_url, status, quality_score, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.id, record.timestamp, record.source_type.value,
                record.source_url, record.status, record.quality_score,
                record.error_message, json.dumps(record.metadata)
            ))

    def get_knowledge_entry_by_id(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, source_type, source_url, content_type, title, content, entities,
                       relationships, quality_score, relevance_score, created_at, updated_at,
                       metadata, tags, source_reliability
                FROM knowledge_entries WHERE id = ?
            ''', (entry_id,))
            row = cursor.fetchone()
            if row:
                return KnowledgeEntry(
                    id=row[0], source_type=SourceType(row[1]), source_url=row[2],
                    content_type=ContentType(row[3]), title=row[4], content=row[5],
                    entities=json.loads(row[6]) if row[6] else [],
                    relationships=json.loads(row[7]) if row[7] else [],
                    quality_score=row[8], relevance_score=row[9], created_at=row[10],
                    updated_at=row[11], metadata=json.loads(row[12]) if row[12] else {},
                    tags=json.loads(row[13]) if row[13] else [], source_reliability=row[14]
                )
        return None

    def get_all_knowledge_entries(self) -> List[KnowledgeEntry]:
        """Get all knowledge entries."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, source_type, source_url, content_type, title, content, entities,
                       relationships, quality_score, relevance_score, created_at, updated_at,
                       metadata, tags, source_reliability
                FROM knowledge_entries
            ''')
            rows = cursor.fetchall()
            entries = []
            for row in rows:
                entries.append(KnowledgeEntry(
                    id=row[0], source_type=SourceType(row[1]), source_url=row[2],
                    content_type=ContentType(row[3]), title=row[4], content=row[5],
                    entities=json.loads(row[6]) if row[6] else [],
                    relationships=json.loads(row[7]) if row[7] else [],
                    quality_score=row[8], relevance_score=row[9], created_at=row[10],
                    updated_at=row[11], metadata=json.loads(row[12]) if row[12] else {},
                    tags=json.loads(row[13]) if row[13] else [], source_reliability=row[14]
                ))
            return entries

    def get_update_records_by_status(self, status: str) -> List[UpdateRecord]:
        """Get update records by status."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, timestamp, source_type, source_url, status, quality_score, error_message, metadata
                FROM update_records WHERE status = ?
            ''', (status,))
            rows = cursor.fetchall()
            records = []
            for row in rows:
                records.append(UpdateRecord(
                    id=row[0], timestamp=row[1], source_type=SourceType(row[2]),
                    source_url=row[3], status=row[4], quality_score=row[5],
                    error_message=row[6], metadata=json.loads(row[7]) if row[7] else {}
                ))
            return records


class KnowledgeBaseUpdater:
    """Main knowledge base updater class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.knowledge_registry = KnowledgeBaseRegistry(os.getenv('KNOWLEDGE_BASE_REGISTRY_DB_PATH', ':memory:'))
        self.content_extractor = ContentExtractor({})
        self.quality_assessor = QualityAssessor({})
        self.knowledge_integrator = KnowledgeIntegrator({})

        # Load configuration
        self.config = self.load_config()

        # Reinitialize components with loaded config
        self.content_extractor = ContentExtractor(self.config)
        self.quality_assessor = QualityAssessor(self.config)
        self.knowledge_integrator = KnowledgeIntegrator(self.config)

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the knowledge base updater."""
        logger = logging.getLogger('KnowledgeBaseUpdater')
        logger.setLevel(getattr(logging, os.getenv('KNOWLEDGE_BASE_UPDATER_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('KNOWLEDGE_BASE_UPDATER_LOG_FILE_PATH', '/tmp/knowledge_base_updater.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'sources': {
                'web_pages': {
                    'enabled': True,
                    'allowed_domains': ['*.example.com'],
                    'rate_limit_requests_per_minute': 10
                },
                'documents': {
                    'enabled': True,
                    'supported_formats': ['.pdf', '.docx', '.txt', '.md']
                }
            },
            'validation': {
                'content_quality': {
                    'minimum_word_count': 50,
                    'maximum_word_count': 10000
                },
                'source_credibility': {
                    'whitelist_domains': ['gov', 'edu', 'org'],
                    'authority_score_threshold': 0.7
                }
            },
            'quality_thresholds': {
                'overall_score': 75
            },
            'update_frequency': {
                'daily': {
                    'enabled': True,
                    'time': '02:00'
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

    def update_knowledge_base(self, source_type: str, source_url: str) -> Dict[str, Any]:
        """Update the knowledge base with content from the specified source."""
        try:
            # Generate entry ID
            entry_id = f"kb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(source_url) % 10000}"

            # Extract content from source
            content_data = self.content_extractor.extract_from_source(SourceType(source_type), source_url)

            if not content_data:
                error_msg = f"Failed to extract content from {source_type} at {source_url}"
                self.logger.error(error_msg)

                # Record the failed update
                update_record = UpdateRecord(
                    id=f"upd_{entry_id}",
                    timestamp=datetime.now().isoformat(),
                    source_type=SourceType(source_type),
                    source_url=source_url,
                    status='failed',
                    quality_score=0,
                    error_message=error_msg,
                    metadata={}
                )
                self.knowledge_registry.add_update_record(update_record)

                return {"status": "failed", "error": error_msg}

            # Assess content quality
            quality_score, quality_metrics = self.quality_assessor.assess_quality(
                content_data['content'],
                content_data['title'],
                source_url
            )

            # Check source credibility
            source_reliability = self.quality_assessor.check_source_credibility(source_url)

            # Check if quality meets threshold
            threshold = self.config.get('quality_thresholds', {}).get('overall_score', 75)
            if quality_score < threshold:
                self.logger.info(f"Content quality {quality_score} below threshold {threshold}, skipping: {source_url}")

                # Record the skipped update
                update_record = UpdateRecord(
                    id=f"upd_{entry_id}",
                    timestamp=datetime.now().isoformat(),
                    source_type=SourceType(source_type),
                    source_url=source_url,
                    status='skipped',
                    quality_score=quality_score,
                    error_message=f"Quality score {quality_score} below threshold {threshold}",
                    metadata={"quality_metrics": quality_metrics}
                )
                self.knowledge_registry.add_update_record(update_record)

                return {
                    "status": "skipped",
                    "reason": f"Quality score {quality_score} below threshold {threshold}",
                    "quality_score": quality_score
                }

            # Create knowledge entry
            knowledge_entry = KnowledgeEntry(
                id=entry_id,
                source_type=SourceType(source_type),
                source_url=source_url,
                content_type=ContentType.TEXT,  # Default to text
                title=content_data['title'],
                content=content_data['content'],
                entities=content_data['entities'],
                relationships=content_data['relationships'],
                quality_score=quality_score,
                relevance_score=quality_score,  # For now, relevance equals quality
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata={
                    "quality_metrics": quality_metrics,
                    "source_reliability": source_reliability
                },
                tags=[],  # Could be populated based on content analysis
                source_reliability=source_reliability
            )

            # Get existing entries for integration
            existing_entries = self.knowledge_registry.get_all_knowledge_entries()

            # Integrate with existing knowledge
            integrated_entry = self.knowledge_integrator.integrate_knowledge(knowledge_entry, existing_entries)

            # Add to knowledge base
            self.knowledge_registry.add_knowledge_entry(integrated_entry)

            # Record successful update
            update_record = UpdateRecord(
                id=f"upd_{entry_id}",
                timestamp=datetime.now().isoformat(),
                source_type=SourceType(source_type),
                source_url=source_url,
                status='success',
                quality_score=quality_score,
                error_message=None,
                metadata={"integrated_entry_id": integrated_entry.id}
            )
            self.knowledge_registry.add_update_record(update_record)

            self.logger.info(f"Successfully updated knowledge base with content from {source_url}")

            return {
                "status": "success",
                "entry_id": integrated_entry.id,
                "quality_score": quality_score,
                "source_reliability": source_reliability
            }

        except Exception as e:
            self.logger.error(f"Error updating knowledge base from {source_type} at {source_url}: {e}")

            # Record the failed update
            error_id = f"upd_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(e)) % 10000}"
            update_record = UpdateRecord(
                id=error_id,
                timestamp=datetime.now().isoformat(),
                source_type=SourceType(source_type),
                source_url=source_url,
                status='failed',
                quality_score=0,
                error_message=str(e),
                metadata={}
            )
            self.knowledge_registry.add_update_record(update_record)

            return {"status": "error", "error": str(e)}

    def get_knowledge_entry(self, entry_id: str) -> Dict[str, Any]:
        """Get a specific knowledge entry."""
        entry = self.knowledge_registry.get_knowledge_entry_by_id(entry_id)
        if not entry:
            return {"error": f"Knowledge entry {entry_id} not found"}

        result = asdict(entry)
        result['source_type'] = entry.source_type.name
        result['content_type'] = entry.content_type.name
        return result

    def get_update_status(self) -> Dict[str, Any]:
        """Get the status of knowledge base updates."""
        all_entries = self.knowledge_registry.get_all_knowledge_entries()
        recent_updates = self.knowledge_registry.get_update_records_by_status('success')
        failed_updates = self.knowledge_registry.get_update_records_by_status('failed')
        skipped_updates = self.knowledge_registry.get_update_records_by_status('skipped')

        return {
            "total_entries": len(all_entries),
            "recent_updates": len(recent_updates),
            "failed_updates": len(failed_updates),
            "skipped_updates": len(skipped_updates),
            "last_update": recent_updates[0].timestamp if recent_updates else None
        }

    def run_scheduled_updates(self):
        """Run scheduled updates based on configuration."""
        # This would normally run in a separate thread
        sources_config = self.config.get('sources', {})

        # Example: Update from a sample source
        results = []
        if sources_config.get('web_pages', {}).get('enabled', False):
            # Update from a sample web page
            results.append(self.update_knowledge_base('web_page', 'https://www.example.com/sample'))

        if sources_config.get('documents', {}).get('enabled', False):
            # Update from a sample document (if it exists)
            sample_doc = '/tmp/sample.txt'
            if os.path.exists(sample_doc):
                results.append(self.update_knowledge_base('document', sample_doc))

        return results


def main():
    """Main function for testing the Knowledge Base Updater."""
    print("Knowledge Base Updater Skill")
    print("============================")

    # Initialize the knowledge base updater
    config_path = os.getenv('KNOWLEDGE_CONFIG_PATH', './knowledge_config.json')
    updater = KnowledgeBaseUpdater(config_path)

    print(f"Knowledge Base Updater initialized with config: {config_path}")

    # Create a sample document for testing
    sample_doc_path = '/tmp/sample_knowledge.txt'
    with open(sample_doc_path, 'w') as f:
        f.write("""
Artificial Intelligence Overview

Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals.

Key concepts in AI include:
- Machine learning: Algorithms that improve through experience
- Neural networks: Computing systems inspired by biological neural networks
- Natural language processing: Ability of computers to understand human language
- Computer vision: Ability to interpret and understand visual information

AI applications span numerous industries including healthcare, finance, transportation, and entertainment.
        """)

    # Update from the sample document
    print("\nUpdating knowledge base from sample document...")
    result = updater.update_knowledge_base('document', sample_doc_path)
    print(f"Document update result: {result}")

    # Get the status of the knowledge base
    status = updater.get_update_status()
    print(f"\nKnowledge base status: {status}")

    # Try to update from a web page (if allowed by config)
    print("\nAttempting to update from example.com...")
    web_result = updater.update_knowledge_base('web_page', 'https://www.example.com/')
    print(f"Web update result: {web_result}")

    # Show status again
    updated_status = updater.get_update_status()
    print(f"\nUpdated knowledge base status: {updated_status}")

    # Clean up sample file
    if os.path.exists(sample_doc_path):
        os.remove(sample_doc_path)

    print("\nKnowledge Base Updater is ready to update and maintain knowledge!")


if __name__ == "__main__":
    main()