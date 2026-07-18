# 🍉 Fruit Ninja — Hand Controlled

Fruit Ninja you play with your hand. No mouse, no keyboard — a webcam tracks your index finger in real time and turns it into a blade.

Built with Python, OpenCV, MediaPipe and Pygame.

<!-- Add a demo GIF or video here — this project is worth seeing in motion.
![demo](assets/demo.gif)
-->

---

## Features

- **Real-time hand tracking** — MediaPipe follows your index finger; the blade follows you
- **Gesture controls** — open palm to pause, hover to click. The menus never need a mouse
- **Two modes** — Classic (3 lives) and Survival (one mistake and you're done)
- **Mouse fallback** — no webcam? Hold left click and swipe
- **Physics** — sliced fruit splits into halves that fly apart, spin, and fall
- **Audio & VFX** — splash effects colored per fruit, explosions, combo sounds, dynamic music

---

## Why it was harder than it looks

**The jitter/lag tradeoff.** Raw hand-tracking coordinates shake constantly — your finger is never truly still. Smoothing kills the jitter but adds lag, and lag is fatal in a game built on fast swipes. The fix was *adaptive* smoothing: filter heavily when the hand is slow, barely at all when it moves fast. Steady when you need steady, instant when you need instant.

```python
dist = math.hypot(raw_x - self.prev_x, raw_y - self.prev_y)
self.alpha = 0.8 if dist > 30 else 0.2   # fast hand -> trust the raw signal
```

**Tunneling.** At 60 FPS a fast hand can cross an entire fruit between two frames. Point-based collision misses it completely — the blade passes straight through and nothing happens. So the game tests the blade's *swept path* as a capsule (a thick line segment) against each fruit's circle. Nothing slips by.

**Blocking I/O.** `cv2.VideoCapture.read()` blocks. Called from the game loop, it stutters everything. The webcam runs on its own thread and the game just grabs the latest frame.

---

## Install

```bash
git clone https://github.com/kianbarkhordarii/fruit-ninja-hand-controlled.git
cd fruit-ninja-hand-controlled
pip install -r requirements.txt
python main.py
```

Python 3.8+ and a webcam (optional — mouse mode works without one).

---

## Controls

| Action | Hand | Mouse |
| --- | --- | --- |
| Slice | Swipe your index finger | Hold left click and drag |
| Navigate menus | Hover over a button for 1s | Click |
| Pause | Open palm | `ESC` |
| Quit | — | `Q` |

---

## Project structure

| File | Role |
| --- | --- |
| `main.py` | Game loop, scene flow, wiring |
| `sensors.py` | Threaded webcam capture + hand tracking with adaptive smoothing |
| `hand_tracker.py` | Standalone MediaPipe tracker (EMA smoothing) |
| `input_manager.py` | Input abstraction — mouse and hand behind one interface |
| `game_objects.py` | Blade, Fruit, Bomb, SlicedFruit, Explosion, SplashEffect |
| `physics.py` | Capsule–circle collision math |
| `game_engine.py` | Game modes (Classic / Survival) and scoring rules |
| `ui_manager.py` | Buttons, scenes, menus |
| `menu_cursor.py` | Dwell-to-click cursor for hand navigation |
| `audio_manager.py` | Sound effects and music |
| `convert_audio.py` | One-time utility: `.m4a` → `.wav` |

---

## How it works

```
webcam (thread) ──> MediaPipe ──> adaptive smoothing ──> (x, y, velocity)
                                                              │
                                                              ▼
                                          blade trail ──> capsule collision
                                                              │
                                                              ▼
                                              slice / bomb / miss ──> game mode
```

Input is abstracted behind `InputProvider`, so mouse and hand are interchangeable — the game loop doesn't know or care which one is feeding it.

A slice only registers above a minimum velocity. Resting your finger on a fruit does nothing; you have to actually swipe.

---

## Notes

- `cv2.CAP_DSHOW` is used for the capture backend — required on Windows, may need adjusting on Linux/macOS
- Assets go in `assets/` (`fruits/`, `vfx/`, `audio/`, `ui/`, `background/`). Missing assets fall back to drawn shapes, so it runs either way
- Audio loading matches on filename keywords (`splat`, `combo`, `bomb`, ...)

---

## License

MIT
