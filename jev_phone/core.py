import base64
import io
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from .decisions import DecisionClient
from .adapters import AndroidAdapter, IOSAdapter, HarmonyAdapter
import threading

STEP_SEPARATORS = json.loads((Path(__file__).parent / "step_rules.json").read_text())["separators"]
STEP_SEPARATOR_PATTERN = re.compile("[" + re.escape(STEP_SEPARATORS) + "]+")

class ClickFailure(RuntimeError):
    pass

class RunFailure(ClickFailure):
    """Sequence stopped; report retains completed steps and failure index."""
    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def split_steps(text):
    steps = [s.strip() for s in STEP_SEPARATOR_PATTERN.split(text) if s.strip()]
    if not steps:
        raise ValueError("请输入至少一个点击目标。")
    if len(steps) > 20:
        raise ValueError("一次最多 20 步。")
    if any(len(s) > 500 for s in steps):
        raise ValueError("单步描述最多 500 字。")
    return steps


def candidates_from_tree(xml, width, height):
    nodes = []
    for node in ET.fromstring(xml).iter("node"):
        a = node.attrib
        b = list(map(int, re.findall(r"-?\d+", a.get("bounds", ""))))
        if a.get("clickable") != "true" or a.get("enabled") != "true" or len(b) != 4:
            continue
        if a.get("visible-to-user") == "false":
            continue
        b = [max(0, b[0]), max(0, b[1]), min(width, b[2]), min(height, b[3])]
        if b[2] <= b[0] or b[3] <= b[1]:
            continue
        def clean(s):
            return re.sub(r"(?<!\d)1\d{10}(?!\d)", "[phone]", s)
        nodes.append({"id": f"N{len(nodes)+1}", "bounds": b,
                      "text": clean(a.get("text", "")),
                      "description": clean(a.get("content-desc", "")),
                      "labels": list(dict.fromkeys(clean(n.get("text") or n.get("content-desc"))
                          for n in node.iter("node") if n.get("text") or n.get("content-desc")))})
    return nodes


