# schemas.py
# ---------------- 文本日志 ----------------
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TextLogIn(BaseModel):
    # 可以不传；不传就用 default
    child_id: Optional[str] = None

    # 两个字段都设成可选：谁有值就用谁
    content: Optional[str] = None      # 孩子原话
    text: Optional[str] = None         # AI 回复

    sentiment: Optional[float] = None  # 只对孩子文本有用

    model_config = ConfigDict(extra="ignore")  # 多余字段直接忽略


class TextLogOut(BaseModel):
    id: int
    child_id: str
    content: str
    sentiment: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ✅ 新增：AI 日志的出入参
class AiLogOut(BaseModel):
    id: int
    child_id: str
    text: str
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
    noise_db: Optional[float] = None  # ✅ 噪音（dB）


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