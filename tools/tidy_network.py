# Tidy /project1: group operators into labelled boxes. Moves nodes only (names and wiring unchanged).
# Run inside TouchDesigner: g = {"op": op, "annotateCOMP": annotateCOMP, "DRY": False}; exec(open(path).read(), g)  (delete the old annotate boxes first)
import re
P = op('/project1')
ALL = {c.name: c for c in P.children}
used = set()

def walk(start, prefix):
    seq = [start]; cur = ALL[start]
    while True:
        nxt = [o for o in cur.outputs if o.name.startswith(prefix) and o.inputs and o.inputs[0] == cur
               and o.name not in seq and not o.name.endswith('_fb')]
        if not nxt: break
        cur = nxt[0]; seq.append(cur.name)
    return seq

def ex(names): return [n for n in names if n in ALL]
def chunk(l, k): return [l[i:i + k] for i in range(0, len(l), k)]

grp = []
grp.append(('CONTROL + LOGIC', 'CONTROLS = every setting  ·  fx_engine runs each frame (td/engine.py)  ·  presets, looks, keyboard', [
    ex(['CONTROLS', 'fx_engine', 'store_pex', 'model_buttons', 'cam_preset_buttons']),
    ex(['FX_STACK', 'LOOKS', 'PRESETS', 'CAM_PRESETS', 'AUDIO']),
    ex(['fx_keys', 'fx_keys_callbacks', 'perf', 'flash_log', 'flash_probe', 'flash_avg'])]))
grp.append(('PHONE REMOTE', 'web server :9980 + MQTT relay (remote_cb = td/remote_cb.py)  ·  phone camera + drawing feeds', [
    ex(['remote_server', 'remote_cb', 'remote_mqtt', 'remote_mqtt_cb', 'remote_mqtt_callbacks']),
    ex(['remote_mqtt2', 'remote_mqtt2_callbacks', 'remote_mqtt3', 'remote_mqtt3_callbacks']),
    ex(['phonecam', 'phonecam_cb', 'phonecam_callbacks', 'camsel']),
    ex(['phonedraw', 'phonedraw_cb', 'phonedraw_callbacks', 'drawslot_cb'])]))
sh = sorted(n for n in ALL if n.startswith('fxsrc_'))
other = sorted(n for n in ALL if re.match(r'(txa\d|txcomp|media_key\d)_(pixel|compute|info)$', n) or n in ('txalpha_src', 'txcomp_src'))
grp.append(('SHADER CODE', 'GLSL text DATs synced to td/fx/*.glsl  (edit the files, not these)', chunk(sh, 8) + chunk(other, 8)))
tex = sorted(n for n in ALL if n.startswith('tex_'))
grp.append(('3D SCENE', 'models, animations, textures, camera + lights  ·  render1 = the models pass', [
    ex(['cam', 'thumbcam', 'ambient', 'key_light', 'fill_light', 'render1', 'anim_thumb_render']),
    ex(['moai_geo', 'moai_mat', 'moai_particles', 'fx_particle_mat', 'draw_geo', 'draw_mat', 'anims']),
    tex[:6], tex[6:] + ex(['model_tex'])]))
grp.append(('MEDIA LAYERS 1-6', 'one row per layer: file / drawing -> source switch -> key + crop -> 3D card (mat, geo, own render) -> feed into the stack',
    [ex(['mf%d' % i, 'ds%d' % i, 'ds%d_callbacks' % i, 'msrc%d' % i, 'mk%d' % i, 'mm%d' % i, 'mg%d' % i, 'mr%d' % i, 'mfeed%d' % i]) for i in range(1, 7)]
    + [ex(['media_next', 'thumb_grab'])]))
grp.append(('TEXT LAYERS 1-3', 'one row per text: words -> letters on black (txo) -> with alpha (txa) -> 3D card (mat, geo, render) -> tl = flat or 3D, into the stack',
    [ex(['text_src' if n == 1 else 'text_src%d' % n, 'txo%d' % n, 'txa%d' % n, 'tm%d' % n, 'tg%d' % n, 'tr%d' % n, 'tl%d' % n]) for n in (1, 2, 3)]
    + [ex(['text_old', 'blackfull'])]))
rows = [ex(['fx_src', 'black8'])]
for n in (1, 2, 3, 4):
    rows.append(ex(['lyr%d' % n]) + walk('cin%d' % n, 'fxS%d_' % n) + ex(['lfx%d' % n]))
rows.append(sorted(n for n in ALL if re.match(r'fxS\d_.*_fb$', n)))
grp.append(('LAYER STACK + PER-LAYER FX', 'fx_src paints the layers back to front  ·  rows 1-4: one layer cut out (lyr) -> its own effect chain -> lfx back into fx_src', rows))
chain = walk('fx_melt', 'fx_')
grp.append(('WHOLE-PICTURE FX', 'All-layers effects in order, left to right, then the text passes on top', chunk(chain, 10) + [ex(['fx_trails_fb', 'txcomp'])]))
grp.append(('OUTPUT', 'safety -> label -> brightness -> blackout -> OUT  ·  thumbnails',
    [ex(['fx_safety', 'fx_safety_fb', 'fx_label', 'master_level', 'xf_black', 'xf_mix', 'OUT', 'out1']), ex(['thumb_out', 'STAGE'])]))

for g in grp:
    for r in g[2]:
        for n in list(r):
            if n in used: r.remove(n)
        used.update(r)
rest = sorted(n for n in ALL if n not in used and ALL[n].OPType != 'annotateCOMP')
if rest: grp.append(('OTHER', 'helpers', chunk(rest, 8)))

DRY = globals().get('DRY', True)
CW, RH, PAD, TOP = 190, 165, 40, 70
# boxes: (column, row-band); bands stack downwards
BANDS = [[0, 1, 2], [3, 4, 5], [6], [7, 8], [9]]
report = {}
y = 0
for band in BANDS:
    x = 0; bh = 0
    for gi in band:
        if gi >= len(grp): continue
        title, body, rws = grp[gi]
        cols = max([len(r) for r in rws] + [1])
        w = cols * CW + 2 * PAD; h = len(rws) * RH + PAD + TOP
        if not DRY:
            for ri, r in enumerate(rws):
                for ci, n in enumerate(r):
                    o = ALL[n]; o.nodeX = x + PAD + ci * CW; o.nodeY = y - TOP - ri * RH - 100
            a = P.create(annotateCOMP, 'box_' + re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_'))
            a.par.Titletext = title; a.par.Bodytext = body
            a.nodeX = x; a.nodeY = y - h; a.nodeWidth = w; a.nodeHeight = h
        report[title] = (cols, len(rws), sum(len(r) for r in rws))
        x += w + 80; bh = max(bh, h)
    y -= bh + 120
REPORT = {'groups': report, 'rest': rest, 'chain': chain}