def annotate(frame, nodes):
    im = Image.open(io.BytesIO(frame)).convert("RGB")
    font = None
    for path in ["/System/Library/Fonts/STHeiti Medium.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(path).exists():
            font = ImageFont.truetype(path, 20)
            break
    font = font or ImageFont.load_default()
    draw = ImageDraw.Draw(im)
    for n in nodes:
        x, y, z, b = n["bounds"]
        draw.rectangle((x, y, z-1, b-1), outline="#dc2020", width=2)
    for n in nodes:
        x, y, z, b = n["bounds"]
        # Fit the badge to the actual glyphs instead of a fixed 70x30 block.
        left, top, right, bottom = draw.textbbox((0, 0), n["id"], font=font)
        pad = 2
        badge_w = right-left+pad*2
        badge_h = bottom-top+pad*2
        label_x = min(x, max(0, im.width-badge_w))
        label_y = min(y, max(0, im.height-badge_h))
        draw.rectangle((label_x, label_y, label_x+badge_w-1, label_y+badge_h-1), fill="white")
        draw.text((label_x+pad-left, label_y+pad-top), n["id"], fill="#b00000", font=font)
    out = io.BytesIO()
    im.resize((round(im.width*.8), round(im.height*.8)), Image.Resampling.LANCZOS).save(out, format="JPEG", quality=85)
    return out.getvalue()


_device_locks = {}
_registry_lock = threading.Lock()

class PhoneClicker:
    """Single-target component. Different devices may run concurrently.

    Instances with the same adapter identity are serialized. No demo dependency.
    """
    def __init__(self, adapter, api_key, provider='openrouter', owns_adapter=False):
        if not api_key.strip():raise ValueError('API Key is required.')
        self.adapter=adapter
        self.serial=getattr(adapter,'serial',adapter.identity)
        self._key=api_key
        self.provider=provider
        self.owns_adapter=owns_adapter
        self.decisions=DecisionClient(api_key,provider)
        self.model=self.decisions.model
        with _registry_lock:self._lock=_device_locks.setdefault(adapter.identity,threading.RLock())
        self._closed=False

    def screenshot(self):
        with self._lock:
            if self._closed:raise ClickFailure('点击组件已经关闭。')
            return self.adapter.screenshot()

    def click(self,target,on_event=None):
        if not isinstance(target,str) or not target.strip():raise ValueError('A single click target is required.')
        with self._lock:
            if self._closed:raise ClickFailure('点击组件已经关闭。')
            return self._click(target.strip(),on_event)

    def run(self, text, on_event=None):
        from .stability import wait_fast_stable, policy_for_platform
        steps = split_steps(text)
        with self._lock:
            if self._closed:
                raise ClickFailure('点击组件已经关闭。')
            started = time.perf_counter()
            report = {'steps': steps, 'results': [], 'transitions': [], 'status': 'running'}
            frame = None
            emit = on_event or (lambda event: None)
            for index, target in enumerate(steps, 1):
                def event(data):
                    emit({**data, 'step': index})
                try:
                    if index > 1 and self.adapter.platform in ('android', 'harmony', 'ios'):
                        event({'phase': 'transition', 'message': '图片对比衔接下一步'})
                        settled = wait_fast_stable(self.adapter.screenshot,
                                                  policy=policy_for_platform(self.adapter.platform))
                        transition = {'before_step': index, 'stable': settled.stable,
                                      'elapsed_ms': settled.elapsed_ms, 'checks': settled.checks}
                        report['transitions'].append(transition)
                        event({'phase': 'transition_completed', 'message': '图片对比已返回',
                               'transition': transition})
                        if not settled.stable:
                            raise ClickFailure('步骤衔接图片对比超时，后续步骤已停止。')
                        frame = settled.bytes_
                    event({'phase': 'start', 'message': target})
                    result = self._click(target, event, frame)
                    report['results'].append(result)
                    frame = None
                except Exception as error:
                    message = str(error).replace(self._key, '[redacted]') if self._key else str(error)
                    report.update(status='failed', failed_step=index, error=message,
                                  total_ms=round((time.perf_counter()-started)*1000, 2))
                    raise RunFailure(message, report) from error
            report.update(status='completed', total_ms=round((time.perf_counter()-started)*1000, 2))
            return report

    def _click(self, target, on_event=None, frame=None):
        emit = on_event or (lambda event: None)
        start = time.perf_counter()
        times = {}
        def stage(name, action):
            t = time.perf_counter()
            try:return action()
            finally:times[name] = round(times.get(name,0)+(time.perf_counter()-t)*1000, 2)
        emit({"phase": "observe", "message": "读取当前 UI 树与截图"})
        observe_with_frame = getattr(self.adapter, 'observe_with_frame', None)
        observation = (observe_with_frame(stage, frame)
                       if frame is not None and observe_with_frame else self.adapter.observe(stage))
        frame=observation.image
        def prepare():
            width,height=Image.open(io.BytesIO(frame)).size
            nodes=candidates_from_tree(observation.tree,width,height)
            if not nodes:raise ClickFailure('当前页面没有可执行候选。')
            return nodes,annotate(frame,nodes)
        nodes,picture=stage('prepare',prepare)
        emit({"phase": "candidates", "message": f"生成 {len(nodes)} 个候选，正在请求模型", "image_bytes": picture, "before_bytes": frame, "candidate_count": len(nodes)})
        state = ["当前点击目标："+target, "只定位此目标，不规划其他动作。编号仅对当前图有效。"]
        if getattr(self.adapter,"model_note",""):state.append(self.adapter.model_note)
        state += ["当前候选："+json.dumps(nodes, ensure_ascii=False), {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,"+base64.b64encode(picture).decode(), "detail": "high"}}]
        criteria = {**{n['id']: '点击红框 '+n['id']+'，标签：'+(n['text'] or n['description'] or ' / '.join(n['labels']) or '无文字控件') for n in nodes}, 'NOT_FOUND':'当前候选没有可确认目标','UNCERTAIN':'不能安全确认'}
        def request():
            return self.decisions.request(state, criteria, '结合截图与候选选择当前目标，无法确认不要猜测。')
        data = stage("model", request)
        choice = data.get("answers", {}).get("node", {}).get("choice")
        node = next((n for n in nodes if n["id"] == choice), None)
        if node is None:
            raise ClickFailure(f"模型返回 {choice or '无效结果'}，未执行点击，后续步骤已停止。")
        # Reject rotation during the request. Same-viewport page changes remain an experimental limitation.
        if getattr(self.adapter, "recheck_before_click", True) and tuple(stage("viewport_check", self.adapter.viewport)) != tuple(observation.viewport):
            raise ClickFailure("模型请求期间设备视口变化，未执行旧坐标。")
        x, y, z, b = node["bounds"]
        point = [(x+z)//2, (y+b)//2]
        emit({"phase": "selected", "message": f"选择 {choice}，点击坐标 {point}", "selected": choice, "bounds": node["bounds"], "point": point})
        stage("click", lambda: self.adapter.click(*point,observation))
        total = round((time.perf_counter()-start)*1000, 2)
        result = {"target": target, "selected": choice, "point": point, "bounds": node["bounds"], "timings": times, "total_ms": total,
                  "non_model_ms": round(total-times["model"], 2), "status": "driver_completed", "model": data.get("model", self.model), "platform": self.adapter.platform, "device": self.adapter.identity}
        emit({"phase": "completed", "message": "点击接口已返回", "result": result})
        return result

    def close(self):
        with self._lock:
            if self._closed:return
            self._closed=True
            try:self.decisions.close()
            finally:
                self._key='';self.decisions._key=''
                if self.owns_adapter:self.adapter.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class AndroidClicker(PhoneClicker):
    def __init__(self,serial,api_key,provider='openrouter',device=None):
        super().__init__(AndroidAdapter(serial,device),api_key,provider,owns_adapter=True)

class IOSClicker(PhoneClicker):
    def __init__(self,wda_url,api_key,provider='openrouter',session_id=None):
        super().__init__(IOSAdapter(wda_url,session_id),api_key,provider,owns_adapter=True)

class HarmonyClicker(PhoneClicker):
    def __init__(self,serial,api_key,provider='openrouter',driver=None):
        super().__init__(HarmonyAdapter(serial,driver),api_key,provider,owns_adapter=True)

