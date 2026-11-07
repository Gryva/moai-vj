import json, subprocess, os, sys
# ---- edit these for your computer
HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(HERE, 'in')                      # unpacked downloads (src / texdir paths are relative to this)
OUTPUT = os.path.join(HERE, 'out')                    # converted models land here, one folder per model
BLENDER_PY = os.path.join(HERE, '..', 'bpyenv', 'Scripts' if os.name == 'nt' else 'bin', 'python')
jobs = json.load(open(os.path.join(HERE, 'jobs.json')))
only = sys.argv[1:]
for j in jobs:
    if only and j['name'] not in only: continue
    a = dict(j); a['src'] = os.path.join(INPUT, j['src'])
    a['texdir'] = os.path.join(INPUT, j.get('texdir', os.path.dirname(j['src'])))
    a['out'] = os.path.join(OUTPUT, j['name'])
    os.makedirs(OUTPUT, exist_ok=True)
    r = subprocess.run([BLENDER_PY, os.path.join(HERE, 'convert.py'), '--', json.dumps(a)], capture_output=True, text=True, timeout=900)
    open(os.path.join(OUTPUT, j['name'] + '.log'), 'w').write(r.stdout + '\n----\n' + r.stderr)
    done = [l for l in r.stdout.splitlines() if l.startswith('[conv]')]
    print('==', j['name'], 'rc', r.returncode); print('\n'.join(done[-6:]))
    if r.returncode or not any('DONE' in l for l in done): print('   ERR:', '\n'.join(r.stderr.strip().splitlines()[-4:]))
