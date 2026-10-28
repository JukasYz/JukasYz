(() => {
'use strict';
const $=id=>document.getElementById(id);
const {draw,clock,colors,text,skins,preview,powers}=window.CyberRender;
const canvas=$('arena');
let ws=null,state=null,joined=false,myId=null,nickname=localStorage.getItem('cybersnake_name')||'',selectedColor=localStorage.getItem('cybersnake_color')||colors[0];
let selectedSkin=localStorage.getItem('cybersnake_skin')||'neon';
if(!skins.some(s=>s.id===selectedSkin))selectedSkin='neon';
let camera={},aimAngle=0,boost=false,activePad=null,keyDirs=new Set(),serverOffset=0;
let toastTimer,wasAlive=false;
let resumeToken=sessionStorage.getItem('cybersnake_token')||'';
joined=!!resumeToken;
function joinPayload(){return {type:'player:join',name:nickname,color:selectedColor,skin:selectedSkin,token:resumeToken};}
const isTouch=('ontouchstart' in window)||navigator.maxTouchPoints>0;
$('nameInput').value=nickname;
for(const color of colors){const button=document.createElement('button');button.className='color-swatch'+(color===selectedColor?' selected':'');button.style.setProperty('--swatch',color);button.setAttribute('aria-label','Cor '+color);button.addEventListener('click',()=>{selectedColor=color;renderPreview();document.querySelectorAll('.color-swatch').forEach(b=>b.classList.toggle('selected',b===button));});$('colors').append(button);}
function renderPreview(){
 const name=$('nameInput').value.trim().slice(0,18)||'Sua cobrinha';
 preview($('skinPreview'),selectedSkin,selectedColor,name);
 $('skinDescription').textContent=skins.find(s=>s.id===selectedSkin).description;
 for(const button of $('skins').children){
   const active=button.dataset.skin===selectedSkin;
   button.classList.toggle('selected',active);button.setAttribute('aria-pressed',String(active));
   preview(button.querySelector('canvas'),button.dataset.skin,selectedColor);
 }
}
for(const skin of skins){
 const button=document.createElement('button');button.type='button';button.className='skin-option';button.dataset.skin=skin.id;
 button.setAttribute('aria-label','Skin '+skin.name);button.title=skin.description;
 const sample=document.createElement('canvas');sample.setAttribute('aria-hidden','true');
 button.append(sample,text('span','',skin.name));
 button.addEventListener('click',()=>{selectedSkin=skin.id;renderPreview();});$('skins').append(button);
}
$('nameInput').addEventListener('input',renderPreview);
window.addEventListener('resize',()=>{if(!joined)renderPreview();});
renderPreview();
function send(payload){if(ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify(payload));}
function toast(message){clearTimeout(toastTimer);$('toast').textContent=message;$('toast').classList.add('show');toastTimer=setTimeout(()=>$('toast').classList.remove('show'),2300);}
function connect(){
 ws=new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
 $('statusText').textContent='Conectando';$('connectionDot').className='status-dot';
 ws.onopen=()=>{ $('statusText').textContent='Online';$('connectionDot').className='status-dot online';if(joined)send(joinPayload());};
 ws.onclose=()=>{boost=false;keyDirs.clear();$('statusText').textContent='Reconectando';$('connectionDot').className='status-dot offline';setTimeout(connect,1200);};
 ws.onerror=()=>{};
 ws.onmessage=event=>{
   let msg;try{msg=JSON.parse(event.data);}catch{return;}
   if(msg.type==='state'){state=msg;serverOffset=msg.serverNow-Date.now();updateUI();}
   if(msg.type==='join:ack'){
     if(!msg.ok){joined=false;$('joinCard').hidden=false;$('joinError').textContent=msg.error||'Não foi possível entrar.';$('joinButton').disabled=false;return;}
     joined=true;myId=msg.id;resumeToken=msg.token||'';sessionStorage.setItem('cybersnake_token',resumeToken);wasAlive=false;nickname=msg.name;selectedSkin=msg.skin||'neon';selectedColor=msg.color||selectedColor;localStorage.setItem('cybersnake_skin',selectedSkin);localStorage.setItem('cybersnake_name',nickname);localStorage.setItem('cybersnake_color',selectedColor);
     $('joinError').textContent='';$('joinButton').disabled=false;$('joinCard').hidden=true;
     $('waitingName').textContent=nickname;updateUI();toast('Você entrou na arena!');
   }
   if(msg.type==='feed'){const myName=nickname;if(joined && msg.entry?.message?.includes(myName) && !msg.entry.message.includes('entrou na arena'))toast(msg.entry.message);}
   if(msg.type==='kicked'){resumeToken='';sessionStorage.removeItem('cybersnake_token');joined=false;myId=null;$('joinCard').hidden=false;$('waitCard').hidden=true;for(const id of ['hud','leaderMini','boostbar','virtualPad','boostButton','resultsCard','countdownCard','respawnToast','pauseOverlay','activePowers'])$(id).hidden=true;toast('O apresentador removeu você da sala.');}
 };
}
$('joinButton').addEventListener('click',()=>{
 const value=$('nameInput').value.trim();
 if(value.length<2){$('joinError').textContent='Escolha um apelido com pelo menos 2 caracteres.';return;}
 nickname=value.slice(0,18);joined=true;$('joinButton').disabled=true;$('joinError').textContent='';
 send(joinPayload());
 if(ws?.readyState!==WebSocket.OPEN){$('joinError').textContent='Aguarde a conexão...';$('joinButton').disabled=false;}
});
$('nameInput').addEventListener('keydown',e=>{if(e.key==='Enter')$('joinButton').click();});
function updateUI(){
 if(!state||!joined)return;
 const phase=state.phase;
 $('waitingPlayers').textContent=state.playerCount;
 $('joinCard').hidden=true;
 $('waitCard').hidden=phase!=='LOBBY';
 $('countdownCard').hidden=phase!=='COUNTDOWN';
 $('resultsCard').hidden=phase!=='RESULTS';
 $('pauseOverlay').hidden=phase!=='PAUSED';
 const playing=phase==='RUNNING'||phase==='PAUSED';
 $('hud').hidden=!playing;$('leaderMini').hidden=!playing;$('boostbar').hidden=!playing;
 $('virtualPad').hidden=!playing||!isTouch;$('boostButton').hidden=!playing||!isTouch;
 const me=state.players.find(p=>p.id===myId);
 $('activePowers').hidden=!playing||!me?.alive||!me?.effects?.length;
 $('activePowers').replaceChildren();
 if(playing&&me?.alive)for(const effect of me.effects||[]){
   const info=powers[effect.kind];if(!info)continue;
   const pill=text('span','power-pill',`${info.icon} ${info.name} · ${Math.ceil(effect.remainingMs/1000)}s`);
   pill.style.borderColor=info.color;$('activePowers').append(pill);
 }
 if(me){
   if(me.alive&&!wasAlive)aimAngle=me.angle;
   wasAlive=me.alive;
   $('myScore').textContent=me.score;
   $('myRank').textContent=(state.leaderboard.find(p=>p.id===myId)?.rank||'—')+'º';
   $('boostFill').style.width=me.boostEnergy+'%';
   $('respawnToast').hidden=!(playing&&!me.alive);
   if(!me.alive)$('respawnToast').textContent=`Reiniciando em ${Math.max(1,Math.ceil(me.respawnMs/1000))}s...`;
 }
 if(phase==='RESULTS'){
   $('podium').replaceChildren();
   state.leaderboard.slice(0,3).forEach((p,i)=>{
     const el=text('div','podium-item','');
     el.append(text('small','', ['🥇 PRIMEIRO','🥈 SEGUNDO','🥉 TERCEIRO'][i]), text('b','',p.name), text('strong','',p.score));
     $('podium').append(el);
   });
   const rank=state.leaderboard.find(p=>p.id===myId);
   $('myResult').textContent=rank?`Seu resultado: ${rank.rank}º lugar • ${rank.score} pontos`:'Você participou da rodada!';
 }
 const leader=$('leaderRows');leader.replaceChildren();
 for(const p of state.leaderboard.slice(0,5)){
   const row=text('div','mini-row','');
   row.append(text('b','',p.rank),text('i','',''),text('span','',(p.id===state.leaderId?'👑 ':'')+p.name),text('strong','',p.score));row.children[1].style.background=p.color;leader.append(row);
 }
}
function tick(){
 if(state){
   draw(canvas,state,myId,false,camera);
   const time=Date.now()+serverOffset;
   if(state.phase==='COUNTDOWN')$('countdownNumber').textContent=Math.max(1,Math.ceil((state.countdownEndAt-time)/1000));
   if(state.phase==='RUNNING'||state.phase==='PAUSED')$('matchClock').textContent=clock(state.roundEndAt-(state.phase==='PAUSED'?state.pausedAt:time));
   const p=state.players?.find(x=>x.id===myId);
  
 }
 requestAnimationFrame(tick);
}
function controlLoop(){
 if(!joined||state?.phase!=='RUNNING')return;
 if(keyDirs.size){
   const dy=(keyDirs.has('ArrowDown')||keyDirs.has('s')?1:0)-(keyDirs.has('ArrowUp')||keyDirs.has('w')?1:0);
   const dx=(keyDirs.has('ArrowRight')||keyDirs.has('d')?1:0)-(keyDirs.has('ArrowLeft')||keyDirs.has('a')?1:0);
   if(dx||dy)aimAngle=Math.atan2(dy,dx);
 }
 send({type:'player:input',angle:aimAngle,boost});
}
window.addEventListener('mousemove',e=>{if(!joined||isTouch)return;const rect=canvas.getBoundingClientRect();const dx=e.clientX-(rect.left+rect.width/2),dy=e.clientY-(rect.top+rect.height/2);if(Math.hypot(dx,dy)>30)aimAngle=Math.atan2(dy,dx);});
window.addEventListener('keydown',e=>{if(e.target.matches('input,textarea,select'))return;if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '].includes(e.key))e.preventDefault();if(e.key===' ')boost=true;else keyDirs.add(e.key.length===1?e.key.toLowerCase():e.key);});
window.addEventListener('keyup',e=>{if(e.key===' ')boost=false;else keyDirs.delete(e.key.length===1?e.key.toLowerCase():e.key);});
function clearControls(){keyDirs.clear();endBoost();activePad=null;thumb.style.transform='translate(0,0)';}
window.addEventListener('blur',clearControls);
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearControls();});
const pad=$('virtualPad'),thumb=$('padThumb'),padBase=pad.querySelector('.pad-base');
function padMove(e){
 if(e.pointerId!==activePad)return;
 const r=padBase.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;
 const dx=e.clientX-cx,dy=e.clientY-cy,len=Math.hypot(dx,dy),limit=34;
 const factor=len?Math.min(1,limit/len):0;
 thumb.style.transform=`translate(${dx*factor}px,${dy*factor}px)`;
 if(len>12)aimAngle=Math.atan2(dy,dx);
}
pad.addEventListener('pointerdown',e=>{e.preventDefault();activePad=e.pointerId;pad.setPointerCapture(e.pointerId);padMove(e);});
pad.addEventListener('pointermove',padMove);
function resetPad(e){if(activePad!==e.pointerId)return;activePad=null;thumb.style.transform='translate(0,0)';}
pad.addEventListener('pointerup',resetPad);pad.addEventListener('pointercancel',resetPad);
const boostButton=$('boostButton');
boostButton.addEventListener('pointerdown',e=>{e.preventDefault();boost=true;boostButton.classList.add('pressed');boostButton.setPointerCapture(e.pointerId);});
function endBoost(){boost=false;boostButton.classList.remove('pressed');}
boostButton.addEventListener('pointerup',endBoost);boostButton.addEventListener('pointercancel',endBoost);
connect();setInterval(controlLoop,50);requestAnimationFrame(tick);
})();
