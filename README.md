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
| `touchdesigner/engine.py` | Main engine. Runs every frame: layer stack, presets and their safe storage (`STORE`), set list, colours, text morph, 3D model animation, keyer, preset dips, thumbnails. |
| `touchdesigner/remote_cb.py` | Phone bridge. Builds the state the phone sees, verifies signed messages, handles uploads (images, video), and routes each command to the engine. |
| `touchdesigner/phonecam_cb.py`, `phonedraw_cb.py` | Callbacks for the phone camera feed and the phone drawing pad. |
| `touchdesigner/grid_inst.py` | Instancing helper for the grid effect. |
| `touchdesigner/remote_mqtt_cb.py` | MQTT transport callbacks used by the relay. |
| `touchdesigner/keys_cb.py` | Keyboard shortcuts (`fx_keys` Keyboard In DAT), including the failsafe show keys. |
| `touchdesigner/store_pex.py` | Buttons on the `CONTROLS → Safety` page (undo, restore, backup). |
| `touchdesigner/fx/*.glsl` | GLSL pixel shaders: one per visual effect (`neon`, `hologram`, `ascii`, `thermal`, ...), the source compositor (`src.glsl`), the green/blue screen keyer (`key.glsl`), and the text shader (`text.glsl`). |
| `thumbs/` | Static preview images used by the phone page. |

---

## How the pieces fit

