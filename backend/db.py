from contextlib import contextmanager
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from .models import Base


def make_engine(url):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    args = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        args["connect_args"] = {"check_same_thread": False, "timeout": 30}
    else:
        args.update(
            pool_size=5,
            max_overflow=0,
            pool_timeout=10,
            connect_args={
                "sslmode": os.getenv("DB_SSLMODE", "require"),
                "connect_timeout": 10,
            },
        )
    engine = create_engine(url, **args)
    if url.startswith("sqlite:"):

        @event.listens_for(engine, "connect")
        def configure(dbapi, record):
            dbapi.isolation_level = None
            dbapi.execute("PRAGMA foreign_keys=ON")
            dbapi.execute("PRAGMA journal_mode=WAL")

        @event.listens_for(engine, "begin")
        def begin(conn):
            conn.exec_driver_sql("BEGIN IMMEDIATE")

    return engine


@contextmanager
def transaction(engine):
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        with db.begin():
            yield db


def initialize(engine):
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(87361245)"))
        Base.metadata.create_all(conn)
