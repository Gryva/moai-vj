# PHONE REMOTE - Web Server DAT callbacks (remote_cb, synced to this file)
# Serves Visuals/web and talks to the page over a WebSocket.
import json, os, time

WEB = os.path.join(project.folder, 'web')
MIME = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css',
        '.jpg': 'image/jpeg', '.ttf': 'font/ttf', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json',
        '.webmanifest': 'application/manifest+json', '.ico': 'image/x-icon'}
CLIENTS = set()
SEEN = {}            # relay DAT name -> last time a phone talked through it
LAST = {'pars': None, 'L': None, 'b': None, 'n': 0}
LIVE = {'t': time.perf_counter(), 'f': absTime.frame, 'fps': 60.0}

# name, label, min, max, step, group
MSLOT_SLIDERS = []                                       # media layers 1-6: one set each (phone groups m<n>crop / key / obj / fr / op)
for _i in range(1, 7):
    _m = 'M%d' % _i
    MSLOT_SLIDERS += [(_m + 'cropl', 'Crop left', 0, 0.45, 0.01, 'm%dcrop' % _i), (_m + 'cropr', 'Crop right', 0, 0.45, 0.01, 'm%dcrop' % _i),
                      (_m + 'cropt', 'Crop top', 0, 0.45, 0.01, 'm%dcrop' % _i), (_m + 'cropb', 'Crop bottom', 0, 0.45, 0.01, 'm%dcrop' % _i),
                      (_m + 'keytol', 'Remove more screen', 0, 1, 0.01, 'm%dkey' % _i), (_m + 'keysoft', 'Edge softness', 0, 1, 0.01, 'm%dkey' % _i),
                      (_m + 'keyspill', 'Remove green / blue tint', 0, 1, 0.01, 'm%dkey' % _i), (_m + 'keyshrink', 'Shrink edges', 0, 4, 0.05, 'm%dkey' % _i),
                      (_m + 'objx', 'Left / right', -3, 3, 0.01, 'm%dobj' % _i), (_m + 'objy', 'Up / down', -2, 2, 0.01, 'm%dobj' % _i),
                      (_m + 'objz', 'Depth (back / front)', -4, 4, 0.05, 'm%dobj' % _i), (_m + 'objscale', 'Size', 0.2, 3, 0.01, 'm%dobj' % _i),
                      (_m + 'objturn', 'Turn', -180, 180, 1, 'm%dobj' % _i), (_m + 'objtilt', 'Tilt', -90, 90, 1, 'm%dobj' % _i),
                      (_m + 'mspeed', 'Spin speed (°/s)', 0, 180, 1, 'm%dmot' % _i), (_m + 'mamt', 'Amount', 0, 2, 0.01, 'm%dmot' % _i),
                      (_m + 'fzoom', 'Zoom', 0.2, 4, 0.01, 'm%dfr' % _i), (_m + 'fx', 'Left / right', -1, 1, 0.005, 'm%dfr' % _i),
                      (_m + 'fy', 'Up / down', -1, 1, 0.005, 'm%dfr' % _i), (_m + 'frot', 'Rotate', -180, 180, 1, 'm%dfr' % _i),
                      (_m + 'op', 'Brightness', 0, 1.5, 0.01, 'm%dop' % _i),
                      (_m + 'speed', 'Speed', 0.1, 4, 0.05, 'm%dplay' % _i), (_m + 'trimin', 'Start', 0, 1, 0.005, 'm%dplay' % _i),
                      (_m + 'trimout', 'End', 0, 1, 0.005, 'm%dplay' % _i)]
