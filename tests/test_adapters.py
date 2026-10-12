import base64,io,json,threading,time,unittest
from PIL import Image
import httpx
from jev_phone import PhoneClicker,ClickFailure
from jev_phone.adapters import Observation,IOSAdapter,HarmonyAdapter
from jev_phone.core import candidates_from_tree

def image(w=200,h=400):
    b=io.BytesIO();Image.new('RGB',(w,h),'white').save(b,format='PNG');return b.getvalue()

SOURCE='<AppiumAUT><XCUIElementTypeApplication type="XCUIElementTypeApplication" x="0" y="0" width="100" height="200" visible="true" enabled="true"><XCUIElementTypeOther type="XCUIElementTypeOther" label="研究" name="研究" x="10" y="20" width="20" height="30" visible="true" enabled="true" accessible="false"/></XCUIElementTypeApplication></AppiumAUT>'

def stage(name,fn):return fn()

class IOSContract(unittest.TestCase):
    def test_visible_other_and_pixel_point_mapping(self):
        calls=[]
        def handler(request):
            path=request.url.path;calls.append((request.method,path,json.loads(request.content) if request.content else None))
            if path.endswith('/appium/settings'):return httpx.Response(200,json={'value':{'waitForIdleTimeout':10,'animationCoolOffTimeout':2}})
            if path=='/session':return httpx.Response(200,json={'sessionId':'owned'})
            if path.endswith('/window/size'):value={'width':100,'height':200}
            elif path.endswith('/orientation'):value='PORTRAIT'
            elif path.endswith('/source'):value=SOURCE
            elif path.endswith('/screenshot'):value=base64.b64encode(image()).decode()
            else:value=None
            return httpx.Response(200,json={'value':value})
        client=httpx.Client(transport=httpx.MockTransport(handler))
        adapter=IOSAdapter('http://wda.test',client=client)
        obs=adapter.observe(stage);nodes=candidates_from_tree(obs.tree,200,400)
        self.assertEqual(nodes[0]['bounds'],[20,40,60,100])
        adapter.click(40,70,obs)
        tap=next(c for c in calls if c[1].endswith('/wda/tap'))
        self.assertEqual(tap[2],{'x':20.0,'y':35.0})
        adapter.close();self.assertTrue(any(c[0]=='DELETE' for c in calls));client.close()

    def test_borrowed_session_is_not_deleted(self):
        calls=[]
        client=httpx.Client(transport=httpx.MockTransport(lambda r:(calls.append(r.method),httpx.Response(200,json={'value':None}))[1]))
        IOSAdapter('http://wda.test',session_id='borrowed',client=client).close()
        self.assertEqual(calls,[]);client.close()

    def test_mismatched_orientation_is_rejected(self):
        with self.assertRaises(RuntimeError):IOSAdapter.convert(SOURCE,image(400,200),(100,200,'PORTRAIT'))

    def test_legacy_route_only_after_404(self):
        calls=[]
        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(404 if request.url.path.endswith('/wda/tap') else 200,json={'value':{'waitForIdleTimeout':10,'animationCoolOffTimeout':2} if request.url.path.endswith('/appium/settings') else None})
        client=httpx.Client(transport=httpx.MockTransport(handler))
        a=IOSAdapter('http://wda.test',session_id='borrowed',client=client)
        a.click(40,70,Observation('',image(),(100,200,'PORTRAIT'),{'sx':2,'sy':2}))
        self.assertEqual([p for p in calls if '/wda/tap' in p],['/session/borrowed/wda/tap','/session/borrowed/wda/tap/0']);client.close()

class HarmonyContract(unittest.TestCase):
    def test_native_image_is_separate_and_clipped(self):
        tree={'attributes':{'type':'Container','bounds':'[0,0][100,100]','clickable':'true','enabled':'true'},'children':[
            {'attributes':{'type':'Image','bounds':'[80,70][140,120]','clickable':'false','enabled':'true'}},
            {'attributes':{'type':'Image','bounds':'[0,0][20,20]','enabled':'true','visible':'false'}}]}
        xml=HarmonyAdapter.convert(tree);nodes=candidates_from_tree(xml,100,100)
        self.assertEqual(len(nodes),2)
        self.assertEqual(nodes[1]['bounds'],[80,70,100,100])

    def test_cached_size_and_rotation_are_invalidated(self):
        class Driver:
            serial='test'
            def __init__(self):self.__dict__.update(display_size=(1,1),display_rotation=0)
            @property
            def display_size(self):return 100,200
            @property
            def display_rotation(self):return 1
        d=Driver();self.assertEqual(HarmonyAdapter(driver=d).viewport(),(100,200))
        self.assertNotIn('display_size',d.__dict__)

