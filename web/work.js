'use strict';
const $=id=>document.getElementById(id),state={rows:[],id:null,editing:null,busy:false,pending:false};let bridge;
const current=()=>state.rows.find(r=>r.n===state.id),parts=s=>s.trim().split(/[、，,；;\s]+/u).filter(Boolean);
const api=(op,body={})=>new Promise((resolve,reject)=>bridge.call(op,JSON.stringify(body),raw=>{try{const v=JSON.parse(raw);v?.error?reject(Error(v.error)):resolve(v)}catch(e){reject(e)}}));
function say(s,type=''){$('status').textContent=s;$('status').parentElement.className=type}
function el(tag,text){const node=document.createElement(tag);node.textContent=text;return node}
function preview(){const r=current();$('film').textContent=r?'作品《'+r.title+'》':'';$('recipient').textContent=r?'第'+r.n+'组：':'';$('awardText').textContent=$('award').value||'待填写奖项';$('credits').textContent=r?'小组成员：'+r.names.join('、'):'';$('stamp').textContent=$('date').value;drawLayout()}
function paint(){
 const query=$('search').value.trim().toLowerCase(),r=current(),count=state.rows.reduce((s,row)=>s+row.awards.length,0);
 $('summary').textContent=state.rows.length+' 个分组　/　'+count+' 张奖状';
 const list=state.rows.filter(x=>[String(x.n),'第'+x.n+'组',x.title,...x.names].some(t=>t.toLowerCase().includes(query)));
 $('rows').replaceChildren(...list.map(x=>{const tr=document.createElement('tr');tr.tabIndex=0;tr.setAttribute('aria-selected',String(x.n===state.id));[x.n+' 组',x.title,x.names.length,x.awards.join('、')||'—'].forEach(t=>tr.append(el('td',t)));tr.onclick=()=>{state.id=x.n;paint()};tr.ondblclick=()=>editor(x);tr.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();state.id=x.n;paint();editor(x)}};return tr}));
 $('empty').hidden=!!list.length;$('empty').textContent=state.rows.length?'没有找到匹配的分组':'导入名单，或新增第一个分组';
 $('groupLabel').textContent=r?'第 '+r.n+' 组 · '+r.names.length+' 位组员':'组员';$('members').replaceChildren(...(r?.names||[]).map(n=>el('span',n)));
 const prior=$('award').value;$('award').replaceChildren(...(r?.awards||[]).map(n=>el('option',n)));if(r?.awards.includes(prior))$('award').value=prior;
 const lock=state.busy||state.pending;
 for(const id of ['import','add','bg','settings','reset','date','design'])$(id).disabled=lock;
 $('edit').disabled=!r||lock;$('awards').disabled=!state.rows.length||lock;$('award').disabled=!r?.awards.length;$('export').disabled=!count||lock||!bridge;
 $('export').setAttribute('aria-busy',String(state.busy));$('export').textContent=state.busy?'正在制作奖状…':'导出 PSD 与分组 PDF　↗';preview()
}
async function action(fn){if(state.pending||state.busy)return;state.pending=true;paint();try{await fn()}catch(e){say(e.message,'error')}finally{state.pending=false;paint()}}
for(const [id,op] of [['import','roster'],['awards','awards']])$(id).onclick=()=>action(async()=>{const rows=await api(op,{rows:state.rows});if(rows){state.rows=rows;state.id=rows[0]?.n;$('search').value='';say('已导入并匹配分组','success')}});
function editor(r){if(state.busy||state.pending)return;state.editing=r?.n??null;$('edtitle').textContent=r?'编辑第 '+r.n+' 组':'新增分组';$('num').value=r?.n??Math.max(0,...state.rows.map(x=>x.n))+1;$('title').value=r?.title||'';$('names').value=r?.names.join('、')||'';$('prizes').value=r?.awards.join('、')||'';$('validation').textContent='';$('editor').showModal();$('title').focus()}
$('form').onsubmit=e=>{e.preventDefault();const n=Number($('num').value),title=$('title').value.trim(),names=parts($('names').value),awards=[...new Set(parts($('prizes').value))];
 if(state.rows.some(x=>x.n===n&&n!==state.editing)||!title||!names.length||new Set(names).size!==names.length||[title,...names,...awards].some(s=>s.includes('|'))){$('validation').textContent='请检查重复组号、姓名或竖线分隔符。';return}
 state.rows=state.rows.filter(x=>x.n!==state.editing).concat({n,title,names,awards}).sort((a,b)=>a.n-b.n);state.id=n;$('editor').close();paint();say('已保存第 '+n+' 组','success')};
$('add').onclick=()=>editor(null);$('edit').onclick=()=>editor(current());$('settings').onclick=()=>$('prefs').showModal();document.querySelectorAll('.close').forEach(b=>b.onclick=()=>b.closest('dialog').close());
for(const id of ['ps','template'])$(id).onclick=()=>action(async()=>{const path=await api(id);if(path){$(id).textContent=path;invalidateProof()}});
$('bg').onclick=()=>action(async()=>{const v=await api('background');if(v){invalidateProof();$('bgname').textContent=v.name;$('bginfo').hidden=false;say('背景已更新','success')}});
$('reset').onclick=()=>action(async()=>{await api('reset');invalidateProof();$('bginfo').hidden=true;say('已恢复内置背景')});
$('export').onclick=()=>action(async()=>{if(await api('export',{rows:state.rows,date:$('date').value.trim(),layout:layoutPlan})){state.busy=true;$('folder').hidden=true;say('Photoshop 正在生成奖状…')}});
$('folder').onclick=()=>action(()=>api('openOutput'));$('date').oninput=preview;$('award').onchange=preview;$('search').oninput=paint;
new QWebChannel(qt.webChannelTransport,async channel=>{bridge=channel.objects.studio;bridge.proof.connect(receiveProof);bridge.result.connect(raw=>{state.busy=false;const v=JSON.parse(raw);$('folder').hidden=!v.ok;say(v.ok?'导出完成 · '+v.path:v.error,v.ok?'success':'error');paint()});try{const v=await api('init');state.rows=v.rows;state.id=v.rows[0]?.n;$('date').value=v.date;$('ps').textContent=v.ps||'选择 Photoshop.exe';say('就绪')}catch(e){say(e.message,'error')}paint()});

async function windowControl(command){
 if(!bridge)return;
 try{const full=await api('window',{command});const b=$('fullscreen');b.title=full?'退出全屏':'全屏';b.setAttribute('aria-label',b.title);b.textContent=full?'❐':'⛶'}
 catch(e){say(e.message,'error')}
}
$('minimize').onclick=()=>windowControl('minimize');$('fullscreen').onclick=()=>windowControl('fullscreen');$('closeWindow').onclick=()=>windowControl('close');
document.querySelector('header').addEventListener('pointerdown',e=>{if(e.button===0&&!e.target.closest('button,nav'))windowControl('move')});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!document.querySelector('dialog[open]'))windowControl('restore')});
