#!/usr/bin/env python3
"""Change-impact report: what a design change touches, what it breaks, what it fixes, and the knock-on
improvements it opens up (e.g. a stack moved next to a bathroom -> the shower can move beside it).

usage: impact.py old.json new.json [--md report.md] [--json report.json] [--all]
  --all   search knock-on moves for every wet fixture, not only those near the change
"""
import sys, json, copy
from hdlib import *
import check_design as CK

NEAR = 120          # inches: neighbourhood around a change (10 ft)
WETMOVE = {'wc', 'shower', 'tub', 'basin', 'vanity', 'wm', 'sink'}


def index(d):
    ix = {}
    for lv in d['levels']:
        for kind in ('rooms', 'doors', 'windows', 'fixtures', 'stairs'):
            for e in lv[kind]:
                ix[(kind, e['id'])] = (lv['id'], e)
        for p in lv['points']:
            ix[('points', lv['id'] + ':' + p['t'] + ':' + p.get('n', ''))] = (lv['id'], p)
    for s in d['stacks']:
        ix[('stacks', s['id'])] = ('*', s)
    for i, c in enumerate(d['structure']['columns']):
        ix[('columns', f"{c[0]},{c[1]}")] = ('*', {'x': c[0], 'y': c[1]})
    for lv in d['levels']:
        ix[('levels', lv['id'])] = (lv['id'], {k: lv[k] for k in ('h', 'ffl', 'name')})
    ix[('structure', 'params')] = ('*', {k: v for k, v in d['structure'].items() if k != 'columns'})
    return ix


def pos(e):
    if 'r' in e: return centre(e['r'])
    if 'x' in e: return (e['x'], e['y'])
    if 'at' in e: m = (e['a'] + e['b']) / 2; return (m, e['at']) if e['o'] == 'h' else (e['at'], m)
    return None


def strip(e):
    return {k: v for k, v in e.items() if not k.startswith('_')}


def diff(old, new):
    A, B = index(old), index(new); ch = []
    for k in sorted(set(A) | set(B), key=str):
        if k not in A: ch.append(dict(kind=k[0], id=k[1], lv=B[k][0], what='added', new=strip(B[k][1]), p=pos(B[k][1])))
        elif k not in B: ch.append(dict(kind=k[0], id=k[1], lv=A[k][0], what='removed', old=strip(A[k][1]), p=pos(A[k][1])))
        else:
            a, b = strip(A[k][1]), strip(B[k][1])
            if a != b:
                keys = sorted(x for x in set(a) | set(b) if a.get(x) != b.get(x))
                ch.append(dict(kind=k[0], id=k[1], lv=B[k][0], what='changed', fields=keys,
                               old={x: a.get(x) for x in keys}, new={x: b.get(x) for x in keys}, p=pos(b), p0=pos(a)))
    return ch


def fkey(f):
    return (f['code'], f['lv'], tuple(sorted(f['ids'])))


def check_diff(fo, fn):
    o = {fkey(f): f for f in fo if f['sev'] in ('fail', 'warn')}
    n = {fkey(f): f for f in fn if f['sev'] in ('fail', 'warn')}
    return [n[k] for k in n if k not in o], [o[k] for k in o if k not in n]


def stacks_on(d, L):
    return [s for s in d['stacks'] if L in s.get('levels', [L])]


def run_to(d, L, f_rect):
    st = stacks_on(d, L)
    if L == d['levels'][0]['id']:
        st = st + [dict(id=g.get('id', 'gully'), x=g['x'], y=g['y']) for g in d['services'].get('gullies', [])]
    if not st: return None, None
    c = centre(f_rect); s = min(st, key=lambda s: abs(c[0] - s['x']) + abs(c[1] - s['y']))
    return (abs(c[0] - s['x']) + abs(c[1] - s['y'])) * 0.0254, s['id']


