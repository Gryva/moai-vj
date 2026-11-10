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
- **Quick controls:** hold the name of any slider, switch (ON/OFF) or effect setting (Amount / its setting in FX) and
  pin it **to the preset on air** or **to every preset**. LIVE then shows a foldable **Quick controls** card with just
  those, for changing a visual during the show. Each one only moves the layer it came from (Video 2's speed = Video 2
  only; an effect pinned while **All layers** is selected = the whole picture). Hold a quick control to move or unpin it.
  Live tweaks are not saved into the preset unless you Update it. Up to 12 per list.
- **Autopilot:** the AUTOPILOT button only turns it on / off. The small button next to it (e.g. "1s fade · 10s") opens the
  settings: **transition between presets** (used by your taps and by autopilot) and **change every** (10s–5m).
- **Groups:** hold a preset → **Group ▸** to put it in a group (or make a new one). On LIVE each group is a
  list you tap to fold / unfold; hold a group's header to rename or ungroup it. Every preset still plays with one tap,
  whatever group it is in. Groups are stored with the presets on the computer.
| ＋ tile, hold (edit) | Save what's on screen as a new preset. |
| ◻ tile (edit) | New clean preset (no effects, no text). |
| **AUTOPILOT** + 10s…5m | Under the fade buttons. Tap AUTOPILOT to switch on/off; tap a time for how long each preset stays. Random, but never the one on screen or the last 5. Uses the set list if it has 2+ presets, otherwise all presets. Tapping a preset restarts the timer. |
| **Set list** | Show or hide the set list (remembered on this phone). |
| **↺ Backups** (edit) | Undo the last preset change, make a restore point, or bring back any earlier one. |
| Set list track | ◀ ▶ step through it. Hold a preset tile to add it; hold a track item to move or remove it. |

"Saved ✓ on computer" appears only after the computer confirms the save is on disk. A red banner = the save failed.

### FX
- **Layers** card at the top, the same list as in SOURCE (with ▲ ▼), plus **ALL LAYERS** (effects over the whole
  picture). Tap a layer: it lights up and everything below now edits only that layer.
  A number on a chip = how many effects that layer has. Up to 4 layers can carry their own effects at once.
  Text layers can have their own effects too: they are drawn on their own, run through a chain and laid back on top.
- **Brightness** (per layer): below 1 fades the layer see-through, above 1 makes it brighter. Saved in presets.
- **Hold a layer** in the FX Layers card for its menu: **Edit its effects**, **Copy its effects**, **Paste effects of …
  here** (once something is copied) and **Remove all its effects**. Works with All layers too.
- **On air:** the chosen layer's effects, with amount, setting and colour. **CLEAR** clears only that layer.
- **Warp / Style / Post:** tap an effect to add it to the chosen layer. 15 in each group:
  - Warp: Melt, Liquid, Mirror, Kaleido, Tunnel, Zoom, Tile, Pixels, Pulse, Swirl, Ripple, Bulge, Wave, Polar, Shards.
  - Style: Thermal, Holo, Neon, Lines, Dots, ASCII, Hue, Matte, Colour, Toon, Duotone, Sketch, Emboss, Night vision, Oil paint.
  - Post: Glitch, Sort, Trails, Glow, VHS, RGB split, Film, CRT, Blocks, Flash, Cinema, Static, Punch, Shake, Strobe.
  - The tiles show the same statue (Antinous), same pose, whole statue in frame. To redo them after adding an effect, run
    `tools/fx_thumbs.py` inside TouchDesigner (it puts every setting back afterwards).
- **Colour** (supported effects): Own, Solid, Ramp or Radial. Colour A/B from 10 swatches or any colour; angle for gradients.
- Presets save every layer's effects. Older presets keep their effects on ALL, so they look the same.

### SOURCE
Source cards follow the Layers order (text first, then front to back); each has its own **ON/OFF**. A card opens when its source is ON; tap its header to fold it away (▴/▾). In the Layers card, **✕** switches that source off.
**NEW CLEAN PRESET** starts from nothing: every source off, no effects.

