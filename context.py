from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from creature import Creature
    from skill import Skill
    from skillslot import Skillslot
    from die import Die

class Context:
    def __init__(self, **kw):
        self.phase = kw.get('phase')
        self.game = kw.get('game')
        self.source = kw.get('source')
        self.ev_data = kw.get('event_data', {})
        self.actor = kw.get('actor')
        self.tgt = kw.get('target')
        self.atk = kw.get('attacker')
        self.def_ = kw.get('defender')
        self.sk = kw.get('skill')
        self.opp_sk = kw.get('opponent_skill')
        self.sl = kw.get('slot')
        self.opp_sl = kw.get('opponent_slot')
        self.die = kw.get('die')
        self.idx = kw.get('index')
        self.ch = kw.get('clash_history', [])
        self.dmg = kw.get('damage', 0)
        self.tgts = kw.get('targets')
        self.tgt_pos = kw.get('target_positions', [])
        self.hp_l = kw.get('hp_lost', 0)
        self.hp_pl = kw.get('hp_percent_lost', 0)
        self.target = kw.get('target')  # alias for compatibility
        self.defender = kw.get('defender')  # alias
        self.attacker = kw.get('attacker')  # alias
        self.damage = kw.get('damage', 0)  # alias
        self.targets = kw.get('targets')  # alias

    def with_die(self, d, i):
        return Context(
            phase=self.phase, game=self.game, source=self.source,
            event_data=self.ev_data.copy() if isinstance(self.ev_data, dict) else self.ev_data,
            actor=self.actor, target=self.tgt, attacker=self.atk, defender=self.def_,
            skill=self.sk, opponent_skill=self.opp_sk, slot=self.sl, opponent_slot=self.opp_sl,
            die=d, index=i, clash_history=list(self.ch), damage=self.dmg,
            hp_lost=self.hp_l, hp_percent_lost=self.hp_pl,
            targets=list(self.tgts) if self.tgts else None, target_positions=list(self.tgt_pos)
        )

    def with_target(self, t):
        return Context(
            phase=self.phase, game=self.game, source=self.source,
            event_data=self.ev_data.copy() if isinstance(self.ev_data, dict) else self.ev_data,
            actor=self.actor, target=t, attacker=self.atk, defender=t,
            skill=self.sk, opponent_skill=self.opp_sk, slot=self.sl, opponent_slot=self.opp_sl,
            die=self.die, index=self.idx, clash_history=list(self.ch), damage=self.dmg,
            targets=list(self.tgts) if self.tgts else None, target_positions=list(self.tgt_pos),
            hp_lost=self.hp_l, hp_percent_lost=self.hp_pl
        )

    def get_opponent(self, c):
        return self.def_ if c == self.atk else self.atk

    def get_allies(self, c):
        return self.game.enemy_list if c in self.game.enemy_list else [self.game.playerchar]
