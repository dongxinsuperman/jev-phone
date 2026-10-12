import io
import re
import tempfile
import time
import json
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from .base import Observation

class HarmonyAdapter:
    """Thin hmdriver2 adapter; no VM, account, or application management."""
    platform='harmony'
    recheck_before_click = False
    model_note='以截图可见控件为准，候选可能包括可点击容器中的独立图片区域。'
    def __init__(self,serial=None,driver=None):
        if driver is None:
            try:from hmdriver2.driver import Driver
            except ImportError as e:raise RuntimeError('Install jev-phone[harmony] and configure HDC.') from e
            driver=Driver(serial)
        self.driver=driver
        self.serial=serial or driver.serial
        self.identity='harmony:'+self.serial

    def viewport(self):
        # V3 refreshes dimensions once; no rotation probe or delayed retry.
        for name in ('display_size','display_rotation'):
            self.driver.__dict__.pop(name,None)
        return tuple(self.driver.display_size)

    def screenshot(self):
        with tempfile.TemporaryDirectory(prefix='jev-phone-hm-') as directory:
            path=Path(directory)/'screen.jpeg';self.driver.screenshot(str(path));return path.read_bytes()

    @staticmethod
    def convert(tree):
        def flag(value):return str(value).lower()=='true'
        def convert_node(item,parent_click=False,parent_bounds=None):
            a=item.get('attributes',{})
            b=list(map(int,re.findall(r'-?\d+',str(a.get('bounds','')))))
            valid=len(b)==4
            if valid and parent_bounds:
                b=[max(b[0],parent_bounds[0]),max(b[1],parent_bounds[1]),min(b[2],parent_bounds[2]),min(b[3],parent_bounds[3])]
            valid=valid and b[2]>b[0] and b[3]>b[1]
            native=flag(a.get('clickable',False));visible=flag(a.get('visible',True))
            active=(native or (parent_click and a.get('type')=='Image')) and visible and valid
            attrs={'text':str(a.get('text','')),'content-desc':str(a.get('description','')),'resource-id':str(a.get('id','')),'class':str(a.get('type','')),
                'clickable':str(active).lower(),'enabled':str(flag(a.get('enabled',False))).lower(),'visible-to-user':str(visible).lower(),
                'bounds':f'[{b[0]},{b[1]}][{b[2]},{b[3]}]' if valid else ''}
            out=ET.Element('node',attrs)
            for child in item.get('children',[]):out.append(convert_node(child,parent_click or native,b if valid else parent_bounds))
            return out
        root=ET.Element('hierarchy');root.append(convert_node(tree));return ET.tostring(root,encoding='unicode')

    def raw_tree(self):
        # V3's captureLayout reader, adapted to this instance's device lock.
        client = self.driver._client
        original = client._recv_msg

        def receive(_client, buff_size=4096, decode=False, print=True):
            payload = bytearray()
            sock = _client.sock
            old_timeout = sock.gettimeout()
            deadline = time.monotonic() + 5.0
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Harmony hierarchy deadline')
                    sock.settimeout(remaining)
                    chunk = sock.recv(65536)
                    if not chunk:
                        raise ConnectionError('Harmony hierarchy connection closed')
                    payload.extend(chunk)
                    if len(payload) > 16 * 1024 * 1024:
                        raise ValueError('Harmony hierarchy exceeds size limit')
                    try:
                        text = payload.decode('utf-8')
                        json.loads(text)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    return text if decode else payload
            finally:
                sock.settimeout(old_timeout)

        client._recv_msg = types.MethodType(receive, client)
        try:
            return client.invoke_captures('captureLayout').result
        finally:
            client._recv_msg = original

    def source(self):return self.convert(self.raw_tree())

    def observe(self,stage,frame=None):
        viewport=stage('capture',self.viewport)
        frame=frame if frame is not None else stage('screenshot',self.screenshot)
        tree=stage('tree',self.source)
        if Image.open(io.BytesIO(frame)).size!=viewport:
            raise RuntimeError('Harmony viewport and screenshot dimensions disagree.')
        return Observation(tree,frame,viewport)

    def observe_with_frame(self,stage,frame):
        return self.observe(stage,frame)

    def click(self,x,y,observation):
        # V3 direct UITest completion; bypass hmdriver2's @delay (600ms).
        return self.driver._invoke('Driver.click',args=[int(x),int(y)])

    def close(self):pass  # Shared device service remains owned by the caller.
