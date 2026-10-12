import unittest
import httpx
from jev_phone.decisions import DecisionClient

class ProtocolContract(unittest.TestCase):
    def test_native_image_and_named_choice(self):
        client=DecisionClient('test-only','openai')
        state=['本步目标',{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,AAAA','detail':'high'}}]
        request=client.payload(state,{'N1':'目标','UNCERTAIN':'不确定'},'选择目标')
        self.assertEqual(request['model'],'gpt-6-luna')
        self.assertEqual(request['input'][0]['content'][1]['type'],'input_image')
        self.assertEqual(request['questions'][0]['choices'][0],{'value':'N1','description':'目标'})
        client.client.close()
        client.client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'answers':[{'name':'node','type':'choice','choice':'N1'}]})))
        self.assertEqual(client.request(state,{'N1':'目标','N2':'其他'},'选择目标')['answers']['node']['choice'],'N1')
        client.close()

    def test_router_shape_and_safe_auth_error(self):
        client=DecisionClient('sensitive-test-value','openrouter')
        payload=client.payload(['本步目标'],{'N1':'目标','N2':'其他'},'选择')
        self.assertIn('state',payload)
        self.assertIn('criteria',payload['questions']['node'])
        client.client.close()
        client.client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(401)))
        with self.assertRaises(RuntimeError) as caught:client.request(['目标'],{'N1':'一','N2':'二'},'选择')
        self.assertNotIn('sensitive-test-value',str(caught.exception))
        client.close()

if __name__=='__main__':unittest.main()
