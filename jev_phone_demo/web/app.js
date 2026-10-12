const $ = id => document.getElementById(id);
// USB hot-plug updates only the device list, never the model session or mirror.
async function refreshDevices(){
 try {
  const s=await api('/api/status'), select=$('device');
  const serials=s.devices.map(d=>d.serial);
  const existing=Array.from(select.options).map(o=>o.value).filter(Boolean);
  if(JSON.stringify(serials)===JSON.stringify(existing))return;
  const previous=select.value;
  select.replaceChildren();
  for(const serial of serials){const option=document.createElement('option');option.value=serial;option.textContent=serial;select.append(option);}
  if(!serials.length){const option=document.createElement('option');option.value='';option.textContent='未发现在线手机';select.append(option);}
  if(serials.includes(previous))select.value=previous;
 }catch(_){} // Keep the last list on temporary service failures.
}
setInterval(()=>{if(!document.hidden)refreshDevices();},2000);
window.addEventListener('focus',refreshDevices);
let prepared = false;
let STEP_SEPARATORS = "";
let displayGeneration = 0;
let running = false, seen = 0, polling = null, currentSteps = [];
const phaseNames = {transition:'步骤衔接', transition_completed:'对比返回', start:'目标', observe:'观察', candidates:'编号图', selected:'选择', completed:'点击返回', result_image:'结果截图', error:'停止'};
function showError(message) { $('banner').textContent = message; $('banner').hidden = false; }
async function api(path, body) {
 const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data = await response.json(); if(!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求失败，请检查本地服务。'); return data;
}
function steps() { if(!STEP_SEPARATORS)return [];return Array.from($('command').value).map(c=>STEP_SEPARATORS.includes(c)?String.fromCharCode(10):c).join('').split(String.fromCharCode(10)).map(s=>s.trim()).filter(Boolean); }
function renderSteps(list, job) {
 $('stepPreview').replaceChildren(); list.forEach((text, i)=>{const chip=document.createElement('span');chip.className='step-chip';const n=document.createElement('i');n.textContent=String(i+1).padStart(2,'0');chip.append(n,document.createTextNode(text));
 if(job){if(i<job.results.length)chip.classList.add('done');else if(i===job.current_step-1)chip.classList.add(job.status==='failed'?'failed':'active');} $('stepPreview').append(chip);});
 $('stepCount').textContent = list.length;
}
function phone(url, label) { if($('phoneImage').dataset.live==='true')return; $('phoneEmpty').hidden=true;$('phoneImage').hidden=false;$('phoneImage').src=url;$('frameLabel').textContent=label; }
function fitMirror() {}
function live(url){$('phoneImage').onload=fitMirror;$('phoneEmpty').hidden=true;$('phoneImage').hidden=false;$('phoneImage').dataset.live='true';$('phoneImage').src=url+'?t='+Date.now();$('frameLabel').textContent='LIVE';}
function seconds(value) { return ms(value); }
function ms(value){return typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('en-US',{maximumFractionDigits:2})+' ms':'—';}
let evidence={}, activeEvidence=null, stepStarts={};
function showEvidence(step){activeEvidence=step;const e=evidence[step];$('evidenceStep').textContent='第 '+step+' 步';$('currentTarget').textContent=e?.target||'—';$('annotationEmpty').hidden=!!e?.image;$('annotationLink').hidden=!e?.image;if(e?.image){$('annotationLink').href=e.image;$('annotationImage').src=e.image;}$('selection').textContent=e?.selected||'等待选择';$('point').textContent=e?.point?e.selected+' → ('+e.point.join(', ')+')':'—';if(e?.result)result(e.result);else{$('total').textContent='—';$('modelTime').textContent='—';$('localTime').textContent='—';$('timingDetails').hidden=true;}renderEvidenceThumbs();}
function renderEvidenceThumbs(){ $('evidenceThumbs').replaceChildren();Object.keys(evidence).forEach(step=>{const e=evidence[step];if(!e.image)return;const button=document.createElement('button');button.className='evidence-thumb'+(String(activeEvidence)===step?' active':'');const img=document.createElement('img');img.src=e.image;img.alt='第 '+step+' 步编号图';const label=document.createElement('span');label.textContent='第 '+step+' 步'+(e.selected?' · '+e.selected:'');button.title=e.target||'';button.append(img,label);button.onclick=()=>showEvidence(step);$('evidenceThumbs').append(button);});}
function result(r){$('total').textContent=ms(r.total_ms);$('modelTime').textContent=ms(r.timings.model);$('localTime').textContent=ms(r.non_model_ms);const labels={capture:'尺寸读取',capture_check:'采集检查',tree:'取树',screenshot:'截图',adapt:'平台适配',prepare:'准备',viewport_check:'视口复核',click:'点击'};const parts=Object.entries(labels).filter(([key])=>Number.isFinite(r.timings[key])).map(([key,label])=>label+' '+ms(r.timings[key]));$('timingDetails').hidden=!parts.length;$('timingDetails').textContent='组件分段：'+parts.join(' · ')+'。';}
function timingRow(step,r){const row=document.createElement('div');row.className='step-timing';const heading=document.createElement('strong');heading.textContent='第 '+step+' 步 · 总计 '+ms(r.total_ms);const model=document.createElement('span');model.className='model-duration';model.textContent='模型请求往返  '+ms(r.timings.model);const component=document.createElement('span');component.className='component-duration';component.textContent='组件自身处理  '+ms(r.non_model_ms);const bar=document.createElement('div');bar.className='duration-bar';const part=document.createElement('i');part.style.width=Math.min(100,r.timings.model/r.total_ms*100)+'%';bar.append(part);row.append(heading,model,component,bar);return row;}

function event(e) {
 if(e.phase==='start'){stepStarts[e.step]=e.elapsed_ms;evidence[e.step]={target:e.message};showEvidence(e.step);}
 if(e.image){evidence[e.step]={...evidence[e.step],image:e.image};showEvidence(e.step);}
 if(e.before)phone(e.before,'执行前截图');if(e.after)phone(e.after,'执行后截图');
 if(e.selected){evidence[e.step]={...evidence[e.step],selected:e.selected,point:e.point};if(activeEvidence===e.step)showEvidence(e.step);}
 if(e.result){evidence[e.step]={...evidence[e.step],result:e.result};if(activeEvidence===e.step)showEvidence(e.step);}
 if(e.phase==='error')showError(e.message);
 const row=document.createElement('div');row.className='log-row'+(e.phase==='error'?' error':'');
 const t=document.createElement('span');t.className='log-time';t.textContent='+'+Math.round(e.elapsed_ms)+' ms';
 const p=document.createElement('span');p.className='log-phase';p.textContent=phaseNames[e.phase]||e.phase;
 const m=document.createElement('span');m.className='log-message';m.textContent=`${String(e.step).padStart(2,'0')} / ${e.message}`;
 if(e.image||e.after){const a=document.createElement('a');a.href=e.image||e.after;a.target='_blank';a.rel='noopener';a.textContent=e.image?'查看编号图 ↗':'查看截图 ↗';a.className='evidence-link';m.append(document.createTextNode('  '),a);}row.append(t,p,m);$('log').append(row);if(e.result)$('log').append(timingRow(e.step,e.result));if(e.phase==='result_image'){const note=document.createElement('div');note.className='capture-time';note.textContent='第 '+e.step+' 步 · 展示结果截图 '+ms(e.capture_ms)+'（单独计时）';$('log').append(note);}if(e.phase==='error'){const note=document.createElement('div');note.className='capture-time';note.textContent='第 '+e.step+' 步 · 停止前用时 '+ms(e.elapsed_ms-(stepStarts[e.step]||0))+'，未获得完整耗时分段。';$('log').append(note);}
}
function setRunning(value){running=value;$('clearRun').disabled=value;$('run').disabled=value||!prepared;$('connect').disabled=value;$('command').disabled=value;$('device').disabled=value;}
async function refreshStatus(){try{const s=await api('/api/status');$('device').replaceChildren();s.devices.forEach(d=>{const opt=document.createElement('option');opt.value=d.serial;opt.textContent=d.serial;$('device').append(opt);});if(!s.devices.length){const opt=document.createElement('option');opt.value='';opt.textContent='未发现在线手机';$('device').append(opt);}if(s.serial){$('device').value=s.serial;$('connectionLabel').textContent='已连接';$('connectionDot').classList.add('connected');live('/api/mirror');}prepared=s.key_ready;$('run').disabled=!prepared;$('prepareStatus').textContent=prepared?'已准备':'待准备';if(s.provider){document.querySelector('input[name=provider][value='+s.provider+']').checked=true;updateProvider();}}catch(e){showError(e.message);}}
$('connect').onclick=async()=>{if(!$('device').value){showError('先用 USB 连接手机，并开启 USB 调试。');return;}$('connect').disabled=true;$('prepareStatus').textContent='准备中…';$('banner').hidden=true;try{const r=await api('/api/connect',{serial:$('device').value,provider:provider(),api_key:$('apiKey').value});prepared=true;$('run').disabled=false;$('prepareStatus').textContent='已准备';live(r.mirror);$('connectionLabel').textContent='已连接';$('connectionDot').classList.add('connected');}catch(e){prepared=false;$('run').disabled=true;$('prepareStatus').textContent='准备失败';showError(e.message);}finally{$('connect').disabled=false;}};
$('command').addEventListener('input',()=>renderSteps(steps()));
$('run').onclick=async()=>{if(running)return;$('banner').hidden=true;try{currentSteps=steps();if(!currentSteps.length)throw new Error('请输入点击目标。');setRunning(true);const r=await api('/api/run',{text:$('command').value});history.replaceState({},'', '/?job='+r.id);seen=0;$('log').replaceChildren();$('timingDetails').hidden=true;evidence={};activeEvidence=null;stepStarts={};$('evidenceThumbs').replaceChildren();$('jobStatus').textContent='执行中';$('runHint').textContent='正在逐步执行，失败即停止。';
 const poll=async()=>{try{const job=await api('/api/jobs/'+r.id);job.events.slice(seen).forEach(event);seen=job.events.length;renderSteps(job.steps,job);if(job.status!=='running'){setRunning(false);$('jobStatus').textContent=job.status==='completed'?'本轮点击已返回':'本轮已停止';$('runHint').textContent=job.status==='completed'?`完成 ${job.results.length} 步，本轮总耗时 ${seconds(job.wall_ms)}`:'失败后的步骤未执行。';polling=null;return;}polling=setTimeout(poll,250);}catch(e){showError('状态读取失败：'+e.message+'。后台可能仍在运行，请勿重复提交。');$('jobStatus').textContent='状态读取中断';polling=null;}};await poll();
 }catch(e){setRunning(false);showError(e.message);}};
function provider(){return document.querySelector('input[name=provider]:checked').value;}
function updateProvider(){const official=provider()==='openai';$('apiKey').placeholder=official?'填写 OpenAI 官方 API Key':'填写 OpenRouter API Key';$('protocolLabel').textContent=official?'OpenAI 官方 · GPT-6 Luna Decisions':'OpenRouter · GPT-6 Luna Decisions';}
function invalidate(){prepared=false;$('run').disabled=true;$('prepareStatus').textContent='待准备';updateProvider();}
document.querySelectorAll('input[name=provider]').forEach(el=>el.addEventListener('change',invalidate));$('apiKey').addEventListener('input',invalidate);
async function initialize(){try{$('apiKey').value='';await api('/api/reset-connection',{});const rules=await api('/api/step-rules');STEP_SEPARATORS=rules.separators;renderSteps(steps());await refreshStatus();await restoreJob();}catch(e){$('run').disabled=true;showError('分隔规则加载失败：'+e.message);}}
initialize();
const refresh=document.createElement('button');refresh.className='secondary refresh';refresh.textContent='重连镜像';refresh.onclick=async()=>{if(running)return;refresh.disabled=true;try{const r=await api('/api/connect',{serial:$('device').value,provider:provider(),api_key:$('apiKey').value});live(r.mirror);}catch(e){showError(e.message);}finally{refresh.disabled=false;}};document.querySelector('.panel-foot').append(refresh);

async function restoreJob(){const generation=displayGeneration;const id=new URLSearchParams(location.search).get('job');if(!id)return;try{const job=await api('/api/jobs/'+id);if(generation!==displayGeneration)return;$('command').value=job.steps.join('；\n');$('log').replaceChildren();evidence={};activeEvidence=null;stepStarts={};job.events.forEach(event);renderSteps(job.steps,job);$('jobStatus').textContent=job.status==='completed'?'本轮点击已返回':job.status==='failed'?'本轮已停止':'执行中';if(job.status==='running'){setRunning(true);setTimeout(restoreJob,400);}else{setRunning(false);$('runHint').textContent=job.status==='completed'?`完成 ${job.results.length} 步，本轮总耗时 ${seconds(job.wall_ms)}`:'失败后的步骤未执行。';}}catch(e){showError('本轮结果已不在服务内存中，请重新执行；原始证据仍保存在本地。');}}

$('clearRun').onclick=()=>{
 if(running)return;
 displayGeneration++;
 if(polling){clearTimeout(polling);polling=null;}
 seen=0;evidence={};activeEvidence=null;stepStarts={};
 $('log').replaceChildren();const empty=document.createElement('div');empty.className='log-placeholder';empty.textContent='本轮展示已清空，可以继续执行。';$('log').append(empty);
 $('evidenceThumbs').replaceChildren();$('annotationImage').removeAttribute('src');$('annotationLink').removeAttribute('href');$('annotationLink').hidden=true;$('annotationEmpty').hidden=false;
 ['currentTarget','point','total','modelTime','localTime'].forEach(id=>$(id).textContent='—');
 $('evidenceStep').textContent='等待执行';$('selection').textContent='等待执行';$('jobStatus').textContent='尚未执行';$('timingDetails').textContent='';$('timingDetails').hidden=true;
 $('runHint').textContent='每一步重新观察，失败即停止。';$('banner').hidden=true;$('banner').textContent='';renderSteps(steps());
 const url=new URL(location.href);url.searchParams.delete('job');history.replaceState({},'',url.pathname+url.search+url.hash);
};
let manualScroll=0;
function flipManual(open){
 const front=$('demoFace'),back=$('technicalManual');
 if(open){manualScroll=window.scrollY;back.inert=false;back.setAttribute('aria-hidden','false');front.inert=true;$('backToDemo').focus({preventScroll:true});front.setAttribute('aria-hidden','true');window.scrollTo({top:0,behavior:'instant'});}
 else{front.inert=false;front.setAttribute('aria-hidden','false');$('showTechnical').focus({preventScroll:true});back.inert=true;back.setAttribute('aria-hidden','true');window.scrollTo({top:manualScroll,behavior:'instant'});}
 $('flipShell').classList.toggle('is-flipped',open);
}
$('showTechnical').onclick=()=>flipManual(true);$('backToDemo').onclick=()=>flipManual(false);$('backToDemoBottom').onclick=()=>flipManual(false);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('flipShell').classList.contains('is-flipped'))flipManual(false);});