SLIDERS = MSLOT_SLIDERS + [
    ('Master', 'Brightness', 0, 1.5, 0.01, 'master'),
    ('Fadetime', 'Blackout fade', 0, 3, 0.05, 'master'),
    ('Autofade', 'Autopilot transition', 0, 4, 0.1, 'apfade'),     # set by the phone's transition buttons
    ('Swapfade', 'Linked layer switch', 0, 3, 0.05, 'swapfade'),    # 0 = instant cut; set by the phone's link menu
    # projector output (OUTPUT tab); corners are dragged on the phone's keystone pad
    ('Kstlx', 'Top-left x', -0.5, 0.5, 0.001, 'kscorner'), ('Kstly', 'Top-left y', -0.5, 0.5, 0.001, 'kscorner'),
    ('Kstrx', 'Top-right x', -0.5, 0.5, 0.001, 'kscorner'), ('Kstry', 'Top-right y', -0.5, 0.5, 0.001, 'kscorner'),
    ('Ksblx', 'Bottom-left x', -0.5, 0.5, 0.001, 'kscorner'), ('Ksbly', 'Bottom-left y', -0.5, 0.5, 0.001, 'kscorner'),
    ('Ksbrx', 'Bottom-right x', -0.5, 0.5, 0.001, 'kscorner'), ('Ksbry', 'Bottom-right y', -0.5, 0.5, 0.001, 'kscorner'),
    ('Kszoom', 'Size', 0.3, 2, 0.005, 'proj'), ('Ksx', 'Move left / right', -1, 1, 0.002, 'proj'), ('Ksy', 'Move down / up', -1, 1, 0.002, 'proj'),
    ('Ksrot', 'Rotate (°)', -45, 45, 0.1, 'proj'), ('Ksfeather', 'Soft edges', 0, 0.2, 0.002, 'proj'),
    ('Ksbright', 'Brightness', 0, 2, 0.01, 'projlook'), ('Kslift', 'Black level', 0, 0.2, 0.002, 'projlook'), ('Ksgamma', 'Gamma', 0.5, 2, 0.01, 'projlook'),
    ('Autotime', 'Autopilot: new preset every (s)', 5, 300, 5, 'master'),
    ('Reactivity', 'Reactivity', 0, 2, 0.01, 'audio'),
    ('Gain', 'Input gain', 0, 4, 0.01, 'audio'),
    ('Gate', 'Noise gate dB', -90, -20, 1, 'audio'),
    ('Range', 'Dynamic range dB', 10, 60, 1, 'audio'),
    ('Smoothing', 'Smoothing', 0, 0.95, 0.01, 'audio'),
    ('Beatsense', 'Beat sensitivity', 0, 1, 0.01, 'beat'),
    ('Beatfeel', 'Beat feel (punchy - smooth)', 0, 1, 0.01, 'beat'),
    ('Safety', 'Flash safety', 0, 1, 0.01, 'beat'),
    ('Modeltrans', 'Transition time (s)', 0, 4, 0.05, 'model'),
    ('Textamount', 'Amount', 0, 1, 0.01, 'text'),
    ('Textsize', 'Size', 0.3, 2.5, 0.01, 'text'),
    ('Textglow', 'Glow', 0, 1.5, 0.01, 'text'),
    ('Textspeed', 'Speed', 0, 3, 0.01, 'text'),
    ('Textreact', 'Beat reaction', 0, 2, 0.01, 'text'),
    ('T2amount', 'Amount', 0, 1, 0.01, 'text2'), ('T2size', 'Size', 0.3, 2.5, 0.01, 'text2'), ('T2glow', 'Glow', 0, 1.5, 0.01, 'text2'), ('T2speed', 'Speed', 0, 3, 0.01, 'text2'), ('T2react', 'Beat reaction', 0, 2, 0.01, 'text2'),
    ('Textx', 'Left / right', -1, 1, 0.01, 'textpos'), ('Texty', 'Down / up', -1, 1, 0.01, 'textpos'),
    ('T2x', 'Left / right', -1, 1, 0.01, 'text2pos'), ('T2y', 'Down / up', -1, 1, 0.01, 'text2pos'),
    ('T3x', 'Left / right', -1, 1, 0.01, 'text3pos'), ('T3y', 'Down / up', -1, 1, 0.01, 'text3pos'),
    ('Textdepth', 'Depth (back / front)', -4, 4, 0.05, 'tobj1'), ('Textoscale', 'Size', 0.2, 3, 0.01, 'tobj1'), ('Textoturn', 'Turn', -180, 180, 1, 'tobj1'), ('Textotilt', 'Tilt', -90, 90, 1, 'tobj1'),
    ('T2depth', 'Depth (back / front)', -4, 4, 0.05, 'tobj2'), ('T2oscale', 'Size', 0.2, 3, 0.01, 'tobj2'), ('T2oturn', 'Turn', -180, 180, 1, 'tobj2'), ('T2otilt', 'Tilt', -90, 90, 1, 'tobj2'),
    ('T3depth', 'Depth (back / front)', -4, 4, 0.05, 'tobj3'), ('T3oscale', 'Size', 0.2, 3, 0.01, 'tobj3'), ('T3oturn', 'Turn', -180, 180, 1, 'tobj3'), ('T3otilt', 'Tilt', -90, 90, 1, 'tobj3'),
    ('Textmspeed', 'Spin speed (°/s)', 0, 180, 1, 'tmot1'), ('Textmamt', 'Amount', 0, 2, 0.01, 'tmot1'),
    ('T2mspeed', 'Spin speed (°/s)', 0, 180, 1, 'tmot2'), ('T2mamt', 'Amount', 0, 2, 0.01, 'tmot2'),
    ('T3mspeed', 'Spin speed (°/s)', 0, 180, 1, 'tmot3'), ('T3mamt', 'Amount', 0, 2, 0.01, 'tmot3'),
    ('Modelx', 'Left / right', -3, 3, 0.01, 'mobj'), ('Modely', 'Up / down', -2, 2, 0.01, 'mobj'), ('Modelz', 'Depth (back / front)', -4, 4, 0.05, 'mobj'),
    ('Modelscale', 'Size', 0.2, 3, 0.01, 'mobj'), ('Modelturn', 'Turn', -180, 180, 1, 'mobj'), ('Modeltilt', 'Tilt', -90, 90, 1, 'mobj'),
    ('T3amount', 'Amount', 0, 1, 0.01, 'text3'), ('T3size', 'Size', 0.3, 2.5, 0.01, 'text3'), ('T3glow', 'Glow', 0, 1.5, 0.01, 'text3'), ('T3speed', 'Speed', 0, 3, 0.01, 'text3'), ('T3react', 'Beat reaction', 0, 2, 0.01, 'text3'),
    ('Speed', 'Spin speed', -180, 180, 1, 'motion'),
    ('Spinboost', 'Bass spin boost', 0, 300, 1, 'motion'),
    ('Tilt', 'Model tilt', -60, 60, 1, 'motion'),
    ('Angle', 'Model angle', -180, 180, 1, 'motion'),
    ('Distance', 'Distance', 0.5, 15, 0.05, 'camera'),
    ('Elevation', 'Elevation', -85, 85, 1, 'camera'),
    ('Orbitspeed', 'Camera circles the scene (°/s)', -120, 120, 1, 'camera'),
    ('Fov', 'Lens (FOV)', 10, 120, 1, 'camera'),
    ('Roll', 'Roll', -180, 180, 1, 'camera'),
    ('Shake', 'Handheld shake', 0, 2, 0.01, 'camera'),
    ('Orbitsway', 'Camera sways around', 0, 90, 1, 'move'),
    ('Elevsway', 'Elevation sway', 0, 60, 1, 'move'),
    ('Distsway', 'Push / pull', 0, 5, 0.05, 'move'),
    ('Rollsway', 'Roll sway', 0, 45, 1, 'move'),
    ('Swayspeed', 'Sway speed', 0, 4, 0.01, 'move'),
    ('Audiocam', 'Audio > camera', 0, 3, 0.01, 'kick'),
    ('Punch', 'Kick push-in', 0, 1.5, 0.01, 'kick'),
    ('Kickjolt', 'Kick jolt', 0, 30, 0.5, 'kick'),
    ('Transition', 'Saved view glide (s)', 0, 5, 0.05, 'move'),
    ('Response', 'Response (s)', 0, 1, 0.01, 'move'),
    ('Inertia', 'Flick inertia', 0, 0.99, 0.01, 'move'),
    ('Gridcount', 'Copies per side', 1, 9, 1, 'grid'),
    ('Griddepth', 'Depth layers', 1, 4, 1, 'grid'),
    ('Gridspace', 'Spacing', 1, 6, 0.05, 'grid'),
    ('Gridwave', 'Bass wave', 0, 3, 0.01, 'grid'),
    ('Gridstagger', 'Spin offset', 0, 180, 1, 'grid'),
    ('Monitorvol', 'Headphone volume', 0, 1.5, 0.01, 'audio'),
    ('Cammix', 'Camera amount', 0, 1, 0.01, 'camfeed'),
    ('Clipspeed', 'Clip speed', 0.25, 2, 0.05, 'clip'),
    ('Drawmix', 'Drawing brightness', 0, 1.5, 0.01, 'draw'),
    ('Motionamt', 'Motion amount', 0, 2, 0.01, 'motion2'),
    ('Animspeed', 'Animation speed', 0, 3, 0.01, 'anim'),
    ('Animbeat', 'Speed-up on the beat', 0, 2, 0.01, 'anim'),
    ('Fcamzoom', 'Zoom', 0.2, 4, 0.01, 'frcam'), ('Fcamx', 'Left / right', -1, 1, 0.005, 'frcam'), ('Fcamy', 'Up / down', -1, 1, 0.005, 'frcam'), ('Fcamrot', 'Rotate', -180, 180, 1, 'frcam'),
    ('Fdrawzoom', 'Zoom', 0.2, 4, 0.01, 'frdraw'), ('Fdrawx', 'Left / right', -1, 1, 0.005, 'frdraw'), ('Fdrawy', 'Up / down', -1, 1, 0.005, 'frdraw'), ('Fdrawrot', 'Rotate', -180, 180, 1, 'frdraw'),
    ('Opmodel', 'Brightness', 0, 1.5, 0.01, 'opmodel'),
    ('Opcamera', 'Brightness', 0, 1.5, 0.01, 'opcamera'),
    ('Opdraw', 'Brightness', 0, 1.5, 0.01, 'opdraw'),
]
TOGGLES = ['M%d%s' % (i, n) for i in range(1, 7) for n in ('on', 'vis', 'keyon', 'mrev')] + ['Textmrev', 'T2mrev', 'T3mrev'] + [ 'Autopilot', 'Autospin', 'Spinrev', 'Blackout', 'Showlabel', 'Texton', 'T2on', 'T3on', 'Monitor', 'Cammirror', 'Textpin', 'Statue', 'Clipbounce', 'Drawon', 'Ksflipx', 'Ksflipy', 'Projwin', 'Aplost', 'Automic']
TEXTMENUS = ['M%d%s' % (i, n) for i in range(1, 7) for n in ('kind', 'file', 'mode', 'keycolor', 'keyhex', 'motion', 'maxis', 'name')] + ['Textmotion', 'Textmaxis', 'T2motion', 'T2maxis', 'T3motion', 'T3maxis', 'Textname', 'T2name', 'T3name', 'Modelname'] + ['Spinaxis', 'Layerorder', 'Links', 'Textstr', 'Textmode', 'Textlayout', 'Textanim', 'Textfont', 'Textcolor', 'Textdir', 'Textadir', 'Textspace'] + ['T%d%s' % (n, k) for n in (2, 3) for k in ('str', 'mode', 'layout', 'anim', 'font', 'color', 'dir', 'adir', 'space')] + ['Camsrc', 'Clipstate', 'Camfit', 'Motion', 'Kstest', 'Projmon', 'Automode']
ALLOWED = set(s[0] for s in SLIDERS) | set(TOGGLES) | {'Model', 'Height', 'Pan', 'Orbit', 'Scene', 'Modelstyle'} | set(TEXTMENUS)

def _C(): return op('/project1/CONTROLS')
def _E(): return op('/project1/fx_engine').module

# ---------------------------------------------------------------- phone camera frames
# JPEG frames published by the phone page to <base>/cam. Only accepted while the camera
# source is switched on (which needs an unlocked phone), decoded here, shown by /project1/phonecam.
CAMF = {'img': None, 'new': False, 't': 0.0, 'n': 0, 'bad': 0}
# ---------------------------------------------------------------- clip library
# Every recording is kept: td/clips/<id>.mjpg (the JPEG frames back to back) + <id>.json (frame sizes,
# arrival times, a small picture). Frames load from disk the first time a clip is played.
CLIPDIR = os.path.join(project.folder, 'td', 'clips')
CLIP_MAX = 60.0
CLIPS = {}                                   # id -> {'times', 'sizes', 'thumb', 'dur', 'frames' (None until played)}
REC = {'frames': [], 'times': []}
CLIP = {'id': None, 't0': 0.0, 'last': -1}

def jpegToRGBA(payload):
    import cv2, numpy as np
    img = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
    if img is None or img.shape[0] > 1080 or img.shape[1] > 1920: return None
    return np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)[::-1])

def _clipScan():
    if CLIPS: return
    try:
        for fn in sorted(os.listdir(CLIPDIR)):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(CLIPDIR, fn)) as fh: m = json.load(fh)
                    CLIPS[fn[:-5]] = {'times': m['times'], 'sizes': m['sizes'], 'thumb': m.get('thumb', ''), 'dur': m['times'][-1], 'frames': None}
                except Exception as e:
                    print('clip skipped', fn, e)
    except FileNotFoundError:
        pass

