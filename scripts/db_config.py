import os
from dataclasses import dataclass

import psycopg
from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        load_dotenv()

        db_name = os.getenv("POSTGRES_DB")
        db_user = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_host = os.getenv("POSTGRES_HOST", "localhost")

        missing = []
        if not db_name:
            missing.append("POSTGRES_DB")
        if not db_user:
            missing.append("POSTGRES_USER")
        if not db_password:
            missing.append("POSTGRES_PASSWORD")

        if missing:
            raise RuntimeError(
                "Hiányzó környezeti változó(k): " + ", ".join(missing)
            )

        return cls(
            host=db_host,
            port=int(db_port),
            dbname=db_name,
            user=db_user,
            password=db_password,
        )

    def to_psycopg_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }


def get_connection() -> psycopg.Connection:
    config = DatabaseConfig.from_env()
    return psycopg.connect(**config.to_psycopg_kwargs())