**Layers** (top of SOURCE) lists every layer you added, front to back. **▲ ▼** move it in front of / behind the
others, **✕** removes it, tap a name to jump to its card. **＋ ADD LAYER** adds Text, 3D models, an Image, a Video,
a Drawing or the Phone camera. A source's card only shows once it is added. Images, videos and drawings can be added
again and again: up to **6 picture / video / drawing layers** at once (e.g. three videos stacked, a background picture
under a green-screen clip, two drawings). Up to **3 text layers**, each with its own words, style, font and colour. Example: Text on top, a 3D model in the
middle, a picture at the back. The order is saved in presets.
**Linked layers (hot-switch):** hold a layer's name → **⇄ Link with…** and pick another layer. Only one of the pair is
on at a time; the **⇄** button on the row (or **Swap now** in the hold menu) turns one off and the other on. The
switched-off partner stays in the list, dimmed, marked *(off)*. **Pin swap to Quick controls** puts a one-tap swap button
on LIVE. **Switch** in the same menu picks how it changes: **Cut** (instant, the default) or a fade of 0.3–2 s. **Unlink** in the same menu; removing a linked layer (✕) unlinks it too. Links are saved in presets. Works for images, videos, drawings, text and 3D models
(not the phone camera). Pictures / videos in **3D OBJECT** mode are drawn by their
own 3D pass with the shared 3D camera, so they stay separate layers too (own order, effects and brightness). **Text** layers move with ▲ ▼ like the others: on top of everything they are drawn after the effects (all text effects work); behind another layer or in 3D they are drawn inside the stack (Mask, Cut-out, Invert and Refract then show as plain letters).

- **3D models:** shows or hides the statues and animations.
  - Static models / 3D animations: tap to switch. **Scene** (Solid, Particles, Grid) sits under Static models;
    animations always play solid.
  - Loop / Bounce (under animations), animation speed, speed-up on the beat. Remembered per animation.
  - **Object motion** (moves the object, never the camera): Spin, Bob, Sway, Float, Still; amount, tilt, angle, spin
    speed, bass boost. With Spin: **SPINNING** on/off, **⟲ REVERSE**, axis Y / X / Z. Applies to models, animations,
    3D-object pictures/videos and drawings.
  - Swap animation: Scale, Spin, Drop or Cut when changing models, and its time.
- **Phone camera:** NORMAL, BLEND or MASK, Fill / Whole image, mirror. **Clips:** record a short loop; play, bounce,
  speed, delete (a playing clip is the camera layer).
- **Image / Video layers** (one card each, named Image 1, Video 2…): ON/OFF, ＋ ADD (upload to this layer), the
  current file (tap **CHANGE** to open the library and pick another), **Playback** for videos (speed 0.1–4×, trim
  start / end, reset), **FLAT** or **3D OBJECT** (placed in VIEW), **Crop** and **Green / blue screen**. Each layer also has its own effects and brightness (FX tab) and framing (VIEW tab). All saved
  in presets; older presets load their image on layer 1 and their video on layer 2.
- **Drawing layers:** draw on the phone; pen and shapes, sizes, colours or gradients. Black is see-through. With several
  drawings, **✎ DRAW ON THIS LAYER** moves the pad to that drawing. Like pictures they can be flat or a 3D object and
  have their own effects, brightness and framing. Saved in presets.
- **Text:** type and press Enter. **Position:** nine spots of the frame (corners, edges, centre) plus Fill, Stack and
  Lower third, and **Left / right**, **Down / up** sliders to nudge it anywhere. **Direction:** horizontal, vertical
  (letters stacked) or sideways ↑ / ↓. **Animations:** static, beat, breathe, wave, scroll, tile, bounce, shake, flicker,
  type, word per beat; scroll, wave, tile and bounce also take a direction (left, right, up, down). **Space:** FLAT or
  **3D** (the words on a card in the 3D scene: 3D camera, Object motion, and a 3D depth slider). Modes (overlay, mask,
  cutout, invert, outline, glitch, refract), font, size, glow, speed, beat reaction, colour (solid, ramp, radial). **Pin** keeps text when presets change. Recent texts are
  one tap away. Text is saved with a preset when you press **Update**.

### VIEW
- **Layers** card at the top, same as in SOURCE. Tap a flat layer (Phone camera, Images, Videos) to frame it. Tap
  any 3D layer (3D models, a 3D picture / video / drawing, 3D text) to place just that layer in the scene: left / right,
  up / down, depth, size, turn, tilt, RESET PLACEMENT (saved in presets). Tap **3D camera** (top row) for the camera
  that films every 3D layer.
- 3D camera (models and 3D objects): saved views (F1–F8), orbit, elevation, distance, lens, roll, height and pan,
  handheld shake. A saved view stores only the camera. Views marked **↻ camera moves** (e.g. Slow Orbit, Top Spiral,
  Chaos Club) keep the camera circling or swaying, which can look like the object spinning; that is the camera, not
  Object motion. **Camera circles the scene** / **Camera sways around** are the sliders that do it. On the preview: drag = orbit, pinch = zoom, two fingers = pan, flick = keep spinning.
  Object movement (spin, bob…) lives in SOURCE → 3D models.
- Flat layer: **zoom, left/right, up/down, rotate** just for that layer, **RESET FRAMING**. Saved in presets.

