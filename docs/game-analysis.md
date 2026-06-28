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
| Shoot | `/` |
| Next weapon | `.` |
| Prev weapon | `,` |
| Select weapon | `0–9` (single player only) |
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
- **Label:** Green text "Pistol" (or current weapon name) above the player
- **Position:** Anywhere on the canvas
- **Detection strategy:** Color segmentation (dark figure) + weapon label text

### Enemies — Zombies
- **Appearance:** Box-shaped figures, similar size to player, darker/grey tones
- **Behavior:** Walk toward the player, melee attack only (close range)
- **Detection strategy:** Color segmentation, shape matching

### Enemies — Devils (later waves)
- **Appearance:** Red box-shaped figures
- **Behavior:** Melee attack + ranged attack (yellow projectiles) — dangerous at any distance
- **Detection strategy:** Red color segmentation

### Score
- **Position:** Top-center of canvas
- **Format:** `000000003100` (zero-padded number)
- **Multiplier:** `x3` shown next to score when combo active

### Weapons
| Weapon | Type |
|---|---|
| Pistol | Ranged, always available |
| Uzi | Ranged, fast fire rate |
| Shotgun | Ranged, spread |
| Grenades | Area of effect |
| Barrels | Explosive, placeable |

### Objects / Pickups
- **Red boxes (crates):** Weapon pickups — scattered around map
- **Grey barrels:** Explosive barrels — can be used tactically
- **Detection strategy:** Template matching (fixed shapes, consistent colors)

### Map — Basic Arena (focus for v1)
- **Shape:** Square/rectangle, open arena with no obstacles inside
- **Background:** Beige/sand colored floor
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
| `game_playing.png` | Active gameplay with player + enemies visible | PlayerDetector, EnemyDetector |
| `game_player_only.png` | Player visible, no enemies nearby | PlayerDetector |
| `game_enemies_only.png` | Multiple enemies, no player in center | EnemyDetector |
| `game_objects.png` | Red crates and barrels visible | ObjectDetector |
| `game_menu.png` | Main menu screen | State detection |
| `game_canvas_crop.png` | Cropped canvas only (no browser chrome) | ROI calibration |

---

## Bot Strategy Notes

- **Movement:** Stay mobile, keep distance from enemies
- **Shooting:** Auto-aim toward nearest enemy (use angle/distance calculation)
- **Priority:** Shoot first, move away if enemy gets too close
- **Weapons:** Pistol always available, others from pickups
- **Wave progression:** More enemies per wave — bot must handle multiple simultaneous enemies
