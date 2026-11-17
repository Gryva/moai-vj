# CLONES + THICKNESS for a media layer in 3D OBJECT mode - Script CHOP callbacks (one per layer: mi<n>)
# One sample per drawn card: every copy of the layout x every slice of its thickness.
# Channels: tx ty tz rx ry rz s cr cg cb (colour darkens the inner slices so the side reads as an edge)
import math, random

LAYOUTS = ('single', 'grid', 'line', 'circle', 'rings', 'zigzag', 'spiral', 'scatter', 'wall')

def onSetupParameters(scriptOp): return
def onPulse(par): return

def _pts(lay, n, sp, T):
    """Positions (x, y, z) of n copies, spaced sp apart, centred on 0."""
    P = []
    if lay == 'grid' or lay == 'wall':
        c = max(1, int(math.ceil(math.sqrt(n)))); r = int(math.ceil(n / c))
        for k in range(n):
            i, j = k % c, k // c
            P.append(((i - (c - 1) / 2.0) * sp, ((r - 1) / 2.0 - j) * sp, 0.0))
    elif lay == 'line':
        P = [((k - (n - 1) / 2.0) * sp, 0.0, 0.0) for k in range(n)]
    elif lay == 'zigzag':
        P = [((k - (n - 1) / 2.0) * sp * 0.8, (0.5 if k % 2 else -0.5) * sp, 0.0) for k in range(n)]
    elif lay == 'circle':
        R = max(sp, n * sp / (2 * math.pi))
        P = [(math.cos(k / n * 2 * math.pi) * R, math.sin(k / n * 2 * math.pi) * R, 0.0) for k in range(n)]
    elif lay == 'rings':                                       # one in the middle, then rings of 6, 12, 18 ...
        P.append((0.0, 0.0, 0.0)); ring = 1
        while len(P) < n:
            m = min(6 * ring, n - len(P)); R = ring * sp
            for k in range(m):
                a = k / m * 2 * math.pi + ring * 0.35
                P.append((math.cos(a) * R, math.sin(a) * R, 0.0))
            ring += 1
    elif lay == 'spiral':
        for k in range(n):
            a = k * 2.39996; R = sp * 0.55 * math.sqrt(k + 0.5)       # golden-angle sunflower
            P.append((math.cos(a) * R, math.sin(a) * R, 0.0))
    elif lay == 'scatter':
        rnd = random.Random(7)
        W = sp * math.sqrt(n) * 0.9
        P = [((rnd.random() - 0.5) * W * 1.6, (rnd.random() - 0.5) * W, (rnd.random() - 0.5) * sp * 2.0) for k in range(n)]
    else:
        P = [(0.0, 0.0, 0.0)]
    return P

def onCook(scriptOp):
    i = int(scriptOp.name[2:]); C = op('/project1/CONTROLS'); E = op('/project1/fx_engine').module; S = E.S
    g = lambda k, d: C.par['M%d%s' % (i, k)].eval() if hasattr(C.par, 'M%d%s' % (i, k)) else d
    lay = str(g('lay', 'single')); n = 1 if lay == 'single' else max(1, min(64, int(g('cnt', 9))))
    sp = float(g('lsp', 1.0)) * 2.2; spin = float(g('lspin', 0.0)); wave = float(g('lwave', 0.0)); turn = float(g('lturn', 0.0))
    thick = max(0.0, float(g('thick', 0.0))); shade = float(g('edge', 0.5))
    T = absTime.seconds; kick = float(S.get('kick', 0.0)) * float(C.par.Reactivity.eval())
    ns = 1 if thick < 0.005 else 6 + int(thick * 18)              # slices: more depth, more slices (stays smooth from the side)
    depth = thick * 0.6
    base = T * spin                                                # the whole layout turns (degrees per second)
    ca, sa = math.cos(math.radians(base)), math.sin(math.radians(base))
    pts = _pts(lay, n, sp, T)
    ext = max([max(abs(x), abs(y)) for x, y, z in pts] + [0.0]) * 2.0 + 2.6
    fit = min(1.0, 4.0 / ext)                                       # more copies = smaller copies: the layout stays about screen size
    pts = [(x * fit, y * fit, z * fit) for x, y, z in pts]
    ch = {k: [] for k in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz', 's', 'cr', 'cg', 'cb')}
    for k, (x, y, z) in enumerate(pts):
        x, y = x * ca - y * sa, x * sa + y * ca
        ph = k * 0.7
        y += math.sin(T * 2.2 + ph) * wave * 0.35 * sp * fit           # copies float up and down, each a little later
        z += math.cos(T * 1.7 + ph) * wave * 0.25 * sp * fit
        s = fit * (1.0 + kick * 0.15 * (1.0 if lay == 'single' else math.cos(ph)))
        ry = turn * math.sin(T * 1.3 + ph) * 35.0 if lay != 'wall' else 0.0     # copies rock left / right
        for j in range(ns):
            f = 0.0 if ns == 1 else j / (ns - 1.0)                   # 0 = front face, 1 = back face
            r_ = math.radians(ry); dz = -f * depth * fit                 # the slice offset turns with the copy
            ch['tx'].append(x + dz * math.sin(r_)); ch['ty'].append(y); ch['tz'].append(z + dz * math.cos(r_))
            ch['rx'].append(0.0); ch['ry'].append(ry); ch['rz'].append(0.0); ch['s'].append(s)
            c = 1.0 if (j == 0 or j == ns - 1) else 1.0 - shade * 0.75   # faces bright, the sides darker
            ch['cr'].append(c); ch['cg'].append(c); ch['cb'].append(c)
    scriptOp.clear(); scriptOp.numSamples = len(ch['tx'])
    for k, v in ch.items(): scriptOp.appendChan(k).vals = v