### AUDIO
Input gain, noise gate, dynamic range, smoothing, beat sensitivity, beat feel (punchy ↔ smooth), flash safety,
headphone monitor and volume. Meters show low, mid, high, kick.

### TUNE
Camera sway (orbit, elevation, push/pull, roll, sway speed), audio → camera, kick push-in, kick jolt, preset glide
time, response, flick inertia, brightness, blackout fade, and **Autopilot: new preset every (s)**.

**Updates:** when a new version is published, the phone shows **New version ready · tap to update**.

---

### SOURCE tidy-ups

- Tap a layer in the Layers list: it lights up green, its card opens and every other card folds, so there is no scrolling
  past settings you don't need. Cards can still be opened by tapping their header.
- In the 3D models card, Static models and 3D animations start folded.
- **Drawing:** tools Pen, Line, Circle, Box, Triangle, Star, Heart, Arrow; sizes S / M / L / XL; shapes Outline or Filled;
  pen colour; Undo / Clear all. **⛶ FULL SCREEN** on the pad gives the whole screen to the drawing (tools beside it on
  a tablet held sideways, under it when upright; **☰ TOOLS** hides them for the full width); **✓ DONE** goes back to
  the card. The pad draws at twice the old resolution, so edges are smooth.

### Object motion for 3D pictures, videos, drawings and text

When a picture, video or drawing is set to **3D OBJECT** (or a text layer to **3D**), its card shows **Object motion**:
**LIKE 3D MODELS** (follows the models' motion, the default), or its own **SPIN** (axis Y / X / Z, ⟲ REV, spin speed),
**BOB**, **SWAY**, **FLOAT** (amount) or **STILL**. Saved in presets; older presets keep following the models.

### LIVE on a tablet

From 900 px wide the presets take three quarters of the screen; the right quarter shows, top to bottom, the **Set list**,
**Autopilot** + fade, a slim **on air** strip (thumbnail + name) and **Quick controls**. Drag the divider between the
columns to resize them (double-tap it to reset; remembered on that device). Phones keep the single column.

### Saved views (VIEW)

16 views, each with a small drawing of how the camera moves: the ring is the orbit, the green dot is the camera, arrows
show circling, swinging, rising / falling, pushing in / out, tilting or shaking. New: Dolly Zoom, Pendulum, Crane,
Bird's Eye, Worm's Eye, Fast Orbit, Close-up, Dutch Tilt. F1–F8 on the keyboard still load the first eight.

### Layer names

Hold a layer in SOURCE → type a name → **✎ Save name** (or **Default name** to go back to "Video 2" etc.). The name is
used everywhere: Layers lists, FX, VIEW, quick controls, link menus. Saved in presets. Quick controls of a layer the
preset on air doesn't have are hidden.

### Saving

- In edit mode the header has **SAVE**: what is on screen goes into the preset that is on air (same name). With no preset
  on air it becomes a new preset at the end. Holding a preset → Update still works.
- **NEW CLEAN PRESET** always lands at the end of the list.

### Tablets and wide screens

From 900 px wide (a tablet held sideways, a laptop) SOURCE, FX, VIEW and OUTPUT use two columns: the Layers list stays
on the left while the settings scroll on the right (in FX the effect library stays visible on the right). A **scroll
rail** runs down the screen edge: drag it to scroll without touching any slider. TUNE → **Scroll rail**: left, right
or off (remembered on that device).

### OUTPUT (projector)

- **⛶ FULL SCREEN OUTPUT** opens the picture full screen, borderless, on the chosen **Screen** (1 = the computer's main
  screen, 2 = usually the projector). Tap again to close it. TouchDesigner's perform window closes when it opens, so the
  picture is never shown twice.
- **Keystone:** drag the four coloured corners on the pad until the picture sits square on the wall; tap a corner and
  use ◀ ▲ ▼ ▶ to nudge it (**FINE** / **BIG** steps). **Test: GRID OVER / GRID ONLY** projects an alignment grid with
  a circle (round when the shape is right) and the same coloured corners.
- **FLIP ↔** for rear projection, **FLIP ↕** for a ceiling mount (both = upside down), **RESET CORNERS**.
- **Position:** size, move, rotate, soft edges. **Picture:** brightness, black level, gamma (for the projector only;
  the phone thumbnails stay unwarped).
- Saved on the computer in `td/projector.json`, not in presets, so the setup stays put when you change looks.
- The warp runs after OUT (`kst_warp`, `td/fx/keystone.glsl`) and feeds `out1` and the projector window. With the
  non-commercial licence the warped picture is 1280 px wide and the window scales it to the screen.

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
