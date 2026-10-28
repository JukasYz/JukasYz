"""Poderes e liderança: regras determinísticas e duração autoritativa."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Game,Player,WIDTH,POWER_MAX,now_ms

class Features(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.g=Game();self.t=now_ms();self.g.phase='RUNNING';self.g.finish_at=self.t+60000;self.g.next_power_at=self.t+8000
        self.g.food.clear()
        self.p=Player('p','Aluno','#B96CFF',None,x=500,y=500,alive=True,trail=[[500,500]],input_at=self.t,skin='circuit')
        self.g.players['p']=self.p
    def body(self):
        q=Player('q','Outro','#53E6D1',None,x=900,y=500,alive=True,trail=[[900,500]]*3+[[500,500]])
        self.g.players['q']=q;return q
    async def test_magnet_pickup_collects_far_food(self):
        self.g.powerups={1:[1,500,500,'magnet']};self.g.food={1:[1,580,500,0]}
        self.g.tick(0,self.t)
        self.assertEqual(self.p.score,2);self.assertEqual(self.p.effects['magnet'],self.t+8000)
        self.assertNotIn(1,self.g.powerups)
    async def test_magnet_expires(self):
        self.p.effects={'magnet':self.t-1};self.g.food={1:[1,580,500,0]}
        self.g.tick(0,self.t);self.assertEqual(self.p.score,0);self.assertFalse(self.p.effects)
    async def test_shield_blocks_body_then_expires(self):
        q=self.body();self.p.effects={'shield':self.t+10}
        self.g.tick(0,self.t);self.assertTrue(self.p.alive)
        self.g.tick(0,self.t+11);self.assertFalse(self.p.alive);self.assertEqual(q.score,10)
    async def test_shield_does_not_block_wall(self):
        self.p.x=WIDTH-14;self.p.effects={'shield':self.t+5000}
        self.g.tick(.1,self.t);self.assertFalse(self.p.alive)
    async def test_turbo_and_expiration(self):
        self.p.effects={'turbo':self.t+100};self.p.boost_energy=0;self.p.boost=True
        self.g.tick(.1,self.t);self.assertAlmostEqual(self.p.x,522);self.assertEqual(self.p.boost_energy,100)
        self.g.tick(.1,self.t+101);self.assertLess(self.p.boost_energy,100);self.assertNotIn('turbo',self.p.effects)
    async def test_pause_freezes_all_effects_and_pickup_timer(self):
        self.p.effects={'turbo':self.t+6000,'magnet':self.t+8000}
        with patch('server.now_ms',return_value=self.t):self.g.toggle_pause()
        with patch('server.now_ms',return_value=self.t+5000):
            s=self.g.snapshot();self.g.toggle_pause()
        self.assertEqual(s['players'][0]['effects'][0]['remainingMs'],6000)
        self.assertEqual(self.p.effects['turbo'],self.t+11000);self.assertEqual(self.g.next_power_at,self.t+13000)
    async def test_pickups_bounded_and_balanced(self):
        self.g.reset_powerups();self.assertEqual(len(self.g.powerups),POWER_MAX)
        self.assertEqual(sorted(p[3] for p in self.g.powerups.values()),['magnet']*2+['shield']*2+['turbo']*2)
        self.g.add_powerup();self.assertEqual(len(self.g.powerups),POWER_MAX)
    async def test_death_clears_powers_skin_preserved(self):
        self.p.effects={'shield':self.t+5000};self.g.kill(self.p);self.assertFalse(self.p.effects)
        self.g.spawn(self.p);self.assertEqual(self.p.skin,'circuit');self.assertFalse(self.p.effects)
    async def test_leader_bounty(self):
        q=self.body();self.p.score=100
        self.assertEqual(self.g.snapshot()['leaderId'],'p')
        self.g.tick(0,self.t);self.assertFalse(self.p.alive);self.assertEqual(q.score,15);self.assertEqual(q.kills,1)
    async def test_no_crown_at_zero_and_transfer(self):
        q=self.body();self.assertIsNone(self.g.leader_id())
        self.p.score=5;self.assertEqual(self.g.leader_id(),'p')
        q.score=10;self.assertEqual(self.g.leader_id(),'q')
    async def test_lobby_clears_powers(self):
        self.g.reset_powerups();self.p.effects={'magnet':self.t+8000};self.g.lobby()
        self.assertFalse(self.g.powerups);self.assertFalse(self.p.effects)
    async def test_repeated_pickup_refreshes_without_unbounded_stacking(self):
        self.p.effects={'magnet':self.t+7000};self.g.powerups={1:[1,500,500,'magnet']}
        self.g.tick(0,self.t);self.assertEqual(self.p.effects['magnet'],self.t+8000)

if __name__=='__main__':unittest.main(verbosity=2)
