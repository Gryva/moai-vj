# MOAI VJ keyboard  (fx_keys Keyboard In DAT callbacks, synced to td/keys_cb.py)
# Works only while the TouchDesigner window has focus. Failsafe keys when the phone is down:
#   PageDown / PageUp  next / previous preset in the set list  (most presenter clickers send these)
#   Shift + 1..9, 0    load preset slot 1..10 (the numbers on the phone tiles)
#   B                  blackout on / off  (the "blank screen" button on most clickers)
KEYFADE = 1.0

def _mods(args, kwargs):
    ctrl = kwargs.get('ctrl', args[3] if len(args) > 3 else False)
    shift = kwargs.get('shift', args[6] if len(args) > 6 else False)
    return bool(ctrl), bool(shift)

def _go(mm, fn, *a):
    try:
        fn(*a)
        R = op('/project1/remote_cb').module
        R._all(mm.qMsg())
    except Exception as e:
        print('key action failed', e)

def onKey(dat, key, character, *args, **kwargs):
    state = kwargs.get('state', args[9] if len(args) > 9 else True)
    if not state:
        return
    C = op('/project1/CONTROLS')
    ch = (character or '') if isinstance(character, str) else ''
    k = (key or '').lower() if isinstance(key, str) else ''
    mm = op('/project1/fx_engine').module
    ctrl, shift = _mods(args, kwargs)
    dg = k if k.isdigit() else (ch if ch.isdigit() else '')

    # ---- failsafe show control
    if k in ('pagedown', 'next'):
        q = mm.qState()
        if q['v']: _go(mm, mm.qGo, q['pos'] + 1, KEYFADE)
        return
    if k in ('pageup', 'prior'):
        q = mm.qState()
        if q['v']: _go(mm, mm.qGo, (q['pos'] if q['pos'] >= 0 else 0) - 1, KEYFADE)
        return
    if shift and dg and not ctrl:
        slot = 10 if dg == '0' else int(dg)
        if mm.bankLoad(slot, fade=KEYFADE, cam=True, model=True, text=True):
            if mm.qSync(slot): _go(mm, lambda: None)
        return
    if ch.lower() == 'b' and not ctrl:
        C.par.Blackout = not C.par.Blackout.eval(); return

    # ---- models-nav
    if ctrl and dg:
        mm.setModel(int(dg) - 1); return
    lc = ch.lower()
    if lc == 'm': mm.stepModel(1); return
    if lc == 'n': mm.stepModel(-1); return
    if lc == 'f': C.par.Pan = 0; C.par.Height = 0; return
    if ch in ('+', '='): C.par.Distance = max(0.3, C.par.Distance.eval() * 0.85); return
    if ch in ('-', '_'): C.par.Distance = min(30, C.par.Distance.eval() / 0.85); return
    if ch == '[': C.par.Roll = C.par.Roll.eval() - 10; return
    if ch == ']': C.par.Roll = C.par.Roll.eval() + 10; return
    if len(ch) == 1 and ch.isdigit():
        mm.toggleLayerIndex(9 if ch == '0' else int(ch) - 1)
    elif ch.lower() == 'c' or k == 'c':
        mm.clearLayers()
    elif k in ('right', 'arrowright'):
        C.par.Speed = C.par.Speed.eval() + 10
    elif k in ('left', 'arrowleft'):
        C.par.Speed = C.par.Speed.eval() - 10
    elif k in ('up', 'arrowup'):
        C.par.Tilt = min(60, C.par.Tilt.eval() + 5)
    elif k in ('down', 'arrowdown'):
        C.par.Tilt = max(-60, C.par.Tilt.eval() - 5)
    elif ch == '.':
        C.par.Angle = C.par.Angle.eval() + 15
    elif ch == ',':
        C.par.Angle = C.par.Angle.eval() - 15
    elif k.startswith('f') and k[1:].isdigit() and 1 <= int(k[1:]) <= 8:
        if shift: mm.savePreset(int(k[1:]))
        else: mm.loadPreset(int(k[1:]))
    elif ch.lower() == 'a': C.par.Orbit = C.par.Orbit.eval() - 10
    elif ch.lower() == 'd': C.par.Orbit = C.par.Orbit.eval() + 10
    elif ch.lower() == 'w': C.par.Elevation = min(80, C.par.Elevation.eval() + 5)
    elif ch.lower() == 's': C.par.Elevation = max(-80, C.par.Elevation.eval() - 5)
    elif ch.lower() == 'q': C.par.Distance = max(1, C.par.Distance.eval() - 0.5)
    elif ch.lower() == 'e': C.par.Distance = min(15, C.par.Distance.eval() + 0.5)
    elif ch.lower() == 'z': C.par.Fov = max(10, C.par.Fov.eval() - 5)
    elif ch.lower() == 'x': C.par.Fov = min(120, C.par.Fov.eval() + 5)
    elif ch.lower() == 'r': mm.loadPreset(1)
    elif ch == ' ' or k == 'space':
        C.par.Autospin = not C.par.Autospin.eval()
