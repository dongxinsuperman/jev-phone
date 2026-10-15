import copy
import unittest
from unittest.mock import Mock,patch
from jev_phone import configure
from jev_phone.settings import visual_enhancement_enabled
from jev_phone.adapters import AndroidAdapter,IOSAdapter,HarmonyAdapter,Observation
from jev_phone.visual_channels import select_ios_context,safe_regions

class VisualSwitchTests(unittest.TestCase):
    def setUp(self):configure(visual_enhancement=False)
    def tearDown(self):configure(visual_enhancement=False)
    def adapters(self):
        return [AndroidAdapter('fake',object()),IOSAdapter('http://localhost:8100','existing',client=Mock()),HarmonyAdapter('fake',driver=Mock())]
    def test_one_switch_controls_existing_adapters(self):
        adapters=self.adapters()
        self.assertFalse(adapters[0].visual_dom)
        configure(visual_enhancement=True)
        self.assertTrue(adapters[0].visual_dom)
        self.assertTrue(adapters[0].visual_native)
        obs=Observation('<hierarchy/>',b'',(100,100),{'_visual_raw':{}})
        with patch('jev_phone.android_visual.enhance',return_value=({},{})) as android,patch('jev_phone.visual_channels.enhance_ios',return_value=({},{})) as ios,patch('jev_phone.visual_channels.enhance_harmony',return_value=({},{})) as harmony:
            for adapter in adapters:adapter.enhance_annotation(copy.deepcopy(obs),[])
            for provider in [android,ios,harmony]:provider.assert_called_once()
    def test_off_performs_no_provider_io_on_any_platform(self):
        with patch('jev_phone.android_visual.enhance',side_effect=AssertionError),patch('jev_phone.visual_channels.enhance_ios',side_effect=AssertionError),patch('jev_phone.visual_channels.enhance_harmony',side_effect=AssertionError):
            for adapter in self.adapters():
                self.assertEqual(adapter.enhance_annotation(Observation('',b'',(1,1)),[]),{})
    def test_switch_rejects_non_bool_without_changing_state(self):
        configure(visual_enhancement=True)
        with self.assertRaises(TypeError):configure(visual_enhancement='false')
        self.assertTrue(visual_enhancement_enabled())
    def test_ios_ambiguous_context_does_not_guess(self):
        tree='<hierarchy><node class="XCUIElementTypeWebView" visible-to-user="true" bounds="[0,0][300,600]"/></hierarchy>'
        ctx={'visible':'visible','focus':False,'items':[{}],'viewport':{'width':100,'height':200},'dpr':3}
        self.assertIs(select_ios_context([ctx],tree,(300,600)),ctx)
        self.assertIsNone(select_ios_context([ctx,copy.deepcopy(ctx)],tree,(300,600)))
        self.assertIsNone(select_ios_context([ctx],tree.replace('true','false'),(300,600)))
    def test_safe_geometry_keeps_click_bounds_immutable(self):
        nodes=[{'id':'N1','bounds':[0,0,100,100]}];original=copy.deepcopy(nodes)
        self.assertFalse(safe_regions({'N1':{'bounds':[60,0,100,100],'radius':0}},nodes,(100,100)))
        self.assertEqual(nodes,original)
