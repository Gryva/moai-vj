# MOAI VJ ENGINE  - runs every frame (fx_engine Execute DAT, synced to this file)
import numpy as np, math, json, os, time, shutil

def hexc(h, i):
    """'#rrggbb' -> channel i as 0..1 (used by the background-removal shaders)"""
    try: return int(str(h)[1 + 2 * i:3 + 2 * i], 16) / 255.0
    except Exception: return 0.0

NAMES = ['CLEAN']   # legacy (single-effect mode is replaced by the layer stack)
S = {'angle': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0, 'level': 0.0, 'kick': 0.0,
     'scene': None, 'label': None, 'master': 1.0, 'frame': 0, 'layers': None,
     'dirty': True, 'rows': [], 'live': [], 'fades': {}, 'bank': 0, 'bankfade': 0.0}
PRESETS_FILE = project.folder + '/td/presets.json'          # THE presets (see STORE below) - not the table in the .toe
BANK_SLOTS = 128
LOOKS_FILE = project.folder + '/td/looks.json'

# ------------------------------------------------------------------ safe files (used by STORE, set list, colours, FX presets)
STORE_DIR = project.folder + '/td'
HIST_DIR = STORE_DIR + '/history'
DRAW_DIR = STORE_DIR + '/drawings'
STORE_LOG = STORE_DIR + '/store_log.txt'
HIST_KEEP = 400                                                # newest restore points kept (+ the first one of every day)
STORE = {'ok': True, 'err': '', 'saved': '', 'n': 0, 'from': '', 'colt': 0.0}

def _now(): return time.strftime('%Y-%m-%d %H:%M:%S')

def storeLog(msg):
    print('[store]', msg)
    try:
        with open(STORE_LOG, 'a', encoding='utf-8') as f: f.write(_now() + '  ' + str(msg) + '\n')
    except Exception: pass

def readJson(path):
    with open(path, 'r', encoding='utf-8') as f: return json.load(f)

def readJsonSafe(path, default=None):
    """The file, else its .bak, else default - and says so in the log."""
    for p in (path, path + '.bak'):
        if not os.path.exists(p): continue
        try:
            v = readJson(p)
            if p != path: storeLog('%s was unreadable - used %s' % (os.path.basename(path), os.path.basename(p)))
            return v
        except Exception as e: storeLog('could not read %s: %s' % (p, e))
    return default

def writeJsonSafe(path, obj, bak=True, indent=None):
    """Never leaves a half-written file behind. Raises if the data didn't land on disk intact."""
    txt = json.dumps(obj, indent=indent)                       # ascii-escaped: any reader can open it
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(txt); f.flush(); os.fsync(f.fileno())
    if readJson(tmp) != json.loads(txt): raise IOError('read-back check failed for ' + os.path.basename(path))
    if bak and os.path.exists(path):
        try: shutil.copyfile(path, path + '.bak')
        except Exception as e: storeLog('could not keep .bak of %s: %s' % (os.path.basename(path), e))
    for i in range(6):                                         # a scanner / sync tool can hold the file for a moment
        try: os.replace(tmp, path); return True
        except PermissionError:
            if i == 5: raise
            time.sleep(0.02)



# ------------------------------------------------------------------ audio analysis (own FFT)
# keep the laptop awake while the show runs: no screen-off / sleep from idling
# (Windows throttles TouchDesigner to ~4 fps while the screen is off or locked)
def keepAwake(on=True):
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM, ES_DISPLAY = 0x80000000, 0x00000001, 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM | ES_DISPLAY if on else 0))
    except Exception as e:
        print('keepAwake failed', e)
keepAwake(True)

SR, N = 48000, 2048
BUF = np.zeros(N, np.float32)
HANN = np.hanning(N).astype(np.float32)
BANDS = {'low': (30, 150), 'mid': (150, 2000), 'high': (2000, 12000)}

def _setRate(sr):
    # band masks follow whatever rate the audio device actually runs at (44.1k / 48k / 96k)
    global SR, FREQ, MASKS
    SR = float(sr) if sr and sr > 1000 else 48000.0
    FREQ = np.fft.rfftfreq(N, 1.0 / SR)
    MASKS = {k: (FREQ >= a) & (FREQ < b) for k, (a, b) in BANDS.items()}
_setRate(SR)
A = {'peak': {'low': -40.0, 'mid': -40.0, 'high': -40.0, 'level': -40.0},
     'raw': {'low': 0.0, 'mid': 0.0, 'high': 0.0, 'level': 0.0},
     'lowslow': -120.0, 'lastkick': 0.0, 'db': {}}

def analyze(C, dt):
    global BUF
    try:
        src = op('/project1/AUDIO/source')
        if abs(src.rate - SR) > 1: _setRate(src.rate)
        x = np.mean([c.numpyArray() for c in src.chans()], axis=0).astype(np.float32)
    except Exception:
        x = np.zeros(0, np.float32)
    x = x[-N:]
    if len(x):
        BUF = np.concatenate([BUF[len(x):], x])
    mic = bool(getattr(C.par, 'Automic', None) and C.par.Automic.eval())
    y = BUF * float(C.par.Gain.eval()) * (A.get('ag', 1.0) if mic else 1.0)
    rms = float(np.sqrt(np.mean(y[-int(SR / 60):] ** 2))) + 1e-12
    X = np.abs(np.fft.rfft(y * HANN)) / (N / 4.0)
    db = {k: 20.0 * math.log10(float(np.sqrt(np.mean(X[m] ** 2))) + 1e-12) for k, m in MASKS.items()}
    db['level'] = 20.0 * math.log10(rms)
    A['db'] = db
    if mic:                                   # ROOM MIC: keep the level around -20 dB whatever the room is doing (slow, so drops stay drops)
        lv = db['level']
        if lv > -75:
            A['ag'] = min(60.0, max(0.5, A.get('ag', 1.0) * 10 ** ((-20.0 - lv) / 20.0 * min(1.0, dt * 0.35))))
    A['lvl'] = db['level']
    gate, rng = float(C.par.Gate.eval()), max(6.0, float(C.par.Range.eval()))
    gated = db['level'] < gate
    for k, d in db.items():
        pk = max(d, A['peak'][k] - 4.0 * dt, gate + rng * 0.5)     # adaptive ceiling, falls 4 dB/s
        A['peak'][k] = pk
        A['raw'][k] = 0.0 if gated else min(1.0, max(0.0, (d - (pk - rng)) / rng))
    return A['raw']

def _ease(cur, tgt, tc, dt):
    if not math.isfinite(cur): cur = tgt                               # self-heal: one bad value must never stick
    dt = min(0.5, max(0.0, dt if math.isfinite(dt) else 0.0))           # clock jumps (reload, timeline) can't overshoot
    v = cur + (tgt - cur) * (1.0 - math.exp(-dt / max(1e-3, tc)))
    return tgt if abs(v - tgt) < 1e-6 else v                            # snap: tiny leftovers (1e-323) read as float-max in TD pars

def audioUpdate(C, dt, T):
    raw = analyze(C, dt)
    sm = float(C.par.Smoothing.eval())
    feel = float(C.par.Beatfeel.eval())                   # 0 punchy .. 1 smooth
    att, rel = 0.035 + 0.09 * sm, 0.10 + 0.55 * sm        # time constants in seconds
    for k in ('low', 'mid', 'high', 'level'):
        v = raw[k]
        S[k] = _ease(S[k], v, att if v > S[k] else rel, dt)
    # ---- beat detection: onset on the raw bass with adaptive threshold + refractory time
    # onset = bass jumps clearly above its own recent average, measured in dB (works at any gain/volume)
    ldb = A['db'].get('low', -120.0)
    A['lowfast'] = _ease(A.get('lowfast', ldb), ldb, 0.03, dt)
    A['lowslow'] = _ease(A['lowslow'] if A['lowslow'] < -1 else ldb, ldb, 0.45, dt)
    rise = A['lowfast'] - A['lowslow']
    A['flux'] = _ease(A.get('flux', 2.0), abs(rise), 1.5, dt)
    sens = float(C.par.Beatsense.eval())
    thr = max(0.8 + 2.4 * (1 - sens), A['flux'] * (2.2 - 1.4 * sens))
    gated = A['db'].get('level', -120.0) < float(C.par.Gate.eval())
    if not gated and rise > thr and T - A['lastkick'] > 0.22:                # max ~270 bpm, no double hits
        A['lastkick'] = T
    A['rise'] = rise
    # ---- kick envelope: smooth rise (~30 ms) then a release set by Beat feel (120 .. 650 ms)
    since = T - A['lastkick']
    tgt = 1.0 if since < 0.045 else 0.0
    S['kick'] = _ease(S['kick'], tgt, 0.028 if tgt > S['kick'] else 0.12 + 0.53 * feel, dt)
    react = C.par.Reactivity.eval()
    o = op('/project1/AUDIO/OUT')
    for i, k in enumerate(('low', 'mid', 'high', 'level', 'kick')):
        setattr(o.par, 'value%d' % i, S[k] * react)

# ------------------------------------------------------------------ model transitions
MT = {'shown': None, 'target': None, 't0': -1e9, 'sfrom': 1.0, 'state': 'idle', 's': 1.0}

def _outBack(x):
    c1 = 1.4; c3 = c1 + 1.0
    return 1.0 + c3 * (x - 1.0) ** 3 + c1 * (x - 1.0) ** 2

def modelUpdate(C, T):
    tgt = C.par.Model.eval()
    if MT['shown'] is None:
        MT['shown'] = MT['target'] = tgt
        if C.par.Modelshown.eval() != tgt: C.par.Modelshown = tgt
        return 1.0
    dur, style = max(0.0, float(C.par.Modeltrans.eval())), C.par.Modelstyle.eval()
    if tgt != MT['target']:
        MT['target'] = tgt
        if style == 'cut' or dur < 0.05 or S.pop('modelcut', False):
            MT['shown'] = tgt; C.par.Modelshown = tgt; MT['state'] = 'idle'; MT['s'] = 1.0
            return 1.0
        MT['sfrom'] = MT['s']; MT['t0'] = T; MT['state'] = 'out'
    half = dur * 0.5
    if MT['state'] == 'out':
        q = min(1.0, (T - MT['t0']) / max(1e-3, half * max(0.2, MT['sfrom'])))
        s = MT['sfrom'] * (1.0 - q ** 3)
        if q >= 1.0:
            MT['shown'] = MT['target']; C.par.Modelshown = MT['target']
            MT['state'] = 'in'; MT['t0'] = T; s = 0.0
    elif MT['state'] == 'in':
        q = min(1.0, (T - MT['t0']) / max(1e-3, half))
        s = _outBack(q)
        if q >= 1.0: MT['state'] = 'idle'; s = 1.0
    else:
        s = 1.0
    MT['s'] = s
    return s

def clonesBB():
    """CLONES copies only the picture itself: find where its visible pixels are (tiny copy of the input, a few times a second)."""
    P = op('/project1')
    for g in [P.op('fx_clones')] + [P.op('fxS%d_clones' % n) for n in (1, 2, 3, 4)]:
        if g is None or g.bypass or not g.inputs: continue
        r = P.op('cbb_' + g.name)
        if r is None:
            r = P.create(td.resolutionTOP, 'cbb_' + g.name); r.nodeX = g.nodeX; r.nodeY = g.nodeY - 120
            r.par.outputresolution = 'custom'; r.par.resolutionw = 192; r.par.resolutionh = 108
        if not r.inputs or r.inputs[0] != g.inputs[0]: r.inputConnectors[0].connect(g.inputs[0])
        a = r.numpyArray(delayed=True)
        if a is None: continue
        solid = float(a[..., 3].min()) > 0.99                          # whole picture: no see-through, so black is the empty part
        m = (a[..., :3].max(axis=2) > 0.03) if solid else (a[..., 3] > 0.008)               # faint edges / soft shadows count too
        ys, xs = np.nonzero(m); h, w = m.shape
        pd = 3                                                       # a safety margin, so nothing of the picture is trimmed
        bb = (max(0, xs.min() - pd) / w, max(0, ys.min() - pd) / h, min(w, xs.max() + 1 + pd) / w, min(h, ys.max() + 1 + pd) / h) if len(xs) else (0.0, 0.0, 1.0, 1.0)
        vi = CBBI.get(g.name)
        if vi is None:
            vi = next((i for i in range(20) if g.par['vec%dname' % i] is not None and g.par['vec%dname' % i].eval() in ('uBB', '')), None)
            if vi is None: continue
            g.par['vec%dname' % vi] = 'uBB'; CBBI[g.name] = vi
        for k, v in zip('xyzw', bb): g.par['vec%dvalue%s' % (vi, k)] = round(v, 4)
CBBI = {}

def noReact(C=None):
    """Layers switched to 'ignore the music' (SOURCE: the note button on a layer)."""
    C = C or op('/project1/CONTROLS')
    v = C.par.Noreact.eval() if hasattr(C.par, 'Noreact') else ''
    return set(k for k in str(v).split(',') if k)

def _gkey(name):
    """3D group -> the layer it belongs to."""
    if name in ('moai_geo', 'moai_particles') or name.startswith('a_') or name == 'anims': return 'model'
    if name == 'draw_geo': return 'draw'
    if name[:2] == 'mg' and name[2:].isdigit(): return 'm' + name[2:]
    if name[:2] == 'tg' and name[2:].isdigit(): return textKey(int(name[2:]))
    return 'model'

def motionOffsets(C, T, react=1.0, m=None, a=None):
    """Extra statue movement on top of the pose: (yaw, nod, roll, lift)."""
    m = C.par.Motion.eval() if m is None else m; a = float(C.par.Motionamt.eval()) if a is None else float(a)
    k = S['kick'] * react; lo = S['low'] * react
    if m == 'bob':   return (0.0, -k * 22.0 * a - math.sin(T * 2.2) * 3.0 * a, math.sin(T * 1.1) * 4.0 * a, k * 0.12 * a)
    if m == 'sway':  return (math.sin(T * 0.9) * 28.0 * a, 0.0, math.sin(T * 0.9 + 1.0) * 10.0 * a * (1.0 + lo), math.sin(T * 1.8) * 0.05 * a)
    if m == 'float': return (math.sin(T * 0.21) * 40.0 * a, math.sin(T * 0.29) * 6.0 * a, math.sin(T * 0.37) * 8.0 * a, math.sin(T * 0.5) * 0.3 * a)
    return (0.0, 0.0, 0.0, 0.0)

# ------------------------------------------------------------------ media layers: 6 slots, each a picture or a video
MSLOTS = (1, 2, 3, 4, 5, 6)
def mp(C, i, n): return C.par['M%d%s' % (i, n)]

def mediaActive(C, i, mode=None):
    """Media layer i is added, switched on and has a file (each layer is independent of 3D and the camera)."""
    has = bool(mp(C, i, 'file').eval()) or mp(C, i, 'kind').eval() == 'draw'      # a drawing layer needs no file
    on = bool(mp(C, i, 'on').eval()) and bool(mp(C, i, 'vis').eval()) and has
    return on and (mode is None or mp(C, i, 'mode').eval() == mode)

def cropUpdate(C, i):
    """Crop the picture / video (both flat and 3D card): the shader cuts, the output keeps the cropped shape."""
    k, mf = op('/project1/mk%d' % i), op('/project1/mf%d' % i)
    if k is None or mf is None: return
    l, r, t, b = [max(0.0, min(0.45, float(mp(C, i, 'crop' + n).eval()))) for n in 'lrtb']
    sig = (l, r, t, b, mf.width, mf.height)
    if sig == S.get('cropsig%d' % i): return
    S['cropsig%d' % i] = sig
    k.par.vec2valuex, k.par.vec2valuey, k.par.vec2valuez, k.par.vec2valuew = l, r, t, b
    if l + r + t + b < 1e-4:
        if k.par.outputresolution.eval() != 'useinput': k.par.outputresolution = 'useinput'
    else:
        k.par.outputresolution = 'custom'
        k.par.resolutionw = max(8, int(mf.width * (1.0 - l - r))); k.par.resolutionh = max(8, int(mf.height * (1.0 - t - b)))

def _cardShape(geo, tex):
    w, h = tex.width, tex.height
    asp = (w / h) if h else 1.0; card = geo.op('card')
    sx, sy = (2.0 * asp, 2.0) if asp <= 1.6 else (3.2, 3.2 / asp)
    if abs(card.par.sizex.eval() - sx) > 1e-3 or abs(card.par.sizey.eval() - sy) > 1e-3:
        card.par.sizex = sx; card.par.sizey = sy

def objUpdate(C):
    """Media layers in 3D OBJECT mode and the drawing are cards in the 3D scene, alongside (not instead of) the models."""
    objs = []
    for i in MSLOTS:
        cropUpdate(C, i)
        g = op('/project1/mg%d' % i); on = mediaActive(C, i, 'object')
        if g is None: continue
        if g.render != on: g.render = on
        if on: objs.append(i); _cardShape(g, op('/project1/mk%d' % i))
        src = op('/project1/msrc%d' % i); dr = 1 if mp(C, i, 'kind').eval() == 'draw' else 0   # drawing layers show the phone drawing
        if src is not None and int(src.par.index.eval()) != dr: src.par.index = dr
        sw = op('/project1/mfeed%d' % i)                             # a 3D object is drawn by its own render pass (mr<n>),
        if sw is not None and int(sw.par.index.eval()) != (1 if on else 0): sw.par.index = 1 if on else 0   # so it stays its own layer
    S['objs'] = objs
    tobjs = []
    for n in TEXTN:                                                   # 3D text: the words on a card in the 3D scene
        g = op('/project1/tg%d' % n); on = bool(C.par[tpn(n, 'Texton')].eval()) and C.par[tpn(n, 'Textspace')].eval() == '3d'
        if g is None: continue
        if g.render != on: g.render = on
        if on: tobjs.append(n); _cardShape(g, op('/project1/txa%d' % n))
        sw = op('/project1/tl%d' % n)
        if sw is not None and int(sw.par.index.eval()) != (1 if on else 0): sw.par.index = 1 if on else 0
    S['tobjs'] = tobjs
    drawing = False                                               # drawings are media layers now (kind 'draw')
    S['drawobj'] = drawing
    dg = op('/project1/draw_geo')
    if dg is not None:
        if dg.render != drawing: dg.render = drawing
        if drawing: _cardShape(dg, op('/project1/phonedraw'))
    S['obj'] = bool(objs) or drawing

def renderGeo(C):
    """What the 3D render draws: the models only if 3D is ON, plus the picture / drawing cards that are on."""
    parts = []
    if C.par.Statue.eval():
        a = animInfo(C.par.Modelshown.eval())
        g = animComp(a) if a else None
        if g is not None: parts.append(g.path)
        else: parts.append('/project1/moai_particles' if C.par.Scene.eval() == 'particles' else '/project1/moai_geo')
    if S.get('drawobj'): parts.append('/project1/draw_geo')
    geo = ' '.join(parts)
    r = op('/project1/render1')
    if r.par.geometry.eval() != geo: r.par.geometry = geo