def valid_spot(d, lv, r, f, rect):
    x, y, w, dd = rect; rx, ry, rw, rd = r['r']
    if x < rx - 0.1 or y < ry - 0.1 or x + w > rx + rw + 0.1 or y + dd > ry + rd + 0.1: return False
    for g in lv['fixtures']:
        if g is f or g['t'] in CK.HIGH: continue
        if overlap(rect, g['r'], 0.5): return False
    for s in stacks_on(d, lv['id']):
        bw, bd = s.get('box', [12, 12])
        if overlap(rect, [s['x'] - bw / 2, s['y'] - bd / 2, bw, bd], 0.3): return False
    for o in lv['doors']:
        rr = opening_rect(o, d, lv)
        if not rr: continue
        L_ = abs(o['b'] - o['a']); a = min(o['a'], o['b'])
        zone = [a, rr[1] - 36, L_, rr[3] + 72] if o['o'] == 'h' else [rr[0] - 36, a, rr[2] + 72, L_]
        if overlap(rect, zone, 0.5): return False
    fz = CK.front_zone(dict(f, r=rect), r, 24)
    if fz:
        for g in lv['fixtures']:
            if g is f or g['t'] in CK.HIGH: continue
            if overlap(fz, g['r'], 1): return False
    return True


def spots(r, f, step=3):
    """Candidate rects for fixture f against each wall of room r."""
    rx, ry, rw, rd = r['r']; w, dd = f['r'][2], f['r'][3]; out = []
    long_, short_ = max(w, dd), min(w, dd)
    for side in 'nsew':
        # back against this wall: depth = short side perpendicular (wc: depth is its long side)
        depth = long_ if f['t'] == 'wc' else short_
        along = short_ if f['t'] == 'wc' else long_
        if side in 'ns':
            fw, fd = along, depth; yy = ry if side == 's' else ry + rd - fd
            t = rx
            while t + fw <= rx + rw + 0.01:
                out.append([t, yy, fw, fd]); t += step
        else:
            fw, fd = depth, along; xx = rx if side == 'w' else rx + rw - fw
            t = ry
            while t + fd <= ry + rd + 0.01:
                out.append([xx, t, fw, fd]); t += step
    return out


def opportunities(d, focus=None, min_gain=0.5):
    """Knock-on moves: wet fixtures that could sit much closer to a stack (and swaps inside a room)."""
    res = []
    for lv in d['levels']:
        walls_for(d, lv)
        for f in lv['fixtures']:
            if f['t'] not in WETMOVE: continue
            r = room_at(lv, centre(f['r']))
            if not r: continue
            if focus is not None and not any(dist(centre(f['r']), p) <= NEAR * 1.6 for (L, p) in focus if L in (lv['id'], '*')):
                continue
            cur, sid = run_to(d, lv['id'], f['r'])
            if cur is None: continue
            best = None
            for c in spots(r, f):
                if not valid_spot(d, lv, r, f, c): continue
                run, s2 = run_to(d, lv['id'], c)
                if best is None or run < best[0]: best = (run, c, s2)
            if best and cur - best[0] >= min_gain and best[0] <= cur * 0.7:
                res.append(dict(lv=lv['id'], id=f['id'], t=f['t'], room=r['n'], frm=f['r'], to=[round(v, 1) for v in best[1]],
                                run_old=round(cur, 2), run_new=round(best[0], 2), stack=best[2],
                                msg=f"{lv['name']}: move {f['t']} {f['id']} in {r['n']} to x {ftin(best[1][0])}, y {ftin(best[1][1])} "
                                    f"(beside stack {best[2]}): pipe run {cur:.1f} m → {best[0]:.1f} m"))
        # swaps of two wet fixtures in the same room
        fx = [f for f in lv['fixtures'] if f['t'] in WETMOVE]
        for i, a in enumerate(fx):
            for b in fx[i + 1:]:
                ra, rb = room_at(lv, centre(a['r'])), room_at(lv, centre(b['r']))
                if not ra or ra is not rb: continue
                if focus is not None and not any(dist(centre(a['r']), p) <= NEAR * 1.6 for (L, p) in focus if L in (lv['id'], '*')): continue
                ca, cb = centre(a['r']), centre(b['r'])
                na = [cb[0] - a['r'][2] / 2, cb[1] - a['r'][3] / 2, a['r'][2], a['r'][3]]
                nb = [ca[0] - b['r'][2] / 2, ca[1] - b['r'][3] / 2, b['r'][2], b['r'][3]]
                # snap to the nearest wall of the room
                def snap(rc):
                    rx, ry, rw, rd = ra['r']; x, y, w, h = rc
                    dx = [(abs(x - rx), rx), (abs(x + w - rx - rw), rx + rw - w)]; dy = [(abs(y - ry), ry), (abs(y + h - ry - rd), ry + rd - h)]
                    m = min(dx + dy)
                    if m in dx: return [m[1], y, w, h]
                    return [x, m[1], w, h]
                na, nb = snap(na), snap(nb)
                tmp_a, tmp_b = a['r'], b['r']; a['r'], b['r'] = na, nb
                ok = valid_spot(d, lv, ra, a, na) and valid_spot(d, lv, ra, b, nb)
                a['r'], b['r'] = tmp_a, tmp_b
                if not ok: continue
                old = run_to(d, lv['id'], a['r'])[0] + run_to(d, lv['id'], b['r'])[0]
                new = run_to(d, lv['id'], na)[0] + run_to(d, lv['id'], nb)[0]
                w_old = run_to(d, lv['id'], a['r'])[0] if a['t'] == 'wc' else run_to(d, lv['id'], b['r'])[0] if b['t'] == 'wc' else 0
                if old - new >= min_gain:
                    res.append(dict(lv=lv['id'], id=a['id'] + '<->' + b['id'], t='swap', room=ra['n'], run_old=round(old, 2), run_new=round(new, 2),
                                    msg=f"{lv['name']}: swap {a['t']} and {b['t']} in {ra['n']}: total pipe run {old:.1f} m → {new:.1f} m"))
    return res


