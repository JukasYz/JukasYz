"""Regras determinísticas: não dependem de sorte, tela ou rede."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Game, Player, now_ms, WIDTH

class Rules(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.g=Game();self.g.phase='RUNNING';self.t=now_ms();self.g.finish_at=self.t+60000
    def player(self,id='p',**kw):
        p=Player(id,id,'#B96CFF',None,x=500,y=500,alive=True,**kw)
        p.trail=[[500,500]];self.g.players[id]=p
        return p
    async def test_move_turn_and_boost(self):
        p=self.player();p.input_at=self.t;p.boost=True
        self.g.tick(.1,self.t)
        self.assertAlmostEqual(p.x,522);self.assertLess(p.boost_energy,100)
        p.target=1.57;self.g.tick(.1,self.t+100);self.assertGreater(p.y,500)
    async def test_food_score_and_growth(self):
        p=self.player();self.g.food={1:[1,500,500,2]};self.g.tick(0,self.t)
        self.assertEqual(p.score,10);self.assertNotIn(1,self.g.food)
        p.score=400;p.trail=[[500-i*8,500] for i in range(140)]
        self.g.tick(0,self.t);self.assertEqual(len(p.trail),118)
    async def test_wall_and_respawn(self):
        p=self.player();p.x=WIDTH-14;self.g.tick(.1,self.t)
        self.assertFalse(p.alive);self.assertEqual(p.deaths,1)
        self.g.tick(0,p.respawn_at+1);self.assertTrue(p.alive);self.assertGreater(p.shield_until,self.t)
    async def test_body_collision_awards_kill(self):
        p=self.player();q=self.player('q');q.x=900
        q.trail=[[900,500],[800,500],[700,500],[600,500],[500,500]]
        self.g.tick(0,self.t);self.assertFalse(p.alive);self.assertEqual(q.kills,1);self.assertEqual(q.score,10)
    async def test_head_on_eliminates_both(self):
        p=self.player();q=self.player('q');q.x=510
        self.g.tick(0,self.t);self.assertFalse(p.alive);self.assertFalse(q.alive)
    async def test_shield_blocks_body_collision(self):
        p=self.player(shield_until=self.t+1000);q=self.player('q');q.x=900
        q.trail=[[900,500]]*3+[[500,500]]
        self.g.tick(0,self.t);self.assertTrue(p.alive)
    async def test_self_collision(self):
        p=self.player();p.trail=[[100+i*8,500] for i in range(15)]+[[500,500]]
        self.g.tick(0,self.t);self.assertFalse(p.alive)
    async def test_pause_freezes_and_restores_timers(self):
        p=self.player();p.shield_until=self.t+2000
        with patch('server.now_ms',return_value=self.t):self.g.toggle_pause()
        before=self.g.finish_at;self.g.tick(1,self.t+1000);self.assertEqual(p.x,500)
        self.assertEqual(self.g.snapshot()['pausedAt'],self.t)
        with patch('server.now_ms',return_value=self.t+3000):self.g.toggle_pause()
        self.assertEqual(self.g.finish_at,before+3000);self.assertEqual(p.shield_until,self.t+5000)
    async def test_ranking_and_results(self):
        a=self.player('a');b=self.player('b');a.score=b.score=20;b.kills=1
        self.assertEqual(self.g.leaderboard()[0]['id'],'b')
        self.g.tick(0,self.g.finish_at);self.assertEqual(self.g.phase,'RESULTS')
    async def test_disconnect_grace_expires(self):
        p=self.player();p.disconnected_at=self.t-31000
        self.g.tick(0,self.t);self.assertFalse(self.g.players)
    async def test_input_timeout_releases_boost(self):
        p=self.player();p.boost=True;p.input_at=self.t-1000
        self.g.tick(.1,self.t);self.assertFalse(p.boost)
    async def test_countdown_starts_with_shield(self):
        p=self.player();self.g.phase='COUNTDOWN';self.g.countdown_at=self.t
        self.g.tick(0,self.t);self.assertEqual(p.shield_until,self.t+3200)
    async def test_start_guard_and_reset(self):
        p=self.player();self.assertFalse(self.g.start(60)[0])
        self.g.lobby();self.assertTrue(self.g.start(60)[0]);self.assertEqual(p.score,0)

if __name__=='__main__':unittest.main(verbosity=2)