# ------------------------------------------------------------------ animated 3D models (FBX / Alembic in /project1/anims)
ANIM_FILE = project.folder + '/3D objects/_anim/anims.json'
ANIMS = {'list': None}

def animList():
    if ANIMS['list'] is None:
        v = readJsonSafe(ANIM_FILE, [])
        ANIMS['list'] = v if isinstance(v, list) else []
    return ANIMS['list']

def animInfo(model):
    if not model or not str(model).startswith('anim_'): return None
    for a in animList():
        if a['name'] == model[5:]: return a
    return None

def animComp(a): return op('/project1/anims/a_' + a['name']) if a else None

LOOPMODES = ('loop', 'bounce')

def animLoop(a):
    """'loop' = start again from the beginning, 'bounce' = play forward, then backward (for clips whose end doesn't meet the start)."""
    m = (a or {}).get('loop', 'loop')
    return m if m in LOOPMODES else 'loop'

def animSetLoop(name, mode):
    """Remembered per animation (it's a property of the clip), saved safely to anims.json."""
    if mode not in LOOPMODES: return False
    for a in animList():
        if a['name'] == name:
            a['loop'] = mode
            try: writeJsonSafe(ANIM_FILE, animList(), indent=1); return True
            except Exception as e: _storeAlert('Animation setting NOT saved: %s' % e); return False
    return False

def animDur(a, g):
    """Clip length in seconds: FBX files report it themselves, the others carry it in anims.json."""
    if g is not None and g.OPType == 'fbxCOMP':
        try:
            L = float(g.op('fbx_info')['length_seconds'].eval())
            if L > 0.05: return L
        except Exception: pass
    return max(0.05, float(a.get('dur', 1.0) or 1.0))

def animPrepare(g):
    """Once per imported model: some FBX exporters mark materials fully transparent (alpha 0),
    which renders as black / white blobs. Nothing we show is meant to be invisible: make them solid."""
    if g.fetch('prepared', False, search=False): return
    n = 0
    for m in g.findChildren(type=MAT):
        try:
            if m.OPType == 'phongMAT' and m.par.alphamode.eval() and float(m.par.alphafront.eval()) < 0.01:
                m.par.alphamode = False; n += 1
        except Exception: pass
    if n: storeLog('%s: %d invisible materials made solid' % (g.name, n))
    g.store('prepared', True)

def animPos(p, mode):
    """p counts clip lengths (0..2). Returns 0..1 inside the clip.
    bounce: forward then backward, slowing to a stop at each end so the turn never jerks."""
    if mode != 'bounce': return p % 1.0
    q = p % 2.0; x = q if q <= 1.0 else 2.0 - q
    e = 0.06
    if x < e: x = x * x / (2.0 * e) + e * 0.5
    elif x > 1.0 - e:
        y = 1.0 - x; x = 1.0 - (y * y / (2.0 * e) + e * 0.5)
    return x

def animUpdate(C, dt, react):
    """Show the animated model (instead of the statue). One clock drives every kind of clip,
    so speed, beat push and loop / bounce behave the same for FBX, Alembic and baked frames."""
    a = animInfo(C.par.Modelshown.eval())
    g = animComp(a)
    if g is None: a = None
    key = a['name'] if a else None
    if key != S.get('anim'):
        for c in op('/project1/anims').children:
            if c.isCOMP and c is not g:
                if c.render: c.render = False
                if c.OPType == 'fbxCOMP' and c.par.play.eval(): c.par.play = False
        if g is not None:
            animPrepare(g)
            g.render = True
            if g.OPType == 'fbxCOMP':                               # we set the position ourselves every frame
                g.par.playmode = 'specifyindex'; g.par.indexunit = 'fraction'; g.par.play = True
            op('/project1/moai_geo').render = False; op('/project1/moai_particles').render = False
            op('/project1/moai_geo').par.instancing = False
            op('/project1/render1').par.geometry = g.path
        else:
            applyScene(C.par.Scene.eval())
        S['anim'] = key; S['animp'] = 0.0                            # a new clip starts at its beginning
    if g is None: return None
    sp = float(C.par.Animspeed.eval()) * (1.0 + float(C.par.Animbeat.eval()) * S['kick'] * react)
    dur = animDur(a, g)
    S['animp'] = (S.get('animp', 0.0) + dt * sp / dur) % 2.0         # 0..2 = one full forward + backward cycle
    x = animPos(S['animp'], animLoop(a))
    kind = a.get('kind')
    if g.OPType == 'fbxCOMP':
        if abs(g.par.index.eval() - x) > 1e-6: g.par.index = x
    elif kind == 'seq':                                              # baked frames (heavy Alembic, pre-decoded)
        n = max(1, int(a.get('frames', 1)))
        i = min(n - 1, int(x * n))
        sw = g.op('seq')
        if int(sw.par.input.eval()) != i: sw.par.input = i
    else:
        g.op('abc').par.time = x * dur
    return g

def mediaFit(i=None):
    """Frame a 3D-object picture / video so it fills the screen as if it were played flat.
    Nothing moves until you touch the camera, then it behaves like an object in the 3D scene."""
    C = op('/project1/CONTROLS')
    if i is None: i = next((j for j in MSLOTS if mediaActive(C, j, 'object')), 1)
    mf = op('/project1/mk%d' % i)
    w, h = mf.width, mf.height
    asp = (w / h) if h else 16 / 9.0
    sx, sy = (2.0 * asp, 2.0) if asp <= 1.6 else (3.2, 3.2 / asp)
    ren = op('/project1/render1'); ra = ren.width / float(ren.height) if ren.height else 16 / 9.0
    t = math.tan(math.radians(max(5.0, C.par.Fov.eval())) / 2.0)
    dist = max((sx / 2.0) / t, (sy / 2.0) * ra / t)                # whole picture visible, centred
    for k, v in (('Distance', round(dist, 4)), ('Orbit', 0.0), ('Elevation', 0.0), ('Height', 0.0), ('Pan', 0.0), ('Roll', 0.0),
                 ('Orbitspeed', 0.0), ('Orbitsway', 0.0), ('Elevsway', 0.0), ('Distsway', 0.0), ('Rollsway', 0.0), ('Shake', 0.0),
                 ('Audiocam', 0.0), ('Angle', 0.0), ('Tilt', 0.0), ('Motion', 'still'), ('M%dobjx' % i, 0.0), ('M%dobjy' % i, 0.0), ('M%dobjscale' % i, 1.0),
                 ('M%dobjz' % i, 0.0), ('M%dobjturn' % i, 0.0), ('M%dobjtilt' % i, 0.0)):
        try: C.par[k] = v
        except Exception: pass
    S['angle'] = 0.0
    CS['cur'] = None; CS['pan'] = 0.0; CS['orb'] = 0.0; CS['joltT'] = CS['jolt'] = 0.0

def applyModelXform(C, g, s, base_ry):
    style = C.par.Modelstyle.eval()
    k = max(0.0, 1.0 - s)                                   # 0 = fully shown, 1 = fully gone
    if style == 'drop':
        g.par.scale = max(0.001, 0.75 + 0.25 * s); g.par.ty = -k * 3.6; g.par.ry = base_ry
    elif style == 'spin':
        g.par.scale = max(0.001, s); g.par.ty = 0.0; g.par.ry = base_ry + k * 540.0
    else:
        g.par.scale = max(0.001, s); g.par.ty = 0.0; g.par.ry = base_ry

def safetyUpdate(C):
    v = float(C.par.Safety.eval()); g = op('/project1/fx_safety')
    off = v < 0.01
    if g.bypass != off: g.bypass = off
    if not off and abs(g.par.vec3valuex.eval() - v) > 1e-4: g.par.vec3valuex = v

# ------------------------------------------------------------------ text layer
TEXTPARS = ['Texton', 'Textstr', 'Textmode', 'Textlayout', 'Textanim', 'Textfont', 'Textcolor',
            'Textsize', 'Textglow', 'Textspeed', 'Textreact', 'Textamount', 'Textcm', 'Textca', 'Textcb', 'Textcang',
            'Textx', 'Texty', 'Textdir', 'Textadir', 'Textspace', 'Textdepth', 'Textoscale', 'Textoturn', 'Textotilt',
            'Textmotion', 'Textmaxis', 'Textmspeed', 'Textmamt', 'Textmrev', 'Textname']
TEXTNEW = {'Textx': 0.0, 'Texty': 0.0, 'Textdir': 'h', 'Textadir': 'left', 'Textspace': 'flat', 'Textdepth': 0.0,
           'Textoscale': 1.0, 'Textoturn': 0.0, 'Textotilt': 0.0,
           'Textmotion': 'models', 'Textmaxis': 'y', 'Textmspeed': 30.0, 'Textmamt': 1.0, 'Textmrev': False, 'Textname': ''}   # older presets: these
TFONTFILES = {'Bangers': 'Bangers-Regular.ttf', 'Permanent Marker': 'PermanentMarker-Regular.ttf', 'Caveat Brush': 'CaveatBrush-Regular.ttf',
              'Monoton': 'Monoton-Regular.ttf', 'Pacifico': 'Pacifico-Regular.ttf', 'Press Start 2P': 'PressStart2P-Regular.ttf',
              'Rubik Glitch': 'RubikGlitch-Regular.ttf', 'Bungee Shade': 'BungeeShade-Regular.ttf', 'Shrikhand': 'Shrikhand-Regular.ttf',
              'Rock Salt': 'RockSalt-Regular.ttf'}                # shipped in td/fonts (open licences), no install needed
TDIRS = {'h': 0, 'v': 1, 'up': 2, 'down': 3}
TADIRS = {'left': 0, 'right': 1, 'up': 2, 'down': 3}
TCOLORS = {'white': (1, 1, 1), 'hot': (1, .3, .18), 'cyan': (.24, .94, 1), 'violet': (.69, .42, 1),
           'lime': (.78, 1, .24), 'gold': (1, .78, .25)}
TMODES = ['overlay', 'mask', 'cutout', 'invert', 'outline', 'glitch', 'refract']
TANIM = {'static': 0, 'pulse': 1, 'wave': 2, 'scroll': 3, 'tile': 4, 'type': 0, 'beat': 1, 'shake': 5, 'flicker': 6, 'breathe': 7, 'bounce': 8}
TLAYOUT = {  # align x, align y, pos x, pos y, font px, autosize, wrap
    'center': ('center', 'center', 0, 0, 150, 'fitiffat', True),
    'fill':   ('center', 'center', 0, 0, 400, 'alwaysfit', True),
    'stack':  ('center', 'center', 0, 0, 120, 'fitiffat', True),
    'lower':  ('left', 'bottom', 70, 70, 64, 'fitiffat', True),
    'corner': ('left', 'top', 50, -50, 40, 'fitiffat', True),
    # the nine spots of the frame (font size follows Size)
    'tl': ('left', 'top', 56, -46, 72, 'fitiffat', True), 'top': ('center', 'top', 0, -46, 72, 'fitiffat', True),
    'tr': ('right', 'top', -56, -46, 72, 'fitiffat', True), 'left': ('left', 'center', 56, 0, 72, 'fitiffat', True),
    'right': ('right', 'center', -56, 0, 72, 'fitiffat', True), 'bl': ('left', 'bottom', 56, 46, 72, 'fitiffat', True),
    'bottom': ('center', 'bottom', 0, 46, 72, 'fitiffat', True), 'br': ('right', 'bottom', -56, 46, 72, 'fitiffat', True)}
TSMALL = ('lower', 'corner', 'tl', 'top', 'tr', 'left', 'right', 'bl', 'bottom', 'br')

def textKey(n): return 'text' if n == 1 else 'text%d' % n

def textInStack(C, n):
    """Text is drawn inside the layer stack when it is in 3D or something sits in front of it; otherwise it goes on top
    after the effects (where Mask / Cutout / Invert / Refract can use the picture under it)."""
    if C.par[tpn(n, 'Textspace')].eval() == '3d': return True
    k = textKey(n)
    for t in layerOrder(C):
        if t == k: return False
        if t not in TXTGT and _layerShown(C, t): return True
    return False
TX = {'sig': None, 't0': 0.0, 'words': [' '], 'wi': 0, 'lk': None, 'shown': None}

TXN = {1: TX, 2: {'sig': None, 't0': 0.0, 'words': [' '], 'wi': 0, 'lk': None, 'shown': None},
       3: {'sig': None, 't0': 0.0, 'words': [' '], 'wi': 0, 'lk': None, 'shown': None}}
TEXTN = (1, 2, 3)

def tpn(n, key):
    """Parameter name of text layer n: layer 1 = Text*, layers 2-3 = T2* / T3* (Textstr -> T2str, Texton -> T2on)."""
    return key if n == 1 else 'T%d%s' % (n, key[4:])

def textAll(C, T):
    for n in TEXTN: textUpdate(C, T, n)

def textUpdate(C, T, n=1):
    TX = TXN[n]; tp = lambda k: C.par[tpn(n, k)]
    g = op('/project1/fx_text' + ('' if n == 1 else str(n)))
    if g is None: return False
    on = bool(tp('Texton').eval()) and float(tp('Textamount').eval()) > 0.001
    own = (('text' if n == 1 else 'text%d' % n) in SLOTS)                # has its own effects: drawn by txcomp instead
    inst = on and textInStack(C, n); TINST[n] = inst                     # behind a layer / 3D: drawn inside the stack
    if g.bypass != ((not on) or own or inst): g.bypass = (not on) or own or inst
    if not on: return False
    tt = op('/project1/text_src' + ('' if n == 1 else str(n)))
    full = tp('Textstr').eval() or ' '
    lay, anim, size = tp('Textlayout').eval(), tp('Textanim').eval(), float(tp('Textsize').eval())
    small = lay in TSMALL
    tdir = tp('Textdir').eval()
    sig = (full, lay, anim, tp('Textfont').eval(), round(size, 3) if small else 0, tdir)
    if sig != TX['sig']:
        TX['sig'] = sig; TX['t0'] = T; TX['words'] = full.split() or [' ']; TX['wi'] = 0; TX['shown'] = None
        ax, ay, px, py, fpx, fit, wrap = TLAYOUT.get(lay, TLAYOUT['center'])
        if anim == 'scroll': wrap = False
        p = tt.par
        fnt = tp('Textfont').eval(); ff = TFONTFILES.get(fnt, '')
        p.fontfile = (project.folder + '/td/fonts/' + ff) if ff else ''; p.font = fnt if not ff else p.font.eval()
        p.alignx = ax; p.aligny = ay
        p.positionx = px; p.positiony = py
        p.fontsizex = fpx * (size if small else 1.0); p.fontautosize = fit; p.wordwrap = wrap
    if anim == 'type':
        nch = int((T - TX['t0']) * 14.0 * max(0.1, tp('Textspeed').eval())) % (len(full) + 25)
        txt = full[:min(nch, len(full))] or ' '
    elif anim == 'beat':
        if A['lastkick'] != TX['lk']:
            TX['lk'] = A['lastkick']; TX['wi'] = (TX['wi'] + 1) % len(TX['words'])
        txt = TX['words'][TX['wi']]
    elif lay == 'stack':
        txt = '\n'.join(full.split()) or ' '
    else:
        txt = full
    if tdir == 'v':                                                  # vertical: one letter under the other
        txt = '\n'.join(' ' if c == ' ' else c for c in txt.replace('\n', ' ')) or ' '
    if txt != TX['shown']:
        tt.par.text = txt; TX['shown'] = txt
        if anim != 'type' or txt == full: TX['bbat'] = S['frame'] + 2          # measure the words once they're drawn
    if TX.get('bbat') and S['frame'] >= TX['bbat']:
        TX['bbat'] = 0
        try:
            al = tt.numpyArray(delayed=False)[..., 3]; ys, xs = np.nonzero(al > 0.05); h, w = al.shape
            if len(xs): TX['bb'] = (xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h)
        except Exception as er: print('text bounds', er)
    bb = TX.get('bb', (0.0, 0.0, 1.0, 1.0))
    g.par.vec9valuex, g.par.vec9valuey, g.par.vec9valuez, g.par.vec9valuew = bb
    o = op('/project1/AUDIO/OUT'); pp = g.par
    e = 1.0                                                      # text morph between presets (old words -> new words)
    if TXM['on']:
        k = (T - TXM['t0']) / TXM['dur']
        if k >= 1.0: TXM['on'] = False
        else: e = k * k * (3.0 - 2.0 * k)
    M = TXM['on'] and n == 1                                   # the preset word morph is for text layer 1
    if n != 1: e = 1.0
    def L(key):
        v = float(tp(key).eval())
        return TXM['frm'][key] + (v - TXM['frm'][key]) * e if M else v
    mode = TXM['mode'] if (M and e < 0.5) else tp('Textmode').eval()
    pp.vec0valuex = T % TWRAP                               # shaders get a wrapped clock
    if textKey(n) in noReact(): pp.vec1valuex = pp.vec1valuey = pp.vec1valuez = pp.vec1valuew = 0.0
    else: pp.vec1valuex, pp.vec1valuey, pp.vec1valuez, pp.vec1valuew = o['low'].eval(), o['mid'].eval(), o['high'].eval(), o['kick'].eval()
    pp.vec2valuex = L('Textamount')
    pp.vec3valuex = TMODES.index(mode) if mode in TMODES else 0
    pp.vec3valuey = TANIM.get(anim, 0); pp.vec3valuez = L('Textspeed'); pp.vec3valuew = L('Textreact')
    r, gg, b = TCOLORS.get(tp('Textcolor').eval(), (1, 1, 1))
    if M:
        r0, g0, b0 = TXM['col']; r, gg, b = r0 + (r - r0) * e, g0 + (gg - g0) * e, b0 + (b - b0) * e
    pp.vec4valuex, pp.vec4valuey, pp.vec4valuez, pp.vec4valuew = r, gg, b, L('Textglow')
    sz = L('Textsize')
    pp.vec5valuex = 1.0 if small else sz; pp.vec5valuey = sz; pp.vec5valuez = 0.5
    pp.vec6valuex = e; pp.vec6valuez = 1.0 if M else 0.0
    tm = int(tp('Textcm').eval()); tv = _hex(tp('Textca').eval()) + _hex(tp('Textcb').eval(), (1.0, 0.24, 0.66)) + (float(tp('Textcang').eval()),)
    if M and TXM.get('tc'):                                      # colours glide with the word morph
        m0, v0 = TXM['tc']
        if m0 == tm: tv = tuple(a_ + (b_ - a_) * e for a_, b_ in zip(v0, tv))
        elif e < 0.5: tm, tv = m0, v0
    pp.vec7valuex, pp.vec7valuey, pp.vec7valuez, pp.vec7valuew = tv[0], tv[1], tv[2], float(tm)
    pp.vec8valuex, pp.vec8valuey, pp.vec8valuez, pp.vec8valuew = tv[3], tv[4], tv[5], math.radians(tv[6])
    try: pp.vec10valuex, pp.vec10valuey, pp.vec10valuez, pp.vec10valuew = float(tp('Textx').eval()), float(tp('Texty').eval()), TDIRS.get(tdir, 0), TADIRS.get(tp('Textadir').eval(), 0)
    except Exception: pass
    return True

