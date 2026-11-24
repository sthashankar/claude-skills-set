#!/usr/bin/env python3
"""Rule checks for a design JSON. usage: check_design.py design.json [--json out.json] [--md out.md]

Every finding: {sev: fail|warn|info|ok, cat, code, msg, ref, lv, ids}.
Categories: clash, size, light, struct, mep, safety, vastu, climate.
Thresholds are concept-stage screens, not a substitute for the engineer's design.
"""
import sys, json, math
import paths as PATHS
from hdlib import *

IN_M = 0.0254
HAB = {'living', 'bed', 'master', 'family', 'study', 'dining', 'sitting', 'drawing'}
HIGH = {'geyser', 'ac', 'mirror', 'solar', 'skylight', 'rug', 'tv'}
INSET_OK = {('counter', 'sink'), ('counter', 'hob'), ('counter', 'dw'), ('counter', 'bar_sink'), ('vanity', 'basin'),
            ('counter', 'wm'), ('shelf', 'tv'), ('counter', 'counter')}
OPENABLE = {'W': 1.0, 'W1': 0.4, 'W1-F': 0.0, 'W1-S': 0.5, 'vent': 1.0, 'fixed': 0.0, 'slide': 0.5, 'louvre': 0.8}
OUTDOOR = {'deck', 'terrace', 'court', 'void', 'roof', 'yard'}


def F(out, sev, cat, code, msg, ref='', lv=None, ids=()):
    out.append(dict(sev=sev, cat=cat, code=code, msg=msg, ref=ref, lv=lv, ids=list(ids)))


ROT = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']


def true_dir(d, lab):
    """Plan direction label -> true direction, snapping project.north_deg to the nearest 45 degrees."""
    if lab == 'C': return lab
    k = round(d['project'].get('north_deg', 0) / 45) % 8
    return ROT[(ROT.index(lab) + k) % 8]


