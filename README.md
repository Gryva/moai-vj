# MOAI // VJ

A live audio-reactive VJ rig built in TouchDesigner, with a phone web page as the control surface.
The phone page is served from GitHub Pages; it talks to TouchDesigner through a public MQTT relay, so
phone and computer do not need to be on the same network.

```
Phone (GitHub Pages: index.html)  <-- MQTT relay (broker.hivemq.com) -->  TouchDesigner (td/*.py, fx/*.glsl)
```

This repository contains the **phone page** (`index.html`) and the **TouchDesigner scripts and shaders**
(`touchdesigner/`). It does not contain the `.toe` project file (see [What is not included](#what-is-not-included)).

---

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | The whole phone UI: one file, no build step. Served by GitHub Pages at `https://gryva.github.io/moai-vj/`. |
| `touchdesigner/engine.py` | Main engine. Runs every frame: layer stack, presets (`PRESETS` table), set list, colours, text morph, 3D model animation, keyer, preset dips, thumbnails. |
| `touchdesigner/remote_cb.py` | Phone bridge. Builds the state the phone sees, verifies signed messages, handles uploads (images, video), and routes each command to the engine. |
| `touchdesigner/phonecam_cb.py`, `phonedraw_cb.py` | Callbacks for the phone camera feed and the phone drawing pad. |
| `touchdesigner/grid_inst.py` | Instancing helper for the grid effect. |
| `touchdesigner/remote_mqtt_cb.py` | MQTT transport callbacks used by the relay. |
| `touchdesigner/fx/*.glsl` | GLSL pixel shaders: one per visual effect (`neon`, `hologram`, `ascii`, `thermal`, ...), the source compositor (`src.glsl`), the green/blue screen keyer (`key.glsl`), and the text shader (`text.glsl`). |
| `thumbs/` | Static preview images used by the phone page. |

---

## How the pieces fit

1. **Presets.** A preset is a JSON snapshot of the whole look: layer stack and amounts, scene, grid, text
   (`Textstr`, font, colours, animation), statue/model, camera, source (camera, media, drawing, keyer), and colours.
   Presets live in the `/project1/PRESETS` table (128 slots). Every save is also written to `td/presets.json`.
2. **Set list.** An ordered list of preset slots (`td/queue.json`). The phone shows it as a track with ◀ ▶ arrows.
   The next preset is pre-loaded in the background so the switch is instant.
3. **Colours.** Each effect, the text and the drawing have two colours (A, B) and a mode: solid, linear ramp
   or radial. Stored per effect in `td/lcols.json` and inside each preset.
4. **Text.** The text string and its style are part of the preset. Switching presets can morph the old words into
   the new ones (`textMorphStart`, shader `fx/text.glsl`).
5. **Models.** Static 3D models are imported from `3D objects/`. Animated models are FBX or Alembic files wired under
   `/project1/anims/`; `anims.json` lists them for the phone. Long Alembic clips are pre-baked to fixed frame counts
   so they play at full speed.
6. **Phone uploads.** Images and short videos are sent from the phone in chunks. Videos can be keyed (green or blue
   screen) and moved in 3D.
7. **Security.** Every phone message is signed with `sha256(relayKey + ':' + password)`. Messages are only accepted
   within a 120-second window, replays are rejected, and wrong passwords are rate-limited.

---

## Requirements

- Windows PC with a GPU (the scripts were developed on Windows)
- TouchDesigner 2025 (build 099 or later)
- Python packages available to TouchDesigner: `numpy` and `opencv-python` (`cv2`)
- A GitHub account (for GitHub Pages) if you want to host your own phone page
- Any phone with a modern browser

---

## Setup

### 1. Clone this repository

```
git clone https://github.com/Gryva/moai-vj.git
```

### 2. Build the TouchDesigner project

The `.toe` project is not in this repository. Recreate the network using the operator names below. The scripts look
operators up by these exact paths, so use them as written.

| Operator path | Role |
|---|---|
| `/project1/CONTROLS` | Base COMP with all custom parameters (Master, Text, Camfeed, Moai, Keyer, Remote). The scripts read and write these. |
| `/project1/fx_engine` | Execute DAT that runs `touchdesigner/engine.py` every frame (`Synced` to the file). |
| `/project1/remote_cb` | Text DAT (or Module) holding `remote_cb.py`. Used by `op('/project1/remote_cb').module`. |
| `/project1/remote_server` | Web/WebSocket server DAT that receives phone messages and passes them to `remote_cb`. |
| `/project1/PRESETS` | Table DAT, 129 rows (row 0 header, rows 1–128 are slots). Holds `name` and preset JSON. |
| `/project1/FX_STACK` | Table of the effect layers (key, label, on, amount, parameters). |
| `/project1/LOOKS` | Table of saved looks. |
| `/project1/fx_text`, `/project1/text_src`, `/project1/text_old` | Text shader and the two text sources used for morphing. |
| `/project1/xf_mix`, `/project1/xf_black` | Preset dip (fade out, switch at black, fade in). |
| `/project1/camsel`, `/project1/media_key`, `/project1/media_next` | Camera/media source switch, keyer, and the preloaded next media. |
| `/project1/moai_geo`, `/project1/img_geo`, `/project1/moai_particles` | Model and image geometry. |
| `/project1/anims/` | One sub-COMP per animated model (`a_skeleton`, `a_mushroom`, `a_steamboat`, `a_hibiscus`, `a_flower`, `a_orrery`). |
| `/project1/AUDIO/OUT`, `/project1/AUDIO/source` | Audio input and analysis (low, mid, high, kick). |
| `/project1/thumb_out` | The final output TOP that thumbnails are captured from. |
| `/project1/render1` | Render TOP of the whole scene. |

Then:

1. Put each `touchdesigner/*.py` file into a Text DAT (or the matching callback DAT) with the same name. Set the DAT
   to *Synced to file* so edits on disk reload automatically.
2. Put the shaders from `touchdesigner/fx/` into GLSL TOPs (one per effect) or Text DATs, matching the layer keys
   in `FX_STACK`.
3. Open `/project1/CONTROLS` and set the **Remote** page:
   - `Remotepass`: the password for the phone. Leave it empty for no password (not recommended).
   - `Remotekey`: created automatically the first time the engine runs.

### 3. Fix the paths for your machine

`engine.py` and `remote_cb.py` have hard-coded folders, for example:

```python
PRESETS_FILE = r'D:/Projects/Visuals/td/presets.json'
LOOKS_FILE   = r'D:/Projects/Visuals/td/looks.json'
THUMB_DIR    = project.folder + '/td/thumbs'
```

Change `D:/Projects/Visuals` to your project folder before running.

### 4. Host the phone page

1. Fork this repository on GitHub.
2. In the fork, go to **Settings → Pages**, choose *Deploy from a branch*, branch `main`, folder `/ (root)`.
3. Wait a minute, then open `https://<your-user>.github.io/<repo>/`.
4. In `remote_cb.py`, change `RELAY['page']` to your Pages URL. TouchDesigner shows the link with the pairing key in
   `CONTROLS → Remote → Phone link`.

### 5. Connect a phone

1. Open the link from TouchDesigner on the phone (it contains `#k=<key>`; keep the key private).
2. Enter the password from `Remotepass`.
3. You should see the preset grid, the set list, and the live status dot turn green.

---

## Using it

- **LIVE tab (perform mode):** tap a preset to load it. Hold a preset to edit it. The **Set list** button hides or
  shows the set list (remembered per phone).
- **Set list:** hold a preset to add it. Drag inside the track to reorder or remove. ◀ ▶ step through it.
- **Colours:** tap a colour box to open the picker. Choose solid, ramp or radial, then pick one of the 10 swatches
  or any colour.
- **Text:** type in the text box and press Enter. The text is saved with the preset when you press *Update*.
- **Video:** upload from the phone under *Source*. Choose green or blue screen to key it out, then move it in 3D.
- **New version:** the phone page checks for a new build every few seconds and shows *New version ready · tap to update*.

---

## Updating the phone page

Each change to `index.html` needs a new `BUILD` value, or phones will not show the update button:

```js
const BUILD = '2026-11-07b';   // change this for every release
```

Then commit and push. GitHub Pages can cache for up to 10 minutes; add `?v=<anything>` to the URL to force a refresh.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Phone shows *offline* | The Pages URL or pairing key is wrong, or the relay is down. Check `RELAY` in `remote_cb.py`. |
| Preset shows the wrong text or picture | The saved preset is what the phone and screen use. Hold the preset and press *Update* after changing it; the preview picture is only refreshed on save. |
| Preset highlight does not match the screen | The on-air slot is reported by the engine. Make sure `engine.py` is reloaded in TouchDesigner (the DAT is synced to disk), then reload the phone page. |
| Missing preview pictures | Pictures are saved as `td/thumbs/p<slot>.jpg`. Presets without a picture file show a blank tile. Call `captureThumbs()` in `engine.py` (from the Textport) to shoot them all again. |
| Animated model stutters | Check the GPU load in TouchDesigner's Performance Monitor. Pre-baked frame sequences are faster than live Alembic. |
| Phone upload stalls | Long videos are sent in chunks. Keep the phone on Wi-Fi and the screen on until the upload finishes. |

---

## What is not included

- **The `.toe` project file.** It contains the pairing key and your saved presets. Recreate the network from the
  operator table above.
- **3D models and animations.** These are third-party downloads with their own licences. Put your own `.fbx`,
  `.abc`, `.usdz` or `.glb` files in `3D objects/` and register them in `anims.json`.
- **Presets, set list and colour files** (`presets.json`, `queue.json`, `lcols.json`). They are personal data.
- **Backups** (`*_backup_v*.py`, `_backup_*` folders).

---

## Credits

Built by Gryva. Relay: HiveMQ public broker.
