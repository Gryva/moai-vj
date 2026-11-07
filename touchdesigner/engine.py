# MOAI VJ ENGINE  - runs every frame (fx_engine Execute DAT, synced to this file)
import numpy as np, math, json

NAMES = ['CLEAN']   # legacy (single-effect mode is replaced by the layer stack)
S = {'angle': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0, 'level': 0.0, 'kick': 0.0,
     'scene': None, 'label': None, 'master': 1.0, 'frame': 0, 'layers': None,
     'dirty': True, 'rows': [], 'live': [], 'fades': {}, 'bank': 0, 'bankfade': 0.0}
PRESETS_FILE = r'D:/Projects/Visuals/td/presets.json'
BANK_SLOTS = 128
LOOKS_FILE = r'D:/Projects/Visuals/td/looks.json'


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
    y = BUF * float(C.par.Gain.eval())
    rms = float(np.sqrt(np.mean(y[-int(SR / 60):] ** 2))) + 1e-12
    X = np.abs(np.fft.rfft(y * HANN)) / (N / 4.0)
    db = {k: 20.0 * math.log10(float(np.sqrt(np.mean(X[m] ** 2))) + 1e-12) for k, m in MASKS.items()}
    db['level'] = 20.0 * math.log10(rms)
    A['db'] = db
    gate, rng = float(C.par.Gate.eval()), max(6.0, float(C.par.Range.eval()))
    gated = db['level'] < gate
    for k, d in db.items():
        pk = max(d, A['peak'][k] - 4.0 * dt, gate + rng * 0.5)     # adaptive ceiling, falls 4 dB/s
        A['peak'][k] = pk
        A['raw'][k] = 0.0 if gated else min(1.0, max(0.0, (d - (pk - rng)) / rng))
    return A['raw']

def _ease(cur, tgt, tc, dt):
    return cur + (tgt - cur) * (1.0 - math.exp(-dt / max(1e-3, tc)))

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

def motionOffsets(C, T, react=1.0):
    """Extra statue movement on top of the pose: (yaw, nod, roll, lift)."""
    m = C.par.Motion.eval(); a = float(C.par.Motionamt.eval()); k = S['kick'] * react; lo = S['low'] * react
    if m == 'bob':   return (0.0, -k * 22.0 * a - math.sin(T * 2.2) * 3.0 * a, math.sin(T * 1.1) * 4.0 * a, k * 0.12 * a)
    if m == 'sway':  return (math.sin(T * 0.9) * 28.0 * a, 0.0, math.sin(T * 0.9 + 1.0) * 10.0 * a * (1.0 + lo), math.sin(T * 1.8) * 0.05 * a)
    if m == 'float': return (math.sin(T * 0.21) * 40.0 * a, math.sin(T * 0.29) * 6.0 * a, math.sin(T * 0.37) * 8.0 * a, math.sin(T * 0.5) * 0.3 * a)
    return (0.0, 0.0, 0.0, 0.0)

def objUpdate(C):
    """Image / video as a 3D object: a card in the 3D scene instead of the statue."""
    obj = C.par.Mediamode.eval() == 'object' and bool(C.par.Media.eval())
    ig = op('/project1/img_geo')
    if ig is None: return
    if obj != S.get('obj'):
        S['obj'] = obj
        if obj:
            op('/project1/moai_geo').render = False; op('/project1/moai_particles').render = False
            ig.render = True; op('/project1/render1').par.geometry = ig.path
        else:
            ig.render = False; applyScene(C.par.Scene.eval())
        S['anim'] = '?'                                          # re-check the animated model next
    if obj:                                                     # keep the card the picture's shape
        mf = op('/project1/mediafile'); w, h = mf.width, mf.height
        asp = (w / h) if h else 1.0; card = ig.op('card')
        sx, sy = (2.0 * asp, 2.0) if asp <= 1.6 else (3.2, 3.2 / asp)
        if abs(card.par.sizex.eval() - sx) > 1e-3 or abs(card.par.sizey.eval() - sy) > 1e-3:
            card.par.sizex = sx; card.par.sizey = sy

