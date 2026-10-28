"""30 clientes reais WebSocket, 20 comandos/s cada, servidor em outro processo.
Executar: python tests/carga_30.py --seconds 65 (padrão: rodada inteira).
"""
import argparse,asyncio,json,math,os,socket,struct,subprocess,sys,time
from pathlib import Path
from aiohttp import ClientSession,WSMsgType
ROOT=Path(__file__).resolve().parents[1]

async def main(seconds):
    env=dict(os.environ,PORT='3107',HOST_KEY='load-test-local-only')
    proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    url='http://127.0.0.1:3107';tasks=[];clients=[];readers=[]
    stats=[dict(states=0,bytes=0,gaps=[],rtt=[],last=None,phases=set(),positions=set(),id=None,skin=None,powers=set()) for _ in range(30)]
    async with ClientSession(trust_env=False) as session:
        try:
            for _ in range(100):
                if proc.poll() is not None:raise RuntimeError(proc.stderr.read().decode())
                try:
                    async with session.get(url+'/health') as res:
                        if res.status==200:break
                except OSError:pass
                await asyncio.sleep(.1)
            else:raise RuntimeError('server startup timeout')
            async def receive(ws,kind):
                async for msg in ws:
                    if msg.type!=WSMsgType.TEXT:raise RuntimeError('connection closed')
                    d=json.loads(msg.data)
                    if d['type']==kind:return d
                raise RuntimeError('connection closed')
            async with session.get(url+'/api/config') as res:
                skins=(await res.json())['skins']
            async def join(i):
                ws=await session.ws_connect(url+'/ws',compress=15)
                await receive(ws,'state');await ws.send_json(dict(type='player:join',name=f'Aluno {i+1}',skin=skins[i%len(skins)]))
                ack=await receive(ws,'join:ack');assert ack['ok'];stats[i]['id']=ack['id'];stats[i]['skin']=ack['skin']
                return ws
            clients=list(await asyncio.gather(*(join(i) for i in range(30))))
            host=await session.ws_connect(url+'/ws');await receive(host,'state')
            await host.send_json(dict(type='host:auth',key=env['HOST_KEY']));assert (await receive(host,'host:auth:ack'))['ok']
            await host.send_json(dict(type='host:start',duration=60));assert (await receive(host,'host:ack'))['ok']
            def tcp_received(ws):
                # Linux tcp_info: verified tcpi_bytes_received offset in linux/tcp.h.
                if not sys.platform.startswith('linux'):return None
                sock=ws._writer.transport.get_extra_info('socket')
                return struct.unpack_from('=Q',sock.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,136),128)[0]
            baseline=[tcp_received(w) for w in clients]
            start=time.monotonic()
            async def read(i,ws):
                async for msg in ws:
                    if msg.type!=WSMsgType.TEXT:break
                    d=json.loads(msg.data);s=stats[i];s['bytes']+=len(msg.data.encode())
                    if d['type']=='pong':s['rtt'].append((time.monotonic()-d['at'])*1000)
                    if d['type']!='state':continue
                    t=time.monotonic();s['states']+=1;s['phases'].add(d['phase'])
                    assert d['playerCount']==30
                    assert len(d['leaderboard'])==30
                    top=d['leaderboard'][0]
                    assert d['leaderId']==(top['id'] if top['score']>0 else None)
                    assert len(d['powerups'])<=6
                    s['powers'].update(item[3] for item in d['powerups'])
                    assert set(p['skin'] for p in d['players'])==set(skins)
                    if s['last'] is not None:s['gaps'].append((t-s['last'])*1000)
                    s['last']=t
                    p=next(p for p in d['players'] if p['id']==s['id']);s['positions'].add((p['x'],p['y']))
                    assert p['skin']==s['skin']
                raise RuntimeError(f'Jogador {i} desconectou durante teste')
            async def control(i,ws):
                n=0
                while True:
                    angle=(time.monotonic()-start)*.8+i*.21
                    await ws.send_json(dict(type='player:input',angle=math.sin(angle)*math.pi,boost=n%80<20))
                    if n%20==0:await ws.send_json(dict(type='ping',at=time.monotonic()))
                    n+=1;await asyncio.sleep(.05)
            readers=[asyncio.create_task(read(i,w)) for i,w in enumerate(clients)]
            tasks=[asyncio.create_task(control(i,w)) for i,w in enumerate(clients)]
            # Drain presenter too; no unconsumed WebSocket buffers.
            async def drain():
                async for _ in host:pass
            tasks.append(asyncio.create_task(drain()))
            await asyncio.sleep(seconds)
            for task in readers:
                assert not task.done(),task.exception() if task.done() else ''
            async with session.get(url+'/health') as res:health=await res.json()
            assert health['players']==30
            assert all(s['states']>seconds*7 and len(s['positions'])>10 for s in stats)
            if seconds>=66:assert all('RESULTS' in s['phases'] for s in stats)
            gaps=[g for s in stats for g in s['gaps']];rtt=[g for s in stats for g in s['rtt']]
            percentile=lambda a,p:round(sorted(a)[int((len(a)-1)*p)],2)
            result=dict(players=30,seconds=seconds,inputHzPerPlayer=20,minStates=min(s['states'] for s in stats),
                skinsSynchronized=sorted({s['skin'] for s in stats}),powerKindsSeen=sorted(set().union(*(s['powers'] for s in stats))),
                stateGapMsP95=percentile(gaps,.95),stateGapMsMax=round(max(gaps),2),rttMsP50=percentile(rtt,.5),rttMsP95=percentile(rtt,.95),
                totalPayloadMB=round(sum(s['bytes'] for s in stats)/1e6,2),
                serverOutboundPayloadMbps=round(sum(s['bytes'] for s in stats)*8/seconds/1e6,2),health=health)
            if baseline[0] is not None:
                received=sum(tcp_received(w)-n for w,n in zip(clients,baseline))
                result['measuredTcpReceivedMB']=round(received/1e6,2)
                result['measuredTcpReceivedMbps']=round(received*8/seconds/1e6,2)
                result['note']='TCP bytes received by 30 clients; WebSocket compression on, no TLS, no IP/TCP headers; payload metrics above are before compression.'
            (ROOT/'artifacts').mkdir(exist_ok=True)
            (ROOT/'artifacts/load30.json').write_text(json.dumps(result,indent=2))
            print(json.dumps(result,indent=2))
        finally:
            for t in tasks+readers:t.cancel()
            await asyncio.gather(*tasks,*readers,return_exceptions=True)
            for w in clients:await w.close()
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            stderr=proc.stderr.read().decode()
            if stderr:print('SERVER STDERR:',stderr,file=sys.stderr)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=67)
    asyncio.run(main(p.parse_args().seconds))