class FakeAdapter:
    platform='test'
    def __init__(self,identity):self.identity=identity;self.token=(100,200);self.clicked=[]
    def observe(self,stage):
        return Observation('<hierarchy><node text="target" bounds="[10,20][50,60]" clickable="true" enabled="true"/></hierarchy>',image(100,200),self.token)
    def viewport(self):return self.token
    def screenshot(self):return image(100,200)
    def click(self,x,y,observation):self.clicked.append((x,y))
    def close(self):pass

class SharedCoreContract(unittest.TestCase):
    def test_rotation_after_model_is_not_clicked(self):
        a=FakeAdapter('rotation');c=PhoneClicker(a,'test-key')
        def response(*args):a.token=(200,100);return {'answers':{'node':{'choice':'N1'}}}
        c.decisions.request=response
        with self.assertRaises(ClickFailure):c.click('target')
        self.assertEqual(a.clicked,[]);c.close()

    def test_same_device_is_serialized_across_instances(self):
        adapters=[FakeAdapter('same') for _ in range(2)];clients=[PhoneClicker(a,'test') for a in adapters]
        active=0;peak=0;guard=threading.Lock();errors=[]
        def response(*args):
            nonlocal active,peak
            with guard:active+=1;peak=max(peak,active)
            time.sleep(.03)
            with guard:active-=1
            return {'answers':{'node':{'choice':'N1'}}}
        def run(c):
            try:c.click('target')
            except Exception as e:errors.append(e)
        for c in clients:c.decisions.request=response
        threads=[threading.Thread(target=run,args=(c,)) for c in clients]
        for t in threads:t.start()
        for t in threads:t.join(2)
        self.assertFalse(errors);self.assertEqual(peak,1)
        self.assertEqual([a.clicked for a in adapters],[[(30,40)],[(30,40)]])
        for c in clients:c.close()

    def test_distinct_devices_can_reach_model_concurrently(self):
        barrier=threading.Barrier(2,timeout=2);clients=[PhoneClicker(FakeAdapter('device-'+str(i)),'test') for i in range(2)];errors=[];results=[]
        def response(*args):barrier.wait();return {'answers':{'node':{'choice':'N1'}}}
        def run(c):
            try:results.append(c.click('target'))
            except Exception as e:errors.append(e)
        for c in clients:c.decisions.request=response
        threads=[threading.Thread(target=run,args=(c,)) for c in clients]
        for t in threads:t.start()
        for t in threads:t.join(3)
        self.assertFalse(errors);self.assertEqual({r['device'] for r in results},{'device-0','device-1'})
        for c in clients:c.close()

class V3Channels(unittest.TestCase):
    def test_android_uses_live_info_without_adb_and_quality95(self):
        from jev_phone.adapters import AndroidAdapter
        class RPC:
            def takeScreenshot(self,scale,quality):
                self.called=(scale,quality)
                return base64.b64encode(image(100,200)).decode()
        class Device:
            serial='test'
            info={'displayWidth':100,'displayHeight':200}
            jsonrpc=RPC()
            def window_size(self):raise AssertionError('unexpected ADB size')
        a=AndroidAdapter(device=Device())
        self.assertEqual(a.viewport(),(100,200));a.screenshot()
        self.assertEqual(a.device.jsonrpc.called,(1,95))

    def test_harmony_fragmented_utf8_and_reader_restoration(self):
        import types
        payload=json.dumps({'attributes':{'text':'显示'}},ensure_ascii=False).encode()
        class Socket:
            timeout=10
            chunks=[payload[:29],payload[29:31],payload[31:]]
            def gettimeout(self):return self.timeout
            def settimeout(self,value):self.timeout=value
            def recv(self,size):return self.chunks.pop(0)
        class Client:
            sock=Socket()
            def _recv_msg(self,*args,**kwargs):raise AssertionError('old receiver')
            def invoke_captures(self,name):
                self.name=name
                return types.SimpleNamespace(result=json.loads(self._recv_msg(decode=True)))
        class Driver:
            serial='test'
            _client=Client()
            def _invoke(self,api,args):self.called=(api,args)
        d=Driver();old=d._client._recv_msg
        a=HarmonyAdapter(driver=d)
        self.assertEqual(a.raw_tree()['attributes']['text'],'显示')
        self.assertEqual(d._client.name,'captureLayout')
        self.assertEqual(d._client._recv_msg,old)
        self.assertEqual(d._client.sock.timeout,10)
        a.click(40,70,None);self.assertEqual(d.called,('Driver.click',[40,70]))

    def test_fast_platform_has_no_post_model_device_query(self):
        a=FakeAdapter('fast');a.recheck_before_click=False
        a.viewport=lambda: (_ for _ in ()).throw(AssertionError('extra viewport query'))
        with PhoneClicker(a,'test') as c:
            c.decisions.request=lambda *args:{'answers':{'node':{'choice':'N1'}}}
            c.click('target')
        self.assertEqual(a.clicked,[(30,40)])

