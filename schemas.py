# schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# ---------- 文本日志 ----------
class TextLogIn(BaseModel):
    child_id: str
    content: str
    sentiment: Optional[float] = None


class TextLogOut(TextLogIn):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# ---------- 环境 ----------
class EnvironmentIn(BaseModel):
    child_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_lux: Optional[float] = None
    noise_db: Optional[float] = None  # ✅ 新增：噪音（dB）


class EnvironmentOut(EnvironmentIn):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- 提醒 ----------
class ReminderIn(BaseModel):
    child_id: str
    title: str
    cron: str         # 例如：DAILY 20:30
    channel: str = "multi"


class ReminderOut(ReminderIn):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- 健康 ----------
class HealthIn(BaseModel):
    child_id: str
    heart_rate: Optional[int] = None   # 心率（次/分）
    spo2: Optional[float] = None       # 血氧 %


class HealthOut(HealthIn):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
