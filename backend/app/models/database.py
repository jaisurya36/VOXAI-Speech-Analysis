from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
import os

from app.config.settings import settings


def get_database_url() -> str:
    url = settings.database_url
    if url.startswith('sqlite:///'):
        # Make path absolute relative to backend dir
        db_path = url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(backend_dir, db_path)
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            url = f'sqlite:///{db_path}'
    return url


DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {}
)


@event.listens_for(engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    if 'sqlite' in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import analysis  # noqa: F401 - import to register models
    Base.metadata.create_all(bind=engine)
    print('Database initialized successfully.')
