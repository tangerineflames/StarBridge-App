# main_server.py
from __future__ import annotations

import threading
from socket import socket, AF_INET, SOCK_DGRAM
from typing import Optional
import time
import os

import cv2
import numpy as np
from fastapi import FastAPI, Depends, Response, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# 你的本地模块
from database import Base, engine, SessionLocal
from models import Environment, TextLog, Alert, Reminder
from schemas import (
    EnvironmentIn, EnvironmentOut,
    TextLogIn, TextLogOut,
    AlertOut,
    ReminderIn, ReminderOut,
)

# -----------------------------------------------------------------------
# 配置（通过环境变量控制行为）
UDP_IP = os.getenv("VIDEO_UDP_IP", "0.0.0.0")   # 监听所有网卡（仅在启用 UDP 时生效）
UDP_PORT = int(os.getenv("VIDEO_UDP_PORT", "8080"))
UDP_RECV_BUFSIZE = int(os.getenv("VIDEO_UDP_RECV_BUFSIZE", str(1024 * 1024)))
FRAME_SIZE = (360, 640)         # (height, width)
MJPEG_SLEEP = float(os.getenv("MJPEG_SLEEP", "0.03"))

# 控制开关（部署时推荐把 ENABLE_UDP 设为 "0" 或不设；在本地测试可设为 "1"）
ENABLE_UDP = os.getenv("ENABLE_UDP", "0") in ("1", "true", "True")
# 是否在 app 启动时自动 create_all（默认关闭，建议用 Alembic 或 create_tables.py）
CREATE_TABLES_ON_STARTUP = os.getenv("CREATE_TABLES_ON_STARTUP", "0") in ("1", "true", "True")

# 全局：最新帧及锁
_latest_frame: Optional[np.ndarray] = None
_latest_lock = threading.Lock()
_stop_flag = False

# -----------------------------------------------------------------------
# FastAPI & DB
app = FastAPI(title="Remote Care API (Unified)")

# 可选在启动时建表（慎用：生产请使用 Alembic）
if CREATE_TABLES_ON_STARTUP:
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] create_all executed on startup (CREATE_TABLES_ON_STARTUP=1)")
    except Exception as e:
        print(f"[DB] create_all failed: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def ping():
    return {"ok": True, "msg": "remote-care backend running (video mode)"}


# ---------- 你原有的其它 API （CRUD 等）应当继续保留在这里 ----------
# （把你所有的路由、CRUD、业务逻辑保留，不需要改动）
# -----------------------------------------------------------------------


# UDP 接收线程（仅在 ENABLE_UDP=True 时启用）
def _udp_receiver():
    """后台接收线程：接收 JPEG（二进制）并解码为 BGR 帧，更新缓存。"""
    global _latest_frame, _stop_flag
    sock = socket(AF_INET, SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"[UDP] bind error {UDP_IP}:{UDP_PORT} -> {e}")
        return

    sock.settimeout(1.0)
    print(f"[UDP] Listening on {UDP_IP}:{UDP_PORT}")

    while not _stop_flag:
        try:
            data, addr = sock.recvfrom(UDP_RECV_BUFSIZE)
        except TimeoutError:
            continue
        except Exception as e:
            print(f"[UDP] recv error: {e}")
            time.sleep(0.05)
            continue

        if not data:
            continue

        try:
            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                print(f"[UDP] recv: cannot decode image from {len(data)} bytes (from {addr})")
                continue

            # 缩放到指定大小，避免内存爆增
            h, w = img.shape[:2]
            if (h, w) != (FRAME_SIZE[0], FRAME_SIZE[1]):
                img = cv2.resize(img, (FRAME_SIZE[1], FRAME_SIZE[0]))

            with _latest_lock:
                _latest_frame = img
        except Exception as e:
            print(f"[UDP] processing error: {e}")
            continue

    try:
        sock.close()
    except Exception:
        pass
    print("[UDP] Receiver stopped.")


def _blank_jpeg() -> bytes:
    blank = np.zeros((FRAME_SIZE[0], FRAME_SIZE[1], 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    return buf.tobytes() if ok else b""


def _encode_jpeg(img: Optional[np.ndarray]) -> Optional[bytes]:
    if img is None:
        return None
    try:
        ok, buf = cv2.imencode(".jpg", img)
        if not ok:
            return None
        return buf.tobytes()
    except Exception as e:
        print(f"[ENCODE] error: {e}")
        return None


def _frame_generator():
    """MJPEG generator for StreamingResponse"""
    boundary = b"--frame\r\n"
    header = b"Content-Type: image/jpeg\r\n\r\n"
    blank = _blank_jpeg()

    while True:
        with _latest_lock:
            frame = None if _latest_frame is None else _latest_frame.copy()
        jpg = _encode_jpeg(frame)
        if jpg is None:
            jpg = blank

        yield boundary + header + jpg + b"\r\n"
        time.sleep(MJPEG_SLEEP)


@app.get("/video")
def video_feed():
    """
    MJPEG 流（浏览器或 WebView 打开）：
      http://<server>/video
    """
    return StreamingResponse(
        _frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/video.jpg")
def single_frame():
    """返回最新一帧的静态 JPEG（或占位图）"""
    with _latest_lock:
        f = None if _latest_frame is None else _latest_frame.copy()
    if f is None:
        jpg = _blank_jpeg()
    else:
        b = _encode_jpeg(f)
        jpg = b if b is not None else _blank_jpeg()
    return Response(content=jpg, media_type="image/jpeg")


# -----------------------------------------------------------------------
# HTTP 上传帧接口（云端推荐）
@app.post("/upload_frame")
async def upload_frame(file: UploadFile = File(...)):
    """
    上传单帧 JPEG（multipart/form-data, field name: file）
    示例 curl:
      curl -F "file=@frame.jpg" https://<your-service>/upload_frame
    """
    # 简单校验 content type
    if file.content_type not in ("image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only JPEG images are accepted")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Failed to decode JPEG")

        # 缩放到指定尺寸
        h, w = img.shape[:2]
        if (h, w) != (FRAME_SIZE[0], FRAME_SIZE[1]):
            img = cv2.resize(img, (FRAME_SIZE[1], FRAME_SIZE[0]))

        with _latest_lock:
            global _latest_frame
            _latest_frame = img
    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

    return {"ok": True, "msg": "frame uploaded"}


# -----------------------------------------------------------------------
# 启停生命周期：根据 ENABLE_UDP 决定是否启动 UDP 线程
_udp_thread: Optional[threading.Thread] = None


@app.on_event("startup")
def _on_startup():
    global _udp_thread, _stop_flag
    _stop_flag = False
    if ENABLE_UDP:
        _udp_thread = threading.Thread(target=_udp_receiver, daemon=True)
        _udp_thread.start()
        print("[APP] Startup complete; UDP receiver running.")
    else:
        print("[APP] Startup complete; UDP disabled (use /upload_frame to push frames).")


@app.on_event("shutdown")
def _on_shutdown():
    global _stop_flag
    _stop_flag = True
    print("[APP] Shutdown signal sent; waiting for background threads to stop.")
