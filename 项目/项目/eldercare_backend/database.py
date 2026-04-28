from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库文件的保存位置（会自动在当前文件夹生成 eldercare.db）
SQLALCHEMY_DATABASE_URL = "sqlite:///./eldercare.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()