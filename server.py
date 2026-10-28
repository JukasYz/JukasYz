"""Cyber Snake Royale: servidor web + WebSocket + simulação autoritativa."""
import asyncio
import io
import json
import math
import os
import random
import secrets
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path

from aiohttp import WSMsgType, web
import qrcode
from qrcode.image.svg import SvgPathImage

ROOT = Path(__file__).resolve().parent
PORT = int(os.getenv('PORT', '3000'))
PUBLIC_URL = os.getenv('PUBLIC_URL', '').rstrip('/')
HOST_KEY = os.getenv('HOST_KEY') or secrets.token_urlsafe(18)
WIDTH, HEIGHT = 3600, 2400
MAX_PLAYERS = 40
FOOD_TARGET, FOOD_MAX = 165, 230
COLORS = ['#B96CFF', '#53E6D1', '#F7CB65', '#FD77B6', '#6BB9FF', '#B8EF73', '#FF946F', '#F3F0FF']
DURATIONS = {60, 90, 120, 180, 240}
SKINS = ('neon', 'circuit', 'striped', 'pixel', 'galaxy')
POWER_DURATIONS = {'magnet': 8000, 'shield': 6000, 'turbo': 6000}
POWER_NAMES = {'magnet': 'Ímã', 'shield': 'Escudo', 'turbo': 'Turbo'}
POWER_MAX = 6


def now_ms():
    return int(time.time() * 1000)


def clamp(v, lo, hi):
    return min(hi, max(lo, v))


def dist2(x, y, a, b):
    return (x-a)**2+(y-b)**2


def clean_name(raw):
    return ''.join(c for c in str(raw or 'Jogador') if c.isprintable() and c not in '<>')[:18].strip() or 'Jogador'


@dataclass
class Player:
    id: str
    name: str
    color: str
    ws: web.WebSocketResponse
    x: float = WIDTH / 2
    y: float = HEIGHT / 2
    angle: float = 0
    target: float = 0
    trail: list = field(default_factory=list)
    score: int = 0
    kills: int = 0
    deaths: int = 0
    alive: bool = False
    respawn_at: int = 0
    shield_until: int = 0
    boost: bool = False
    boost_energy: float = 100
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    disconnected_at: int = 0
    input_at: int = 0
    skin: str = 'neon'
    effects: dict = field(default_factory=dict)


