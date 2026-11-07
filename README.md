# MOAI // VJ

A live, audio-reactive VJ rig built in TouchDesigner, controlled from a phone web page.

```
Phone page (GitHub Pages, or the computer's own Wi-Fi page)
        │  signed messages
        ▼
MQTT relay (broker.hivemq.com)  ── or direct Wi-Fi WebSocket (port 9980)
        │
        ▼
TouchDesigner: engine.py (every frame) + remote_cb.py (phone bridge) + GLSL effects
```

This repo holds the phone page (`index.html`), the TouchDesigner scripts and shaders (`touchdesigner/`), the model
converter (`tools/`) and model thumbnails (`thumbs/`). The `.toe` project, presets and 3D model files are not
included (see [What is not in this repo](#what-is-not-in-this-repo)).

**Contents**
1. [Quick start](#1-quick-start)
2. [Phone controls](#2-phone-controls)
3. [Computer controls (failsafes)](#3-computer-controls-failsafes)
4. [How presets are saved](#4-how-presets-are-saved)
5. [Adding your own 3D models and animations](#5-adding-your-own-3d-models-and-animations)
6. [Adding media, effects and other content](#6-adding-media-effects-and-other-content)
7. [Troubleshooting](#7-troubleshooting)
8. [Setting it up from scratch](#8-setting-it-up-from-scratch)
9. [Files and folders](#9-files-and-folders)

---

## 1. Quick start

1. Open the newest `NewProject.<n>.toe` in TouchDesigner.
2. Press **F1** for perform mode (or drag the output window to the projector).
3. On the phone, open the link from `CONTROLS → Master → Phone link` (it carries your private pairing key after `#k=`).
4. Enter the password (`CONTROLS → Master → Remotepass`).
5. Green dot = connected. Tap a preset.

**No internet?** Put the phone on the same Wi-Fi as the computer and open `CONTROLS → Safety → Wi-Fi link`.
The phone's offline screen shows this link automatically once it has connected once.

---

## 2. Phone controls

**Header:** status dot (green = live), fps, **✎ EDIT**, **BLACKOUT**.
Friends see the simple view (presets, set list, blackout). **✎ EDIT** unlocks all tabs.

### LIVE
| Control | What it does |
|---|---|
| CUT / 0.5s / 1s / 2s / 4s | How long switching to a preset takes. |
| Preset tile, tap | Loads it: effects, text, model, camera, source, colours. The number is its slot. **ON AIR** = on screen. |
| Preset tile, hold | Friends: add to set list or play. Edit mode: **Update** (save what's on screen), rename, delete, add to set list, copy its effects. |
| ＋ tile, hold (edit) | Save what's on screen as a new preset. |
| ◻ tile (edit) | New clean preset (no effects, no text). |
| **AUTOPILOT** + 10s…5m | Under the fade buttons. Tap AUTOPILOT to switch on/off; tap a time for how long each preset stays. Random, but never the one on screen or the last 5. Uses the set list if it has 2+ presets, otherwise all presets. Tapping a preset restarts the timer. |
| **Set list** | Show or hide the set list (remembered on this phone). |
| **↺ Backups** (edit) | Undo the last preset change, make a restore point, or bring back any earlier one. |
| Set list track | ◀ ▶ step through it. Hold a preset tile to add it; hold a track item to move or remove it. |

"Saved ✓ on computer" appears only after the computer confirms the save is on disk. A red banner = the save failed.

### FX
- **FX presets:** tap = apply that effect stack to what's on screen, hold = rename or delete, ＋ = save the current stack.
- **On air:** effects currently on. **CLEAR ALL** turns them off.
- **Warp / Style / Post:** tap an effect to turn it on; each has an amount and its own setting.
- **Colour** (supported effects): Own, Solid, Ramp or Radial. Colour A/B from 10 swatches or any colour; angle for gradients.

### SOURCE
- **Static models / 3D animations:** tap to switch.
- **Loop / Bounce** (under animations): Loop restarts from the beginning. Bounce plays forward then backward, for clips
  whose end doesn't match the start. Remembered per animation. Plus animation speed and speed-up on the beat.
- **Scene:** Solid, Particles, Grid (copies, depth, spacing, bass wave, spin offset).
- **Motion:** Spin, Bob, Sway, Float, Still; amount, tilt, angle, spin speed, bass spin boost.
- **Spin axis:** SPIN ↻ Y (turn), TUMBLE X, ROLL Z. **⟲ REVERSE** (VIEW tab, next to Auto spin) flips the direction. Both apply to statues, animations, pictures/videos in Object mode and drawings, and are saved in presets.
- **Swap animation:** Scale, Spin, Drop or Cut when changing models, and its time.
- **Camera feed:** phone camera as a source (Off, Cam, Behind, Blend, Mask), Fill / Whole image, mirror.
- **Clips:** record a short loop from the phone camera; play, bounce, speed, delete.
- **Media:** upload images or videos. Flat (fills the screen) or Object (a card in the 3D scene).
- **Green / blue screen:** key out a video's background (tolerance, softness, spill, edge shrink).
- **Move it in 3D:** left/right, up/down, size. **Fit** puts it back to full screen.
- **Drawing:** draw on the phone; it appears as a 3D card in the scene (orbits, spins and follows the camera like a model). Pen and shapes, sizes, colours or gradients. An Object-mode picture/video takes priority.

### TEXT
Type and press Enter. Layouts (centre, fill, stack, lower third, corner), animations (static, beat, wave, scroll,
tile, type, word per beat), modes (overlay, mask, cutout, invert, outline, glitch, refract), font, size, glow, speed,
beat reaction, colour (solid, ramp, radial). **TEXT ON/OFF**; **Pin** keeps text when presets change. Recent texts
are one tap away. Text is saved with a preset when you press **Update**.

### VIEW
Camera: saved views (F1–F8), orbit, elevation, distance, lens, roll, height and pan, handheld shake.
On the preview: drag = orbit, pinch = zoom, two fingers = pan, flick = keep spinning.

### AUDIO
Input gain, noise gate, dynamic range, smoothing, beat sensitivity, beat feel (punchy ↔ smooth), flash safety,
headphone monitor and volume. Meters show low, mid, high, kick.

### TUNE
Camera sway (orbit, elevation, push/pull, roll, sway speed), audio → camera, kick push-in, kick jolt, preset glide
time, response, flick inertia, brightness, blackout fade, and **Autopilot: new preset every (s)**.

**Updates:** when a new version is published, the phone shows **New version ready · tap to update**.

---

## 3. Computer controls (failsafes)

Work with the TouchDesigner window focused, no phone needed.

| Key | Action |
|---|---|
| **PageDown / PageUp** | Next / previous preset in the set list (a wireless presenter clicker sends these) |
| **Shift + 1…9, 0** | Load preset slot 1…10 |
| **B** | Blackout on/off (the clicker's "blank" button) |
| **P** | Autopilot on/off |
| 1…9, 0 / C | Toggle effect 1…10 / clear all effects |
| M / N, Ctrl + 1…9 | Next / previous model, model by number |
| A D / W S / Q E / Z X | Orbit / elevation / distance / lens |
| ← → / ↑ ↓ | Spin speed / tilt |
| , . / [ ] / + − | Angle / roll / zoom |
| F | Centre the camera |
| F1…F8, Shift + F1…F8 | Load / save a camera view |
| Space | Auto spin on/off |

**`CONTROLS → Safety`:** presets status, Undo last preset change, Make restore point now, Reload presets from disk,
List restore points (printed in the Textport), Restore point # + Restore that point, Open backups folder, Wi-Fi link.

---

## 4. How presets are saved

1. **The disk file is the only truth.** `td/presets.json` holds every preset. The table inside the `.toe` is a fast
   copy, refilled from disk every time TouchDesigner starts, so an unsaved or older project can never bring back
   old presets. The phone stores nothing about presets.
2. **Saves can't leave a broken file:** temp file → flush → read back and check → swap. The previous file stays as `.bak`.
3. **Every change is a restore point** in `td/history/` (presets + set list + FX presets). The newest 400 are kept,
   plus the first of every day. If `presets.json` is unreadable, the newest good restore point is loaded.
4. **Failures are loud:** a red banner on every phone and `CONTROLS → Safety → Presets status`.

The same safe saving covers the set list, effect colours, FX presets, camera views, the animation list and clip info.
Everything is logged in `td/store_log.txt`.

**Long sets:** each part of the per-frame engine is isolated (one failure can't freeze the picture), the shader clock
wraps every 20 minutes (no precision drift after hours), feedback effects reject bad pixel values, and a watchdog
reconnects any dropped phone relay within ~15 seconds.

---

## 5. Adding your own 3D models and animations

Models are normalised to **2 units on their longest side, centred on the origin, Y up, front facing +Z**.
Keep to that and they fit the camera and every effect.

### 5a. Automatic: the converter (recommended)

`tools/convert.py` runs Blender's Python module: fixes textures, normalises size, measures whether an animation
loops cleanly, and writes files TouchDesigner reads well. Inputs: `.fbx`, `.gltf/.glb`, `.blend`, `.dae`, `.usdz`, `.obj`.

One-time setup:
```
pip install uv
uv venv -p 3.11 bpyenv
bpyenv\Scripts\pip install bpy==4.2.0        (Mac/Linux: bpyenv/bin/pip)
```
Edit the folder paths at the top of `tools/run.py`, add a line per model to `tools/jobs.json`, run `python tools/run.py <name>`:
```json
{"name":"duck", "kind":"static", "src":"duck/source/rubber duck.fbx", "texdir":"duck", "tex":{"*":"Duck_Diffuse.png"}, "label":"Rubber Duck"}
{"name":"alien", "kind":"anim", "src":"alien/source/Arms Hip Hop Dance.fbx", "texdir":"alien", "label":"Dancing Alien"}
```
- `static` → `<name>.obj` + `<name>.jpg` (several materials get baked into one picture).
- `anim` → `<name>.fbx` (animation baked, textures embedded as PNG) + `<name>.json` (length, suggested loop/bounce).
- `tex` → which picture goes on which material (`"*"` = all). Only needed when the file doesn't link its own.

Then follow 5b or 5c from step 2.

### 5b. Static model

1. **Files:** `3D objects/_library/<name>/<name>.obj` + `<name>.jpg` (max 1024 px). By hand in Blender: one object,
   one material with one texture, longest side 2, apply transforms, Export → Wavefront OBJ, **Forward −Z, Up Y**, UVs + normals on.
2. **Geometry:** in `/project1/moai_geo` copy `m_moai` → rename `m_<name>`, set File, connect to the next free input of
   `model_switch`. Same in `/project1/moai_particles`.
3. **Texture:** in `/project1` copy `tex_moai` → rename `tex_<name>`, set File, connect to `model_tex`.
   Models are matched to geometry and texture **by name**, so input order doesn't matter.
4. **Menu:** in the Textport:
   ```python
   C = op('/project1/CONTROLS')
   for p in ('Model', 'Modelshown'):
       C.par[p].menuNames  = list(C.par[p].menuNames)  + ['<name>']
       C.par[p].menuLabels = list(C.par[p].menuLabels) + ['<Label>']
   ```
5. **Thumbnail:** 240×240 `<name>.jpg` in `web/thumbs/` (Wi-Fi page) and `thumbs/` in this repo (GitHub page).
6. **Ctrl+S.** Reconnect the phone; it's under **Static models**. Works with Particles and Grid too.

### 5c. Animation

1. **File:** `3D objects/_anim/<name>/<name>.fbx` with baked animation. Embed textures as **PNG** (TouchDesigner can't
   read JPEGs embedded in FBX). Alembic `.abc` also works (see Flower Loop).
2. **Import:** in `/project1/anims` add an **FBX COMP** named `a_<name>`, set File, press **Import**, turn Render off
   (the engine turns on the one in use).
3. **Size:** if far too big/small, set Pre-Transform → Uniform Scale (aim for about 2 units).
4. **Register** in `3D objects/_anim/anims.json`:
   ```json
   {"name": "<name>", "label": "<Label>", "kind": "fbx", "loop": "loop"}
   ```
   `loop` = `"loop"` or `"bounce"` (changeable on the phone). Alembic: `"kind": "abc", "dur": <seconds>`.
5. **Menu:** add `anim_<name>` / `<Label>` (code in 5b step 4).
6. **Thumbnail:** `anim_<name>.jpg` in `web/thumbs/` and `thumbs/`.
7. **Ctrl+S.** The engine reads the clip length from the file and drives it with the shared clock, so speed, beat
   push and Loop/Bounce work automatically.

**If it looks wrong:** black/white blobs → the engine makes fully transparent materials solid on first use; if colours
are still wrong, assign your own `phongMAT`s. Nothing moves → the file's animation may be empty (check in Blender).
Slow → fewer separate parts, 1024 px textures.

---

## 6. Adding media, effects and other content

- **Pictures/videos:** drop into `videos/` or `media/` in the project folder (MP4, MOV, WEBM, AVI, MKV, GIF, JPG, PNG…), or upload from the phone. They appear under SOURCE → Media on the next phone connect (the newest 80). The first time, preview pictures take a few seconds per new file.
- **Fonts:** any installed font name works in `CONTROLS → Text → Textfont`.
- **Effects:** shader `td/fx/<key>.glsl` + GLSL TOP `fx_<key>` + a row in `/project1/FX_STACK` (key, label, group, on,
  amount, setting name/min/max/step). Uniforms: `uTime`, `uAudio` (low, mid, high, kick), `uMix` (amount), `uP`
  (setting); colour effects also get `uCA`/`uCB`.
- **Preset pictures:** re-shoot all with `op('/project1/fx_engine').module.captureThumbs()` (screen restored after).

---

## 7. Troubleshooting

| Symptom | What to do |
|---|---|
| Phone *offline* | TouchDesigner open and online? Try the Wi-Fi link. |
| "Wrong password" | Check `Remotepass`. (A wrong phone clock is corrected automatically.) |
| Red *PRESETS NOT SAVED* | `td/` can't be written: disk full, read-only, or locked by a sync tool. Resumes on its own. |
| *Not confirmed* after saving | The computer didn't answer. Check TouchDesigner; the preset may still have saved. |
| Wrong / lost preset | Phone: Edit → ↺ Backups → Undo or a restore point. Computer: `CONTROLS → Safety`. |
| Model has wrong texture | `m_<name>` and `tex_<name>` must match the menu name. |
| Missing preview picture | Hold the preset → Update, or run `captureThumbs()`. |
| Stutter | Frame time in `/project1/perf` should stay under 16 ms. Rubik's Cube is the heaviest model (~15 ms). |
| Projector blank | F1 for perform mode; output is `/project1/out1`. |
| Something off after hours | Open `td/store_log.txt`: every 10 min a `health:` line shows fps, frame time, GPU memory, relays (1 = connected) and any errors. Errors in one part never stop the rest from drawing. |

---

## 8. Setting it up from scratch

Requirements: Windows PC with a GPU, TouchDesigner 2025 (build 099+), `numpy` + `opencv-python` for TouchDesigner,
any modern phone browser.

1. `git clone https://github.com/Gryva/moai-vj.git`
2. Recreate the network with these names (the scripts use them exactly):

| Operator | Role |
|---|---|
| `/project1/CONTROLS` | Base COMP with all custom parameters (Master, Moai, Model, Text, Camfeed, Audio, Camera, Safety…). |
| `/project1/fx_engine` | Execute DAT synced to `td/engine.py`, Frame Start on. |
| `/project1/remote_server` + `remote_cb` | Web Server DAT (port 9980) with callbacks synced to `td/remote_cb.py`. |
| `/project1/remote_mqtt`, `2`, `3` | MQTT Client DATs (relay), callbacks `remote_mqtt_cb`. |
| `/project1/fx_keys` + `fx_keys_callbacks` | Keyboard In DAT, callbacks synced to `td/keys_cb.py`. |
| `/project1/store_pex` | Parameter Execute DAT on `CONTROLS`, pars `Store*`, On Pulse, synced to `td/store_pex.py`. |
| `PRESETS`, `FX_STACK`, `LOOKS`, `CAM_PRESETS` | Tables (PRESETS is refilled from disk at start). |
| `moai_geo`, `moai_particles` | `m_<name>` File In SOPs → `model_switch` → `fix_axes` → `orient`. |
| `model_tex` | Switch TOP of `tex_<name>` textures. |
| `anims/a_<name>` | One FBX COMP (or Geometry COMP with Alembic) per animation. |
| `render1` → effects → `xf_mix` → `OUT` → `out1` | Render, effects, preset dip, output. |
| `fx_text`, `text_src`, `text_old` | Text shader + the two text sources for morphing. |
| `AUDIO` | Audio in, analysis (`OUT`: low, mid, high, level, kick), headphone monitor. |
| `thumb_out` | Small copy of the output for preset pictures. |

3. `CONTROLS → Master`: set `Remotepass`; `Remotekey` is created on first run.
4. Phone page: fork this repo, *Settings → Pages → Deploy from branch `main`, root*, put your URL in `RELAY['page']`
   in `remote_cb.py`.
5. Every change to `index.html` needs a new `const BUILD = '…'` so phones offer the update.

All data paths are relative to the project folder.

---

## 9. Files and folders

**In this repo**

| Path | What |
|---|---|
| `index.html` | The whole phone page. |
| `thumbs/` | Model thumbnails (GitHub page). |
| `touchdesigner/engine.py` | Engine: layers, presets + safe storage, set list, colours, text, models, animation clock, camera. |
| `touchdesigner/remote_cb.py` | Phone bridge: state, signed messages, uploads, clips, media. |
| `touchdesigner/keys_cb.py`, `store_pex.py` | Keyboard shortcuts, Safety buttons. |
| `touchdesigner/fx/*.glsl` | Effect shaders, source compositor, keyer, text. |
| `tools/` | Model converter (section 5a). |

**On the computer**

| Path | What |
|---|---|
| `td/presets.json`, `.bak`, `history/` | Presets and restore points. |
| `td/queue.json`, `lcols.json`, `fxpresets.json`, `cam_presets.json` | Set list, colours, FX presets, camera views. |
| `td/thumbs/`, `drawings/`, `clips/`, `store_log.txt` | Preset pictures, drawings, camera clips, storage log. |
| `media/` | Pictures and videos (`uploads/` from phones). |
| `3D objects/_library/`, `_anim/` | Static models (`library.json`), animations (`anims.json`). |
| `web/` | Page the computer serves on Wi-Fi. |

## What is not in this repo

- The `.toe` project (contains your pairing key and password).
- Presets, set list, colours, restore points, media (personal data).
- 3D model files (third-party downloads with their own licences).

Built by Gryva. Relay: HiveMQ public broker. Models converted with Blender.
