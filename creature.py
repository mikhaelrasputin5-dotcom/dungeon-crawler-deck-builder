import random
from typing import TYPE_CHECKING
from interactible import Interactible
from skill import Skill
from skillslot import Skillslot
from effect import Effect
from status import Status

if TYPE_CHECKING:
    from game import Game
    from context import Context

class Creature(Interactible):
    def __init__(self, nm, desc, hp, sr, res, slots, deck, max_pts=-1, pos=(0, 0)):
        self.name = nm
        self.description = desc
        self.HP = hp
        self.max_HP = hp
        self.SR = sr
        self.max_SR = sr
        self.resist = res
        self.slots = slots
        self.deck = deck
        self.hand = []
        self.disc = []
        self.pts = 0
        self.max_pts = max_pts
        self.stag_turns = 0
        self.pos = pos
        self.fx = []
        self.stat = {}
        self.pend_stat = []
        self.shield = 0
        self.layout = None

    def apply_stat(self, s, pot=0, cnt=0):
        k = getattr(s, 'id', s.name)
        if k not in self.stat:
            self.stat[k] = s.copy()
            self.stat[k].potency = pot or s.potency
            self.stat[k].count = cnt or s.count
        else:
            self.stat[k].potency += pot
            self.stat[k].count += cnt
    
    def add_stat(self, s, pot=0, cnt=0):
        if isinstance(s, str):
            if self.layout and s in self.layout.statuses:
                s = self.layout.statuses[s]
            else:
                s = Status(s, s, '')
        self.apply_stat(s, pot, cnt)
        if self.layout:
            lbl = f'+{s.name}'
            if cnt:
                lbl += f' x{cnt}'
            self.layout.add_stat_num(self, lbl)
    
    def get_stat(self, nm):
        s = self.stat.get(nm)
        if s:
            return s
        for s in self.stat.values():
            if s.name == nm:
                return s
        return None
    
    def get_stat_cnt(self, nm):
        s = self.get_stat(nm)
        return s.count if s else 0
    
    def sched_stat(self, s, pot=0, cnt=0, del_=1):
        if isinstance(s, Status):
            s = s.id
        self.pend_stat.append({'status': s, 'potency': pot, 'count': cnt, 'delay': del_})
    
    def apply_pend_stat(self):
        rem = []
        for p in self.pend_stat:
            p['delay'] -= 1
            if p['delay'] <= 0:
                s = p['status']
                if isinstance(s, str) and self.layout:
                    s = self.layout.statuses.get(s)
                if isinstance(s, str):
                    s = Status(s, s, '')
                self.add_stat(s, p['potency'], p['count'])
            else:
                rem.append(p)
        self.pend_stat = rem

    def decay_stat(self):
        for nm in list(self.stat.keys()):
            if self.stat[nm].decay():
                del self.stat[nm]

    def take_dmg(self, dmg, dt, ctx=None):
        prev_hp = int(self.HP)
        adj = int(dmg * (1 - self.resist.get(dt + '_HP', 0)))
        if self.shield > 0 and adj > 0:
            blk = min(self.shield, adj)
            self.shield -= blk
            adj -= blk
            if adj <= 0:
                if ctx:
                    ctx.dmg = 0
                    ctx.hp_l = 0
                    ctx.hp_pl = 0
                return
        self.HP -= adj
        if adj > 0 and self.layout:
            self.layout.add_dmg_num(self, adj)
            self.layout.add_atk_anim(self, dt)
        if ctx:
            ctx.dmg = adj
            ctx.hp_l = prev_hp - self.HP
            ctx.hp_pl = (prev_hp - self.HP) * 100 / prev_hp if prev_hp > 0 else 0
            self.fx_proc('on_hit', ctx)
        if self.SR > 0:
            sr_d = int(adj * (1 - self.resist.get(dt + '_SR', 0)))
            self.SR = max(0, self.SR - sr_d)
            if self.is_stag() and ctx:
                self.fx_proc('on_stagger', ctx)
                if self.layout:
                    self.layout.handle_stag(self, ctx)
        if self.HP <= 0 and self.layout and ctx:
            self.layout.handle_death(self, ctx)

    def heal(self, amt):
        if self.HP > 0:
            self.HP = min(self.max_HP, self.HP + amt)

    def is_alive(self):
        return self.HP > 0

    def is_stag(self):
        return self.SR <= 0

    def take_turn(self):
        self.autopilot()
    
    def autopilot(self):
        if not self.hand:
            return
        aff = [s for s in self.hand if self.pts >= s.cost] if self.max_pts > 0 else list(self.hand)
        if not aff:
            return
        sk = random.choice(aff)
        if self.max_pts > 0:
            self.pts -= sk.cost
        if self.layout:
            tgt = None
            if self == self.layout.playerchar:
                tgt = next((e for e in self.layout.enemy_list if e.is_alive()), None)
            else:
                tgt = self.layout.playerchar if self.layout.playerchar.is_alive() else None
            sl = Skillslot(speed_range=(0, 0))
            sl.owner = self
            sl.set_target_creature(tgt)
            sl.sk = sk
            sl.roll_spd()
            self.layout.add_slot(sl)

    def assignSlot(self, sl):
        if sl in self.slots:
            return False
        self.slots.append(sl)
        return True
    
    def draw_sk(self, n=1):
        if not self.deck and self.disc:
            self.refresh()
        for _ in range(n):
            if self.deck:
                self.hand.append(self.deck.pop(0))

    def discard(self, sk, ctx):
        if sk in self.hand:
            self.hand.remove(sk)
            self.disc.append(sk)
            self.fx_proc('on_discard', ctx)
    
    def refresh(self):
        if self.disc:
            self.deck.extend(self.disc)
            self.disc.clear()
            random.shuffle(self.deck)

    def get_fx(self):
        return self.fx.copy()
    
    def fx_proc(self, t, ctx):
        for e in self.fx:
            if e.trigger == t:
                e.execute(ctx)
        self.stat_fx_proc(t, ctx)
    
    def stat_fx_proc(self, t, ctx):
        for s in list(self.stat.values()):
            for e in s.effects:
                if e.trigger == t:
                    e.execute(ctx)