# ------------------------------------------------------------------ animated 3D models (FBX / Alembic in /project1/anims)
ANIM_FILE = project.folder + '/3D objects/_anim/anims.json'
ANIMS = {'list': None}

def animList():
    if ANIMS['list'] is None:
        try: ANIMS['list'] = json.load(open(ANIM_FILE))
        except Exception: ANIMS['list'] = []
    return ANIMS['list']

def animInfo(model):
    if not model or not str(model).startswith('anim_'): return None
    for a in animList():
        if a['name'] == model[5:]: return a
    return None

def animComp(a): return op('/project1/anims/a_' + a['name']) if a else None

def animUpdate(C, dt, react):
    """Show the animated model (instead of the statue) and drive its playback speed from the music."""
    a = None if S.get('obj') else animInfo(C.par.Modelshown.eval())
    g = animComp(a)
    if g is None: a = None
    key = a['name'] if a else None
    if key != S.get('anim'):
        for c in op('/project1/anims').children:
            if c.isCOMP:
                c.render = False
                if c.OPType == 'fbxCOMP': c.par.play = False
        if g is not None:
            g.render = True
            if g.OPType == 'fbxCOMP': g.par.play = True
            op('/project1/moai_geo').render = False; op('/project1/moai_particles').render = False
            op('/project1/moai_geo').par.instancing = False
            op('/project1/render1').par.geometry = g.path
        elif not S.get('obj'):
            applyScene(C.par.Scene.eval())
        S['anim'] = key
    if g is None: return None
    sp = float(C.par.Animspeed.eval()) * (1.0 + float(C.par.Animbeat.eval()) * S['kick'] * react)
    if g.OPType == 'fbxCOMP':
        if abs(g.par.speed.eval() - sp) > 1e-3: g.par.speed = sp
    else:
        dur = max(0.05, float(a.get('dur', 1.0)))
        S['animt'] = (S.get('animt', 0.0) + dt * sp) % dur
        if a.get('kind') == 'seq':                                # baked frames (heavy Alembic, pre-decoded)
            i = int(S['animt'] * float(a.get('fps', 12))) % int(a.get('frames', 1))
            sw = g.op('seq')
            if int(sw.par.input.eval()) != i: sw.par.input = i
        else:
            g.op('abc').par.time = S['animt']
    return g

def mediaFit():
    """Frame the picture / video so it fills the screen as if it were played flat.
    Nothing moves until you touch the camera, then it behaves like an object in the 3D scene."""
    C = op('/project1/CONTROLS')
    mf = op('/project1/mediafile'); w, h = mf.width, mf.height
    asp = (w / h) if h else 16 / 9.0
    sx, sy = (2.0 * asp, 2.0) if asp <= 1.6 else (3.2, 3.2 / asp)
    ren = op('/project1/render1'); ra = ren.width / float(ren.height) if ren.height else 16 / 9.0
    t = math.tan(math.radians(max(5.0, C.par.Fov.eval())) / 2.0)
    dist = max((sx / 2.0) / t, (sy / 2.0) * ra / t)                # whole picture visible, centred
    for k, v in (('Distance', round(dist, 4)), ('Orbit', 0.0), ('Elevation', 0.0), ('Height', 0.0), ('Pan', 0.0), ('Roll', 0.0),
                 ('Orbitspeed', 0.0), ('Orbitsway', 0.0), ('Elevsway', 0.0), ('Distsway', 0.0), ('Rollsway', 0.0), ('Shake', 0.0),
                 ('Audiocam', 0.0), ('Angle', 0.0), ('Tilt', 0.0), ('Motion', 'still'), ('Objx', 0.0), ('Objy', 0.0), ('Objscale', 1.0)):
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
            'Textsize', 'Textglow', 'Textspeed', 'Textreact', 'Textamount', 'Textcm', 'Textca', 'Textcb', 'Textcang']