TINST = {1: False, 2: False, 3: False}

TXM = {'on': False, 't0': 0.0, 'dur': 1.0, 'frm': {}, 'col': (1, 1, 1), 'mode': 'overlay'}
TNUM = ['Textsize', 'Textglow', 'Textamount', 'Textspeed', 'Textreact']

def textMorphStart(nt, dur):
    """Both looks have words on screen: the old words dissolve into the new ones (colour, size, glow glide)."""
    C = op('/project1/CONTROLS')
    if not any(p in TEXTPARS and C.par[p].eval() != v for p, v in nt.items()): return False
    src, old = op('/project1/text_src'), op('/project1/text_old')
    if old is None: return False
    for p in src.pars():                                         # freeze the current words into text_old
        if p.readOnly or p.isPulse or p.mode != ParMode.CONSTANT: continue
        try: old.par[p.name] = p.eval()
        except Exception: pass
    TXM.update(on=True, t0=absTime.seconds, dur=max(0.4, float(dur)),
               frm={k: float(C.par[k].eval()) for k in TNUM},
               col=TCOLORS.get(C.par.Textcolor.eval(), (1, 1, 1)), mode=C.par.Textmode.eval(),
               tc=(int(C.par.Textcm.eval()), _hex(C.par.Textca.eval()) + _hex(C.par.Textcb.eval(), (1.0, 0.24, 0.66)) + (float(C.par.Textcang.eval()),)))
    for p, v in nt.items():
        if p in TEXTPARS:
            try: C.par[p] = v
            except Exception: pass
    return True

# ------------------------------------------------------------------ frame loop
# ------------------------------------------------------------------ scenes + layer stack
def applyScene(sc):
    g, pg = op('/project1/moai_geo'), op('/project1/moai_particles')
    parts = (sc == 'particles')
    g.render = not parts; pg.render = parts
    op('/project1/render1').par.geometry = pg.path if parts else g.path
    g.par.instancing = (sc == 'grid')
    if sc == 'grid':                                    # frame the whole grid once when entering
        C = op('/project1/CONTROLS')
        need = C.par.Gridcount.eval() * C.par.Gridspace.eval() * 0.9 + 2.5
        if C.par.Distance.eval() < need: C.par.Distance = round(need, 2)

def _rows():
    t = op('/project1/FX_STACK')
    if S['dirty'] or not S['rows'] or S['frame'] % 30 == 0:      # re-read only when something changed
        S['rows'] = [{t[0, c].val: t[r, c].val for c in range(t.numCols)} for r in range(1, t.numRows)]
        S['dirty'] = False
    return t, S['rows']

def layers():
    return _rows()[1]

def _isOn(r): return r['on'] in ('1', 'True', 'true')

FEEDBACK = {'trails': '/project1/fx_trails_fb'}

def applyLayers(T=None):
    t, rows = _rows()
    T = absTime.seconds if T is None else T
    fades = S['fades']
    live = []
    for r in rows:
        k = r['key']; amt = float(r['amt'] or 0); p1 = float(r['p1'] or 0); on = _isOn(r)
        f = fades.get(k)
        if f:                                                     # crossfade in progress
            x = min(1.0, (T - f['t0']) / max(0.001, f['dur']))
            x = x * x * (3 - 2 * x)
            amt = f['a0'] + (f['a1'] - f['a0']) * x
            if f['a1'] == 0 and x < 1: on = True; p1 = f.get('p1', p1)
            if x >= 1: del fades[k]
        live.append((k, on and amt > 0.001, amt, p1))
    sig = tuple(live)
    if sig != S['layers']:
        S['layers'] = sig
        for k, on, amt, p1 in live:
            g = op('/project1/fx_' + k)
            if g is None: continue
            if on and g.bypass and k in FEEDBACK:                  # start feedback layers from a clean buffer
                fb = op(FEEDBACK[k])
                if fb: fb.par.resetpulse.pulse()
            g.bypass = not on
            if on:
                g.par.vec2valuex = amt
                g.par.vec3valuex = p1
    S['live'] = [k for k, on, a, p in live if on]

def pushUniforms(T):
    """Audio + time straight into the active layers only (no per-layer Python expressions)."""
    o = op('/project1/AUDIO/OUT')
    au = (o['low'].eval(), o['mid'].eval(), o['high'].eval(), o['kick'].eval())
    for k in S['live']:
        p = op('/project1/fx_' + k).par
        p.vec0valuex = T % TWRAP                               # shaders get a wrapped clock
        p.vec1valuex, p.vec1valuey, p.vec1valuez, p.vec1valuew = au
        if k in COLFX: _colPush(k, p, T)

# ------------------------------------------------------------------ effect colours (own colour / solid / linear / radial gradient)
COLFX = ['hologram', 'neon', 'lines', 'halftone', 'ascii', 'thermal', 'palette', 'glow', 'glitch', 'matte', 'strobe', 'kaleido', 'tunnel', 'duotone', 'sketch', 'nightvis', 'flash']
LCOL_FILE = project.folder + '/td/lcols.json'
LCOL = readJsonSafe(LCOL_FILE, {})                           # key -> {'m', 'a', 'b', 'ang'}
if not isinstance(LCOL, dict): LCOL = {}
LCOLF = {}                                                   # key -> glide {'f': from rgb/rgb/ang, 't0', 'dur'}
def _hex(h, d=(1.0, 1.0, 1.0)):
    try:
        h = str(h).strip().lstrip('#')
        if len(h) != 6: return d
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except Exception: return d

def _colClean(c):
    c = c or {}
    m = int(c.get('m', 0)) if str(c.get('m', 0)).lstrip('-').isdigit() else 0
    hx = lambda v, d: ('#%02x%02x%02x' % tuple(int(round(x * 255)) for x in _hex(v, _hex(d))))
    return {'m': max(0, min(3, m)), 'a': hx(c.get('a'), '#22e6ff'), 'b': hx(c.get('b'), '#ff3da8'),
            'ang': max(0.0, min(360.0, float(c.get('ang', 0) or 0)))}

def _colVals(c):
    return _hex(c['a']) + _hex(c['b']) + (c['ang'],)

def colSet(k, c, fade=0.0):
    if k not in COLFX: return None
    new = _colClean(c); old = LCOL.get(k)
    if fade > 0.01 and old and old['m'] == new['m'] and new['m'] > 0:
        LCOLF[k] = {'f': _colVals(old), 't0': absTime.seconds, 'dur': float(fade)}
    else: LCOLF.pop(k, None)
    LCOL[k] = new
    S['lcolsave'] = True
    return new

def colSave():
    try: writeJsonSafe(LCOL_FILE, LCOL); return True
    except Exception as e: storeLog('colour save failed: %s' % e); return False

def colsApply(d, fade=0.0):
    """A look / preset brings its effect colours; effects it doesn't mention go back to their own colour."""
    d = d or {}
    for k in COLFX: colSet(k, d.get(k, {'m': 0}), fade)

def _colPush(k, p, T):
    c = LCOL.get(k)
    if not c or c['m'] == 0:
        if p.vec4valuew != 0: p.vec4valuew = 0
        return
    v = _colVals(c); g = LCOLF.get(k)
    if g:
        x = min(1.0, (T - g['t0']) / max(0.001, g['dur'])); x = x * x * (3 - 2 * x)
        v = tuple(a + (b - a) * x for a, b in zip(g['f'], v))
        if x >= 1.0: LCOLF.pop(k, None)
    p.vec4valuex, p.vec4valuey, p.vec4valuez, p.vec4valuew = v[0], v[1], v[2], float(c['m'])
    p.vec5valuex, p.vec5valuey, p.vec5valuez, p.vec5valuew = v[3], v[4], v[5], math.radians(v[6])

def setLayer(key, on=None, amt=None, p1=None):
    t = op('/project1/FX_STACK'); row = t.row(key)
    if row is None: return
    S['dirty'] = True; S['fades'].pop(key, None)
    r = row[0].row
    if on is not None: t[r, 'on'] = 1 if on else 0
    if amt is not None: t[r, 'amt'] = round(float(amt), 4)
    if p1 is not None: t[r, 'p1'] = round(float(p1), 4)

def toggleLayer(key):
    t = op('/project1/FX_STACK'); row = t.row(key)
    if row is not None: setLayer(key, on=(t[row[0].row, 'on'].val not in ('1', 'True', 'true')))

def toggleLayerIndex(i):
    rows = layers()
    if 0 <= i < len(rows): toggleLayer(rows[i]['key'])

def clearLayers():
    for r in layers(): setLayer(r['key'], on=False)

# ------------------------------------------------------------------ per-layer effects
# 'all' = the main chain (FX_STACK, whole picture). Each source layer can have its own effect stack; up to 4 layers
# with effects at once get one of the four copies of the chain (fxS<n>_*), fed by an isolated copy of that layer (lyr<n>).
FXTGTS = ['model', 'camera', 'draw'] + ['m%d' % i for i in MSLOTS] + ['text', 'text2', 'text3']
TXTGT = {'text': 1, 'text2': 2, 'text3': 3}                     # text layers: drawn after the effects, own chain via txo/txa
FXT = {k: {} for k in FXTGTS}                                  # target -> effect key -> [on, amt, p1]
TCOL = {k: {} for k in FXTGTS}                                 # target -> effect key -> colour
SLOTS = {}                                                     # target -> chain 1..4
SLOTSIG = {}

def _defRow(key):
    for r in layers():
        if r['key'] == key: return float(r['amt'] or 1.0), float(r['p1'] or 0.0)
    return 1.0, 0.0

def tSetLayer(tgt, key, on=None, amt=None, p1=None):
    if tgt not in FXT: return
    cur = FXT[tgt].get(key) or ([False] + list(_defRow(key)))
    if on is not None: cur[0] = bool(on)
    if amt is not None: cur[1] = float(amt)
    if p1 is not None: cur[2] = float(p1)
    FXT[tgt][key] = cur

def tClear(tgt=None):
    for t in ([tgt] if tgt else FXTGTS):
        if t in FXT: FXT[t] = {}

def fxCopy(src, dst):
    """Copy every effect (on/amount/setting) and its colour from one layer to another ('all' = the whole-picture stack)."""
    if src == dst or (src != 'all' and src not in FXT) or (dst != 'all' and dst not in FXT): return False
    if src == 'all':
        stack = {r['key']: [_isOn(r), float(r['amt']), float(r['p1'])] for r in layers() if _isOn(r)}
        cols = {k: dict(v) for k, v in LCOL.items() if v.get('m', 0) > 0}
    else:
        stack = {k: list(v) for k, v in FXT[src].items() if v[0]}
        cols = {k: dict(v) for k, v in TCOL[src].items()}
    if dst == 'all':
        clearLayers()
        for k, v in stack.items(): setLayer(k, on=True, amt=v[1], p1=v[2])
        for k in COLFX: colSet(k, cols.get(k, {'m': 0}))
    else:
        FXT[dst] = {k: [True, v[1], v[2]] for k, v in stack.items()}
        TCOL[dst] = {k: _colClean(v) for k, v in cols.items()}
    return True

def tColSet(tgt, k, c):
    if tgt not in TCOL or k not in COLFX: return None
    TCOL[tgt][k] = _colClean(c); return TCOL[tgt][k]

def tData():
    return {t: {k: [int(v[0]), round(v[1], 4), round(v[2], 4)] for k, v in FXT[t].items() if v[0]} for t in FXTGTS}

def tLive():
    return {t: [[k, int(v[0]), round(v[1], 3), round(v[2], 3)] for k, v in sorted(FXT[t].items())] for t in FXTGTS if FXT[t]}

def _layerShown(C, t):
    if t == 'model': return bool(C.par.Statue.eval())
    if t == 'camera': return C.par.Camsrc.eval() in CAMMODES
    if t == 'draw': return bool(C.par.Drawon.eval()) and not S.get('drawobj')
    if t[:1] == 'm' and t[1:].isdigit(): return mediaActive(C, int(t[1:]))
    if t in TXTGT: return bool(C.par[tpn(TXTGT[t], 'Texton')].eval())
    return False

def fxTargets(C):
    """Give each visible layer that has effects one of the four chains (front layers first); free the rest."""
    want = [t for t in layerOrder(C) if t in FXT and any(v[0] and v[1] > 0.001 for v in FXT[t].values()) and _layerShown(C, t)][:4]
    for t in list(SLOTS):
        if t not in want: del SLOTS[t]
    free = [n for n in (1, 2, 3, 4) if n not in SLOTS.values()]
    for t in want:
        if t not in SLOTS and free: SLOTS[t] = free.pop(0)
    P = op('/project1'); fx = P.op('fx_src')
    g = lambda t: float(SLOTS.get(t, 0))
    fx.par.vec9valuex, fx.par.vec9valuey, fx.par.vec9valuez = g('model'), g('camera'), g('draw')
    fx.par.vec15valuex, fx.par.vec15valuey, fx.par.vec15valuez, fx.par.vec15valuew = g('m1'), g('m2'), g('m3'), g('m4')
    fx.par.vec16valuex, fx.par.vec16valuey = g('m5'), g('m6')
    tc = P.op('txcomp')
    gt = lambda n, inst: 0.0 if TINST.get(n) == inst else g(textKey(n))          # text on top -> txcomp, in the stack -> fx_src
    if tc is not None: tc.par.vec0valuex, tc.par.vec0valuey, tc.par.vec0valuez = gt(1, True), gt(2, True), gt(3, True)
    fx.par.vec28valuex, fx.par.vec28valuey, fx.par.vec28valuez = gt(1, False), gt(2, False), gt(3, False)
    for n in (1, 2, 3, 4):
        t = next((k for k, v in SLOTS.items() if v == n), None)
        sw = P.op('lfx%d' % n)
        if sw is not None and int(sw.par.index.eval()) != (1 if t else 0): sw.par.index = 1 if t else 0
        if t is None: SLOTSIG.pop(n, None); continue
        cin = P.op('cin%d' % n); ci = TXTGT.get(t, 0)                  # chain input: an isolated layer, or a text layer on its own
        if cin is not None and int(cin.par.index.eval()) != ci: cin.par.index = ci
        iso = P.op('lyr%d' % n)
        if t in LAYER_IDS and t not in TXTGT and iso is not None and iso.par.vec9valuew.eval() != LAYER_IDS[t]: iso.par.vec9valuew = LAYER_IDS[t]
        sig = (t, tuple(sorted((k, bool(v[0] and v[1] > 0.001), v[1], v[2]) for k, v in FXT[t].items())))
        if SLOTSIG.get(n) != sig:
            SLOTSIG[n] = sig
            for r in layers():
                k = r['key']; g = P.op('fxS%d_%s' % (n, k))
                if g is None: continue
                v = FXT[t].get(k); on = bool(v and v[0] and v[1] > 0.001)
                if on and g.bypass and k in FEEDBACK:
                    fb = P.op('fxS%d_%s_fb' % (n, k))
                    if fb: fb.par.resetpulse.pulse()
                g.bypass = not on
                if on: g.par.vec2valuex = v[1]; g.par.vec3valuex = v[2]

def tUniforms(T):
    if not SLOTS: return
    o = op('/project1/AUDIO/OUT')
    au0 = (o['low'].eval(), o['mid'].eval(), o['high'].eval(), o['kick'].eval()); NR = noReact()
    for t, n in SLOTS.items():
        au = (0.0, 0.0, 0.0, 0.0) if t in NR else au0             # a layer set to ignore the music: its effects ignore it too
        for k, v in FXT[t].items():
            if not (v[0] and v[1] > 0.001): continue
            g = op('/project1/fxS%d_%s' % (n, k))
            if g is None: continue
            p = g.par
            p.vec0valuex = T % TWRAP
            p.vec1valuex, p.vec1valuey, p.vec1valuez, p.vec1valuew = au
            if k in COLFX:
                c = TCOL[t].get(k)
                if not c or c['m'] == 0:
                    if p.vec4valuew != 0: p.vec4valuew = 0
                else:
                    cv = _colVals(c)
                    p.vec4valuex, p.vec4valuey, p.vec4valuez, p.vec4valuew = cv[0], cv[1], cv[2], float(c['m'])
                    p.vec5valuex, p.vec5valuey, p.vec5valuez, p.vec5valuew = cv[3], cv[4], cv[5], math.radians(cv[6])

GRIDPARS = ['Gridcount', 'Griddepth', 'Gridspace', 'Gridwave', 'Gridstagger']

def lookData():
    C = op('/project1/CONTROLS')
    return {'layers': {r['key']: [int(r['on'] in ('1', 'True', 'true')), float(r['amt']), float(r['p1'])] for r in layers()},
            'scene': C.par.Scene.eval(), 'grid': {p: C.par[p].eval() for p in GRIDPARS},
            'text': {p: C.par[p].eval() for p in TEXTPARS}, 'statue': bool(C.par.Statue.eval()),
            'texts': {str(n): {p: C.par[tpn(n, p)].eval() for p in TEXTPARS} for n in (2, 3) if C.par[tpn(n, 'Texton')].eval()},
            'lcols': {k: dict(v) for k, v in LCOL.items() if v.get('m', 0) > 0},
            'tfx': tData(), 'tcol': {t: {k: dict(v) for k, v in TCOL[t].items() if v.get('m', 0) > 0} for t in FXTGTS}}