1. **Presets.** A preset is a JSON snapshot of the whole look: layer stack and amounts, scene, grid, text
   (`Textstr`, font, colours, animation), statue/model, camera, source (camera, media, drawing, keyer), and colours.
   Presets are stored in `td/presets.json` (128 slots). See [How presets are saved](#how-presets-are-saved).
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

## How presets are saved

A VJ set must never lose its presets, so storage follows four rules:

1. **The disk file is the only truth.** `td/presets.json` holds every preset (effects, amounts, text and its colours,
   model, camera, source, keyer, effect colours). The `PRESETS` table inside the `.toe` is only a fast copy. Every
   time the engine starts, it fills the table from disk. An unsaved or older `.toe`, a crash, a different phone or a
   cleared browser cannot bring back old presets. (Before this rule, the table inside the `.toe` won, which is how
   edits were lost when TouchDesigner was closed without saving.)
2. **Writes cannot leave a broken file.** Each save writes a temp file, flushes it to disk, reads it back and checks it,
   then swaps it in. The previous file stays as `presets.json.bak`. A save takes about 20 ms.
3. **Every change is a restore point.** After each save, `td/history/` gets a file with the presets, the set list and
   the FX presets. The newest 400 are kept, plus the first one of every day. If `presets.json` is ever unreadable,
   the engine loads the newest good restore point, then the `.bak`. If the `.toe` held a different copy at start,
   that copy is archived in `td/history/` too (named `project-copy-…`), so nothing is thrown away.
4. **Failures are loud.** If a save fails, it is retried. If it still fails, every phone shows a red
   *PRESETS NOT SAVED* banner and `CONTROLS → Safety → Presets status` says why. The phone only shows
   *Saved ✓ on computer* after the computer confirms the file is on disk; with no answer in 6 seconds it warns you.

Each preset also names its own picture and drawing file (`td/thumbs/p<slot>_<time>.jpg`), so a picture can never
belong to a different preset, and restore points keep their pictures.

The phone stores nothing about presets. It keeps only screen preferences (tab, fade time, set list shown or
hidden, recent texts).

Log of everything the store does: `td/store_log.txt`.

---

## Failsafes (when the phone or the internet fails)

| Problem | What to do |
|---|---|
| **Internet or relay down** | Phone and computer on the same Wi-Fi: open the link in `CONTROLS → Safety → Wi-Fi link`. TouchDesigner serves the same page itself (port 9980), no internet needed. The phone's offline screen shows this link automatically once it has connected once. |
| **Phone dead or page broken** | Use the keyboard on the computer (TouchDesigner window focused): **PageDown / PageUp** = next / previous preset in the set list, **Shift + 1…9, 0** = preset slot 1…10, **B** = blackout on/off. A wireless presenter clicker (sends PageDown/PageUp, and B for "blank") works as a remote. |
| **Wrong change / deleted preset** | Phone: *Edit → ↺ Backups → Undo last preset change*, or pick a restore point. Computer: `CONTROLS → Safety → Undo last preset change`. Restoring first saves the current state as a restore point, so a restore can be undone too. |
| **Need a specific old version** | `CONTROLS → Safety → List restore points` prints a numbered list in the Textport. Set *Restore point #* and press *Restore that point*. Or *Open backups folder*. |
| **Edited `presets.json` by hand** | `CONTROLS → Safety → Reload presets from disk`. |

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
| `/project1/PRESETS` | Table DAT, 129 rows (row 0 header, rows 1–128 are slots). A copy of `td/presets.json`, refilled from disk at every start. |
| `/project1/store_pex` | Parameter Execute DAT on `CONTROLS`, parameters `Store*`, *On Pulse* on, synced to `store_pex.py`. |
| `/project1/fx_keys`, `/project1/fx_keys_callbacks` | Keyboard In DAT and its callbacks, synced to `keys_cb.py`. |
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
3. Open `/project1/CONTROLS` and set the **Master** page:
   - `Remotepass`: the password for the phone. Leave it empty for no password (not recommended).
   - `Remotekey`: created automatically the first time the engine runs.
4. Add a custom page **Safety** on `CONTROLS` with: `Storestatus` (string), `Storeundo`, `Storebackup`,
   `Storereload`, `Storelist`, `Storerestore`, `Storeopen` (pulses), `Storepick` (integer) and `Locallink` (string).

### 3. Folders

All data paths are relative to the folder of the `.toe` (`project.folder`): `td/` for presets, set list, colours,
history and pictures, `media/` for uploads, `web/` for the page TouchDesigner serves on Wi-Fi, and `3D objects/` for
models. Keep that layout and nothing needs editing.

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
const BUILD = '2026-11-07c';   // change this for every release
```

Then commit and push. GitHub Pages can cache for up to 10 minutes; add `?v=<anything>` to the URL to force a refresh.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Phone shows *offline* | The Pages URL or pairing key is wrong, or the relay is down. Check `RELAY` in `remote_cb.py`. |
| Red *PRESETS NOT SAVED* banner | The computer can't write `td/`. Check free disk space and that the folder isn't read-only or locked by a sync tool. Saving resumes on its own and the next save includes everything. |
| *Not confirmed* warning after saving | The phone got no answer. Check that TouchDesigner is running; the preset may still have saved (check the tile). |
| Preset shows the wrong text or picture | Hold the preset and press *Update* after changing it. To go back, use *Backups*. |
| Missing preview pictures | Call `captureThumbs()` in `engine.py` (from the Textport) to shoot them all again; the screen is put back afterwards. |
| Animated model stutters | Check the GPU load in TouchDesigner's Performance Monitor. Pre-baked frame sequences are faster than live Alembic. |
| Phone upload stalls | Long videos are sent in chunks. Keep the phone on Wi-Fi and the screen on until the upload finishes. |

---

## What is not included

- **The `.toe` project file.** It contains the pairing key and your saved presets. Recreate the network from the
  operator table above.
- **3D models and animations.** These are third-party downloads with their own licences. Put your own `.fbx`,
  `.abc`, `.usdz` or `.glb` files in `3D objects/` and register them in `anims.json`.
- **Presets, set list, colour files and restore points** (`presets.json`, `queue.json`, `lcols.json`, `history/`). They are personal data.
- **Backups** (`*_backup_v*.py`, `_backup_*` folders).

---

## Credits

Built by Gryva. Relay: HiveMQ public broker.
