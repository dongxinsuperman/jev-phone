"""Protocol adapters: OpenRouter Decisions and native OpenAI Decisions."""
import httpx

class DecisionClient:
    def __init__(self, api_key, provider='openrouter'):
        if provider not in ('openrouter','openai'):
            raise ValueError('不支持的模型通道。')
        self.provider=provider
        self._key=api_key
        self.model='openai/gpt-6-luna-decisions' if provider=='openrouter' else 'gpt-6-luna'
        self.url='https://openrouter.ai/api/alpha/decisions' if provider=='openrouter' else 'https://api.openai.com/v1/decisions'
        self.client=httpx.Client(timeout=35,limits=httpx.Limits(keepalive_expiry=180))

    def payload(self, state, criteria, instructions):
        if self.provider=='openrouter':
            return {'model':self.model,'state':state,'questions':{'node':{'type':'choice','instructions':instructions,'criteria':criteria}}}
        parts=[]
        for item in state:
            if isinstance(item,str):parts.append({'type':'input_text','text':item})
            else:parts.append({'type':'input_image','image_url':item['image_url']['url'],'detail':item['image_url'].get('detail','high')})
        return {'model':self.model,'input':[{'role':'user','content':parts}],
                'questions':[{'type':'choice','name':'node','instructions':instructions,'choices':[{'value':k,'description':v} for k,v in criteria.items()]}]}

    def request(self, state, criteria, instructions):
        response=self.client.post(self.url,json=self.payload(state,criteria,instructions),headers={'Authorization':'Bearer '+self._key})
        if response.is_error:
            raise RuntimeError(f'{self.provider} 请求失败（HTTP {response.status_code}），请检查密钥、额度和模型访问权限。')
        data=response.json()
        if self.provider=='openai':
            answer=next((a for a in data.get('answers',[]) if a.get('name')=='node'),{})
            data={**data,'answers':{'node':answer}}
        return data

    def prepare(self):
        data=self.request(['连接检查：请选择 READY。'],{'READY':'通道已经准备好','NOT_READY':'通道未准备好'},'选择 READY。')
        if data.get('answers',{}).get('node',{}).get('choice')!='READY':
            raise RuntimeError('模型未返回有效准备结果。')

    def close(self):self.client.close()
