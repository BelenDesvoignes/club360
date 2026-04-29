import os
from typing import Optional
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base, sessionmaker


# Load environment from local dev files (Vercel uses Environment Variables).
load_dotenv()

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_database_url() -> Optional[str]:
    # Prefer the exact variables that Vercel's Supabase integration provides.
    for env_name in (
        "POSTGRES_URL_NON_POOLING",
        "POSTGRES_URL",
        "POSTGRES_PRISMA_URL",
        "SQLALCHEMY_DATABASE_URL",
        "DATABASE_URL",
    ):
        url = os.getenv(env_name)
        if url:
            return url
    return None


def _normalize_database_url(database_url: str) -> str:
    # Supabase/Heroku style URLs sometimes use postgres:// which SQLAlchemy 2 may reject.
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    return database_url


def _validate_database_url(database_url: str) -> None:
    parsed = urlparse(database_url)

    # Basic sanity checks so misconfigured env vars fail fast with a useful message.
    if not parsed.scheme or "://" not in database_url:
        raise RuntimeError(
            "Invalid database URL: missing scheme. Expected something like "
            "postgresql://user:pass@host:5432/dbname"
        )

    # Accept common SQLAlchemy postgres dialect schemes.
    if not parsed.scheme.startswith("postgres"):
        raise RuntimeError(
            f"Invalid database URL scheme '{parsed.scheme}'. Expected a postgres URL."
        )

    if not parsed.hostname:
        raise RuntimeError(
            "Invalid database URL: missing hostname. Expected something like "
            "postgresql://user:pass@host:5432/dbname"
        )


def get_engine():
    global _engine, _SessionLocal

    if _engine is not None:
        return _engine

    database_url = _get_database_url()
    if not database_url:
        # Do NOT crash at import time (important for serverless cold starts).
        # Raise only when DB is actually used.
        raise RuntimeError(
            "Missing database URL env var. Set POSTGRES_URL_NON_POOLING (or POSTGRES_URL, POSTGRES_PRISMA_URL, SQLALCHEMY_DATABASE_URL, DATABASE_URL)."
        )

    database_url = _normalize_database_url(database_url)
    _validate_database_url(database_url)

    try:
        engine_kwargs = {"pool_pre_ping": True}
        connect_args = {"connect_timeout": 10}

        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        host = (parsed.hostname or "").lower()

        # Supabase typically requires SSL. Prefer connect_args so the URL env var can stay clean.
        if os.getenv("VERCEL") and host and host not in {"localhost", "127.0.0.1"}:
            if "sslmode" not in query:
                connect_args["sslmode"] = "require"

        # Serverless: avoid long-lived pools / connection storms.
        if os.getenv("VERCEL"):
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 0

        if connect_args:
            engine_kwargs["connect_args"] = connect_args

        _engine = create_engine(database_url, **engine_kwargs)
        # Ensure the database schema exists before the first write.
        # This is safe to run repeatedly and keeps fresh Vercel deploys working.
        Base.metadata.create_all(bind=_engine)
    except Exception as exc:
        # Avoid leaking the full URL, but still provide useful diagnostics.
        raise RuntimeError(
            f"Database engine init failed: {exc.__class__.__name__}: {exc}"
        ) from exc

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        try:
            get_engine()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            )

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()