# Game Analysis: Boxhead 2Play

## Overview

- **Genre:** Top-down shooter, wave survival
- **Objective:** Kill zombies (and devils in later waves) — survive as long as possible
- **Mode used by bot:** Single Play (Player 1)
- **URL:** https://www.twoplayergames.org/game/boxhead-2play

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
- **HUD overlay:** Live text directly above the player, format `<WeaponName>:<AmmoCount>` (e.g. `Shotgun:40`), with a bar underneath (color observed green — likely health, unconfirmed). Always visible during play, not just in the pause menu — the simplest detection target for current weapon + ammo (see [Fire Mechanics](#fire-mechanics))
- **Position:** Anywhere on the canvas
- **Movement:** 8 directions — Up, Down, Left, Right, Up-Left, Up-Right, Down-Left, Down-Right (diagonal via two keys held simultaneously)
- **Detection:** YOLO label `player`. The HUD text (weapon + ammo) is a separate OCR task, not covered by object detection.

### Enemies — Zombies
- **Appearance:** Box-shaped figures, similar size to player, darker/grey tones
- **Behavior:** Walk toward the player, melee attack only (close range)
- **Detection:** YOLO label `enemy` — current 4-class label set (`player`, `enemy`, `weapon`, `health_pack`, per `CLAUDE.md`) doesn't distinguish zombies from devils

### Enemies — Devils (later waves)
- **Appearance:** Red box-shaped figures
- **Behavior:** Melee attack + ranged attack (yellow projectiles) — dangerous at any distance
- **Detection:** Also YOLO label `enemy` (same as zombies, see above) — may need a dedicated label later if the policy needs to react differently to devils' ranged attacks

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
| Barrel | `4` | |
| Grenade | `5` | Area of effect |
| Fake Wall | `6` | |
| Claymore | `7` | |
| Rocket | `8` | |
| Chargepack | `9` | |
| Railgun | `0` | |

### Fire Mechanics

- **Semi-auto by default:** base weapons (pistol, shotgun, etc.) do not fire continuously while the fire key is held — each shot needs a fresh key-press edge (release + re-press). Continuous fire while holding only becomes available after picking up that weapon's **Fast Fire** upgrade (see [Upgrades](#upgrades)).
- **Ammo depletion auto-switches to pistol:** when the equipped weapon runs out of ammo, the game automatically re-equips the pistol (infinite ammo), with no explicit input from the player.
- **Movement and shooting are independent** — arrow keys (movement) and the fire key can be held/pressed simultaneously with no conflict.

### Upgrades

Pressing Pause (`P`) opens a screen listing all upgrades ("UPGRADE LIST"). Owned upgrades render in **white** text, unowned in **gray** — reading this table (OCR + text color check) gives a full snapshot of owned upgrades in one shot.

Upgrade categories seen per weapon: Fast Fire, Double Damage, Double Ammo, Rapid Fire, Big Bang, Cluster Explode, Wide Shot, Long Shot, Quad Ammo, Quad Damage, Infinite Range. New weapons themselves (see [Weapons](#weapons)) are also unlocked as upgrades, shown in green with their select key once owned.

Alternative detection path: an on-screen toast briefly names the upgrade when picked up (transient, harder to catch reliably than reading the pause-menu table).

### Objects / Pickups
- **Red boxes (crates):** Weapon pickups — scattered around map
- **Grey barrels:** Explosive barrels — can be used tactically
- **Detection:** YOLO label `weapon` for crates. `health_pack` is in the planned label set (`CLAUDE.md`) but not yet observed/documented here.

### Map — Basic Arena (focus for v1)
- **Shape:** Square/rectangle, open arena with no obstacles inside
- **Background:** Beige/sand-colored floor
- **Spawn points:** Top and bottom edges of the map — enemies enter from there in waves
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
| `game_playing.png` | Active gameplay with player + enemies visible | YOLODetector (`player`, `enemy`) |
| `game_player_only.png` | Player visible, no enemies nearby | YOLODetector (`player`) |
| `game_enemies_only.png` | Multiple enemies, no player in center | YOLODetector (`enemy`) |
| `game_objects.png` | Red crates and barrels visible | YOLODetector (`weapon`, `health_pack`) |
| `game_menu.png` | Main menu screen | State detection |
| `game_canvas_crop.png` | Cropped canvas only (no browser chrome) | ROI calibration |

---

## Reward Shaping Inspiration

These aren't hardcoded rules — the RL policy (`BoxheadEnv`, PPO) learns its own behavior from the reward signal (`+score_delta`, `-death`, `+survival_tick` per `CLAUDE.md`). Domain intuition worth keeping in mind when tuning the reward function:

- Staying mobile / keeping distance from enemies tends to correlate with survival
- Aiming is a side effect of movement direction (no mouse aim — see [Controls](#controls-player-1)), so "shooting effectively" is entangled with "moving toward/away from the right spot"
- Pistol is always available (infinite ammo) as a fallback; other weapons come from pickups and ammo runs out (see [Fire Mechanics](#fire-mechanics))
- Enemy count increases per wave (see [Round Structure](#round-structure)) — the policy needs to generalize to handling more simultaneous enemies than it may see early in training