def applyLook(d, text=True):
    C = op('/project1/CONTROLS'); S['dirty'] = True
    saved = d.get('layers', {})
    for r in layers():                                           # a preset is the WHOLE stack:
        if r['key'] not in saved: setLayer(r['key'], on=False)   # layers it doesn't mention go off
    for k, v in saved.items():
        setLayer(k, on=bool(v[0]), amt=v[1], p1=v[2])
    if text and d.get('text') and 'Textcm' not in d['text']: C.par.Textcm = 0
    if text and d.get('text'):
        for p_, v in TEXTNEW.items():
            if p_ not in d['text']: C.par[p_] = v
    for p, v in list(d.get('grid', {}).items()) + (list(d.get('text', {}).items()) if text else []):
        try: C.par[p] = v
        except Exception: pass
    if d.get('scene'): C.par.Scene = d['scene']
    tx2 = d.get('texts') or {}                                   # text layers 2 and 3 (older presets: off)
    for n in (2, 3):
        for p_, v in TEXTNEW.items():
            if str(n) in tx2 and p_ not in tx2[str(n)]: C.par[tpn(n, p_)] = v
        for p_, v in (tx2.get(str(n)) or {'Texton': False}).items():
            try: C.par[tpn(n, p_)] = v
            except Exception: pass
        if str(n) not in tx2: C.par[tpn(n, 'Texton')] = False
    C.par.Statue = bool(d.get('statue', True))                  # older presets: statue on
    colsApply(d.get('lcols'), S.get('colfade', 0.0))
    tfx = dict(d.get('tfx') or {}); tcol = dict(d.get('tcol') or {})   # per-layer effects (older presets: none)
    for a, b in (('images', 'm1'), ('videos', 'm2')):                 # before media layers were slots
        if a in tfx and b not in tfx: tfx[b] = tfx.pop(a)
        if a in tcol and b not in tcol: tcol[b] = tcol.pop(a)
    for t in FXTGTS:
        FXT[t] = {k: [bool(v[0]), float(v[1]), float(v[2])] for k, v in (tfx.get(t) or {}).items()}
        TCOL[t] = {k: _colClean(v) for k, v in (tcol.get(t) or {}).items()}

def lookNames():
    t = op('/project1/LOOKS')
    return [t[r, 'name'].val for r in range(1, t.numRows)]

def loadLook(n):
    t = op('/project1/LOOKS')
    if 1 <= n < t.numRows: applyLook(json.loads(t[n, 'data'].val))

def saveLook(n, name=None):
    t = op('/project1/LOOKS')
    while t.numRows <= n: t.appendRow(['Look %d' % t.numRows, '{}'])
    t[n, 'name'] = name or t[n, 'name'].val or ('Look %d' % n)
    t[n, 'data'] = json.dumps(lookData())
    try: writeJsonSafe(LOOKS_FILE, [{'name': t[r, 'name'].val, 'data': json.loads(t[r, 'data'].val)} for r in range(1, t.numRows)], indent=1)
    except Exception as e: storeLog('looks export failed: %s' % e)

# ------------------------------------------------------------------ STORE: presets live on disk, never only inside the .toe
# td/presets.json is the one true copy. The PRESETS table is just a fast copy of it, refilled from disk every time
# the engine starts, so an unsaved / old .toe, a crash, another phone or a cleared browser can't bring back old presets.
# Every write: temp file -> fsync -> read back + compare -> atomic swap (previous file kept as .bak),
# then a restore point (presets + set list + FX presets) in td/history/. Failures are shouted, never just printed.
def _storeStatus():
    s = ('OK' if STORE['ok'] else 'NOT SAVED: ' + STORE['err'][:80]) + ' | %d presets | saved %s' % (STORE['n'], STORE['saved'] or '-')
    try:
        C = op('/project1/CONTROLS')
        if hasattr(C.par, 'Storestatus') and C.par.Storestatus.eval() != s: C.par.Storestatus = s
    except Exception: pass
    return s

def storeInfo():
    return {'ok': STORE['ok'], 'err': STORE['err'], 'saved': STORE['saved'], 'n': STORE['n']}

def _storeAlert(msg):
    """Something went wrong with saving: every phone gets a banner that stays until saving works again."""
    storeLog('ALERT: ' + msg)
    try:
        R = op('/project1/remote_cb').module
        R._all({'t': 'store', 'v': storeInfo(), 'alert': msg})
    except Exception: pass

def _presetRows():
    """The PRESETS table as plain data: 128 entries of {'name', 'data'} or None."""
    t = _bankTable(); out = []
    for i in range(1, BANK_SLOTS + 1):
        nm, data = t[i, 0].val, t[i, 1].val
        if not data: out.append(None); continue
        try: out.append({'name': nm, 'data': json.loads(data)})
        except Exception: storeLog('slot %d in the table is damaged - skipped' % i); out.append(None)
    return out

def _parsePresets(obj):
    """Reads the current format, a restore point, or the old [[name, json-text], ...] list. Raises on anything odd."""
    if isinstance(obj, dict) and obj.get('format') == 'moai-restore': obj = obj['presets']
    if isinstance(obj, dict) and obj.get('format') == 'moai-presets': rows = list(obj.get('slots') or [])
    elif isinstance(obj, list):
        rows = []
        for r in obj:
            if not r or not r[1]: rows.append(None); continue
            rows.append({'name': str(r[0]), 'data': json.loads(r[1]) if isinstance(r[1], str) else r[1]})
    else: raise ValueError('not a preset file')
    if len(rows) > BANK_SLOTS: rows = rows[:BANK_SLOTS]
    rows += [None] * (BANK_SLOTS - len(rows))
    for r in rows:
        if r is not None and not (isinstance(r, dict) and isinstance(r.get('data'), dict) and 'layers' in r['data']):
            raise ValueError('a preset entry is damaged')
    return rows

def _presetDoc(rows, why):
    return {'format': 'moai-presets', 'version': 2, 'saved': _now(), 'why': why,
            'count': sum(1 for r in rows if r), 'slots': rows}

def _sameRows(a, b):
    return [(r['name'], r['data']) if r else None for r in a] == [(r['name'], r['data']) if r else None for r in b]

def _rowsToTable(rows):
    t = _bankTable()
    for i in range(1, BANK_SLOTS + 1):
        r = rows[i - 1]
        nm, data = (r['name'], json.dumps(r['data'])) if r else ('', '')
        if t[i, 0].val != nm: t[i, 0] = nm
        if t[i, 1].val != data: t[i, 1] = data

def _histWrite(why, rows=None):
    """One restore point: presets + set list + FX presets."""
    try:
        rows = _presetRows() if rows is None else rows
        q = qState()
        doc = {'format': 'moai-restore', 'version': 2, 'saved': _now(), 'why': why,
               'presets': _presetDoc(rows, why), 'queue': {'v': list(q['v']), 'pos': q['pos']}, 'fxpresets': list(fxList())}
        tag = ''.join(c if c.isalnum() else '-' for c in str(why))[:32]
        name = '%s_%03d_%s.json' % (time.strftime('%Y%m%d_%H%M%S'), int(time.time() * 1000) % 1000, tag)
        writeJsonSafe(HIST_DIR + '/' + name, doc, bak=False)
        files = sorted(f for f in os.listdir(HIST_DIR) if f.endswith('.json'))
        firsts = {}
        for f in files: firsts.setdefault(f[:8], f)            # first restore point of each day is kept forever
        keepday = set(firsts.values())
        for f in files[:-HIST_KEEP]:
            if f not in keepday:
                try: os.remove(HIST_DIR + '/' + f)
                except Exception: pass
        return name
    except Exception as e:
        storeLog('restore point failed (%s): %s' % (why, e)); return None

def storeSave(why='save'):
    """Writes the presets to disk. True = safely saved. On failure: retried, logged, and every phone is told."""
    rows = _presetRows(); err = None
    for attempt in range(3):
        try: writeJsonSafe(PRESETS_FILE, _presetDoc(rows, why), indent=1); err = None; break
        except Exception as e: err = e; time.sleep(0.05)
    if err is not None:
        STORE.update(ok=False, err=str(err)); _storeStatus()
        _storeAlert('PRESETS NOT SAVED (%s): %s' % (why, err))
        return False
    was = STORE['ok']
    STORE.update(ok=True, err='', saved=time.strftime('%H:%M:%S'), n=sum(1 for r in rows if r))
    _histWrite(why, rows); _storeStatus()
    if not was:
        storeLog('saving works again')
        try: op('/project1/remote_cb').module._all({'t': 'store', 'v': storeInfo()})
        except Exception: pass
    return True

def _archiveOnly(f):
    """Restore points that are NOT a step in the timeline: the stale copy a .toe held, or the state just before a restore."""
    b = os.path.basename(f)
    return '_project-copy' in b or '_before-restore' in b or '_before-reload' in b

def _diskPresets():
    """Newest readable copy: presets.json, then the newest restore point (written after every save), then .bak, then older ones."""
    try: hist = [HIST_DIR + '/' + f for f in sorted(os.listdir(HIST_DIR), reverse=True) if f.endswith('.json')]
    except Exception: hist = []
    good = [h for h in hist if not _archiveOnly(h)]             # real states, newest first
    cands = [PRESETS_FILE] + good[:1] + [PRESETS_FILE + '.bak'] + good[1:] + [h for h in hist if _archiveOnly(h)]
    for p in cands:
        if not os.path.exists(p): continue
        try: return _parsePresets(readJson(p)), p
        except Exception as e: storeLog('could not read %s: %s' % (os.path.basename(p), e))
    return None, None

def storeBoot():
    """Engine start: the disk copy wins over whatever the .toe remembered. Nothing is ever thrown away."""
    tbl = _presetRows()
    rows, src = _diskPresets()
    if rows is None:
        if any(tbl):
            storeLog('no readable preset file - writing the %d presets kept in the project to disk' % sum(1 for r in tbl if r))
            storeSave('rescued from project')
        else:
            STORE.update(n=0, saved='-'); storeLog('no presets yet')
        STORE['from'] = 'project'; _storeStatus(); return
    if not _sameRows(tbl, rows):
        if any(tbl): _histWrite('project copy replaced at start', tbl)   # the .toe's version stays restorable
        _rowsToTable(rows)
        storeLog('loaded %d presets from %s%s' % (sum(1 for r in rows if r), os.path.basename(src),
                 ' (the project file held a different, older copy - kept in td/history)' if any(tbl) else ''))
    else:
        storeLog('loaded %d presets from %s' % (sum(1 for r in rows if r), os.path.basename(src)))
    STORE.update(n=sum(1 for r in rows if r), **{'from': src})
    try:
        old = readJson(PRESETS_FILE) if src == PRESETS_FILE else None
        if src != PRESETS_FILE or not (isinstance(old, dict) and old.get('format') == 'moai-presets'):
            storeSave('restored at start' if src != PRESETS_FILE else 'converted to new format')
        else:
            STORE['saved'] = old.get('saved', '')[-8:]
    except Exception: storeSave('start')
    q = qState()                                               # set list: drop slots that are empty now
    keep = [x for x in q['v'] if 1 <= x <= BANK_SLOTS and rows[x - 1]]
    if keep != q['v']: qSet(keep)
    _storeStatus()

def _storeNotify():
    """Presets changed underneath the phones (restore / reload): send them everything again."""
    try:
        R = op('/project1/remote_cb').module
        R._all({'t': 'bank', 'bank': bankList()}); R._all(qMsg()); R._all(R.fxpMsg())
        R._all({'t': 'store', 'v': storeInfo()}); R._publish(R.state())
        for i in range(1, BANK_SLOTS + 1): R._all({'t': 'thumb', 's': i, 'img': thumbB64(i)})
    except Exception as e: storeLog('phone refresh failed: %s' % e)

def storeReload():
    """Read presets.json again (e.g. after copying one in by hand)."""
    rows, src = _diskPresets()
    if rows is None: _storeAlert('No readable preset file found'); return False
    if not _sameRows(_presetRows(), rows): _histWrite('before reload')
    _rowsToTable(rows); STORE.update(n=sum(1 for r in rows if r), **{'from': src})
    storeLog('reloaded %d presets from %s' % (STORE['n'], os.path.basename(src)))
    _storeStatus(); _storeNotify(); return True

def storeHistory(n=40):
    try: files = sorted((f for f in os.listdir(HIST_DIR) if f.endswith('.json')), reverse=True)[:n]
    except Exception: return []
    out = []
    for f in files:
        p = f[:-5].split('_', 3)                              # 20261107_120102_123_save-4
        when = '%s-%s-%s %s:%s:%s' % (p[0][:4], p[0][4:6], p[0][6:8], p[1][:2], p[1][2:4], p[1][4:6]) if len(p) >= 2 and len(p[0]) == 8 else f
        out.append({'f': f, 'when': when, 'why': (p[3] if len(p) > 3 else '').replace('-', ' ')})
    return out

def storeRestore(fname):
    """Bring back a restore point (the current state becomes a restore point first, so this can be undone too)."""
    p = HIST_DIR + '/' + os.path.basename(str(fname))
    try:
        doc = readJson(p); rows = _parsePresets(doc)
    except Exception as e:
        _storeAlert('Restore point unreadable: %s' % e); return False
    _histWrite('before restore')
    _rowsToTable(rows)
    if isinstance(doc, dict) and isinstance(doc.get('queue'), dict):
        Q['v'] = [int(x) for x in doc['queue'].get('v', []) if 1 <= int(x) <= BANK_SLOTS and rows[int(x) - 1]][:64]
        Q['pos'] = -1; _qSave()
    if isinstance(doc, dict) and isinstance(doc.get('fxpresets'), list):
        FXP['list'] = doc['fxpresets']; _fxSave()
    ok = storeSave('restored ' + os.path.basename(p)[:15])
    storeLog('restored %s' % os.path.basename(p)); _storeNotify()
    return ok

def storeUndo():
    """One step back: the newest restore point whose presets differ from what is loaded now."""
    cur = _presetRows()
    for h in storeHistory(400):
        if '_project-copy' in h['f']: continue                   # an old .toe copy is never "the previous step"
        try: rows = _parsePresets(readJson(HIST_DIR + '/' + h['f']))
        except Exception: continue
        if not _sameRows(rows, cur): return storeRestore(h['f'])
    _storeAlert('Nothing to undo'); return False

def storeBackupNow(why='manual backup'):
    n = _histWrite(why); storeLog('restore point %s' % n); return n

# ------------------------------------------------------------------ preset bank (128 slots)
def _bankTable():
    t = op('/project1/PRESETS')
    if t.numRows < BANK_SLOTS + 1:
        while t.numRows < BANK_SLOTS + 1: t.appendRow(['', ''])
    return t

OBJKEYS = ['Angle', 'Tilt', 'Speed', 'Spinboost', 'Autospin', 'Spinrev', 'Spinaxis', 'Motion', 'Motionamt', 'Animspeed', 'Animbeat',
           'Modelx', 'Modely', 'Modelz', 'Modelscale', 'Modelturn', 'Modeltilt']
MODEL3D = {'Modelx': 0.0, 'Modely': 0.0, 'Modelz': 0.0, 'Modelscale': 1.0, 'Modelturn': 0.0, 'Modeltilt': 0.0}

def snapshot():
    C = op('/project1/CONTROLS')
    d = lookData()
    d['model'] = C.par.Model.eval()
    d['cam'] = {k: round(float(C.par[k].eval()), 4) for k in CAMKEYS + ['Pan']}
    d['obj'] = {k: (bool(C.par[k].eval()) if k in ('Autospin', 'Spinrev') else C.par[k].eval() if k in ('Motion', 'Spinaxis') else round(float(C.par[k].eval()), 4)) for k in OBJKEYS}
    d['src'] = srcData()
    d['obj']['angle'] = round(S['angle'], 3)
    d['extra'] = {}
    for k in EXTRAPARS:                                          # small look settings that used to leak between presets
        try:
            v = C.par[k].eval(); d['extra'][k] = v if isinstance(v, (bool, str)) else round(float(v), 4)
        except Exception: pass
    return d

HIST = {'undo': [], 'redo': [], 't': 0.0}
def histMark(label):
    """Called just before a command from the remote changes the look. One drag / quick burst = one step."""
    now = time.time()
    if HIST['undo'] and now - HIST['t'] < 1.2: HIST['t'] = now; return False
    try: d = snapshot()
    except Exception: return False
    HIST['t'] = now
    HIST['undo'].append({'d': d, 'l': str(label)[:40], 'at': time.strftime('%H:%M:%S')}); del HIST['undo'][:-40]
    del HIST['redo'][:]
    return True

def histGo(redo=False):
    a, b = (HIST['redo'], HIST['undo']) if redo else (HIST['undo'], HIST['redo'])
    if not a: return False
    it = a.pop(); b.append({'d': snapshot(), 'l': it['l'], 'at': it['at']})
    _bankApply(it['d'], 0.0, True, True, True, cut=True, slot=None)
    HIST['t'] = 0.0; S['dirty'] = True
    return True

def histList():
    return {'u': [[x['at'], x['l']] for x in HIST['undo'][-15:]], 'r': len(HIST['redo'])}

EXTRAPARS = ['Flip', 'Modelyaw', 'Cammirror', 'Clipspeed', 'Clipbounce']

# ------------------------------------------------------------------ source (what the effects work on) in presets
MPARS = ['on', 'vis', 'kind', 'file', 'mode', 'cropl', 'cropr', 'cropt', 'cropb', 'keyon', 'keycolor', 'keyhex', 'keytol', 'keysoft', 'keyspill',
         'keyshrink', 'objx', 'objy', 'objscale', 'objz', 'objturn', 'objtilt', 'motion', 'maxis', 'mspeed', 'mamt', 'mrev', 'name', 'fzoom', 'fx', 'fy', 'frot', 'op', 'speed', 'trimin', 'trimout', 'fit']

def _mval(par):
    v = par.eval()
    return bool(v) if par.style == 'Toggle' else (round(float(v), 4) if isinstance(v, float) else v)

def mediaSlotData(C, i): return {n: _mval(mp(C, i, n)) for n in MPARS}

SLOTLOG = []
def mediaSlotClear(C, i):
    if mp(C, i, 'on').eval() or mp(C, i, 'file').eval():                 # who emptied a layer that had something in it
        import traceback
        SLOTLOG.append((time.strftime('%H:%M:%S'), i, mp(C, i, 'file').eval(), ' < '.join(f.name for f in traceback.extract_stack()[-5:-1])))
        del SLOTLOG[:-30]
    for n in MPARS:
        par = mp(C, i, n)
        try: par.val = par.default
        except Exception: pass
    mp(C, i, 'on').val = False; mp(C, i, 'vis').val = True; mp(C, i, 'file').val = ''; mp(C, i, 'kind').val = 'video'
    mf = op('/project1/mf%d' % i)
    if mf is not None: mf.par.file = ''; mf.par.play = False

def srcData():
    C = op('/project1/CONTROLS'); R = op('/project1/remote_cb').module
    return {'camsrc': C.par.Camsrc.eval(), 'cammix': round(float(C.par.Cammix.eval()), 3), 'camfit': C.par.Camfit.eval(),
            'mslots': {str(i): mediaSlotData(C, i) for i in MSLOTS if mp(C, i, 'on').eval()},
            'layers': layerOrder(C), 'links': C.par.Links.eval(), 'noreact': C.par.Noreact.eval() if hasattr(C.par, 'Noreact') else '', 'modelname': C.par.Modelname.eval() if hasattr(C.par, 'Modelname') else '',
            'frame': {n: round(float(C.par[n].eval()), 4) for n in FRAMEPARS},
            'opacity': {n: round(float(C.par[n].eval()), 4) for n in OPPARS},
            'clip': R.CLIP['id'] if C.par.Clipstate.eval() == 'loop' else None,
            'draw': bool(C.par.Drawon.eval()), 'drawmix': round(float(C.par.Drawmix.eval()), 3)}

