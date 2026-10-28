"""Capacidade, mensagens inválidas, autenticação e retomada pelo protocolo real."""
import asyncio,json,sys
from pathlib import Path
from aiohttp import web,ClientSession,WSMsgType,WSServerHandshakeError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import game,create_app,HOST_KEY,SKINS
async def recv(ws,kind):
    async def loop():
        async for m in ws:
            if m.type==WSMsgType.TEXT:
                d=json.loads(m.data)
                if d['type']==kind:return d
        raise AssertionError('disconnected')
    return await asyncio.wait_for(loop(),5)
async def main():
    runner=web.AppRunner(create_app());await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    url=f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    clients=[]
    try:
        async with ClientSession() as session:
            ws=await session.ws_connect(url+'/ws');clients.append(ws);await recv(ws,'state')
            for data in ['null','[]','42','not json']:
                await ws.send_str(data)
            await ws.send_json(dict(type='host:auth',key='ç-invalid'))
            assert not (await recv(ws,'host:auth:ack'))['ok']
            await ws.send_json(dict(type='host:start'));await asyncio.sleep(.1);assert game.phase=='LOBBY'
            await ws.send_json(dict(type='player:join',name='<Aluno>',skin='galaxy'));ack=await recv(ws,'join:ack');assert ack['ok'] and '<' not in ack['name']
            assert ack['skin']=='galaxy'
            pid=ack['id'];token=ack['token'];game.players[pid].score=55
            await ws.close();await asyncio.sleep(.05)
            w=await session.ws_connect(url+'/ws');clients.append(w);await recv(w,'state')
            await w.send_json(dict(type='player:join',token=token,skin='neon'));res=await recv(w,'join:ack')
            assert res['skin']=='galaxy'
            assert res['id']==pid and game.players[pid].score==55 and len(game.players)==1
            print('PASS: malformed JSON, Unicode key, unauthorized commands, name sanitation, reconnect score')
            for i in range(39):
                w=await session.ws_connect(url+'/ws');clients.append(w);await recv(w,'state')
                await w.send_json(dict(type='player:join',name=f'P{i}',skin=SKINS[i%len(SKINS)] if i else 'invalid-skin'))
                ack=await recv(w,'join:ack');assert ack['ok']
                assert ack['skin']==(SKINS[i%len(SKINS)] if i else 'neon')
            w=await session.ws_connect(url+'/ws');clients.append(w);await recv(w,'state')
            await w.send_json(dict(type='player:join',name='Overflow'));assert not (await recv(w,'join:ack'))['ok']
            assert len(game.players)==40
            print('PASS: 40 accepted, 41st rejected; skins synchronized, invalid skin falls back to neon')
            try:await session.ws_connect(url+'/ws',headers={'Origin':'https://other.example'})
            except WSServerHandshakeError as e:assert e.status==403
            else:raise AssertionError('cross-origin accepted')
            async with session.get(url+'/api/qr?url=javascript:alert(1)') as res:assert res.status==400
            print('PASS: foreign WebSocket Origin and invalid QR URL rejected')
            for w in clients:await w.close()
    finally:await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
