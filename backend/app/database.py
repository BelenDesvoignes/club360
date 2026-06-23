import os
from typing import Optional
from urllib.parse import parse_qs, urlparse
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
from fastapi import HTTPException, status
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
            "Invalid database URL: missing scheme. Expected something like " )
    # Accept common SQLAlchemy postgres dialect schemes.
    if not parsed.scheme.startswith("postgres"):
        raise RuntimeError( f"Invalid database URL scheme '{parsed.scheme}'. Expected a postgres URL.")
    if not parsed.hostname:
        raise RuntimeError("Invalid database URL: missing hostname. Expected something like ")

def get_engine():
    global _engine, _SessionLocal

    if _engine is not None:
        return _engine

    database_url = _get_database_url()
    if not database_url:
        raise RuntimeError( "Missing database URL env var. Set POSTGRES_URL_NON_POOLING (or POSTGRES_URL, POSTGRES_PRISMA_URL, SQLALCHEMY_DATABASE_URL, DATABASE_URL)." )
    database_url = _normalize_database_url(database_url)
    _validate_database_url(database_url)

    try:
        engine_kwargs = {"pool_pre_ping": True}
        connect_args = {"connect_timeout": 10}
        host = (urlparse(database_url).hostname or "").lower()

        # Configuración para Vercel
        if os.getenv("VERCEL") and host and host not in {"localhost", "127.0.0.1"}:
            connect_args["sslmode"] = "require"
            engine_kwargs["poolclass"] = NullPool
        else:
            # Configuración local
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 0

        # LA CORRECCIÓN ESTÁ AQUÍ:
        # Metemos connect_args dentro de engine_kwargs antes de crear el engine
        engine_kwargs["connect_args"] = connect_args

        # Ahora pasamos solo una cosa: las engine_kwargs (que ya incluyen los connect_args)
        _engine = create_engine(database_url, **engine_kwargs)

        Base.metadata.create_all(bind=_engine)
        inspector = inspect(_engine)
        if inspector.has_table("users"):
            columns = {column["name"] for column in inspector.get_columns("users")}
            if "profile_photo_url" not in columns:
                with _engine.begin() as connection:
                    connection.execute(text("ALTER TABLE users ADD COLUMN profile_photo_url TEXT"))

        if inspector.has_table("suspensions"):
            columns = {column["name"] for column in inspector.get_columns("suspensions")}
            if "activity_id" not in columns:
                with _engine.begin() as connection:
                    connection.execute(text("ALTER TABLE suspensions ADD COLUMN activity_id INTEGER"))

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

engine = get_engine()