def clipList():
    _clipScan()
    return [{'id': k, 'dur': round(v['dur'], 1), 'thumb': v['thumb']} for k, v in sorted(CLIPS.items())]

def fxpMsg():
    return {'t': 'fxps', 'v': [{'name': p['name'], 'on': [k for k, v in p['layers'].items() if v[0]]} for p in _E().fxList()]}

def clipsMsg():
    if CAMERA_REMOVED: return {'t': 'clips', 'v': [], 'cur': None}
    playing = CLIP['id'] if _C().par.Clipstate.eval() == 'loop' else None
    return {'t': 'clips', 'v': clipList(), 'cur': playing}

CAMERA_REMOVED = True        # phone camera + clips removed for privacy: frames are thrown away unread

def camFrame(payload):
    if CAMERA_REMOVED: return
    payload = streamCheck(payload)
    if payload is None: return
    C = _C()
    state = C.par.Clipstate.eval()
    if C.par.Camsrc.eval() == 'off' and state != 'rec': return
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < 200 or len(payload) > 400000: return
    if state == 'loop': return                                   # a clip owns the picture now
    try:
        img = jpegToRGBA(payload)
        if img is None: CAMF['bad'] += 1; return
        now = time.perf_counter()
        if state == 'rec':
            REC['frames'].append(bytes(payload)); REC['times'].append(now)
            C.par.Cliplen = round(now - REC['times'][0], 1)
            if now - REC['times'][0] >= CLIP_MAX: clipStop(); _all(clipsMsg())
        CAMF['img'] = img; CAMF['new'] = True; CAMF['t'] = now; CAMF['n'] += 1
    except Exception:
        CAMF['bad'] += 1

# ---------------------------------------------------------------- doodles / shapes drawn on the phone
DRAWF = {'img': None, 'new': False, 't': 0.0}              # (old single drawing - kept so older code never breaks)
DRAWS = {}                                                  # media layer -> {'img': RGBA, 'new'} for layers of kind 'draw'

def drawRGBA(bgr):
    """Phone drawings are colour on black: black becomes see-through, colours keep full strength."""
    import numpy as np, cv2
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
    a = rgb.max(axis=2, keepdims=True)
    col = np.where(a > 0, rgb * 255.0 / np.maximum(a, 1.0), 0)
    return np.concatenate([col, a], axis=2).clip(0, 255).astype(np.uint8)

def drawFrame(payload):
    """The phone sends its whole drawing as a PNG whenever it changes (black = empty). Only while Draw is on."""
    payload = streamCheck(payload)
    if payload is None or not isinstance(payload, (bytes, bytearray)) or len(payload) < 60 or len(payload) > 1500000: return
    C = _C()
    if payload[0] != 0x89 and 1 <= payload[0] <= 6: slot, payload = payload[0], payload[1:]     # first byte = which drawing layer
    else: slot = next((i for i in range(1, 7) if C.par['M%don' % i].eval() and C.par['M%dkind' % i].eval() == 'draw'), 0)
    if not slot or not C.par['M%don' % slot].eval() or C.par['M%dkind' % slot].eval() != 'draw': return
    try:
        import cv2, numpy as np
        img = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        if img is None or img.shape[0] > 1080 or img.shape[1] > 1920: return
        DRAWS[slot] = {'img': np.ascontiguousarray(drawRGBA(img)[::-1]), 'new': True, 't': time.perf_counter()}
    except Exception as e:
        print('draw frame failed', e)

# ---------------------------------------------------------------- media library (images + videos)
# Drop files into <project>/media on the laptop, or send images from the phone (saved in media/uploads).
# Phones only ever pick files from this list by id - never a path.
MEDIADIR = os.path.join(project.folder, 'media')
MEDIA_THUMBS = os.path.join(project.folder, 'td', 'mediathumbs')
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')
VID_EXT = ('.mp4', '.mov', '.m4v', '.webm', '.avi', '.mkv', '.gif')
VIDEODIR = os.path.join(project.folder, 'videos')       # your own clip library: shows up in the phone's Media list
UPLOADS = {}

def _mediaFiles():
    out = []
    for root, pre in ((MEDIADIR, ''), (VIDEODIR, 'videos/')):
        for dp, dn, fn in os.walk(root):
            for n in fn:
                ext = os.path.splitext(n)[1].lower()
                if ext in IMG_EXT or ext in VID_EXT:
                    full = os.path.join(dp, n)
                    out.append((pre + os.path.relpath(full, root).replace('\\', '/'), full, 'video' if ext in VID_EXT else 'image'))
    return sorted(out, key=lambda x: os.path.getmtime(x[1]))

def _asciiPath(p):
    """OpenCV on Windows can't open names with letters like č ć đ š ž: use the short 8.3 name instead."""
    try:
        p.encode('ascii'); return p
    except UnicodeEncodeError: pass
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(p, buf, 1024): return buf.value
    except Exception: pass
    return p

def _tdGrab(full):
    """A frame read by a hidden Movie File In TOP (handles any name and format TouchDesigner can play)."""
    try:
        import numpy as np, cv2
        g = op('/project1/thumb_grab') or op('/project1').create(moviefileinTOP, 'thumb_grab')
        g.par.play = False; g.par.file = full; g.par.indexunit = 'fraction'; g.par.index = 0.2
        g.cook(force=True)
        a = g.numpyArray(delayed=False)
        g.par.file = ''
        if a is None or a.size == 0 or g.width < 8: return None
        a = (np.clip(a[::-1, :, :3], 0, 1) * 255).astype(np.uint8)
        return cv2.cvtColor(a, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print('thumb grab failed', full, e); return None

def _mediaThumb(rel, full, kind):
    import cv2, base64, hashlib
    os.makedirs(MEDIA_THUMBS, exist_ok=True)
    key = hashlib.sha1((rel + str(os.path.getmtime(full))).encode()).hexdigest()[:16]
    tp = os.path.join(MEDIA_THUMBS, key + '.jpg')
    if not os.path.exists(tp):
        im = None
        try:
            if kind == 'video':
                cap = cv2.VideoCapture(_asciiPath(full)); n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if n > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * 0.2))
                ok, im = cap.read(); cap.release()
            else:
                im = cv2.imread(full)
        except Exception as e:
            print('media thumb failed', rel, e)
        if im is None:                                           # GIFs and odd files: try Pillow
            try:
                from PIL import Image
                import numpy as np
                g = Image.open(full); g.seek(0)
                im = cv2.cvtColor(np.array(g.convert('RGB')), cv2.COLOR_RGB2BGR)
            except Exception: pass
        if im is None: im = _tdGrab(full)                       # last resort: TouchDesigner decodes it itself
        if im is None: return ''
        h, w = im.shape[:2]; k = 192.0 / max(w, h)
        cv2.imwrite(tp, cv2.resize(im, (max(1, int(w * k)), max(1, int(h * k)))), [cv2.IMWRITE_JPEG_QUALITY, 70])
    return base64.b64encode(open(tp, 'rb').read()).decode('ascii')

def mediaMsg():
    """The list only (small enough for every relay); pictures follow one per message (mediaThumbs)."""
    items = [{'id': rel, 'kind': kind, 'up': rel.startswith('uploads/')} for rel, full, kind in _mediaFiles()]
    return {'t': 'media', 'v': items[-80:]}

def mediaThumbs(send):
    for rel, full, kind in _mediaFiles()[-80:]:
        th = _mediaThumb(rel, full, kind)
        if th: send({'t': 'mthumb', 'id': rel, 'img': th})

def _fitSoon(i=None):
    run("op('/project1/fx_engine').module.mediaFit(%r)" % i, delayFrames=12)   # after the new file has loaded (its size is known)

def isVideo(rel):
    return os.path.splitext(str(rel))[1].lower() in VID_EXT

MEDIA_UP = {'slot': None}                                  # the layer that pressed + ADD gets the next upload

def mediaFree(kind='video'):
    """First empty media layer (1-6), switched on and ready for a file; None when all 6 are used."""
    C = _C()
    for i in range(1, 7):
        if not C.par['M%don' % i].eval():
            _E().mediaSlotClear(C, i)
            C.par['M%don' % i] = True; C.par['M%dvis' % i] = True; C.par['M%dkind' % i] = kind
            o = [k for k in _E().layerOrder(C) if k != 'm%d' % i]                 # a new layer goes on top of the others
            C.par.Layerorder = ','.join(['m%d' % i] + o)
            return i
    return None

