# schemas.py 追加
from pydantic import BaseModel
from typing import Optional

# ---- 文本日志 ----
class TextLogIn(BaseModel):
    child_id: str
    content: str
    sentiment: Optional[float] = None  # 可不传

class TextLogOut(TextLogIn):
    id: int

# ---- 预警 ----
class AlertOut(BaseModel):
    id: int
    child_id: str
    level: str
    title: str
    message: str
    source: str
    acknowledged: bool


class EnvironmentIn(BaseModel):
    child_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_lux: Optional[float] = None

class EnvironmentOut(EnvironmentIn):
    id: int

class ReminderIn(BaseModel):
    child_id: str
    title: str
    cron: str              # 例如：DAILY 20:30 或 WEEKLY MON 08:00
    channel: str = "multi"

class ReminderOut(ReminderIn):
    id: int