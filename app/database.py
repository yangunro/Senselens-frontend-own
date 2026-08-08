import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker


# Load variables from .env
load_dotenv()


# Build PostgreSQL connection safely
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
    query={
        "sslmode": "require"
    },
)


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