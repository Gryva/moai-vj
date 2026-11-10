# Render effect preview tiles: Antinous, same angle, whole statue in frame, one effect at a time.
# Saves web/thumbs/fx/<key>.jpg (256x256). Restores every setting afterwards. Run: exec(open(path).read(), {'op': op, ...})
import json, copy
P = op('/project1'); C = P.op('CONTROLS'); E = P.op('fx_engine').module
OUTDIR = project.folder + '/web/thumbs/fx/'
KEYS = globals().get('KEYS') or [r['key'] for r in E.layers()]
WAIT = globals().get('WAIT', 24)

ST = {}
def save_state():
    ST['pars'] = {p.name: p.eval() for p in C.customPars if not p.isPulse and not p.readOnly and p.mode == ParMode.CONSTANT}
    ST['stack'] = P.op('FX_STACK').text
    ST['fxt'] = copy.deepcopy(E.FXT); ST['lcol'] = copy.deepcopy(E.LCOL)

def restore_state():
    for k, v in ST['pars'].items():
        try: C.par[k] = v
        except Exception: pass
    P.op('FX_STACK').text = ST['stack']; E.S['dirty'] = True
    for k in E.FXT: E.FXT[k] = ST['fxt'].get(k, {})
    E.LCOL.clear(); E.LCOL.update(ST['lcol'])
    for n in ('thumb_crop', 'thumb_fit'):
        o = P.op(n)
        if o is not None: o.destroy()

SP = {}
def apply_params():
    E.S['angle'] = 0.0                                    # the running spin angle: same pose every time
    for k, v in SP.items():
        if hasattr(C.par, k):
            try: C.par[k] = v
            except Exception: pass

def clean_now():
    return C.par.Model.eval() == 'antinous' and C.par.Statue.eval() and not any(C.par['M%don' % i].eval() for i in range(1, 7)) \
        and not C.par.Texton.eval() and C.par.Camsrc.eval() == 'off' and not C.par.Blackout.eval()

def setup():
    S = {'Statue': True, 'Model': 'antinous', 'Motion': 'still', 'Autospin': False, 'Angle': 35.0, 'Tilt': 0.0,
         'Orbit': 0.0, 'Orbitspeed': 0.0, 'Elevation': 5.0, 'Distance': 5.6, 'Height': 0.0, 'Pan': 0.0, 'Roll': 0.0,
         'Fov': 45.0, 'Shake': 0.0, 'Blackout': False, 'Autopilot': False, 'Showlabel': False, 'Camsrc': 'off',
         'Drawon': False, 'Texton': False, 'T2on': False, 'T3on': False, 'Scene': 'single',
         'Modelx': 0.0, 'Modely': 0.0, 'Modelz': 0.0, 'Modelscale': 1.0, 'Modelturn': 0.0, 'Modeltilt': 0.0, 'Modeltrans': 0.0, 'Master': 1.0}
    S.update(globals().get('EXTRA', {}))
    for i in range(1, 7): S['M%don' % i] = False
    SP.update(S); apply_params()
    for k in E.FXT: E.FXT[k] = {}
    E.LCOL.clear()
    E.clearLayers()
    o = P.op('OUT')
    cr = P.create(cropTOP, 'thumb_crop'); cr.inputConnectors[0].connect(o)
    w, h = o.width, o.height; side = min(w, h)
    cr.par.cropleft = (w - side) / 2.0 / w; cr.par.cropright = 1 - (w - side) / 2.0 / w
    fit = P.create(fitTOP, 'thumb_fit'); fit.inputConnectors[0].connect(cr)
    fit.par.outputresolution = 'custom'; fit.par.resolutionw = 256; fit.par.resolutionh = 256

def shot(name):
    P.op('thumb_fit').save(OUTDIR + name + '.jpg')

def step(i, retry=0):
    try:
        if i > 0 and not clean_now():                      # something else changed the picture: set it up again, redo this one
            apply_params(); E.clearLayers()
            if retry < 5:
                k = KEYS[i - 1]
                if k != '_none':
                    p1 = [float(r['p1'] or 0) for r in E.layers() if r['key'] == k]
                    E.setLayer(k, on=True, amt=1.0, p1=p1[0] if p1 else None)
                run("args[0](args[1], args[2])", step, i, retry + 1, delayFrames=90); return
        if i > 0: shot(KEYS[i - 1])
        if i >= len(KEYS):
            restore_state(); E.ERRS['thumbs'] = 'done %d' % len(KEYS); return
        E.clearLayers(); E.S['angle'] = 0.0
        k = KEYS[i]
        if k != '_none':
            p1 = [float(r['p1'] or 0) for r in E.layers() if r['key'] == k]
            E.setLayer(k, on=True, amt=1.0, p1=p1[0] if p1 else None)
        run("args[0](args[1], args[2])", step, i + 1, 0, delayFrames=WAIT)
    except Exception as e:
        E.ERRS['thumbs'] = 'failed: %s' % e
        restore_state()

save_state(); setup()
run("args[0](args[1], args[2])", step, 0, 0, delayFrames=90)
