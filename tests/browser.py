"""Teste real de DOM/canvas e controles em Chromium com celular emulado."""
import asyncio,json,sys,os,shutil,io
import zxingcpp
from PIL import Image
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import create_app,game,HOST_KEY,now_ms,SKINS
ROOT=Path(__file__).resolve().parents[1]
async def main():
    runner=web.AppRunner(create_app());await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    url=f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    errors=[];checks=[]
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(executable_path=os.getenv('BROWSER_EXECUTABLE') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
            desktop=await browser.new_context(viewport={'width':1440,'height':1000})
            host=await desktop.new_page();host.on('pageerror',lambda e:errors.append(str(e)))
            await host.goto(url+'/host.html?key='+HOST_KEY)
            await host.wait_for_function("document.querySelector('#hostStatus').textContent==='Servidor online'")
            await host.wait_for_function("document.querySelector('#qrImage').naturalWidth>0")
            qr=await host.locator('#qrImage').screenshot()
            decoded=zxingcpp.read_barcode(Image.open(io.BytesIO(qr)))
            assert decoded and decoded.text==await host.locator('#joinUrl').input_value()
            assert 'key=' not in decoded.text
            assert '?key=' not in host.url
            checks.append('host authentication, displayed QR decoded to player URL without key, secret removed from URL')
            mobile=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
            page=await mobile.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto(url)
            await page.locator('#nameInput').fill('Aluno Mobile')
            assert await page.locator('#skins button').count()==5
            previews=[]
            for skin in SKINS:
                await page.locator(f'[data-skin="{skin}"]').click()
                assert await page.locator(f'[data-skin="{skin}"]').get_attribute('aria-pressed')=='true'
                previews.append(await page.locator('#skinPreview').evaluate('c=>c.toDataURL()'))
            assert len(set(previews))==5
            await page.locator('[data-skin="circuit"]').click()
            await page.locator('[aria-label="Cor #53E6D1"]').click()
            assert 'Rede Cidadã' in await page.locator('.citizen-tribute').inner_text()
            for width,height in [(360,640),(390,844)]:
                await page.set_viewport_size({'width':width,'height':height})
                for selector in ['#skins','#joinButton']:
                    await page.locator(selector).scroll_into_view_if_needed()
                    assert await page.locator(selector).is_visible()
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await page.locator('#skins').scroll_into_view_if_needed()
            (ROOT/'artifacts').mkdir(exist_ok=True)
            await page.screenshot(path=str(ROOT/'artifacts/customization.png'))
            checks.append('five distinct skin previews, color and skin selection, Rede Cidadã tribute and scrollable mobile join')
            await page.locator('#joinButton').click()
            await page.locator('#waitCard').wait_for(state='visible')
            await host.locator('#startButton').click()
            await page.locator('#countdownCard').wait_for(state='visible')
            await page.locator('#virtualPad').wait_for(state='visible',timeout=10000)
            p=next(iter(game.players.values()));pid=p.id
            assert p.skin=='circuit' and p.color=='#53E6D1'
            # Chromium touch input: two real touch points (joystick + boost).
            cdp=await mobile.new_cdp_session(page)
            box=await page.locator('.pad-base').bounding_box()
            touch={'id':1,'x':box['x']+box['width']/2,'y':box['y']+box['height']/2}
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[touch]})
            touch['y']=box['y']+4
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[touch]})
            await asyncio.sleep(.2);assert p.target < -1
            box=await page.locator('#boostButton').bounding_box()
            boost_touch={'id':2,'x':box['x']+box['width']/2,'y':box['y']+box['height']/2}
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[touch,boost_touch]})
            await asyncio.sleep(.2);assert p.boost
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            await asyncio.sleep(.15);assert not p.boost
            checks.append('mobile join, countdown, joystick changes server target, boost on/off')
            for kind,label in [('magnet','Ímã'),('shield','Escudo'),('turbo','Turbo')]:
                game.powerups={1:[1,p.x,p.y,kind]}
                await page.wait_for_function('(label)=>document.querySelector("#activePowers").textContent.includes(label)',arg=label)
            assert all(k in p.effects for k in ['magnet','shield','turbo'])
            checks.append('three server-authoritative pickups displayed with countdowns on mobile')
            await host.locator('#pauseButton').click()
            await page.locator('#pauseOverlay').wait_for(state='visible')
            first=await page.locator('#matchClock').inner_text()
            powers_text=await page.locator('#activePowers').inner_text();await asyncio.sleep(1.2)
            assert await page.locator('#matchClock').inner_text()==first
            assert await page.locator('#activePowers').inner_text()==powers_text
            (ROOT/'artifacts').mkdir(exist_ok=True)
            await page.screenshot(path=str(ROOT/'artifacts/mobile-paused.png'))
            checks.append('pause overlay and frozen clock')
            # Reload restores token and score, including disconnect lifecycle.
            p.score=77
            await page.reload();await page.locator('#pauseOverlay').wait_for(state='visible')
            await page.wait_for_function("document.querySelector('#myScore').textContent==='77'")
            assert len(game.players)==1 and pid in game.players
            assert game.players[pid].skin=='circuit' and game.players[pid].effects
            await page.wait_for_function('document.querySelector("#leaderRows").textContent.includes("👑")')
            await host.wait_for_function('document.querySelector("#hostLeaderboard").textContent.includes("👑")')
            checks.append('leader marked on both rankings and skin/powers retained on reload')
            await mobile.set_offline(True);await asyncio.sleep(.3);await mobile.set_offline(False)
            await page.wait_for_function("document.querySelector('#statusText').textContent==='Online'")
            assert pid in game.players and game.players[pid].score==77
            checks.append('reload and network reconnect preserve identity and score')
            await host.locator('#pauseButton').click();await page.locator('#pauseOverlay').wait_for(state='hidden')
            await page.screenshot(path=str(ROOT/'artifacts/mobile-playing.png'))
            await host.screenshot(path=str(ROOT/'artifacts/presenter.png'))
            for width,height in [(360,640),(844,390),(390,844)]:
                await page.set_viewport_size({'width':width,'height':height})
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                for sel in ['#virtualPad','#boostButton']:
                    box=await page.locator(sel).bounding_box();assert box and box['x']>=0 and box['y']>=0 and box['x']+box['width']<=width+1 and box['y']+box['height']<=height+1
            checks.append('controls fit 360x640, 844x390 and 390x844')
            # Exercise result transition using authoritative test clock.
            final_score=game.players[pid].score
            game.finish_at=now_ms()-1
            await page.locator('#resultsCard').wait_for(state='visible')
            assert f'{final_score} pontos' in await page.locator('#myResult').inner_text()
            await host.locator('#startButton').click()
            await page.locator('#countdownCard').wait_for(state='visible')
            assert game.players[pid].score==0
            checks.append('results show score and next round resets points')
            assert not errors,errors
            await browser.close()
            print(json.dumps(dict(checks=checks,pageErrors=errors),ensure_ascii=False,indent=2))
            (ROOT/'artifacts/browser.json').write_text(json.dumps(dict(checks=checks,pageErrors=errors),ensure_ascii=False,indent=2))
    finally:await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