TCOLORS = {'white': (1, 1, 1), 'hot': (1, .3, .18), 'cyan': (.24, .94, 1), 'violet': (.69, .42, 1),
           'lime': (.78, 1, .24), 'gold': (1, .78, .25)}
TMODES = ['overlay', 'mask', 'cutout', 'invert', 'outline', 'glitch', 'refract']
TANIM = {'static': 0, 'pulse': 1, 'wave': 2, 'scroll': 3, 'tile': 4, 'type': 0, 'beat': 1}
TLAYOUT = {  # align x, align y, pos x, pos y, font px, autosize, wrap
    'center': ('center', 'center', 0, 0, 150, 'fitiffat', True),
    'fill':   ('center', 'center', 0, 0, 400, 'alwaysfit', True),
    'stack':  ('center', 'center', 0, 0, 120, 'fitiffat', True),
    'lower':  ('left', 'bottom', 70, 70, 64, 'fitiffat', True),
    'corner': ('left', 'top', 50, -50, 40, 'fitiffat', True)}
TX = {'sig': None, 't0': 0.0, 'words': [' '], 'wi': 0, 'lk': None, 'shown': None}

def textUpdate(C, T):
    g = op('/project1/fx_text')
    on = bool(C.par.Texton.eval()) and float(C.par.Textamount.eval()) > 0.001
    if g.bypass == on: g.bypass = not on
    if not on: return False
    tt = op('/project1/text_src')
    full = C.par.Textstr.eval() or ' '
    lay, anim, size = C.par.Textlayout.eval(), C.par.Textanim.eval(), float(C.par.Textsize.eval())
    small = lay in ('lower', 'corner')
    sig = (full, lay, anim, C.par.Textfont.eval(), round(size, 3) if small else 0)
    if sig != TX['sig']:
        TX['sig'] = sig; TX['t0'] = T; TX['words'] = full.split() or [' ']; TX['wi'] = 0; TX['shown'] = None
        ax, ay, px, py, fpx, fit, wrap = TLAYOUT.get(lay, TLAYOUT['center'])
        if anim == 'scroll': wrap = False
        p = tt.par
        p.font = C.par.Textfont.eval(); p.alignx = ax; p.aligny = ay
        p.positionx = px; p.positiony = py
        p.fontsizex = fpx * (size if small else 1.0); p.fontautosize = fit; p.wordwrap = wrap
    if anim == 'type':
        n = int((T - TX['t0']) * 14.0 * max(0.1, C.par.Textspeed.eval())) % (len(full) + 25)
        txt = full[:min(n, len(full))] or ' '
    elif anim == 'beat':
        if A['lastkick'] != TX['lk']:
            TX['lk'] = A['lastkick']; TX['wi'] = (TX['wi'] + 1) % len(TX['words'])
        txt = TX['words'][TX['wi']]
    elif lay == 'stack':
        txt = '\n'.join(full.split()) or ' '
    else:
        txt = full
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
    M = TXM['on']
    def L(key):
        v = float(C.par[key].eval())
        return TXM['frm'][key] + (v - TXM['frm'][key]) * e if M else v
    mode = TXM['mode'] if (M and e < 0.5) else C.par.Textmode.eval()
    pp.vec0valuex = T
    pp.vec1valuex, pp.vec1valuey, pp.vec1valuez, pp.vec1valuew = o['low'].eval(), o['mid'].eval(), o['high'].eval(), o['kick'].eval()
    pp.vec2valuex = L('Textamount')
    pp.vec3valuex = TMODES.index(mode) if mode in TMODES else 0
    pp.vec3valuey = TANIM.get(anim, 0); pp.vec3valuez = L('Textspeed'); pp.vec3valuew = L('Textreact')
    r, gg, b = TCOLORS.get(C.par.Textcolor.eval(), (1, 1, 1))
    if M:
        r0, g0, b0 = TXM['col']; r, gg, b = r0 + (r - r0) * e, g0 + (gg - g0) * e, b0 + (b - b0) * e
    pp.vec4valuex, pp.vec4valuey, pp.vec4valuez, pp.vec4valuew = r, gg, b, L('Textglow')
    sz = L('Textsize')
    pp.vec5valuex = 1.0 if small else sz; pp.vec5valuey = sz; pp.vec5valuez = 0.5
    pp.vec6valuex = e; pp.vec6valuez = 1.0 if M else 0.0
    tm = int(C.par.Textcm.eval()); tv = _hex(C.par.Textca.eval()) + _hex(C.par.Textcb.eval(), (1.0, 0.24, 0.66)) + (float(C.par.Textcang.eval()),)
    if M and TXM.get('tc'):                                      # colours glide with the word morph
        m0, v0 = TXM['tc']
        if m0 == tm: tv = tuple(a_ + (b_ - a_) * e for a_, b_ in zip(v0, tv))
        elif e < 0.5: tm, tv = m0, v0
    pp.vec7valuex, pp.vec7valuey, pp.vec7valuez, pp.vec7valuew = tv[0], tv[1], tv[2], float(tm)
    pp.vec8valuex, pp.vec8valuey, pp.vec8valuez, pp.vec8valuew = tv[3], tv[4], tv[5], math.radians(tv[6])
    return True

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
        p.vec0valuex = T
        p.vec1valuex, p.vec1valuey, p.vec1valuez, p.vec1valuew = au
        if k in COLFX: _colPush(k, p, T)

