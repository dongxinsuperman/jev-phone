import json
import os
import threading
import time
import uuid
from pathlib import Path

from adbutils import adb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
import uvicorn

from jev_phone import AndroidClicker, split_steps
from jev_phone.core import STEP_SEPARATORS
from .mirror import AndroidMirror

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("JEV_PHONE_DATA_DIR", ".data/demo")).resolve()
DATA.mkdir(parents=True, exist_ok=True)
mirror = AndroidMirror(DATA)
app = FastAPI(title="Jev Phone · Android demo")
app.mount("/assets", StaticFiles(directory=ROOT/"web"), name="assets")
app.mount("/evidence", StaticFiles(directory=DATA), name="evidence")
lock = threading.Lock()
clicker = None
jobs = {}
# Keep saved evidence reviewable when the local service restarts after an edit.
for saved in sorted(DATA.glob("*.json"), key=lambda p: p.stat().st_mtime)[-30:]:
    try:
        item = json.loads(saved.read_text())
        if item.get("id") == saved.stem and item.get("status") in {"completed", "failed"}:
            jobs[item["id"]] = item
    except (ValueError, OSError):
        pass
busy = False
session_epoch = 0

class ConnectBody(BaseModel):
    serial: str
    provider: Literal["openrouter", "openai"] = "openrouter"
    api_key: str = Field(default="", repr=False)

class RunBody(BaseModel):
    text: str

@app.get("/")
def index():
    return FileResponse(ROOT/"web/index.html")

@app.get("/api/step-rules")
def step_rules():
    return {"separators": STEP_SEPARATORS}

@app.get("/api/status")
def status():
    try:
        devices = [{"serial": d.serial} for d in adb.device_list()]
    except Exception:
        devices = []
    return {"devices": devices, "serial": clicker.serial if clicker else None, "busy": busy, "model": clicker.model if clicker else None, "provider": clicker.provider if clicker else "openrouter", "key_ready": bool(clicker)}

@app.post("/api/connect")
def connect(body: ConnectBody):
    global clicker
    with lock:
        if busy:
            raise HTTPException(409, "正在执行，请先等本轮结束。")
        available = [d.serial for d in adb.device_list()]
        if body.serial not in available:
            raise HTTPException(400, "请选择当前在线的 Android 设备。")
        key = body.api_key.strip()
        if not key:
            raise HTTPException(400, "请填写所选通道的 API Key。")
        try:
            if not clicker or clicker.serial != body.serial or clicker.provider != body.provider or clicker._key != key:
                new = AndroidClicker(body.serial, key, provider=body.provider)
                try:
                    new.decisions.prepare()
                except Exception:
                    new.close()
                    raise
                if clicker:
                    clicker.close()
                clicker = new
            frame = clicker.screenshot()
            name = "preview-"+uuid.uuid4().hex+".jpg"
            (DATA/name).write_bytes(frame)
            mirror.start(clicker.serial)
            return {"serial": clicker.serial, "image": "/evidence/"+name, "mirror": "/api/mirror"}
        except Exception as exc:
            raise HTTPException(400, str(exc).replace(key, "[redacted]"))

@app.post("/api/reset-connection")
def reset_connection():
    global clicker, session_epoch
    with lock:
        session_epoch += 1
        old, clicker = clicker, None
        if old:
            old._key = ""
            old.decisions._key = ""
    if old:
        old.close()
    mirror.stop()
    return {"reset": True}

@app.get("/api/mirror")
def live_mirror():
    if mirror.stopped:
        raise HTTPException(409, "请先连接 Android 设备。")
    return StreamingResponse(mirror.stream(), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-store"})

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    with lock:
        if job_id not in jobs:
            raise HTTPException(404, "未找到本轮执行。")
        return json.loads(json.dumps(jobs[job_id]))

@app.post("/api/run")
def run(body: RunBody):
    global busy
    try:
        steps = split_steps(body.text)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    with lock:
        if busy:
            raise HTTPException(409, "当前设备已有执行中的步骤。")
        if not clicker:
            raise HTTPException(400, "请先连接设备。")
        busy = True
        runner, epoch = clicker, session_epoch
        job_id = uuid.uuid4().hex
        jobs[job_id] = {"id": job_id, "status": "running", "steps": steps, "events": [], "results": [], "current_step": 0}
    def worker():
        global busy
        started = time.perf_counter()
        def emit(event):
            event = dict(event)
            if epoch != session_epoch and event.get("phase") != "error":
                raise RuntimeError("页面已刷新，本轮执行已停止。")
            with lock:
                jobs[job_id]['current_step'] = event.get('step', jobs[job_id]['current_step'])
            for field in ["image_bytes", "before_bytes"]:
                data = event.pop(field, None)
                if data:
                    name = f"{job_id}-{jobs[job_id]['current_step']}-{field}.jpg"
                    (DATA/name).write_bytes(data)
                    event["image" if field == "image_bytes" else "before"] = "/evidence/"+name
            event["step"] = jobs[job_id]["current_step"]
            event["elapsed_ms"] = round((time.perf_counter()-started)*1000)
            with lock:
                jobs[job_id]["events"].append(event)
                if event.get('phase') == 'completed':
                    jobs[job_id]['results'].append(event['result'])
        try:
            report = runner.run(body.text, on_event=emit)
            with lock:
                jobs[job_id]['transitions'] = report['transitions']
                jobs[job_id]["status"] = "completed"
        except Exception as exc:
            key = getattr(runner, "_key", "")
            message = str(exc)
            if key:
                message = message.replace(key, "[redacted]")
            emit({"phase": "error", "message": message})
            with lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = message
        finally:
            with lock:
                jobs[job_id]["wall_ms"] = round((time.perf_counter()-started)*1000, 2)
                busy = False
                snapshot = json.loads(json.dumps(jobs[job_id]))
            (DATA/f"{job_id}.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    threading.Thread(target=worker, daemon=True).start()
    return {"id": job_id, "steps": steps}

def main():
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("JEV_PHONE_PORT", "8765")), log_level="warning", timeout_graceful_shutdown=2)

if __name__ == "__main__":
    main()
