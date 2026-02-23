from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from books_rec_api.config import settings

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
