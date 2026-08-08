from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# By using sqlite we don't require any installation it automatically creates db file
DATABASE_URL = "sqlite:///./bank.db"


# create engine is use to establish connection between database and python code
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()