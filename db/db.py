import os
import ssl
import asyncio
import certifi
from typing import Optional
from urllib.parse import parse_qsl, urlsplit, urlunsplit, urlencode

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models.entities import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[sessionmaker] = None
_logged_db_url = False


def _build_ssl_context() -> ssl.SSLContext:
    """
    Modo por defecto: verificación estricta con CA bundle de certifi.
    Modo dev (si DB_SSL_INSECURE=1): desactiva validación para saltar inspección TLS local.
    """
    if os.getenv("DB_SSL_INSECURE", "").strip() in ("1", "true", "True"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=certifi.where())
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def _mask_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        user = parsed.username
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        prefix = f"{user}:***@" if user else ("***@" if "@" in parsed.netloc else "")
        netloc = f"{prefix}{host}{port}"  
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    except Exception:
        return "***"


def _strip_sslmode(url: str) -> str:
    parsed = urlsplit(url)
    filtered_qs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "sslmode"]
    cleaned_query = urlencode(filtered_qs)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, cleaned_query, parsed.fragment))


def get_engine() -> AsyncEngine:
    global _engine, _logged_db_url

    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL no esta definido en .env")

        engine_url = _strip_sslmode(DATABASE_URL)

        if not _logged_db_url:
            try:
                print("DB_URL =", _mask_url(engine_url))
            finally:
                _logged_db_url = True

        ssl_ctx = _build_ssl_context()

        _engine = create_async_engine(
            engine_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            # asyncpg usa 'timeout' durante el handshake TLS y autent.
            connect_args={"ssl": ssl_ctx, "timeout": 15},
        )

    return _engine


def get_session_maker() -> sessionmaker:
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_maker


async def init_db(retries: int = 5):
    """
    Inicializa la BD con reintentos exponenciales (1,2,4,8,16 s) para absorber
    errores transitorios de red/TLS del pooler de Supabase.
    """
    delay = 1
    for attempt in range(1, retries + 1):
        try:
            async with get_engine().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("DB init OK")
            return
        except Exception as exc:
            if attempt == retries:
                print(f"DB init FAILED (final): {exc}")
                raise
            print(f"DB init failed ({attempt}/{retries}): {exc} -> retry in {delay}s")
            await asyncio.sleep(delay)
            delay *= 2