def mediaPlay(mid, fit=False, slot=None, keep=False):
    """Put a picture / video on media layer <slot> (a new layer if none given)."""
    C = _C()
    for rel, full, kind in _mediaFiles():
        if rel == mid:
            i = slot or mediaFree(kind)
            if not i: return False
            mf = op('/project1/mf%d' % i); mf.par.file = full; mf.par.play = True
            C.par['M%dfile' % i] = rel; C.par['M%dkind' % i] = kind
            if not keep: C.par['M%don' % i] = True; C.par['M%dvis' % i] = True       # picking a file switches its layer on
            if C.par['M%dmode' % i].eval() == 'object' and fit: _fitSoon(i)
            return True
    return False

def mediaStop(i):
    C = _C(); C.par['M%dfile' % i] = ''; op('/project1/mf%d' % i).par.file = ''

def mediaDel(mid):
    """Only pictures sent from a phone can be deleted from a phone."""
    if not mid.startswith('uploads/') or '..' in mid: return
    full = os.path.normpath(os.path.join(MEDIADIR, mid))
    if os.path.commonpath([os.path.normpath(os.path.join(MEDIADIR, 'uploads')), full]) != os.path.normpath(os.path.join(MEDIADIR, 'uploads')): return
    for i in range(1, 7):
        if _C().par['M%dfile' % i].eval() == mid: mediaStop(i)
    try: os.remove(full)
    except Exception: pass

# ---- video upload: the phone sends JPEG frames (any phone, any codec) in parts; rebuilt here as an MP4
VUPS = {}
VJOBS = {}
VID_MAXF, VID_MAXB = 480, 48 * 1024 * 1024

def videoPart(msg):
    import base64
    now = time.time()
    for k in [k for k, u in VUPS.items() if now - u['t'] > 600]: VUPS.pop(k, None)
    uid = str(msg.get('u', ''))[:24]
    n, f, p, np_ = int(msg.get('n', 0)), int(msg.get('f', -1)), int(msg.get('p', -1)), int(msg.get('np', 0))
    fps = float(msg.get('fps', 15))
    if not uid or not (0 < n <= VID_MAXF) or not (0 <= f < n) or not (0 < np_ <= 12) or not (0 <= p < np_) or not (4 <= fps <= 30): return
    d = str(msg.get('d', ''))
    if len(d) > 30000: return
    u = VUPS.setdefault(uid, {'n': n, 'fps': fps, 'fr': {}, 't': now, 'size': 0, 'c': str(msg.get('c', ''))[:16]})
    if u['n'] != n: return
    fr = u['fr'].setdefault(f, {'np': np_, 'parts': {}})
    if p in fr['parts']: return
    try: b = base64.b64decode(d, validate=True)
    except Exception: return
    u['size'] += len(b); u['t'] = now
    if u['size'] > VID_MAXB: VUPS.pop(uid, None); return
    fr['parts'][p] = b

def videoEnd(msg):
    """Phone finished sending: build the video, or ask again for whatever got lost on the way."""
    import threading
    uid = str(msg.get('u', ''))[:24]; u = VUPS.get(uid)
    if not u: return {'t': 'vmiss', 'u': uid, 'all': True}
    miss = []
    for f in range(u['n']):
        fr = u['fr'].get(f)
        if fr is None: miss.append([f, -1])
        else: miss += [[f, p] for p in range(fr['np']) if p not in fr['parts']]
        if len(miss) >= 300: break
    if miss: return {'t': 'vmiss', 'u': uid, 'miss': miss}
    VUPS.pop(uid, None)
    frames = [b''.join(u['fr'][f]['parts'][p] for p in range(u['fr'][f]['np'])) for f in range(u['n'])]
    os.makedirs(os.path.join(MEDIADIR, 'uploads'), exist_ok=True)
    name = 'uploads/phone_vid_%s.mp4' % time.strftime('%Y%m%d_%H%M%S')
    VJOBS[uid] = {'state': 'run', 'name': name, 'err': ''}
    threading.Thread(target=_videoBuild, args=(uid, frames, u['fps'], os.path.join(MEDIADIR, name)), daemon=True).start()
    run("op('/project1/remote_cb').module.videoPoll(%r)" % uid, delayMilliSeconds=300)
    return {'t': 'vbusy', 'u': uid}

