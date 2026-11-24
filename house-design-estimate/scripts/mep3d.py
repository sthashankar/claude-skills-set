"""3D services, doors and lights for the design page.

extras3d(d) -> dict(boxes=[...], doors=[...], lights=[...], fans=[...])
  boxes: extra 3D boxes with k = 'plumb' (drains, PVC grey), 'cold' / 'hot' (water), 'exh' (ducts), 'wire' (cable runs),
         'elec' (switches, sockets, DB/inverter/battery gear, always shown), 'exhfan' (fan grilles), 'tankx' (UG tank,
         septic, gullies). Layer toggles in the viewer switch them on and off.
  doors: one leaf per hinged door (pivot, closed/open angles) or a pair of glass panels for a slide door.
  lights: ceiling oysters (indoor, count = the estimate's light points) and wall bulkheads (open decks), one room lamp each.
  fans: ceiling fans in habitable rooms and the kitchen (count = the estimate's fan points).
Run after check_design.run(d) so f['_drain'] (stack or gully each wet fixture drains to) is filled in.
"""
import math
from hdlib import (WET_FIX, KINDS_OPEN, opening_rect, room_at, centre, ceiling_h, room_areas, walls_for)

HAB = {'living', 'bed', 'master', 'family', 'study', 'dining', 'sitting', 'drawing'}
SOCKETS = {'living': 4, 'master': 4, 'bed': 3, 'family': 3, 'study': 3, 'dining': 2, 'kitchen': 4, 'laundry': 2, 'hall': 1}
WATER = {'wc': 'c', 'basin': 'ch', 'shower': 'ch', 'tub': 'ch', 'sink': 'ch', 'bar_sink': 'c', 'wm': 'c', 'dw': 'c'}
SKIP_ELEC = {'roof', 'court', 'void'}


def _run(B, p, q, size, m, lv, k, order='xy'):
    """Orthogonal pipe/duct/cable from p=(x,y,z) to q: x leg, then y leg, then z leg (or y first)."""
    (x1, y1, z1), (x2, y2, z2) = p, q; s = size; pts = [(x1, y1, z1)]
    if order == 'xy': pts += [(x2, y1, z1), (x2, y2, z1), (x2, y2, z2)]
    elif order == 'yx': pts += [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2)]
    else: pts += [(x1, y1, z2), (x2, y1, z2), (x2, y2, z2)]          # 'zxy': up/down first
    for (a, b, c), (e, f, g) in zip(pts, pts[1:]):
        if abs(a - e) + abs(b - f) + abs(c - g) < 0.3: continue
        B.append(dict(x=min(a, e) - s / 2, y=min(b, f) - s / 2, z=min(c, g) - s / 2, w=abs(a - e) + s, d=abs(b - f) + s,
                      h=abs(c - g) + s, m=m, lv=lv, k=k))


def _face_side(o, r):
    """+1 when room r lies on the +y (h) / +x (v) side of the opening's wall."""
    cx, cy = centre(r['r'])
    return 1 if ((cy if o['o'] == 'h' else cx) > o['at']) else -1


def _grid(r, n, inset=0.0):
    x, y, w, dd = r['r']; cols = max(1, round(math.sqrt(n * w / max(dd, 1)))); rows = math.ceil(n / cols); out = []
    for i in range(n):
        cx, cy = i % cols, i // cols
        out.append((x + w * (cx + .5) / cols, y + dd * (cy + .5) / rows))
    return out


