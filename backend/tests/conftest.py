import pytest
import sqlite3
import uuid
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base, engine, SessionLocal

# Adapt uuid.UUID to string in sqlite3
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

# Compile PG's UUID type to VARCHAR(36) in SQLite
@compiles(UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
