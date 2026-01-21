from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DATABASE_URL = os.getenv(
  'DATABASE_URL',
  'postgresql://postgres:postgres@localhost:5432/investigations'
)

engine = create_engine(DATABASE_URL, echo= True)

SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
  pass