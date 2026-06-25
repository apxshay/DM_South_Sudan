"""Load database connection settings from environment or .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str


def load_env() -> None:
    load_dotenv(ROOT / ".env")
    local_yaml = ROOT / "config" / "db.local.yaml"
    if local_yaml.exists():
        try:
            import yaml

            data = yaml.safe_load(local_yaml.read_text()) or {}
            for key, value in data.items():
                if key not in os.environ and value is not None:
                    os.environ[key] = str(value)
        except ImportError:
            pass


def postgres_config() -> PostgresConfig:
    load_env()
    return PostgresConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "dm_ssd"),
        password=os.environ.get("POSTGRES_PASSWORD", "dm_ssd_dev"),
        database=os.environ.get("POSTGRES_DB", "dm_south_sudan"),
    )


def neo4j_config() -> Neo4jConfig:
    load_env()
    return Neo4jConfig(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "dm_ssd_dev"),
    )
