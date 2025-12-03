from __future__ import annotations

from typing import List, Optional
import threading
import time

import cv2
import numpy as np
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# 本地模块
from database import Base, engine, SessionLocal
from models import Environment, TextLog, Alert, Reminder, HealthStatus
from schemas import (
    EnvironmentIn, EnvironmentOut,
    TextLogIn, TextLogOut,
    AlertOut,
    ReminderIn, ReminderOut,
    HealthIn, HealthOut,
)

# ================================================================
# 全局配置：默认 child_id（POST 时可以不传）
# ================================================================
DEFAULT_CHILD_ID = "default"   # 你也可以改成 "c001" 看自己喜好

def normalize_child_id(child_id: Optional[str]) -> str:
    """
    把 None / 空字符串 都统一换成一个默认 child_id，
    这样设备发数据就可以不带 child_id 了。
    """
    if child_id is None:
        return DEFAULT_CHILD_ID
    cid = child_id.strip()
    return cid or DEFAULT_CHILD_ID


# ================================================================
# FastAPI 初始化 + Database 初始化
# ================================================================
app = FastAPI(title="Remote Care API (Unified, UDP Video)")
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def ping():
    return {"ok": True, "msg": "remote-care backend running (with UDP video)"}


# ================================================================
# 环境数据（带噪音）
# ================================================================
@app.post("/api/environment", response_model=EnvironmentOut)
def create_environment(item: EnvironmentIn, db: Session = Depends(get_db)):
    # ✅ 不传 child_id 时自动使用 DEFAULT_CHILD_ID
    child_id = normalize_child_id(item.child_id)

    obj = Environment(
        child_id=child_id,
        temperature=item.temperature,
        humidity=item.humidity,
        light_lux=item.light_lux,
        noise_db=item.noise_db,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # 自动分析规则
    analyze_environment(db, obj)

    # 你 schemas.py 里用了 from_attributes=True，可以直接这样返回
    return EnvironmentOut.model_validate(obj)

from typing import Optional

@app.get("/api/environment", response_model=List[EnvironmentOut])
def list_environment(child_id: Optional[str] = None,
                     db: Session = Depends(get_db)):
    cid = normalize_child_id(child_id)
    q = (
        db.query(Environment)
        .filter(Environment.child_id == cid)
        .order_by(Environment.created_at.desc())
        .all()
    )
    return [EnvironmentOut.model_validate(o) for o in q]

# ================================================================
# 文本流状态机：用来区分【孩子文本 / AI 回复】
# ================================================================
_text_lock = threading.Lock()
_expect_child_text = True   # True：下一条非 "1" 当作孩子；False：当作 AI

'''
# ❗这里建议去掉 response_model=TextLogOut，因为有时会返回 "忽略了 AI" 这种简单信息
@app.post("/api/textlog")
def create_textlog(item: TextLogIn, db: Session = Depends(get_db)):
    global _expect_child_text

    text = (item.content or "").strip()
    if not text:
        return {"ok": False, "msg": "empty text"}

    # 0️⃣ 收到 "1"：只当标记用，不入库
    if text == "1":
        with _text_lock:
            # 重置为“下一条非1的文本当作孩子”
            _expect_child_text = True
        return {"ok": True, "msg": "marker 1 received, no log created"}

    # 1️⃣ 这里一定是非 "1" 文本：根据当前状态判断是孩子还是 AI
    with _text_lock:
        is_child_text = _expect_child_text
        # 每处理一条非 "1"，就在孩子 / AI 间切换
        _expect_child_text = not _expect_child_text

    # 2️⃣ 如果是 AI 回复 -> 直接忽略（不写数据库）
    if not is_child_text:
        return {"ok": True, "msg": "ai reply ignored"}

    # 3️⃣ 走到这里：确定是孩子心情，正常入库并做情绪分析
    #    TextLogIn 里 child_id 可以是可选的，没传就走默认
    child_id = normalize_child_id(getattr(item, "child_id", None))

    score = item.sentiment
    if score is None:
        score = rule_based_sentiment(text)

    obj = TextLog(child_id=child_id, content=text, sentiment=score)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    analyze_textlog(db, obj)

    # 前端其实只看 status_code=200，不用关心具体字段
    return {
        "ok": True,
        "id": obj.id,
        "sentiment": obj.sentiment,
        "child_id": obj.child_id,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
    }
'''
@app.post("/api/textlog")
def create_textlog(item: TextLogIn, db: Session = Depends(get_db)):
    """
    调试版：
    - 所有非空文本都直接当作孩子日志写入数据库（包括 "1"、AI 回复）
    - 不再区分孩子 / AI
    """
    text = (item.content or "").strip()
    if not text:
        return {"ok": False, "msg": "empty text"}

    # child_id 可不传，统一走默认
    child_id = normalize_child_id(getattr(item, "child_id", None))

    # 情绪分：如果没传就用规则算
    score = item.sentiment
    if score is None:
        score = rule_based_sentiment(text)

    obj = TextLog(child_id=child_id, content=text, sentiment=score)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # 还是可以做情绪预警
    analyze_textlog(db, obj)

    # 返回一个简单 JSON，前端其实只看 200 即可
    return {
        "ok": True,
        "id": obj.id,
        "content": obj.content,
        "sentiment": obj.sentiment,
        "child_id": obj.child_id,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
    }

@app.get("/api/textlog", response_model=List[TextLogOut])
def list_textlog(child_id: Optional[str] = None,
                 db: Session = Depends(get_db)):
    cid = normalize_child_id(child_id)
    q = (
        db.query(TextLog)
        .filter(TextLog.child_id == cid)
        .order_by(TextLog.created_at.desc())
        .all()
    )
    return [TextLogOut.model_validate(o) for o in q]



# ================================================================
# 预警
# ================================================================
@app.get("/api/alerts", response_model=List[AlertOut])
def list_alerts(child_id: Optional[str] = None,
                db: Session = Depends(get_db)):
    cid = normalize_child_id(child_id)
    q = (
        db.query(Alert)
        .filter(Alert.child_id == cid)
        .order_by(Alert.created_at.desc())
        .all()
    )
    return [AlertOut.model_validate(o) for o in q]


@app.post("/api/alerts/{aid}/ack")
def ack_alert(aid: int, db: Session = Depends(get_db)):
    o = db.get(Alert, aid)
    if not o:
        return {"ok": False, "msg": "not found"}
    o.acknowledged = True
    db.commit()
    return {"ok": True}


# ================================================================
# 提醒
# ================================================================
@app.post("/api/reminder", response_model=ReminderOut)
def create_reminder(item: ReminderIn, db: Session = Depends(get_db)):
    child_id = normalize_child_id(item.child_id)

    obj = Reminder(
        child_id=child_id,
        title=item.title,
        cron=item.cron,
        channel=item.channel,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    return ReminderOut.model_validate(obj)

@app.get("/api/reminder", response_model=List[ReminderOut])
def list_reminder(child_id: Optional[str] = None,
                  db: Session = Depends(get_db)):
    cid = normalize_child_id(child_id)
    q = (
        db.query(Reminder)
        .filter(Reminder.child_id == cid)
        .order_by(Reminder.created_at.desc())
        .all()
    )
    return [ReminderOut.model_validate(o) for o in q]



# ================================================================
# ✅ 个人健康：心率 & 血氧
# ================================================================
@app.post("/api/health", response_model=HealthOut)
def create_health(item: HealthIn, db: Session = Depends(get_db)):
    child_id = normalize_child_id(item.child_id)

    obj = HealthStatus(
        child_id=child_id,
        heart_rate=item.heart_rate,
        spo2=item.spo2,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    analyze_health(db, obj)

    return HealthOut.model_validate(obj)

@app.get("/api/health", response_model=List[HealthOut])
def list_health(child_id: Optional[str] = None,
                db: Session = Depends(get_db)):
    cid = normalize_child_id(child_id)
    q = (
        db.query(HealthStatus)
        .filter(HealthStatus.child_id == cid)
        .order_by(HealthStatus.created_at.desc())
        .all()
    )
    return [HealthOut.model_validate(o) for o in q]



# ================================================================
# 规则引擎
# ================================================================
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
    noise = getattr(env, "noise_db", None)

    # 温度
    if t is not None and (t < 16 or t > 29):
        lvl = "critical" if (t < 14 or t > 31) else "warn"
        create_alert(
            db,
            child_id=env.child_id,
            level=lvl,
            source="environment",
            title="环境温度异常",
            message=f"当前温度 {t:.1f}℃，请注意调整。",
        )

    # 湿度
    if h is not None and (h < 30 or h > 75):
        create_alert(
            db,
            child_id=env.child_id,
            level="warn",
            source="environment",
            title="湿度不适",
            message=f"湿度 {h:.0f}%，请加湿或除湿。",
        )

    # 光照
    if lx is not None and lx < 50:
        create_alert(
            db,
            child_id=env.child_id,
            level="info",
            source="environment",
            title="光照偏暗",
            message="光照不足，请注意用眼。",
        )

    # ✅ 噪音（>65 dB 警告，>80 dB 严重）
    if noise is not None and noise > 65:
        lvl = "critical" if noise > 80 else "warn"
        create_alert(
            db,
            child_id=env.child_id,
            level=lvl,
            source="environment",
            title="环境噪音偏大",
            message=f"当前噪声约 {noise:.1f} dB，建议降低噪音或更换环境。",
        )

def rule_based_sentiment(text: str) -> float:
    neg = ["难过", "生气", "害怕", "烦", "讨厌", "哭"]
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
            title="情绪低落",
            message=f"文本情绪得分 {s:.2f}，建议关注沟通。",
        )

def analyze_health(db: Session, h: HealthStatus):
    hr = h.heart_rate
    spo2 = h.spo2

    # 心率简单范围（示例）
    if hr is not None and (hr < 55 or hr > 130):
        lvl = "critical" if (hr < 45 or hr > 150) else "warn"
        create_alert(
            db,
            child_id=h.child_id,
            level=lvl,
            source="health",
            title="心率异常",
            message=f"当前心率约 {hr} 次/分，请留意或咨询医生。",
        )

    # 血氧
    if spo2 is not None and spo2 < 94:
        lvl = "critical" if spo2 < 90 else "warn"
        create_alert(
            db,
            child_id=h.child_id,
            level=lvl,
            source="health",
            title="血氧偏低",
            message=f"当前血氧约 {spo2:.1f}%，建议及时关注。",
        )


# ================================================================
# ✅ UDP 视频接收 + MJPEG 输出（保持不变）
# ================================================================
UDP_IP = "0.0.0.0"
UDP_PORT = 8080
UDP_RECV_BUFSIZE = 1024 * 1024

FRAME_SIZE = (360, 640)

_latest_frame: Optional[np.ndarray] = None
_latest_lock = threading.Lock()
_stop_flag = False

def _udp_receiver():
    from socket import socket, AF_INET, SOCK_DGRAM, timeout as SocketTimeout

    global _latest_frame

    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(1.0)
    print(f"[UDP] Listening on {UDP_IP}:{UDP_PORT}")

    while not _stop_flag:
        try:
            data, addr = sock.recvfrom(UDP_RECV_BUFSIZE)
        except SocketTimeout:
            continue
        except Exception as e:
            print("[UDP] recv error:", e)
            time.sleep(0.05)
            continue

        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            continue

        if img.shape[0] != FRAME_SIZE[0] or img.shape[1] != FRAME_SIZE[1]:
            img = cv2.resize(img, (FRAME_SIZE[1], FRAME_SIZE[0]))

        with _latest_lock:
            _latest_frame = img

    try:
        sock.close()
    except Exception:
        pass
    print("[UDP] Receiver stopped.")

def _blank_jpeg() -> bytes:
    blank = np.zeros((FRAME_SIZE[0], FRAME_SIZE[1], 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    return buf.tobytes() if ok else b""

def _encode_jpeg(img: np.ndarray) -> Optional[bytes]:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buf.tobytes() if ok else None

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
        time.sleep(0.03)

@app.get("/video")
def video_feed():
    return StreamingResponse(
        _frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

_udp_thread: Optional[threading.Thread] = None

@app.on_event("startup")
def _on_startup():
    global _udp_thread, _stop_flag
    _stop_flag = False
    _udp_thread = threading.Thread(target=_udp_receiver, daemon=True)
    _udp_thread.start()
    print("[APP] Startup complete; UDP receiver running.")

@app.on_event("shutdown")
def _on_shutdown():
    global _stop_flag
    _stop_flag = True
    print("[APP] Shutdown signal sent; UDP receiver will stop.")