def extras3d(d):
    S = d['structure']; W, D = d['building']['w'], d['building']['d']
    boundary = set(d['project'].get('boundary', []))
    B, doors, lights, fans = [], [], [], []
    global ENTRY; ENTRY = []
    levels = d['levels']; top = levels[-1]; roof_z = top['ffl'] + top['h']
    stacks = d['stacks']
    for li, lv in enumerate(levels):
        lid, z0, H = lv['id'], lv['ffl'], lv['h']
        lv.setdefault('_walls', walls_for(d, lv))
        rooms = lv['rooms']
        # ---------------- doors ----------------
        for o in lv['doors']:
            if o['type'] in ('arch', 'opening'): continue
            rr = opening_rect(o, d, lv)
            if not rr: continue
            a, b = min(o['a'], o['b']), max(o['a'], o['b'])
            lo, th = (rr[1], rr[3]) if o['o'] == 'h' else (rr[0], rr[2])
            sgn = o.get('dir', 1)
            face = lo + th if sgn > 0 else lo                    # wall face on the swing side
            doors.append(dict(id=o['id'], lv=lid, o=o['o'], a=a, b=b, hg=o.get('hg', 'a'), dir=sgn, type=o['type'],
                              h=min(o.get('h', 84), H - S['slab']), z=z0, face=face, mid=lo + th / 2, th=th,
                              open=o['type'] in ('door', 'bath')))
        if lv.get('roof_level'): continue
        # ---------------- lights, fans, switches, sockets, wiring ----------------
        for r in rooms:
            k, u = r['k'], r['use']
            if k in SKIP_ELEC: continue
            x, y, w, dd = r['r']; fin = room_areas(r)['fin']; ov = r.get('elec', {})
            outdoor = k in KINDS_OPEN
            ch = ceiling_h(d, lv, r)
            covered = li + 1 < len(levels) and room_at(levels[li + 1], centre(r['r'])) is not None
            n_l = ov.get('L', 1 if outdoor else max(1, math.ceil(fin / 80)))
            n_f = ov.get('F', (max(1, round(fin / 150)) if (u in HAB or u == 'kitchen') else 0))
            if outdoor and not covered:                         # wall bulkhead on the house side of an open deck
                cx, cy = centre(r['r']); bx = min(max(W / 2, x + 6), x + w - 6); by = y + 3 if cy > D / 2 else y + dd - 3
                lights.append(dict(lv=lid, x=bx, y=by, z=z0 + 78, kind='wall', room=r['id'], area=fin, ip=True, cct=f'{lid}-L', sw=r['id']))
            else:
                zc = z0 + (H - S['slab'] if outdoor else ch)
                for (lx, ly) in _grid(r, n_l):
                    lights.append(dict(lv=lid, x=lx, y=ly, z=zc - 1.5, kind='ceil', room=r['id'], area=fin / n_l, ip=outdoor, cct=f'{lid}-L', sw=r['id']))
            if n_f:
                for (fx, fy) in _grid(r, n_f):
                    # keep the fan clear of a light in the same spot
                    if any(abs(L['x'] - fx) < 14 and abs(L['y'] - fy) < 14 and L['room'] == r['id'] for L in lights):
                        fx += min(30, w / 4)
                    fans.append(dict(lv=lid, x=fx, y=fy, z=z0 + ch - 12, room=r['id'], cct=f'{lid}-L', sw=r['id']))
            if outdoor: continue
            # switchboard at the ENTRY: beside the latch side of the door you come in by, inside the room, 1.1 m up,
            # so light and fan are on before you walk in (a bedside switch alone is not enough).
            # A door counts when its clear width lies along this room's edge (it may run past the corner).
            cand = []
            for o in lv['doors']:
                rr = opening_rect(o, d, lv)
                if not rr: continue
                a, b = min(o['a'], o['b']), max(o['a'], o['b'])
                if o['o'] == 'h': on = abs(rr[1] - (y + dd)) < 1 or abs(rr[1] + rr[3] - y) < 1; ovl = min(b, x + w) - max(a, x)
                else: on = abs(rr[0] - (x + w)) < 1 or abs(rr[0] + rr[2] - x) < 1; ovl = min(b, y + dd) - max(a, y)
                if not on or ovl < 18: continue
                far = room_at(lv, ((rr[0] + rr[2] / 2) + (_face_side(o, r) * -(rr[2] / 2 + 6) if o['o'] == 'v' else 0),
                                   (rr[1] + rr[3] / 2) + (_face_side(o, r) * -(rr[3] / 2 + 6) if o['o'] == 'h' else 0)))
                fu = (far or {}).get('use', '')
                rank = (0 if o['type'] in ('door', 'main', 'bath') and fu in ('hall', 'passage', 'lobby', 'corridor', 'stair', 'living', 'family', 'dining') else
                        1 if o['type'] in ('door', 'main', 'bath') else 2 if o['type'] == 'arch' else 3)
                cand.append((rank, o, rr))
            cand.sort(key=lambda c: c[0])
            sw = None
            for ci, (rank, o, rr) in enumerate(cand):
                if ci and (rank != 0 or o['type'] not in ('door', 'main')): continue     # a second door from a hall/passage gets a two-way switch; not ensuite or wardrobe doors
                a, b = min(o['a'], o['b']), max(o['a'], o['b'])
                latch = b + 5 if o.get('hg', 'a') == 'a' else a - 5
                if o['type'] in ('arch', 'slide', 'opening'): latch = b + 5
                lo = x if o['o'] == 'h' else y; hi = (x + w) if o['o'] == 'h' else (y + dd)
                if not (lo + 3 <= latch <= hi - 3):                                     # latch side runs past the room: use the other side
                    latch = a - 5 if latch > b else b + 5
                latch = min(max(latch, lo + 3), hi - 3)
                side = _face_side(o, r); what = 'switch' if not ci else 'two-way switch (second door)'
                if o['o'] == 'h':
                    fy = (rr[1] + rr[3]) if side > 0 else rr[1]
                    p_ = (latch, fy + side * 0.6); B.append(dict(x=latch - 1.7, y=fy + (0 if side > 0 else -0.8), z=z0 + 42, w=3.4, d=0.8, h=4.6, m='sw', lv=lid, k='elec', cct=f'{lid}-L', sw=r['id'], what=what))
                else:
                    fx_ = (rr[0] + rr[2]) if side > 0 else rr[0]
                    p_ = (fx_ + side * 0.6, latch); B.append(dict(x=fx_ + (0 if side > 0 else -0.8), y=latch - 1.7, z=z0 + 42, w=0.8, d=3.4, h=4.6, m='sw', lv=lid, k='elec', cct=f'{lid}-L', sw=r['id'], what=what))
                ENTRY.append(dict(lv=lid, room=r['id'], door=o.get('id'), x=p_[0], y=p_[1], what=what))
                if sw is None: sw = p_
            # wiring: switch -> up the wall -> across the ceiling to each light and fan
            if sw:
                zc = z0 + ch - 0.8
                n0 = len(B)
                for L in [L for L in lights if L['room'] == r['id']] + [F for F in fans if F['room'] == r['id']]:
                    _run(B, (sw[0], sw[1], z0 + 46), (L['x'], L['y'], zc), 0.7, 'wire', lid, 'wire', 'zxy')
                for b_ in B[n0:]: b_.update(cct=f'{lid}-L', sw=r['id'])
            # passages, halls and stairs: PIR motion sensor on the pathway lights (sensors + two-way switching)
            if u in ('hall', 'passage', 'lobby', 'corridor') or k == 'stair':
                cx_, cy_ = centre(r['r'])
                B.append(dict(x=cx_ - 2, y=cy_ - 2, z=z0 + ch - 1.2, w=4, d=4, h=1.2, m='sw', lv=lid, k='elec', cct=f'{lid}-L', sw='path', what='PIR sensor'))
            fxr = [f for f in lv['fixtures'] if room_at(lv, centre(f['r'])) is r]
            # wet rooms: no general sockets; a shaver/mirror socket beside each basin, outside the shower zone
            if k == 'wet':
                for f in fxr:
                    if f['t'] not in ('basin', 'vanity'): continue
                    bxr = f['r']; dists = {'s': bxr[1] - y, 'n': y + dd - bxr[1] - bxr[3], 'w': bxr[0] - x, 'e': x + w - bxr[0] - bxr[2]}
                    bk = min(dists, key=dists.get)
                    if bk in 'sn':
                        px = bxr[0] + bxr[2] + 4 if bxr[0] + bxr[2] + 8 < x + w else bxr[0] - 4; py = y if bk == 's' else y + dd - 0.8
                        B.append(dict(x=px - 3, y=py, z=z0 + 46, w=6, d=0.8, h=3, m='sw', lv=lid, k='elec', cct=f'{lid}-W', sw=r['id'], what='mirror socket'))
                    else:
                        py = bxr[1] + bxr[3] + 4 if bxr[1] + bxr[3] + 8 < y + dd else bxr[1] - 4; px = x if bk == 'w' else x + w - 0.8
                        B.append(dict(x=px, y=py - 3, z=z0 + 46, w=0.8, d=6, h=3, m='sw', lv=lid, k='elec', cct=f'{lid}-W', sw=r['id'], what='mirror socket'))
                continue
            # bedrooms: twin socket + two-way light switch on each side of the bed head
            for f in fxr:
                if f['t'] != 'bed': continue
                bxr = f['r']; dists = {'s': bxr[1] - y, 'n': y + dd - bxr[1] - bxr[3], 'w': bxr[0] - x, 'e': x + w - bxr[0] - bxr[2]}
                hd = f.get('head') or min(dists, key=dists.get)
                pts = ([(bxr[0] - 8, y if hd == 's' else y + dd), (bxr[0] + bxr[2] + 8, y if hd == 's' else y + dd)] if hd in 'sn'
                       else [(x if hd == 'w' else x + w, bxr[1] - 8), (x if hd == 'w' else x + w, bxr[1] + bxr[3] + 8)])
                for px, py in pts:
                    if not (x <= px <= x + w and y <= py <= y + dd): continue
                    if hd in 'sn':
                        B.append(dict(x=px - 3, y=py - (0 if hd == 's' else 0.8), z=z0 + 24, w=6, d=0.8, h=3, m='sw', lv=lid, k='elec', cct=f'{lid}-P', sw=r['id'], what='bedside socket'))
                        B.append(dict(x=px - 1.7, y=py - (0 if hd == 's' else 0.8), z=z0 + 34, w=3.4, d=0.8, h=3.4, m='sw', lv=lid, k='elec', cct=f'{lid}-L', sw=r['id'], what='bedside two-way switch'))
                    else:
                        B.append(dict(x=px - (0 if hd == 'w' else 0.8), y=py - 3, z=z0 + 24, w=0.8, d=6, h=3, m='sw', lv=lid, k='elec', cct=f'{lid}-P', sw=r['id'], what='bedside socket'))
                        B.append(dict(x=px - (0 if hd == 'w' else 0.8), y=py - 1.7, z=z0 + 34, w=0.8, d=3.4, h=3.4, m='sw', lv=lid, k='elec', cct=f'{lid}-L', sw=r['id'], what='bedside two-way switch'))
                    zc = z0 + ch - 0.8; n0 = len(B)
                    for L in [L for L in lights if L['room'] == r['id']][:1]:
                        _run(B, (px, py, z0 + 38), (L['x'], L['y'], zc), 0.7, 'wire', lid, 'wire', 'zxy')
                    for b_ in B[n0:]: b_.update(cct=f'{lid}-L', sw=r['id'])
            # twin sockets: accessible heights, 12" (300 mm) above floor; kitchen and laundry at 42" over the counter
            n_s = ov.get('S', SOCKETS.get(u, 1))
            hz = 42 if (u == 'kitchen' or k == 'wet' or u == 'laundry') else 12
            spans = []
            for o in lv['doors'] + lv['windows']:
                rr = opening_rect(o, d, lv)
                if rr and (o in lv['doors'] or hz > o.get('sill', 0)): spans.append(rr)
            cands = []
            for side in ('s', 'n', 'w', 'e'):
                if side in r['open']: continue
                for f in (.5, .2, .8, .35, .65):
                    if side in 'sn':
                        px, py = x + w * f, (y if side == 's' else y + dd)
                    else:
                        px, py = (x if side == 'w' else x + w), y + dd * f
                    if any(s_[0] - 8 <= px <= s_[0] + s_[2] + 8 and s_[1] - 8 <= py <= s_[1] + s_[3] + 8 for s_ in spans): continue
                    cands.append((side, px, py))
            seen = []
            for side, px, py in cands:
                if len(seen) >= n_s: break
                if any(abs(px - a) + abs(py - b) < 30 for _, a, b in seen): continue
                seen.append((side, px, py))
                cc = f'{lid}-K' if u == 'kitchen' else f'{lid}-W' if u == 'laundry' else f'{lid}-P'
                if side in 'sn':
                    B.append(dict(x=px - 3, y=py - (0 if side == 's' else 0.8), z=z0 + hz, w=6, d=0.8, h=3, m='sw', lv=lid, k='elec', cct=cc, sw=r['id'], what='twin socket'))
                else:
                    B.append(dict(x=px - (0 if side == 'w' else 0.8), y=py - 3, z=z0 + hz, w=0.8, d=6, h=3, m='sw', lv=lid, k='elec', cct=cc, sw=r['id'], what='twin socket'))
        # electrical gear (meter, DB, inverter, battery, network cabinet ...)
        GEAR = {'MS': (14, 6, 18, 48, 'gear'), 'DB': (16, 4, 24, 54, 'gear'), 'INV': (16, 8, 24, 48, 'gear'),
                'BAT': (20, 10, 26, 4, 'gear'), 'NET': (22, 18, 24, 54, 'dark'), 'SI': (12, 6, 16, 54, 'gear'),
                'DCI': (10, 6, 14, 54, 'gear'), 'SA': (5, 5, 1.5, None, 'sw'), 'AP': (8, 8, 1.5, None, 'sw'), 'CCTV': (5, 5, 5, None, 'dark')}
        for p in lv['points']:
            gw, gd, gh, gz, gm = GEAR.get(p['t'], (8, 4, 8, 48, 'gear'))
            zz = z0 + (gz if gz is not None else H - S['slab'] - gh)
            B.append(dict(x=p['x'] - gw / 2, y=p['y'] - gd / 2, z=zz, w=gw, d=gd, h=gh, m=gm, lv=lid, k='elec', id=p['t']))
            if p['t'] == 'DB' and li + 1 < len(levels):    # cable riser to the floor above
                _run(B, (p['x'] + 10, p['y'], zz + gh), (p['x'] + 10, p['y'], levels[li + 1]['ffl'] + 54), 2, 'wire', lid, 'wire', 'zxy')
        # ---------------- plumbing ----------------
        lvst = [s_ for s_ in stacks if lid in s_.get('levels', [l['id'] for l in levels])]
        zdrain = z0 - (10 if li == 0 else S['slab'] + 4)
        for f in lv['fixtures']:
            if f['t'] not in WET_FIX: continue
            c = centre(f['r']); dia = 4 if f['t'] == 'wc' else 2
            dr = f.get('_drain') or {}
            tgt = next(((s_['x'], s_['y']) for s_ in lvst if s_['id'] == dr.get('stack')), None)
            if tgt is None:
                g = next((g for g in d['services'].get('gullies', []) if g.get('id', 'gully') == dr.get('stack')), None)
                if g: tgt = (g['x'], g['y'])
            if tgt is None and lvst:
                s_ = min(lvst, key=lambda s_: abs(c[0] - s_['x']) + abs(c[1] - s_['y'])); tgt = (s_['x'], s_['y'])
            if tgt is None and 'new gully' in str(dr.get('stack', '')):
                fac = dr['stack'].split('(')[1][0]; tgt = {'S': (c[0], -12), 'N': (c[0], D + 12), 'W': (-12, c[1]), 'E': (W + 12, c[1])}[fac]
                B.append(dict(x=tgt[0] - 6, y=tgt[1] - 6, z=0, w=12, d=12, h=2, m='gully', lv=lid, k='tankx'))
            if tgt is None: continue
            _run(B, (c[0], c[1], z0 + 1), (tgt[0], tgt[1], zdrain), dia, 'pvc', lid, 'plumb', 'zxy')
            # water: cold riser beside the stack, hot from a geyser in the same room
            rr = room_at(lv, c)
            src = min(lvst, key=lambda s_: abs(c[0] - s_['x']) + abs(c[1] - s_['y'])) if lvst else None
            zw = z0 + (24 if f['t'] in ('wc', 'shower', 'tub') else 20)
            if src and WATER.get(f['t']):
                _run(B, (src['x'] + 7, src['y'] + 7, zw), (c[0], c[1], zw), 1, 'cold', lid, 'cold', 'xy')
            gy = next((g for g in lv['fixtures'] if g['t'] == 'geyser' and rr is not None and room_at(lv, centre(g['r'])) is rr), None)
            if gy and 'h' in WATER.get(f['t'], ''):
                gc = centre(gy['r']); _run(B, (gc[0], gc[1], z0 + 72), (c[0] + 3, c[1] + 3, zw + 6), 1, 'hot', lid, 'hot', 'zxy')
        # ---------------- exhaust ----------------
        for e in d['services'].get('exhaust', []):
            r = next((r for r in rooms if r['id'] == e['room']), None)
            if not r: continue
            x, y, w, dd = r['r']; zc = z0 + ceiling_h(d, lv, r) - 5
            if e.get('via') == 'hood':
                hob = next((f for f in lv['fixtures'] if f['t'] == 'hob' and room_at(lv, centre(f['r'])) is r), None)
                hc = centre(hob['r']) if hob else centre(r['r'])
                hw = (hob['r'][2] + 6) if hob else 30; hd_ = (hob['r'][3] + 2) if hob else 20
                hx = hob['r'][0] - 3 if hob else hc[0] - hw / 2; hy = hob['r'][1] - 1 if hob else hc[1] - hd_ / 2
                B.append(dict(x=hx, y=hy, z=z0 + 62, w=hw, d=hd_, h=6, m='steel', lv=lid, k='elec', id='hood'))
                B.append(dict(x=hc[0] - 5, y=hc[1] - 5, z=z0 + 68, w=10, d=10, h=zc - z0 - 63, m='steel', lv=lid, k='elec', id='hood-chimney'))
                out = e.get('out') or (hc[0], 0 if hc[1] < D / 2 else D)
                _run(B, (hc[0], hc[1], zc), (out[0], out[1], zc), 6, 'exh', lid, 'exh', 'xy')
                B.append(dict(x=out[0] - 5, y=out[1] - 5, z=zc - 5, w=10, d=10, h=10, m='grille', lv=lid, k='exhfan'))
                continue
            st = next((s_ for s_ in stacks if s_['id'] == e.get('via')), None)
            if st:
                fx = min(max(st['x'], x + 8), x + w - 8); fy = min(max(st['y'], y + 8), y + dd - 8)
                B.append(dict(x=fx - 5, y=fy - 5, z=zc + 2, w=10, d=10, h=2, m='grille', lv=lid, k='exhfan'))
                _run(B, (fx, fy, zc), (st['x'], st['y'] + 3, zc), 4, 'exh', lid, 'exh', 'xy')
            else:                                                # through the nearest outside wall
                cx, cy = centre(r['r']); opts = [(cx, y, y), (cx, y + dd, D - y - dd), (x, cy, x), (x + w, cy, W - x - w)]
                px, py, _ = min(opts, key=lambda t: t[2])
                B.append(dict(x=px - 5, y=py - 5, z=zc - 4, w=10, d=10, h=10, m='grille', lv=lid, k='exhfan'))
    # stack soil pipes (inside the pipe boxes) down to the ground-floor drain level, then to the septic tank
    sv = d['services']; sep = sv.get('septic'); ug = (sv.get('water') or {}).get('ug_tank')
    gf = levels[0]
    for s_ in stacks:
        ls = [l for l in levels if l['id'] in s_.get('levels', [l['id'] for l in levels])]
        if not ls: continue
        z_top = ls[-1]['ffl'] + ls[-1]['h'] + 24
        _run(B, (s_['x'], s_['y'], gf['ffl'] - 10), (s_['x'], s_['y'], z_top), 4, 'pvc', ls[0]['id'], 'plumb', 'zxy')
        _run(B, (s_['x'] + 7, s_['y'] + 7, gf['ffl'] + 20), (s_['x'] + 7, s_['y'] + 7, roof_z + 12), 1.2, 'cold', ls[0]['id'], 'cold', 'zxy')
        if sep:
            _run(B, (s_['x'], s_['y'], gf['ffl'] - 10), (sep['x'], sep['y'], -14), 4, 'pvc', ls[0]['id'], 'plumb', 'zxy')
    for g in sv.get('gullies', []):
        B.append(dict(x=g['x'] - 9, y=g['y'] - 9, z=0, w=18, d=18, h=2, m='gully', lv=gf['id'], k='tankx'))
        if sep: _run(B, (g['x'], g['y'], -6), (sep['x'], sep['y'], -14), 4, 'pvc', gf['id'], 'plumb', 'yx')
    if sep:
        B.append(dict(x=sep['x'] - 48, y=sep['y'] - 30, z=-60, w=96, d=60, h=60, m='tank', lv='*', k='tankx'))
        B.append(dict(x=sep['x'] - 12, y=sep['y'] - 12, z=0, w=24, d=24, h=1.5, m='gully', lv='*', k='tankx'))
    if ug:
        side = max(48, (ug.get('l', 5000) / 1000 / 1.5) ** .5 * 39.37)
        B.append(dict(x=ug['x'] - side / 2, y=ug['y'] - side / 2, z=-60, w=side, d=side, h=60, m='water', lv='*', k='tankx'))
        B.append(dict(x=ug['x'] - 12, y=ug['y'] - 12, z=0, w=24, d=24, h=1.5, m='gully', lv='*', k='tankx'))
        if stacks:
            s_ = min(stacks, key=lambda s_: abs(ug['x'] - s_['x']) + abs(ug['y'] - s_['y']))
            _run(B, (ug['x'], ug['y'], -8), (s_['x'] + 7, s_['y'] + 7, gf['ffl'] + 20), 1.2, 'cold', gf['id'], 'cold', 'yx')
    # rainwater: 110 mm pipes hidden in the pipe boxes, roof outlet with leaf guard on top, to the recharge pit / tank
    for p_ in rw_pipes(d):
        for l in levels:
            _run(B, (p_['x'], p_['y'], l['ffl'] - (10 if l is gf else 0)), (p_['x'], p_['y'], l['ffl'] + l['h']), 4.3, 'rw', l['id'], 'rwp', 'zxy')
        B.append(dict(x=p_['x'] - 6, y=p_['y'] - 6, z=roof_z, w=12, d=12, h=3, m='grille', lv=top['id'], k='rwp', what='roof outlet + leaf guard'))
        dst = (sv.get('water') or {}).get('rwh') or ug or sep
        if dst: _run(B, (p_['x'], p_['y'], gf['ffl'] - 10), (dst['x'], dst['y'], -10), 4.3, 'rw', gf['id'], 'rwp', 'xy')
    # sliding wardrobes: anthracite frame, one mirror door, the rest lacquered glass
    for lv in levels:
        for f in lv['fixtures']:
            if f['t'] != 'wardrobe' or f.get('slide') is False: continue
            r = room_at(lv, centre(f['r']))
            if not r: continue
            x, y, w, dd = f['r']; rx, ry, rw_, rd = r['r']
            back = min({'s': y - ry, 'n': ry + rd - y - dd, 'w': x - rx, 'e': rx + rw_ - x - w}.items(), key=lambda t: t[1])[0]
            front = {'s': 'n', 'n': 's', 'w': 'e', 'e': 'w'}[back]; L_ = w if front in 'sn' else dd; n = max(2, round(L_ / 30)); z = lv['ffl'] + 1
            for i in range(n):
                a = (x if front in 'sn' else y) + L_ * i / n + .3; ln = L_ / n - .6
                if front in 'sn':
                    fy = y + dd if front == 'n' else y - .8
                    B.append(dict(x=a, y=fy, z=z, w=ln, d=.8, h=82, m='wmirr' if i == 0 else 'lacq', lv=lv['id'], k='fixw', fid=f['id']))
                else:
                    fx = x + w if front == 'e' else x - .8
                    B.append(dict(x=fx, y=a, z=z, w=.8, d=ln, h=82, m='wmirr' if i == 0 else 'lacq', lv=lv['id'], k='fixw', fid=f['id']))
    return dict(boxes=B, doors=doors, lights=lights, fans=fans, entry=ENTRY)


def rw_pipes(d):
    """Rainwater downpipes: services.rw if given, else one 110 mm pipe in each pipe box that reaches the roof."""
    sv = d['services']
    if sv.get('rw'): return sv['rw']
    top = d['levels'][-1]['id']
    return [dict(x=s_['x'] + 3, y=s_['y'] - 3, auto=True) for s_ in d['stacks'] if top in s_.get('levels', [l['id'] for l in d['levels']])]
