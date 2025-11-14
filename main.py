from __future__ import annotations

from typing import List, Optional
import threading
import time

import cv2
import numpy as np
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# 本地模块
from database import Base, engine, SessionLocal
from models import Environment, TextLog, Alert, Reminder
from schemas import (
    EnvironmentIn, EnvironmentOut,
    TextLogIn, TextLogOut,
    AlertOut,
    ReminderIn, ReminderOut,
)

# ---------------------------------------------------------------------
# App 初始化 & DB
# ---------------------------------------------------------------------
app = FastAPI(title="Remote Care API (Unified)")
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def ping():
    return {"ok": True, "msg": "remote-care backend running (with video/ws)"}


# ---------------------------------------------------------------------
# 环境数据：接收和存储
# ---------------------------------------------------------------------
@app.post("/api/environment", response_model=EnvironmentOut)
def create_environment(
    item: EnvironmentIn,
    db: Session = Depends(get_db),
):
    obj = Environment(**item.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # 入库后触发分析
    analyze_environment(db, obj)

    # 注意：补上 created_at
    return EnvironmentOut(
        id=obj.id,
        child_id=obj.child_id,
        temperature=obj.temperature,
        humidity=obj.humidity,
        light_lux=obj.light_lux,
        created_at=obj.created_at,
    )


@app.get("/api/environment", response_model=List[EnvironmentOut])
def list_environment(child_id: str, db: Session = Depends(get_db)):
    q = (
        db.query(Environment)
        .filter(Environment.child_id == child_id)
        .order_by(Environment.created_at.desc())
        .all()
    )
    return [
        EnvironmentOut(
            id=o.id,
            child_id=o.child_id,
            humidity=o.humidity,
            temperature=o.temperature,
            light_lux=o.light_lux,
            created_at=o.created_at,
        )
        for o in q
    ]


# ---------------------------------------------------------------------
# 文本情绪：处理文本数据
# ---------------------------------------------------------------------
@app.post("/api/textlog", response_model=TextLogOut)
def create_textlog(item: TextLogIn, db: Session = Depends(get_db)):
    score = item.sentiment
    if score is None:
        score = rule_based_sentiment(item.content)

    obj = TextLog(child_id=item.child_id, content=item.content, sentiment=score)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # 文本情绪规则
    analyze_textlog(db, obj)

    return TextLogOut(
        id=obj.id,
        child_id=obj.child_id,
        content=obj.content,
        sentiment=obj.sentiment,
        created_at=obj.created_at,   # 补上 created_at
    )


@app.get("/api/textlog", response_model=List[TextLogOut])
def list_textlog(child_id: str, db: Session = Depends(get_db)):
    q = (
        db.query(TextLog)
        .filter(TextLog.child_id == child_id)
        .order_by(TextLog.created_at.desc())
        .all()
    )
    return [
        TextLogOut(
            id=o.id,
            child_id=o.child_id,
            content=o.content,
            sentiment=o.sentiment,
            created_at=o.created_at,   # 补上 created_at
        )
        for o in q
    ]


# ---------------------------------------------------------------------
# 预警：处理预警消息
# ---------------------------------------------------------------------
@app.get("/api/alerts", response_model=List[AlertOut])
def list_alerts(child_id: str, db: Session = Depends(get_db)):
    q = (
        db.query(Alert)
        .filter(Alert.child_id == child_id)
        .order_by(Alert.created_at.desc())
        .all()
    )
    return [
        AlertOut(
            id=o.id,
            child_id=o.child_id,
            level=o.level,
            title=o.title,
            message=o.message,
            source=o.source,
            acknowledged=o.acknowledged,
            created_at=o.created_at,   # 补上 created_at
        )
        for o in q
    ]


@app.post("/api/alerts/{aid}/ack")
def ack_alert(aid: int, db: Session = Depends(get_db)):
    o = db.get(Alert, aid)
    if not o:
        return {"ok": False, "msg": "not found"}
    o.acknowledged = True
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------
# 提醒：创建 / 列表
# ---------------------------------------------------------------------
@app.post("/api/reminder", response_model=ReminderOut)
def create_reminder(item: ReminderIn, db: Session = Depends(get_db)):
    obj = Reminder(**item.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ReminderOut(
        id=obj.id,
        child_id=obj.child_id,
        title=obj.title,
        cron=obj.cron,
        channel=obj.channel,
        created_at=obj.created_at,   # 补上 created_at
    )


@app.get("/api/reminder", response_model=List[ReminderOut])
def list_reminder(child_id: str, db: Session = Depends(get_db)):
    q = db.query(Reminder).filter(Reminder.child_id == child_id).all()
    return [
        ReminderOut(
            id=o.id,
            child_id=o.child_id,
            title=o.title,
            cron=o.cron,
            channel=o.channel,
            created_at=o.created_at,   # 补上 created_at
        )
        for o in q
    ]


# ---------------------------------------------------------------------
# 规则引擎
# ---------------------------------------------------------------------
def create_alert(
    db: Session, *, child_id: str, level: str, title: str, message: str, source: str
):
    a = Alert(
        child_id=child_id, level=level, title=title, message=message, source=source
    )
    db.add(a)
    db.commit()


def analyze_environment(db: Session, env: Environment):
    t = env.temperature
    h = env.humidity
    lx = env.light_lux

    if t is not None and (t < 16 or t > 29):
        lvl = "critical" if t < 14 or t > 31 else "warn"
        create_alert(
            db,
            child_id=env.child_id,
            level=lvl,
            source="environment",
            title="环境温度异常",
            message=f"当前温度 {t:.1f}℃，建议调整空调/衣物。",
        )

    if h is not None and (h < 30 or h > 75):
        create_alert(
            db,
            child_id=env.child_id,
            level="warn",
            source="environment",
            title="湿度不舒适",
            message=f"当前湿度 {h:.0f}%，建议加湿或除湿。",
        )

    if lx is not None and lx < 50:
        create_alert(
            db,
            child_id=env.child_id,
            level="info",
            source="environment",
            title="光照偏暗",
            message="光照偏暗，注意用眼卫生。",
        )


def rule_based_sentiment(text: str) -> float:
    neg = ["难过", "生气", "害怕", "不想", "烦", "讨厌", "哭"]
    pos = ["开心", "喜欢", "高兴", "满意", "放松"]
    score = 0.0
    if any(w in text for w in neg):
        score -= 0.6
    if any(w in text for w in pos):
        score += 0.6
    return max(-1.0, min(1.0, score))


def analyze_textlog(db: Session, tl: TextLog):
    s = tl.sentiment or 0.0
    if s <= -0.5:
        create_alert(
            db,
            child_id=tl.child_id,
            level="warn",
            source="text",
            title="情绪低落迹象",
            message=f"文本情绪分 {s:.2f}，建议关注沟通与疏导。",
        )


# ---------------------------------------------------------------------
# 视频流：WebSocket 上传 + MJPEG 输出
# ---------------------------------------------------------------------
FRAME_SIZE = (360, 640)

_latest_frame: Optional[np.ndarray] = None
_latest_lock = threading.Lock()


def _blank_jpeg() -> bytes:
    blank = np.zeros((FRAME_SIZE[0], FRAME_SIZE[1], 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    return buf.tobytes() if ok else b""


def _encode_jpeg(img: np.ndarray) -> Optional[bytes]:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not ok:
        return None
    return buf.tobytes()


def _frame_generator():
    boundary = b"--frame\r\n"
    header = b"Content-Type: image/jpeg\r\n\r\n"
    blank = _blank_jpeg()

    while True:
        with _latest_lock:
            frame = None if _latest_frame is None else _latest_frame.copy()
        jpg = _encode_jpeg(frame) if frame is not None else blank
        if jpg is None:
            jpg = blank

        yield boundary + header + jpg + b"\r\n"
        time.sleep(0.03)  # 控制帧率，大约 30fps -> 0.03s 一帧


@app.get("/video")
def video_feed():
    """App / 浏览器 访问的视频流接口（MJPEG）"""
    return StreamingResponse(
        _frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.websocket("/ws/video")
async def ws_video(websocket: WebSocket):
    """
    摄像头端通过 WebSocket 发送 JPEG 帧：
    - URL（云端）：wss://你的域名/ws/video
    - 消息内容：二进制 JPEG 数据
    """
    await websocket.accept()
    print("[WS] video client connected")

    global _latest_frame
    try:
        while True:
            data = await websocket.receive_bytes()
            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                continue

            # 缩放到统一尺寸，避免内存爆炸
            h, w = img.shape[:2]
            if (h, w) != (FRAME_SIZE[0], FRAME_SIZE[1]):
                img = cv2.resize(img, (FRAME_SIZE[1], FRAME_SIZE[0]))

            with _latest_lock:
                _latest_frame = img

    except WebSocketDisconnect:
        print("[WS] video client disconnected")
    except Exception as e:
        print(f"[WS] error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