def _videoBuild(uid, frames, fps, path):
    """Runs in a background thread (no TouchDesigner calls here). Every frame is decoded and re-encoded."""
    import cv2, numpy as np
    try:
        w = None; size = None; tmp = path + '.part.mp4'; good = 0
        for b in frames:
            im = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
            if im is None: continue
            if size is None:
                h0, w0 = im.shape[:2]; k = min(1.0, 1280.0 / max(w0, h0))
                size = (max(2, int(w0 * k) // 2 * 2), max(2, int(h0 * k) // 2 * 2))
                w = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
            if im.shape[1] != size[0] or im.shape[0] != size[1]: im = cv2.resize(im, size)
            w.write(im); good += 1
        if w is not None: w.release()
        if good < 2: raise ValueError('no usable frames')
        os.replace(tmp, path)
        VJOBS[uid]['state'] = 'done'
    except Exception as e:
        VJOBS[uid].update(state='fail', err=str(e)[:80])

def videoPoll(uid):
    j = VJOBS.get(uid)
    if not j: return
    if j['state'] == 'run':
        run("op('/project1/remote_cb').module.videoPoll(%r)" % uid, delayMilliSeconds=300); return
    VJOBS.pop(uid, None)
    if j['state'] == 'done':
        mediaPlay(j['name'], fit=True, slot=MEDIA_UP['slot'] if MEDIA_UP['slot'] and not _C().par['M%dfile' % MEDIA_UP['slot']].eval() else None)
        _all({'t': 'vdone', 'u': uid, 'id': j['name']}); _allMedia(); _all(clipsMsg()); _publish(state(), active_only=True)
    else:
        _all({'t': 'err', 'msg': 'Video failed: ' + j['err']})

def mediaChunk(msg):
    """Image upload from the phone, in base64 chunks. Re-encoded as a clean JPEG (nothing else gets through)."""
    import base64, cv2, numpy as np
    now = time.time()
    for k in [k for k, u in UPLOADS.items() if now - u['t'] > 120]: UPLOADS.pop(k, None)
    uid, i, n = str(msg.get('u', ''))[:24], int(msg.get('i', -1)), int(msg.get('n', 0))
    if not uid or not (0 < n <= 200) or not (0 <= i < n): return None
    u = UPLOADS.setdefault(uid, {'n': n, 'parts': {}, 't': now, 'size': 0})
    d = base64.b64decode(str(msg.get('d', '')), validate=True)
    u['size'] += len(d); u['t'] = now
    if u['size'] > 8 * 1024 * 1024: UPLOADS.pop(uid, None); return 'too big'
    u['parts'][i] = d
    if len(u['parts']) < u['n']: return None
    data = b''.join(u['parts'][k] for k in range(u['n'])); UPLOADS.pop(uid, None)
    im = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if im is None: return 'not an image'
    h, w = im.shape[:2]; k = min(1.0, 1920.0 / max(w, h))
    if k < 1: im = cv2.resize(im, (int(w * k), int(h * k)))
    os.makedirs(os.path.join(MEDIADIR, 'uploads'), exist_ok=True)
    name = 'uploads/phone_%s.jpg' % time.strftime('%Y%m%d_%H%M%S')
    cv2.imwrite(os.path.join(MEDIADIR, name), im, [cv2.IMWRITE_JPEG_QUALITY, 90])
    mediaPlay(name, slot=MEDIA_UP['slot'] if MEDIA_UP['slot'] and not _C().par['M%dfile' % MEDIA_UP['slot']].eval() else None)
    return 'ok'

def clipRec():
    C = _C()
    REC['frames'] = []; REC['times'] = []; C.par.Cliplen = 0
    if C.par.Camsrc.eval() == 'off': C.par.Camsrc = 'cam'
    C.par.Clipstate = 'rec'

def clipStop():
    """Stop recording, keep it as a new clip and start looping it."""
    import cv2, numpy as np, base64
    C = _C(); fr, ts = REC['frames'], REC['times']
    REC['frames'], REC['times'] = [], []
    if len(fr) < 3: C.par.Clipstate = 'off'; return None
    cid = time.strftime('%Y%m%d_%H%M%S')
    times = [round(x - ts[0], 4) for x in ts]
    thumb = ''
    try:
        im = cv2.imdecode(np.frombuffer(fr[len(fr) // 2], np.uint8), cv2.IMREAD_COLOR)
        h, w = im.shape[:2]; k = 192.0 / max(w, h)
        ok, b = cv2.imencode('.jpg', cv2.resize(im, (int(w * k), int(h * k))), [cv2.IMWRITE_JPEG_QUALITY, 70])
        thumb = base64.b64encode(b.tobytes()).decode('ascii')
    except Exception as e:
        print('clip thumb failed', e)
    try:
        os.makedirs(CLIPDIR, exist_ok=True)
        with open(os.path.join(CLIPDIR, cid + '.mjpg'), 'wb') as fh:
            for b in fr: fh.write(b)
        _E().writeJsonSafe(os.path.join(CLIPDIR, cid + '.json'), {'times': times, 'sizes': [len(b) for b in fr], 'thumb': thumb}, bak=False)
    except Exception as e:
        print('clip save failed', e)
    _clipScan()
    CLIPS[cid] = {'times': times, 'sizes': [len(b) for b in fr], 'thumb': thumb, 'dur': times[-1], 'frames': fr}
    while len(CLIPS) > 24: clipDel(sorted(CLIPS)[0])                # keep the newest 24
    clipPlay(cid)
    return cid

def clipPlay(cid):
    _clipScan()
    c = CLIPS.get(cid)
    if c is None: return False
    if c['frames'] is None:
        data = open(os.path.join(CLIPDIR, cid + '.mjpg'), 'rb').read(); fr, p = [], 0
        for n in c['sizes']: fr.append(data[p:p + n]); p += n
        c['frames'] = fr
    for k, v in CLIPS.items():                                   # long sets: don't keep every clip ever played in memory
        if k != cid: v['frames'] = None
    C = _C()
    CLIP.update(id=cid, t0=time.perf_counter(), last=-1)
    C.par.Cliplen = round(c['dur'], 1)
    if C.par.Camsrc.eval() == 'off': C.par.Camsrc = 'cam'
    C.par.Clipstate = 'loop'
    return True

def clipFrame():
    """Every frame while looping: show the frame for 'now' using the real recorded timing. Bounce = back and forth."""
    import bisect
    c = CLIPS.get(CLIP['id'])
    if not c or not c['frames'] or len(c['frames']) < 2: return
    fr, ts = c['frames'], c['times']
    C = _C(); dur = max(0.05, ts[-1])
    pos = (time.perf_counter() - CLIP['t0']) * float(C.par.Clipspeed.eval())
    if C.par.Clipbounce.eval():
        pos = pos % (2.0 * dur); pos = pos if pos <= dur else 2.0 * dur - pos
    else:
        pos = pos % dur
    i = min(len(fr) - 1, max(0, bisect.bisect_right(ts, pos) - 1))
    CAMF['t'] = time.perf_counter()
    if i == CLIP['last']: return
    img = jpegToRGBA(fr[i])
    if img is not None:
        CAMF['img'] = img; CAMF['new'] = True; CLIP['last'] = i

def clipLive():
    _C().par.Clipstate = 'off'; CLIP['id'] = None

def clipDel(cid):
    if CLIP['id'] == cid: clipLive()
    CLIPS.pop(cid, None)
    for ext in ('.mjpg', '.json'):
        try: os.remove(os.path.join(CLIPDIR, cid + ext))
        except Exception: pass

def _pars():
    C = _C()
    d = {s[0]: round(float(C.par[s[0]].eval()), 4) for s in SLIDERS}
    for t in TOGGLES: d[t] = bool(C.par[t].eval())
    d['Model'] = C.par.Model.eval(); d['Scene'] = C.par.Scene.eval(); d['Modelstyle'] = C.par.Modelstyle.eval()
    for t in TEXTMENUS: d[t] = C.par[t].eval()
    d['Presetslot'] = int(C.par.Presetslot.eval()); d['Presetname'] = C.par.Presetname.eval()
    d['Cliplen'] = round(float(C.par.Cliplen.eval()), 1)
    for pre in ('Text', 'T2', 'T3'):
        d[pre + 'cm'] = int(C.par[pre + 'cm'].eval()); d[pre + 'ca'] = C.par[pre + 'ca'].eval(); d[pre + 'cb'] = C.par[pre + 'cb'].eval(); d[pre + 'cang'] = round(float(C.par[pre + 'cang'].eval()), 1)
    return d

def _presets():
    t = op('/project1/CAM_PRESETS')
    return [t[r, 'name'].val for r in range(1, t.numRows)]

def _presetData():
    """Each saved view's camera numbers, for the little movement icons on the phone."""
    t = op('/project1/CAM_PRESETS'); out = []
    keys = ('Orbit', 'Orbitspeed', 'Orbitsway', 'Elevation', 'Elevsway', 'Distance', 'Distsway', 'Roll', 'Rollsway', 'Shake', 'Fov')
    for r in range(1, t.numRows):
        d = {}
        for k in keys:
            try: d[k] = round(float(t[r, k].val or 0), 2)
            except Exception: d[k] = 0.0
        out.append(d)
    return out

def _presetsMoving():
    """Saved views whose camera keeps moving (circles / sways) - marked on the phone so they aren't mistaken for object spin."""
    t = op('/project1/CAM_PRESETS'); out = []
    for r in range(1, t.numRows):
        try: out.append(any(abs(float(t[r, k].val or 0)) > 0.01 for k in ('Orbitspeed', 'Orbitsway', 'Elevsway', 'Distsway', 'Rollsway')))
        except Exception: out.append(False)
    return out

def _layers():
    out = []
    for r in _E().layers():
        out.append({'k': r['key'], 'label': r['label'], 'g': r['group'], 'on': r['on'] in ('1', 'True', 'true'),
                    'amt': float(r['amt']), 'p1': float(r['p1']), 'p1label': r['p1label'],
                    'p1min': float(r['p1min']), 'p1max': float(r['p1max']), 'p1step': float(r['p1step']),
                    'col': r['key'] in _E().COLFX})
    return out

def _layersLive():
    return [[r['key'], int(r['on'] in ('1', 'True', 'true')), round(float(r['amt']), 3), round(float(r['p1']), 3)] for r in _E().layers()]

def _audioDev():
    a = op('/project1/AUDIO')
    if a is None: return None
    d = [o for o in a.findChildren(type=audiodeviceinCHOP)]
    return d[0] if d else None

def audioInputs():
    """Sound inputs Windows offers (laptop mic, line-in, USB sound card...) for the AUDIO tab."""
    d = _audioDev()
    if d is None: return {'v': [], 'cur': ''}
    try: return {'v': [{'n': n, 'l': l} for n, l in zip(d.par.device.menuNames, d.par.device.menuLabels)][:12], 'cur': d.par.device.eval()}
    except Exception: return {'v': [], 'cur': ''}

def state():
    C = _C()
    return {'t': 'state', 'pars': _pars(), 'presets': _presets(), 'presetmov': _presetsMoving(), 'presetdata': _presetData(), 'layers': _layers(), 'looks': _E().lookNames(),
            'queue': {'v': _E().qMsg()['v'], 'pos': _E().qMsg()['pos']}, 'lcols': {k: v for k, v in _E().LCOL.items()},
            'tfx': _E().tLive(), 'tcol': {t: dict(v) for t, v in _E().TCOL.items()},
            'bank': _E().bankList(), 'b': _E().S.get('bank', 0), 'mons': _E().projMonitors(), 'quick': _E().quickAll(), 'store': _E().storeInfo(), 'local': localLink(),
            'models': [dict({'name': n, 'label': l, 'anim': n.startswith('anim_')}, **({'loop': _E().animLoop(_E().animInfo(n))} if n.startswith('anim_') else {}))
                       for n, l in zip(C.par.Model.menuNames, C.par.Model.menuLabels)],
            'audioin': audioInputs(),
            'sliders': [dict(zip(('p', 'label', 'min', 'max', 'step', 'group'), s)) for s in SLIDERS]}

def _send(dat, client, obj):
    try: dat.webSocketSendText(client, json.dumps(obj))
    except Exception: CLIENTS.discard(client)

RELAY = {'host': 'broker.hivemq.com', 'tcp': 1883, 'wss': 'wss://broker.hivemq.com:8884/mqtt',
         'page': 'https://gryva.github.io/moai-vj/'}

def relayKey():
    C = _C()
    k = C.par.Remotekey.eval() if hasattr(C.par, 'Remotekey') else ''
    if not k:
        import secrets
        k = secrets.token_hex(6)
        try: C.par.Remotekey = k
        except Exception: pass
    return k

def relayBase(): return 'moaivj/' + relayKey()

def relayLink(): return RELAY['page'] + '#k=' + relayKey()

def _mqs():
    out = []
    for n in ('remote_mqtt', 'remote_mqtt2', 'remote_mqtt3'):
        m = op('/project1/' + n)
        if m is not None and m.isConnected: out.append(m)
    return out

def _mq():
    l = _mqs()
    return l[0] if l else None

def _publish(obj, retain=False, active_only=False):
    ms = _mqs()
    if active_only:                                   # live meters: only relays a phone used in the last 30 s
        now = time.perf_counter()
        ms = [m for m in ms if now - SEEN.get(m.name, -1e9) < 30]
    if not ms: return
    topic, data = relayBase() + '/' + obj.get('t', 'evt'), json.dumps(obj).encode('utf-8')
    for m in ms:
        try: m.publish(topic, data, qos=0, retain=retain)
        except Exception as e: print('relay publish failed', m.name, e)

def _all(obj, skip=None, retain=False):
    dat = op('/project1/remote_server')
    for c in list(CLIENTS):
        if c != skip: _send(dat, c, obj)
    _publish(obj, retain, active_only=not retain)     # the internet relays only get updates while a phone actually uses them

def _allMedia():
    _all(mediaMsg()); mediaThumbs(_all)

def _thumbsPaced(reply, items, gap=3):
    """Send preset pictures a few frames apart instead of all at once."""
    for idx, (s_, img_) in enumerate(list(items.items())):
        try: run("args[0]({'t': 'thumb', 's': args[1], 'img': args[2]})", reply, int(s_), img_, delayFrames=2 + idx * gap)
        except Exception as e: print('thumb send failed', e)

def _phones():
    now = time.perf_counter()
    return bool(CLIENTS) or any(now - t < 30 for t in SEEN.values())

def broadcastMeters():
    if not _phones(): return                          # nobody listening -> no work, no traffic
    now = time.perf_counter(); f = _E().S['frame']                 # real frames drawn (absTime skips when throttled)
    if now - LIVE['t'] > 0.5:
        LIVE['fps'] = (f - LIVE['f']) / (now - LIVE['t']); LIVE['t'], LIVE['f'] = now, f
    S = _E().S
    msg = {'t': 'm', 'l': round(S['low'], 3), 'm': round(S['mid'], 3), 'h': round(S['high'], 3),
           'k': round(S['kick'], 3), 'v': round(S['level'], 3), 'fps': round(LIVE['fps']), 'b': S.get('bank', 0),
           'db': round(_E().A.get('lvl', -120.0), 1), 'ag': round(_E().A.get('ag', 1.0), 1)}
    LAST['n'] += 1
    full = LAST['n'] % 40 == 0                        # full resync every ~10 s, otherwise only changes
    P, L = _pars(), _layersLive()
    if full or P != LAST['pars']: msg['pars'] = P; LAST['pars'] = P
    if full or L != LAST['L']: msg['L'] = L; LAST['L'] = L
    LT = _E().tLive()
    if full or LT != LAST.get('LT'): msg['LT'] = LT; LAST['LT'] = LT
    dat = op('/project1/remote_server')
    for c in list(CLIENTS): _send(dat, c, msg)
    _publish(msg, active_only=True)

# ---------------------------------------------------------------- HTTP
def onHTTPRequest(dat, request, response):
    uri = request.get('uri', '/').split('?')[0]
    if uri in ('', '/'): uri = '/index.html'
    root_ = os.path.normpath(WEB); path = os.path.normpath(os.path.join(root_, uri.lstrip('/')))
    if os.path.commonpath([root_, path]) != root_ or not os.path.isfile(path):
        response['statusCode'] = 404; response['statusReason'] = 'Not Found'; response['data'] = 'not found'
        return response
    ext = os.path.splitext(path)[1].lower()
    with open(path, 'rb') as f: data = f.read()
    response['statusCode'] = 200; response['statusReason'] = 'OK'
    response['content-type'] = MIME.get(ext, 'application/octet-stream')
    response['cache-control'] = 'no-cache'
    response['data'] = data.decode('utf-8') if ext in ('.html', '.js', '.css', '.json', '.svg', '.webmanifest') else data
    return response

# ---------------------------------------------------------------- WebSocket
def onWebSocketOpen(dat, client, uri):
    CLIENTS.add(client)
    _send(dat, client, state())

def onWebSocketClose(dat, client):
    CLIENTS.discard(client)

def onWebSocketReceiveText(dat, client, data):
    try: msg = json.loads(data)
    except Exception: return
    CLIENTS.add(client)                               # self-healing: a phone that talks is always on the list (survives code reloads)
    r = lambda o: _send(dat, client, o)
    r.local = True                                    # direct link: may be told the computer's addresses (never sent to the public relays)
    handle(msg, r)

# ---------------------------------------------------------------- addresses for the direct link
# The phone keeps every address of this computer (Wi-Fi, USB cable, Bluetooth) and moves to another when one goes quiet.
HOSTS = {'v': [], 't': 0, 'busy': False}

def _hostsRefresh():
    if HOSTS['busy'] or time.time() - HOSTS['t'] < 4: return
    try:                                              # cheap check first: only ask Windows for details when an address changed
        import socket
        ips = sorted({a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)})
    except Exception: ips = None
    if ips is not None and ips == HOSTS.get('ips') and HOSTS['v']:
        HOSTS['t'] = time.time(); return
    HOSTS['ips'] = ips
    HOSTS['busy'] = True
    import threading
    def job():
        try:
            import subprocess
            cmd = ("Get-NetIPAddress -AddressFamily IPv4 | ForEach-Object { $a = Get-NetAdapter -InterfaceIndex $_.InterfaceIndex -ErrorAction SilentlyContinue; "
                   "if ($a -and $a.Status -eq 'Up') { $_.IPAddress + '|' + $a.InterfaceDescription } }")
            r = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True, timeout=15, creationflags=0x08000000)
            out = []
            for ln in r.stdout.splitlines():
                ip, _, d = ln.strip().partition('|'); dl = d.lower()
                if not ip or ip.startswith(('127.', '169.254.')) or any(w in dl for w in ('hyper-v', 'virtual', 'loopback', 'vpn', 'tap-', 'wintun')): continue
                k = 'USB' if ('ndis' in dl or 'usb' in dl) else 'BT' if 'bluetooth' in dl else 'WIFI' if any(w in dl for w in ('wi-fi', 'wireless', 'wlan', '802.11')) else 'LAN'
                out.append({'ip': ip, 'k': k})
            if out: HOSTS['v'] = out
        except Exception: pass
        HOSTS['t'] = time.time(); HOSTS['busy'] = False
    threading.Thread(target=job, daemon=True).start()

def hostsMsg():
    _hostsRefresh()
    return {'t': 'hosts', 'v': HOSTS['v']}

def authToken():
    import hashlib
    pw = _C().par.Remotepass.eval()
    return hashlib.sha256((relayKey() + ':' + pw).encode('utf-8')).hexdigest() if pw else ''

# ---------------------------------------------------------------- security
# Phones never send the password or the token. Each command is {p: <json text>, s: HMAC-SHA256(token, p)}.
# p carries a timestamp; a signature is accepted once, within 2 minutes. Wrong guesses are rate limited.
SIGS = {}                     # signature -> expiry (replay protection)
FAILS = []                    # times of failed logins

def _hm(tok, text):
    import hmac, hashlib
    return hmac.new(tok.encode('utf-8'), text.encode('utf-8'), hashlib.sha256).hexdigest()

def _verify(msg):
    """-> (inner message, ok)"""
    import hmac
    tok = authToken()
    if 'p' not in msg:
        return msg, not tok                                   # unsigned: only allowed when no password is set
    try: inner = json.loads(str(msg['p']))
    except Exception: return {}, False
    if not isinstance(inner, dict): return {}, False
    if not tok: return inner, True
    if not hmac.compare_digest(str(msg.get('s', '')), _hm(tok, str(msg['p']))): return inner, False
    now = time.time()
    if abs(now * 1000.0 - float(inner.get('ts', 0))) > 120000: return inner, False
    for k in [k for k, e in SIGS.items() if e < now]: SIGS.pop(k, None)
    if msg['s'] in SIGS: return inner, False                   # replayed
    SIGS[msg['s']] = now + 130
    return inner, True

def _tooManyFails():
    now = time.time()
    while FAILS and FAILS[0] < now - 60: FAILS.pop(0)
    return len(FAILS) >= 8

def streamKey(minute):
    tok = authToken()
    return bytes.fromhex(_hm(tok, 'stream:%d' % minute)[:32]) if tok else b''

def streamCheck(payload):
    """Camera / drawing frames start with a 16-byte key that changes every minute. -> frame bytes or None"""
    if not isinstance(payload, (bytes, bytearray)): return None
    if not authToken(): return bytes(payload)
    m = int(time.time() // 60); head = bytes(payload[:16])
    import hmac
    for k in (m, m - 1, m + 1, m - 2):
        if hmac.compare_digest(head, streamKey(k)): return bytes(payload[16:])
    return None

SLIDERDEF = {}

def _clean(p, v):
    """Clamp / type-check a value sent by a phone."""
    if not SLIDERDEF: SLIDERDEF.update({s[0]: (s[2], s[3]) for s in SLIDERS})
    if p in SLIDERDEF: lo, hi = SLIDERDEF[p]; return min(hi, max(lo, float(v)))
    if p in TOGGLES: return bool(v)
    if p.endswith('keyhex'):
        import re
        v = str(v).strip().lower()
        if not re.fullmatch(r'#[0-9a-f]{6}', v): raise ValueError('bad colour')
        return v
    if p in TEXTMENUS or p in ('Scene', 'Modelstyle', 'Model'): return str(v)[:120]
    return float(v)

def _ensurePars():
    """Settings added after the project was built: create them if this .toe doesn't have them yet."""
    try:
        C = op('/project1/CONTROLS')
        if not hasattr(C.par, 'Automic'): C.par.Gain.page.appendToggle('Automic', label='Room mic mode')
        if not hasattr(C.par, 'Aplost'): C.par.Autopilot.page.appendToggle('Aplost', label='Remote lost -> autopilot')
        for i in range(1, 7):                          # any background colour can be removed (picked on the remote)
            m = C.par['M%dkeycolor' % i]
            if m is None: continue
            if 'custom' not in m.menuNames:
                m.menuNames = ['auto', 'green', 'blue', 'custom']; m.menuLabels = ['Auto', 'Green', 'Blue', 'Picked']
            if not hasattr(C.par, 'M%dkeyhex' % i):
                pp = m.page.appendStr('M%dkeyhex' % i, label='M%d key colour' % i)[0]; pp.default = '#00ff00'; pp.val = '#00ff00'
            k = op('/project1/mk%d' % i)
            if k is not None and k.par.vec3name.eval() != 'uKC':
                k.par.vec3name = 'uKC'; k.par.vec3valuew = 1
                for j, ax in enumerate('xyz'):
                    k.par['vec3value' + ax].expr = "op('/project1/fx_engine').module.hexc(op('/project1/CONTROLS').par.M%dkeyhex.eval(), %d)" % (i, j)
    except Exception as e: print('ensurePars', e)
_ensurePars()

LOST = {'t': 0.0, 'fired': False}      # last time a signed message came from a remote

def lostCheck():
    """Called once a second by the engine: remote silent for 15 s and the option is on -> autopilot carries the show."""
    C = _C()
    if not LOST['t'] or LOST['fired'] or not getattr(C.par, 'Aplost', None) or not C.par.Aplost.eval(): return
    if time.time() - LOST['t'] > 15 and not C.par.Autopilot.eval():
        C.par.Autopilot = True; LOST['fired'] = True

def handle(msg, reply):
    msg, ok = _verify(msg)
    if ok and msg: LOST['t'] = time.time(); LOST['fired'] = False
    t = msg.get('t'); C, E = _C(), _E()
    cid = str(msg.get('c', ''))[:16]
    if not ok:                                        # locked: nothing happens without the password
        if t == 'hello':
            FAILS.append(time.time())
            if not _tooManyFails():                   # answer only a login attempt, only to that phone, not too often
                reply({'t': 'auth', 'ok': False, 'locked': True, 'to': cid, 'now': time.time() * 1000.0})   # phone clocks can be wrong
        return
    if t == 'setpass':
        C.par.Remotepass = str(msg.get('v', ''))[:64]
        _all({'t': 'auth', 'ok': False, 'locked': bool(C.par.Remotepass.eval()), 'changed': True})
        return
    try:
        if t == 'set' and msg.get('p') in ALLOWED:
            p = msg['p']; v = _clean(p, msg['v'])
            if CAMERA_REMOVED and p in ('Camsrc', 'Clipstate') and v != 'off': return
            if p in ('Model', 'Scene', 'Modelstyle', 'Camsrc', 'Camfit', 'Clipstate') or p in TEXTMENUS and p != 'Textstr':
                par = C.par[p]
                if hasattr(par, 'menuNames') and par.menuNames and v not in par.menuNames: return
            setattr(C.par, p, v)
        elif t == 'layer':
            tg = msg.get('tgt') or 'all'                          # which layer the effect is for (FX tab chips)
            if tg == 'all': E.setLayer(msg['k'], on=msg.get('on'), amt=msg.get('amt'), p1=msg.get('p1'))
            else: E.tSetLayer(tg, msg['k'], on=msg.get('on'), amt=msg.get('amt'), p1=msg.get('p1'))
        elif t == 'fxcopy':                                        # hold a layer in FX = copy, hold another = paste
            if E.fxCopy(str(msg.get('from', '')), str(msg.get('to', ''))):
                _all({'t': 'lcols', 'v': dict(E.LCOL)}); _publish(state(), active_only=True)
        elif t == 'clear':
            tg = msg.get('tgt') or 'all'
            if tg == 'all': E.clearLayers()
            else: E.tClear(tg)
        elif t == 'scene':
            C.par.Scene = msg['v']
        elif t == 'look':
            E.loadLook(int(msg['v']))
        elif t == 'savelook':
            E.saveLook(int(msg['v']), msg.get('name') or None)
            _all({'t': 'looks', 'looks': E.lookNames()})
            _publish(state(), active_only=True)
        elif t == 'model':
            C.par.Model = msg['v']
        elif t == 'preset':
            E.loadPreset(int(msg['v']))
        elif t == 'save':
            E.savePreset(int(msg['v']), msg.get('name') or None)
            _all({'t': 'presets', 'presets': _presets(), 'presetmov': _presetsMoving(), 'presetdata': _presetData()})
            _publish(state(), active_only=True)
        elif t == 'orbit':
            E.navOrbit(float(msg['dx']), float(msg['dy']))
        elif t == 'fling':
            E.navFling(float(msg['vy']), float(msg['vp']))
        elif t == 'pan':
            E.navPan(float(msg['du']), float(msg['dv']))
        elif t == 'zoom':
            E.navZoom(float(msg['f']))
        elif t == 'center':
            C.par.Pan = 0; C.par.Height = 0
        elif t == 'bank':
            E.bankLoad(int(msg['v']), fade=float(msg.get('fade', 0)), cam=True, model=True, text=True)   # a preset is the whole look
            if E.qSync(int(msg['v'])): _all(E.qMsg())
        elif t == 'queue':
            a = msg.get('do')
            if a == 'set' and isinstance(msg.get('v'), list): E.qSet(msg['v'])
            elif a == 'go': E.qGo(int(msg.get('i', 0)), fade=max(0.0, min(10.0, float(msg.get('fade', 0)))))
            _all(E.qMsg())
        elif t == 'animloop':                                    # loop / bounce for the animation on screen
            m = str(C.par.Model.eval())
            if m.startswith('anim_') and E.animSetLoop(m[5:], str(msg.get('v', ''))):
                _all({'t': 'animloop', 'name': m, 'v': E.animLoop(E.animInfo(m))})
        elif t == 'tcol':
            c = E._colClean({'m': msg.get('m', 1), 'a': msg.get('a'), 'b': msg.get('b'), 'ang': msg.get('ang', 0)})
            pre = {2: 'T2', 3: 'T3'}.get(int(msg.get('n') or 1), 'Text')         # which text layer
            C.par[pre + 'cm'] = max(1, c['m']); C.par[pre + 'ca'] = c['a']; C.par[pre + 'cb'] = c['b']; C.par[pre + 'cang'] = c['ang']
        elif t == 'lcol':
            k = str(msg.get('k', '')); tg = msg.get('tgt') or 'all'
            cv = {'m': msg.get('m', 0), 'a': msg.get('a'), 'b': msg.get('b'), 'ang': msg.get('ang', 0)}
            if tg == 'all':
                c = E.colSet(k, cv)
                if c: _all({'t': 'lcols', 'v': {k: c}})
            else:
                c = E.tColSet(tg, k, cv)
                if c: _all({'t': 'tcols', 'tgt': tg, 'v': {k: c}})
        elif t == 'swap':                                          # linked layers: one goes off, the other comes on
            E.layerSwap(str(msg.get('a', '')), str(msg.get('b', '')))
        elif t == 'quick':                                         # pinned controls for LIVE
            ok = E.quickEdit(msg.get('do'), 'all' if msg.get('scope') == 'all' else 'preset', msg.get('item') or {}, msg.get('slot'), int(msg.get('d') or 0))
            _all({'t': 'quick', 'v': E.quickAll()})
            if not ok: reply({'t': 'err', 'msg': 'Could not save the quick control'})
        elif t == 'bankgroupren':                                  # rename a group / take presets out of it
            ok = E.bankRenameGroup(msg.get('old', ''), msg.get('name', ''))
            reply({'t': 'saved', 'n': msg.get('n'), 'ok': bool(ok), 'v': {}})
            _all({'t': 'bank', 'bank': E.bankList()})
        elif t in ('banksave', 'bankclear', 'bankrename', 'bankgroup'):
            n = int(msg['v'])
            if t == 'banksave': ok = E.bankSave(n, msg.get('name') or None)
            elif t == 'bankclear': ok = E.bankClear(n)
            elif t == 'bankgroup': ok = E.bankSetGroup(n, msg.get('name') or '')
            else: ok = E.bankRename(n, msg.get('name') or ('Preset %d' % n))
            _all({'t': 'bank', 'bank': E.bankList()})
            _all(E.qMsg())
            _publish(state(), active_only=True)
            if t not in ('bankrename', 'bankgroup'):
                th = {'t': 'thumb', 's': n, 'img': E.thumbB64(n)}
                _all(th)
            _all({'t': 'saved', 's': n, 'do': t, 'ok': bool(ok), 'n': msg.get('n'), 'v': E.storeInfo()})   # the phone only says "saved" after this
        elif t == 'store':
            a = msg.get('do')
            if a == 'history': reply({'t': 'history', 'v': E.storeHistory(40)})
            elif a in ('undo', 'restore', 'reload'):
                ok = E.storeUndo() if a == 'undo' else E.storeReload() if a == 'reload' else E.storeRestore(str(msg.get('f', '')))
                reply({'t': 'history', 'v': E.storeHistory(40), 'done': a, 'ok': bool(ok)})
            elif a == 'backup': E.storeBackupNow(); reply({'t': 'history', 'v': E.storeHistory(40), 'done': 'backup', 'ok': True})
        elif t == 'clip' and CAMERA_REMOVED:
            return
        elif t == 'clip':
            a = msg.get('do')                                    # ('a' is the login token)
            if a == 'rec': clipRec()
            elif a == 'stop':
                if not clipStop(): reply({'t': 'err', 'msg': 'Clip too short - record a bit longer'})
            elif a == 'play': clipPlay(str(msg.get('id')))
            elif a == 'live': clipLive()
            elif a == 'del': clipDel(str(msg.get('id')))
            _all(clipsMsg()); _publish(state(), active_only=True)
        elif t == 'media':
            a = msg.get('do')
            try: sl = int(msg.get('slot') or 0)
            except Exception: sl = 0
            sl = sl if 1 <= sl <= 6 else 0
            if a == 'add':                                        # + ADD LAYER -> a new empty picture / video layer
                kd = msg.get('kind'); n = mediaFree(kd if kd in ('image', 'draw') else 'video')
                if n and kd == 'draw': DRAWS[n] = {'img': None, 'new': True}
                if n is None: reply({'t': 'err', 'msg': 'All 6 picture / video layers are in use - remove one first'})
                else: reply({'t': 'added', 'slot': n})
            elif a == 'remove' and sl: E.mediaSlotClear(C, sl); E.tClear('m%d' % sl); E.unlink(C, 'm%d' % sl)
            elif a == 'target': MEDIA_UP['slot'] = sl or None
            elif a == 'play' and sl: mediaPlay(str(msg.get('id', '')), fit=True, slot=sl)
            elif a == 'mode' and sl:
                C.par['M%dmode' % sl] = 'object' if msg.get('v') == 'object' else 'flat'
                if C.par['M%dfile' % sl].eval(): mediaPlay(C.par['M%dfile' % sl].eval(), fit=True, slot=sl)
            elif a == 'fit': E.mediaFit(sl or None)
            elif a == 'stop' and sl: mediaStop(sl)
            elif a == 'del': mediaDel(str(msg.get('id', '')))
            _allMedia(); _all(clipsMsg()); _publish(state(), active_only=True)
        elif t == 'vup':
            videoPart(msg)
        elif t == 'vend':
            r_ = videoEnd(msg)
            if r_: reply(r_)
        elif t == 'up':
            r_ = mediaChunk(msg)
            if r_ == 'ok': _allMedia(); _all(clipsMsg()); _publish(state(), active_only=True)
            elif r_: reply({'t': 'err', 'msg': 'Upload failed: ' + r_})
        elif t == 'fxp':
            a = msg.get('do'); i = int(msg.get('i', -1))
            if a == 'save': E.fxSave(str(msg.get('name') or '') or None)
            elif a == 'apply': E.fxApply(i, float(msg.get('fade', 0)))
            elif a == 'del': E.fxDelete(i)
            elif a == 'rename': E.fxRename(i, str(msg.get('name', ''))[:40])
            elif a == 'from': E.fxFromPreset(int(msg.get('slot', 0)), float(msg.get('fade', 0)))
            _all(fxpMsg())
        elif t == 'clean':
            n = E.cleanSlate()
            _all({'t': 'bank', 'bank': E.bankList()}); _publish(state(), active_only=True)
            if n:
                th = {'t': 'thumb', 's': n, 'img': E.thumbB64(n)}; _all(th)
        elif t == 'audioin':                          # pick the sound input (laptop mic, line-in, USB card...)
            d = _audioDev(); v = str(msg.get('v', ''))
            if d is not None and v in d.par.device.menuNames:
                d.par.device = v; d.par.active = True
            reply({'t': 'audioin', 'v': audioInputs()})
            _all({'t': 'audioin', 'v': audioInputs()}, skip=None)
        elif t == 'ping':
            if getattr(reply, 'local', False): reply({'t': 'pong'}); reply(hostsMsg())
        elif t == 'thumbs':                               # the phone is missing some preset pictures: send just those
            need = {str(int(x)) for x in (msg.get('need') or [])[:128]}
            _thumbsPaced(reply, {k: v for k, v in E.thumbAll().items() if str(k) in need})
        elif t == 'qtext':                                # quick-control text: show it, and keep it in the preset on air
            n = int(msg.get('n', 1)); v = str(msg.get('v', ''))[:120]
            if n in (1, 2, 3):
                C.par[E.tpn(n, 'Textstr')] = v; C.par[E.tpn(n, 'Texton')] = True
                if E.S.get('bank'): E.bankSetText(E.S['bank'], n, v)
        elif t == 'hello':
            reply({'t': 'auth', 'ok': True, 'locked': bool(authToken()), 'to': cid})
            reply(state())
            if getattr(reply, 'local', False): reply(hostsMsg())
            if not E.STORE['ok']: reply({'t': 'store', 'v': E.storeInfo(), 'alert': 'PRESETS NOT SAVED: ' + E.STORE['err']})
            _thumbsPaced(reply, E.thumbAll())                 # one small message per picture, spaced out (public relays drop bursts)
            reply(clipsMsg())
            reply(mediaMsg()); mediaThumbs(reply)
            reply(fxpMsg())
    except Exception as e:
        reply({'t': 'err', 'msg': str(e)})

def onWebSocketReceiveBinary(dat, client, data):
    drawFrame(bytes(data))                                       # local Wi-Fi: drawings arrive as binary frames
def onWebSocketReceivePing(dat, client, data): dat.webSocketSendPong(client, data=data)
def onWebSocketReceivePong(dat, client, data): return
LOCAL = {'link': '', 't': -1e9}

def localLink():
    """Backup route: this computer's own address on the Wi-Fi - works with no internet at all."""
    now = time.perf_counter()
    if now - LOCAL['t'] < 30 and LOCAL['link']: return LOCAL['link']
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1)); ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    _hostsRefresh()                                   # a USB cable to the tablet is the most solid route: point the link there
    usb = [h['ip'] for h in HOSTS['v'] if h['k'] == 'USB']
    if usb: ip = usb[0]
    LOCAL['link'] = 'http://%s:%d/#k=%s' % (ip, int(op('/project1/remote_server').par.port.eval()), relayKey()); LOCAL['t'] = now
    try:
        if hasattr(_C().par, 'Locallink') and _C().par.Locallink.eval() != LOCAL['link']: _C().par.Locallink = LOCAL['link']
    except Exception: pass
    return LOCAL['link']

def phoneLink():
    LOCAL['t'] = -1e9; link = localLink()
    try: _C().par.Phonelink = relayLink()
    except Exception: pass
    return link

def onServerStart(dat):
    print('PHONE REMOTE ->', phoneLink())
def onServerStop(dat): CLIENTS.clear()