KEYPARS = ['Keyon', 'Keycolor', 'Keytol', 'Keysoft', 'Keyspill', 'Keyshrink', 'Objx', 'Objy', 'Objscale']
FRAMEPARS = ['F%s%s' % (l, n) for l in ('cam', 'draw') for n in ('zoom', 'x', 'y', 'rot')]
OPPARS = ['Op' + t for t in ('model', 'camera', 'draw')]      # per-layer brightness / see-through (media layers: M<n>op)

def _legacySlots(s):
    """Presets from before media layers were slots: Images -> layer 1, Videos -> layer 2 (with their settings)."""
    R = op('/project1/remote_cb').module
    out = {}
    img, vid = dict(s), dict(s)
    if 'vmedia' not in s and s.get('media') and R.isVideo(s['media']):          # even older: one slot for both
        vid = {'vmedia': s['media'], 'vmediamode': s.get('mediamode', 'flat'), 'vmediaon': s.get('mediaon', True),
               'vcrop': s.get('crop'), 'vkey': s.get('key') or {}}
        img = {}
    fr, opd = s.get('frame') or {}, s.get('opacity') or {}
    for i, pre, crop, key, fpre, opk in ((1, 'media', 'crop', 'key', 'Fimg', 'Opimages'), (2, 'vmedia', 'vcrop', 'vkey', 'Fvid', 'Opvideos')):
        src = img if i == 1 else vid
        f = src.get(pre)
        if not f: continue
        k = src.get(key) or {}
        c = src.get(crop) or [0, 0, 0, 0]
        out[str(i)] = {'on': True, 'vis': bool(src.get(pre + 'on', True)), 'kind': 'video' if R.isVideo(f) else 'image', 'file': f,
                       'mode': src.get(pre + 'mode', 'flat'), 'cropl': c[0], 'cropr': c[1], 'cropt': c[2], 'cropb': c[3],
                       'keyon': bool(k.get('Keyon', False)), 'keycolor': k.get('Keycolor', 'auto'),
                       'keytol': k.get('Keytol', 0.45), 'keysoft': k.get('Keysoft', 0.25), 'keyspill': k.get('Keyspill', 0.7), 'keyshrink': k.get('Keyshrink', 1.0),
                       'objx': k.get('Objx', 0.0), 'objy': k.get('Objy', 0.0), 'objscale': k.get('Objscale', 1.0),
                       'fzoom': fr.get(fpre + 'zoom', 1.0), 'fx': fr.get(fpre + 'x', 0.0), 'fy': fr.get(fpre + 'y', 0.0), 'frot': fr.get(fpre + 'rot', 0.0),
                       'op': opd.get(opk, 1.0)}
    return out

def applySrc(d, slot=None):
    """Presets saved before sources existed just show the statue."""
    import os
    C = op('/project1/CONTROLS'); R = op('/project1/remote_cb').module
    s = dict(d.get('src') or {'camsrc': 'off', 'clip': None, 'draw': False})
    ms = s.get('mslots')
    if ms is None: ms = _legacySlots(s)
    for i in MSLOTS:
        m = ms.get(str(i))
        if not m:
            if mp(C, i, 'on').eval() or mp(C, i, 'file').eval(): mediaSlotClear(C, i)
            continue
        for n in MPARS:
            if n == 'file': continue
            try: mp(C, i, n).val = m[n] if n in m else mp(C, i, n).default      # older presets: defaults, not leftovers
            except Exception: pass
        f = m.get('file') or ''
        if f and mp(C, i, 'file').eval() != f and not R.mediaPlay(f, slot=i, keep=True):
            storeLog('preset media missing: %s' % f); R.mediaStop(i)          # deleted file: show nothing, not the old picture
        elif not f: R.mediaStop(i)
    order = s.get('layers')
    if not order:                                               # older presets: the camera's own BEHIND mode set the order
        order = list(LAYER_DEFAULT)
        if s.get('camsrc') == 'behind': order.remove('camera'); order.append('camera')
    C.par.Layerorder = ','.join(_LEGACY.get(k, k) for k in order)
    C.par.Links = s.get('links', '')
    if hasattr(C.par, 'Noreact'): C.par.Noreact = s.get('noreact', '')
    if hasattr(C.par, 'Modelname'): C.par.Modelname = s.get('modelname', '')
    fr = s.get('frame') or {}
    for n in FRAMEPARS: C.par[n] = fr.get(n, C.par[n].default)
    opd = s.get('opacity') or {}
    for n in OPPARS: C.par[n] = opd.get(n, 1.0)
    if getattr(R, 'CAMERA_REMOVED', False):                         # phone camera removed: old presets never switch it back on
        C.par.Camsrc = 'off'
        if C.par.Clipstate.eval() != 'off': C.par.Clipstate = 'off'
    else:
        if s.get('clip') and R.clipPlay(s['clip']): pass
        elif C.par.Clipstate.eval() == 'loop': R.clipLive()
        C.par.Camsrc = 'cam' if s.get('camsrc') == 'behind' else s.get('camsrc', 'off')   # BEHIND is now just the layer order
    if 'cammix' in s: C.par.Cammix = s['cammix']
    if 'camfit' in s: C.par.Camfit = s['camfit']
    C.par.Drawon = False                                          # drawings are media layers now
    meta = d.get('_meta') or {}
    for i in MSLOTS:
        R.DRAWS[i] = {'img': None, 'new': True}
    draws = dict(meta.get('draws') or {})
    if s.get('draw') and meta.get('draw') and not any((m or {}).get('kind') == 'draw' for m in ms.values()):   # older preset: one drawing
        n = R.mediaFree('draw')
        if n:
            draws[str(n)] = meta['draw']
            fr = s.get('frame') or {}
            for a, b in (('zoom', 'fzoom'), ('x', 'fx'), ('y', 'fy'), ('rot', 'frot')):
                if 'Fdraw' + a in fr: mp(C, n, b).val = fr['Fdraw' + a]
    for k, fn in draws.items():
        dp = DRAW_DIR + '/' + os.path.basename(fn)
        if os.path.exists(dp):
            import cv2
            im = cv2.imread(dp, cv2.IMREAD_UNCHANGED)
            if im is not None:
                if im.shape[2] == 3: im = R.drawRGBA(im)
                else: im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
                R.DRAWS[int(k)] = {'img': np.ascontiguousarray(im[::-1]), 'new': True}

def drawPath(slot): return '%s/td/drawings/p%d.png' % (project.folder, int(slot))

FXP_FILE = project.folder + '/td/fxpresets.json'
FXP = {'list': None}

def fxList():
    if FXP['list'] is None:
        v = readJsonSafe(FXP_FILE, [])
        FXP['list'] = v if isinstance(v, list) else []
    return FXP['list']

def _fxSave():
    try: writeJsonSafe(FXP_FILE, fxList()); _histWrite('fx presets'); return True
    except Exception as e: _storeAlert('FX presets NOT saved: %s' % e); return False

def fxSave(name=None):
    L = fxList(); lay = lookData()['layers']
    L.append({'name': (name or ' + '.join(r['label'] for r in layers() if _isOn(r))[:40] or 'Clean')[:40], 'layers': lay,
              'lcols': lookData()['lcols']})
    _fxSave(); return len(L) - 1

def fxDelete(i):
    L = fxList()
    if 0 <= i < len(L): L.pop(i); _fxSave()

def fxRename(i, name):
    L = fxList()
    if 0 <= i < len(L): L[i]['name'] = str(name)[:40]; _fxSave()

def layersApply(lay, fade=0.0, lcols=None):
    """Swap the effect stack only (source, statue, camera stay), crossfading the amounts."""
    T = absTime.seconds
    if lcols is not None: colsApply(lcols, fade)
    old = {r['key']: (_isOn(r), float(r['amt']), float(r['p1'])) for r in layers()}
    for r in layers():
        if r['key'] not in lay: setLayer(r['key'], on=False)
    for k, v in lay.items(): setLayer(k, on=bool(v[0]), amt=v[1], p1=v[2])
    if fade > 0.01:
        for k, (on0, a0, p0) in old.items():
            on1, a1, p1 = lay.get(k, [0, a0, p0])
            A0 = a0 if on0 else 0.0; A1 = float(a1) if on1 else 0.0
            if abs(A0 - A1) > 0.001: S['fades'][k] = {'t0': T, 'dur': fade, 'a0': A0, 'a1': A1, 'p1': p0}
    S['dirty'] = True

def fxApply(i, fade=0.0):
    L = fxList()
    if 0 <= i < len(L): layersApply(L[i]['layers'], fade, L[i].get('lcols', {}))

def fxFromPreset(slot, fade=0.0):
    t = _bankTable()
    if t[slot, 1].val:
        d = json.loads(t[slot, 1].val); layersApply(d.get('layers', {}), fade, d.get('lcols', {}))

def bankList():
    t = _bankTable(); out = []
    for i in range(1, BANK_SLOTS + 1):
        nm, data = t[i, 0].val, t[i, 1].val
        if not data: out.append(None); continue
        try: d = json.loads(data)
        except Exception: out.append(None); continue
        out.append({'name': nm, 'on': [k for k, v in d.get('layers', {}).items() if v[0]], 'scene': d.get('scene', 'solid'), 'model': d.get('model', ''),
                    'group': (d.get('_meta') or {}).get('group', '')})
    return out

def bankSave(slot, name=None):
    """Saves what is on screen into a slot. Returns True only once it is safely on disk."""
    slot = int(slot)
    if not 1 <= slot <= BANK_SLOTS: return False
    t = _bankTable()
    d = snapshot()
    stamp = time.strftime('%Y%m%d_%H%M%S') + '%03d' % (int(time.time() * 1000) % 1000)
    meta = {'saved': _now(), 'thumb': 'p%d_%s.jpg' % (slot, stamp)}   # own picture file per save: a restore point keeps its picture
    try: g0 = (json.loads(t[slot, 1].val).get('_meta') or {}).get('group', '') if t[slot, 1].val else ''
    except Exception: g0 = ''
    if g0: meta['group'] = g0                                   # updating a preset keeps its group
    try: q0 = (json.loads(t[slot, 1].val).get('_meta') or {}).get('quick') if t[slot, 1].val else None
    except Exception: q0 = None
    if q0: meta['quick'] = q0                                    # ... and its quick controls
    try:
        R = op('/project1/remote_cb').module; C_ = op('/project1/CONTROLS'); draws = {}
        for i in MSLOTS:
            img = (R.DRAWS.get(i) or {}).get('img')
            if mp(C_, i, 'on').eval() and mp(C_, i, 'kind').eval() == 'draw' and img is not None:
                import cv2
                fn = 'p%d_%s_d%d.png' % (slot, stamp, i)
                os.makedirs(DRAW_DIR, exist_ok=True)
                cv2.imwrite(DRAW_DIR + '/' + fn, cv2.cvtColor(np.ascontiguousarray(img[::-1]), cv2.COLOR_RGBA2BGRA))
                draws[str(i)] = fn
        if draws: meta['draws'] = draws
    except Exception as er: storeLog('drawing save failed (slot %d): %s' % (slot, er)); meta.pop('draws', None)
    d['_meta'] = meta
    t[slot, 0] = (name or t[slot, 0].val or ('Preset %d' % slot))[:60]
    t[slot, 1] = json.dumps(d)
    try: thumbSave(slot)
    except Exception as e: storeLog('thumb failed (slot %d): %s' % (slot, e))
    return storeSave('save %d' % slot)

def bankClear(slot):
    slot = int(slot)
    if not 1 <= slot <= BANK_SLOTS: return False
    t = _bankTable(); t[slot, 0] = ''; t[slot, 1] = ''        # its picture file stays: older restore points still use it
    q = qState()
    if slot in q['v']: qSet([x for x in q['v'] if x != slot])
    return storeSave('clear %d' % slot)

def bankRename(slot, name):
    t = _bankTable()
    if t[slot, 1].val: t[slot, 0] = str(name)[:60]; return storeSave('rename %d' % slot)
    return False

def _groupName(g): return ' '.join(str(g or '').split())[:30]

def bankSetGroup(slot, group):
    """Put a preset in a group (empty = no group). Stored with the preset on disk."""
    t = _bankTable(); slot = int(slot)
    if not 1 <= slot <= BANK_SLOTS or not t[slot, 1].val: return False
    d = json.loads(t[slot, 1].val); m = dict(d.get('_meta') or {}); g = _groupName(group)
    if g: m['group'] = g
    else: m.pop('group', None)
    d['_meta'] = m; t[slot, 1] = json.dumps(d)
    return storeSave('group %d' % slot)

def bankSetText(slot, n, v):
    """Quick-control text: the new words also go into the preset on air, so coming back to it keeps them."""
    t = _bankTable(); slot = int(slot or 0)
    if not 1 <= slot <= BANK_SLOTS or not t[slot, 1].val: return False
    d = json.loads(t[slot, 1].val)
    if n == 1: d.setdefault('text', {})['Textstr'] = v
    else:
        tx = d.setdefault('texts', {})
        if str(n) not in tx: return False
        tx[str(n)]['Textstr'] = v
    t[slot, 1] = json.dumps(d)
    return storeSave('text %d' % slot)

def bankRenameGroup(old, new):
    """Rename a group (new = '' takes every preset out of it)."""
    t = _bankTable(); old = _groupName(old); new = _groupName(new); n = 0
    for i in range(1, BANK_SLOTS + 1):
        if not t[i, 1].val: continue
        d = json.loads(t[i, 1].val); m = dict(d.get('_meta') or {})
        if m.get('group', '') != old: continue
        if new: m['group'] = new
        else: m.pop('group', None)
        d['_meta'] = m; t[i, 1] = json.dumps(d); n += 1
    return storeSave('group rename') if n else True

# ------------------------------------------------------------------ quick controls (LIVE): pinned sliders / switches / effect settings
QUICK_FILE = STORE_DIR + '/quick.json'                         # pins shown with every preset
QUICK_MAX = 12

# ------------------------------------------------------------------ linked layers (swap one off, the other on)
def visPar(k):
    """The ON/OFF switch of a layer that can be swapped: picture / video / drawing layers, 3D models, text layers."""
    if k[:1] == 'm' and k[1:].isdigit() and 1 <= int(k[1:]) <= 6: return 'M%svis' % k[1:]
    return {'model': 'Statue', 'text': 'Texton', 'text2': 'T2on', 'text3': 'T3on'}.get(k)

def layerSwap(a, b):
    C = op('/project1/CONTROLS'); pa, pb = visPar(a), visPar(b)
    if not pa or not pb or pa == pb: return False
    on = bool(C.par[pa].eval())
    import time as _t
    SWAPT[a] = SWAPT[b] = _t.perf_counter()                       # this switch uses the chosen fade (0 = instant cut)
    C.par[pa] = not on; C.par[pb] = on                            # a was showing -> b shows instead, and back
    return True

SWAPT = {}
def swapTc(C, k, tc):
    """Fade speed for layer k: right after a linked swap, the Swapfade time (0 = cut on the next frame)."""
    import time as _t
    t = SWAPT.get(k)
    if t is None: return tc
    f = float(C.par.Swapfade.eval()) if hasattr(C.par, 'Swapfade') else 0.0
    if _t.perf_counter() - t > f + 0.3: SWAPT.pop(k, None); return tc
    return f / 4.0 if f > 0.001 else 0.0

def unlink(C, k):
    """A removed layer leaves its link (so no ghost row stays behind)."""
    v = [x for x in str(C.par.Links.eval() or '').split(',') if x and k not in x.split('-')]
    C.par.Links = ','.join(v)

def _qid(it): return '%s:%s:%s:%s' % (it.get('k'), it.get('p', it.get('t', it.get('a', ''))), it.get('e', it.get('b', '')), it.get('f', ''))

def _qclean(it):
    """A pinned item: a slider ('par'), a switch ('tog') or one setting of one effect on one layer ('fx')."""
    R = op('/project1/remote_cb').module; k = it.get('k')
    if k in ('par', 'tog'):
        p = str(it.get('p', ''))
        if p in R.ALLOWED: return {'k': k, 'p': p}
    elif k == 'swap':
        a, b = str(it.get('a', '')), str(it.get('b', ''))
        if visPar(a) and visPar(b) and a != b: return {'k': 'swap', 'a': a, 'b': b}
    elif k == 'fx':
        t, e, f = str(it.get('t', '')), str(it.get('e', '')), str(it.get('f', ''))
        if (t == 'all' or t in FXTGTS) and any(r['key'] == e for r in layers()) and f in ('amt', 'p1', 'on'):
            return {'k': 'fx', 't': t, 'e': e, 'f': f}
    return None

def quickAll():
    t = _bankTable(); per = {}
    for i in range(1, BANK_SLOTS + 1):
        if not t[i, 1].val: continue
        try: q = (json.loads(t[i, 1].val).get('_meta') or {}).get('quick')
        except Exception: q = None
        if q: per[str(i)] = q
    return {'all': readJsonSafe(QUICK_FILE, []) or [], 'p': per}

def quickEdit(do, scope, item, slot=None, d=0):
    """Pin / unpin / move a quick control, for one preset (scope 'preset') or for every preset ('all')."""
    it = _qclean(item or {})
    if it is None: return False
    if scope == 'all': cur = list(readJsonSafe(QUICK_FILE, []) or [])
    else:
        t = _bankTable(); slot = int(slot or 0)
        if not 1 <= slot <= BANK_SLOTS or not t[slot, 1].val: return False
        dd = json.loads(t[slot, 1].val); m = dict(dd.get('_meta') or {}); cur = list(m.get('quick') or [])
    ids = [_qid(x) for x in cur]; i = ids.index(_qid(it)) if _qid(it) in ids else -1
    if do == 'pin' and i < 0 and len(cur) < QUICK_MAX: cur.append(it)
    elif do == 'unpin' and i >= 0: cur.pop(i)
    elif do == 'move' and i >= 0:
        j = max(0, min(len(cur) - 1, i + (1 if d > 0 else -1))); cur.insert(j, cur.pop(i))
    else: return True
    if scope == 'all':
        try: return writeJsonSafe(QUICK_FILE, cur)
        except Exception as er: storeLog('quick controls not saved: %s' % er); return False
    if cur: m['quick'] = cur
    else: m.pop('quick', None)
    dd['_meta'] = m; t[slot, 1] = json.dumps(dd)
    return storeSave('quick %d' % slot)