def zone9(d, p):
    W, D = d['building']['w'], d['building']['d']
    cx = min(2, max(0, int(p[0] // (W / 3)))); cy = min(2, max(0, int(p[1] // (D / 3))))
    return true_dir(d, [['SW', 'S', 'SE'], ['W', 'C', 'E'], ['NW', 'N', 'NE']][cy][cx])


def touching_side(f, r, tol=2.0):
    """Which room wall(s) a fixture rect sits against."""
    x, y, w, dd = f['r']; rx, ry, rw, rd = r['r']; s = []
    if abs(x - rx) <= tol: s.append('w')
    if abs(x + w - (rx + rw)) <= tol: s.append('e')
    if abs(y - ry) <= tol: s.append('s')
    if abs(y + dd - (ry + rd)) <= tol: s.append('n')
    return s


def front_zone(f, r, depth):
    x, y, w, dd = f['r']; s = touching_side(f, r)
    if not s: return None
    back = s[0] if len(s) == 1 else (s[0] if f['t'] != 'wc' else s[0])
    # choose the wall along the fixture's long back edge
    if len(s) > 1:
        cand = [k for k in s if (k in 'ns' and w >= dd) or (k in 'ew' and dd > w)]
        back = cand[0] if cand else s[0]
    return {'s': [x, y + dd, w, depth], 'n': [x, y - depth, w, depth],
            'w': [x + w, y, depth, dd], 'e': [x - depth, y, depth, dd]}[back]


def other_side(d, lv, o, r):
    """Room (or 'outside') on the far side of an opening that sits on room r's edge."""
    a, b = min(o['a'], o['b']), max(o['a'], o['b']); mid = (a + b) / 2
    x, y, w, dd = r['r']; t = 14
    if o['o'] == 'h':
        p = (mid, o['at'] + (t if abs(o['at'] - (y + dd)) < abs(o['at'] - y) else -t))
    else:
        p = (o['at'] + (t if abs(o['at'] - (x + w)) < abs(o['at'] - x) else -t), mid)
    W, D = d['building']['w'], d['building']['d']
    if not (0 <= p[0] <= W and 0 <= p[1] <= D):
        return 'outside', facade(d, o)
    q = room_at(lv, p)
    return q, None


def glazing(o):
    return (abs(o['b'] - o['a']) * max(0, o['head'] - o['sill'])) / 144.0


def under(v, m):
    return m is not None and v < m


def over(v, m):
    return m is not None and v > m


def rng(r):
    return f"{r[0]}–{r[1]}"


def mn(v, unit):
    return 'not given' if v is None else f'{v} {unit}'


def outside(v, rng):
    return rng is not None and not rng[0] <= v <= rng[1]


def run(d):
    C = codes(d); out = _run(d)
    if C.get('refs') != 'builtin':        # references in this file belong to the sample codes: swap in the project's own
        refs = C.get('refs') or {}
        for f in out:
            if f['cat'] != 'vastu': f['ref'] = refs.get(f['code'], '')
    if C.get('_unset'):
        F(out, 'warn', 'safety', 'codes-missing', "Building codes not given: these checks use the sample numbers. Ask the user which codes apply")
    nulls = [k for k in sample_limits() if C.get('limits', {}).get(k) is None]
    if nulls:
        F(out, 'warn', 'safety', 'codes-unset', f"NOT CHECKED, no limit given in {C.get('name') or 'the codes file'}: {', '.join(nulls)}")
    return out


def sample_limits():
    return data_file({}, 'codes', 'sample')['limits']


def _run(d):
    out = []; X = lambda k: lim(d, k)
    W, D = d['building']['w'], d['building']['d']; S = d['structure']
    boundary = set(d['project'].get('boundary', []))
    lvmap = {l['id']: l for l in d['levels']}
    # ---------- a light switch inside every room, at the door you enter by (latch side, 1.1 m) ----------
    import copy, mep3d
    try:
        M3 = mep3d.extras3d(copy.deepcopy(d)); ent = {(e['lv'], e['room']) for e in M3['entry']}
        lit = {(l_['lv'], l_['room']) for l_ in M3['lights']}
        for lv_ in d['levels']:
            for r_ in lv_['rooms']:
                key = (lv_['id'], r_['id'])
                if key in lit and key not in ent and r_['k'] not in OUTDOOR and r_['k'] != 'stair':
                    F(out, 'fail', 'mep', 'switch-entry', f"{r_['n']}: no light switch at the entry door. Put a switch for the light and fan inside the room, on the latch side of the door, 1.1 m up",
                      'AS/NZS 3000 + LHD: switch reachable on entry, 900–1100 mm', lv_['id'], [r_['id']])
    except Exception as e_:
        F(out, 'warn', 'mep', 'switch-entry', f"Entry-switch check could not run: {e_}")
    for li, lv in enumerate(d['levels']):
        L = lv['id']; walls = walls_for(d, lv); lv['_walls'] = walls
        rooms = lv['rooms']
        # ---------- walkways: furniture must not cut off a door or stair ----------
        if not lv.get('roof_level'):
            nm = {o['id']: f"door {o['id']}" for o in lv['doors']}; nm.update({r['id']: r['n'] for r in rooms})
            for sev, tid, who in PATHS.check(d, lv, li):
                by = ', '.join(who) if who else 'furniture'
                F(out, sev, 'clash', 'path-blocked' if sev == 'fail' else 'path-narrow',
                  (f"No way through to {nm.get(tid, tid)}: blocked by {by}" if sev == 'fail' else
                   f"Way to {nm.get(tid, tid)} is under 750 mm clear because of {by}"),
                  'walkway 750 mm min (900–1000 mm main routes, LHD)', L, [tid] + who)
        # ---------- geometry / clashes ----------
        for i, a in enumerate(rooms):
            x, y, w, dd = a['r']
            if x < -0.1 or y < -0.1 or x + w > W + 0.1 or y + dd > D + 0.1:
                if a['k'] not in OUTDOOR:
                    F(out, 'fail', 'clash', 'room-outside', f"{a['n']} extends outside the building outline", lv=L, ids=[a['id']])
            for b in rooms[i + 1:]:
                if overlap(a['r'], b['r'], 0.6):
                    F(out, 'fail', 'clash', 'room-overlap', f"{a['n']} overlaps {b['n']}", lv=L, ids=[a['id'], b['id']])
        # ---------- every wall between two rooms must survive its openings ----------
        cuts = [rr for rr in (opening_rect(o, d, lv) for o in lv['doors'] + lv['windows'] if o.get('type') != 'arch') if rr]
        arch = [rr for rr in (opening_rect(o, d, lv) for o in lv['doors'] if o.get('type') == 'arch') if rr]
        for o in lv['doors'] + lv['windows']:
            rr = opening_rect(o, d, lv)
            if rr and (min(rr[2], rr[3]) > 13.5 or max(rr[2], rr[3]) > abs(o['b'] - o['a']) + 1):
                F(out, 'fail', 'clash', 'opening-cuts-wall', f"Opening {o['id']} cuts a {ftin(rr[2])} × {ftin(rr[3])} hole: it would delete a wall", lv=L, ids=[o['id']])
        _inw = lambda p_, rs: any(r_[0] - .3 <= p_[0] <= r_[0] + r_[2] + .3 and r_[1] - .3 <= p_[1] <= r_[1] + r_[3] + .3 for r_ in rs)
        for a in rooms:
            if a['k'] in KINDS_OPEN: continue
            ax, ay, aw, ad = a['r']
            for b in rooms:
                if b is a or b['k'] in KINDS_OPEN: continue
                bx, by, bw, bd = b['r']
                if 0.5 < by - (ay + ad) <= 13.5 and not {'n'} & set(a['open'] + a['rail']) and not {'s'} & set(b['open'] + b['rail']):      # b north of a
                    lo, hi, cy = max(ax, bx), min(ax + aw, bx + bw), (ay + ad + by) / 2
                    pts = [(lo + t, cy) for t in range(2, int(hi - lo) - 1, 3)]
                elif 0.5 < bx - (ax + aw) <= 13.5 and not {'e'} & set(a['open'] + a['rail']) and not {'w'} & set(b['open'] + b['rail']):    # b east of a
                    lo, hi, cx = max(ay, by), min(ay + ad, by + bd), (ax + aw + bx) / 2
                    pts = [(cx, lo + t) for t in range(2, int(hi - lo) - 1, 3)]
                else: continue
                wl = lv['_walls']; gone = [p_ for p_ in pts if not _inw(p_, wl) and not _inw(p_, cuts) and not _inw(p_, arch)]
                if len(gone) >= 3:
                    F(out, 'fail', 'clash', 'wall-missing', f"No wall between {a['n']} and {b['n']} for {ftin(len(gone) * 3)}: add the wall or an opening",
                      lv=L, ids=[a['id'], b['id']])
        for o in lv['doors'] + lv['windows']:
            if not opening_rect(o, d, lv):
                F(out, 'fail', 'clash', 'opening-no-wall', f"Opening {o['id']} ({ftin(abs(o['b']-o['a']))} wide) does not sit on any wall",
                  lv=L, ids=[o['id']])
        fx = lv['fixtures']
        for f in fx:
            c = centre(f['r']); r = room_at(lv, c)
            if not r:
                F(out, 'fail', 'clash', 'fix-no-room', f"{f['t']} {f['id']} is not inside any room", lv=L, ids=[f['id']]); continue
            f['_room'] = r['id']
            rx, ry, rw, rd = r['r']; x, y, w, dd = f['r']
            if f['t'] not in ('solar', 'skylight', 'ac') and (x < rx - 1 or y < ry - 1 or x + w > rx + rw + 1 or y + dd > ry + rd + 1):
                F(out, 'warn', 'clash', 'fix-outside', f"{f['t']} {f['id']} sticks out of {r['n']}", lv=L, ids=[f['id'], r['id']])
            for s_ in d['stacks']:
                if L in s_.get('levels', [L]):
                    bw, bd = s_.get('box', [12, 12])
                    if overlap(f['r'], [s_['x'] - bw / 2, s_['y'] - bd / 2, bw, bd], 0.5) and f['t'] not in HIGH:
                        F(out, 'fail', 'clash', 'fix-stack', f"{f['t']} {f['id']} clashes with pipe box {s_['id']}", lv=L, ids=[f['id'], s_['id']])
            for col in S['columns']:
                cw, cd = S['col']
                if overlap(f['r'], [col[0] - cw / 2, col[1] - cd / 2, cw, cd], 0.5) and f['t'] not in HIGH:
                    F(out, 'info', 'clash', 'fix-column', f"{f['t']} {f['id']} meets the column projection at ({ftin(col[0])}, {ftin(col[1])}): notch, shorten or shift it", lv=L, ids=[f['id']])
        for i, a in enumerate(fx):
            for b in fx[i + 1:]:
                if a['t'] in HIGH or b['t'] in HIGH: continue
                if (a['t'], b['t']) in INSET_OK or (b['t'], a['t']) in INSET_OK: continue
                if overlap(a['r'], b['r'], 0.6):
                    F(out, 'fail', 'clash', 'fix-overlap', f"{a['t']} {a['id']} overlaps {b['t']} {b['id']}", lv=L, ids=[a['id'], b['id']])
        # clear zones in front of fixtures
        need = {'wc': 24, 'basin': 24, 'vanity': 24, 'shower': 24, 'tub': 24, 'wardrobe': 30, 'fridge': 36, 'hob': 36,
                'sink': 36, 'wm': 30, 'dw': 30, 'counter': 36}
        for f in fx:
            if f['t'] not in need or '_room' not in f: continue
            r = next(r for r in rooms if r['id'] == f['_room'])
            z = front_zone(f, r, need[f['t']])
            if not z: continue
            for g in fx:
                if g is f or g['t'] in HIGH or g['t'] == 'rug': continue
                if (f['t'], g['t']) in INSET_OK or (g['t'], f['t']) in INSET_OK: continue
                if f['t'] in ('counter', 'sink', 'hob', 'dw') and g['t'] in ('counter', 'sink', 'hob', 'dw', 'fridge'): continue
                if overlap(z, g['r'], 1.0):
                    F(out, 'warn', 'clash', 'clear-zone', f"{g['t']} {g['id']} sits in the {need[f['t']]}\" clear space in front of {f['t']} {f['id']}",
                      'AS 1428 / LHD circulation, practical minimum', L, [f['id'], g['id']])
        # door swings
        for o in lv['doors']:
            if o['type'] in ('arch', 'opening', 'slide'): continue
            rr = opening_rect(o, d, lv)
            if not rr: continue
            Lw = abs(o['b'] - o['a']); a_ = min(o['a'], o['b'])
            if o['o'] == 'h':
                face = rr[1] + rr[3] if o['dir'] > 0 else rr[1] - Lw
                sw = [a_, face, Lw, Lw]
            else:
                face = rr[0] + rr[2] if o['dir'] > 0 else rr[0] - Lw
                sw = [face, a_, Lw, Lw]
            sw_in = [sw[0] + 1, sw[1] + 1, sw[2] - 2, sw[3] - 2]
            into = room_at(lv, centre(sw))
            for g in fx:
                if g['t'] in HIGH or g['t'] == 'rug': continue
                if overlap(sw_in, g['r'], 1.5):
                    F(out, 'warn', 'clash', 'door-swing', f"Door {o['id']} swings into {g['t']} {g['id']}", lv=L, ids=[o['id'], g['id']])
            for o2 in lv['doors']:
                if o2 is o or o2['type'] in ('arch', 'opening', 'slide'): continue
                r2 = opening_rect(o2, d, lv)
                if r2 and overlap(sw_in, r2, 0.5):
                    F(out, 'warn', 'clash', 'door-door', f"Doors {o['id']} and {o2['id']} clash when open", lv=L, ids=[o['id'], o2['id']])
            if into and into['k'] == 'wet' and o['type'] in ('bath', 'door'):
                F(out, 'info', 'safety', 'wet-door-in', f"Door {o['id']} swings into {into['n']}; prefer outward-opening, sliding or lift-off hinges for WCs",
                  'Livable Housing Design / NCC H4D5 (outward or removable)', L, [o['id']])
            if o['type'] == 'main' and under(Lw * 25.4, X('entry_door_mm')):
                F(out, 'warn', 'safety', 'entry-width', f"Main door {ftin(Lw)}: under {X('entry_door_mm')} mm wide for step-free access", 'LHD', L, [o['id']])
        # leftover space nobody owns (usually a transcription slip); cells next to decks/terraces are open air
        if not lv.get('roof_level'):
            g = 3; cells = set()
            outd = [r['r'] for r in rooms if r['k'] in OUTDOOR]
            colr = [[cc[0] - S['col'][0] / 2, cc[1] - S['col'][1] / 2, S['col'][0], S['col'][1]] for cc in S['columns']]
            for iy in range(int(D // g)):
                for ix in range(int(W // g)):
                    p = (ix * g + g / 2, iy * g + g / 2)
                    if any(inside(p, r['r'], 0) for r in rooms) or any(inside(p, w_, 0) for w_ in walls) or any(inside(p, c_, 0) for c_ in colr):
                        continue
                    if any(inside(p, o_, 10) for o_ in outd): continue
                    cells.add((ix, iy))
            seen = set()
            for c0 in cells:
                if c0 in seen: continue
                comp = [c0]; seen.add(c0); k_ = 0
                while k_ < len(comp):
                    cx_, cy_ = comp[k_]; k_ += 1
                    for nb in ((cx_ + 1, cy_), (cx_ - 1, cy_), (cx_, cy_ + 1), (cx_, cy_ - 1)):
                        if nb in cells and nb not in seen: seen.add(nb); comp.append(nb)
                a_ = len(comp) * g * g / 144
                if a_ > 4:
                    xs_ = [q[0] * g for q in comp]; ys_ = [q[1] * g for q in comp]
                    F(out, 'warn', 'clash', 'leftover', f"{a_:.0f} sq ft of floor belongs to no room and no wall (x {ftin(min(xs_))}–{ftin(max(xs_)+g)}, y {ftin(min(ys_))}–{ftin(max(ys_)+g)}): check room edges", '', L)
        # ---------- stairs ----------
        for st in lv['stairs']:
            parts = [fl['r'] for fl in st['flights']] + [ld['r'] for ld in st.get('landings', [])]
            for i_, p_ in enumerate(parts):
                for q_ in parts[i_ + 1:]:
                    if overlap(p_, q_, 0.6):
                        F(out, 'fail', 'clash', 'stair-geom', f"Stair {st['id']}: a flight overlaps another flight or landing", '', L, [st['id']])
            R_ = st['rise'] * 25.4; G_ = st['going'] * 25.4; tot = sum(fl['n'] for fl in st['flights'])
            if outside(R_, X('stair_rise_mm')): F(out, 'fail', 'safety', 'stair-rise', f"Stair rise {R_:.0f} mm ({rng(X('stair_rise_mm'))})", 'NCC H5D2 / NBC 206', L, [st['id']])
            if outside(G_, X('stair_going_mm')): F(out, 'fail', 'safety', 'stair-going', f"Stair going {G_:.0f} mm ({rng(X('stair_going_mm'))})", 'NCC H5D2', L, [st['id']])
            if outside(2 * R_ + G_, X('stair_2rg_mm')): F(out, 'fail', 'safety', 'stair-2rg', f"2R+G {2*R_+G_:.0f} mm ({rng(X('stair_2rg_mm'))})", 'NCC H5D2', L, [st['id']])
            if any(over(fl['n'], X('stair_max_risers')) for fl in st['flights']): F(out, 'fail', 'safety', 'stair-18', f"A flight has more than {X('stair_max_risers')} risers", 'NCC H5D2', L, [st['id']])
            if under(st.get('width', 36) * 25.4, X('stair_width_mm')): F(out, 'warn', 'safety', 'stair-width', f"Stair clear width {ftin(st.get('width', 36))} < {X('stair_width_mm')} mm", 'NBC 206 practice', L, [st['id']])
            if li + 1 < len(d['levels']) and abs(tot * st['rise'] - lv['h']) > 0.6:
                F(out, 'fail', 'safety', 'stair-total', f"Risers {tot} × {st['rise']:.2f}\" = {tot*st['rise']:.1f}\" but floor-to-floor is {lv['h']}\"", '', L, [st['id']])
            if st.get('turn') == 'anticlockwise' and d['vastu'].get('enabled'):
                F(out, 'info', 'vastu', 'stair-turn', "Stair turns anticlockwise going up; Vastu prefers clockwise", 'Vastu', L, [st['id']])
            F(out, 'ok' if X('stair_rise_mm') and X('stair_going_mm') else 'info', 'safety', 'stair-ok', f"Stair {tot}R × {R_:.0f} mm, going {G_:.0f} mm, 2R+G {2*R_+G_:.0f} mm", 'NCC H5D2', L, [st['id']])
        # ---------- room sizes ----------
        for r in rooms:
            if r['k'] in OUTDOOR: continue
            A = room_areas(r); m2 = A['fin'] * 0.0929; wmin = min(A['fw'], A['fd']) * IN_M
            ch = ceiling_h(d, lv, r) * IN_M
            u = r['use']
            if u in HAB:
                if under(m2, X('hab_area_m2')): F(out, 'warn', 'size', 'hab-area', f"{r['n']} {m2:.1f} m² < {X('hab_area_m2')} m² habitable minimum", 'NBC 206 / municipal bylaws', L, [r['id']])
                if under(wmin, X('hab_width_m')): F(out, 'warn', 'size', 'hab-width', f"{r['n']} narrowest side {wmin:.2f} m < {X('hab_width_m')} m", 'NBC 206', L, [r['id']])
                if under(ch, X('hab_height_m')): F(out, 'warn', 'size', 'hab-height', f"{r['n']} ceiling {ch:.2f} m < {X('hab_height_m')} m", 'NBC 206 / NCC H4D4', L, [r['id']])
            if u == 'kitchen' and (under(m2, X('kitchen_area_m2')) or under(wmin, X('kitchen_width_m'))):
                F(out, 'warn', 'size', 'kit-size', f"Kitchen {m2:.1f} m², width {wmin:.2f} m (min {mn(X('kitchen_area_m2'), 'm²')}, {mn(X('kitchen_width_m'), 'm')})", 'NBC 206', L, [r['id']])
            if u in ('bath', 'ensuite') and (under(m2, X('bath_area_m2')) or under(wmin, X('bath_width_m'))):
                F(out, 'warn', 'size', 'bath-size', f"{r['n']} {m2:.1f} m², width {wmin:.2f} m (min {mn(X('bath_area_m2'), 'm²')}, {mn(X('bath_width_m'), 'm')})", 'NBC 206', L, [r['id']])
            if u == 'wc' and (under(m2, X('wc_area_m2')) or under(wmin, X('wc_width_m'))):
                F(out, 'warn', 'size', 'wc-size', f"{r['n']} {m2:.1f} m² (min {mn(X('wc_area_m2'), 'm²')}, {mn(X('wc_width_m'), 'm')})", 'NBC 206', L, [r['id']])
        # ---------- light and air ----------
        for r in rooms:
            if r['k'] in OUTDOOR or r['use'] in ('stair', 'hall', 'store'): continue
            A = room_areas(r)['fin']; gl = 0; op = 0; faces = set()
            for o in openings_in(lv, r):
                q, fac = other_side(d, lv, o, r)
                if q == 'outside':
                    if fac and fac in boundary and X('boundary_openings_banned'):
                        F(out, 'fail', 'light', 'boundary-opening', f"Opening {o['id']} is on the {fac} boundary wall (not allowed; fire separation)",
                          'Municipal bylaws / NBC 107', L, [o['id']])
                    if o in lv['windows'] or o.get('type') in ('slide',) or o.get('glass'):
                        g = glazing(o) if o in lv['windows'] else abs(o['b'] - o['a']) * o['h'] / 144
                        gl += g; op += g * OPENABLE.get(o['type'], 0.5); faces.add(fac or 'out')
                elif q and q['k'] in OUTDOOR:
                    if o in lv['windows'] or o.get('type') == 'slide' or o.get('glass'):
                        g = glazing(o) if o in lv['windows'] else abs(o['b'] - o['a']) * o['h'] / 144
                        gl += g; op += g * OPENABLE.get(o['type'], 0.5); faces.add('well' if q['k'] in ('court', 'void') else q['k'])
            ex = next((e for e in d['services'].get('exhaust', []) if e['room'] == r['id']), None)
            pct = 100 * gl / A if A else 0; vp = 100 * op / A if A else 0
            r['_light'] = dict(glaze_pct=round(pct, 1), open_pct=round(vp, 1), faces=sorted(faces), exhaust=bool(ex))
            if r['use'] in HAB or r['use'] in ('kitchen', 'puja'):
                if under(pct, X('light_pct')): F(out, 'warn', 'light', 'light-10', f"{r['n']}: glazing {pct:.0f}% of floor (need ≥ {X('light_pct')}%)", 'NCC H4D6 / NBC 206', L, [r['id']])
                if under(vp, X('vent_pct')): F(out, 'warn', 'light', 'vent-5', f"{r['n']}: openable {vp:.1f}% of floor (need ≥ {X('vent_pct')}%)", 'NCC H4D7', L, [r['id']])
                if len(faces) >= 2: F(out, 'ok', 'light', 'cross', f"{r['n']}: cross-ventilation ({', '.join(sorted(faces))})", '', L, [r['id']])
                elif r['use'] in HAB: F(out, 'info', 'light', 'single', f"{r['n']}: single-sided air ({', '.join(faces) or 'none'}); keep doors/fanlights open or add a high vent", '', L, [r['id']])
                deep_ = max(room_areas(r)['fw'], room_areas(r)['fd'])
                if faces and deep_ > 2.5 * 96 and len(faces) < 2:
                    F(out, 'info', 'light', 'depth', f"{r['n']} is {ftin(deep_)} deep from one window wall: back half dim (rule of thumb 2.5 × head height)", '', L, [r['id']])
            if r['k'] == 'wet' or r['use'] in ('kitchen', 'laundry'):
                if not ex and (under(vp, X('vent_pct')) or (X('vent_pct') is None and not vp)):
                    ls = X('exhaust_ls'); need_ls = f" ({ls[0]} L/s bath, {ls[1]} L/s kitchen)" if ls else ''
                    F(out, 'fail', 'mep', 'wet-vent', f"{r['n']}: not enough openable window and no exhaust fan listed{need_ls}", 'NCC H4D7 / AS 1668.2', L, [r['id']])
                if ex and ex.get('via') and ex['via'] not in ('hood', 'wall') and not any(s_['id'] == ex['via'] for s_ in d['stacks']):
                    F(out, 'fail', 'mep', 'exh-route', f"{r['n']}: exhaust routed via {ex['via']} which does not exist", '', L, [r['id']])
        # ---------- services ----------
        stacks = [s_ for s_ in d['stacks'] if L in s_.get('levels', [L])]
        sunk = {r['id']: r.get('sunken', 0) for r in rooms}
        for f in fx:
            if f['t'] not in WET_FIX: continue
            c = centre(f['r'])
            targets = [dict(id=s_['id'], x=s_['x'], y=s_['y']) for s_ in stacks]
            if li == 0:      # ground floor: may drain straight out to a gully / inspection chamber
                targets += [dict(id=g.get('id', 'gully'), x=g['x'], y=g['y']) for g in d['services'].get('gullies', [])]
                te = S['wall_ext']
                for fac, pt in {'S': (c[0], 0), 'N': (c[0], D), 'W': (0, c[1]), 'E': (W, c[1])}.items():
                    if fac not in boundary:
                        targets.append(dict(id=f'new gully ({fac} wall)', x=pt[0], y=pt[1]))
            if not targets:
                F(out, 'fail', 'mep', 'no-stack', f"{f['t']} {f['id']} has no stack on this level", 'AS/NZS 3500.2', L, [f['id']]); continue
            best = min(targets, key=lambda s_: abs(c[0] - s_['x']) + abs(c[1] - s_['y']))
            run_in = abs(c[0] - best['x']) + abs(c[1] - best['y'])          # orthogonal pipe run
            run_m = run_in * IN_M
            grade = 1 / (X('drain_grade_wc') or 60) if f['t'] == 'wc' else 1 / (X('drain_grade') or 40)
            dia = 100 if f['t'] == 'wc' else 50
            depth = run_m * 1000 * grade + dia + 30
            f['_drain'] = dict(stack=best['id'], run_m=round(run_m, 2), depth_mm=round(depth))
            mxr = X('drain_run_wc_m') if f['t'] == 'wc' else X('drain_run_m')
            if over(run_m, X('drain_run_max_m')):
                F(out, 'fail', 'mep', 'drain-long', f"{f['t']} {f['id']}: {run_m:.1f} m to stack {best['id']}", 'AS/NZS 3500.2 (vent the branch)', L, [f['id'], best['id']])
            elif over(run_m, mxr):
                F(out, 'warn', 'mep', 'drain-long', f"{f['t']} {f['id']}: {run_m:.1f} m pipe run to {best['id']}, needs {depth:.0f} mm under the floor", 'AS/NZS 3500.2', L, [f['id'], best['id']])
            rid = f.get('_room'); sk = sunk.get(rid, 0) * 25.4
            if li > 0 and sk and depth > sk:
                F(out, 'warn', 'mep', 'sunken', f"{f['t']} {f['id']} needs {depth:.0f} mm drop but the sunken slab is {sk:.0f} mm", '', L, [f['id']])
        for g in [f for f in fx if f['t'] == 'geyser']:
            for sh in [f for f in fx if f['t'] in ('shower', 'tub')]:
                z_ = (X('wet_zone_mm') or 0) / 25.4
                gx = [g['r'][0] - z_, g['r'][1] - z_, g['r'][2] + 2 * z_, g['r'][3] + 2 * z_]
                if z_ and overlap(gx, sh['r'], 0):
                    F(out, 'warn', 'mep', 'geyser-zone', f"Geyser {g['id']} is within {X('wet_zone_mm')} mm of {sh['t']} {sh['id']}", 'AS/NZS 3000 cl 6.2 zones', L, [g['id'], sh['id']])
        for h in [f for f in fx if f['t'] == 'hob']:
            for o in lv['windows']:
                rr = opening_rect(o, d, lv); z_ = (X('hob_window_mm') or 0) / 25.4
                if z_ and rr and overlap([h['r'][0] - z_, h['r'][1] - z_, h['r'][2] + 2 * z_, h['r'][3] + 2 * z_], rr, 0):
                    F(out, 'warn', 'mep', 'hob-window', f"Hob {h['id']} within {X('hob_window_mm')} mm of window {o['id']} (curtains, draughts on the flame)", 'AS/NZS 5601.1', L, [h['id'], o['id']])
            for fr in [f for f in fx if f['t'] == 'fridge']:
                if dist(centre(h['r']), centre(fr['r'])) < 36:
                    F(out, 'info', 'mep', 'hob-fridge', "Hob right beside the fridge: keep a 300 mm counter between", '', L, [h['id'], fr['id']])
        pts = {p['t']: p for p in lv['points']}
        for p in lv['points']:
            r = room_at(lv, (p['x'], p['y']))
            if p['t'] in ('DB', 'MS', 'INV', 'BAT', 'NET') and r and r['k'] == 'wet' and r['use'] != 'laundry':
                F(out, 'fail', 'mep', 'db-wet', f"{p['t']} ({p.get('n','')}) is inside {r['n']}: keep switchgear out of bathrooms", 'AS/NZS 3000 cl 6.2', L)
        if 'BAT' in pts:
            b = pts['BAT']; r = room_at(lv, (b['x'], b['y']))
            if r and r['use'] in HAB | {'hall'}:
                F(out, 'fail', 'mep', 'bat-room', f"Battery in {r['n']}: not in habitable rooms or escape paths", 'AS/NZS 5139', L)
            if 'DB' in pts and under(dist((b['x'], b['y']), (pts['DB']['x'], pts['DB']['y'])) * 25.4, X('battery_db_mm')):
                F(out, 'warn', 'mep', 'bat-db', f"Battery within {X('battery_db_mm')} mm of the DB", 'AS/NZS 5139', L)
        if any(r['use'] in ('bed', 'master') for r in rooms):
            F(out, 'info', 'safety', 'smoke', "Interconnected mains-powered smoke alarms in the hall outside the bedrooms on this level", 'AS 3786 / NCC H3D6', L)
        # wet over habitable
        if li > 0:
            below = d['levels'][li - 1]
            for r in rooms:
                if r['k'] != 'wet': continue
                for q in below['rooms']:
                    if overlap(r['r'], q['r'], 3) and q['k'] != 'wet' and q['use'] in HAB | {'kitchen', 'puja'}:
                        sev = 'fail' if q['use'] == 'puja' else 'warn'
                        F(out, sev, 'mep', 'wet-over', f"{r['n']} sits over {below['name']} {q['n']}: sunken slab + waterproof membrane; pipes in a boxed bulkhead",
                          'AS 3740, Vastu', L, [r['id'], q['id']])
        # balustrades
        if over(lv['ffl'] * 25.4, X('balustrade_fall_mm')):
            for r in rooms:
                if r['k'] not in OUTDOOR or r['k'] == 'roof' and not r['rail']: pass
                if r['k'] not in OUTDOOR: continue
                x, y, w, dd = r['r']
                for side in 'snwe':
                    if side in r['rail']: continue
                    ok = False
                    for t in (3, 8, 14):
                        p = {'s': (x + w / 2, y - t), 'n': (x + w / 2, y + dd + t), 'w': (x - t, y + dd / 2), 'e': (x + w + t, y + dd / 2)}[side]
                        q = room_at(lv, p)
                        opp = {'s': 'n', 'n': 's', 'e': 'w', 'w': 'e'}[side]
                        if any(inside(p, wr, 0.5) for wr in walls) or (q is not None and q is not r and (q['k'] != 'void' or r['k'] == 'void' or opp in q['rail'])):
                            ok = True; break
                    if not ok:
                        F(out, 'fail', 'safety', 'balustrade', f"{r['n']} {side} edge: fall > {X('balustrade_fall_mm') / 1000:.1f} m with no balustrade ({mn(X('balustrade_h_mm'), 'mm')} high, gaps < {mn(X('balustrade_gap_mm'), 'mm')})", 'NCC H5D3', L, [r['id']])
        # window restrictors
        if over(lv['ffl'] * 25.4, X('restrictor_ffl_mm')):
            for r in rooms:
                if r['use'] not in ('bed', 'master'): continue
                for o in openings_in(lv, r):
                    if o in lv['windows'] and OPENABLE.get(o['type'], 0) > 0 and under(o['sill'] * 25.4, X('restrictor_sill_mm')):
                        F(out, 'info', 'safety', 'restrictor', f"{r['n']} window {o['id']} sill {ftin(o['sill'])}: fit a {mn(X('restrictor_gap_mm'), 'mm')} opening limiter", 'NCC H5D4 (11.3.7)', L, [o['id']])
    # ---------- structure ----------
    cols = S['columns']; cw, cd = S['col']
    if cols and under(min(cw, cd) * 25.4, X('col_min_mm')): F(out, 'fail', 'struct', 'col-size', f"Columns {cw}×{cd}\" < {X('col_min_mm')} mm minimum", 'NBC 205 MRT')
    nl = len([l for l in d['levels'] if not l.get('roof_level') and any(r['k'] not in OUTDOOR and r['use'] != 'stair' for r in l['rooms'])])
    if cols and nl >= 3 and under(min(cw, cd) * 25.4, X('col_3storey_mm')):
        F(out, 'info', 'struct', 'col-g2', f"3 storeys: columns of about {X('col_3storey_mm')} mm are usual; confirm with the structural design", 'NBC 205:2024 / NBC 105')
    xs = sorted({round(c[0], 1) for c in cols}); ys = sorted({round(c[1], 1) for c in cols})
    spans = []
    for y in ys:
        row = sorted(cc[0] for cc in cols if abs(cc[1] - y) < 1)
        spans += [(b - a, f"x {ftin(a)}–{ftin(b)} at y {ftin(y)}") for a, b in zip(row, row[1:])]
    for x in xs:
        row = sorted(cc[1] for cc in cols if abs(cc[0] - x) < 1)
        spans += [(b - a, f"y {ftin(a)}–{ftin(b)} at x {ftin(x)}") for a, b in zip(row, row[1:])]
    mx = max([s_[0] for s_ in spans] or [0])
    grp = {}
    for sp, where in spans:
        if over(sp * IN_M, X('span_m')): grp.setdefault(round(sp * IN_M, 2), []).append(where)
    for m, wh in sorted(grp.items(), reverse=True):
        txt = wh[0] if len(wh) == 1 else f"{len(wh)} beams, e.g. {wh[0]}"
        if over(m, X('span_max_m')): F(out, 'fail', 'struct', 'span', f"Beam span {m:.2f} m ({txt}) > {X('span_max_m')} m: needs a designed deep beam or an extra column", 'NBC 205 MRT ≤ 4.5 m')
        else: F(out, 'warn', 'struct', 'span', f"Beam span {m:.2f} m ({txt}) > {X('span_m')} m rule-of-thumb limit: engineer to design (or add a column line)", 'NBC 205 MRT')
    if spans:
        bd = S['beam'][1] * IN_M; n_ = X('beam_span_ratio'); need = mx * IN_M / n_ if n_ else 0
        if bd < need: F(out, 'warn', 'struct', 'beam-depth', f"Beam depth {bd*1000:.0f} mm < span/{n_} = {need*1000:.0f} mm for the longest span", 'IS 456 / NBC 205')
        sl = S['slab'] * 25.4
        if under(sl, X('slab_mm')): F(out, 'warn', 'struct', 'slab', f"Slab {sl:.0f} mm < {X('slab_mm')} mm", 'NBC 205 MRT')
    lenB, widB = max(W, D), min(W, D)
    if X('plan_aspect') is not None and lenB / widB >= X('plan_aspect'): F(out, 'warn', 'struct', 'aspect', f"Plan aspect ratio {lenB/widB:.1f} ≥ {X('plan_aspect')}: add a seismic joint or extra cross frames; check torsion", 'NBC 105 §5 regularity, NBC 205')
    if cols:
        ex = max(c[0] for c in cols) - min(c[0] for c in cols); ey = max(c[1] for c in cols) - min(c[1] for c in cols)
        ov = [(min(c[1] for c in cols) - 0) * IN_M, (D - max(c[1] for c in cols)) * IN_M, (min(c[0] for c in cols)) * IN_M, (W - max(c[0] for c in cols)) * IN_M]
        if over(max(ov), X('cantilever_m')): F(out, 'warn', 'struct', 'cantilever', f"Cantilever {max(ov):.2f} m beyond the outer column line (> {X('cantilever_m')} m)", 'NBC 205 MRT')
    wl = []
    for lv in d['levels']:
        if lv.get('roof_level'): continue
        wl.append((lv['name'], sum(max(w[2], w[3]) for w in lv.get('_walls', walls_for(d, lv)))))
    if len(wl) >= 2 and X('soft_storey') is not None and wl[0][1] < X('soft_storey') * wl[1][1]:
        F(out, 'warn', 'struct', 'soft-storey', f"{wl[0][0]} has {wl[0][1]/12:.0f} ft of walls vs {wl[1][1]/12:.0f} ft above: possible soft storey", 'NBC 105 §5.2')
    for lv in d['levels']:
        if lv.get('roof_level'): continue
        walls = lv.get('_walls') or walls_for(d, lv)
        A = sum(w[2] * w[3] for w in walls)
        if not A: continue
        cx = sum((w[0] + w[2] / 2) * w[2] * w[3] for w in walls) / A; cy = sum((w[1] + w[3] / 2) * w[2] * w[3] for w in walls) / A
        exx, eyy = abs(cx - W / 2) / W, abs(cy - D / 2) / D
        if over(max(exx, eyy), X('torsion')):
            F(out, 'warn', 'struct', 'torsion', f"{lv['name']}: wall mass centre is {max(exx,eyy)*100:.0f}% off centre (> {X('torsion')*100:.0f}%): torsion risk; balance infill or add frames", 'NBC 105 torsional irregularity', lv['id'])
        holes = sum(r['r'][2] * r['r'][3] for r in lv['rooms'] if r['k'] in ('void', 'stair')) / (W * D)
        if over(holes, X('diaphragm')): F(out, 'fail', 'struct', 'diaphragm', f"{lv['name']}: openings {holes*100:.0f}% of slab (> {X('diaphragm')*100:.0f}%)", 'NBC 105 diaphragm discontinuity', lv['id'])
    # seismic base shear (indicative)
    sz = seismic(d)
    if str(sz.get('code', '')).startswith('NBC 105') and sz.get('Z'):
        h = sum(l['h'] for l in d['levels'] if not l.get('roof_level')) * IN_M
        T = 1.25 * 0.075 * h ** 0.75
        soil = {'A': (0.1, 1.5, 2.5), 'B': (0.1, 1.5, 2.5), 'C': (0.1, 2.0, 2.5), 'D': (0.5, 3.0, 2.25)}.get(sz.get('soil', 'D'), (0.5, 3.0, 2.25))
        Ta, Tc, al = soil
        Ch = al if Ta <= T <= Tc else (1 + (al - 1) * T / Ta if T < Ta else al * Tc / T)
        C = Ch * sz['Z'] * sz['I']; Cd = C / (sz['R_mu'] * sz['omega_u'])
        floorA = sum((W * D - sum(r['r'][2] * r['r'][3] for r in l['rooms'] if r['k'] in ('void', 'court'))) * IN_M ** 2 for l in d['levels'][1:])
        Wt = floorA * 11.0
        F(out, 'info', 'struct', 'base-shear', f"Indicative ULS base shear: T≈{T:.2f} s, Ch={Ch:.2f}, Z={sz['Z']}, Cd≈{Cd:.3f} → V ≈ {Cd*Wt:.0f} kN for W ≈ {Wt:.0f} kN (11 kN/m² per floor). Engineer to verify.",
          'NBC 105:2020 §4–6 (soil ' + sz.get('soil', 'D') + ')')
    else:
        F(out, 'info', 'struct', 'base-shear', f"Seismic load not computed ({sz.get('code') or 'no seismic code given'}): the structural engineer sizes it, with wind and snow, to the local code")
    if boundary:
        F(out, 'info', 'struct', 'boundary-footing', f"Walls on the {', '.join(sorted(boundary))} boundary: eccentric footings with strap beams (or raft); no openings on those walls",
          'NBC 205 / bylaws')
    # ---------- vastu ----------
    if d['vastu'].get('enabled'):
        out += vastu(d)
    # ---------- lessons learned ----------
    import mep3d as _M
    top = d['levels'][-1]; roof_m2 = W * D * 0.00064516
    rws = _M.rw_pipes(d); need = max(2, math.ceil(roof_m2 / X('roof_m2_per_rwp'))) if X('roof_m2_per_rwp') else 0
    if len(rws) < need:
        F(out, 'warn', 'mep', 'rw-pipes', f"{len(rws)} rainwater pipe(s) for {roof_m2:.0f} m² of roof: use at least {need} × 110 mm, hidden in the pipe boxes", 'AS/NZS 3500.3', top['id'])
    else:
        F(out, 'info', 'mep', 'rw-pipes', f"{len(rws)} × 110 mm rainwater pipes hidden in the pipe boxes, roof outlets with leaf guards; add an overflow scupper through the parapet at each low point", 'AS/NZS 3500.3 overflow', top['id'])
    QUIET = {'living': 'warn', 'bed': 'warn', 'master': 'warn', 'family': 'info', 'study': 'info', 'dining': 'info', 'drawing': 'info', 'sitting': 'info'}
    for s_ in d['stacks']:
        bx = s_.get('box', [12, 12]); sr = [s_['x'] - bx[0] / 2 - 6, s_['y'] - bx[1] / 2 - 6, bx[0] + 12, bx[1] + 12]
        for lv in d['levels']:
            if lv['id'] not in s_.get('levels', [l['id'] for l in d['levels']]) or lv.get('roof_level'): continue
            for r in lv['rooms']:
                sev = QUIET.get(r['use'])
                if sev and overlap(sr, r['r'], 0):
                    F(out, sev, 'mep', 'stack-noise', f"Stack {s_['id']} pipe box is on the {r['n']} wall: drain noise. Lag the pipes (acoustic wrap / low-noise PVC) or move the box to the stair or wet side",
                      'AS/NZS 3500.2 + AS 2107 comfort', lv['id'], [s_['id'], r['id']])
    gf_ = d['levels'][0]
    for st in gf_['stairs']:
        fl = st.get('flights', [None])[0]
        if not fl: continue
        i0 = math.ceil((36 + 6) / st['rise'])
        if fl['n'] > i0:
            run = (fl['n'] - i0) * st['going']
            if not any(f['t'] in ('cupboard', 'shelf', 'wardrobe') and overlap(f['r'], fl['r'], 0) for f in gf_['fixtures']):
                F(out, 'info', 'clash', 'under-stair', f"Under the first flight from riser {i0} on ({ftin(run)} long, 3'-0\"+ high): room for fitted cupboards. A bench needs 4'-6\" headroom",
                  '', gf_['id'], [st['id']])
    pts = [(lv, p_) for lv in d['levels'] for p_ in lv['points'] if p_['t'] == 'MS']
    road = (d['project'].get('road') or 'S')[0]
    for lv, p_ in pts:
        face = {'S': p_['y'] <= 12, 'N': p_['y'] >= D - 12, 'W': p_['x'] <= 12, 'E': p_['x'] >= W - 12}[road]
        if lv is not gf_ or not face:
            F(out, 'warn', 'safety', 'meter', "Meter and main switch should be on the ground floor, on the road-side wall or at the gate, for the meter reader and fire service", 'Utility practice / AS/NZS 3000 2.10', lv['id'])

    return out


VPREF = {
    'kitchen': ({'SE'}, {'NW', 'E', 'S'}, {'NE', 'SW', 'C', 'N'}),
    'master': ({'SW'}, {'S', 'W'}, {'NE', 'SE', 'C'}),
    'bed': ({'S', 'W', 'SW', 'NW'}, {'N', 'E'}, {'NE', 'SE', 'C'}),
    'puja': ({'NE'}, {'E', 'N'}, {'S', 'SW', 'SE', 'C'}),
    'wc': ({'NW', 'W'}, {'S', 'SE', 'N'}, {'NE', 'C', 'SW', 'E'}),
    'bath': ({'NW', 'W', 'E'}, {'S', 'SE', 'N'}, {'NE', 'C', 'SW'}),
    'ensuite': ({'NW', 'W', 'E'}, {'S', 'SE', 'N'}, {'NE', 'C', 'SW'}),
    'stair': ({'S', 'W', 'SW'}, {'NW', 'SE'}, {'NE', 'C', 'N', 'E'}),
    'living': ({'N', 'E', 'NE'}, {'NW', 'W', 'S', 'C'}, {'SW'}),
    'dining': ({'W', 'E'}, {'N', 'S', 'C', 'NW'}, set()),
    'store': ({'SW', 'S', 'W'}, {'NW', 'SE'}, {'NE', 'C'}),
    'study': ({'W', 'NE', 'E', 'N'}, {'SW', 'S'}, set()),
    'court': ({'C'}, {'NE', 'N', 'E'}, {'SW'}), 'void': ({'C'}, {'NE', 'N', 'E'}, {'SW'}),
}


def vastu(d):
    out = []
    for lv in d['levels']:
        for r in lv['rooms']:
            u = r['use']
            if u not in VPREF: continue
            z = zone9(d, centre(r['r'])); best, ok, bad = VPREF[u]
            if z in best: F(out, 'ok', 'vastu', 'zone', f"{r['n']} in {z}: ideal", 'Vastu', lv['id'], [r['id']])
            elif z in bad: F(out, 'warn', 'vastu', 'zone', f"{r['n']} in {z}: avoid; ideal {'/'.join(sorted(best))}", 'Vastu', lv['id'], [r['id']])
            else: F(out, 'info', 'vastu', 'zone', f"{r['n']} in {z}: acceptable (ideal {'/'.join(sorted(best))})", 'Vastu', lv['id'], [r['id']])
        for f in lv['fixtures']:
            r = room_at(lv, centre(f['r']))
            if not r: continue
            s = touching_side(f, r)
            if f['t'] == 'bed' and s:
                hd = [k for k in s if (k in 'ew' and f['r'][2] > f['r'][3]) or (k in 'ns' and f['r'][3] >= f['r'][2])]
                if hd:
                    k = hd[0]; good = k in 'se'
                    F(out, 'ok' if good else ('warn' if k == 'n' else 'info'), 'vastu', 'bed-head',
                      f"Bed {f['id']} in {r['n']}: head to the {dict(n='north', s='south', e='east', w='west')[k]}" + ('' if good else ' (prefer south or east)'),
                      'Vastu', lv['id'], [f['id']])
            if f['t'] == 'hob' and s:
                face = {'e': 'east', 'w': 'west', 'n': 'north', 's': 'south'}[s[0]]
                F(out, 'ok' if face == 'east' else 'info', 'vastu', 'cook-face', f"Cook faces {face} at hob {f['id']}" + ('' if face == 'east' else ' (east preferred)'), 'Vastu', lv['id'], [f['id']])
            if f['t'] == 'tank' and lv is d['levels'][-1]:
                z = zone9(d, centre(f['r']))
                F(out, 'ok' if z in ('SW', 'S', 'W') else 'info', 'vastu', 'tank', f"Roof tank in {z}" + ('' if z in ('SW', 'S', 'W') else ' (SW/S/W preferred)'), 'Vastu', lv['id'], [f['id']])
            if f['t'] == 'altar' and s:
                F(out, 'ok' if s[0] in 'en' else 'info', 'vastu', 'altar', f"Altar on the {s[0].upper()} wall: devotee faces {'east' if s[0]=='e' else 'north' if s[0]=='n' else 'west/south'}", 'Vastu', lv['id'], [f['id']])
        for o in lv['doors']:
            if o['type'] != 'main': continue
            W, D = d['building']['w'], d['building']['d']; fac = facade(d, o) or 'S'
            if round(d['project'].get('north_deg', 0) / 90) % 4:
                F(out, 'info', 'vastu', 'rotated', f"Plan north is turned {d['project']['north_deg']}° from true north: pada count uses the plan face; confirm on site with a compass", 'Vastu', lv['id'])
            a, b = min(o['a'], o['b']), max(o['a'], o['b'])
            L_ = W if fac in 'NS' else D; pw = L_ / 9
            good = {'S': (3, 4), 'N': (3, 4, 5), 'E': (3, 4), 'W': (3, 4, 5)}[fac]
            # padas counted from: S side from SE corner westwards, N from NE westwards? use standard: N from NW→NE? keep S/E rules
            # padas: S from the SE corner going west, N from NW going east, E from NE going south, W from SW going north
            pos = {'S': lambda v: (L_ - v) / pw, 'N': lambda v: v / pw, 'E': lambda v: (L_ - v) / pw, 'W': lambda v: v / pw}[fac]
            p0, p1 = sorted((pos(a), pos(b)))
            pads = set(range(int(p0) + 1, int(math.ceil(p1 - 1e-6)) + 1))
            okp = pads <= set(good)
            F(out, 'ok' if okp else 'warn', 'vastu', 'main-door', f"Main door on the {fac} face covers pada {', '.join(map(str, sorted(pads)))} (counted from the {'SE' if fac=='S' else 'NW' if fac=='N' else 'NE' if fac=='E' else 'SW'} corner); good padas {good}",
              'Vastu Purusha mandala (81 padas)', lv['id'], [o['id']])
    # centre
    gf = d['levels'][0]; W, D = d['building']['w'], d['building']['d']
    cz = [W / 3, D / 3, W / 3, D / 3]
    def ov_area(a, b):
        return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    heavy = [r['n'] for r in gf['rooms'] if r['use'] in ('wc', 'bath', 'ensuite', 'stair', 'kitchen') and ov_area(r['r'], cz) > 0.1 * cz[2] * cz[3]]
    if heavy: F(out, 'warn', 'vastu', 'brahma', f"Brahmasthan (centre ninth) holds {', '.join(heavy)}; keep it open/light", 'Vastu', gf['id'])
    for s_ in d['stacks']:
        z = zone9(d, (s_['x'], s_['y']))
        if z == 'NE': F(out, 'warn', 'vastu', 'stack-ne', f"Stack {s_['id']} in the NE", 'Vastu', ids=[s_['id']])
    sep = d['services'].get('septic')
    if sep:
        z = zone9(d, (min(max(sep['x'], 0), W - 1), min(max(sep['y'], 0), D - 1)))
        F(out, 'ok' if z in ('NW', 'W') else 'info', 'vastu', 'septic', f"Septic tank towards {z}" + ('' if z in ('NW', 'W') else ' (NW/W preferred)'), 'Vastu')
    return out


def summary(fs):
    from collections import Counter
    c = Counter(f['sev'] for f in fs)
    return f"{c['fail']} fail, {c['warn']} warn, {c['info']} info, {c['ok']} ok"


def to_md(fs):
    order = {'fail': 0, 'warn': 1, 'info': 2, 'ok': 3}
    lines = [f"# Design checks: {summary(fs)}", ""]
    for f in sorted(fs, key=lambda f: (order[f['sev']], f['cat'])):
        lines.append(f"- **{f['sev'].upper()}** [{f['cat']}] {f['msg']}" + (f" _(ref: {f['ref']})_" if f['ref'] else '') + (f" — {f['lv']}" if f['lv'] else ''))
    return '\n'.join(lines)


if __name__ == '__main__':
    d = load(sys.argv[1]); fs = run(d)
    a = sys.argv
    if '--json' in a: json.dump(fs, open(a[a.index('--json') + 1], 'w'), indent=1, ensure_ascii=False)
    if '--md' in a: open(a[a.index('--md') + 1], 'w').write(to_md(fs))
    print(summary(fs))
    for f in fs:
        if f['sev'] in ('fail', 'warn'): print(f"  {f['sev'].upper():4} [{f['cat']}] {f['lv'] or '-'}: {f['msg']}")
