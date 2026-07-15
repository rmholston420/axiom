"""Shared enumerations for Axiom."""

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ServiceName(StrEnum):
    OLLAMA = "ollama"
    SEARXNG = "searxng"
    NEO4J = "neo4j"
    VALKEY = "valkey"
