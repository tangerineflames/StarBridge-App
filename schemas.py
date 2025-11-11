# schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ---------- 文本日志 ----------
class TextLogIn(BaseModel):
    child_id: str
    content: str
    sentiment: Optional[float] = None  # 可选字段

class TextLogOut(TextLogIn):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- 预警 ----------
class AlertOut(BaseModel):
    id: int
    child_id: str
    level: str
    title: str
    message: str
    source: str
    acknowledged: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- 环境数据 ----------
class EnvironmentIn(BaseModel):
    child_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_lux: Optional[float] = None

class EnvironmentOut(EnvironmentIn):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- 提醒 ----------
class ReminderIn(BaseModel):
    child_id: str
    title: str
    cron: str                 # 例如：DAILY 20:30
    channel: str = "multi"

class ReminderOut(ReminderIn):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
