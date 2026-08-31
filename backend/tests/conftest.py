import pytest
import sqlite3
import uuid
from sqlalchemy import create_engine, String, TypeDecorator, CHAR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID

# Patch: Adapt uuid.UUID to string in sqlite3
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
sqlite3.register_converter("VARCHAR", lambda b: b.decode())


# Compile PG's UUID type to VARCHAR(36) in SQLite
@compiles(UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"


# ── Fixtures cho test chuẩn (PostgreSQL / SessionLocal từ settings) ───────────
try:
    from app.core.database import Base as PgBase, engine as pg_engine, SessionLocal as PgSessionLocal

    @pytest.fixture(scope="module")
    def db():
        PgBase.metadata.create_all(bind=pg_engine)
        session = PgSessionLocal()
        yield session
        session.close()

except Exception:
    # Nếu không kết nối được PostgreSQL (CI / local không có PG), dùng SQLite fallback
    @pytest.fixture(scope="module")
    def db(db_session):
        yield db_session


# ── SQLite In-Memory Fixture (dành cho unit & E2E tests không cần PG) ─────────
@pytest.fixture(scope="function")
def db_session():
    """
    SQLite in-memory session fixture với hỗ trợ Supabase auth schema.
    Tạo tất cả tables mới, yield session sạch, drop sau mỗi test.
    UUID(as_uuid=True) được patch sang VARCHAR(36) qua @compiles.
    """
    from sqlalchemy import event
    from app.core.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False, "detect_types": sqlite3.PARSE_COLNAMES},
        poolclass=StaticPool,
    )

    # SQLite không hỗ trợ named schema "auth" — attach một in-memory DB để giả lập
    @event.listens_for(engine, "connect")
    def attach_auth_schema(dbapi_connection, connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS auth")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

