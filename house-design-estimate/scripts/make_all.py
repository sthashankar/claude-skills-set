#!/usr/bin/env python3
"""Build every output for a design JSON in one go. Stops with a list of questions if the user has not given the intake details.
usage: make_all.py design.json OUTDIR [--name Base_Name] [--png]
Writes OUTDIR/<Name>_Design.html, <Name>_Estimate.html, <Name>_checks.md, <Name>_estimate_summary.json
and with --png one 2D PNG per level (needs node + playwright).
"""
import sys, os, json, subprocess, tempfile
from hdlib import load, require_intake, IntakeError
import build_design as BD, build_estimate as BE, check_design as CK
from plan2d import svg_level

HERE = os.path.dirname(os.path.abspath(__file__))


def main(a):
    d = load(a[1]); require_intake(d); out = a[2]; os.makedirs(out, exist_ok=True)
    name = a[a.index('--name') + 1] if '--name' in a else ''.join(c if c.isalnum() else '_' for c in d['project']['name']).strip('_')[:40]
    epage, summ = BE.build(load(a[1]))
    open(os.path.join(out, f'{name}_Estimate.html'), 'w').write(epage)
    json.dump(summ, open(os.path.join(out, f'{name}_estimate_summary.json'), 'w'), indent=1)
    dpage, fs = BD.build(load(a[1]), summ)
    open(os.path.join(out, f'{name}_Design.html'), 'w').write(dpage)
    open(os.path.join(out, f'{name}_checks.md'), 'w').write(CK.to_md(fs))
    print(f"design + estimate written to {out}: {summ['total_txt']} · {CK.summary(fs)}" + (' · SAMPLE RATES, not local prices' if summ['sample_rates'] else ''))
    if '--png' in a:
        dd = load(a[1])
        for lv in dd['levels']:
            t = tempfile.NamedTemporaryFile('w', suffix='.svg', delete=False); t.write(svg_level(dd, lv)); t.close()
            subprocess.run(['node', os.path.join(HERE, 'render.js'), t.name, os.path.join(out, f"{name}_{lv['id']}.png"),
                            '--w', '520', '--h', str(int(520 * (dd['building']['d'] + 180) / (dd['building']['w'] + 140))), '--wait', '200', '--dpr', '2'],
                           check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    try: main(sys.argv)
    except IntakeError as e: sys.exit(str(e))
