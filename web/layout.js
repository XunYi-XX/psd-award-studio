'use strict';
const presets={
 heading:['证书标题','荣誉证书',50,12.7,67.3,84,'center'],
 group:['组别称呼','{组别}：',10.1,27.8,27.8,82,'left'],
 body:['活动正文','        在南京工业大学融媒体中心电视台组织的“2026新生\n微视频创作大赛”中，表现优异，作品《{作品名}》',10.1,35.2,22.2,82,'left'],
 award:['奖项文字','被评为“{奖项}”',50,53.2,48,84,'center'],
 members:['组员名单','小组成员： {组员}',12.9,67.4,20,79,'left'],
 note:['名单排序说明','（按照姓氏首字母排序）',17.4,72.1,9,22,'center'],
 signature:['发证单位与日期','南京工业大学融媒体中心电视台\n{日期}',74.2,80.5,14,44,'center']
};
let layoutPlan={version:1,layers:{}},activeBlock='heading',drag=null;
const blockKeys=()=>[...new Set([...Object.keys(presets),...Object.keys(layoutPlan.layers)])];
function config(k){if(layoutPlan.layers[k])return layoutPlan.layers[k];const [,text,x,y,pt,width,align]=presets[k];return {text,x,y,pt,width,align,visible:true}}
function changed(k){return layoutPlan.layers[k]??=Object.assign({},config(k))}
let proof=null, requested='', wanted='', ticket=0, activeTicket=0, revision=0, timer=0, running=false;
function proofMsg(msg){$('proofStatus').textContent=msg;if($('designer').open)$('designStatus').textContent=msg}
function invalidateProof(){revision++;drawLayout()}
function proofInput(){const row=current();return row?{row,award:$('award').value,date:$('date').value.trim(),layout:layoutPlan,revision}:null}
function drawLayout(){
 const data=proofInput();const key=data?JSON.stringify(data):'';
 if(key!==wanted){wanted=key;$('paper').classList.add('pending');$('sheet').classList.add('pending');proofMsg(key?'正在更新 Photoshop 预览…':'导入分组后显示 Photoshop 预览');}
 if(!key){for(const e of [$('paper'),$('sheet')])e.style.backgroundImage='none';proof=null;requested='';return}
 if(key!==requested&&!running&&!drag){clearTimeout(timer);timer=setTimeout(async()=>{
    if(running||!wanted||drag)return;running=true;requested=wanted;activeTicket=++ticket;
    try{await api('preview',{...JSON.parse(requested),ticket:activeTicket})}catch(e){receiveProof(JSON.stringify({ticket:activeTicket,error:e.message}))}
 },500)}
 if($('designer').open)drawHandles()
}
function receiveProof(raw){
 const v=JSON.parse(raw);if(v.ticket!==activeTicket)return;running=false;
 if(requested!==wanted){drawLayout();return}
 if(v.error){proof=null;for(const e of [$('paper'),$('sheet')]){e.style.backgroundImage='none';e.classList.add('pending')};$('sheet').replaceChildren();proofMsg('预览未生成：'+v.error);return}
 proof=v;
 for(const e of [$('paper'),$('sheet')]){e.style.backgroundImage='url("'+v.url+'")';e.style.aspectRatio=v.width+'/'+v.height;e.classList.remove('pending')}
 proofMsg('Photoshop 实际渲染 · '+v.width+' × '+v.height+' px');drawHandles()
}
function drawHandles(){
 const sheet=$('sheet');sheet.replaceChildren();if(!proof||!$('designer').open)return;
 for(const [k,b] of Object.entries(proof.rects)){
  if(!blockKeys().includes(k)||!config(k).visible)continue;
  const node=document.createElement('span'),c=config(k);node.className='hitbox'+(k===activeBlock?' active':'');node.dataset.key=k;node.title=presets[k]?.[0]||'自定义文本';
  const [x,y,r,d]=b;let left=x/proof.width*100,top=y/proof.height*100;
  if(drag?.key===k){left+=c.x-drag.x;top+=c.y-drag.y}
  Object.assign(node.style,{left:left+'%',top:top+'%',width:(r-x)/proof.width*100+'%',height:(d-y)/proof.height*100+'%'});sheet.append(node);
  node.onpointerdown=e=>{if(requested!==wanted||running)return;e.preventDefault();activeBlock=k;
   const orig=config(k),bx=orig.align==='left'?x:orig.align==='right'?r:(x+r)/2;
   const box=sheet.getBoundingClientRect();drag={key:k,px:e.clientX,py:e.clientY,x:bx/proof.width*100,y:y/proof.height*100,w:box.width,h:box.height};
   inspector();sheet.setPointerCapture(e.pointerId);node.classList.add('active')}
 }
}
function inspector(){
 const select=$('block');select.replaceChildren(...blockKeys().map(k=>{const o=document.createElement('option');o.value=k;o.textContent=presets[k]?.[0]||'自定义文本 '+k.split('_')[1];return o}));select.value=activeBlock;
 const c=config(activeBlock);for(const [id,key] of [['copy','text'],['posX','x'],['posY','y'],['pointSize','pt'],['textWidth','width'],['alignment','align']])$(id).value=c[key];$('visible').checked=c.visible
}
function commitFields(){for(const id of ['posX','posY','pointSize','textWidth'])if(!$(id).value||!$(id).checkValidity()){$(id).reportValidity();return false}return true}
document.addEventListener('DOMContentLoaded',()=>{
 $('design').onclick=()=>{$('designer').showModal();inspector();drawLayout();$('designStatus').textContent=$('proofStatus').textContent};
 $('block').onchange=e=>{activeBlock=e.target.value;inspector();drawLayout()};
 for(const [id,key] of [['copy','text'],['posX','x'],['posY','y'],['pointSize','pt'],['textWidth','width'],['alignment','align'],['visible','visible']]){
  $(id).oninput=e=>{const t=e.target;if(t.type==='number'&&(!t.value||!t.checkValidity()))return;changed(activeBlock)[key]=t.type==='number'?Number(t.value):t.type==='checkbox'?t.checked:t.value;drawLayout()}
 }
 for(const k of ['组号','组别','作品名','奖项','组员','日期']){const o=document.createElement('option');o.value='{'+k+'}';o.textContent=o.value;$('token').append(o)}
 $('token').onchange=e=>{const t=$('copy');t.setRangeText(e.target.value,t.selectionStart,t.selectionEnd,'end');t.oninput({target:t});e.target.value='';t.focus()};
 $('newBlock').onclick=()=>{let i=1;while(layoutPlan.layers['extra_'+i])i++;if(blockKeys().length>=30){$('designStatus').textContent='最多可使用 30 个文本块';return}activeBlock='extra_'+i;layoutPlan.layers[activeBlock]={text:'自定义文字',x:50,y:47,pt:21,width:75,align:'center',visible:true};inspector();drawLayout()};
 const sheet=$('sheet');sheet.onpointermove=e=>{if(!drag)return;const c=changed(drag.key);
  const pct=v=>Math.max(0,Math.min(100,Math.round(v*10)/10));c.x=pct(drag.x+(e.clientX-drag.px)*100/drag.w);c.y=pct(drag.y+(e.clientY-drag.py)*100/drag.h);$('posX').value=c.x;$('posY').value=c.y;drawLayout()};
 sheet.onpointerup=sheet.onpointercancel=()=>{drag=null;drawLayout()};
 $('doneLayout').onclick=()=>{if(commitFields()){$('designer').close();say('布局已应用到本次批量导出','success')}};
 $('factory').onclick=()=>{if(!Object.keys(layoutPlan.layers).length)return;layoutPlan={version:1,layers:{}};activeBlock='heading';inspector();drawLayout();$('designStatus').textContent='已恢复模板原版布局'};
 $('saveLayout').onclick=async()=>{if(!commitFields())return;try{if(await api('saveLayout',layoutPlan))$('designStatus').textContent='布局方案已保存'}catch(e){$('designStatus').textContent=e.message}};
 $('loadLayout').onclick=async()=>{try{const v=await api('loadLayout');if(v){layoutPlan=v;activeBlock='heading';inspector();drawLayout();$('designStatus').textContent='布局方案已载入'}}catch(e){$('designStatus').textContent=e.message}};
 new ResizeObserver(()=>{if(typeof state!=='undefined')drawLayout()}).observe($('paper'))
});
