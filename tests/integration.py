import asyncio
import json
import socket
import sys
from pathlib import Path
from aiohttp import ClientSession, WSMsgType, web

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import create_app,game,HOST_KEY

async def receive(ws, predicate, max_wait=4):
    async def get():
        while True:
            msg=await ws.receive()
            if msg.type == WSMsgType.TEXT:
                data=json.loads(msg.data)
                if predicate(data):return data
            elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):raise RuntimeError('WebSocket disconnect')
    return await asyncio.wait_for(get(),max_wait)

async def main():
    app=create_app()
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0)
    await site.start()
    port=site._server.sockets[0].getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    async with ClientSession() as session:
        res=await session.get(url+'/health')
        assert res.status==200 and (await res.json())['ok']
        res=await session.get(url+'/')
        assert res.status==200 and 'CYBER SNAKE' in await res.text()
        res=await session.get(url+'/api/qr',params={'url':url+'/'})
        assert res.status==200 and '<svg' in await res.text()
        host=await session.ws_connect(url+'/ws')
        await receive(host,lambda d:d['type']=='state')
        await host.send_json({'type':'host:auth','key':HOST_KEY})
        assert (await receive(host,lambda d:d['type']=='host:auth:ack'))['ok']
        players=[]
        for n in range(3):
            w=await session.ws_connect(url+'/ws')
            await receive(w,lambda d:d['type']=='state')
            await w.send_json({'type':'player:join','name':f'Jogador {n+1}','color':'#B96CFF'})
            ack=await receive(w,lambda d:d['type']=='join:ack')
            assert ack['ok']
            players.append((w,ack['id']))
        await host.send_json({'type':'host:start','duration':60})
        ack=await receive(host,lambda d:d.get('type')=='host:ack' and d.get('action')=='start')
        assert ack['ok']
        snap=await receive(host,lambda d:d.get('type')=='state' and d.get('phase')=='COUNTDOWN')
        assert snap['playerCount']==3 and len(snap['players'])==3
        print('✅ 3 jogadores simultâneos, QR Code e lobby')
        await asyncio.sleep(5.4)
        snapshot=await receive(host,lambda d:d.get('type')=='state' and d.get('phase')=='RUNNING')
        first=next(p for p in snapshot['players'] if p['id']==players[0][1]); initial_x=first['x']
        await players[0][0].send_json({'type':'player:input','angle':0,'boost':True})
        await asyncio.sleep(.55)
        moved=await receive(host,lambda d:d.get('type')=='state' and d.get('phase')=='RUNNING' and next(p for p in d['players'] if p['id']==players[0][1])['x']!=initial_x)
        print('✅ Rodada iniciou e as cobrinhas se movimentam')
        await host.send_json({'type':'host:pause'})
        await receive(host,lambda d:d.get('type')=='host:ack' and d.get('phase')=='PAUSED')
        paused=await receive(host,lambda d:d.get('type')=='state' and d.get('phase')=='PAUSED')
        await asyncio.sleep(.25)
        still=await receive(host,lambda d:d.get('type')=='state' and d.get('phase')=='PAUSED')
        assert paused['players'][0]['x']==still['players'][0]['x']
        await host.send_json({'type':'host:pause'})
        await receive(host,lambda d:d.get('type')=='host:ack' and d.get('phase')=='RUNNING')
        print('✅ Pausa e retomada funcionam')
        await host.send_json({'type':'host:kick','id':players[2][1]})
        await receive(players[2][0],lambda d:d.get('type')=='kicked')
        newstate=await receive(host,lambda d:d.get('type')=='state' and d.get('playerCount')==2)
        assert newstate['playerCount']==2
        print('✅ O apresentador consegue remover um participante')
        await host.send_json({'type':'host:lobby'})
        await receive(host,lambda d:d.get('type')=='host:ack' and d.get('action')=='lobby')
        lobby=await receive(host,lambda d:d.get('type')=='state' and d.get('phase')=='LOBBY')
        assert all(p['score']==0 for p in lobby['players'])
        print('✅ Lobby e reinício de pontuação funcionam')
        for w,_ in players:await w.close()
        await host.close()
    await runner.cleanup()
    print('\nTODOS OS TESTES PASSARAM')

asyncio.run(main())
