"""Native enhancement must preserve action identity and avoid extra capture on success."""
import copy
import io
import unittest
from unittest.mock import Mock, patch
import httpx
from PIL import Image
from jev_phone import configure, PhoneClicker
from jev_phone.adapters import IOSAdapter, HarmonyAdapter, Observation
from jev_phone.core import candidates_from_tree, annotate
from jev_phone.native_visual import ios_source, ios_regions, clip, bind_harmony, harmonic_regions, ancestor_fill_regions, render_index, paint_supported, reliable_bindings
from jev_phone.visual_channels import enhance_ios


def frame():
    output=io.BytesIO();Image.new('RGB',(200,100),'white').save(output,'JPEG');return output.getvalue()


def snapshot(web=False):
    child={'uid':'button','type':'XCUIElementTypeButton','frame':'{{0,0},{100,50}}',
           'visibleFrame':'{{0,0},{80,50}}','label':'button','enabled':True,'visible':True}
    if web:child={'uid':'web','type':'XCUIElementTypeWebView','frame':'{{0,0},{100,50}}',
                  'visible':True,'enabled':True,'children':[child]}
    return {'version':1,'tree':{'uid':'app','type':'XCUIElementTypeApplication',
            'frame':'{{0,0},{100,50}}','enabled':True,'visible':True,'children':[child]}}