def bankExport():                                              # old name, kept for anything that still calls it
    return storeSave('export')

def bankImport():                                              # old name: reload the presets from disk
    return storeReload()

def bankLoad(slot, fade=0.0, cam=True, model=True, text=False):
    t = _bankTable()
    try: slot = int(slot)
    except Exception: return False
    if not 1 <= slot <= BANK_SLOTS or not t[slot, 1].val: return False
    try: d = json.loads(t[slot, 1].val)
    except Exception as e:
        storeLog('preset %d is unreadable: %s' % (slot, e)); _storeAlert('Preset %d is damaged - use Undo / a restore point' % slot)
        return False
    C = op('/project1/CONTROLS')
    newModel = bool(model and d.get('model') and d['model'] != C.par.Model.eval())
    newScene = bool(d.get('scene') and d['scene'] != C.par.Scene.eval())
    s_ = d.get('src') or {}
    newSrc = (sorted(m.get('file', '') for m in (s_.get('mslots') or {}).values()) != sorted(mp(C, i, 'file').eval() for i in MSLOTS if mp(C, i, 'on').eval())) \
             or (s_.get('camsrc', 'off') != C.par.Camsrc.eval() and not getattr(op('/project1/remote_cb').module, 'CAMERA_REMOVED', False))
    S['bank'] = slot; S['dirty'] = True
    tx = dict(d.get('text') or {})
    if tx: tx.setdefault('Textcm', 0)                           # presets from before text gradients: named colour
    keepText = bool(text and C.par.Texton.eval() and tx.get('Texton') and float(tx.get('Textamount', 1.0)) > 0.001
                    and not op('/project1/fx_text').bypass)
    if keepText: textMorphStart(tx, max(fade, 1.4))              # words stay up and morph into the new ones
    if fade > 0.01 and (newModel or newScene or newSrc):
        # statue / style changes hide in a live dip: everything swaps instantly at the darkest point
        xfadeStart(fade, lambda: _bankApply(d, 0.0, cam, model, text, cut=True, slot=slot), keeptext=keepText)
    else:
        _bankApply(d, fade, cam, model, text, cut=fade <= 0.01, slot=slot)
    return True

def _bankApply(d, fade, cam, model, text, cut, slot=None):
    C = op('/project1/CONTROLS'); T = absTime.seconds
    try: applySrc(d, slot)
    except Exception as er: print('preset source failed', er)
    old = {r['key']: (_isOn(r), float(r['amt']), float(r['p1'])) for r in layers()}
    S['colfade'] = fade
    applyLook(d, text=text)                                      # writes the table (instant values)
    S['colfade'] = 0.0
    if not text and not C.par.Textpin.eval(): C.par.Texton = False
    if fade > 0.01:
        for k, (on0, a0, p0) in old.items():
            on1, a1, p1 = d['layers'].get(k, [0, a0, p0])
            A0 = a0 if on0 else 0.0; A1 = float(a1) if on1 else 0.0
            if abs(A0 - A1) > 0.001:
                S['fades'][k] = {'t0': T, 'dur': fade, 'a0': A0, 'a1': A1, 'p1': p0}
    if model and d.get('model') and d['model'] != C.par.Model.eval():
        S['modelcut'] = True                                     # presets never play the statue swap animation
        C.par.Model = d['model']
    ob = d.get('obj', {})
    if 'Spinaxis' not in ob: C.par.Spinaxis = 'y'                # older presets: spin turns around Y
    if 'Spinrev' not in ob: C.par.Spinrev = False
    for k, v in MODEL3D.items():                                 # older presets: the models sit where they always did
        if k not in ob: C.par[k] = v
    for k, v in ob.items():                                      # statue pose: angle, tilt, spin
        try: C.par[k] = v
        except Exception: pass
    if 'angle' in d.get('obj', {}): S['angle'] = float(d['obj']['angle'])
    ex = d.get('extra') or {}
    for k in EXTRAPARS:                                          # older presets: back to the default, not the last look's value
        try: C.par[k] = ex[k] if k in ex else C.par[k].default
        except Exception: pass
    if cam and d.get('cam'):
        for k, v in d['cam'].items():
            try: C.par[k] = v
            except Exception: pass
        if cut:
            CS['cur'] = None; CS['pan'] = float(C.par.Pan.eval()); CS['blend_until'] = 0.0; CS['orb'] = 0.0
        else:
            CS['blend_until'] = T + max(fade, 0.3)

# ------------------------------------------------------------------ set list: presets in playing order, ◀ ▶ on the phone
QUEUE_FILE = project.folder + '/td/queue.json'
Q = {'v': None, 'pos': -1}

def qState():
    if Q['v'] is None:
        try:
            d = readJsonSafe(QUEUE_FILE, {}) or {}
            Q['v'] = [int(x) for x in d.get('v', [])][:64]; Q['pos'] = int(d.get('pos', -1))
        except Exception:
            Q['v'] = []; Q['pos'] = -1
    if not (-1 <= Q['pos'] < len(Q['v'])): Q['pos'] = -1
    return Q

def qMsg():
    q = qState(); return {'t': 'queue', 'v': list(q['v']), 'pos': q['pos']}

def _qSave():
    try: writeJsonSafe(QUEUE_FILE, {'v': Q['v'], 'pos': Q['pos']}); return True
    except Exception as e: _storeAlert('Set list NOT saved: %s' % e); return False

def qSet(v):
    q = qState(); t = _bankTable()
    cur = q['v'][q['pos']] if 0 <= q['pos'] < len(q['v']) else None
    out = []
    for x in list(v or [])[:64]:
        try: x = int(x)
        except Exception: continue
        if 1 <= x <= BANK_SLOTS and t[x, 1].val: out.append(x)
    changed = out != q['v']
    q['v'] = out; q['pos'] = out.index(cur) if cur in out else -1
    _qSave(); qPrewarm()
    if changed: _histWrite('set list')

def qGo(i, fade=0.0):
    q = qState(); n = len(q['v'])
    if not n: return
    q['pos'] = int(i) % n; _qSave()
    bankLoad(q['v'][q['pos']], fade=fade, cam=True, model=True, text=True)
    qPrewarm()

def qSync(slot):
    """A preset tapped directly: if it's in the set list, the arrows continue from there."""
    q = qState(); n = len(q['v'])
    if slot not in q['v']: return False
    st = max(0, q['pos'])
    for d in range(n):
        j = (st + d) % n
        if q['v'][j] == slot: q['pos'] = j; break
    _qSave(); qPrewarm(); return True

def qPrewarm():
    """Get the NEXT preset ready while this one plays: its animated model and its picture / video are loaded now."""
    q = qState(); n = len(q['v'])
    if not n: return
    t = _bankTable(); nxt = q['v'][(q['pos'] + 1) % n]
    try: d = json.loads(t[nxt, 1].val or '{}')
    except Exception: return
    g = animComp(animInfo(d.get('model')))
    if g is not None:
        for o in g.findChildren():
            if o.OPType in ('importselectPOP', 'importselectTOP', 'fileinSOP', 'moviefileinTOP') and o.totalCooks == 0:
                try: o.cook(force=True)
                except Exception: pass
    sd = d.get('src') or {}
    med = next((m.get('file') for m in (sd.get('mslots') or {}).values() if m.get('file')), None) or sd.get('media') or sd.get('vmedia')
    if med:
        R = op('/project1/remote_cb').module
        for rel, full, kind in R._mediaFiles():
            if rel == med:
                mn = op('/project1/media_next')
                if mn is None:
                    mn = op('/project1').create(moviefileinTOP, 'media_next'); mn.par.play = False
                    mf = op('/project1/mf1'); mn.nodeX = mf.nodeX; mn.nodeY = mf.nodeY - 150
                if mn.par.file.eval() != full: mn.par.file = full
                try: mn.cook(force=True)                         # decodes the first frame now, not at the switch
                except Exception: pass
                break

# ------------------------------------------------------------------ preset dip (live old look -> dark -> live new look)
XF = {'on': False, 't0': 0.0, 'dur': 1.0, 'phase': 'out', 'pending': None}

def xfadeStart(dur, pending=None, keeptext=False):
    """Fade the running look down (it keeps moving), run `pending` at the dark point, fade the new look up."""
    x = op('/project1/xf_mix')
    if x is None:
        if pending: pending()
        return
    if XF['on'] and XF['phase'] == 'out' and XF['pending']:    # a switch during a switch: finish the old one now
        try: XF['pending']()
        except Exception as e: print('preset dip', e)
    XF.update(on=True, t0=absTime.seconds, dur=max(0.1, float(dur)) * 0.5, phase='out', pending=pending, keep=bool(keeptext))
    if keeptext: x.par.cross = 0.0; x.bypass = True                # the words stay lit, only the picture dips
    else: x.bypass = False

def _dipLevel(v):
    if XF.get('keep'): op('/project1/fx_text').par.vec6valuey = v
    else: op('/project1/xf_mix').par.cross = v

def xfadeUpdate(T):
    if not XF['on']: return
    x = op('/project1/xf_mix')
    k = min(1.0, (T - XF['t0']) / XF['dur']); e = k * k * (3.0 - 2.0 * k)
    if XF['phase'] == 'out':
        _dipLevel(e)
        if k >= 1.0:
            p, XF['pending'] = XF['pending'], None
            if p:
                try: p()
                except Exception as er: print('preset dip', er)
            XF.update(phase='in', t0=T)
    else:
        _dipLevel(1.0 - e)
        if k >= 1.0:
            x.bypass = True; XF['on'] = False
            if XF.get('keep'): op('/project1/fx_text').par.vec6valuey = 0.0; XF['keep'] = False

def cleanSlate():
    """Empty look (no effects, no text, statue centred) saved straight into a new preset, ready to build."""
    C = op('/project1/CONTROLS'); t = _bankTable()
    used = [i for i in range(1, BANK_SLOTS + 1) if t[i, 1].val]
    slot = (max(used) + 1) if used and max(used) < BANK_SLOTS else None            # always the last preset
    if slot is None: slot = next((i for i in range(1, BANK_SLOTS + 1) if not t[i, 1].val), None)
    clearLayers(); S['fades'].clear(); tClear()
    R = op('/project1/remote_cb').module                         # a clean preset is EMPTY: every source off
    C.par.Texton = False; C.par.T2on = False; C.par.T3on = False; C.par.Statue = False; C.par.Scene = 'solid'
    C.par.Drawon = False; C.par.Camsrc = 'off'
    for i in MSLOTS: mediaSlotClear(C, i); R.DRAWS[i] = {'img': None, 'new': True}
    C.par.Spinaxis = 'y'; C.par.Spinrev = False
    if C.par.Clipstate.eval() == 'loop': C.par.Clipstate = 'off'
    C.par.Layerorder = ','.join(LAYER_DEFAULT); C.par.Links = ''
    for n_ in ('Textname', 'T2name', 'T3name', 'Modelname'):
        if hasattr(C.par, n_): C.par[n_] = ''
    for n in FRAMEPARS + OPPARS: C.par[n] = C.par[n].default
    for k in CAMKEYS + ['Pan']:
        try: C.par[k] = C.par[k].default
        except Exception: pass
    CS['blend_until'] = absTime.seconds + 0.6
    if slot is None: return None
    n = sum(1 for i in range(1, BANK_SLOTS + 1) if t[i, 1].val) + 1
    bankSave(slot, 'New look %d' % n)
    S['bank'] = slot
    SWEEP['q'].append(((lambda s=slot: thumbSave(s)), 40))         # re-shoot the picture once the screen settled
    SWEEP['q'].append(((lambda s=slot: _thumbPush(s)), 1))
    return slot

def _thumbPush(slot):
    try:
        R = op('/project1/remote_cb').module
        th = {'t': 'thumb', 's': slot, 'img': thumbB64(slot)}; R._all(th)
    except Exception as e:
        print('thumb push failed', e)

def activeLabel():
    return ' + '.join(r['label'].upper() for r in layers() if r['on'] in ('1', 'True', 'true')) or 'CLEAN'

# ------------------------------------------------------------------ phone camera source (fx_src)
CAMS = {'alive': 0.0}
CAMMODES = {'cam': 1, 'behind': 2, 'screen': 3, 'mask': 4}

LAYER_IDS = dict({'model': 1, 'camera': 2, 'draw': 5, 'text': 21, 'text2': 22, 'text3': 23}, **{'m%d' % i: 10 + i for i in MSLOTS})
LAYER_DEFAULT = ['text', 'text2', 'text3', 'draw'] + ['m%d' % i for i in MSLOTS] + ['camera', 'model']          # front -> back
_LEGACY = {'images': 'm1', 'videos': 'm2'}

def layerOrder(C=None):
    """Front-to-back order of the layers (the phone's LAYERS list). Unknown names are dropped, missing ones added."""
    C = C or op('/project1/CONTROLS')
    seen = []
    for k in str(C.par.Layerorder.eval()).split(','):
        k = _LEGACY.get(k.strip(), k.strip())
        if k in LAYER_IDS and k not in seen: seen.append(k)
    for k in LAYER_DEFAULT:
        if k not in seen: seen.insert(min(len(seen), LAYER_DEFAULT.index(k)), k)
    return seen

def camfeedUpdate(C, dt, T):
    import time as _t
    g = op('/project1/fx_src')
    if g is None: return
    mode = C.par.Camsrc.eval()
    CAMS['stat'] = _ease(CAMS.get('stat', 1.0), 1.0 if (C.par.Statue.eval() or S.get('obj')) else 0.0, swapTc(C, 'model', 0.25), dt)
    flat = C.par.Drawon.eval() and not S.get('drawobj')            # shown as a 3D card instead: no flat overlay
    CAMS['draw'] = _ease(CAMS.get('draw', 0.0), float(C.par.Drawmix.eval()) if flat else 0.0, 0.25, dt)
    R = op('/project1/remote_cb').module; F = R.CAMF
    D = R.DRAWF
    for i, DF in list(R.DRAWS.items()):
        if DF.get('new'): op('/project1/ds%d' % i).cook(force=True)
    if C.par.Clipstate.eval() == 'loop': R.clipFrame()          # recorded clip plays as the camera
    fresh = F['img'] is not None and (_t.perf_counter() - F['t']) < 1.5   # phone stopped -> fade out, never freeze
    CAMS['alive'] = _ease(CAMS.get('alive', 0.0), 1.0 if fresh else 0.0, 0.2 if fresh else 0.7, dt)
    if F['new']: op('/project1/phonecam').cook(force=True)
    ma = []
    for i in MSLOTS:
        k = 'm%d' % i
        CAMS[k] = _ease(CAMS.get(k, 0.0), 1.0 if mediaActive(C, i) else 0.0, swapTc(C, k, 0.2), dt)
        ma.append(CAMS[k])
        mf = op('/project1/mf%d' % i)
        if mf is not None:
            play = mediaActive(C, i)
            if bool(mf.par.play.eval()) != play: mf.par.play = play
            if S['frame'] % 30 == i and mp(C, i, 'kind').eval() != 'draw':     # the file a layer names is always the file it plays
                want = R.mediaFull(mp(C, i, 'file').eval()); have = mf.par.file.eval()
                if os.path.normcase(os.path.normpath(have or '.')) != os.path.normcase(os.path.normpath(want or '.')):
                    mf.par.file = want; SLOTLOG.append((time.strftime('%H:%M:%S'), i, 'resync', str(have)[-40:] + ' -> ' + str(want)[-40:])); del SLOTLOG[:-30]
    if g.bypass: g.bypass = False
    p = g.par; o = op('/project1/AUDIO/OUT')
    p.vec0valuex = T % TWRAP                               # shaders get a wrapped clock
    p.vec1valuex, p.vec1valuey, p.vec1valuez, p.vec1valuew = o['low'].eval(), o['mid'].eval(), o['high'].eval(), o['kick'].eval()
    p.vec2valuex = 1.0
    p.vec3valuex = CAMMODES.get(mode, 0); p.vec3valuey = (1.0 if C.par.Cammirror.eval() else 0.0) + (2.0 if C.par.Camfit.eval() == 'fit' else 0.0); p.vec3valuez = CAMS['alive']
    p.vec3valuew = CAMS['stat']
    p.vec4valuex = CAMS['draw']
    ids = [LAYER_IDS[k] for k in reversed(layerOrder(C))] + [0] * 12      # shader paints back to front
    p.vec5valuex, p.vec5valuey, p.vec5valuez, p.vec5valuew = ids[0:4]
    p.vec6valuex, p.vec6valuey, p.vec6valuez, p.vec6valuew = ids[4:8]
    p.vec7valuex, p.vec7valuey, p.vec7valuez, p.vec7valuew = ids[8:12]
    cam = float(C.par.Cammix.eval()) * CAMS['alive'] if mode in CAMMODES else 0.0
    p.vec8valuex, p.vec8valuey = CAMS['stat'], cam
    p.vec13valuex, p.vec13valuey, p.vec13valuez, p.vec13valuew = ma[0:4]
    p.vec14valuex, p.vec14valuey = ma[4:6]
    mm = [1.0 if i in S.get('objs', []) else 0.0 for i in MSLOTS]
    p.vec25valuex, p.vec25valuey, p.vec25valuez, p.vec25valuew = mm[0:4]
    p.vec26valuex, p.vec26valuey = mm[4:6]
    p.vec27valuex, p.vec27valuey, p.vec27valuez = [1.0 if TINST.get(n) else 0.0 for n in TEXTN]

# ------------------------------------------------------------------ thumbnails (preset pictures + effect tiles)
THUMB_DIR = project.folder + '/td/thumbs'
FXTHUMB_DIR = project.folder + '/web/thumbs/fx'

def thumbBytes(q=74, norm=False):
    """Small JPEG of what is on the output right now (norm = auto-brighten, for effect tiles)."""
    import cv2
    t = op('/project1/thumb_out'); t.cook(force=True)
    a = np.clip(t.numpyArray(delayed=False)[::-1, :, :3], 0.0, 1.0)
    if norm:
        hi = float(np.percentile(a.max(axis=2), 99.5))
        a = np.clip(a / max(0.08, hi) * 0.95, 0.0, 1.0) ** 0.85
    img = (a * 255.0).astype(np.uint8)
    ok, buf = cv2.imencode('.jpg', cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])
    return buf.tobytes() if ok else b''

def _slotMeta(slot):
    try: return (json.loads(_bankTable()[int(slot), 1].val or '{}').get('_meta') or {})
    except Exception: return {}

def thumbPath(slot):
    """Each saved preset names its own picture file, so a picture can never belong to a different preset."""
    th = _slotMeta(slot).get('thumb')
    return '%s/%s' % (THUMB_DIR, os.path.basename(th)) if th else '%s/p%d.jpg' % (THUMB_DIR, int(slot))

