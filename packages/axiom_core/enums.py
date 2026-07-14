"""Shared enumerations for Axiom."""
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ServiceName(str, Enum):
    OLLAMA = "ollama"
    SEARXNG = "searxng"
    NEO4J = "neo4j"
    VALKEY = "valkey"
