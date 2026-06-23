from typing import TYPE_CHECKING
from die import Die
from effect import Effect

if TYPE_CHECKING:
    from creature import Creature
    from context import Context

class Skill:
    def __init__(self, nm, desc, cost, tgt_t, dice):
        self.name = nm
        self.description = desc
        self.cost = cost
        self.targeting_type = tgt_t
        self.dice = dice
        self.effects = []

    def clash(self, opp, ctx):
        self.fx_proc('on_play', ctx)
        self.fx_proc('on_clash_start', ctx)
        my_d = [d.copy() for d in self.dice]
        their_d = [d.copy() for d in opp.dice]
        orig_atk = ctx.atk
        orig_def = ctx.def_
        dmg_cnt = 0
        
        for i in range(min(len(my_d), len(their_d))):
            self.fx_proc('on_clash', ctx)
            md = my_d[i]
            td = their_d[i]
            
            ctx.die = md
            ctx.idx = i
            ctx.atk = orig_atk
            ctx.def_ = orig_def
            ctx.atk.fx_proc('on_die_roll', ctx)
            md.fx_proc('on_die_roll', ctx)
            
            ctx.die = td
            ctx.atk = orig_def
            ctx.def_ = orig_atk
            ctx.atk.fx_proc('on_die_roll', ctx)
            td.fx_proc('on_die_roll', ctx)
            
            ctx.atk = orig_atk
            ctx.def_ = orig_def
            my_r = md.roll(ctx)
            their_r = td.roll(ctx)
            ctx.ch.append((my_r, their_r))
            
            if my_r > their_r:
                ctx.dmg = my_r - their_r
                ctx.die = md
                md.fx_proc('on_win', ctx)
                ctx.die = td
                td.fx_proc('on_lose', ctx)
                tgt = ctx.get_opponent(ctx.atk)
                tgt.take_damage(ctx.dmg, md.type, ctx)
            elif their_r > my_r:
                ctx.dmg = their_r - my_r
                ctx.die = td
                td.fx_proc('on_win', ctx)
                ctx.die = md
                md.fx_proc('on_lose', ctx)
                tgt = ctx.get_opponent(ctx.def_)
                tgt.take_damage(ctx.dmg, td.type, ctx)
            ctx.dmg = 0
            dmg_cnt += 1
        return dmg_cnt

    def attack(self, ctx, start=0):
        self.fx_proc('on_play', ctx)
        self.fx_proc('on_unopposed_attack', ctx)
        for i, d in enumerate(self.dice):
            if i < start:
                continue
            ctx.die = d
            ctx.idx = i
            ctx.atk.fx_proc('on_die_roll', ctx)
            d.fx_proc('on_die_roll', ctx)
            ctx.dmg = d.roll(ctx)
            tgts = ctx.tgts or ([ctx.def_] if ctx.def_ else [])
            for t in tgts:
                if t and t.is_alive():
                    tc = ctx.with_target(t)
                    d.fx_proc('on_unopposed_hit', tc)
                    t.take_damage(ctx.dmg, d.type, tc)
            ctx.dmg = 0

    def fx_proc(self, t, ctx):
        for e in self.effects:
            if e.trigger == t:
                e.execute(ctx)