def thumbSave(slot):
    os.makedirs(THUMB_DIR, exist_ok=True)
    b = thumbBytes()
    if b:
        p = thumbPath(slot); tmp = p + '.tmp'
        with open(tmp, 'wb') as f: f.write(b)
        os.replace(tmp, p)
    return b

def thumbB64(slot):
    import base64
    if not _bankTable()[int(slot), 1].val: return None             # empty slot: no picture, whatever files exist
    p = thumbPath(slot)
    return base64.b64encode(open(p, 'rb').read()).decode('ascii') if os.path.exists(p) else None

def thumbAll():
    out = {}
    for i in range(1, BANK_SLOTS + 1):
        b = thumbB64(i)
        if b: out[str(i)] = b
    return out

# a capture sweep runs as a little job queue, one step per frame, so the visuals never freeze
SWEEP = {'q': [], 'wait': 0}

def sweepUpdate():
    if not SWEEP['q']: return
    if SWEEP['wait'] > 0: SWEEP['wait'] -= 1; return
    fn, wait = SWEEP['q'].pop(0)
    try: fn()
    except Exception as e: print('thumb sweep step failed', e)
    SWEEP['wait'] = wait

def captureThumbs(presets=True, effects=True):
    """Re-shoot every preset picture and every effect tile (takes ~30 s, restores the screen afterwards)."""
    import os
    C = op('/project1/CONTROLS'); before = snapshot(); bankBefore = S.get('bank', 0)
    keep = {p: C.par[p].eval() for p in ('Texton', 'Camsrc', 'Blackout', 'Scene', 'Model')}
    try: writeJsonSafe(project.folder + '/td/_before_sweep.json', {'look': before, 'keep': keep, 'bank': bankBefore}, bak=False)   # survives a reload
    except Exception: pass
    q = SWEEP['q']
    def prep():
        C.par.Blackout = False; C.par.Camsrc = 'off'
    q.append((prep, 2))
    if presets:
        for i in range(1, BANK_SLOTS + 1):
            if _bankTable()[i, 1].val:
                q.append(((lambda s=i: bankLoad(s, fade=0.0, cam=True, model=True, text=True)), 75))
                q.append(((lambda s=i: thumbSave(s)), 1))
    if effects:
        os.makedirs(FXTHUMB_DIR, exist_ok=True)
        def ref():
            C.par.Texton = False; C.par.Scene = 'solid'; C.par.Model = 'moai'; clearLayers()
            for k, v in {'Orbit': 25, 'Orbitspeed': 0, 'Orbitsway': 0, 'Elevation': 4, 'Elevsway': 0, 'Distance': 3.4,
                         'Distsway': 0, 'Height': 0, 'Fov': 45, 'Roll': 0, 'Rollsway': 0, 'Shake': 0, 'Pan': 0}.items():
                try: C.par[k] = v
                except Exception: pass
        q.append((ref, 40))
        for r in layers():
            k = r['key']
            q.append(((lambda k=k: (clearLayers(), setLayer(k, on=True, amt=1.0))), 10))
            q.append(((lambda k=k: open('%s/%s.jpg' % (FXTHUMB_DIR, k), 'wb').write(thumbBytes(72, norm=True))), 1))
    q.append((lambda: _sweepRestore(before, keep, bankBefore), 1))   # (this line was missing: the screen never came back)

def _sweepRestore(before, keep, bank):
    """After a picture shoot: the exact look from before (source, statue, camera, text), and the on-air slot."""
    C = op('/project1/CONTROLS')
    _bankApply(before, 0.0, True, True, True, cut=True, slot=None)
    for p, v in keep.items():
        try: C.par[p] = v
        except Exception: pass
    S['bank'] = int(bank or 0); S['dirty'] = True
    try:
        R = op('/project1/remote_cb').module
        for i in range(1, BANK_SLOTS + 1):
            if _bankTable()[i, 1].val: R._all({'t': 'thumb', 's': i, 'img': thumbB64(i)})
    except Exception: pass
    storeLog('picture shoot done, screen restored')

def restoreBeforeSweep():
    """Put back the look from before the last picture shoot (if it was interrupted)."""
    d = readJson(project.folder + '/td/_before_sweep.json')
    _sweepRestore(d['look'], d.get('keep', {}), d.get('bank', 0))

def bankRestoreCam(d):
    C = op('/project1/CONTROLS')
    for k, v in d.get('cam', {}).items():
        try: C.par[k] = v
        except Exception: pass
    if d.get('model'): C.par.Model = d['model']

PRELOAD = {'todo': None}

def preloadStep():
    # load every statue (geometry + texture) once at startup, one file every ~1/3 s,
    # so a model switch mid-set never freezes the frame (and never cracks the headphone audio)
    if PRELOAD['todo'] is None:
        ops_ = []
        for p in ('/project1/moai_geo', '/project1/moai_particles'):
            g = op(p)
            if g: ops_ += [o for o in g.children if o.OPType == 'fileinSOP']
        ops_ += [o for o in op('/project1').children if o.OPType == 'moviefileinTOP' and o.name.startswith('tex_')]
        an = op('/project1/anims')
        if an: ops_ += [o for o in an.findChildren() if o.OPType in ('importselectPOP', 'importselectTOP', 'alembicSOP', 'moviefileinTOP', 'fileinSOP')]
        PRELOAD['todo'] = ops_
    if S['frame'] < 30 or S['frame'] % 20: return
    while PRELOAD['todo']:
        o = PRELOAD['todo'].pop(0)
        try:
            if o.totalCooks == 0:
                o.cook(force=True); return
        except Exception:
            pass

# ------------------------------------------------------------------ frame loop (built to run for hours)
# Every stage is isolated: if one part ever throws, only that part skips a frame - the rest keeps drawing.
# (Before, one error stopped everything after it in that frame, every frame: visuals froze or vanished.)
ERRS = {}
TWRAP = 1200.0                     # shader clock wraps every 20 min: float precision stays perfect for any set length

def _safe(name, fn, *a):
    try: return fn(*a)
    except Exception as e:
        n = ERRS.get(name, 0) + 1; ERRS[name] = n
        if n in (1, 10, 100) or n % 3600 == 0: storeLog('FRAME ERROR in %s (x%d): %r' % (name, n, e))
        return None

def _models(C, dt, T, react, grid):
    ms = modelUpdate(C, T)
    msh = C.par.Modelshown.eval()
    if msh != S.get('msw'): S['msw'] = msh; staticSwitch(msh)
    _safe('objects', objUpdate, C)
    NR = noReact(C); mreact = 0.0 if 'model' in NR else react
    ag = _safe('animation', animUpdate, C, dt, mreact)
    o_ry, o_rx, o_rz, o_ty = motionOffsets(C, T, mreact)
    ax = C.par.Spinaxis.eval() if hasattr(C.par, 'Spinaxis') else 'y'   # spin axis: y = turn, x = tumble, z = roll
    for g in [op('/project1/moai_geo'), op('/project1/moai_particles'), op('/project1/draw_geo'), ag] + [op('/project1/mg%d' % i) for i in S.get('objs', [])] + [op('/project1/tg%d' % n) for n in S.get('tobjs', [])]:
        if g is None: continue
        react = 0.0 if _gkey(g.name) in NR else mreact if _gkey(g.name) == 'model' else C.par.Reactivity.eval()
        own = ownMotion(C, g.name)                                # a 3D picture / video / drawing / text with its own motion
        if own:
            m_, spd, ax_, amt, rev = own
            if m_ == 'spin': OANG[g.name] = (OANG.get(g.name, 0.0) + (-1.0 if rev else 1.0) * (spd + C.par.Spinboost.eval() * S['low'] * react) * dt) % 360.0
            spin = OANG.get(g.name, 0.0) if m_ == 'spin' else 0.0
            if m_ == 'still': OANG[g.name] = 0.0
            b_ry, b_rx, b_rz, b_ty = motionOffsets(C, T, react, m_, amt)
            applyModelXform(C, g, ms, (spin if ax_ == 'y' else 0.0) + b_ry)
            g.par.rx = b_rx + (spin if ax_ == 'x' else 0.0); g.par.rz = b_rz + (spin if ax_ == 'z' else 0.0)
            if b_ty: g.par.ty = g.par.ty.eval() + b_ty
        else:
            spin = 0.0 if (grid and g.name == 'moai_geo') else S['angle']
            base = 0.0 if (grid and g.name == 'moai_geo') else C.par.Angle.eval()
            applyModelXform(C, g, ms, base + (spin if ax == 'y' else 0.0) + o_ry)
            g.par.rx = C.par.Tilt.eval() + o_rx + (spin if ax == 'x' else 0.0); g.par.rz = o_rz + (spin if ax == 'z' else 0.0)
            if o_ty: g.par.ty = g.par.ty.eval() + o_ty
        x, y, z, sc, tu, ti = obj3d(C, g.name)                     # each 3D layer's own place in the scene (VIEW tab)
        g.par.tx = x; g.par.tz = z
        if y: g.par.ty = g.par.ty.eval() + y
        if sc != 1.0: g.par.scale = g.par.scale.eval() * sc
        if tu: g.par.ry = g.par.ry.eval() + tu
        if ti: g.par.rx = g.par.rx.eval() + ti
    if grid:
        op('/project1/moai_geo/grid_inst').cook(force=True)

OANG = {}                                                       # own spin angle per 3D layer
def ownMotion(C, name):
    """(motion, spin speed, axis, amount, reverse) for a 3D layer that moves on its own; None = it follows the 3D models."""
    if name.startswith('mg') and name[2:].isdigit(): q = 'M%s' % name[2:]
    elif name.startswith('tg') and name[2:].isdigit(): n = int(name[2:]); q = 'Text' if n == 1 else 'T%d' % n
    else: return None
    if not hasattr(C.par, q + 'motion'): return None
    m = C.par[q + 'motion'].eval()
    if m == 'models': return None
    return (m, float(C.par[q + 'mspeed'].eval()), C.par[q + 'maxis'].eval(), float(C.par[q + 'mamt'].eval()), bool(C.par[q + 'mrev'].eval()))

def obj3d(C, name):
    """Left/right, up/down, depth, size, turn, tilt of one 3D layer: the models, a 3D picture / video / drawing, 3D text."""
    f = lambda p: float(C.par[p].eval()) if hasattr(C.par, p) else 0.0
    if name.startswith('mg') and name[2:].isdigit():
        q = 'M%sobj' % name[2:]; return f(q + 'x'), f(q + 'y'), f(q + 'z'), f(q + 'scale') or 1.0, f(q + 'turn'), f(q + 'tilt')
    if name.startswith('tg') and name[2:].isdigit():
        n = int(name[2:]); return 0.0, 0.0, f(tpn(n, 'Textdepth')), f(tpn(n, 'Textoscale')) or 1.0, f(tpn(n, 'Textoturn')), f(tpn(n, 'Textotilt'))
    if name == 'draw_geo': return 0.0, 0.0, 0.0, 1.0, 0.0, 0.0
    return f('Modelx'), f('Modely'), f('Modelz'), f('Modelscale') or 1.0, f('Modelturn'), f('Modeltilt')   # models + animations

def _label(C):
    show = bool(C.par.Showlabel.eval())
    txt = ('%s      CAM %s' % (activeLabel(), camLabel())) if show else ''
    if txt != S['label']:
        lab = op('/project1/fx_label')
        try: lab.par.text = txt
        except Exception: pass
        lab.bypass = not show                                  # no full-screen pass when the label is off
        S['label'] = txt

def _colsave(T):
    if S.get('lcolsave') and T - STORE['colt'] > 0.5:           # colour drags: at most 2 writes a second
        S.pop('lcolsave', None); STORE['colt'] = T; colSave()


# ---------------------------------------------------------------- projector output (keystone) ---------------
# Venue setup, not part of presets: kept in td/projector.json and restored at start.
PROJ_FILE = 'td/projector.json'
PROJ_KEYS = ['Kstlx', 'Kstly', 'Kstrx', 'Kstry', 'Ksblx', 'Ksbly', 'Ksbrx', 'Ksbry', 'Kszoom', 'Ksx', 'Ksy', 'Ksrot',
             'Ksfeather', 'Ksbright', 'Kslift', 'Ksgamma', 'Ksflipx', 'Ksflipy', 'Kstest', 'Projmon']
PROJ = {'sig': None, 'loaded': False, 'dirty': 0.0, 'win': None}

def _projLoad(C):
    PROJ['loaded'] = True
    try:
        d = json.load(open(PROJ_FILE))
        for k in PROJ_KEYS:
            if k in d and hasattr(C.par, k): C.par[k] = d[k]
    except Exception: pass

def _projSave(C):
    try:
        d = {k: C.par[k].eval() for k in PROJ_KEYS if hasattr(C.par, k)}
        tmp = PROJ_FILE + '.tmp'
        with open(tmp, 'w') as f: json.dump(d, f, indent=1)
        os.replace(tmp, PROJ_FILE)
    except Exception as e: ERRS['projsave'] = str(e)

def _homography(src, dst):
    """3x3 matrix taking the four src points onto the four dst points."""
    import numpy as np
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(A, float), np.array(b, float))
    return np.append(h, 1.0).reshape(3, 3)

def projQuad(C):
    """Where the picture's corners land on the projector (0-1, y up): corner drags, then zoom, rotate, move."""
    f = lambda k: float(C.par[k].eval())
    q = [(0.0 + f('Ksblx'), 0.0 + f('Ksbly')), (1.0 + f('Ksbrx'), 0.0 + f('Ksbry')),
         (1.0 + f('Kstrx'), 1.0 + f('Kstry')), (0.0 + f('Kstlx'), 1.0 + f('Kstly'))]
    z, a = max(0.05, f('Kszoom')), math.radians(f('Ksrot'))
    kw = op('/project1/kst_warp'); asp = (kw.width / max(1.0, kw.height)) if kw is not None else 16.0 / 9.0
    ca, sa, out = math.cos(a), math.sin(a), []
    for x, y in q:
        x, y = (x - 0.5) * asp * z, (y - 0.5) * z
        x, y = x * ca - y * sa, x * sa + y * ca
        out.append((x / asp + 0.5 + f('Ksx') * 0.5, y + 0.5 + f('Ksy') * 0.5))
    return out

def projUpdate(C):
    if not hasattr(C.par, 'Kszoom'): return
    if not PROJ['loaded']: _projLoad(C)
    sig = tuple(C.par[k].eval() for k in PROJ_KEYS)
    kw = op('/project1/kst_warp')
    if sig != PROJ['sig'] and kw is not None:
        import numpy as np
        first = PROJ['sig'] is None
        PROJ['sig'] = sig
        try:
            Hi = np.linalg.inv(_homography([(0, 0), (1, 0), (1, 1), (0, 1)], projQuad(C)))   # projector pixel -> picture
            p = kw.par
            for r in range(3):
                p['vec%dvaluex' % r], p['vec%dvaluey' % r], p['vec%dvaluez' % r] = [float(v) for v in Hi[r]]
        except Exception as e: ERRS['keystone'] = str(e)
        p = kw.par
        p.vec3valuex = 1.0 if C.par.Ksflipx.eval() else 0.0; p.vec3valuey = 1.0 if C.par.Ksflipy.eval() else 0.0
        p.vec3valuez = float(C.par.Ksfeather.eval()); p.vec3valuew = {'off': 0, 'over': 1, 'grid': 2}.get(C.par.Kstest.eval(), 0)
        p.vec4valuex, p.vec4valuey, p.vec4valuez = float(C.par.Ksbright.eval()), float(C.par.Kslift.eval()), float(C.par.Ksgamma.eval())
        if not first: PROJ['dirty'] = absTime.seconds
    if PROJ['dirty'] and absTime.seconds - PROJ['dirty'] > 1.0:       # saved a second after the last change
        PROJ['dirty'] = 0.0; _projSave(C)
    projWindow(C)

def projMonitors():
    try: return [(m.width, m.height) for m in monitors]
    except Exception: return []

def projWindow(C):
    """Open / close the full-screen projector window on the chosen screen."""
    w = op('/project1/proj_window')
    if w is None: return
    want = bool(C.par.Projwin.eval())
    mons = projMonitors()
    mi = min(max(0, int(C.par.Projmon.eval()) - 1), max(0, len(mons) - 1))
    key = (want, mi)
    if key == PROJ['win'] and (w.isOpen == want or absTime.seconds - PROJ.get('wt', 0) < 3.0): return
    PROJ['win'] = key; PROJ['wt'] = absTime.seconds
    if want:
        mw, mh = mons[mi] if mons else (1920, 1080)
        kw = op('/project1/kst_warp'); c = op('/PROJECTOR') or op('/project1/PROJECTOR')
        rw = min(1280, mw); rh = int(round(rw * mh / max(1, mw)))      # the window scales it up (licence caps textures at 1280)
        if kw is not None and (kw.par.resolutionw.eval(), kw.par.resolutionh.eval()) != (rw, rh):
            kw.par.resolutionw, kw.par.resolutionh = rw, rh; PROJ['sig'] = None     # re-fit the warp to the screen's shape
        if c is not None: c.par.w, c.par.h = mw, mh
        w.par.monitor = mi; w.par.size = 'fill'; w.par.borders = False
        if w.isOpen: w.par.winclose.pulse()
        try:
            if ui.performMode: ui.performMode = False      # one output only: the perform window would show it a second time
        except Exception: pass
        w.par.winopen.pulse()
    elif w.isOpen:
        w.par.winclose.pulse()

def onFrameStart(frame):
    C = op('/project1/CONTROLS')
    dt = 1.0 / max(1.0, float(project.cookRate))
    T = absTime.seconds
    S['frame'] += 1
    if S['frame'] % 60 == 0: _safe('lost', op('/project1/remote_cb').module.lostCheck)
    if S['frame'] % 8 == 0: _safe('clonesbb', clonesBB)
    if PRELOAD['todo'] is None or PRELOAD['todo']: _safe('preload', preloadStep)
    _safe('audio', audioUpdate, C, dt, T)
    react = C.par.Reactivity.eval()
    if C.par.Autospin.eval() and C.par.Motion.eval() == 'spin':
        sd = -1.0 if C.par.Spinrev.eval() else 1.0                  # spin direction (statues, animations, pictures, drawings)
        S['angle'] = (S['angle'] + sd * (C.par.Speed.eval() + C.par.Spinboost.eval() * S['low'] * (0.0 if 'model' in noReact(C) else react)) * dt) % 360.0
    sc = C.par.Scene.eval()
    if sc != S['scene']:
        _safe('scene', applyScene, sc); S['scene'] = sc; S['obj'] = None; S['anim'] = '?'
    _safe('models', _models, C, dt, T, react, sc == 'grid')
    _safe('projector', projUpdate, C)
    _safe('render', renderGeo, C)
    _safe('layers', applyLayers, T)
    _safe('uniforms', pushUniforms, T)
    _safe('layerfx', fxTargets, C)
    _safe('layerfxu', tUniforms, T)
    _safe('colours', _colsave, T)
    _safe('camfeed', camfeedUpdate, C, dt, T)
    _safe('sweep', sweepUpdate)
    _safe('dip', xfadeUpdate, T)
    _safe('camera', camUpdate, C, dt)
    _safe('label', _label, C)
    _safe('text', textAll, C, T)
    _safe('master', masterUpdate, C, dt)
    _safe('safety', safetyUpdate, C)
    _safe('flash', flashWatch, C, T)
    _safe('autopilot', autopilotUpdate, C, T)
    if S['frame'] % 300 == 0: _safe('watchdog', watchdog)       # every ~5 s
    if S['frame'] % 4 == 0:
        try: op('/project1/remote_cb').module.broadcastMeters()
        except Exception: pass

