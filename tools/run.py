import json, subprocess, os, sys
jobs = json.load(open('/home/claude/assets/tools/jobs.json'))
only = sys.argv[1:]
for j in jobs:
    if only and j['name'] not in only: continue
    a = dict(j); a['src'] = os.path.join('/home/claude/assets/in', j['src'])
    a['texdir'] = os.path.join('/home/claude/assets/in', j.get('texdir', os.path.dirname(j['src'])))
    a['out'] = os.path.join('/home/claude/assets/out', j['name'])
    r = subprocess.run(['/home/claude/bpyenv/bin/python', '/home/claude/assets/tools/convert.py', '--', json.dumps(a)], capture_output=True, text=True, timeout=900)
    open('/home/claude/assets/logs/%s.log' % j['name'], 'w').write(r.stdout + '\n----\n' + r.stderr)
    done = [l for l in r.stdout.splitlines() if l.startswith('[conv]')]
    print('==', j['name'], 'rc', r.returncode); print('\n'.join(done[-6:]))
    if r.returncode or not any('DONE' in l for l in done): print('   ERR:', '\n'.join(r.stderr.strip().splitlines()[-4:]))
