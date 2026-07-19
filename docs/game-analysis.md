# Game Analysis: Boxhead 2Play

## Overview

- **Genre:** Top-down shooter, wave survival
- **Objective:** Kill zombies (and devils in later waves) — survive as long as possible
- **Mode used by bot:** Single Play (Player 1)
- **URL:** https://www.twoplayergames.org/game/boxhead-2play

---

## Launch & Reset Sequence

Getting from a fresh page load to the player standing on the arena requires navigating several screens first — **all via mouse**, not keyboard. This happens before `InputController` (keyboard-only, in-arena controls) becomes relevant at all.

### First launch (full sequence)
1. Page loads — a **random ad** appears first (unpredictable presence/timing)
2. Once ready, a red **"Play" button** appears. Confirmed via DevTools inspection: this is a **real DOM element**, not part of the game canvas — `<a id="button-play" class="play-button" href="#">`. Click it via a Playwright selector (`page.click("#button-play")`), and use `wait_for_selector` to handle the random ad delay instead of guessing a fixed wait time.
3. Two loading screens with progress bars
4. Publisher intro screen
5. Main menu appears — click **"SINGLE PLAY"**. Confirmed via DevTools: **not** in the DOM — this and everything from here on is rendered inside the game's `<canvas>` (Ruffle/Flash), so it needs `page.mouse.click(x, y)` at calibrated pixel coordinates, same concern as the canvas ROI (see [Game Canvas](#game-canvas)).
6. Character/map select screen — character choice is **cosmetic only** (no gameplay effect). Click a map (highlights red on hover) to select it.
7. Short loading → player appears on the arena, gameplay begins

### Reset after death (fast path — use this for RL episode resets)
On death, a Game Over screen appears (canvas-rendered) showing score, a name-entry/"SEND SCORE" prompt, "View Highscores", "Select new level", and **"Retry"**. Clicking **"Retry"** skips the entire first-launch sequence above (no ad, no intro, no menu, no character/map select) — short loading, then the player is back on the arena.

This makes `Retry` the right reset mechanism for `BoxheadEnv.reset()` — reloading the page for every training episode would be far slower and re-expose the random ad each time.

### Architecture note
The project's "no mouse input" framing (see `CLAUDE.md`) applies to **in-arena gameplay only** — aiming is by movement direction, no mouse aiming during play. Launch/menu/reset navigation is a separate concern and does need `page.mouse`, but only for clicking fixed, known locations (not aiming) — a much narrower need than the earlier-rejected "MouseController — aim and click" idea (issue #16).

---

## Controls (Player 1)