# ------------------------------------------------------------------ effect colours (own colour / solid / linear / radial gradient)
COLFX = ['hologram', 'neon', 'lines', 'halftone', 'ascii', 'thermal', 'palette', 'glow', 'glitch', 'matte', 'strobe', 'kaleido', 'tunnel']
LCOL_FILE = project.folder + '/td/lcols.json'
try: LCOL = {k: v for k, v in json.load(open(LCOL_FILE)).items()}   # key -> {'m', 'a', 'b', 'ang'}
except Exception: LCOL = {}
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
    try: json.dump(LCOL, open(LCOL_FILE, 'w'))
    except Exception as e: print('colour save failed', e)

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

GRIDPARS = ['Gridcount', 'Griddepth', 'Gridspace', 'Gridwave', 'Gridstagger']

def lookData():
    C = op('/project1/CONTROLS')
    return {'layers': {r['key']: [int(r['on'] in ('1', 'True', 'true')), float(r['amt']), float(r['p1'])] for r in layers()},
            'scene': C.par.Scene.eval(), 'grid': {p: C.par[p].eval() for p in GRIDPARS},
            'text': {p: C.par[p].eval() for p in TEXTPARS}, 'statue': bool(C.par.Statue.eval()),
            'lcols': {k: dict(v) for k, v in LCOL.items() if v.get('m', 0) > 0}}

def applyLook(d, text=True):
    C = op('/project1/CONTROLS'); S['dirty'] = True
    saved = d.get('layers', {})
    for r in layers():                                           # a preset is the WHOLE stack:
        if r['key'] not in saved: setLayer(r['key'], on=False)   # layers it doesn't mention go off
    for k, v in saved.items():
        setLayer(k, on=bool(v[0]), amt=v[1], p1=v[2])
    if text and d.get('text') and 'Textcm' not in d['text']: C.par.Textcm = 0
    for p, v in list(d.get('grid', {}).items()) + (list(d.get('text', {}).items()) if text else []):
        try: C.par[p] = v
        except Exception: pass
    if d.get('scene'): C.par.Scene = d['scene']
    C.par.Statue = bool(d.get('statue', True))                  # older presets: statue on
    colsApply(d.get('lcols'), S.get('colfade', 0.0))

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
    try:
        json.dump([{'name': t[r, 'name'].val, 'data': json.loads(t[r, 'data'].val)} for r in range(1, t.numRows)],
                  open(LOOKS_FILE, 'w'), indent=1)
    except Exception as e: print('looks export failed', e)