def neighbourhood(new, changes):
    """Everything within NEAR of a change, on the same level and directly above/below."""
    lids = [l['id'] for l in new['levels']]; out = []
    for c in changes:
        if not c.get('p') or c['kind'] in ('levels', 'structure'): continue
        L = c['lv']; i = lids.index(L) if L in lids else None
        lvls = new['levels'] if L == '*' else [new['levels'][j] for j in (i - 1, i, i + 1) if 0 <= j < len(lids)]
        for p in [c['p']] + ([c['p0']] if c.get('p0') and c['p0'] != c['p'] else []):
            for lv in lvls:
                for r in lv['rooms']:
                    if inside(p, [r['r'][0] - NEAR / 2, r['r'][1] - NEAR / 2, r['r'][2] + NEAR, r['r'][3] + NEAR]):
                        out.append((lv['id'], 'room', r['id'], r['n']))
                for f in lv['fixtures']:
                    if dist(centre(f['r']), p) <= NEAR: out.append((lv['id'], 'fixture', f['id'], f['t']))
                for o in lv['doors'] + lv['windows']:
                    if dist(pos(o), p) <= NEAR: out.append((lv['id'], 'opening', o['id'], o['type']))
                for pt in lv['points']:
                    if dist((pt['x'], pt['y']), p) <= NEAR: out.append((lv['id'], 'electrical', pt['t'], pt.get('n', '')))
            for col in new['structure']['columns']:
                if dist(col[:2], p) <= 36: out.append(('*', 'column', f"{col[0]},{col[1]}", 'within 3 ft: check beam/column penetration'))
    seen = set(); res = []
    for x in out:
        if x not in seen: seen.add(x); res.append(x)
    return res


SYSTEMS = [
    ('Plumbing', 'drain runs and falls to each stack, sunken slab depth, vents, cleanouts, hot water length from geyser/solar, rainwater pipes in the same box'),
    ('Exhaust', 'duct route from each wet room / kitchen, outlet ≥ 1.5 m from openable windows and boundary, cowl above parapet'),
    ('Electrical', 'switch and socket positions after the move, bathroom zones, DB/riser path, light points over new furniture'),
    ('Structure', 'columns and beams under/over the change, slab openings, beam penetrations for pipes, cantilevers, soft storey'),
    ('Light and air', 'window to floor ratios, cross-ventilation path, sun and glare at the new position'),
    ('Vastu', 'zone of every room or fixture that moved, main door pada, stair turn, toilets off NE/centre, nothing over the puja'),
    ('Furniture and use', 'clear space in front of fixtures, door swings, walk paths ≥ 900 mm, bed/wardrobe/TV walls'),
    ('Acoustics and smell', 'stacks and WCs away from bedroom/living walls, lagging, pipe box access'),
    ('Floors above and below', 'what sits directly over and under the change'),
    ('Estimate', 're-run the estimate and quote the delta'),
]


