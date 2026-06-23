from interactible import Interactible
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import Context
    from creature import Creature

class Effect(Interactible):
    def __init__(self, t, act, cond=None):
        self.trigger = t
        self.action = act
        self.condition = cond
    
    def get_trigger(self):
        return self.trigger
    
    def get_action(self):
        return self.action
    
    def get_cond(self):
        return self.condition
    
    def _get_tgt_lbl(self):
        tgt = self.action.get('target')
        match tgt:
            case 'self':
                return 'self'
            case 'defender' | 'target':
                return 'target'
            case 'ally':
                return 'ally'
            case 'all_allies':
                return 'all allies'
            case 'enemy':
                return 'enemy'
            case 'all_enemies':
                return 'all enemies'
            case None:
                return 'target'
            case _:
                return str(tgt)

    def _resolve_tgts(self, ctx):
        tgt = self.action.get('target')
        def alive(c):
            return c and c.is_alive()
        if tgt in (None, 'target', 'defender'):
            if ctx.tgts:
                return [t for t in ctx.tgts if alive(t)]
            if ctx.def_ and alive(ctx.def_):
                return [ctx.def_]
            if ctx.tgt and alive(ctx.tgt):
                return [ctx.tgt]
            return []
        if tgt == 'self':
            return [ctx.atk] if alive(ctx.atk) else []
        if tgt in ('enemy', 'opponent'):
            if ctx.atk and ctx.game:
                opp = ctx.get_opponent(ctx.atk)
                return [opp] if alive(opp) else []
            if ctx.def_ and alive(ctx.def_):
                return [ctx.def_]
            return []
        if tgt in ('ally', 'all_allies'):
            if ctx.atk and ctx.game:
                return [a for a in ctx.game.get_allies(ctx.atk) if alive(a)]
            return [ctx.atk] if alive(ctx.atk) else []
        if tgt == 'all_enemies':
            if ctx.atk and ctx.game:
                if ctx.atk == ctx.game.playerchar:
                    return [e for e in ctx.game.enemy_list if alive(e)]
                return [ctx.game.playerchar] if alive(ctx.game.playerchar) else []
            return []
        if tgt == 'all_targets':
            return [t for t in (ctx.tgts or []) if alive(t)]
        return []

    def _desc_action(self):
        at = self.action.get('type')
        tl = self._get_tgt_lbl()
        match at:
            case 'modify_max_roll':
                return f"Increase max roll by {self.action.get('value', 0)}"
            case 'modify_min_roll':
                return f"Increase min roll by {self.action.get('value', 0)}"
            case 'inflict_status':
                p = self.action.get('potency', 0)
                s = self.action.get('status', 'status')
                c = self.action.get('count', 0)
                pts = []
                if p:
                    pts.append(str(p))
                pts.append(s.capitalize())
                d = 'Inflict ' + ' '.join(pts)
                if c:
                    d += f' ({c} stacks)'
                if tl != 'target':
                    d += f' on {tl}'
                return d
            case 'grant_next_turn_status':
                s = self.action.get('status', 'status')
                c = self.action.get('count', 0)
                p = self.action.get('potency', 0)
                d = f'Grant {s.capitalize()} next turn'
                if p:
                    d += f' ({p})'
                if c:
                    d += f' x{c}'
                if tl != 'target':
                    d += f' to {tl}'
                return d
            case 'double_damage':
                m = self.action.get('multiplier', 2)
                return f'Double damage x{m}'
            case 'heal':
                a = self.action.get('amount', 0)
                return f'Heal {a} to {tl}'
            case 'damage_by_potency':
                s = self.action.get('status', 'status')
                m = self.action.get('multiplier', 1)
                return f'Damage by {m}x {s.capitalize()} potency to {tl}'
            case 'restore_points':
                p = self.action.get('points', 1)
                return f'Restore {p} points to {tl}'
            case 'restore_points_to_max':
                return f'Restore points to max for {tl}'
            case 'draw_skills':
                c = self.action.get('count', 1)
                pl = 's' if c != 1 else ''
                return f'Draw {c} card{pl}'
            case 'draw_if_empty_hand':
                c = self.action.get('count', 1)
                return f'Draw {c} if hand empty'
            case 'refresh_if_deck_empty':
                return 'Refresh deck if empty'
            case 'refresh':
                return 'Refresh deck'
            case 'gain_shield':
                a = self.action.get('amount', 0)
                return f'Gain {a} shield'
            case _:
                return f'{at.replace("_", " ").capitalize()}'

    def describe(self):
        tg = self.trigger.replace('_', ' ').capitalize()
        ad = self._desc_action()
        return f'[{tg}] {ad}'

    def check_cond(self, ctx):
        if not self.condition:
            return True
        match self.condition.get('type'):
            case 'status_count':
                tgt = ctx.def_ if self.condition.get('subject') == 'target' else ctx.atk
                s = self.condition['status']
                v = self.condition['value']
                return tgt.get_stat_cnt(s) >= v
            case 'consecutive_wins':
                n = self.condition['count']
                h = ctx.ch
                if len(h) < n:
                    return False
                return all(my > their for my, their in h[-n:])
            case 'opponent_skill_type':
                if not hasattr(ctx, 'opp_sk') or not ctx.opp_sk:
                    return False
                return ctx.opp_sk.targeting_type == self.condition.get('skill_type')
        return False

    def execute(self, ctx):
        if not self.check_cond(ctx):
            return
        match self.action.get('type'):
            case 'modify_max_roll':
                if ctx.die:
                    ctx.die.max_roll += self.action.get('value', 1)
            case 'modify_min_roll':
                if ctx.die:
                    ctx.die.min_roll += self.action.get('value', 1)
            case 'inflict_status':
                p = self.action.get('potency', 1)
                c = self.action.get('count', 1)
                sn = self.action['status']
                s = None
                if hasattr(ctx, 'game') and ctx.game:
                    s = ctx.game.statuses.get(sn)
                for tgt in self._resolve_tgts(ctx):
                    tgt.add_stat(s or sn, p, c)
            case 'grant_next_turn_status':
                p = self.action.get('potency', 1)
                c = self.action.get('count', 1)
                for tgt in self._resolve_tgts(ctx):
                    tgt.sched_stat(self.action['status'], p, c, del_=1)
            case 'double_damage':
                ctx.dmg *= self.action.get('multiplier', 2)
            case 'heal':
                a = self.action.get('amount', 10)
                for tgt in self._resolve_tgts(ctx):
                    tgt.HP = min(tgt.HP + a, tgt.max_HP)
            case 'damage_by_potency':
                for tgt in self._resolve_tgts(ctx):
                    s = tgt.get_stat(self.action['status'])
                    if not s:
                        continue
                    d = self.action.get('multiplier', 1) * s.potency
                    tgt.take_dmg(d, self.action.get('damage_type', 'true'), ctx)
                    if s.decay():
                        tgt.stat.pop(self.action['status'], None)
            case 'restore_points':
                p = self.action.get('points', 1)
                for tgt in self._resolve_tgts(ctx):
                    tgt.pts = min(tgt.pts + p, tgt.max_pts)
            case 'restore_points_to_max':
                for tgt in self._resolve_tgts(ctx):
                    tgt.pts = tgt.max_pts
            case 'draw_skills':
                c = self.action.get('count', 1)
                for tgt in self._resolve_tgts(ctx):
                    tgt.draw_sk(c)
            case 'draw_if_empty_hand':
                c = self.action.get('count', 1)
                for tgt in self._resolve_tgts(ctx):
                    if not tgt.hand:
                        tgt.draw_sk(c)
            case 'refresh_if_deck_empty':
                for tgt in self._resolve_tgts(ctx):
                    if not tgt.deck and tgt.disc:
                        tgt.refresh()
            case 'refresh':
                for tgt in self._resolve_tgts(ctx):
                    tgt.refresh()
            case 'gain_shield':
                a = self.action.get('amount', 0)
                for tgt in self._resolve_tgts(ctx):
                    if hasattr(tgt, 'shield'):
                        tgt.shield += a