# ------------------------------------------------------------------ preset bank (64 slots, 4 banks x 16)
def _bankTable():
    t = op('/project1/PRESETS')
    if t.numRows < BANK_SLOTS + 1:
        while t.numRows < BANK_SLOTS + 1: t.appendRow(['', ''])
    return t

OBJKEYS = ['Angle', 'Tilt', 'Speed', 'Spinboost', 'Autospin', 'Motion', 'Motionamt', 'Animspeed', 'Animbeat']

def snapshot():
    C = op('/project1/CONTROLS')
    d = lookData()
    d['model'] = C.par.Model.eval()
    d['cam'] = {k: round(float(C.par[k].eval()), 4) for k in CAMKEYS + ['Pan']}
    d['obj'] = {k: (bool(C.par[k].eval()) if k == 'Autospin' else C.par[k].eval() if k == 'Motion' else round(float(C.par[k].eval()), 4)) for k in OBJKEYS}
    d['src'] = srcData()
    d['obj']['angle'] = round(S['angle'], 3)
    return d

# ------------------------------------------------------------------ source (what the effects work on) in presets
def srcData():
    C = op('/project1/CONTROLS'); R = op('/project1/remote_cb').module
    return {'camsrc': C.par.Camsrc.eval(), 'cammix': round(float(C.par.Cammix.eval()), 3), 'camfit': C.par.Camfit.eval(),
            'media': C.par.Media.eval(), 'mediamode': C.par.Mediamode.eval(),
            'clip': R.CLIP['id'] if C.par.Clipstate.eval() == 'loop' else None,
            'draw': bool(C.par.Drawon.eval()), 'drawmix': round(float(C.par.Drawmix.eval()), 3),
            'key': {k: (bool(C.par[k].eval()) if k == 'Keyon' else C.par[k].eval() if k == 'Keycolor' else round(float(C.par[k].eval()), 4)) for k in KEYPARS}}

KEYPARS = ['Keyon', 'Keycolor', 'Keytol', 'Keysoft', 'Keyspill', 'Keyshrink', 'Objx', 'Objy', 'Objscale']

def drawPath(slot): return '%s/td/drawings/p%d.png' % (project.folder, int(slot))

def applySrc(d, slot=None):
    """Presets saved before sources existed just show the statue."""
    import os
    C = op('/project1/CONTROLS'); R = op('/project1/remote_cb').module
    s = d.get('src') or {'camsrc': 'off', 'media': '', 'clip': None, 'draw': False}
    C.par.Mediamode = s.get('mediamode', 'flat')
    if s.get('media'):
        if C.par.Media.eval() != s['media']: R.mediaPlay(s['media'])
    elif C.par.Media.eval(): R.mediaStop()
    if s.get('clip') and R.clipPlay(s['clip']): pass
    elif C.par.Clipstate.eval() == 'loop': R.clipLive()
    C.par.Camsrc = s.get('camsrc', 'off')
    if 'cammix' in s: C.par.Cammix = s['cammix']
    if 'camfit' in s: C.par.Camfit = s['camfit']
    for k in KEYPARS:                                            # green screen + where the picture stands
        if k in s.get('key', {}):
            try: C.par[k] = s['key'][k]
            except Exception: pass
    if 'key' not in s: C.par.Keyon = False; C.par.Objx = 0.0; C.par.Objy = 0.0; C.par.Objscale = 1.0
    C.par.Drawon = bool(s.get('draw'))
    if 'drawmix' in s: C.par.Drawmix = s['drawmix']
    if s.get('draw') and slot and os.path.exists(drawPath(slot)):
        import cv2
        im = cv2.imread(drawPath(slot))
        if im is not None:
            R.DRAWF['img'] = np.ascontiguousarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGBA)[::-1]); R.DRAWF['new'] = True

FXP_FILE = project.folder + '/td/fxpresets.json'
FXP = {'list': None}