| Action | Key |
|---|---|
| Move up | Arrow Up |
| Move down | Arrow Down |
| Move left | Arrow Left |
| Move right | Arrow Right |
| Shoot | `Space` |
| Next weapon | `.` |
| Prev weapon | `,` |
| Select weapon | `0–9` (single player only) — see [Weapons](#weapons) for the mapping |
| Pause | `P` |

---

## Game Canvas

The game runs inside a `<canvas>` element (Ruffle/WebAssembly) embedded in the twoplayergames.org page. The canvas is surrounded by browser chrome (navbar, ads).

**Canvas position on page:** centered, approximately `515x415px` starting at ~`(460, 160)` (may vary by screen resolution).

**What the bot sees:** full browser screenshot — canvas must be cropped via ROI.

---

## Visual Elements to Detect

### Player
- **Appearance:** Small box-shaped figure, dark/black color
- **HUD overlay:** Live text directly above the player, format `<WeaponName>:<AmmoCount>` (e.g. `Shotgun:40`, `UZI:73`), with a bar underneath (color observed green — likely health, unconfirmed). Always visible during play, not just in the pause menu — the simplest detection target for current weapon + ammo (see [Fire Mechanics](#fire-mechanics))
- **Health:** No health packs in this game — the health bar regenerates automatically over time after the player stops taking hits. No pickup item to detect for healing.
- **Position:** Anywhere on the canvas
- **Movement:** 8 directions — Up, Down, Left, Right, Up-Left, Up-Right, Down-Left, Down-Right (diagonal via two keys held simultaneously)
- **Death:** Dead player sprite is rendered lying flat/rotated (not upright), and appears to switch to a darker navy-blue color — distinct from the normal standing sprite
- **Detection:** YOLO label `player` (alive) / `player_dead`. The `player_dead` sighting is a candidate signal for the `-death` reward term in `BoxheadEnv` — more direct than reading the Game Over screen or health-bar state. The HUD text (weapon + ammo) is a separate OCR task, not covered by object detection.

### Enemies — Zombies
- **Appearance:** Box-shaped figures, similar size to player, darker/grey tones
- **Behavior:** Walk toward the player, melee attack only (close range)
- **Death:** Dead zombies are rendered lying flat/rotated on the ground, same grey tones — no longer a threat, but visually similar enough to a standing zombie that conflating the two would mislead the policy
- **Detection:** YOLO label `zombie` (alive) / `zombie_dead`

### Enemies — Devils (later waves)
- **Appearance:** Red box-shaped figures
- **Behavior:** Melee attack + ranged attack — dangerous at any distance
- **Death:** Same lying-flat/rotated pose as dead zombies, red-toned
- **Detection:** YOLO label `devil` (alive) / `devil_dead` — kept separate from `zombie`/`zombie_dead` since the ranged attack means the policy likely needs to react differently while alive (devils are dangerous from a distance, zombies only up close)

### Devil Projectiles
- **Appearance:** Small yellow dot, travels from a devil toward the player
- **Behavior:** Devils' ranged attack — the actual threat that makes them dangerous at a distance (see above)
- **Detection:** YOLO label `devil_projectile` — small and fast-moving, but important for the policy to learn to dodge

### Score
- **Position:** Top-center of canvas
- **Format:** `000000003100` (zero-padded number)
- **Multiplier:** `x3` shown next to score when combo active

### Weapons

Full roster and select-key mapping, from the pause-menu "UPGRADE LIST" screen (unlocked weapons shown there in green with a `Key N` label):

| Weapon | Key | Notes |
|---|---|---|
| Pistol | `1` | Always available, infinite ammo |
| UZI | `2` | |
| Shotgun | `3` | |
| Barrel | `4` | Placeable explosive — same visual as pre-placed level barrels (see [Objects / Pickups](#objects--pickups)) |
| Grenade | `5` | Charge-and-release throw — see [Fire Mechanics](#fire-mechanics) |
| Fake Wall | `6` | Placeable obstacle |
| Claymore | `7` | In-game HUD shows this weapon as `Mines` (e.g. `Mines:10`), not `Claymore` — the pause-menu upgrade list and the live HUD use different names for the same weapon |
| Rocket | `8` | |
| Chargepack | `9` | |
| Railgun | `0` | |

New weapons are **not** floor pickups — they unlock automatically at score/time thresholds shown in the pause-menu upgrade list (e.g. "5: New Weapon: UZI (Key 2)"), same as other upgrades (see [Upgrades](#upgrades)).

### Fire Mechanics

- **Semi-auto by default:** base weapons (pistol, shotgun, etc.) do not fire continuously while the fire key is held — each shot needs a fresh key-press edge (release + re-press). Continuous fire while holding only becomes available after picking up that weapon's **Fast Fire** upgrade (see [Upgrades](#upgrades)).
- **Charge-and-release (Grenade):** pressing Space does not throw immediately — holding it charges the throw, and the longer it's held the farther it throws (up to a cap; holding indefinitely doesn't keep increasing distance). The grenade is actually thrown on **release** of Space. This maps naturally onto `InputController.shoot()`'s existing hold-based design (`shoot(True)`/`shoot(False)` mirrors press/release) — no controller changes needed.
- **Ammo depletion auto-switches to pistol:** when the equipped weapon runs out of ammo, the game automatically re-equips the pistol (infinite ammo), with no explicit input from the player.
- **Movement and shooting are independent** — arrow keys (movement) and the fire key can be held/pressed simultaneously with no conflict.

### Upgrades

Pressing Pause (`P`) opens a screen listing all upgrades ("UPGRADE LIST"). Owned upgrades render in **white** text, unowned in **gray** — reading this table (OCR + text color check) gives a full snapshot of owned upgrades in one shot.

Upgrade categories seen per weapon: Fast Fire, Double Damage, Double Ammo, Rapid Fire, Big Bang, Cluster Explode, Wide Shot, Long Shot, Quad Ammo, Quad Damage, Infinite Range. New weapons themselves (see [Weapons](#weapons)) are also unlocked as upgrades, shown in green with their select key once owned — all unlocked automatically by score/time progression, not by picking anything up off the ground.

Alternative detection path: an on-screen toast briefly names the upgrade when picked up (transient, harder to catch reliably than reading the pause-menu table).

### Objects / Pickups
- **Red boxes (crates):** Ammo pickups (not new weapons — see [Weapons](#weapons)) — scattered around map
- **Grey barrels:** Explosive barrels — can be used tactically
- **Detection:** YOLO label `ammo_pack` for crates, `barrel` for barrels. No `health_pack` class — this game has no health pickups (see [Player](#player)).

### Placed Objects — Fake Wall / Mine
- Both are placed on the map by the player as weapons (see [Weapons](#weapons): `Fake Wall` key `6`, `Claymore`/`Mines` key `7`), then persist as level objects until triggered/destroyed
- **Mine appearance (confirmed):** small white/light tilted rectangle with a red marking/symbol
- **Fake Wall appearance:** not yet documented in detail — flag when a fixture screenshot shows one clearly
- **Detection:** YOLO labels `fake_wall` and `mine`

### Explosions
- **Appearance:** large yellow ring(s)/shockwave, can overlap when multiple trigger close together
- **Confirmed trigger:** shooting a `barrel`. Mines likely explode similarly (not yet directly confirmed on a screenshot); grenades/rockets presumably too, given they're explosive weapons (see [Weapons](#weapons)) — unconfirmed.
- **Danger:** lethal to the player at close range — a death was observed immediately after standing next to a barrel explosion. This is a significant, fast-appearing hazard, not just a visual effect.
- **Screen flash:** the background briefly turns white during an explosion — this is a transient visual effect, not a different map/terrain (see [Terrain](#terrain--floor--wall)); worth accounting for as noise if using color segmentation for floor/wall around the time of an explosion.
- **Detection:** YOLO label `explosion` — a direct, source-agnostic "danger here" signal, useful even before the bot has learned to fear specific objects like `barrel`/`mine`.

### Terrain — Floor / Wall
- **Floor (walkable):** irregular beige/sand-colored patch
- **Wall (not walkable):** irregular lavender/pink area surrounding the floor patch — soft, organic-shaped boundary within the arena (distinct from the hard boundary below)
- **Hard boundary:** solid grey rectangular blocks along the outer edges of the arena (seen at the top of the canvas when the player is near that edge — the arena is larger than one viewport, so this scrolls in/out of frame with player position). Gaps between blocks line up with enemy spawn points (see [Map](#map--basic-arena-focus-for-v1)).
- **Detection:** not a YOLO class — both the floor/wall boundary and the hard-boundary blocks are large, flat, solid-color regions, poorly suited to bounding boxes. Better handled with plain OpenCV color segmentation/thresholding (already a project dependency) than by training a detector class. Note the white screen-flash during [explosions](#explosions) as a transient edge case for this segmentation.

### Map — Basic Arena (focus for v1)
- **Shape:** Square/rectangle, open arena with no obstacles inside
- **Background:** Beige/sand-colored floor, bounded by wall terrain (see [Terrain](#terrain--floor--wall))
- **Spawn points:** Top and bottom edges of the map, at gaps in the hard boundary — enemies enter from there in waves
- **Multiple maps available** — bot targets basic arena first

### Round Structure
- Game is divided into rounds (waves)
- Each round starts with a short delay before enemies spawn
- Round ends when all enemies in the wave are killed
- Enemy count increases with each round

---

## Screenshots Needed for Test Fixtures

| Fixture | Description | Used by |
|---|---|---|
| `game_playing.png` | Active gameplay with player + zombies + devils visible | YOLODetector (`player`, `zombie`, `devil`) |
| `game_player_only.png` | Player visible, no enemies nearby | YOLODetector (`player`) |
| `game_enemies_only.png` | Multiple zombies and devils, no player in center | YOLODetector (`zombie`, `devil`) |
| `game_devil_projectile.png` | Devil mid-ranged-attack, projectile visible | YOLODetector (`devil_projectile`) |
| `game_objects.png` | Ammo crates and barrels visible | YOLODetector (`ammo_pack`, `barrel`) |
| `game_placed_objects.png` | Fake wall and/or mine placed on the map | YOLODetector (`fake_wall`, `mine`) |
| `game_dead_entities.png` | Dead zombie/devil/player corpses visible | YOLODetector (`zombie_dead`, `devil_dead`, `player_dead`) |
| `game_explosion.png` | Barrel/mine explosion in progress | YOLODetector (`explosion`) |
| `game_menu.png` | Main menu screen | State detection |
| `game_canvas_crop.png` | Cropped canvas only (no browser chrome) | ROI calibration |

---

## Reward Shaping Inspiration

These aren't hardcoded rules — the RL policy (`BoxheadEnv`, PPO) learns its own behavior from the reward signal (`+score_delta`, `-death`, `+survival_tick` per `CLAUDE.md`). Domain intuition worth keeping in mind when tuning the reward function:

- Staying mobile / keeping distance from enemies tends to correlate with survival
- Aiming is a side effect of movement direction (no mouse aim — see [Controls](#controls-player-1)), so "shooting effectively" is entangled with "moving toward/away from the right spot"
- Pistol is always available (infinite ammo) as a fallback; other weapons unlock over time/score, and their ammo runs out and must be topped up from crates (see [Fire Mechanics](#fire-mechanics))
- Devils are dangerous at range (see [Devil Projectiles](#devil-projectiles)) — "keep distance" isn't a universally safe strategy once devils appear
- Enemy count increases per wave (see [Round Structure](#round-structure)) — the policy needs to generalize to handling more simultaneous enemies than it may see early in training
- `zombie_dead`/`devil_dead` detections are inert — don't treat them as threats when computing distance-to-nearest-enemy features. `player_dead` is a candidate direct signal for the `-death` reward term (see [Player](#player))
- A detected `explosion` near the player is an immediate, severe danger signal (see [Explosions](#explosions)) — a death was directly observed from standing too close to one. Likely worth a stronger/more immediate penalty signal than generic enemy proximity, since it can kill in a single tick.
