"""Centralised settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=False,
    )

    # Pre-existing infrastructure
    axiom_ollama_base_url: str = "http://localhost:7434"
    axiom_searxng_url: str = "http://localhost:7300"
    axiom_neo4j_uri: str = "bolt://localhost:7687"
    axiom_neo4j_user: str = "neo4j"
    axiom_neo4j_password: str = "collosus"
    # Default matches docker-compose `axiom-redis:6379`; local dev override: redis://localhost:6379
    axiom_redis_url: str = "redis://localhost:6379"

    # Service ports
    axiom_api_port: int = 7200
    axiom_council_port: int = 7201
    axiom_axiomatizer_port: int = 7202
    axiom_web_port: int = 7100

    # Default models
    axiom_model_planner: str = "deepseek-r1:14b"
    axiom_model_synthesizer: str = "phi4:14b"
    axiom_model_code: str = "qwen2.5-coder:14b"
    axiom_model_critic: str = "llama3.1:8b"
    axiom_model_chairman: str = "deepseek-r1:14b"
    axiom_model_axiomatizer: str = "deepseek-r1:14b"

    # Runtime defaults
    axiom_breadth: int = 4
    axiom_depth: int = 3
    axiom_max_results_per_query: int = 5
    axiom_council_size: int = 3
    axiom_council_enabled: bool = True
    axiom_axiomatizer_enabled: bool = True
    axiom_graph_node_limit: int = 2000
    axiom_graph_edge_limit: int = 4000


# Module-level singleton
settings = Settings()
