# Premise

This project is a prototype of a roguelike dungeon crawler built around a card-based combat system. The player explores a procedurally generated floor, enters rooms, and resolves fights using a deck of skill cards rather than conventional weapons or equipment.

## Core mechanics

### Exploration
- The world is generated as a grid of rooms connected by corridors.
- The player moves with simple tile-based controls and discovers rooms as they walk.
- Rooms may contain encounter triggers, and entering an uncleared room begins combat.
- The current dungeon loop is functional but intentionally minimal: floor generation is basic room-and-corridor layout, enemy placement is random, and progression is limited to moving from one floor to the next.

### Deck-driven combat
- Combat is driven by skill cards drawn from a personal deck.
- The player has a deck, a hand, and a discard pile, with simple drawing and reshuffle behavior.
- Each skill card has a cost, a targeting type, and one or more dice that define its combat behavior.
- The player assigns cards into combat slots, chooses targets, and then resolves those slots in a speed-based order.
- The combat UI includes hand and slot visibility toggles, and long card descriptions can be scrolled with the mouse wheel when visible.
- Combat includes floating feedback: red damage pop-ups appear when creatures take damage.
- Enemies can be clicked to inspect them during combat, and slots can be dragged onto enemy targets for assignment.
- The combat camera view centers dynamically between the player and all alive enemies during combat.

### Speed and slot resolution
- Cards are not played instantly. They are assigned to slots, and each slot generates a speed value.
- Combat resolves as a series of ordered actions: faster slots resolve first, and opposing actions can clash.
- When both sides choose actions that target each other, the system can create a clash sequence rather than a simple hit.
- This gives the combat a tactical rhythm where timing and target assignment matter as much as raw card power.

## Combat structure

### Clash vs unopposed attacks
- A skill can clash with an opposing skill if both participants target each other.
- In a clash, dice from each side are compared pairwise; the winner deals damage based on the roll difference.
- If a skill has more dice than its opponent, any extra dice can continue as an unopposed attack.
- If no clash occurs, the skill resolves as an unopposed attack and deals damage directly based on its dice rolls.

### AoE attacks
- Attacks of fireball/cone/line types can strike multiple opponents at once, yet can only be aimed at one.
- The clash on such attacks occurs only against the primary target.
- Evade or guard dice on secodary target's skills can still defend against AoE attacks if order of resolution allows as such.

### Dice-driven effects
- Each skill contains one or more dice with a type and roll range.
- Dice types such as `evade`, `pierce`, `blunt`, or `true` determine how effects trigger and how damage interacts with targets.
- Dice can carry their own effects, allowing individual die results to influence the flow of combat.
- This makes the die the smallest expressive unit: a single skill can behave differently depending on which die succeeds or loses.

## Status and effect systems

### Effect system
- Effects are defined as trigger/action pairs, optionally gated by conditions.
- Triggers include combat events like `on_play`, `on_die_roll`, `on_hit`, `turn_start`, and `turn_end`.
- Actions include modifying die ranges, inflicting statuses, healing, restoring action points, drawing cards, and refreshing the deck.
- Conditions allow effects to depend on state, for example whether a target has a certain amount of a status or whether the opponent used a specific skill type.
- The effect model is intentionally generic and context-driven, so future cards and abilities can be added without changing core resolution logic.

### Status system
- Creatures can gain statuses that persist over multiple turns.
- Statuses are stored with potency and stack count, and they can decay automatically at the end of a turn.
- Statuses may contain multiple effects, though some merely serve as counters for outside effects.
- Actual status application is now shown with floating pop-ups near the creature receiving the status.
- Statuses may activate on specific triggers and can be scheduled to appear after a certain number of turns.

## Player state and resources

- The player has hit points (HP) and stagger resistance (SR).
- SR acts like a secondary threshold that can be broken by damage, causing a stagger until a full turn passes.
- When the player is staggered, the card assignment phase is skipped and combat resolution begins immediately.
- Slot speeds are rolled once at turn start and remain fixed for that turn, so timing is locked in when actions are committed.
- A separate shield value is tracked on creatures and can absorb damage before HP is reduced.
- Action points are used to assign cards to slots, making budget management a core part of each turn.
- The current implementation includes basic restore and refresh mechanics, including draw-when-empty and deck-refresh triggers.
- A player status button in combat allows toggling an expanded status panel for quick in-fight status inspection.

## Current limitations

- Enemy AI is still rudimentary: enemies choose random affordable cards and attack directly, though they now commit their actions before the player chooses theirs.
- Floor generation works, but it is not yet feature-rich: rooms are generic and there are no special events, traps, or noncombat locations, though tiles of different types have been prepared.
- Game progression is limited to floor advancement; there is no persistent meta-progression, shops, or reward systems yet.

## Future additions

### Equipment, weapons, and classes
- Introduce equipment and weapon systems that interact with die types and status effects.
  - e.g. a spear that adds `pierce` dice on skills, armor that increases SR or resists a damage type, or a cloak that boosts `evade` effects.
- Add classes or archetypes with unique deck-building rules and combat identity.
  - a “duelist” whose cards gain bonus speed or counterstrike effects
  - a “warden” who manipulates SR and defends allies
  - a “spellblade” who converts status stacks into AoE burst damage
- Allow weapon affinity and passive traits to modify how cards resolve, such as enabling extra clash rolls for weapons that “disrupt” enemy attacks.

### Deck and run systems
- Add card acquisition, upgrade, and removal during the run.
- Implement a reward choice after combat or room clears, such as choosing between new cards, permanent buffs, or currency.
- Add a draft/shop layer where players choose between a few options rather than receiving fixed loot.

### Dungeon and encounter depth
- Add special rooms and noncombat events, including merchants, resting points, trap floors, puzzles, or hidden caches.
- Support bosses and elite enemies with signature decks and scripted behaviors.
- Introduce room modifiers or environmental hazards that change the meaning of certain dice or statuses.

### Combat enhancements
- Add richer targeting options: multi-target cards, tile-targeting skills, and conditional AoE.
- Add more interaction between cards and status systems, such as skills that consume status stacks to amplify damage.
- Introduce temporary stances, combo chains, or initiative manipulation to deepen turn planning.

### Meta-progression and player identity
- Introduce permanent relics, experience, or unlockable classes that evolve the run.
- Add a layer of progression tied to player choices, such as unlocking new starting cards or class-specific talents.
- Add a small narrative thread or event system that gives context to dungeon floors and makes progression feel meaningful.

## Why this approach
The current design is centered on tactical card play rather than raw numerical stats. Its distinct strength is the interaction between assigned skills, speed-based slot resolution, and a flexible effect engine. By keeping the combat system generic and context-aware, the project is well positioned to support a wide variety of card types, status synergies, and emergent combat behavior.

This document is meant to capture the current implementation and to frame improvements in a way that preserves the project’s core identity: a dungeon crawler where the deck is the primary tool, and every fight is shaped by timing, status interaction, and the choices made before a single die is rolled.