class Game:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.connections: set[web.WebSocketResponse] = set()
        self.hosts: set[web.WebSocketResponse] = set()
        self.food: dict[int, list] = {}
        self.food_id = 0
        self.powerups = {}
        self.power_id = 0
        self.next_power_at = 0
        self.phase = 'LOBBY'
        self.countdown_at = 0
        self.finish_at = 0
        self.duration_ms = 180000
        self.paused_at = 0
        self.round = 0
        self.events = []
        self.writers = {}
        self.metrics = {"ticks": 0, "maxTickMs": 0, "snapshots": 0}
        self.reset_food()

    def reset_powerups(self):
        self.powerups.clear()
        for kind in list(POWER_DURATIONS) * 2:
            self.add_powerup(kind)
        self.next_power_at = 0

    def add_powerup(self, kind=None):
        if len(self.powerups) >= POWER_MAX:
            return
        self.power_id += 1
        self.powerups[self.power_id] = [self.power_id, round(random.uniform(90, WIDTH-90)),
            round(random.uniform(90, HEIGHT-90)), kind or random.choice(list(POWER_DURATIONS))]

    def leader_id(self):
        top = self.roster()
        return top[0].id if top and top[0].score > 0 else None

    def protected(self, p, now):
        return now < max(p.shield_until, p.effects.get('shield', 0))

    def reset_food(self):
        self.food.clear()
        for _ in range(FOOD_TARGET):
            self.add_food()

    def add_food(self, x=None, y=None):
        if len(self.food) >= FOOD_MAX:
            return
        self.food_id += 1
        pick = random.random()
        kind = 2 if pick < 0.13 else 1 if pick < 0.40 else 0
        self.food[self.food_id] = [self.food_id, round(x if x is not None else random.uniform(30, WIDTH-30)), round(y if y is not None else random.uniform(30, HEIGHT-30)), kind]

    def roster(self):
        return sorted(self.players.values(), key=lambda p: (-p.score, -p.kills, p.name.casefold()))

    def leaderboard(self):
        return [dict(rank=i+1,id=p.id,name=p.name,color=p.color,score=p.score,kills=p.kills,alive=p.alive)
                for i,p in enumerate(self.roster())]

    def spawn(self, p):
        x, y = WIDTH / 2, HEIGHT / 2
        for _ in range(100):
            x, y = random.uniform(120,WIDTH-120), random.uniform(120,HEIGHT-120)
            if all(not q.alive or q.id == p.id or dist2(x,y,q.x,q.y) > 250**2 for q in self.players.values()):
                break
        p.x,p.y=x,y
        p.angle = random.uniform(-math.pi, math.pi)
        p.target = p.angle
        p.trail = [[x,y]]
        p.boost = False
        p.boost_energy = 100
        p.alive=True
        p.respawn_at=0
        p.shield_until=(self.paused_at if self.phase=='PAUSED' else now_ms())+3200
        p.input_at=now_ms()
        p.effects.clear()

    def reset_p(self,p):
        p.score=p.kills=p.deaths=0
        p.trail=[]
        p.alive=False
        p.respawn_at=0
        p.boost_energy=100
        p.boost=False
        p.effects.clear()

    def announce(self,message):
        entry={'message':message,'at':now_ms()}
        self.events.insert(0,entry)
        self.events=self.events[:7]
        asyncio.create_task(self.broadcast({'type':'feed','entry':entry}))

    async def send(self,ws,payload):
        if not ws.closed:
            try:
                await ws.send_str(json.dumps(payload,ensure_ascii=False,separators=(',',':')))
            except (ConnectionError, RuntimeError):
                pass

    async def writer(self, ws, queue):
        try:
            while True:
                msg = await queue.get()
                await asyncio.wait_for(ws.send_str(msg), timeout=2)
        except (ConnectionError, RuntimeError, asyncio.TimeoutError):
            await ws.close()

    async def broadcast(self,payload):
        msg=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
        for ws, (queue, task) in list(self.writers.items()):
            if ws.closed or task.done():
                continue
            # Bound pending frames. Slow clients cannot stall simulation.
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(msg)

    def kill(self,p,opponent=None):
        if not p.alive:
            return
        bounty = 5 if self.leader_id() == p.id else 0
        p.alive=False
        p.deaths+=1
        p.boost=False
        p.effects.clear()
        p.respawn_at=now_ms()+2800
        if opponent is not None and opponent != p:
            opponent.kills += 1
            opponent.score += 10 + bounty
            self.announce(f'{opponent.name} eliminou {p.name} (+{10+bounty})' + (' — líder derrubado!' if bounty else ''))
        else:
            self.announce(f'{p.name} foi eliminado')
        n=min(8,len(p.trail))
        for i in range(n):
            bx,by=p.trail[int(i*len(p.trail)/n)]
            self.add_food(clamp(bx+random.randint(-18,18),25,WIDTH-25),clamp(by+random.randint(-18,18),25,HEIGHT-25))

    def start(self,duration):
        if self.phase not in ('LOBBY','RESULTS'):
            return False,'A rodada já está em andamento.'
        if not any(not p.disconnected_at for p in self.players.values()):
            return False,'Aguarde ao menos um jogador entrar pelo QR Code.'
        self.round+=1
        self.duration_ms=(int(duration) if str(duration).isdigit() and int(duration) in DURATIONS else 180)*1000
        self.phase='COUNTDOWN'
        self.countdown_at=now_ms()+5000
        self.finish_at=0
        self.reset_food()
        self.reset_powerups()
        for p in self.players.values():
            self.reset_p(p)
            self.spawn(p)
        self.announce(f'Rodada {self.round}: preparem-se!')
        return True,''

    def toggle_pause(self):
        if self.phase=='RUNNING':
            self.phase='PAUSED'
            self.paused_at=now_ms()
            self.announce('Partida pausada pelo apresentador')
        elif self.phase=='PAUSED':
            delta=now_ms()-self.paused_at
            self.finish_at+=delta
            for p in self.players.values():
                p.respawn_at+=delta
                p.shield_until+=delta
                p.effects = {kind: until+delta for kind, until in p.effects.items()}
            if self.next_power_at:self.next_power_at+=delta
            self.phase='RUNNING'
            self.announce('Partida retomada!')
        return self.phase

    def lobby(self):
        self.phase='LOBBY'
        self.countdown_at=self.finish_at=0
        for p in self.players.values():self.reset_p(p)
        self.reset_food()
        self.powerups.clear()
        self.next_power_at=0
        self.announce('Aguardando próxima rodada')

    def tick(self, dt,now):
        for pid,p in list(self.players.items()):
            if p.disconnected_at and now-p.disconnected_at>30000:
                self.players.pop(pid,None)
        if self.phase == 'COUNTDOWN' and now >=self.countdown_at:
            self.phase='RUNNING'
            self.finish_at=now+self.duration_ms
            for p in self.players.values():
                if p.alive:p.shield_until=now+3200
            self.announce('GO! Colete os dados e sobreviva!')
        if self.phase!='RUNNING':return
        if now>=self.finish_at:
            self.phase='RESULTS'
            winner=self.roster()[0] if self.players else None
            self.announce(f'Fim! {winner.name} venceu com {winner.score} pontos' if winner else 'Fim da partida!')
            return
        if now >= self.next_power_at:
            self.add_powerup()
            self.next_power_at = now + 8000
        for p in list(self.players.values()):
            if not p.alive:
                if now>=p.respawn_at:self.spawn(p)
                continue
            if now-p.input_at>700: p.boost=False
            p.effects = {kind: until for kind, until in p.effects.items() if until > now}
            turbo=p.effects.get('turbo', 0)>now
            boost=p.boost and (turbo or p.boost_energy > 1)
            p.boost_energy=100 if turbo else clamp(p.boost_energy+(-31 if boost else 19)*dt,0,100)
            turn=math.atan2(math.sin(p.target-p.angle),math.cos(p.target-p.angle))
            p.angle+=clamp(turn,-4.8*dt,4.8*dt)
            speed=220 if boost else 145
            p.x+=math.cos(p.angle)*speed*dt
            p.y+=math.sin(p.angle)*speed*dt
            if not p.trail or dist2(p.x,p.y,*p.trail[0])>7**2:
                p.trail.insert(0,[p.x,p.y])
            maxsegments=min(145,18+p.score//4)
            if len(p.trail)>maxsegments:del p.trail[maxsegments:]
            if p.x<13 or p.x>WIDTH-13 or p.y<13 or p.y>HEIGHT-13:
                self.kill(p)
                continue
            for item in list(self.powerups.values()):
                _,x,y,kind=item
                if dist2(p.x,p.y,x,y)<28**2:
                    p.effects[kind]=now+POWER_DURATIONS[kind]
                    self.powerups.pop(item[0],None)
                    self.announce(f'{p.name} coletou {POWER_NAMES[kind]}!')
            collect_radius=115 if p.effects.get('magnet',0)>now else 20
            for item in list(self.food.values()):
                _,x,y,kind=item
                if dist2(p.x,p.y,x,y)<collect_radius**2:
                    p.score+=(10 if kind==2 else 5 if kind==1 else 2)
                    self.food.pop(item[0],None)
                    self.add_food()
        alive=[p for p in self.players.values() if p.alive and not self.protected(p,now)]
        head_hits=set()
        for i,p in enumerate(alive):
            for q in alive[i+1:]:
                if dist2(p.x,p.y,q.x,q.y)<22**2:
                    head_hits.update((p.id,q.id))
        for pid in head_hits:self.kill(self.players[pid])
        for p in list(self.players.values()):
            if not p.alive or self.protected(p,now):continue
            for other in list(self.players.values()):
                if not other.alive:continue
                for x,y in other.trail[14 if p.id==other.id else 3:]:
                    if dist2(p.x,p.y,x,y)<18**2:
                        self.kill(p,None if other==p else other)
                        break
                if not p.alive:break

    def snapshot(self):
        tick=now_ms()
        effective_now=self.paused_at if self.phase=='PAUSED' else tick
        return dict(type='state',phase=self.phase,serverNow=tick,countdownEndAt=self.countdown_at,
            roundEndAt=self.finish_at,roundDurationMs=self.duration_ms,round=self.round,
            width=WIDTH,height=HEIGHT,playerCount=sum(not p.disconnected_at for p in self.players.values()),
            pausedAt=self.paused_at,
            leaderId=self.leader_id(),
            powerups=list(self.powerups.values()),
            players=[dict(id=p.id,name=p.name,color=p.color,skin=p.skin,x=round(p.x),y=round(p.y),angle=p.angle,
                score=p.score,kills=p.kills,deaths=p.deaths,alive=p.alive,
                connected=not p.disconnected_at,shield=p.alive and self.protected(p,effective_now),boostEnergy=round(p.boost_energy),
                effects=[dict(kind=kind,remainingMs=until-effective_now) for kind,until in p.effects.items() if until>effective_now],
                respawnMs=max(0,p.respawn_at-(self.paused_at if self.phase=='PAUSED' else tick)) if not p.alive else 0,
                trail=[[round(x),round(y)] for x,y in p.trail]) for p in self.players.values()],
            food=list(self.food.values()),leaderboard=self.leaderboard())


game=Game()


def ips():
    found=[]
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80))
        ip=s.getsockname()[0]
        if ip!='127.0.0.1':found.append(ip)
        s.close()
    except OSError:pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip!='127.0.0.1' and not ip.startswith('169.254.') and ip not in found:found.append(ip)
    except OSError:pass
    return found