class NativeVisualTests(unittest.TestCase):
    def tearDown(self):configure(visual_enhancement=False)

    def observation(self,raw):
        tree,meta=IOSAdapter.convert(ios_source(raw),frame(),(100,50))
        meta['_native_snapshot']=raw
        return Observation(tree,frame(),(100,50),meta),candidates_from_tree(tree,200,100)

    def test_ios_identity_clip_preserves_candidate_payload(self):
        obs,nodes=self.observation(snapshot());before=copy.deepcopy(nodes)
        regions,status=ios_regions(obs,nodes)
        self.assertEqual(regions,{'N1':{'bounds':[0,0,160,100],'radius':0}})
        self.assertEqual(nodes,before);self.assertEqual(status['count'],1)
        self.assertNotIn('_native_snapshot',obs.metadata)

    def test_ios_duplicate_bounds_use_distinct_snapshot_uids(self):
        raw=snapshot();other=copy.deepcopy(raw['tree']['children'][0]);other.update(uid='second',label='other')
        raw['tree']['children'].append(other);obs,nodes=self.observation(raw)
        self.assertEqual(set(ios_regions(obs,nodes)[0]),{'N1','N2'})

    def test_click_uses_original_center_after_native_visible_clip(self):
        configure(visual_enhancement=True);obs,nodes=self.observation(snapshot())
        a=IOSAdapter('http://localhost:8100','existing',client=Mock())
        a.observe=Mock(return_value=obs)
        def request(method,path,body=None):
            return {'value':{'waitForIdleTimeout':10,'animationCoolOffTimeout':2} if method=='GET' else None}
        a._request=Mock(side_effect=request)
        c=PhoneClicker(a,'test-key')
        c.decisions.request=Mock(return_value={'answers':{'node':{'choice':'N1'}}})
        try:
            result=c.click('button')
            self.assertEqual(result['point'],[100,50])
            tap=next(call for call in a._request.call_args_list if call.args[1].endswith('/wda/tap'))
            self.assertEqual(tap.args[2],{'x':50.0,'y':25.0})
            self.assertEqual(result['visual_enhancement']['native']['count'],1)
        finally:c.close()

    def test_ios_web_descendants_never_get_native_geometry(self):
        obs,nodes=self.observation(snapshot(web=True));self.assertEqual(ios_regions(obs,nodes)[0],{})

    def test_fractional_rounding_and_center_exclusion_are_rejected(self):
        self.assertIsNone(clip([0,0,102,102],'{{0.1,0.1},{33.8,33.8}}','{{0.1,0.1},{33.8,33.8}}',3,3))
        self.assertIsNone(clip([0,0,200,100],'{{0,0},{100,50}}','{{80,0},{20,50}}',2,2))

    def test_incomplete_and_duplicate_identity_snapshots_rejected(self):
        raw=snapshot();raw['tree']['truncated']=True
        with self.assertRaises(ValueError):ios_source(raw)
        raw=snapshot();raw['tree']['frame']='{{0,0},{0,0}}'
        with self.assertRaises(ValueError):ios_source(raw)
        raw=snapshot();raw['tree']['children'][0]['uid']='app'
        with self.assertRaises(ValueError):ios_source(raw)

    def test_ios_supported_observe_uses_one_tree_and_one_frame(self):
        configure(visual_enhancement=True);a=IOSAdapter('http://localhost:8100','existing',client=Mock())
        with patch.object(a,'screenshot',return_value=frame()) as screenshot,patch.object(a,'_request',return_value={'value':snapshot()}) as request:
            obs=a.observe(lambda name,f:f())
        screenshot.assert_called_once();request.assert_called_once_with('GET','/session/existing/wda/nativeGeometryProbe')
        self.assertIn('_native_snapshot',obs.metadata)

    def test_ios_unsupported_wda_falls_back_and_is_not_reprobed(self):
        configure(visual_enhancement=True);a=IOSAdapter('http://localhost:8100','existing',client=Mock())
        response=httpx.Response(404,request=httpx.Request('GET','http://localhost/missing'))
        error=httpx.HTTPStatusError('missing',request=response.request,response=response)
        with patch.object(a,'_request',side_effect=[error,{'value':'base'},{'value':'base'}]) as request:
            self.assertEqual(a.source(),'base');self.assertEqual(a.source(),'base')
        self.assertEqual(request.call_count,3)

    def test_off_does_not_call_native_capture_on_either_platform(self):
        a=IOSAdapter('http://localhost:8100','existing',client=Mock())
        with patch.object(a,'_request',return_value={'value':'base'}) as request:
            self.assertEqual(a.source(),'base')
            request.assert_called_once_with('GET','/session/existing/source?format=xml')
        h=HarmonyAdapter('fake',driver=Mock());raw={'attributes':{},'children':[]}
        with patch.object(h,'raw_tree',return_value=raw) as base,patch('jev_phone.native_visual.harmony_capture',side_effect=AssertionError):
            h.source();base.assert_called_once()

    def test_harmony_success_replaces_base_tree_and_failure_is_cached(self):
        configure(visual_enhancement=True);h=HarmonyAdapter('fake',driver=Mock());raw={'attributes':{},'children':[]}
        with patch.object(h,'raw_tree',side_effect=AssertionError),patch('jev_phone.native_visual.harmony_capture',return_value=(raw,{'status':'available'})) as capture:
            h.source();capture.assert_called_once()
        h=HarmonyAdapter('fake',driver=Mock())
        with patch.object(h,'raw_tree',return_value=raw) as base,patch('jev_phone.native_visual.harmony_capture',side_effect=OSError) as capture:
            h.source();h.source();capture.assert_called_once();self.assertEqual(base.call_count,2)

    def test_malformed_harmony_enriched_tree_keeps_original_capture(self):
        configure(visual_enhancement=True);h=HarmonyAdapter('fake',driver=Mock())
        base={'attributes':{},'children':[]}
        with patch.object(h,'raw_tree',return_value=base) as original,patch(
                'jev_phone.native_visual.harmony_capture',return_value=({'attributes':None},{})):
            self.assertEqual(h.source(),HarmonyAdapter.convert(base))
            original.assert_called_once()

    def test_dom_unavailable_does_not_discard_ios_native(self):
        obs,nodes=self.observation(snapshot())
        with patch('jev_phone.visual_channels._enhance_ios_dom',return_value=({}, {'dom':{'status':'unavailable'}})):
            regions,status=enhance_ios(Mock(),obs,nodes)
        self.assertTrue(regions);self.assertEqual(status['native']['count'],1)

    def test_harmony_exact_parent_fill_produces_partial_rounding(self):
        child={'attributes':{'type':'Button','uniqueId':'1','enabled':'true','clickable':'true','bounds':'[0,0][100,40]'}}
        raw={'attributes':{'type':'Column','uniqueId':'2','bounds':'[0,0][100,80]'},'children':[child]}
        tree,nodes,bindings=bind_harmony(raw,(200,100));original=copy.deepcopy(nodes)
        rs={'2':[{'render_id':'7','line':'BackgroundColor[RGBA-0xffffffff] CornerRadius[x:10 y:10 z:10 w:10]'}]}
        regions,_=ancestor_fill_regions(raw,bindings,nodes,rs,(200,100))
        self.assertEqual(regions['N1']['corners'],[10,10,0,0]);self.assertEqual(nodes,original)
        self.assertTrue(annotate(frame(),nodes,regions))

    def test_harmony_same_frame_id_in_other_app_window_is_excluded(self):
        def window(bundle):
            return {'attributes':{'type':'WindowScene','bundleName':bundle},'children':[
                {'attributes':{'type':'Button','uniqueId':'9','enabled':'true',
                 'clickable':'true','bounds':'[0,0][100,50]'}}]}
        raw={'attributes':{},'children':[window('system.keyboard'),window('example.app')]}
        _,nodes,binding=bind_harmony(raw,(200,100),bundle='example.app')
        self.assertEqual(len(nodes),2)
        self.assertEqual(set(binding),{'N2'})

    def test_empty_root_opacity_is_unspecified_not_transparent(self):
        child={'attributes':{'uniqueId':'1','opacity':'1.000000'}}
        root={'attributes':{'opacity':''},'children':[child]}
        self.assertEqual(set(reliable_bindings(root,{'N1':child},{})),{'N1'})
        root['attributes']['opacity']='0.000000'
        self.assertEqual(reliable_bindings(root,{'N1':child},{}),{})

    def test_animated_transformed_or_transparent_paint_is_not_used(self):
        for line in ['animations[42]','Scale[x:0.5 y:1.0]','Alpha[0.0]','Rotation[30]','Matrix[identity]']:
            self.assertFalse(paint_supported(line),line)
        self.assertTrue(paint_supported('animations[] Scale[x:1.0 y:1.0] Alpha[1.0]'))
        child={'attributes':{'uniqueId':'1'}}
        parent={'attributes':{'uniqueId':'2'},'children':[child]}
        rs={'2':[{'line':'Scale[x:2 y:2]'}]}
        self.assertEqual(reliable_bindings(parent,{'N1':child},rs),{})
        duplicate={'1':[{'line':'animations[]'},{'line':'animations[]'}]}
        self.assertEqual(reliable_bindings(parent,{'N1':child},duplicate),{})

    def test_duplicate_render_identity_and_other_process_do_not_bind(self):
        text='| pid[2]\nCanvasNode[3] frameNodeId[9]\n| pid[4]\nCanvasNode[5] frameNodeId[9]'
        self.assertEqual(render_index(text,'7'),{})
        self.assertEqual(render_index(text,'2')['9'][0]['render_id'],'3')
        raw={'attributes':{'type':'Button','uniqueId':'9','backgroundColor':'#FFFFFFFF','enabled':'true','clickable':'true','bounds':'[0,0][100,50]'}}
        _,nodes,binding=bind_harmony(raw,(200,100))
        self.assertEqual(harmonic_regions(binding,nodes,{'9':[{},{}]},(200,100))[0],{})


if __name__=='__main__':unittest.main()