def fxList():
    if FXP['list'] is None:
        try: FXP['list'] = json.load(open(FXP_FILE))
        except Exception: FXP['list'] = []
    return FXP['list']

def _fxSave():
    try: json.dump(fxList(), open(FXP_FILE, 'w'))
    except Exception as e: print('fx presets save failed', e)

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
        out.append({'name': nm, 'on': [k for k, v in d.get('layers', {}).items() if v[0]], 'scene': d.get('scene', 'solid'), 'model': d.get('model', '')})
    return out

def bankSave(slot, name=None):
    t = _bankTable()
    t[slot, 0] = name or t[slot, 0].val or ('Preset %d' % slot)
    t[slot, 1] = json.dumps(snapshot())
    bankExport()
    try:
        R = op('/project1/remote_cb').module; img = R.DRAWF.get('img')
        if op('/project1/CONTROLS').par.Drawon.eval() and img is not None:
            import cv2, os
            os.makedirs(os.path.dirname(drawPath(slot)), exist_ok=True)
            cv2.imwrite(drawPath(slot), cv2.cvtColor(np.ascontiguousarray(img[::-1]), cv2.COLOR_RGBA2BGR))
    except Exception as er: print('drawing save failed', er)
    try: thumbSave(slot)
    except Exception as e: print('thumb failed', e)

def bankClear(slot):
    t = _bankTable(); t[slot, 0] = ''; t[slot, 1] = ''; bankExport()
    import os
    try: os.remove(thumbPath(slot))
    except Exception: pass

def bankRename(slot, name):
    t = _bankTable()
    if t[slot, 1].val: t[slot, 0] = name; bankExport()

def bankExport():
    t = _bankTable()
    try: json.dump([[t[i, 0].val, t[i, 1].val] for i in range(1, BANK_SLOTS + 1)], open(PRESETS_FILE, 'w'))
    except Exception as e: print('preset export failed', e)

def bankImport():
    t = _bankTable()
    try:
        rows = json.load(open(PRESETS_FILE))
        for i, (nm, data) in enumerate(rows[:BANK_SLOTS], start=1): t[i, 0] = nm; t[i, 1] = data
        return True
    except Exception:
        return False

def bankLoad(slot, fade=0.0, cam=True, model=True, text=False):
    t = _bankTable()
    if not t[slot, 1].val: return
    d = json.loads(t[slot, 1].val); C = op('/project1/CONTROLS')
    newModel = bool(model and d.get('model') and d['model'] != C.par.Model.eval())
    newScene = bool(d.get('scene') and d['scene'] != C.par.Scene.eval())
    s_ = d.get('src') or {}
    newSrc = (s_.get('media', '') != C.par.Media.eval()) or (s_.get('camsrc', 'off') != C.par.Camsrc.eval()) or bool(s_.get('draw')) != bool(C.par.Drawon.eval())
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
    for k, v in d.get('obj', {}).items():                        # statue pose: angle, tilt, spin
        try: C.par[k] = v
        except Exception: pass
    if 'angle' in d.get('obj', {}): S['angle'] = float(d['obj']['angle'])
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
            d = json.load(open(QUEUE_FILE)); Q['v'] = [int(x) for x in d.get('v', [])][:64]; Q['pos'] = int(d.get('pos', -1))
        except Exception:
            Q['v'] = []; Q['pos'] = -1
    if not (-1 <= Q['pos'] < len(Q['v'])): Q['pos'] = -1
    return Q

def qMsg():
    q = qState(); return {'t': 'queue', 'v': list(q['v']), 'pos': q['pos']}

def _qSave():
    try: json.dump({'v': Q['v'], 'pos': Q['pos']}, open(QUEUE_FILE, 'w'))
    except Exception as e: print('set list save failed', e)