async def config(request):
    hostname=request.host
    proto=request.headers.get('X-Forwarded-Proto',request.scheme).split(',')[0]
    if PUBLIC_URL:
        urls=[PUBLIC_URL+'/']
    elif hostname.startswith(('localhost:', '127.0.0.1:')):
        urls=[f'http://{ip}:{PORT}/' for ip in ips()] or [f'{proto}://{hostname}/']
    else:
        urls=[f'{proto}://{hostname}/']
    return web.json_response(dict(name='Cyber Snake Royale',joinUrls=urls,maxPlayers=MAX_PLAYERS,skins=list(SKINS)))


async def qr(request):
    url=request.query.get('url','')
    if len(url)>260 or not url.startswith(('http://','https://')) or any(c.isspace() for c in url):
        return web.Response(status=400,text='URL inválida')
    img=qrcode.make(url, image_factory=SvgPathImage,box_size=9,border=4)
    stream=io.BytesIO()
    img.save(stream)
    return web.Response(body=stream.getvalue(),content_type='image/svg+xml',headers={'Cache-Control':'no-store'})


async def health(request):
    return web.json_response({'ok':True,'phase':game.phase,'players':sum(not p.disconnected_at for p in game.players.values()),'metrics':game.metrics})


async def ws_handler(request):
    if len(game.connections)>=100:
        raise web.HTTPServiceUnavailable(text='Limite de conexões atingido')
    origin=request.headers.get('Origin')
    if origin:
        from urllib.parse import urlsplit
        if urlsplit(origin).netloc!=request.host:
            raise web.HTTPForbidden(text='Origem não permitida')
    ws=web.WebSocketResponse(heartbeat=25,max_msg_size=4096,compress=True)
    await ws.prepare(request)
    client_id=secrets.token_hex(7)
    game.connections.add(ws)
    queue=asyncio.Queue(maxsize=3)
    task=asyncio.create_task(game.writer(ws,queue))
    game.writers[ws]=(queue,task)
    is_host=False
    window_start=time.monotonic()
    messages=0
    await game.send(ws,game.snapshot())
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:continue
            if time.monotonic()-window_start>=1:
                window_start=time.monotonic();messages=0
            messages+=1
            if messages>100:
                await ws.close(code=1008,message=b'too many messages');break
            try:
                data=json.loads(msg.data)
                action=data.get('type')
                if not isinstance(data,dict):continue
            except (json.JSONDecodeError,ValueError,AttributeError):continue
            if action=='ping':
                await game.send(ws,{'type':'pong','at':data.get('at')})
            elif action=='host:auth':
                if client_id in game.players:continue
                is_host=isinstance(data.get('key'),str) and secrets.compare_digest(data['key'].encode(),HOST_KEY.encode())
                if is_host:game.hosts.add(ws)
                await game.send(ws,{'type':'host:auth:ack','ok':is_host,'events':game.events})
            elif action=='player:join':
                if is_host:continue
                if client_id in game.players:
                    p=game.players[client_id]
                    await game.send(ws,{'type':'join:ack','ok':True,'id':client_id,'name':p.name,'color':p.color,'skin':p.skin,'token':p.token})
                    continue
                token=data.get('token')
                old=next((p for p in game.players.values() if isinstance(token,str) and secrets.compare_digest(p.token.encode(),token.encode())),None)
                if old:
                    previous_ws=old.ws
                    client_id=old.id
                    old.ws=ws;old.disconnected_at=0
                    if not previous_ws.closed:await previous_ws.close()
                    await game.send(ws,{'type':'join:ack','ok':True,'id':old.id,'name':old.name,'color':old.color,'skin':old.skin,'token':old.token})
                    continue
                if len(game.players)>=MAX_PLAYERS:
                    await game.send(ws,{'type':'join:ack','ok':False,'error':'Sala cheia (40 pessoas).'});continue
                color=data.get('color')
                skin=data.get('skin')
                p=Player(id=client_id,name=clean_name(data.get('name')),color=color if color in COLORS else random.choice(COLORS),ws=ws,skin=skin if skin in SKINS else 'neon')
                game.players[client_id]=p
                if game.phase in ('COUNTDOWN','RUNNING','PAUSED'):
                    game.spawn(p)
                game.announce(f'{p.name} entrou na arena')
                await game.send(ws,{'type':'join:ack','ok':True,'id':client_id,'name':p.name,'color':p.color,'skin':p.skin,'token':p.token})
            elif action=='player:input':
                p=game.players.get(client_id)
                if p and p.alive and game.phase=='RUNNING':
                    p.input_at=now_ms()
                    angle=data.get('angle')
                    if type(angle) in (int,float) and -1000<=angle<=1000 and math.isfinite(angle):p.target=clamp(angle,-1000,1000)
                    p.boost=data.get('boost') is True
            elif is_host and action=='host:start':
                ok,error=game.start(data.get('duration',180))
                await game.send(ws,{'type':'host:ack','action':'start','ok':ok,'error':error})
            elif is_host and action=='host:pause':
                phase=game.toggle_pause()
                await game.send(ws,{'type':'host:ack','action':'pause','ok':True,'phase':phase})
            elif is_host and action=='host:lobby':
                game.lobby()
                await game.send(ws,{'type':'host:ack','action':'lobby','ok':True})
            elif is_host and action=='host:kick':
                pid=str(data.get('id') or '')
                p=game.players.get(pid)
                if p:
                    await game.send(p.ws,{'type':'kicked'})
                    game.players.pop(pid,None)
                    await p.ws.close(message=b'removed by host')
    finally:
        game.connections.discard(ws)
        game.hosts.discard(ws)
        game.writers.pop(ws,None)
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        p=game.players.get(client_id)
        if p and p.ws is ws:
            p.disconnected_at=now_ms();p.boost=False
            game.announce(f'{p.name} desconectou (30s para voltar)')
    return ws


