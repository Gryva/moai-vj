# Add new effects to the whole-picture chain, the four per-layer chains and FX_STACK. Safe to re-run (skips existing).
P = op('/project1')
NEW = [  # key, label, group, p1, p1label, p1min, p1max, p1step, insert after
    ('swirl', 'Swirl', 'warp', 0.4, '', 0, 1, 0.01, 'pulse'),
    ('ripple', 'Ripple', 'warp', 0.4, '', 0, 1, 0.01, 'swirl'),
    ('bulge', 'Bulge', 'warp', 0.8, '', 0, 1, 0.01, 'ripple'),
    ('wave', 'Wave', 'warp', 0.0, 'Mode', 0, 2, 1, 'bulge'),
    ('polar', 'Polar', 'warp', 0.0, 'Mode', 0, 1, 1, 'wave'),
    ('shards', 'Shards', 'warp', 0.4, '', 0, 1, 0.01, 'polar'),
    ('posterize', 'Toon', 'style', 0.3, '', 0, 1, 0.01, 'palette'),
    ('duotone', 'Duotone', 'style', 0.2, '', 0, 1, 0.01, 'posterize'),
    ('sketch', 'Sketch', 'style', 0.4, '', 0, 1, 0.01, 'duotone'),
    ('emboss', 'Emboss', 'style', 0.3, '', 0, 1, 0.01, 'sketch'),
    ('nightvis', 'Night vision', 'style', 0.3, '', 0, 1, 0.01, 'emboss'),
    ('oil', 'Oil paint', 'style', 0.5, '', 0, 1, 0.01, 'nightvis'),
    ('rgbsplit', 'RGB split', 'post', 0.3, '', 0, 1, 0.01, 'vhs'),
    ('grain', 'Film', 'post', 0.3, '', 0, 1, 0.01, 'rgbsplit'),
    ('crt', 'CRT', 'post', 0.4, '', 0, 1, 0.01, 'grain'),
    ('blocks', 'Blocks', 'post', 0.3, '', 0, 1, 0.01, 'crt'),
    ('flash', 'Flash', 'post', 0.5, '', 0, 1, 0.01, 'blocks'),
    ('letterbox', 'Cinema', 'post', 0.2, '', 0, 1, 0.01, 'flash'),
    ('static', 'Static', 'post', 0.3, '', 0, 1, 0.01, 'letterbox'),
    ('punch', 'Punch', 'post', 0.4, '', 0, 1, 0.01, 'static'),
    ('shake', 'Shake', 'post', 0.4, '', 0, 1, 0.01, 'punch'),
]
T = P.op('FX_STACK'); tmpl = P.op('fx_kaleido'); log = []

def insert_after(prefix, after, key, tmpl_op, dat):
    a = P.op(prefix + after)
    if P.op(prefix + key) is not None or a is None: return None
    nxt = [o for o in a.outputs if o.inputs and o.inputs[0] == a and not o.name.endswith('_fb')]
    g = P.copy(tmpl_op, name=prefix + key)
    g.par.pixeldat = dat.path
    g.inputConnectors[0].connect(a)
    for o in nxt: o.inputConnectors[0].connect(g)
    g.bypass = True; g.nodeX = a.nodeX + 40; g.nodeY = a.nodeY - 60
    return g

for key, label, grp, p1, p1l, lo, hi, st, after in NEW:
    dat = P.op('fxsrc_' + key)
    if dat is None:
        dat = P.create(textDAT, 'fxsrc_' + key); dat.par.file = 'td/fx/%s.glsl' % key; dat.par.syncfile = True
        dat.nodeX, dat.nodeY = tmpl.par.pixeldat.eval().nodeX, tmpl.par.pixeldat.eval().nodeY - 200
    g = insert_after('fx_', after, key, tmpl, dat)
    if g is not None:
        g.par.vec2valuex = 1.0; g.par.vec3valuex = p1; g.par.vec4valuew = 0; log.append(key)
    for n in (1, 2, 3, 4):
        insert_after('fxS%d_' % n, after, key, P.op('fxS%d_kaleido' % n), dat)
    if T.row(key) is None:
        r = T.row(after)[0].row + 1
        T.insertRow([key, label, grp, 0, 1.0, p1, p1l, lo, hi, st], r)
RESULT = log
