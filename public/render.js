/* Renderizador compartilhado por celulares, PCs e telão.  Sem bibliotecas externas. */
(() => {
  const TAU = Math.PI * 2;
  const palette = ['#B96CFF','#53E6D1','#F7CB65','#FD77B6','#6BB9FF','#B8EF73','#FF946F','#F3F0FF'];
  const grid = 80;
  const renderer = {};
  renderer.fit = function(canvas) {
    const box = canvas.getBoundingClientRect();
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.7);
    const w = Math.max(1, Math.round(box.width * pixelRatio));
    const h = Math.max(1, Math.round(box.height * pixelRatio));
    if(canvas.width !== w || canvas.height !== h) {canvas.width = w; canvas.height = h;}
    return {ctx:canvas.getContext('2d'), w:box.width,h:box.height,dpr:pixelRatio};
  };
  renderer.skins = [
    {id:'neon',name:'Neon',description:'Brilho clássico da arena.'},
    {id:'circuit',name:'Conexões',description:'Nós e circuitos para conectar caminhos.'},
    {id:'striped',name:'Listras',description:'Faixas claras na sua cor favorita.'},
    {id:'pixel',name:'Pixel',description:'Um visual quadrado de jogo retrô.'},
    {id:'galaxy',name:'Galáxia',description:'Pequenas estrelas no seu rastro.'}
  ];
  renderer.powers={magnet:{icon:'🧲',name:'Ímã',color:'#fd77b6'},shield:{icon:'🛡',name:'Escudo',color:'#53e6d1'},turbo:{icon:'⚡',name:'Turbo',color:'#f7cb65'}};
  renderer.snake=function(ctx,p,{focus=false,leader=false,t=0}={}){
    if(!p.alive||!p.trail?.length)return;
    ctx.save();
    const pts=[...p.trail].reverse(),pixel=p.skin==='pixel';
    ctx.globalAlpha=p.shield ? .68 : 1;
    if(pts.length>=2){
      ctx.lineJoin=pixel?'miter':'round';ctx.lineCap=pixel?'butt':'round';
      ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);
      for(const [x,y] of pts.slice(1))ctx.lineTo(x,y);
      ctx.strokeStyle=p.color;ctx.lineWidth=19;ctx.shadowColor=p.color;ctx.shadowBlur=12;ctx.stroke();ctx.shadowBlur=0;
      ctx.strokeStyle='#fff';ctx.lineWidth=4;ctx.globalAlpha=p.shield ? .12 : .19;ctx.stroke();ctx.globalAlpha=p.shield ? .68 : 1;
    }
    ctx.strokeStyle='#ffffffbb';ctx.fillStyle='#fff';
    for(let i=3;i<p.trail.length;i+=p.skin==='galaxy'?4:3){
      const [x,y]=p.trail[i],prior=p.trail[i-1];
      const angle=Math.atan2(y-prior[1],x-prior[0])+Math.PI/2;
      const dx=Math.cos(angle),dy=Math.sin(angle);
      if(p.skin==='striped'){
        ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x-dx*8,y-dy*8);ctx.lineTo(x+dx*8,y+dy*8);ctx.stroke();
      }else if(p.skin==='circuit'){
        ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,3,0,TAU);ctx.stroke();
        ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+dx*7,y+dy*7);ctx.stroke();
      }else if(p.skin==='pixel'){
        ctx.fillStyle='#ffffff99';ctx.fillRect(x-3,y-3,5,5);
      }else if(p.skin==='galaxy'){
        const side=i%2?1:-1,sx=x+dx*side*5,sy=y+dy*side*5;
        ctx.lineWidth=1.3;ctx.beginPath();ctx.moveTo(sx-2.5,sy);ctx.lineTo(sx+2.5,sy);ctx.moveTo(sx,sy-2.5);ctx.lineTo(sx,sy+2.5);ctx.stroke();
      }
    }
    ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=18;
    if(pixel)ctx.fillRect(p.x-10,p.y-10,20,20);
    else{ctx.beginPath();ctx.arc(p.x,p.y,11,0,TAU);ctx.fill();}
    ctx.shadowBlur=0;
    const dx=Math.cos(p.angle),dy=Math.sin(p.angle);
    ctx.fillStyle='#fff';
    for(const side of [-1,1]){ctx.beginPath();ctx.arc(p.x+dx*5-dy*side*5,p.y+dy*5+dx*side*5,2.4,0,TAU);ctx.fill();}
    if(p.shield){ctx.strokeStyle='#b7fff1';ctx.lineWidth=2;ctx.setLineDash([5,5]);ctx.beginPath();ctx.arc(p.x,p.y,25+Math.sin(t*8)*2,0,TAU);ctx.stroke();ctx.setLineDash([]);}
    if(p.effects?.some(e=>e.kind==='magnet')){ctx.strokeStyle='#fd77b644';ctx.lineWidth=1;ctx.setLineDash([8,12]);ctx.beginPath();ctx.arc(p.x,p.y,115,0,TAU);ctx.stroke();ctx.setLineDash([]);}
    ctx.globalAlpha=1;
    if(p.name){
      const label=p.name.slice(0,18);ctx.font='700 13px system-ui';ctx.textAlign='center';ctx.textBaseline='bottom';
      ctx.strokeStyle='#10091d';ctx.lineWidth=4;ctx.strokeText(label,p.x,p.y-19);
      ctx.fillStyle=focus?'#fff':p.color;ctx.fillText(label,p.x,p.y-19);
    }
    if(leader){
      // Vector crown: same appearance on mobile and desktop, without emoji fonts.
      ctx.save();ctx.translate(p.x,p.y-52);ctx.fillStyle='#f7cb65';ctx.strokeStyle='#5b3615';ctx.lineWidth=2;
      ctx.beginPath();ctx.moveTo(-13,0);ctx.lineTo(-10,13);ctx.lineTo(10,13);ctx.lineTo(13,0);ctx.lineTo(5,6);ctx.lineTo(0,-4);ctx.lineTo(-5,6);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
      ctx.strokeStyle='#f7cb6599';ctx.lineWidth=2;ctx.beginPath();ctx.arc(p.x,p.y,30,0,TAU);ctx.stroke();
    }
    if(focus){ctx.strokeStyle='#fff4';ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(p.x,p.y,34,0,TAU);ctx.stroke();}
    ctx.restore();
  };
  renderer.preview=function(canvas,skin,color,name=''){
    const {ctx,w,h,dpr}=renderer.fit(canvas);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    const headX=w*.78,headY=h*.62,spacing=Math.min(5,w/42);
    const trail=Array.from({length:26},(_,i)=>[headX-i*spacing,headY+Math.sin(i*.22)*7]);
    renderer.snake(ctx,{id:'preview',alive:true,x:headX,y:headY,angle:0,trail,skin,color,name});
  };
  renderer.draw = function(canvas, state, focusId, host=false, camera={}) {
    const box=renderer.fit(canvas), {ctx,w,h,dpr}=box;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle='#100b1c';ctx.fillRect(0,0,w,h);
    if(!state) return;
    // Smooth authoritative snapshots; do not predict collisions or scores.
    const stamp=performance.now(), dt=Math.min(.1,(stamp-(camera.stamp||stamp))/1000);
    camera.stamp=stamp;camera.positions??={};
    const alpha=1-Math.exp(-dt*24);
    const players=state.players.map(p=>{
      let old=camera.positions[p.id];
      if(!old||!p.alive||Math.hypot(p.x-old.x,p.y-old.y)>180)old={x:p.x,y:p.y};
      const x=old.x+(p.x-old.x)*alpha,y=old.y+(p.y-old.y)*alpha;
      camera.positions[p.id]={x,y};
      return {...p,x,y};
    });
    const active=new Set(players.map(p=>p.id));
    for(const id of Object.keys(camera.positions))if(!active.has(id))delete camera.positions[id];
    const W=state.width||3600,H=state.height||2400;
    const player=players.find(p=>p.id===focusId);
    const zoom=host ? Math.min((w-20)/W,(h-20)/H) : Math.min(1.25,Math.max(.68,Math.min(w/510,h/700)));
    const targetX=host? W/2:player?.x??W/2;
    const targetY=host? H/2:player?.y??H/2;
    camera.x = camera.x===undefined ? targetX : camera.x+(targetX-camera.x)*(host?1:.16);
    camera.y = camera.y===undefined ? targetY : camera.y+(targetY-camera.y)*(host?1:.16);
    const visible=(x,y,margin=30)=>Math.abs(x-camera.x)<=w/(2*zoom)+margin&&Math.abs(y-camera.y)<=h/(2*zoom)+margin;
    ctx.save();ctx.translate(w/2,h/2);ctx.scale(zoom,zoom);ctx.translate(-camera.x,-camera.y);
    ctx.fillStyle='#171025';ctx.fillRect(0,0,W,H);
    ctx.strokeStyle='#2a1b3d';ctx.lineWidth=1;
    ctx.beginPath();for(let x=0;x<=W;x+=grid){ctx.moveTo(x,0);ctx.lineTo(x,H);}
    for(let y=0;y<=H;y+=grid){ctx.moveTo(0,y);ctx.lineTo(W,y);}ctx.stroke();
    ctx.strokeStyle='#9A51EB';ctx.shadowBlur=18;ctx.shadowColor='#a24eff';ctx.lineWidth=7;ctx.strokeRect(3,3,W-6,H-6);ctx.shadowBlur=0;
    const t=performance.now()/1000;
    for(const item of state.food || []) {
      const [id,x,y,kind]=item;
      if(!visible(x,y))continue;
      const color=kind===2?'#f9cf6d':kind===1?'#54ebd5':'#aa73ee';
      const r=kind===2?8:kind===1?6:4;
      ctx.globalAlpha=.6+.3*Math.sin(t*2+id);
      ctx.fillStyle=color;ctx.shadowColor=color;ctx.shadowBlur=kind===2?18:12;
      ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();ctx.shadowBlur=0;
      if(kind===2){ctx.strokeStyle='#ffe9aa';ctx.lineWidth=1.4;ctx.stroke();}
    }ctx.globalAlpha=1;
    for(const [,x,y,kind] of state.powerups||[]){
      if(!visible(x,y,50))continue;
      const info=renderer.powers[kind];if(!info)continue;
      ctx.save();ctx.translate(x,y);ctx.fillStyle='#20112fee';ctx.strokeStyle=info.color;ctx.lineWidth=2;
      ctx.beginPath();for(let i=0;i<6;i++){const a=i*TAU/6;const px=Math.cos(a)*21,py=Math.sin(a)*21;i?ctx.lineTo(px,py):ctx.moveTo(px,py);}ctx.closePath();ctx.fill();ctx.stroke();
      ctx.font='20px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=info.color;ctx.fillText(info.icon,0,1);
      ctx.font='bold 10px system-ui';ctx.fillText(info.name,0,34);ctx.restore();
    }
    for(const p of players){
      if(visible(p.x,p.y,130)||p.trail?.some(([x,y])=>visible(x,y)))
        renderer.snake(ctx,p,{focus:p.id===focusId,leader:p.id===state.leaderId,t});
    }
    ctx.restore();
    const grad=ctx.createRadialGradient(w/2,h/2,0,w/2,h/2,Math.max(w,h)*.75);
    grad.addColorStop(0,'rgba(8,5,15,0)');grad.addColorStop(1,'rgba(8,5,15,.37)');
    ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);
    return camera;
  };
  renderer.colors=palette;
  renderer.clock=(milliseconds)=>{
    const s=Math.max(0,Math.ceil(milliseconds/1000));
    return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;
  };
  renderer.text=(tag,cls,content)=>{const n=document.createElement(tag);if(cls)n.className=cls;n.textContent=String(content);return n;};
  window.CyberRender=renderer;
})();