def qSet(v):
    q = qState(); t = _bankTable()
    cur = q['v'][q['pos']] if 0 <= q['pos'] < len(q['v']) else None
    out = []
    for x in list(v or [])[:64]:
        try: x = int(x)
        except Exception: continue
        if 1 <= x <= BANK_SLOTS and t[x, 1].val: out.append(x)
    q['v'] = out; q['pos'] = out.index(cur) if cur in out else -1
    _qSave(); qPrewarm()

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
    med = (d.get('src') or {}).get('media')
    if med:
        R = op('/project1/remote_cb').module
        for rel, full, kind in R._mediaFiles():
            if rel == med:
                mn = op('/project1/media_next')
                if mn is None:
                    mn = op('/project1').create(moviefileinTOP, 'media_next'); mn.par.play = False
                    mf = op('/project1/mediafile'); mn.nodeX = mf.nodeX; mn.nodeY = mf.nodeY - 150
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
    slot = next((i for i in range(1, BANK_SLOTS + 1) if not t[i, 1].val), None)
    clearLayers(); S['fades'].clear()
    C.par.Texton = False; C.par.Statue = True; C.par.Scene = 'solid'
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

def camfeedUpdate(C, dt, T):
    import time as _t
    g = op('/project1/fx_src')
    if g is None: return
    mode = C.par.Camsrc.eval()
    CAMS['stat'] = _ease(CAMS.get('stat', 1.0), 1.0 if C.par.Statue.eval() else 0.0, 0.25, dt)   # statue on/off fades
    CAMS['draw'] = _ease(CAMS.get('draw', 0.0), float(C.par.Drawmix.eval()) if C.par.Drawon.eval() else 0.0, 0.25, dt)
    D = op('/project1/remote_cb').module.DRAWF
    if D['new']: op('/project1/phonedraw').cook(force=True)
    g.par.vec4valuex = CAMS['draw']
    if mode not in CAMMODES and CAMS['stat'] > 0.999 and CAMS['draw'] < 0.002:
        if not g.bypass: g.bypass = True
        CAMS['alive'] = 0.0
        return
    R = op('/project1/remote_cb').module; F = R.CAMF
    media = bool(C.par.Media.eval()) and C.par.Mediamode.eval() == 'flat'
    sel = op('/project1/camsel')
    if sel is not None and int(sel.par.index.eval()) != (1 if media else 0): sel.par.index = 1 if media else 0
    if C.par.Clipstate.eval() == 'loop': R.clipFrame()          # recorded clip plays as the camera
    fresh = media or (F['img'] is not None and (_t.perf_counter() - F['t']) < 1.5)   # phone stopped -> fade out, never freeze
    CAMS['alive'] = _ease(CAMS['alive'], 1.0 if fresh else 0.0, 0.2 if fresh else 0.7, dt)
    if F['new']: op('/project1/phonecam').cook(force=True)
    if g.bypass: g.bypass = False
    p = g.par; o = op('/project1/AUDIO/OUT')
    p.vec0valuex = T
    p.vec1valuex, p.vec1valuey, p.vec1valuez, p.vec1valuew = o['low'].eval(), o['mid'].eval(), o['high'].eval(), o['kick'].eval()
    p.vec2valuex = float(C.par.Cammix.eval()) * CAMS['alive'] if mode in CAMMODES else 1.0   # nothing running -> statue shows
    p.vec3valuex = CAMMODES.get(mode, 0); p.vec3valuey = (1.0 if C.par.Cammirror.eval() else 0.0) + (2.0 if C.par.Camfit.eval() == 'fit' else 0.0); p.vec3valuez = CAMS['alive']
    p.vec3valuew = CAMS['stat']

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

def thumbPath(slot): return '%s/p%d.jpg' % (THUMB_DIR, int(slot))

def thumbSave(slot):
    import os
    os.makedirs(THUMB_DIR, exist_ok=True)
    b = thumbBytes()
    if b: open(thumbPath(slot), 'wb').write(b)
    return b

