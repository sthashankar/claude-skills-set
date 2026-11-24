#!/usr/bin/env python3
"""Before/after 2D preview (and optional 3D) of a proposed change, for the user to approve BEFORE applying.
usage: preview.py old.json new.json out.png [--levels gf,ff] [--title "..."] [--note "..."] [--hl id1,id2] [--3d out3d.png]
Changed elements are outlined in orange on both sides. Requires node + playwright (render.js).
"""
import sys, os, json, subprocess, tempfile, html
from hdlib import load
from plan2d import svg_level
import impact as IM

HERE = os.path.dirname(os.path.abspath(__file__))


def main(a):
    old, new, out = load(a[1]), load(a[2]), os.path.abspath(a[3])
    opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt
    ch = IM.diff(old, new)
    hl = {c['id'] for c in ch} | set(filter(None, (opt('--hl') or '').split(',')))
    lvls = (opt('--levels') or '').split(',') if opt('--levels') else sorted({c['lv'] for c in ch if c['lv'] != '*'} or {new['levels'][0]['id']},
                                                                          key=[l['id'] for l in new['levels']].index)
    if any(c['lv'] == '*' for c in ch) and not opt('--levels'):
        lvls = [l['id'] for l in new['levels'] if not l.get('roof_level')]
    cols = []
    for L in lvls:
        lo = next(l for l in old['levels'] if l['id'] == L); ln = next(l for l in new['levels'] if l['id'] == L)
        cols.append(f"<div class=c><h2>Now</h2>{svg_level(old, lo, hl)}</div><div class=c><h2>Proposed</h2>{svg_level(new, ln, hl)}</div>")
    title = html.escape(opt('--title', 'Proposed change'))
    note = html.escape(opt('--note', '; '.join(f"{c['kind']} {c['id']} {c['what']}" for c in ch)[:400]))
    page = (f"<!doctype html><meta charset=utf-8><style>body{{margin:0;background:#F8F9F6;font:15px Arial;color:#1C282D}}"
            f"h1{{font-size:22px;margin:14px 20px 2px}}p{{margin:0 20px 10px;color:#5A686D}}.g{{display:grid;grid-template-columns:repeat({2*len(cols)},1fr);gap:8px;padding:0 12px 12px}}"
            f".c{{background:#fff;border:1px solid #C9D0CA;border-radius:6px}}.c h2{{font-size:16px;margin:8px 12px 0;color:#B4740E}}svg{{width:100%;height:auto;display:block}}</style>"
            f"<h1>{title}</h1><p>{note}. Orange outline = what changes.</p><div class=g>{''.join(cols)}</div>")
    tmp = tempfile.NamedTemporaryFile('w', suffix='.html', delete=False); tmp.write(page); tmp.close()
    w = 520 * 2 * len(cols)
    subprocess.run(['node', os.path.join(HERE, 'render.js'), tmp.name, out, '--w', str(min(w, 2400)), '--h', '1400', '--wait', '300', '--full'], check=True)
    if '--3d' in a:
        import build_design as BD
        page, _ = BD.build(new)
        t2 = tempfile.NamedTemporaryFile('w', suffix='.html', delete=False); t2.write(page); t2.close()
        pts = [c['p'] for c in ch if c.get('p') and (c['lv'] in (lvls[0], '*'))] or [(new['building']['w'] / 2, new['building']['d'] / 2)]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        ev = f"HD.focus({cx:.1f},{cy:.1f},'{lvls[0]}');1"
        subprocess.run(['node', os.path.join(HERE, 'render.js'), t2.name, os.path.abspath(opt('--3d')), '--w', '1200', '--h', '900',
                        '--wait', '2500', '--eval', ev, '--sel', '#view'], check=True)


if __name__ == '__main__':
    main(sys.argv)
