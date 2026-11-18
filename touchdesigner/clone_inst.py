# CLONES + THICKNESS for a media layer in 3D OBJECT mode - Script CHOP callbacks (one per layer: mi<n>)
# One sample per drawn card: every copy of the layout x every slice of its thickness.
# Channels: tx ty tz rx ry rz s cr cg cb (colour darkens the inner slices so the side reads as an edge)
import math, random

LAYOUTS = ('single', 'grid', 'line', 'circle', 'rings', 'zigzag', 'spiral', 'scatter', 'wall')

def onSetupParameters(scriptOp): return
def onPulse(par): return

def _pts(lay, n, sp, T, cols=0, brick=0.0):
    """Positions (x, y, z) of n copies, spaced sp apart, centred on 0. Grids are widescreen unless you set the columns."""
    P = []
    if lay == 'grid' or lay == 'wall':
        c = int(cols) if cols >= 1 else max(1, int(round(math.sqrt(n * 16.0 / 9.0))))
        c = min(c, n); r = int(math.ceil(n / float(c)))
        for k in range(n):
            i, j = k % c, k // c
            P.append(((i - (c - 1) / 2.0 + (brick * 0.5 if j % 2 else 0.0)) * sp, ((r - 1) / 2.0 - j) * sp, 0.0))
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
    lay = str(g('lay', 'single')); n = 1 if lay == 'single' else max(1, min(400, int(g('cnt', 9))))
    sp = float(g('lsp', 1.0)) * 2.2; spin = float(g('lspin', 0.0)); wave = float(g('lwave', 0.0)); turn = float(g('lturn', 0.0))
    thick = max(0.0, float(g('thick', 0.0))); shade = float(g('edge', 0.5))
    T = absTime.seconds; kick = float(S.get('kick', 0.0)) * float(C.par.Reactivity.eval())
    ns = 1 if thick < 0.005 else 6 + int(thick * 18)              # slices: more depth, more slices (stays smooth from the side)
    if n * ns > 3200: ns = max(2, 3200 // n)                        # lots of copies: fewer slices each, so it stays smooth
    depth = thick * 0.6
    base = T * spin                                                # the whole layout turns (degrees per second)
    ca, sa = math.cos(math.radians(base)), math.sin(math.radians(base))
    pts = _pts(lay, n, sp, T, float(g('gcols', 0)), float(g('gbrick', 0.0)))
    W_ = max([abs(x) for x, y, z in pts] + [0.0]) * 2.0 + sp; H_ = max([abs(y) for x, y, z in pts] + [0.0]) * 2.0 + sp
    fit = 1.0 if lay == 'single' else min(7.2 / W_, 4.05 / H_) * float(g('lzoom', 1.0))   # the layout fills a 16:9 frame; Layout size zooms it
    csz = float(g('csz', 1.0))                                      # copy size: bigger copies can overlap
    pts = [(x * fit, y * fit, z * fit) for x, y, z in pts]; pts0 = pts
    sx_, sy_ = float(g('lscx', 0.0)), float(g('lscy', 0.0))         # the whole wall slides; copies leaving one side come back on the other
    if lay != 'single' and (abs(sx_) > 1e-4 or abs(sy_) > 1e-4 or ('cloff%d' % i) in S):
        d = S.setdefault('cloff%d' % i, [0.0, 0.0, T]); dt = max(0.0, min(0.1, T - d[2])); d[2] = T
        d[0] += sx_ * dt * 1.5; d[1] += sy_ * dt * 1.5
        Wf, Hf = W_ * fit, H_ * fit
        pts = [(((x + d[0] + Wf / 2) % Wf) - Wf / 2, ((y + d[1] + Hf / 2) % Hf) - Hf / 2, z) for x, y, z in pts]
    ch = {k: [] for k in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz', 's', 'cr', 'cg', 'cb', 'ti')}
    nt = max(1, int(S.get('mitex%d' % i, 1)))                       # how many GIFs share this layout (the engine sets this)
    pat = str(g('pat', 'order')); rnd = random.Random(11)
    cs = float(g('cspin', 0.0)); ax = str(g('caxis', 'y')); stag = float(g('cstag', 0.5))
    for k, (x, y, z) in enumerate(pts):
        x0, y0 = pts0[k][0], pts0[k][1]                               # the pattern stays with each copy while the wall slides
        u_ = max(sp * fit, 1e-4); col, row = int(math.floor(x0 / u_ + 0.501)), int(math.floor(y0 / u_ + 0.501))   # half-way rows don't pair up
        ring = int(round(math.hypot(x0, y0) / max(sp * fit, 1e-4)))
        ti = {'rows': row, 'cols': col, 'checker': col + row, 'rings': ring, 'random': rnd.randrange(nt)}.get(pat, k) % nt   # which GIF this copy shows
        x, y = x * ca - y * sa, x * sa + y * ca
        ph = k * 0.7
        y += math.sin(T * 2.2 + ph) * wave * 0.35 * sp * fit           # copies float up and down, each a little later
        z += math.cos(T * 1.7 + ph) * wave * 0.25 * sp * fit
        s = fit * csz * (1.0 + kick * 0.15 * (1.0 if lay == 'single' else math.cos(ph)))
        rx = rz = 0.0; ry = turn * math.sin(T * 1.3 + ph) * 35.0 if lay != 'wall' else 0.0     # copies rock left / right
        a_ = (T * cs + k * stag * 137.5) if abs(cs) > 1e-4 else 0.0                                # each copy spins around itself (stagger = not all in step)
        if ax == 'x': rx += a_
        elif ax == 'z': rz += a_
        elif ax == 'tumble': rx += a_ * 0.61; ry += a_; rz += a_ * 0.37
        else: ry += a_
        X, Y, Z = (math.radians(v) for v in (rx, ry, rz))
        for j in range(ns):
            f = 0.0 if ns == 1 else j / (ns - 1.0)                   # 0 = front face, 1 = back face
            ox, oy, oz = 0.0, 0.0, -f * depth * fit * csz                   # the slice offset turns with the copy (x, then y, then z)
            oy, oz = oy * math.cos(X) - oz * math.sin(X), oy * math.sin(X) + oz * math.cos(X)
            ox, oz = ox * math.cos(Y) + oz * math.sin(Y), -ox * math.sin(Y) + oz * math.cos(Y)
            ox, oy = ox * math.cos(Z) - oy * math.sin(Z), ox * math.sin(Z) + oy * math.cos(Z)
            ch['tx'].append(x + ox); ch['ty'].append(y + oy); ch['tz'].append(z + oz)
            ch['rx'].append(rx); ch['ry'].append(ry); ch['rz'].append(rz); ch['s'].append(s); ch['ti'].append(ti)
            c = 1.0 if (j == 0 or j == ns - 1) else 1.0 - shade * 0.75   # faces bright, the sides darker
            ch['cr'].append(c); ch['cg'].append(c); ch['cb'].append(c)
    scriptOp.clear(); scriptOp.numSamples = len(ch['tx'])
    for k, v in ch.items(): scriptOp.appendChan(k).vals = v
