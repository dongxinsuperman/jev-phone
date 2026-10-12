"""Read-only scrcpy video -> local MJPEG. Independent of click capture RPCs."""
import atexit
import os
import shutil
import socket
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

class AndroidMirror:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.serial = None
        self.frame = None
        self.sequence = 0
        self.condition = threading.Condition()
        self.processes = []
        self.fifo = None
        self.stopped = True
        atexit.register(self.stop)

    def start(self, serial):
        if self.serial == serial and self.processes and all(p.poll() is None for p in self.processes):
            return
        self.stop()
        if not shutil.which('scrcpy') or not shutil.which('ffmpeg'):
            raise RuntimeError('安卓镜像需要安装 scrcpy 和 ffmpeg。')
        executable = Path(shutil.which('scrcpy')).resolve()
        server = executable.parent.parent/'share/scrcpy/scrcpy-server'
        if not server.exists():
            raise RuntimeError('没有找到安装的 scrcpy-server。')
        version = re.search(r'scrcpy ([0-9.]+)', subprocess.check_output(['scrcpy','--version'],text=True)).group(1)
        scid = uuid.uuid4().hex[:7].zfill(8)
        remote = '/data/local/tmp/jev-phone-'+scid+'.jar'
        subprocess.run(['adb','-s',serial,'push',str(server),remote],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.forward = subprocess.check_output(['adb','-s',serial,'forward','tcp:0','localabstract:scrcpy_'+scid],text=True).strip()
        self.remote = remote
        self.serial, self.stopped, self.frame = serial, False, None
        log = open(self.directory/'mirror.log','ab',buffering=0)
        capture = subprocess.Popen(['adb','-s',serial,'shell','CLASSPATH='+remote,'app_process','/','com.genymobile.scrcpy.Server',version,'scid='+scid,'log_level=warn','audio=false','control=false','tunnel_forward=true','raw_stream=true','max_size=1280','max_fps=12','video_bit_rate=2000000'],stdout=log,stderr=log)
        self.processes=[capture]
        connected = None
        for _ in range(60):
            if capture.poll() is not None:break
            try:
                candidate = socket.create_connection(('127.0.0.1',int(self.forward)),timeout=.2)
                candidate.settimeout(3)
                first = candidate.recv(65536)
                if first: connected=candidate;break
                candidate.close()
            except (OSError,socket.timeout):
                try:candidate.close()
                except Exception:pass
            time.sleep(.1)
        if connected is None:
            log.close();self.stop();raise RuntimeError('安卓视频流启动失败，详见本地 mirror.log。')
        self.socket=connected
        connected.settimeout(None)
        decoder = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-flags','low_delay','-probesize','32','-analyzeduration','0','-framerate','12','-threads','1','-f','h264','-i','pipe:0','-vf','fps=12','-f','image2pipe','-vcodec','mjpeg','-pix_fmt','yuvj420p','-threads','1','-q:v','5','pipe:1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log)
        self.processes.append(decoder);log.close()
        def pump():
            try:
                decoder.stdin.write(first);decoder.stdin.flush()
                while not self.stopped:
                    data=connected.recv(65536)
                    if not data:break
                    decoder.stdin.write(data);decoder.stdin.flush()
            except (OSError,ValueError):pass
            finally:
                try:decoder.stdin.close()
                except Exception:pass
        threading.Thread(target=pump,daemon=True).start()
        threading.Thread(target=self._read,args=(decoder,),daemon=True).start()

    def _read(self, decoder):
        pending = bytearray()
        while not self.stopped:
            data = decoder.stdout.read1(65536)
            if not data: break
            pending.extend(data)
            while True:
                start = pending.find(b'\xff\xd8')
                end = pending.find(b'\xff\xd9',max(0,start)+2)
                if start < 0 or end < 0: break
                frame = bytes(pending[start:end+2]);del pending[:end+2]
                with self.condition:
                    self.frame=frame;self.sequence+=1;self.condition.notify_all()
            if len(pending)>8_000_000:pending.clear()
        with self.condition:self.condition.notify_all()

    def stream(self):
        last = -1
        while not self.stopped:
            with self.condition:
                self.condition.wait_for(lambda:self.sequence!=last or self.stopped,timeout=3)
                if self.stopped: return
                if self.frame is None: continue
                frame,last=self.frame,self.sequence
            yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(frame)).encode()+b'\r\n\r\n'+frame+b'\r\n'

    def stop(self):
        self.stopped = True
        if getattr(self,'socket',None):
            self.socket.close();self.socket=None
        with self.condition:self.condition.notify_all()
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill()
        self.processes=[]
        if getattr(self,'forward',None):
            subprocess.run(['adb','-s',self.serial,'forward','--remove','tcp:'+self.forward],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.forward=None
        if getattr(self,'remote',None):
            subprocess.run(['adb','-s',self.serial,'shell','rm',self.remote],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.remote=None
        if self.fifo:
            self.fifo.unlink(missing_ok=True)
            self.fifo=None

