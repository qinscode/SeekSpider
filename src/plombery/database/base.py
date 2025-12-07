import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from plombery.config import settings


def json_serializer(*args, **kwargs) -> str:
    return json.dumps(*args, default=jsonable_encoder, **kwargs)


def get_engine(poolclass=None):
    engine_kwargs = {
        "json_serializer": json_serializer,
        "connect_args": connect_args,
    }

    if poolclass:
        engine_kwargs["poolclass"] = poolclass

    # PostgreSQL/Supabase specific configuration
    if settings.database_url.startswith("postgresql"):
        # Disable hstore for PostgreSQL (Supabase pooler doesn't support it)
        engine_kwargs["use_native_hstore"] = False
        # Enable connection health checks to detect stale connections
        engine_kwargs["pool_pre_ping"] = True
        # Set pool recycle time to prevent connection timeout issues
        engine_kwargs["pool_recycle"] = 3600  # 1 hour

    return create_engine(
        settings.database_url,
        **engine_kwargs,
    )


connect_args = {}

if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

if settings.database_url.startswith("sqlite+libsql"):
    try:
        import sqlalchemy_libsql  # noqa: F401
    except ImportError:
        raise Exception(
            "To use libsql install the package sqlalchemy-libsql",
        )

    connect_args["auth_token"] = settings.database_auth_token

# PostgreSQL/Supabase specific configuration
if settings.database_url.startswith("postgresql"):
    # Connection timeout
    connect_args["connect_timeout"] = 10
    # Set keepalives to prevent connection from being closed
    connect_args["keepalives"] = 1
    connect_args["keepalives_idle"] = 30
    connect_args["keepalives_interval"] = 10
    connect_args["keepalives_count"] = 5


engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