# ------------------------------------------------------------------ autopilot: a new preset every N seconds
# Random, but never the one on screen or any of the last 5 shown. Uses the set list if it has 2+ presets,
# otherwise every saved preset. Tapping a preset yourself restarts the timer.
AP = {'t': 0.0, 'recent': [], 'last': 0}

def autopilotUpdate(C, T):
    import random
    b = int(S.get('bank', 0) or 0)
    if b and b != AP['last']:                                    # remember what was shown (autopilot or by hand)
        AP['last'] = b; AP['recent'] = ([x for x in AP['recent'] if x != b] + [b])[-5:]; AP['t'] = T
    if not C.par.Autopilot.eval(): AP['t'] = T; return
    if T - AP['t'] < max(5.0, float(C.par.Autotime.eval())): return
    AP['t'] = T
    fd = max(0.0, min(10.0, float(op('/project1/CONTROLS').par.Autofade.eval())))
    if hasattr(C.par, 'Automode') and C.par.Automode.eval() == 'setlist' and qState()['v']:     # play the set list in order
        if len(qState()['v']) == 1 and qState()['v'][0] == b: return          # one preset only: nothing to change to
        qGo(qState()['pos'] + 1, fade=fd)
        try: op('/project1/remote_cb').module._all(qMsg())
        except Exception: pass
        return
    q = [x for x in qState()['v'] if _bankTable()[x, 1].val]
    mode = C.par.Automode.eval() if hasattr(C.par, 'Automode') else 'random'
    allp = [i for i in range(1, BANK_SLOTS + 1) if _bankTable()[i, 1].val]
    pool = sorted(set(q)) if (mode == 'setrand' and len(set(q)) >= 2) else allp   # set list - random / every preset
    if len(pool) < 2: return
    avoid = set(AP['recent'][-min(5, len(pool) - 1):]) | {b}
    cand = [x for x in pool if x not in avoid] or [x for x in pool if x != b]
    slot = random.choice(cand)
    if bankLoad(slot, fade=max(0.0, min(10.0, float(op('/project1/CONTROLS').par.Autofade.eval()))), cam=True, model=True, text=True):   # the phone's transition time
        try:
            if qSync(slot): op('/project1/remote_cb').module._all(qMsg())
        except Exception: pass

def watchdog():
    """Long sets: bring dropped phone relays back, and log the rig's health every 10 minutes."""
    now = absTime.seconds
    for n in ('remote_mqtt', 'remote_mqtt2', 'remote_mqtt3'):
        m = op('/project1/' + n)
        if m is None: continue
        if m.isConnected: WD[n] = now; continue
        if now - WD.get(n, now) > 15:                            # down 15 s: restart that connection
            storeLog('relay %s was down - reconnecting' % n)
            try: m.par.reconnect.pulse()
            except Exception: m.par.active = False; run("op('/project1/%s').par.active = True" % n, delayFrames=30)
            WD[n] = now
        WD.setdefault(n, now)
    if now - WD.get('_health', -1e9) > 600:
        WD['_health'] = now
        try:
            p = op('/project1/perf')
            storeLog('health: %.0f min up, %.0f fps, %.1f ms, gpu %.0f MB, relays %s, errors %s'
                     % (now / 60, p['fps'].eval(), p['msec'].eval(), p['gpu_mem_used'].eval(),
                        ''.join('1' if op('/project1/' + n) and op('/project1/' + n).isConnected else '0' for n in ('remote_mqtt', 'remote_mqtt2', 'remote_mqtt3')),
                        dict(ERRS) or 'none'))
        except Exception: pass

WD = {}

def masterUpdate(C, dt):
    tgt = 0.0 if C.par.Blackout.eval() else float(C.par.Master.eval())
    ft = max(0.01, float(C.par.Fadetime.eval()))
    S['master'] += (tgt - S['master']) * min(1.0, dt * 3.0 / ft)
    if abs(S['master'] - tgt) < 0.002: S['master'] = tgt
    lv = op('/project1/master_level')
    idle = abs(S['master'] - 1.0) < 1e-4
    if lv.bypass != idle: lv.bypass = idle                      # skip the pass at full brightness
    if not idle and lv.par.brightness1.eval() != S['master']: lv.par.brightness1 = S['master']

def flashWatch(C, T):
    """Logs any near-white frame with the full state, so the cause can be found."""
    try:
        p = op('/project1/flash_probe')
        b = (p['r'].eval() + p['g'].eval() + p['b'].eval()) / 3.0
    except Exception:
        return
    prev = S.get('bright', b); S['bright'] = b
    if b > 0.75 and prev <= 0.75:
        t = op('/project1/flash_log')
        if t.numRows > 400: t.deleteRows(range(1, t.numRows - 300))     # long sets: keep the newest 300
        if t.numRows == 0:
            t.appendRow(['time', 'bright', 'style', 'model', 'kick', 'low', 'camdist', 'fov', 'campreset'])
        cam = op('/project1/cam')
        d = math.sqrt(cam.par.tx.eval() ** 2 + cam.par.ty.eval() ** 2 + cam.par.tz.eval() ** 2)
        t.appendRow([round(T, 2), round(b, 3), activeLabel() + ' / ' + C.par.Scene.eval(), C.par.Model.eval(),
                     round(S['kick'], 2), round(S['low'], 2), round(d, 2), round(cam.par.fov.eval(), 1),
                     int(C.par.Presetslot.eval())])

# ------------------------------------------------------------------ camera
CAMKEYS = ['Orbit', 'Orbitspeed', 'Orbitsway', 'Elevation', 'Elevsway', 'Distance', 'Distsway',
           'Height', 'Fov', 'Roll', 'Rollsway', 'Swayspeed', 'Shake', 'Audiocam']
PRESET_FILE = project.folder + '/td/cam_presets.json'          # camera shots F1-F8 (disk wins at start too)
CS = {'orb': 0.0, 't': 0.0, 'cur': None}

def _pv(pnl, name, default=0.0):
    try: return float(getattr(pnl, name).val)
    except Exception: return default

def _clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)

def _halfsize(C):
    ren = op('/project1/render1')
    aspect = (ren.width / float(ren.height)) if ren is not None and ren.height else 16 / 9.0
    halfW = C.par.Distance.eval() * math.tan(math.radians(max(5.0, C.par.Fov.eval())) / 2.0)
    return halfW, halfW / aspect

# remote / mouse helpers (shared by STAGE mouse and the phone)
def navOrbit(dx, dy):
    C = op('/project1/CONTROLS')
    C.par.Orbit = C.par.Orbit.eval() + dx
    C.par.Elevation = _clamp(C.par.Elevation.eval() + dy, -85, 85)

def navFling(vy, vp):
    M = CS.setdefault('m', {'u': 0.0, 'v': 0.0, 'btn': '', 'vy': 0.0, 'vp': 0.0, 'w': 0.0, 'grab': True})
    M['vy'], M['vp'] = vy, vp

def navPan(du, dv):
    C = op('/project1/CONTROLS'); hw, hh = _halfsize(C)
    C.par.Pan = _clamp(C.par.Pan.eval() - du * 2.0 * hw, -5, 5)
    C.par.Height = _clamp(C.par.Height.eval() - dv * 2.0 * hh, -3, 3)

def navZoom(factor):
    C = op('/project1/CONTROLS')
    C.par.Distance = _clamp(C.par.Distance.eval() * factor, 0.5, 30)

def camUpdate(C, dt):
    T = absTime.seconds
    dt = max(dt, 1e-3)
    M = CS.setdefault('m', {'u': 0.0, 'v': 0.0, 'btn': '', 'vy': 0.0, 'vp': 0.0, 'w': 0.0, 'grab': True})
    halfW, halfH = _halfsize(C)
    dist0 = C.par.Distance.eval()
    st = op('/project1/STAGE')
    btn = ''
    if st is not None:
        pnl = st.panel
        u, v = _pv(pnl, 'u'), _pv(pnl, 'v')
        l, r, m = _pv(pnl, 'lselect'), _pv(pnl, 'rselect'), _pv(pnl, 'mselect')
        w = _pv(pnl, 'wheel')
        sens = C.par.Mousesens.eval()
        btn = 'l' if l > 0 else ('r' if r > 0 else ('m' if m > 0 else ''))
        if btn and not M['btn']:
            M['vy'] = M['vp'] = 0.0
        if btn and btn == M['btn']:
            du, dv = u - M['u'], v - M['v']
            if btn == 'l':
                dy, dp = -du * 320.0 * sens, -dv * 160.0 * sens
                navOrbit(dy, dp)
                M['vy'] = M['vy'] * 0.4 + (dy / dt) * 0.6
                M['vp'] = M['vp'] * 0.4 + (dp / dt) * 0.6
            elif btn == 'm':
                navPan(du, dv)
            elif btn == 'r':
                C.par.Distance = _clamp(dist0 * math.exp(-(du + dv) * 3.0 * sens), 0.5, 30)
        if w != M['w'] and w != 0:
            k = 0.12 * sens * (1.0 if w > M['w'] else -1.0)
            if C.par.Zoomtocursor.eval() and 0 <= u <= 1 and 0 <= v <= 1:
                C.par.Pan = _clamp(C.par.Pan.eval() + (u - 0.5) * 2.0 * halfW * k, -5, 5)
                C.par.Height = _clamp(C.par.Height.eval() + (v - 0.5) * 2.0 * halfH * k, -3, 3)
            C.par.Distance = _clamp(dist0 * (1.0 - k), 0.5, 30)
        M['u'], M['v'], M['btn'], M['w'] = u, v, btn, w
    if not btn and (abs(M['vy']) > 0.3 or abs(M['vp']) > 0.3):          # flick inertia (mouse or phone)
        navOrbit(M['vy'] * dt, M['vp'] * dt)
        decay = C.par.Inertia.eval() ** (dt * 60.0)
        M['vy'] *= decay; M['vp'] *= decay

    tgt = {k: getattr(C.par, k).eval() for k in CAMKEYS}
    if CS['cur'] is None:
        CS['cur'] = dict(tgt)
    cur = CS['cur']
    if T < CS.get('blend_until', 0.0):
        a = 1.0 - math.exp(-dt * 4.0 / max(0.01, C.par.Transition.eval()))
    else:
        a = 1.0 - math.exp(-dt / max(0.005, C.par.Response.eval()))
    for k in CAMKEYS:
        cur[k] += (tgt[k] - cur[k]) * a
    pan = CS.get('pan', 0.0); pan += (C.par.Pan.eval() - pan) * a; CS['pan'] = pan

    react = C.par.Reactivity.eval()
    kick, low, ac = S['kick'] * react, S['low'] * react, cur['Audiocam']
    if A['lastkick'] != CS.get('lastkick'):                 # new beat -> smooth sideways nudge
        CS['lastkick'] = A['lastkick']
        soft = 1.0 - 0.6 * float(C.par.Beatfeel.eval())
        CS['joltT'] = CS.get('joltT', 0.0) + C.par.Kickjolt.eval() * ac * soft * (1 if (int(T * 7) % 2) else -1)
    CS['joltT'] = _ease(CS.get('joltT', 0.0), 0.0, 0.35, dt)
    CS['jolt'] = _ease(CS.get('jolt', 0.0), CS['joltT'], 0.08, dt)
    if abs(CS['joltT']) < 1e-6: CS['joltT'] = 0.0               # flush tiny values: denormals broke the camera roll
    if abs(CS['jolt']) < 1e-6: CS['jolt'] = 0.0
    CS['t'] += dt * cur['Swayspeed'] * (1.0 + low * ac)
    CS['orb'] = (CS['orb'] + cur['Orbitspeed'] * dt * (1.0 + low * ac * 0.5)) % 360.0
    t = CS['t']
    yaw = cur['Orbit'] + CS['orb'] + cur['Orbitsway'] * math.sin(t * 0.7) + CS['jolt']
    pitch = cur['Elevation'] + cur['Elevsway'] * math.sin(t * 0.53 + 1.0)
    base = max(0.5, cur['Distance'] + cur['Distsway'] * math.sin(t * 0.41 + 2.0))
    punch = min(C.par.Punch.eval() * kick * ac, base * 0.35)            # never push more than 35% closer
    dist = max(0.5, base - punch)
    roll = cur['Roll'] + cur['Rollsway'] * math.sin(t * 0.37 + 0.5) + CS['jolt'] * 0.3
    sh = cur['Shake'] + low * ac * 0.25
    yaw += sh * 2.0 * (math.sin(T * 7.3) + 0.5 * math.sin(T * 11.7))
    pitch += sh * 1.5 * (math.sin(T * 8.1 + 3.0) + 0.5 * math.sin(T * 13.3))
    roll += sh * math.sin(T * 9.7 + 1.0)
    pitch = _clamp(pitch, -89, 89)
    yr, pr = math.radians(yaw), math.radians(pitch)
    tx, ty, tz = pan * math.cos(yr), cur['Height'], -pan * math.sin(yr)
    cam = op('/project1/cam')
    cam.par.tx = tx + dist * math.cos(pr) * math.sin(yr)
    cam.par.ty = ty + dist * math.sin(pr)
    cam.par.tz = tz + dist * math.cos(pr) * math.cos(yr)
    if not all(math.isfinite(v) for v in (pitch, yaw, roll, dist)): return   # never write a broken camera
    cam.par.rx, cam.par.ry, cam.par.rz = -pitch, yaw, roll
    try: cam.par.fov = _clamp(cur['Fov'] + kick * ac * 8.0, 5.0, 130.0)
    except Exception: pass

# ------------------------------------------------------------------ models + presets
def setModel(i):
    C = op('/project1/CONTROLS'); names = C.par.Model.menuNames
    if 0 <= i < len(names):
        C.par.Model = names[i]

def staticSwitch(name):
    """Point the statue geometry + texture switches at a model BY NAME (m_<name> / tex_<name>),
    so the order of the model list can never pair a statue with the wrong picture."""
    for path, prefix, par in (('/project1/moai_geo/model_switch', 'm_', 'input'), ('/project1/moai_particles/model_switch', 'm_', 'input'),
                              ('/project1/model_tex', 'tex_', 'index')):
        sw = op(path)
        if sw is None: continue
        names = [i.name for i in sw.inputs]
        if prefix + str(name) not in names: continue                 # an animation: the statue isn't shown anyway
        i = names.index(prefix + str(name)); p = sw.par[par]
        if p.mode != ParMode.CONSTANT: p.mode = ParMode.CONSTANT
        if int(p.eval()) != i: p.val = i

def stepModel(d):
    C = op('/project1/CONTROLS')
    setModel((C.par.Model.menuIndex + d) % len(C.par.Model.menuNames))

def camLabel():
    C = op('/project1/CONTROLS')
    return '%d %s      %s' % (int(C.par.Presetslot.eval()), C.par.Presetname.eval(),
                             C.par.Model.menuLabels[C.par.Model.menuIndex].upper())

def loadPreset(n):
    t, C = op('/project1/CAM_PRESETS'), op('/project1/CONTROLS')
    if t is None or n < 1 or n >= t.numRows:
        return
    for k in CAMKEYS:
        cell = t[n, k]
        if cell is not None and cell.val != '':
            setattr(C.par, k, float(cell.val))
    C.par.Presetslot = n
    C.par.Presetname = t[n, 'name'].val
    CS['blend_until'] = absTime.seconds + C.par.Transition.eval()
    C.par.Pan = 0
    C.par.Height = float(t[n, 'Height'].val or 0)

def savePreset(n, name=None):
    t, C = op('/project1/CAM_PRESETS'), op('/project1/CONTROLS')
    while t.numRows <= n:
        t.appendRow(['Preset %d' % t.numRows])
    nm = name or (C.par.Presetname.eval() if int(C.par.Presetslot.eval()) == n else '')
    t[n, 'name'] = nm or t[n, 'name'].val or ('Preset %d' % n)
    for k in CAMKEYS:
        t[n, k] = round(getattr(C.par, k).eval(), 3)
    C.par.Presetslot = n
    C.par.Presetname = t[n, 'name'].val
    exportPresets()

def exportPresets():
    t = op('/project1/CAM_PRESETS')
    rows = [{t[0, c].val: t[r, c].val for c in range(t.numCols)} for r in range(1, t.numRows)]
    try: writeJsonSafe(PRESET_FILE, rows, indent=2)
    except Exception as e: _storeAlert('Camera shots NOT saved: %s' % e)


def camBoot():
    """Camera shots (F1-F8) come from disk at start, same rule as the presets."""
    t = op('/project1/CAM_PRESETS')
    if t is None: return
    rows = readJsonSafe(PRESET_FILE, None)
    if rows is None:                                           # first run: the shots only lived in the .toe - put them on disk
        if t.numRows > 1:
            try: writeJsonSafe(PRESET_FILE, [{t[0, c].val: t[r, c].val for c in range(t.numCols)} for r in range(1, t.numRows)], indent=2)
            except Exception as e: storeLog('camera shots rescue failed: %s' % e)
        return
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows): return
    head = [t[0, c].val for c in range(t.numCols)] if t.numRows else []
    for r in rows:
        for k in r:
            if k not in head: head.append(k)
    want = [head] + [[str(r.get(k, '')) for k in head] for r in rows]
    have = [[t[r, c].val for c in range(t.numCols)] for r in range(t.numRows)]
    if want != have:
        t.clear()
        for row in want: t.appendRow(row)
        storeLog('camera shots loaded from disk (%d)' % len(rows))

# ------------------------------------------------------------------ start-up: presets come from disk
try: storeBoot()
except Exception as _e: storeLog('STORE BOOT FAILED: %r' % (_e,))
try: camBoot()
except Exception as _e: storeLog('camera shots boot failed: %r' % (_e,))
