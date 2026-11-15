# GRID SCENE - Script CHOP callbacks: one sample per model copy (tx ty tz ry s)
import math

def onSetupParameters(scriptOp): return
def onPulse(par): return

def onCook(scriptOp):
    C = op('/project1/CONTROLS'); S = op('/project1/fx_engine').module.S
    n, d = int(C.par.Gridcount.eval()), int(C.par.Griddepth.eval())
    sp, wave, stag = C.par.Gridspace.eval(), C.par.Gridwave.eval(), C.par.Gridstagger.eval()
    react = C.par.Reactivity.eval(); low, kick = S['low'] * react, S['kick'] * react
    T = absTime.seconds; base = S['angle'] + S.get('angoffv', 0.0) + C.par.Angle.eval()
    G = max(0.0, min(1.0, float(S.get('gridgrow', 1.0))))          # 0 = all copies sit in the middle one (looks like a single statue), 1 = the full grid
    Gs = G * G * (3.0 - 2.0 * G)
    ic = (d // 2) * n * n + (n // 2) * n + (n // 2)                 # the copy that stays: the middle one
    tx, ty, tz, ry, sc = [], [], [], [], []
    idx = 0
    for k in range(d):
        for j in range(n):
            for i in range(n):
                x = (i - (n - 1) / 2.0) * sp
                y = (j - (n - 1) / 2.0) * sp * 1.15
                r = math.hypot(x, y)
                z = -(k - (d - 1) / 2.0) * sp * 1.3 + math.sin(r * 1.2 - T * 3.0) * wave * (0.35 + low)
                tx.append(x * G); ty.append(y * G); tz.append(z * G)
                ry.append(base + idx * stag * G)
                sc.append((1.0 + kick * 0.18 * math.cos(r * 0.8)) * (1.0 if idx == ic else Gs))
                idx += 1
    scriptOp.clear()
    scriptOp.numSamples = len(tx)
    for name, vals in (('tx', tx), ('ty', ty), ('tz', tz), ('ry', ry), ('s', sc)):
        scriptOp.appendChan(name).vals = vals
