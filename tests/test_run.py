import unittest
from unittest.mock import patch
from jev_phone import PhoneClicker, RunFailure
from jev_phone.stability import FastStabilityPolicy, wait_fast_stable, pixel_change_ratio, thumbnail
from test_adapters import FakeAdapter, image

class SequenceAdapter(FakeAdapter):
    platform='harmony'
    recheck_before_click=False
    def __init__(self):
        super().__init__('sequence');self.frames=0;self.reused=[]
    def screenshot(self):
        self.frames+=1
        return image(100,200)
    def observe_with_frame(self,stage,frame):
        self.reused.append(frame)
        observation=self.observe(stage)
        observation.image=frame
        return observation

class SequenceContract(unittest.TestCase):
    def test_split_order_fresh_targets_and_last_frame_reuse(self):
        adapter=SequenceAdapter();requests=[];events=[]
        with PhoneClicker(adapter,'test') as phone:
            def decision(state,*args):
                requests.append(state[0]);return {'answers':{'node':{'choice':'N1'}}}
            phone.decisions.request=decision
            report=phone.run('点击A；点击B,点击C',on_event=events.append)
        self.assertEqual(requests,['当前点击目标：点击A','当前点击目标：点击B','当前点击目标：点击C'])
        self.assertEqual(report['status'],'completed')
        self.assertEqual(len(report['results']),3)
        self.assertEqual(adapter.frames,4)
        self.assertEqual(len(adapter.reused),2)
        self.assertEqual([t['checks'] for t in report['transitions']],[2,2])
        self.assertEqual([e['step'] for e in events if e['phase']=='start'],[1,2,3])

    def test_model_failure_stops_and_retains_completed_steps(self):
        adapter=SequenceAdapter();answers=iter(['N1','NOT_FOUND'])
        with PhoneClicker(adapter,'test') as phone:
            phone.decisions.request=lambda *args:{'answers':{'node':{'choice':next(answers)}}}
            with self.assertRaises(RunFailure) as caught:phone.run('A;B;C')
        self.assertEqual(caught.exception.report['failed_step'],2)
        self.assertEqual(len(caught.exception.report['results']),1)
        self.assertEqual(len(adapter.clicked),1)
        self.assertEqual(adapter.frames,2)

    def test_transition_timeout_does_not_click_next_step(self):
        adapter=SequenceAdapter()
        with PhoneClicker(adapter,'test') as phone:
            phone.decisions.request=lambda *args:{'answers':{'node':{'choice':'N1'}}}
            with patch('jev_phone.stability.policy_for_platform',return_value=FastStabilityPolicy(timeout_s=0)):
                with self.assertRaises(RunFailure) as caught:phone.run('A;B')
        self.assertEqual(len(adapter.clicked),1)
        self.assertEqual(caught.exception.report['failed_step'],2)

    def test_one_step_has_no_transition_capture(self):
        adapter=SequenceAdapter()
        with PhoneClicker(adapter,'test') as phone:
            phone.decisions.request=lambda *args:{'answers':{'node':{'choice':'N1'}}}
            self.assertEqual(phone.run('A')['transitions'],[])
        self.assertEqual(adapter.frames,0)

    def test_comparison_ignores_old_frame_and_uses_fresh_consecutive_images(self):
        data=image(100,200);calls=[]
        def screenshot():calls.append(1);return data
        result=wait_fast_stable(screenshot,frame_a_bytes=b'not-an-image',policy=FastStabilityPolicy(interval_s=0))
        self.assertTrue(result.stable);self.assertEqual(len(calls),2)
        self.assertEqual(result.bytes_,data)

class PlatformPolicyContract(unittest.TestCase):
    def test_ios_run_uses_confirmed_policy(self):
        adapter=SequenceAdapter();adapter.platform='ios'
        with PhoneClicker(adapter,'test') as phone:
            phone.decisions.request=lambda *args:{'answers':{'node':{'choice':'N1'}}}
            with patch('jev_phone.stability.policy_for_platform',return_value=FastStabilityPolicy(interval_s=0)):
                report=phone.run('A;B')
        self.assertEqual(len(report['results']),2)
        self.assertEqual(len(report['transitions']),1)
        self.assertEqual(adapter.frames,2)

    def test_only_tuned_platforms_have_policies(self):
        from jev_phone.stability import policy_for_platform
        self.assertEqual(policy_for_platform('android').interval_s,.1)
        self.assertEqual(policy_for_platform('harmony').interval_s,0)
        self.assertEqual(policy_for_platform('ios').interval_s,.2)
