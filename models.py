# models.py 追加
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from database import Base

class TextLog(Base):
    __tablename__ = "textlogs"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    content = Column(String)             # 文本（家长记录/AI转写/自评）
    sentiment = Column(Float, nullable=True)  # 情绪分( -1.0 ~ 1.0 )，可选：前端传或后端计算
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    level = Column(String, default="info")    # info/warn/critical
    title = Column(String)                    # 简短标题
    message = Column(String)                  # 详细说明
    source = Column(String)                   # 来源：environment/text/other
    acknowledged = Column(Boolean, default=False)  # 已确认/已读
    created_at = Column(DateTime(timezone=True), server_default=func.now())
class Environment(Base):
    __tablename__ = "environments"
    id = Column(Integer,primary_key=True, index=True)
    child_id = Column(String, index=True)
    temperature = Column(Float,nullable=True)
    humidity = Column(Float,nullable=True)
    light_lux = Column(Float,nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
# 新增：提醒表
class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String, index=True)
    title = Column(String)              # 提醒标题，如“睡前刷牙”
    cron = Column(String)               # 简化的重复规则，比如：DAILY 20:30 / WEEKLY MON 08:00
    channel = Column(String, default="multi")  # 提醒方式占位：multi/voice/vibration等
    '''
    "multi" = 多模态（语音+振动+推送）
    "voice" = 语音提醒
    "vibration" = 振动提醒
    目前只是个占位字段，后期你可以根据需要拓展。
    '''
    created_at = Column(DateTime(timezone=True), server_default=func.now())
