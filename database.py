from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

#使用SQLite数据库（data.db)
DB_URL = "sqlite:///./data.db"
#创建数据库引擎
engine = create_engine(DB_URL,connect_args={"check_same_thread":False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()