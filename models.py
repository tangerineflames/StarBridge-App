# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, func
from database import Base

# 注意：
# - 使用 Text 存放可能较长的 content 字段（比 String 更合适）
# - 为常用的短字符串指定长度（可提高可读性），但不是必需
# - created_at 使用 server_default=func.now()，在 Postgres 上工作良好

class TextLog(Base):
    __tablename__ = "textlogs"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    content = Column(Text, nullable=False)                 # 可能较长，使用 Text
    sentiment = Column(Float, nullable=True)                # -1.0 ~ 1.0，可选
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<TextLog id={self.id} child_id={self.child_id}>"

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    level = Column(String(16), default="info", nullable=False)   # info / warn / critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)                       # 详细说明，使用 Text
    source = Column(String(50), default="other", nullable=False) # environment / text / other
    acknowledged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Alert id={self.id} level={self.level} child_id={self.child_id}>"

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    light_lux = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Environment id={self.id} child_id={self.child_id}>"

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    cron = Column(String(64), nullable=False)   # 简化的重复规则（例如：DAILY 20:30）
    channel = Column(String(32), default="multi", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Reminder id={self.id} cron={self.cron} child_id={self.child_id}>"