def report(old, new, all_=False):
    o, n = load_obj(old), load_obj(new)
    fo, fn = CK.run(o), CK.run(n)
    ch = diff(o, n)
    added, resolved = check_diff(fo, fn)
    focus = None if all_ else [(c['lv'], c['p']) for c in ch if c.get('p')] + [(c['lv'], c['p0']) for c in ch if c.get('p0')]
    opp = opportunities(n, focus)
    # drain-run changes on fixtures that did not move themselves
    runs = []
    for lv in n['levels']:
        lo = next((l for l in o['levels'] if l['id'] == lv['id']), None)
        if not lo: continue
        for f in lv['fixtures']:
            g = next((x for x in lo['fixtures'] if x['id'] == f['id']), None)
            if g and f.get('_drain') and g.get('_drain') and abs(f['_drain']['run_m'] - g['_drain']['run_m']) >= 0.3:
                runs.append(f"{lv['name']}: {f['t']} {f['id']} pipe run {g['_drain']['run_m']} m → {f['_drain']['run_m']} m (to {f['_drain']['stack']})")
    lights = []
    for lv in n['levels']:
        lo = next((l for l in o['levels'] if l['id'] == lv['id']), None)
        for r in lv['rooms']:
            q = next((x for x in lo['rooms'] if x['id'] == r['id']), None) if lo else None
            if q and q.get('_light') and r.get('_light') and abs(q['_light']['glaze_pct'] - r['_light']['glaze_pct']) >= 1:
                lights.append(f"{lv['name']} {r['n']}: glazing {q['_light']['glaze_pct']}% → {r['_light']['glaze_pct']}%, openable {q['_light']['open_pct']}% → {r['_light']['open_pct']}%")
    nb = neighbourhood(n, ch)
    cost = None
    try:
        import build_estimate as BE
        _, so = BE.build(load_obj(old)); _, sn = BE.build(load_obj(new))
        cost = BE.compare(so, sn)
    except Exception as e:
        cost = f"(estimate not compared: {e})"
    return dict(changes=ch, new_issues=added, resolved=resolved, opportunities=opp, drain_changes=runs, light_changes=lights,
                neighbourhood=nb, cost=cost)


def load_obj(x):
    return normalise(copy.deepcopy(x)) if isinstance(x, dict) else load(x)


def to_md(R):
    L = ['# Change impact report', '', '## What changed']
    for c in R['changes']:
        if c['what'] == 'changed':
            L.append(f"- {c['kind']} `{c['id']}` ({c['lv']}): " + '; '.join(f"{k}: {c['old'][k]} → {c['new'][k]}" for k in c['fields']))
        else:
            L.append(f"- {c['kind']} `{c['id']}` ({c['lv']}) {c['what']}")
    L += ['', '## New problems (fix or accept before applying)'] + ([f"- **{f['sev']}** [{f['cat']}] {f['msg']} _({f['ref']})_" for f in R['new_issues']] or ['- none'])
    L += ['', '## Problems this change solves'] + ([f"- [{f['cat']}] {f['msg']}" for f in R['resolved']] or ['- none'])
    L += ['', '## Knock-on improvements now possible (offer these to the user)']
    groups = {}
    for o in R['opportunities']:
        groups.setdefault((o['lv'], o['room']), []).append(o)
    if not groups: L.append('- none found by the search; still look around by eye')
    for k, os_ in groups.items():
        os_.sort(key=lambda o: o['run_new'] - o['run_old'])
        L.append(f"- {os_[0]['msg']}")
        for o in os_[1:]: L.append(f"  - or: {o['msg'].split(': ', 1)[1]}")
    L += ['', '## Pipe runs that changed'] + (['- ' + x for x in R['drain_changes']] or ['- none'])
    L += ['', '## Daylight and air that changed'] + (['- ' + x for x in R['light_changes']] or ['- none'])
    L += ['', '## Things within 10 ft of the change (same floor, above and below)']
    L += [f"- {a}: {b} {c} {d}" for a, b, c, d in R['neighbourhood']] or ['- none']
    L += ['', '## Cost', '```', R['cost'] or '', '```', '', '## Re-check by eye (the script cannot see everything)']
    L += [f"- **{a}**: {b}" for a, b in SYSTEMS]
    return '\n'.join(L)


if __name__ == '__main__':
    a = sys.argv
    R = report(a[1], a[2], '--all' in a)
    md = to_md(R)
    if '--md' in a: open(a[a.index('--md') + 1], 'w').write(md)
    if '--json' in a: json.dump(R, open(a[a.index('--json') + 1], 'w'), indent=1, default=str)
    print(md)