async def homepage(request):
    return web.FileResponse(ROOT/'public'/'index.html')


async def on_startup(app):
    async def loop():
        previous=time.monotonic()
        next_snapshot=previous
        next_tick=previous
        while True:
            current=time.monotonic()
            tick_start=time.perf_counter()
            game.tick(clamp(current-previous,0,0.1),now_ms())
            game.metrics['ticks']+=1
            game.metrics['maxTickMs']=round(max(game.metrics['maxTickMs'],(time.perf_counter()-tick_start)*1000),3)
            previous=current
            if current>=next_snapshot:
                await game.broadcast(game.snapshot())
                game.metrics['snapshots']+=1
                next_snapshot=max(next_snapshot+1/12,time.monotonic())
            next_tick=max(next_tick+1/30,time.monotonic())
            await asyncio.sleep(max(0,next_tick-time.monotonic()))
    app['loop_task']=asyncio.create_task(loop())


async def on_cleanup(app):
    app['loop_task'].cancel()
    try:await app['loop_task']
    except asyncio.CancelledError:pass


@web.middleware
async def security_headers(request, handler):
    response=await handler(request)
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self' ws: wss:; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
    return response


def create_app():
    app=web.Application(client_max_size=4096,middlewares=[security_headers])
    app.router.add_get('/',homepage)
    app.router.add_get('/api/config',config)
    app.router.add_get('/api/qr',qr)
    app.router.add_get('/health',health)
    app.router.add_get('/ws',ws_handler)
    app.router.add_static('/',ROOT/'public',show_index=False)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__=='__main__':
    print('\n'+'='*58)
    print('  CYBER SNAKE ROYALE - INICIANDO SERVIDOR')
    print('='*58)
    print(f'\n PAINEL DO APRESENTADOR (NÃO COMPARTILHAR):\n http://localhost:{PORT}/host.html?key={HOST_KEY}')
    for ip in ips():print(f'\n JOGADORES NA MESMA REDE WI-FI:\n http://{ip}:{PORT}/')
    if not ips():print('\n Conecte-se a uma rede Wi-Fi para encontrar o endereço dos celulares.')
    print('\n Pressione Ctrl+C para encerrar.\n')
    web.run_app(create_app(),host='0.0.0.0',port=PORT,print=lambda _: print('Servidor ouvindo na porta '+str(PORT),flush=True))
