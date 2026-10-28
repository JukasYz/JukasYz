(() => {
'use strict';
const $=id=>document.getElementById(id);
const {draw,clock,text}=window.CyberRender;
const key=new URLSearchParams(location.search).get('key')||sessionStorage.getItem('cybersnake_host_key')||'';
if(key){sessionStorage.setItem('cybersnake_host_key',key);history.replaceState(null,'',location.pathname);}
const hostCanvas=$('hostArena');
let ws=null,authorized=false,state=null,camera={},feed=[],serverOffset=0,selectedUrl='';
const phases={LOBBY:'LOBBY',COUNTDOWN:'CONTAGEM',RUNNING:'AO VIVO',PAUSED:'PAUSADO',RESULTS:'ENCERRADO'};
function send(payload){if(ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify(payload));}
function connect(){
 ws=new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
 $('hostStatus').textContent='Conectando';$('hostDot').className='status-dot';
 ws.onopen=()=>{send({type:'host:auth',key});};
 ws.onclose=()=>{authorized=false;$('hostStatus').textContent='Reconectando';$('hostDot').className='status-dot offline';setTimeout(connect,1500);};
 ws.onmessage=event=>{
   let msg;try{msg=JSON.parse(event.data);}catch{return;}
   if(msg.type==='host:auth:ack'){
     if(!msg.ok){$('hostAuthFail').hidden=false;return;}
     authorized=true;$('hostAuthFail').hidden=true;$('hostStatus').textContent='Servidor online';$('hostDot').className='status-dot online';feed=msg.events||[];renderEvents();
   }
   if(msg.type==='state'&&authorized){state=msg;serverOffset=msg.serverNow-Date.now();updateUI();}
   if(msg.type==='feed'&&authorized){feed.unshift(msg.entry);feed=feed.slice(0,7);renderEvents();}
   if(msg.type==='host:ack'){if(!msg.ok)$('hostMessage').textContent=msg.error||'Ação não permitida.';}
 };
}
function renderEvents(){
 const el=$('events');el.replaceChildren();
 if(!feed.length)el.append(text('p','roster-empty','Nenhuma atividade ainda.'));
 for(const ev of feed)el.append(text('div','event-row',ev.message));
}
function updateUI(){
 if(!state)return;
 $('statsPlayers').replaceChildren(document.createTextNode(state.playerCount+' '),text('span','','/ 40'));
 $('statsRound').textContent=String(state.round).padStart(2,'0');
 $('statsPhase').textContent=phases[state.phase]||state.phase;
 $('statsBest').textContent=state.leaderboard[0]?.score||0;
 $('rosterCount').textContent=`${state.playerCount}/40`;
 $('hostArenaOverlay').hidden=state.phase!=='LOBBY' && state.phase!=='RESULTS';
 if(state.phase==='RESULTS'){
   $('hostArenaOverlay').querySelector('b').textContent='🏆 RODADA ENCERRADA';
   $('hostArenaOverlay').querySelector('small').textContent=state.leaderboard[0]?`${state.leaderboard[0].name} venceu com ${state.leaderboard[0].score} pontos!`:'Todos podem tentar novamente!';
 }else{
   $('hostArenaOverlay').querySelector('b').textContent='AGUARDANDO JOGADORES';
   $('hostArenaOverlay').querySelector('small').textContent='Compartilhe o QR Code com a turma';
 }
 $('pauseButton').disabled=!['RUNNING','PAUSED'].includes(state.phase);
 $('pauseButton').textContent=state.phase==='PAUSED'?'▶ CONTINUAR':'⏸ PAUSAR';
 $('startButton').disabled=state.playerCount===0 || !['LOBBY','RESULTS'].includes(state.phase);
 $('startButton').textContent=state.phase==='RESULTS'?'▶ NOVA RODADA':'▶ INICIAR RODADA';
 $('duration').disabled=!['LOBBY','RESULTS'].includes(state.phase);
 if(state.phase==='LOBBY')$('hostMessage').textContent=state.playerCount ? `${state.playerCount} pessoa(s) conectada(s). Tudo pronto para começar.`:'Aguarde alguém entrar pelo celular.';
 if(state.phase==='COUNTDOWN')$('hostMessage').textContent='Contagem regressiva iniciada. Prepare-se!';
 if(state.phase==='RUNNING')$('hostMessage').textContent='Partida acontecendo. Você pode pausar a qualquer momento.';
 if(state.phase==='PAUSED')$('hostMessage').textContent='Tempo congelado. Clique em continuar para retomar.';
 if(state.phase==='RESULTS')$('hostMessage').textContent='Jogo encerrado. Inicie outra rodada quando quiser.';
 const rank=$('hostLeaderboard');rank.replaceChildren();
 if(!state.leaderboard.length)rank.append(text('div','roster-empty','O ranking aparecerá após a entrada dos jogadores.'));
 for(const p of state.leaderboard.slice(0,10)){
   const row=text('div','rank-row',''),num=text('div','rank-num',`${p.rank}º`),dot=text('div','rank-dot','');dot.style.background=p.color;
   row.append(num,dot,text('span','rank-name',(p.id===state.leaderId?'👑 ':'')+p.name),text('span','rank-score',`${p.score} pts`));rank.append(row);
 }
 const roster=$('roster');roster.replaceChildren();
 if(!state.players.length)roster.append(text('p','roster-empty','Ninguém entrou ainda.'));
 const participants=[...state.players].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
 for(const p of participants){
   const row=text('div','roster-row',''),dot=text('div','rank-dot','');dot.style.background=p.color;
   const kick=text('button','','×');kick.title='Remover '+p.name;kick.setAttribute('aria-label','Remover '+p.name);
   kick.addEventListener('click',()=>{if(confirm(`Remover ${p.name} da sala?`))send({type:'host:kick',id:p.id});});
   row.append(dot,text('span','rank-name',p.name),kick);roster.append(row);
 }
}
function animation(){
 if(state){
   draw(hostCanvas,state,null,true,camera);
   const time=Date.now()+serverOffset;
   if(state.phase==='COUNTDOWN')$('clockHost').textContent=String(Math.max(1,Math.ceil((state.countdownEndAt-time)/1000)))+'...';
   else if(['RUNNING','PAUSED','RESULTS'].includes(state.phase))$('clockHost').textContent=clock(state.roundEndAt-(state.phase==='PAUSED'?state.pausedAt:time));
   else $('clockHost').textContent=clock(Number($('duration').value)*1000);
 }
 requestAnimationFrame(animation);
}
async function loadJoinUrls(){
 try{
 const resp=await fetch('/api/config',{cache:'no-store'}),config=await resp.json();
 const options=[...new Set([...(location.hostname==='localhost'||location.hostname==='127.0.0.1'?[]:[location.origin+'/']),...config.joinUrls])];
 const select=$('joinUrl');select.replaceChildren();
 for(const url of options){const opt=document.createElement('option');opt.value=url;opt.textContent=url;select.append(opt);}
 selectedUrl=options[0]||location.origin+'/';updateQR();
 }catch{$('hostMessage').textContent='Não foi possível gerar o QR Code. Atualize a página.';}
}
function updateQR(){selectedUrl=$('joinUrl').value;$('qrImage').src='/api/qr?url='+encodeURIComponent(selectedUrl);}
$('joinUrl').addEventListener('change',updateQR);
$('copyButton').addEventListener('click',async()=>{
 try{await navigator.clipboard.writeText(selectedUrl);$('copyButton').textContent='LINK COPIADO ✓';setTimeout(()=>$('copyButton').textContent='COPIAR LINK DE ENTRADA ↗',1800);}
 catch{prompt('Copie o link:',selectedUrl);}
});
$('startButton').addEventListener('click',()=>send({type:'host:start',duration:Number($('duration').value)}));
$('pauseButton').addEventListener('click',()=>send({type:'host:pause'}));
$('lobbyButton').addEventListener('click',()=>{if(state?.phase==='LOBBY'||confirm('Encerrar a partida atual e voltar ao lobby?'))send({type:'host:lobby'});});
$('duration').addEventListener('change',()=>{if(state?.phase==='LOBBY')$('clockHost').textContent=clock(Number($('duration').value)*1000);});
if(!key)$('hostAuthFail').hidden=false;
connect();loadJoinUrls();requestAnimationFrame(animation);
})();
