import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker


# Load variables from .env
load_dotenv()


def get_database_url():
    """Support either one connection URL or the existing DB_* settings."""
    connection_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DATABASE_URL")
    )

    if connection_url:
        if connection_url.startswith("postgres://"):
            connection_url = connection_url.replace(
                "postgres://",
                "postgresql+psycopg://",
                1,
            )
        elif connection_url.startswith("postgresql://"):
            connection_url = connection_url.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        return connection_url

    required_settings = {
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_NAME": os.getenv("DB_NAME"),
    }
    missing = [
        name
        for name, value in required_settings.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Database configuration is missing: "
            + ", ".join(missing)
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=required_settings["DB_USER"],
        password=required_settings["DB_PASSWORD"],
        host=required_settings["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=required_settings["DB_NAME"],
        query={"sslmode": "require"},
    )


DATABASE_URL = get_database_url()


# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


# Database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)
