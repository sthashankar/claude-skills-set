#!/usr/bin/env python3
"""Apply an APPROVED change: back up, swap in the proposed JSON, log it, rebuild everything, print the cost delta.
Only run after the user has said yes to the preview.
usage: apply_change.py design.json proposed.json OUTDIR --tag short-tag --change "what changed" [--impacts "knock-ons handled"]
Backups go to OUTDIR/backups/<file>_pre-<tag>.<ext> (design JSON, design HTML, estimate HTML, summary).
"""
import sys, os, json, shutil, datetime
from hdlib import load, save, require_intake, IntakeError
import impact as IM
import build_estimate as BE

HERE = os.path.dirname(os.path.abspath(__file__))


def main(a):
    cur, prop, out = a[1], a[2], a[3]
    opt = lambda k, dflt='': a[a.index(k) + 1] if k in a else dflt
    pd = load(prop); require_intake(pd); BE.build(pd)        # stop before anything is swapped in
    tag = opt('--tag') or datetime.datetime.now().strftime('%Y%m%d%H%M')
    bdir = os.path.join(out, 'backups'); os.makedirs(bdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(cur))[0]
    shutil.copy2(cur, os.path.join(bdir, f'{base}_pre-{tag}.json'))
    for f in os.listdir(out):
        if f.endswith(('_Design.html', '_Estimate.html', '_estimate_summary.json')):
            s, e = os.path.splitext(f); shutil.copy2(os.path.join(out, f), os.path.join(bdir, f'{s}_pre-{tag}{e}'))
    R = IM.report(cur, prop)
    d = json.load(open(prop))
    d.setdefault('log', []).append(dict(date=datetime.date.today().isoformat(), tag=tag, change=opt('--change'),
                                        impacts=opt('--impacts') or '; '.join(f['msg'] for f in R['resolved'])[:300]))
    with open(cur, 'w') as f: json.dump(d, f, indent=1, ensure_ascii=False)
    import make_all
    make_all.main(['make_all.py', cur, out] + (['--name', opt('--name')] if '--name' in a else []))
    print('backups in', bdir)
    print(R['cost'])
    if R['new_issues']:
        print('STILL OPEN after apply:'); [print('  -', f['sev'], f['msg']) for f in R['new_issues']]


if __name__ == '__main__':
    try: main(sys.argv)
    except IntakeError as e: sys.exit(str(e))
