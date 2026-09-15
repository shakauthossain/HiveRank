import os
import socket
import time
from typing import Optional
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# NeonDB Connection URL
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_vk0AX1NsTPba@ep-quiet-snow-a1nvw1ht-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
)

_url = SQLALCHEMY_DATABASE_URL or ""
_parsed = urlparse(_url)
_db_host = _parsed.hostname or ""
_db_port = _parsed.port or 5432
_uses_neon_pooler = "-pooler." in _url or "pgbouncer=true" in _url.lower()


def _ipv4_addrs(host: str, port: int) -> list[str]:
    if not host:
        return []
    seen: list[str] = []
    try:
        for info in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if ip not in seen:
                seen.append(ip)
    except OSError:
        return []
    return seen


def _connect_args(hostaddr: Optional[str] = None) -> dict:
    args = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 3,
    }
    if "sslmode=" not in _url:
        args["sslmode"] = "require"
    if hostaddr:
        args["hostaddr"] = hostaddr
    return args


def _dbapi_connect():
    """Open a Postgres connection over IPv4 only, retrying Neon pooler IPs.

    Docker has no IPv6 path to Neon, and individual pooler A records can take
    >10s or time out. libpq would otherwise burn connect_timeout across every
    AAAA + A address and fail the request.
    """
    last_err: Optional[Exception] = None
    addrs = _ipv4_addrs(_db_host, _db_port) or [None]
    for attempt in range(3):
        for hostaddr in addrs:
            try:
                return psycopg2.connect(_url, **_connect_args(hostaddr))
            except psycopg2.OperationalError as exc:
                last_err = exc
        time.sleep(1.5 * (attempt + 1))
    if last_err:
        raise last_err
    raise psycopg2.OperationalError("Could not connect to the database")


# QueuePool + short-lived sessions: reuse TCP to Neon (Docker→SG is 2–9s).
# pool_pre_ping / recycle handle Neon dropping idle sockets.
# NullPool is avoided here — every Snapshot poll was opening a new SSL session.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    creator=_dbapi_connect,
    pool_pre_ping=True,
    pool_recycle=180 if _uses_neon_pooler else 280,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def close_db(db) -> None:
    try:
        db.close()
    except Exception:
        try:
            db.invalidate()
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        close_db(db)