def thumbB64(slot):
    import os, base64
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
    try: json.dump({'look': before, 'keep': keep, 'bank': bankBefore}, open(project.folder + '/td/_before_sweep.json', 'w'))   # survives a reload
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
    def restore():
        applyLook(before); bankRestoreCam(before)
        S['bank'] = bankBefore; S['dirty'] = True                 # the sweep walked through every slot: put the on-air slot back
        for p, v in keep.items():
            try: C.par[p] = v
            except Exception: pass
        print('thumb sweep done')

def restoreBeforeSweep():
    """Put back the look from before the last picture shoot (if it was interrupted)."""
    d = json.load(open(project.folder + '/td/_before_sweep.json'))
    C = op('/project1/CONTROLS'); applyLook(d['look']); bankRestoreCam(d['look'])
    for p, v in d['keep'].items():
        try: C.par[p] = v
        except Exception: pass
    q.append((restore, 1))
    q.append(((lambda: (S.__setitem__('bank', int(d.get('bank', 0))), S.__setitem__('dirty', True))), 1))

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

def onFrameStart(frame):
    C = op('/project1/CONTROLS')
    dt = 1.0 / max(1.0, float(project.cookRate))
    T = absTime.seconds
    S['frame'] += 1
    if PRELOAD['todo'] is None or PRELOAD['todo']: preloadStep()
    audioUpdate(C, dt, T)
    react = C.par.Reactivity.eval()
    if C.par.Autospin.eval() and C.par.Motion.eval() == 'spin':
        S['angle'] = (S['angle'] + (C.par.Speed.eval() + C.par.Spinboost.eval() * S['low'] * react) * dt) % 360.0
    sc = C.par.Scene.eval()
    if sc != S['scene']:
        applyScene(sc); S['scene'] = sc; S['obj'] = None; S['anim'] = '?'
    grid = (sc == 'grid')
    ms = modelUpdate(C, T)
    objUpdate(C)
    ag = animUpdate(C, dt, react)
    o_ry, o_rx, o_rz, o_ty = motionOffsets(C, T, react)
    for g in (op('/project1/moai_geo'), op('/project1/moai_particles'), op('/project1/img_geo'), ag):
        if g is None: continue
        base = 0.0 if (grid and g.name == 'moai_geo') else S['angle'] + C.par.Angle.eval()
        applyModelXform(C, g, ms, base + o_ry)
        g.par.rx = C.par.Tilt.eval() + o_rx; g.par.rz = o_rz
        if o_ty: g.par.ty = g.par.ty.eval() + o_ty
        if g.name == 'img_geo':                                  # the picture / video can be moved around the scene
            g.par.tx = float(C.par.Objx.eval()); g.par.ty = g.par.ty.eval() + float(C.par.Objy.eval())
            g.par.scale = g.par.scale.eval() * float(C.par.Objscale.eval())
    if grid:
        op('/project1/moai_geo/grid_inst').cook(force=True)
    applyLayers(T)
    pushUniforms(T)
    if S.pop('lcolsave', False) and S['frame'] % 1 == 0: colSave()
    camfeedUpdate(C, dt, T)
    sweepUpdate()
    xfadeUpdate(T)
    camUpdate(C, dt)
    show = bool(C.par.Showlabel.eval())
    txt = ('%s      CAM %s' % (activeLabel(), camLabel())) if show else ''
    if txt != S['label']:
        lab = op('/project1/fx_label')
        try: lab.par.text = txt
        except Exception: pass
        lab.bypass = not show                                  # no full-screen pass when the label is off
        S['label'] = txt
    textUpdate(C, T)
    masterUpdate(C, dt)
    safetyUpdate(C)
    flashWatch(C, T)
    if S['frame'] % 4 == 0:
        try: op('/project1/remote_cb').module.broadcastMeters()
        except Exception: pass

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
PRESET_FILE = r'D:/Projects/Visuals/3D objects/hoa-hakananaia/cam_presets.json'
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
    try:
        with open(PRESET_FILE, 'w') as f:
            json.dump(rows, f, indent=2)
    except Exception as e:
        print('could not write presets file:', e)
