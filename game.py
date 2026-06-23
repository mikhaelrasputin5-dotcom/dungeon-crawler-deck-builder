from enum import Enum, auto
import random
from pathlib import Path
from typing import Optional
import pygame
from pygame import Vector2
from creature import Creature
from skillslot import Skillslot
from context import Context
from engine import Engine
from floor import Floor, RoomRect
from tile import HiddenTile
from config import GW, GH, TS, CBG

class GameState(Enum):
    INIT = auto()
    EXPLORING = auto()
    COMBAT = auto()
    LOOT = auto()
    GAME_OVER = auto()

class Game:
    def __init__(self, pc, w=GW, h=GH, seed=None, engine=None):
        self.pc = pc
        self.ene_lst = []
        self.res_ord = []
        self.eng = engine if engine else Engine()
        self.state = GameState.INIT
        self.seed = seed if seed else random.randrange(2**31)
        self.flr = Floor(w, h, seed=self.seed)
        self.cur_flr = 1
        self.pc.pos = self.flr.start
        self.pc.layout = self
        self.pc.pts = self.pc.max_pts if self.pc.max_pts > 0 else 0
        self.p_room = self.flr.get_room_at(*self.pc.pos)
        self.c_room = None
        self.stat = self.eng.load_all_st()
        self.res_q = []
        self.cur_res_ev = None
        self.res_act = False
        self.dmg_num = []
        self.stat_num = []
        self.atk_anim = []
        self.atk_anim_fr = {}
        self._load_atk_anim()
        try:
            self.pc.fx.append(self.eng.load_fx('restore_points'))
        except ValueError:
            pass
        self._apply_def_turn_end_fx(self.pc)
        self.set_state(GameState.EXPLORING)

    def add_dmg_num(self, c, a):
        if a <= 0:
            return
        ex = self._pop_ofs(c)
        x = c.pos[0] * TS + TS // 2 + ex[0]
        y = c.pos[1] * TS + ex[1]
        self.dmg_num.append({
            'tgt': c, 'txt': f'-{a}', 'x': x, 'y': y, 'vy': -40,
            'age': 0, 'dur': 900, 'col': (255, 80, 80),
        })

    def add_stat_num(self, c, txt):
        if not txt:
            return
        ex = self._pop_ofs(c)
        x = c.pos[0] * TS + TS // 2 + ex[0]
        y = c.pos[1] * TS + ex[1]
        self.stat_num.append({
            'tgt': c, 'txt': txt, 'x': x, 'y': y, 'vy': -40,
            'age': 0, 'dur': 900, 'col': (100, 220, 220),
        })

    def _pop_ofs(self, c):
        ex = [n for n in self.dmg_num + self.stat_num if n['tgt'] == c]
        oi = len(ex)
        xo = (oi % 2) * 12 - 6
        yo = oi * 16
        return (xo, yo)

    def _load_atk_anim(self):
        ad = Path(__file__).resolve().parent / 'animations'
        self.atk_anim_fr = {}
        for k in ('blunt', 'slash', 'pierce'):
            p = ad / f'basic_{k}.png'
            try:
                sh = pygame.image.load(str(p))
            except pygame.error:
                continue
            fh = sh.get_height()
            if fh <= 0:
                continue
            fc = max(1, sh.get_width() // fh)
            fw = sh.get_width() // fc
            fr = [sh.subsurface(pygame.Rect(i * fw, 0, fw, fh)).copy() for i in range(fc)]
            self.atk_anim_fr[k] = fr

    def add_atk_anim(self, c, dt):
        k = 'slash'
        dl = dt.lower()
        if 'blunt' in dl:
            k = 'blunt'
        elif 'slash' in dl:
            k = 'slash'
        elif 'pierce' in dl:
            k = 'pierce'
        fr = self.atk_anim_fr.get(k)
        if not fr:
            self._load_atk_anim()
            fr = self.atk_anim_fr.get(k)
        if not fr:
            return
        self.atk_anim.append({
            'tgt': c, 'fr': fr, 'age': 0, 'dur': 220, 'ofs': (0, -6),
        })

    def upd_dmg_num(self, dt):
        if not self.dmg_num and not self.stat_num:
            return
        rd = []
        for n in self.dmg_num:
            n['age'] += dt
            n['y'] += n['vy'] * (dt / 1000.0)
            if n['age'] < n['dur']:
                rd.append(n)
        self.dmg_num = rd
        rs = []
        for n in self.stat_num:
            n['age'] += dt
            n['y'] += n['vy'] * (dt / 1000.0)
            if n['age'] < n['dur']:
                rs.append(n)
        self.stat_num = rs

    def upd_atk_anim(self, dt):
        if not self.atk_anim:
            return
        rm = []
        for a in self.atk_anim:
            a['age'] += dt
            if a['age'] < a['dur']:
                rm.append(a)
        self.atk_anim = rm

    def draw_atk_anim(self, surf, ofs=(0, 0)):
        for a in self.atk_anim:
            prg = min(1.0, a['age'] / a['dur'])
            idx = min(len(a['fr']) - 1, int(prg * len(a['fr'])))
            fr = a['fr'][idx]
            x = a['tgt'].pos[0] * TS + TS // 2 + ofs[0] + a['ofs'][0]
            y = a['tgt'].pos[1] * TS + TS // 2 + ofs[1] + a['ofs'][1]
            r = fr.get_rect(center=(x, y))
            surf.blit(fr, r)

    def set_state(self, ns):
        self.state = ns

    def _apply_def_turn_end_fx(self, c):
        for fid in ['refresh_if_deck_empty', 'draw_if_empty_hand']:
            try:
                c.fx.append(self.eng.load_fx(fid))
            except ValueError:
                pass

    def create_flr(self, seed=None, scr=None):
        self.seed = seed if seed else random.randrange(2**31)
        self.flr = Floor(self.flr.w, self.flr.h, seed=self.seed)
        self.pc.pos = self.flr.start
        self.p_room = self.flr.get_room_at(*self.pc.pos)
        if scr:
            self._rend_flr(scr)

    def adv_flr(self, scr=None):
        self.cur_flr += 1
        self.create_flr(scr=scr)
        self.set_state(GameState.EXPLORING)

    def _rend_flr(self, sf):
        pygame.event.pump()
        sf.fill(CBG)
        self.draw_flr(sf)
        pygame.display.flip()

    def draw_flr(self, sf, ofs=(0, 0)):
        pp = Vector2(self.pc.pos[0] * TS + TS / 2 + ofs[0],
                     self.pc.pos[1] * TS + TS / 2 + ofs[1])
        for row in self.flr.tiles:
            for tile in row:
                if isinstance(tile, HiddenTile):
                    tile.draw(sf, pp, ofs)
                else:
                    tile.draw(sf, ofs)
        pygame.draw.circle(sf, (255, 50, 50), pp, TS // 3)
        if self.flr.start:
            sp = Vector2(self.flr.start[0] * TS + TS / 2 + ofs[0],
                        self.flr.start[1] * TS + TS / 2 + ofs[1])
            pygame.draw.circle(sf, (50, 255, 50), sp, TS // 4)
        if self.flr.exit:
            pygame.draw.rect(sf, (255, 255, 50),
                            pygame.Rect(self.flr.exit[0] * TS + ofs[0],
                                       self.flr.exit[1] * TS + ofs[1], TS, TS), 2)

    def can_walk(self, x, y):
        return self.flr.is_walk(x, y)

    def move_pc(self, dx, dy):
        if self.state != GameState.EXPLORING:
            return False
        x, y = self.pc.pos
        tx, ty = x + dx, y + dy
        if not self.can_walk(tx, ty):
            return False
        self.pc.pos = (tx, ty)
        t = self.flr.get_tile(tx, ty)
        if t:
            t.on_enter(self, self.pc)
        nr = self.flr.get_room_at(tx, ty)
        pr = self.p_room
        if nr != pr:
            self.p_room = nr
            ene = self.enc_found(nr)
            if ene:
                self.enter_combat(ene, nr)
                return True
        if self.state == GameState.EXPLORING and (tx, ty) == self.flr.exit:
            self.adv_flr()
        return True

    def upd(self, act=None):
        if self.state != GameState.EXPLORING or act is None:
            return False
        match act.get('type'):
            case 'move' if isinstance(act.get('direction'), tuple):
                dx, dy = act['direction']
                return self.move_pc(dx, dy)
            case _:
                return False

    def enter_combat(self, ene, room=None):
        self.ene_lst = ene
        self.res_ord.clear()
        self.c_room = room
        if room:
            self.flr.lock_room(room)
        self.set_state(GameState.COMBAT)
        self.begin_turn()

    def begin_turn(self):
        self.res_ord.clear()
        self.pc.apply_pend_stat()
        for e in self.ene_lst:
            if e.is_alive():
                e.apply_pend_stat()
        mc = Context(game=self, target=None, slot=None, damage=0)
        self.mass_bc('turn_start', 'turn_start', mc)
        self._autopilot_ene()
        if self.pc.is_stag() and any(s.owner != self.pc for s in self.res_ord):
            self.exec_turn()

    def _autopilot_ene(self):
        for e in self.ene_lst:
            if e.is_alive() and not e.is_stag():
                e.autopilot()

    def exec_turn(self):
        mc = Context(game=self, target=None, slot=None, damage=0)
        self.mass_bc('resolve_start', 'resolve_start', mc)
        self.start_res()

    def start_res(self):
        self.res_q = []
        self.cur_res_ev = None
        self.res_act = False
        self._build_res_q()
        if self.res_q:
            self.res_act = True
        else:
            self._finish_res()

    def step_res(self):
        if not self.res_act:
            return
        if not self.res_q:
            self._finish_res()
            return
        ev = self.res_q.pop(0)
        self.cur_res_ev = ev
        self._proc_res_ev(ev)
        if not self.res_q:
            self._finish_res()

    def _finish_res(self):
        self.res_act = False
        self.cur_res_ev = None
        mc = Context(game=self, target=None, slot=None, damage=0)
        self.mass_bc('turn_end', 'turn_end', mc)
        for c in [self.pc] + self.ene_lst:
            if c.is_alive():
                c.draw_sk(1)
        self.pc.decay_stat()
        self._recover_stag_sr(self.pc)
        for e in self.ene_lst:
            e.decay_stat()
            self._recover_stag_sr(e)
        if self.state == GameState.COMBAT:
            if not any(e.is_alive() for e in self.ene_lst):
                self.exit_combat()
            else:
                self.begin_turn()

    def _build_res_q(self):
        snap = sorted(self.res_ord, key=lambda s: s.get_speed(), reverse=True)
        proc = set()
        for sl in snap:
            if id(sl) in proc:
                continue
            if not sl.owner or not sl.owner.is_alive():
                continue
            def_ = sl.get_target_creature()
            tgts = self.get_sk_tgts(sl)
            if not tgts:
                continue
            pt = def_ if def_ and def_.is_alive() else next((t for t in tgts if t.is_alive()), None)
            if not pt:
                continue
            csl = next((s for s in snap if s.owner == def_ and s.get_target_creature() == sl.owner and id(s) not in proc), None)
            if not sl.sk:
                continue
            if csl:
                if not csl.sk:
                    continue
                self.res_q.extend(self._build_clash_seq(sl, csl, pt))
                proc.add(id(csl))
            else:
                self.res_q.extend(self._build_atk_seq(sl, pt))
            proc.add(id(sl))
        self.res_ord.clear()

    def _build_clash_seq(self, sl, csl, pt):
        atk = sl.owner
        def_ = pt
        sk = sl.sk
        osk = csl.sk
        md = [d.copy() for d in sk.dice]
        td = [d.copy() for d in osk.dice]
        bc = Context(
            game=self, attacker=atk, defender=def_, target=sl.get_target_creature() or pt,
            skill=sk, opponent_skill=osk, slot=sl, opponent_slot=csl, die=None, index=-1,
            clash_history=[], damage=0, targets=self.get_sk_tgts(sl), target_positions=sl.get_target_positions()
        )
        seq = [{'type': 'clash_start', 'context': bc, 'description': f'{atk.name} clashes with {def_.name}'}]
        ml = min(len(md), len(td))
        for i in range(ml):
            seq.append({
                'type': 'clash_die', 'index': i, 'context': bc,
                'my_die': md[i], 'their_die': td[i],
                'player_is_attacker': atk == self.pc, 'description': f'Clash roll {i + 1}'
            })
        if len(td) > ml:
            seq.extend(self._build_atk_seq(csl, sl.owner, start_index=ml, use_slot=csl))
        elif len(md) > ml:
            seq.extend(self._build_atk_seq(sl, pt, start_index=ml, use_slot=sl))
        seq.append({'type': 'sequence_end', 'slot': sl, 'counter_slot': csl})
        return seq

    def _build_atk_seq(self, sl, pt, start_index=0, use_slot=None):
        if not use_slot:
            use_slot = sl
        sk = use_slot.sk
        atk = use_slot.owner
        tgts = self.get_sk_tgts(use_slot)
        ctx = Context(
            game=self, attacker=atk, defender=pt, target=use_slot.get_target_creature() or pt,
            skill=sk, slot=use_slot, die=None, index=-1, clash_history=[], damage=0,
            targets=tgts, target_positions=use_slot.get_target_positions()
        )
        seq = [{'type': 'attack_start', 'context': ctx, 'start_index': start_index,
               'player_attack': atk == self.pc, 'description': f'{atk.name} begins an unopposed attack'}]
        d = [die.copy() for die in sk.dice]
        for i in range(start_index, len(d)):
            seq.append({
                'type': 'attack_die', 'index': i, 'context': ctx, 'die': d[i],
                'player_attack': atk == self.pc, 'description': f'Attack roll {i + 1}'
            })
        seq.append({'type': 'sequence_end', 'slot': use_slot, 'counter_slot': None})
        return seq

    def _proc_res_ev(self, ev):
        et = ev.get('type')
        match et:
            case 'clash_start':
                ctx = ev['context']
                ctx.phase = 'clash'
                ctx.atk.fx_proc('on_play', ctx)
                ctx.sk.fx_proc('on_play', ctx)
                ctx.sk.fx_proc('on_clash_start', ctx)
            case 'clash_die':
                ctx = ev['context']
                ctx.phase = 'clash'
                ctx.idx = ev['index']
                ctx.sk.fx_proc('on_clash', ctx)
                atk = ctx.atk
                def_ = ctx.def_
                md = ev['my_die']
                td = ev['their_die']
                ctx.die = md
                ctx.atk = atk
                ctx.def_ = def_
                atk.fx_proc('on_die_roll', ctx)
                md.fx_proc('on_die_roll', ctx)
                ar = md.roll(ctx)
                ctx.die = td
                ctx.atk = def_
                ctx.def_ = atk
                def_.fx_proc('on_die_roll', ctx)
                td.fx_proc('on_die_roll', ctx)
                dr = td.roll(ctx)
                ctx.ch.append((ar, dr))
                ev['attacker_roll'] = ar
                ev['defender_roll'] = dr
                if ar > dr:
                    ctx.dmg = ar - dr
                    ctx.die = md
                    ctx.atk = atk
                    ctx.def_ = def_
                    atk.fx_proc('on_win', ctx)
                    md.fx_proc('on_win', ctx)
                    tgt = ctx.get_opponent(atk)
                    tgt.take_dmg(ctx.dmg, md.type, ctx)
                elif dr > ar:
                    ctx.dmg = dr - ar
                    ctx.die = td
                    ctx.atk = def_
                    ctx.def_ = atk
                    def_.fx_proc('on_win', ctx)
                    td.fx_proc('on_win', ctx)
                    tgt = ctx.get_opponent(def_)
                    tgt.take_dmg(ctx.dmg, td.type, ctx)
                else:
                    ev['result'] = 'tie'
            case 'attack_start':
                ctx = ev['context']
                ctx.phase = 'attack'
                ctx.opp_sk = None
                ctx.opp_sl = None
                ctx.atk.fx_proc('on_play', ctx)
                ctx.sk.fx_proc('on_play', ctx)
                ctx.sk.fx_proc('on_unopposed_attack', ctx)
            case 'attack_die':
                ctx = ev['context']
                ctx.phase = 'attack'
                ctx.idx = ev['index']
                ctx.die = ev['die']
                atk = ctx.atk
                ctx.atk.fx_proc('on_die_roll', ctx)
                ctx.die.fx_proc('on_die_roll', ctx)
                rll = ctx.die.roll(ctx)
                ev['roll'] = rll
                tgts = ctx.tgts or ([ctx.def_] if ctx.def_ else [])
                for tgt in tgts:
                    if not tgt or not tgt.is_alive():
                        continue
                    tc = ctx.with_target(tgt)
                    ctx.sk.fx_proc('on_hit', tc)
                    ctx.die.fx_proc('on_hit', tc)
                    ctx.die.fx_proc('on_unopposed_hit', tc)
                    tgt.take_dmg(rll, ctx.die.type, tc)
            case 'sequence_end':
                sl = ev['slot']
                csl = ev.get('counter_slot')
                ctx = Context(game=self, attacker=sl.owner, defender=sl.get_target_creature(), skill=sl.sk, slot=sl, die=None, index=-1, clash_history=[], damage=0)
                if sl.owner:
                    sl.owner.fx_proc('on_attack_end', ctx)
                    sl.owner.discard(sl.sk, ctx)
                if csl and csl.owner:
                    cc = Context(game=self, attacker=csl.owner, defender=csl.get_target_creature(), skill=csl.sk, slot=csl, die=None, index=-1, clash_history=[], damage=0)
                    csl.owner.fx_proc('on_attack_end', cc)
                    csl.owner.discard(csl.sk, cc)

    def exit_combat(self):
        if self.c_room:
            self.flr.unlock_room(self.c_room)
            self.c_room.clr = True
            self.c_room = None
        self.res_ord.clear()
        self.ene_lst = []
        self.set_state(GameState.EXPLORING)

    def enc_found(self, room):
        if not room or room.clr or not room.enc_pos:
            return None
        ene = [self.spawn_ene_at(pos) for pos in room.enc_pos]
        room.enc_pos = []
        return ene

    def spawn_ene_at(self, pos):
        e = self.eng.create_rand_enemy(pos)
        self.add_ene(e)
        return e
    
    def add_ene(self, e):
        e.layout = self
        if e.max_pts > 0:
            e.pts = e.max_pts
        try:
            e.fx.append(self.eng.load_fx('restore_points'))
        except ValueError:
            pass
        if e.max_pts > 0:
            try:
                e.fx.append(self.eng.load_fx('card_draw'))
            except ValueError:
                pass
        self._apply_def_turn_end_fx(e)
        self.ene_lst.append(e)

    def get_c_at(self, x, y):
        if self.pc.is_alive() and self.pc.pos == (x, y):
            return self.pc
        return next((c for c in self.ene_lst if c.is_alive() and c.pos == (x, y)), None)

    def get_c_in_pos(self, pos):
        t = []
        for p in pos:
            c = self.get_c_at(*p)
            if c and c not in t:
                t.append(c)
        return t

    def get_sk_tgts(self, sl):
        sk = sl.get_skill()
        if not sk:
            return []
        if sl.get_target_positions():
            return self.get_c_in_pos(sl.get_target_positions())
        match sk.targeting_type:
            case 'self':
                return [sl.owner] if sl.owner and sl.owner.is_alive() else []
            case 'all_enemies':
                return [e for e in self.ene_lst if e.is_alive()] if sl.owner == self.pc else ([self.pc] if self.pc.is_alive() else [])
            case 'all_allies':
                return [self.pc] if sl.owner == self.pc else [e for e in self.ene_lst if e.is_alive()]
            case 'enemy':
                t = sl.get_target_creature()
                return [t] if t and t.is_alive() else []
            case _:
                t = sl.get_target_creature()
                return [t] if t and t.is_alive() else []

    def add_slot(self, sl):
        self.res_ord.append(sl)

    def get_allies(self, c):
        if c == self.pc:
            return [self.pc]
        return [a for a in self.ene_lst if a.is_alive()]
    
    def mass_bc(self, t, ph, ctx):
        ctx.phase = ph
        ctx.actor = self.pc
        ctx.atk = self.pc
        self.pc.fx_proc(t, ctx)
        for e in self.ene_lst:
            if not e.is_alive():
                continue
            ctx.actor = e
            ctx.atk = e
            e.fx_proc(t, ctx)

    def bc_ally_fx(self, c, t, ctx):
        for a in self.get_allies(c):
            if a != c:
                a.fx_proc(t, ctx)

    def handle_death(self, c, ctx=None):
        if c == self.pc:
            self.end()
        else:
            if ctx:
                self.bc_ally_fx(c, 'on_ally_death', ctx)
            tr = [s for s in self.res_ord if s.owner == c or s.tgt == c]
            for s in tr:
                self.res_ord.remove(s)
            if c in self.ene_lst:
                self.ene_lst.remove(c)
    
    def handle_stag(self, c, ctx=None):
        if ctx:
            self.bc_ally_fx(c, 'on_ally_stagger', ctx)
            tr = [s for s in self.res_ord if s.owner == c]
            for s in tr:
                self.res_ord.remove(s)
            self._rem_stag_res_ev(c)

    def _ev_belong_to_c(self, ev, c):
        if ev.get('slot') and ev['slot'].owner == c:
            return True
        if ev.get('counter_slot') and ev['counter_slot'].owner == c:
            return True
        ctx = ev.get('context')
        if not ctx:
            return False
        return ctx.atk == c or ctx.def_ == c or ctx.tgt == c

    def _rem_stag_res_ev(self, c):
        self.res_q = [ev for ev in self.res_q if not self._ev_belong_to_c(ev, c)]

    def _recover_stag_sr(self, c):
        if c.is_stag():
            c.stag_turns += 1
            if c.stag_turns > 1:
                c.SR = c.max_SR
                c.stag_turns = 0

    def end(self):
        if self.c_room:
            self.flr.unlock_room(self.c_room)
            self.c_room = None
        self.ene_lst.clear()
        self.res_ord.clear()
        self.set_state(GameState.GAME_OVER)

    def playerchar(self):
        return self.pc
    
    @property
    def playerchar(self):
        return self.pc
    
    @property
    def enemy_list(self):
        return self.ene_lst
    
    @property
    def current_resolution_event(self):
        return self.cur_res_ev
    
    @property
    def resolution_active(self):
        return self.res_act
    
    @property
    def statuses(self):
        return self.stat
    
    @property
    def res_order(self):
        return self.res_ord
    
    @property
    def damage_numbers(self):
        return self.dmg_num
    
    @property
    def status_numbers(self):
        return self.stat_num
