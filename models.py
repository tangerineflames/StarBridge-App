        # models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from database import Base

class TextLog(Base):
    __tablename__ = "textlogs"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    content = Column(String)                      # 文本（家长记录 / AI 转写 / 自评）
    sentiment = Column(Float, nullable=True)      # 情绪分 (-1.0 ~ 1.0)，可由前端传或后端计算
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    level = Column(String, default="info")       # info / warn / critical
    title = Column(String)                        # 简短标题
    message = Column(String)                      # 详细说明
    source = Column(String)                       # 来源：environment / text / other
    acknowledged = Column(Boolean, default=False) # 是否已确认/已读
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Environment(Base):
    __tablename__ = "environments"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    light_lux = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    title = Column(String)           # 提醒标题（如“睡前刷牙”）
    cron = Column(String)            # 简化的重复规则（例如：DAILY 20:30）
    channel = Column(String, default="multi")
    # channel 的含义（占位）： "multi" = 多模态（语音+振动+推送），"voice" = 语音，"vibration" = 振动
    created_at = Column(DateTime(timezone=True), server_default=func.now())

