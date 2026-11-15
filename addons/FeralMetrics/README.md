# FeralMetrics

Measured damage for a feral druid on WoW Forever. It reads your own combat and reports what
actually happened, never what a tooltip claims should happen.

## What it shows

Tooltips of your abilities gain green `FM:` lines:

```
FM: 39 per tick x 3 ticks = 118
FM: landed 99 over 5.7s (3 ticks, every 2.20s)
FM: 5cp: Ferocious Bite avg 310 (300-320, 3 hits)
FM: Rip 5cp: 30 per tick x 8 ticks = 240
```

- **Per tick x designed ticks.** The per-tick figure is the average of ticks that really landed.
  It is multiplied by the number of ticks the spell is designed to deliver, not the number you
  happened to get, so a bleed cut short by a dying mob still reads as its full potential.
- **Landed.** What you actually got out of it, and how long it ran, so the clipping cost is
  visible next to the potential.
- **Every 2.20s.** The measured gap between ticks. If haste changes tick rate on this client,
  this number moves. If it stays put across gear with haste, it does not.
- **Combo spenders** (Rip, Ferocious Bite) are recorded separately at 1 through 5 points, so the
  damage per point spent is directly comparable.

## Profiles: why old data never lies about new gear

Every sample is stamped with a fingerprint of everything that changes your damage:

- level
- Strength, Agility, Stamina, attack power
- crit chance
- main hand weapon id and speed
- points in each talent tree

Change any of them and a new profile starts automatically. The old profile stays on disk, so
`/fm compare` shows old against new per ability and per combo point. Numbers from before a gear
change can never be mixed into the average after it.

## Commands

| command | does |
|---|---|
| `/fm` | current profile and its measured numbers |
| `/fm compare` | current profile against the one before it |
| `/fm profiles` | every profile stored, newest last, `*` marks the active one |
| `/fm tips` | toggle the tooltip lines |
| `/fm reset` | clear the current profile's samples |
| `/fm debug` | event counters, for checking the client is feeding it events |

## If nothing records

`/fm debug` reporting `events 0` after a fight means this client is not delivering combat log
events to addons. Details registers the same event, so it should, but if it does not, tell me and
we will find the path Details uses on Forever.

## Files

- `FeralMetrics.lua` - the addon
- `FeralMetrics.toc` - interface 16001
- `tests/stub.lua`, `tests/smoke.lua` - runs the addon outside the game: `luajit tests/smoke.lua`
