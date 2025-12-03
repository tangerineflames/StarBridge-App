# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.sql import func

from database import Base

class TextLog(Base):
    __tablename__ = "text_logs"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    content = Column(Text)
    sentiment = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ✅ 新增：专门存 AI 回复
class AiLog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    level = Column(String(16), default="info", nullable=False)   # info / warn / critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String(50), default="other", nullable=False) # environment / text / health / other
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
    noise_db = Column(Float, nullable=True)  # ✅ 新增：噪音，单位 dB
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Environment id={self.id} child_id={self.child_id}>"

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    cron = Column(String(64), nullable=False)   # 简化的重复规则
    channel = Column(String(32), default="multi", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Reminder id={self.id} cron={self.cron} child_id={self.child_id}>"

class HealthStatus(Base):
    __tablename__ = "health_status"  # ✅ 新表：个人健康

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(64), index=True, nullable=False)
    heart_rate = Column(Integer, nullable=True)  # 心率（次/分）
    spo2 = Column(Float, nullable=True)         # 血氧饱和度 %
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<HealthStatus id={self.id} child_id={self.child_id}>"