class IOSFastContract(unittest.TestCase):
    def test_demand_capture_single_tree_and_reused_frame_without_viewport_queries(self):
        calls=[]
        def handler(r):
            calls.append(r.url.path)
            value=SOURCE if r.url.path.endswith('/source') else base64.b64encode(image()).decode()
            return httpx.Response(200,json={'value':value})
        client=httpx.Client(transport=httpx.MockTransport(handler))
        a=IOSAdapter('http://wda.test',session_id='borrowed',client=client)
        o=a.observe(stage)
        self.assertEqual(Image.open(io.BytesIO(o.image)).format,'JPEG')
        self.assertEqual(calls,['/session/borrowed/screenshot','/session/borrowed/source'])
        calls.clear();a.observe_with_frame(stage,o.image)
        self.assertEqual(calls,['/session/borrowed/source'])
        a.close();client.close()

    def test_tap_temporarily_shortens_waits_and_restores_even_if_tap_fails(self):
        calls=[]
        def handler(r):
            body=json.loads(r.content) if r.content else None
            calls.append((r.method,r.url.path,body))
            if '/wda/tap' in r.url.path:return httpx.Response(500,json={'value':None})
            return httpx.Response(200,json={'value':{'waitForIdleTimeout':10,'animationCoolOffTimeout':2}})
        client=httpx.Client(transport=httpx.MockTransport(handler))
        a=IOSAdapter('http://wda.test',session_id='borrowed',client=client)
        with self.assertRaises(httpx.HTTPStatusError):
            a.click(40,70,Observation('',image(),(100,200),{'sx':2,'sy':2}))
        self.assertEqual(calls[1][2],{'settings':{'waitForIdleTimeout':0,'animationCoolOffTimeout':0}})
        self.assertEqual(calls[-1][2],{'settings':{'waitForIdleTimeout':10,'animationCoolOffTimeout':2}})
        self.assertEqual(len([c for c in calls if '/wda/tap' in c[1]]),1)
        a.close();client.close()

class IOSCandidateRegions(unittest.TestCase):
    def test_static_text_tab_is_kept_and_identical_regions_are_deduplicated(self):
        source='''<AppiumAUT><XCUIElementTypeApplication type="XCUIElementTypeApplication" x="0" y="0" width="100" height="200" visible="true" enabled="true">
        <node type="XCUIElementTypeStaticText" label="学习" x="10" y="150" width="30" height="30" visible="true" enabled="true"/>
        <node type="XCUIElementTypeButton" label="学习" x="10" y="150" width="30" height="30" visible="true" enabled="true"/>
        <node type="XCUIElementTypeStaticText" label="学习" x="50" y="150" width="30" height="30" visible="true" enabled="true"/>
        <node type="XCUIElementTypeStaticText" label=" " x="10" y="20" width="30" height="30" visible="true" enabled="true"/>
        <node type="XCUIElementTypeStaticText" label="隐藏" x="10" y="60" width="30" height="30" visible="false" enabled="true"/>
        <node type="XCUIElementTypeStaticText" label="禁用" x="10" y="100" width="30" height="30" visible="true" enabled="false"/>
        </XCUIElementTypeApplication></AppiumAUT>'''
        tree,_=IOSAdapter.convert(source,image(),(100,200))
        nodes=candidates_from_tree(tree,200,400)
        self.assertEqual([n['text'] for n in nodes],['学习','学习'])
        self.assertEqual([n['bounds'] for n in nodes],[[20,300,80,360],[100,300,160,360]])
