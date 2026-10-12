import time
import unittest
from fastapi.testclient import TestClient
from jev_phone import demo
from jev_phone.core import ClickFailure

class StopOnFailure(unittest.TestCase):
    def test_failed_step_never_runs_next_step(self):
        class FailingClicker:
            calls = []
            def run(self, text, on_event=None):
                target=demo.split_steps(text)[0]
                on_event({'phase':'start','message':target,'step':1})
                self.calls.append(target)
                raise ClickFailure("UNCERTAIN")
        fake = FailingClicker()
        original = demo.clicker
        demo.clicker = fake
        try:
            client = TestClient(demo.app)
            response = client.post('/api/run', json={'text': '点击星球；点击我的'})
            self.assertEqual(response.status_code, 200)
            job_id = response.json()['id']
            for _ in range(100):
                job = client.get('/api/jobs/'+job_id).json()
                if job['status'] != 'running': break
                time.sleep(.01)
            self.assertEqual(job['status'], 'failed')
            self.assertEqual(fake.calls, ['点击星球'])
            self.assertEqual(job['results'], [])
            self.assertFalse(demo.busy)
        finally:
            demo.clicker = original

if __name__ == '__main__': unittest.main()

class KeyLifetime(unittest.TestCase):
    def test_empty_key_cannot_reuse_existing_key(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        original = demo.clicker
        demo.clicker = SimpleNamespace(_key='test-old-key', provider='openrouter')
        try:
            with patch.object(demo.adb,'device_list',return_value=[SimpleNamespace(serial='test-device')]):
                response=TestClient(demo.app).post('/api/connect',json={'serial':'test-device','provider':'openrouter','api_key':''})
            self.assertEqual(response.status_code,400)
            self.assertNotIn('test-old-key',response.text)
        finally:demo.clicker=original

    def test_reset_clears_client_credentials(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        original=demo.clicker
        old=SimpleNamespace(_key='test-key',decisions=SimpleNamespace(_key='test-key'),close=Mock())
        demo.clicker=old
        try:
            with patch.object(demo.mirror,'stop'):
                response=TestClient(demo.app).post('/api/reset-connection',json={})
            self.assertEqual(response.status_code,200)
            self.assertIsNone(demo.clicker)
            self.assertEqual(old._key,'')
            self.assertEqual(old.decisions._key,'')
            old.close.assert_called_once()
        finally:demo.clicker=original

class SharedSequence(unittest.TestCase):
    def test_demo_uses_sdk_sequence_without_result_screenshot(self):
        from jev_phone import PhoneClicker
        from test_run import SequenceAdapter
        adapter=SequenceAdapter()
        phone=PhoneClicker(adapter,'test')
        phone.decisions.request=lambda *args:{'answers':{'node':{'choice':'N1'}}}
        original=demo.clicker;demo.clicker=phone
        try:
            client=TestClient(demo.app)
            job_id=client.post('/api/run',json={'text':'A;B'}).json()['id']
            for _ in range(100):
                job=client.get('/api/jobs/'+job_id).json()
                if job['status']!='running':break
                time.sleep(.01)
            self.assertEqual(job['status'],'completed')
            self.assertEqual(len(job['results']),2)
            self.assertEqual(adapter.frames,2)
            self.assertEqual(len(adapter.reused),1)
            self.assertFalse(any(e['phase']=='result_image' for e in job['events']))
            self.assertEqual([e['step'] for e in job['events'] if e['phase']=='completed'],[1,2])
            self.assertEqual(len(job['transitions']),1)
        finally:
            demo.clicker=original;phone.close()
