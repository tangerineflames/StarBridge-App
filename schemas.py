# schemas.py
from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import Optional
from datetime import datetime
# ---------------- 文本日志 ----------------

class TextLogBase(BaseModel):
    # ✅ 核心：content 同时支持 JSON 里的 "content" 和 "text"
    content: str = Field(
        validation_alias=AliasChoices("content", "text")
    )
    sentiment: Optional[float] = None  # 情绪分可以前端传，也可以后端算

class TextLogIn(TextLogBase):
    # 可不传；单片机 / 简易客户端可以不管 child_id
    child_id: Optional[str] = None

class TextLogOut(TextLogBase):
    # 输出里我们保证一定有 child_id（后端 normalize 后写进 DB）
    id: int
    child_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- 预警 ----------------

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


# ---------------- 环境 ----------------

class EnvironmentBase(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_lux: Optional[float] = None
    noise_db: Optional[float] = None  #噪音（dB）


class EnvironmentIn(EnvironmentBase):
    # ✅ 可不传
    child_id: Optional[str] = None


class EnvironmentOut(EnvironmentBase):
    id: int
    child_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- 提醒 ----------------

class ReminderBase(BaseModel):
    title: str
    cron: str          # 例如：DAILY 20:30
    channel: str = "multi"


class ReminderIn(ReminderBase):
    # ✅ 可不传
    child_id: Optional[str] = None


class ReminderOut(ReminderBase):
    id: int
    child_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- 健康 ----------------

class HealthBase(BaseModel):
    heart_rate: Optional[int] = None   # 心率（次/分）
    spo2: Optional[float] = None       # 血氧 %


class HealthIn(HealthBase):
    # ✅ 可不传
    child_id: Optional[str] = None


class HealthOut(HealthBase):
    id: int
    child_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
