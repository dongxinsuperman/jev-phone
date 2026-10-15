import copy,unittest
from unittest.mock import patch
from jev_phone.android_visual import native_regions,dom_regions
from jev_phone.adapters.android import AndroidAdapter
from jev_phone.adapters.base import Observation

class AndroidVisualTests(unittest.TestCase):
    def test_native_generic_nested_subject_and_no_mutation(self):
        raw='''  android.widget.FrameLayout{abc V.E...... ........ 0,0-300,300}
    android.widget.FrameLayout{def V.E...... ........ 0,0-200,100}
      android.view.View{aaa VFED..C.. ........ 0,30-200,100}
      android.widget.FrameLayout{bbb V.E...... ........ 0,0-200,100}
        android.widget.ImageView{ccc V.ED..... ........ 50,0-150,100}
'''
        tree='<hierarchy><node class="android.view.View" clickable="true" enabled="true" bounds="[0,30][200,100]"/></hierarchy>'
        nodes=[{'id':'N1','bounds':[0,30,200,100]}];before=copy.deepcopy(nodes)
        self.assertEqual(native_regions(raw,tree,nodes)['N1']['bounds'],[50,0,150,100]);self.assertEqual(nodes,before)
        self.assertFalse(native_regions(raw.replace('bbb V.','bbb G.'),tree,nodes))
    def test_dom_geometry_and_ambiguity(self):
        n=[{'id':'N1','bounds':[0,0,100,100]}]
        e={'rect':[0,0,100,100],'img':True,'bg':'transparent','shadow':'none','border':'0px','radius':'20px','tag':'IMG'}
        self.assertEqual(dom_regions({'items':[e],'dpr':1},n)['N1']['radius'],20)
        other={**e,'rect':[3,0,97,100]}
        self.assertFalse(dom_regions({'items':[e,other],'dpr':1},n))
    def test_default_switches_are_off(self):
        a=AndroidAdapter("fake",object())
        self.assertFalse(a.visual_dom)
        self.assertFalse(a.visual_native)

    def test_disabled_switch_never_collects(self):
        a=AndroidAdapter('fake',object())
        with patch('jev_phone.android_visual.enhance',side_effect=AssertionError):
            self.assertEqual(a.enhance_annotation(Observation('',b'',(100,100)),[]),{})
