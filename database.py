# /path/to/your/project/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 从环境变量读取 DATABASE_URL；开发时可使用 sqlite（仅限本地）
# 在 Render 或其它 PaaS 上请确保 DATABASE_URL 指向托管的 Postgres / MySQL 等
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data.db")

# 是否为 sqlite（本地开发）
_is_sqlite = DATABASE_URL.startswith("sqlite")

# 通用 engine 选项
engine_kwargs = {"future": True}

# sqlite 需要特殊 connect_args
if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # sqlite 不需要连接池配置（也不建议在 PaaS 上使用 sqlite）
else:
    # 生产 / PaaS 下的连接池优化（可通过环境变量调节）
    # Render 上通常会提供一个 Postgres DATABASE_URL（格式示例：postgres://...）
    pool_size = int(os.environ.get("DATABASE_POOL_SIZE", 5))
    max_overflow = int(os.environ.get("DATABASE_MAX_OVERFLOW", 10))
    pool_timeout = int(os.environ.get("DATABASE_POOL_TIMEOUT", 30))
    # pool_pre_ping 可帮助在长连接失效时自动重连
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
        }
    )

# 是否打印 SQL（便于本地调试）
echo_flag = os.environ.get("DATABASE_ECHO", "false").lower() in ("1", "true", "yes")

# 创建 engine
engine = create_engine(DATABASE_URL, echo=echo_flag, **engine_kwargs)

# SessionLocal 用于依赖注入（FastAPI/Flask 等）
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Base 用于模型继承
Base = declarative_base()
