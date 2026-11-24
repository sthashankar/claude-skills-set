#!/usr/bin/env python3
"""Quantity take-off + editable estimate page from a design JSON.
usage: build_estimate.py design.json out.html [--rates rates.json] [--summary out_summary.json] [--compare old_summary.json]

Every quantity comes from the drawing (finished room sizes, openings, fixtures, stacks, rails), so the estimate
moves with every design change. Rates come from the book named in design estimate.rates (or --rates); "sample" = the
sample book, which must be the user's explicit choice. A rate the design needs but the book leaves null stops the build.
Lines in design JSON: room 'extra': [{label, qty, unit, rate|rk}] adds project-specific items;
design 'estimate': {'wh_extra': [{label, amount}], 'pct': {...}, 'notice': '', 'basis': ''} overrides whole-house parts.
"""
import sys, os, json, math, html
from hdlib import *
import check_design as CK

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape
HAB = CK.HAB
FALSE_CEIL = {'living', 'master', 'bed', 'dining', 'family', 'drawing', 'sitting'}
SOCKETS = {'living': 4, 'master': 4, 'bed': 3, 'family': 3, 'study': 3, 'dining': 2, 'kitchen': 4, 'laundry': 2, 'hall': 1,
           'puja': 1, 'store': 1, 'wc': 0, 'bath': 1, 'ensuite': 1, 'deck': 1, 'balcony': 1, 'terrace': 1, 'verandah': 1}
FURN = ('sofa', 'bed', 'dtable', 'table', 'desk', 'tv', 'chair', 'rug', 'plant')


class Book:
    """The project's rate book. Labels fall back to the blank template, prices never do."""
    def __init__(self, d, path=None):
        v = path or d.get('estimate', {}).get('rates')
        if not v: raise IntakeError('No rate book chosen: ask the user for local rates and currency, then set estimate.rates (or "sample" if the user accepts the sample rates)')
        self.R = R = data_file(d, 'rates', v); T = data_file(d, 'rates', 'rates_template.json')
        self.sample = bool(R.get('_sample')); self.cur = R.get('currency') or {}
        if not self.cur.get('symbol'): raise IntakeError('The rate book has no currency symbol')
        self.rb = {r['k']: r for r in T['rates'] if 'k' in r}; self.rb.update({r['k']: r for r in R['rates'] if 'k' in r})
        self.fx = {r['k']: r for r in T['fixed']}; self.fx.update({r['k']: r for r in R.get('fixed', [])})
        self.pct = {r['k']: r for r in T['pct']}; self.pct.update({r['k']: dict(r) for r in R.get('pct', [])})
        self.need = {}

    def price(self, r):
        if r.get('def') is None: self.need[r['k']] = r['label']
        return r.get('def') or 0

    def fixed(self, k):
        return self.price(self.fx[k])

    def check(self):
        if self.need:
            raise IntakeError('Estimate not built: the rate book has no price for these. Ask the user (0 = not applicable):\n' +
                              '\n'.join(f'  - {k}: {l}' for k, l in self.need.items()))


def door_room(d, lv, o):
    """The room an opening is priced in: the indoor room; for internal doors, the one it swings into (wet rooms win)."""
    a, b = min(o['a'], o['b']), max(o['a'], o['b']); mid = (a + b) / 2; c = []
    for sgn in (1, -1):
        for t in (8, 14):
            p = (mid, o['at'] + sgn * t) if o['o'] == 'h' else (o['at'] + sgn * t, mid)
            q = room_at(lv, p)
            if q: c.append((sgn, q)); break
    indoor = [x for x in c if x[1]['k'] not in CK.OUTDOOR]
    if not indoor: return c[0][1] if c else None
    if len(indoor) == 1: return indoor[0][1]
    wet = [x for x in indoor if x[1]['k'] == 'wet']
    if wet: return wet[0][1]
    sw = [x for x in indoor if x[0] == o.get('dir', 1)]
    return (sw or indoor)[0][1]


def build_lines(d, BK):
    RB = BK.rb
    floors = []; n = [0]
    def L(lines, rk, label, qty, unit, cls='f', rate=None, opt=False):
        if qty is None or qty <= 0: return
        if rate is None: BK.price(RB[rk])
        n[0] += 1
        it = dict(id=f"L{n[0]}", rk=rk, label=label, qty=round(qty, 2), unit=unit, cls=cls)
        if rate is not None: it['rate'] = rate; it['rk'] = None
        if opt: it['opt'] = True
        lines.append(it)
    priced_ops = {}
    for lv in d['levels']:
        walls = walls_for(d, lv); lv['_walls'] = walls
        for o in lv['doors'] + lv['windows']:
            r = door_room(d, lv, o)
            if r: priced_ops.setdefault(r['id'], []).append(o)
    sa_levels = set()
    for li, lv in enumerate(d['levels']):
        rooms = []
        for r in lv['rooms']:
            k, u = r['k'], r['use']; A = room_areas(r); lines = []
            brick, fin = A['brick'], A['fin']
            if k == 'void':
                continue
            # structure
            if k == 'roof':
                L(lines, 'bRoof', 'Roof: XPS insulation, screed, membrane, reflective tiles', fin, 'sq ft', 's')
            else:
                rk = {'room': 'sHab', 'wet': 'sWet', 'stair': 'sStair', 'deck': 'sDeck', 'terrace': 'sDeck', 'court': 'sCourt'}.get(k, 'sHab')
                L(lines, rk, 'Structure: RCC frame, slab, brick walls, plaster, foundation share (brick-to-brick area)', brick, 'sq ft', 's')
            # floor
            fk = {'wet': 'fWet', 'deck': 'fDeck', 'terrace': 'fDeck', 'stair': 'fStair', 'court': 'fCourt'}.get(k) or \
                 {'parq': 'fParq', 'black': 'fBlack'}.get(r.get('floor'), 'fHab')
            if k != 'roof': L(lines, fk, RB[fk]['label'], fin, 'sq ft')
            if k == 'terrace': L(lines, 'bRoof', 'Terrace waterproofing and insulation under the tiles', fin, 'sq ft', 's')
            if k == 'wet': L(lines, 'bWP', RB['bWP']['label'], fin, 'sq ft of floor')
            # walls and ceiling
            if k not in CK.OUTDOOR:
                ch = ceiling_h(d, lv, r) / 12
                ops = openings_in(lv, r)
                op_area = sum(abs(o['b'] - o['a']) * ((o['head'] - o['sill']) if 'sill' in o else o['h']) for o in ops) / 144
                wall = A['perim'] / 12 * ch - op_area
                tile = 0
                if k == 'wet':
                    tile = A['perim'] / 12 * min(ch, 7.0) - op_area * 0.7
                    L(lines, 'wTile', 'Wall tile to 7\'-0"' + cite(d, 'wet-wall'), tile, 'sq ft of wall')
                if u == 'kitchen':
                    run = sum(max(f['r'][2], f['r'][3]) / 12 for f in lv['fixtures'] if f['t'] == 'counter' and room_at(lv, centre(f['r'])) is r)
                    tile = run * 2.0
                    L(lines, 'wTile', 'Kitchen splashback tile, 2\'-0" high', tile, 'sq ft of wall')
                L(lines, 'wPaint', 'Wall putty and 2 coats emulsion', wall - tile, 'sq ft of wall')
                ck = 'cWet' if k == 'wet' else ('cFalse' if u in FALSE_CEIL else 'cPlain')
                L(lines, ck, RB[ck]['label'], fin, 'sq ft')
            # openings
            for o in priced_ops.get(r['id'], []):
                wdt = abs(o['b'] - o['a'])
                if o in lv['doors']:
                    t = o['type']
                    if t in ('arch', 'opening'): continue
                    if t == 'slide':
                        L(lines, 'wSlide', f"Sliding glass door {ftin(wdt)} × {ftin(o['h'])}", wdt * o['h'] / 144, 'sq ft')
                    else:
                        rk = {'main': 'dMain', 'ext': 'dExt', 'bath': 'dBath'}.get(t, 'dInt')
                        L(lines, rk, f"{RB[rk]['label'].split(':')[0]} {ftin(wdt)} wide", 1, 'each')
                else:
                    t = o['type']; q, fac = CK.other_side(d, lv, o, r); outside = q == 'outside' or (q and q['k'] in CK.OUTDOOR)
                    rk = 'wW1' if t.startswith('W1') else ('wFix' if outside else 'wFixN') if t == 'fixed' else ('wAluT' if outside else 'wAlu')
                    L(lines, rk, f"Window {o['id']} {t} {ftin(wdt)} × {ftin(o['head']-o['sill'])}" + ('' if outside else ' (inside)'),
                      wdt * (o['head'] - o['sill']) / 144, 'sq ft')
            # electrical (auto, override with r['elec'])
            ov = r.get('elec', {})
            if k not in ('roof', 'court'):
                fx = [f for f in lv['fixtures'] if room_at(lv, centre(f['r'])) is r]
                lights = ov.get('L', max(1, math.ceil(fin / 80)) if k not in CK.OUTDOOR else 1)
                fans = ov.get('F', (max(1, round(fin / 150)) if (u in HAB or u == 'kitchen') else 0))
                sk = ov.get('S', SOCKETS.get(u, 1))
                p15 = ov.get('P', (2 if u == 'kitchen' else 0) + sum(1 for f in fx if f['t'] in ('wm', 'dw')))
                acs = ov.get('AC', sum(1 for f in fx if f['t'] == 'ac'))
                ex = ov.get('EX', 1 if any(e['room'] == r['id'] and e.get('via') != 'hood' for e in d['services'].get('exhaust', [])) else 0)
                oth = ov.get('O', sum(1 for f in fx if f['t'] in ('tv', 'geyser', 'hob', 'mirror')))
                L(lines, 'eL', 'Light points (LED)', lights, 'each'); L(lines, 'eF', 'Ceiling fan points with fan', fans, 'each')
                L(lines, 'eS5', 'Double sockets', sk, 'each'); L(lines, 'eS15', 'High-power outlets', p15, 'each')
                L(lines, 'eAC', 'AC points', acs, 'each'); L(lines, 'eEx', 'Exhaust fan with duct share', ex, 'each')
                L(lines, 'eOther', 'TV/data, geyser, chimney, mirror points', oth, 'each')
                if k not in CK.OUTDOOR: L(lines, 'eSB', 'Switchboard', 1, 'each')
                if u in ('bed', 'master') and lv['id'] not in sa_levels:
                    sa_levels.add(lv['id']); L(lines, 'eSA', 'Smoke alarms (hall outside bedrooms, interconnected)', 2, 'each')
                for f in fx:
                    t = f['t']; w_, d_ = f['r'][2] / 12, f['r'][3] / 12
                    if t == 'wc': L(lines, 'pWC', RB['pWC']['label'], 1, 'each')
                    if t == 'basin': L(lines, 'pBasin', RB['pBasin']['label'], 1, 'each')
                    if t == 'vanity':
                        rk = 'pVan9' if max(w_, d_) >= 2.9 else 'pVan6' if max(w_, d_) >= 1.9 else 'pVanS'
                        L(lines, 'pBasin', 'Basin with tap and waste', 1, 'each'); L(lines, rk, RB[rk]['label'], 1, 'each')
                        L(lines, 'pMirC', RB['pMirC']['label'], 1, 'each')
                    if t == 'shower':
                        L(lines, 'pShower', RB['pShower']['label'], 1, 'each')
                        L(lines, 'pScreen', 'Shower screen, 2.0 m high', (w_ + d_) / 2 * 6.5, 'sq ft')
                    if t == 'tub': L(lines, 'pTub', RB['pTub']['label'], 1, 'each')
                    if t in ('sink', 'bar_sink'): L(lines, 'pSink', 'Sink with tap', 1, 'each')
                    if t == 'wm': L(lines, 'pWM', RB['pWM']['label'], 1, 'each')
                    if t == 'geyser': L(lines, 'pGeyser', RB['pGeyser']['label'], 1, 'each')
                    if t == 'wardrobe': L(lines, 'bWard', f"Wardrobe {ftin(max(f['r'][2], f['r'][3]))} wide, floor to ceiling", max(w_, d_) * 7.5, 'sq ft of face')
                    if t == 'shelf': L(lines, 'bShelf', 'Open shelves', max(w_, d_) * 7, 'sq ft of face')
                    if t == 'cupboard': L(lines, 'bCab', 'Cupboard', max(w_, d_), 'running ft')
                    if t == 'counter' and u == 'kitchen':
                        L(lines, 'bCounter', RB['bCounter']['label'], max(w_, d_), 'running ft')
                        L(lines, 'bWall', RB['bWall']['label'], max(w_, d_) * 0.7, 'running ft')
                    elif t == 'counter': L(lines, 'bCab', 'Counter / base unit', max(w_, d_), 'running ft')
                    if t == 'hob': L(lines, 'bHob', RB['bHob']['label'], 1, 'each')
                    if t == 'ac': L(lines, 'aAC20' if fin > 250 else 'aAC15', RB['aAC20' if fin > 250 else 'aAC15']['label'], 1, 'each')
                    if t == 'altar': L(lines, None, 'Marble altar platform', 1, 'each', rate=BK.fixed('altar'))
                    if t == 'skylight': L(lines, 'bSky', RB['bSky']['label'], w_ * d_, 'sq ft')
                    if t in FURN: L(lines, None, BK.fx['f_' + t]['label'], 1, 'each', 'o', rate=BK.fixed('f_' + t), opt=True)
                if any(f['t'] in ('shower', 'tub') for f in fx): L(lines, 'pTMV', RB['pTMV']['label'], 1, 'each')
            elif k == 'roof':
                for f in [f for f in lv['fixtures'] if room_at(lv, centre(f['r'])) is r and f['t'] == 'skylight']:
                    L(lines, 'bSky', RB['bSky']['label'], f['r'][2] * f['r'][3] / 144, 'sq ft')
            # rails and stairs
            rl = sum((r['r'][2] if s in 'ns' else r['r'][3]) for s in r['rail']) / 12
            if rl and k != 'roof': L(lines, 'bRailDeck', 'Balustrade 1.0 m, MS, gaps < 125 mm', rl, 'running ft')
            if rl and k == 'roof': L(lines, None, 'Parapet 3\'-6" brick, plastered, coping', rl, 'running ft', 's', rate=BK.fixed('parapet_rft'))
            if k == 'void':
                pass
            for st in lv['stairs']:
                if overlap(st['flights'][0]['r'], r['r'], 1):
                    run = sum(max(fl['r'][2], fl['r'][3]) for fl in st['flights']) / 12 * 1.15
                    L(lines, 'bRailStair', 'Stair balustrade with timber handrail', run, 'running ft')
            for x in r.get('extra', []):
                L(lines, x.get('rk'), x['label'], x['qty'], x.get('unit', 'each'), x.get('cls', 'f'), rate=x.get('rate'))
            rooms.append(dict(id=r['id'], name=r['n'], area=round(fin, 2), cat=('roof' if k == 'roof' else k if k in ('deck', 'terrace', 'court') else 'room'), lines=lines))
        # void rooms: light-well balustrades go to the level
        for r in lv['rooms']:
            if r['k'] == 'void' and r['rail']:
                lines = []
                L(lines, 'bRailDeck', 'Light-well balustrade / glass guard', sum((r['r'][2] if s in 'ns' else r['r'][3]) for s in r['rail']) / 12, 'running ft')
                rooms.append(dict(id=r['id'], name=r['n'], area=0, cat='void', lines=lines))
        floors.append(dict(k=lv['id'], name=lv['name'], rooms=rooms))
    return floors


def whole_house(d, fs, BK):
    X = BK.fixed; rnd = BK.cur.get('round') or 1
    P = d['project']; S = d['services']; W, D = d['building']['w'] / 12, d['building']['d'] / 12
    foot = W * D; occ = P.get('occupants', 6); lvls = [l for l in d['levels'] if not l.get('roof_level')]
    ext_wall = 2 * (W + D) * sum(l['h'] for l in lvls) / 12 * (0.5 if set(P.get('boundary', [])) >= {'E', 'W'} else 0.85)
    wh = []
    def A(k, label, amt): wh.append(dict(k=k, label=label, def_=round(amt / rnd) * rnd))
    ffl0 = d['levels'][0]['ffl'] / 12
    A('w1', f"Plinth filling {ffl0:.1f} ft and entry steps", foot * ffl0 * X('plinth_cft') + X('entry_steps'))
    A('w2', 'Front wall, car gate, pedestrian gate', P.get('plot', {}).get('w', W * 12) / 12 * X('front_wall_rft'))
    A('w3', 'Parking, paths and garden', X('parking_rft') * P.get('plot', {}).get('w', 240) / 12)
    A('w5', f"Septic tank (3 chambers) and soak pit, {occ} people", X('septic_person') * occ + X('septic_base'))
    ug = S.get('water', {}).get('ug_tank', {}).get('l', 6000)
    A('w6', f"Underground water tank {ug:,} L, pump and lift", ug * X('ug_tank_l'))
    A('w7', f"{S.get('water', {}).get('roof_tanks', 2)} × 1,000 L overhead tanks and platform", X('roof_tank') * S.get('water', {}).get('roof_tanks', 2))
    A('w8', 'Rainwater harvesting: first flush, filter, recharge pit', X('rwh'))
    shw = S.get('water', {}).get('solar_hw', 300)
    if shw: A('w9', f"Solar water heater {shw} L", shw * X('solar_hw_l'))
    kwp = S.get('pv_kwp', 0)
    if kwp: A('w10', f"Solar PV {kwp} kWp, hybrid inverter, net metering{cite(d, 'pv')}", kwp * X('pv_kwp'))
    kwh = S.get('battery_kwh', 0)
    if kwh: A('w11', f"Battery {kwh} kWh{cite(d, 'battery')}", kwh * X('battery_kwh'))
    A('w12', f"Main supply: meter box, {len(lvls)} DBs, earthing, SPD", X('supply_base') + X('db_each') * len(lvls))
    A('w13', f"External walls: weatherproof acrylic paint, about {ext_wall:,.0f} sq ft", ext_wall * X('ext_paint'))
    A('w14', 'Building approval, permits, utility connections', X('approvals'))
    glazed = sum(abs(o['b'] - o['a']) for l in d['levels'] for o in l['windows'] if facade(d, o)) / 12
    A('w15', f"Sunshades (chajja) over outside windows, drip grooves, about {glazed:.0f} rft", glazed * X('chajja_rft'))
    bnd = P.get('boundary', [])
    if bnd: A('w16', f"Boundary footings ({', '.join(bnd)}): eccentric footings with strap beams (reserve until the engineer designs)", X('boundary_ft') * D * len(bnd))
    A('w18', 'Soil test and anti-termite treatment' + cite(d, 'termite'), X('soil_test') + foot * X('termite_sqft'))
    if d['levels'][0]['ffl'] > 6: A('w19', 'Step-free entry: ramp 1:14 with handrails and landing' + cite(d, 'access'), X('ramp'))
    circuits = sum(1 for l in lvls for r in l['rooms'] if r['k'] not in CK.OUTDOOR) // 2 + 4
    A('w20', f"Electrical safety: 30 mA RCDs on every circuit (about {circuits}), SPD, interconnected smoke alarms", circuits * X('rcd_circuit'))
    A('w21', 'Plumbing: pressure pump, backflow and pressure-limiting valves, ORG, inspection openings', X('plumbing_safety'))
    A('w24', f"Pipe boxes beside the stacks: {len(d['stacks'])} stacks, access panels, acoustic lagging", X('pipe_box') * sum(len(s.get('levels', [])) for s in d['stacks']))
    nres = sum(1 for f in fs if f['code'] == 'restrictor')
    if nres: A('w25', f"Window opening limiters{cite(d, 'restrictor')}: {nres}", nres * X('limiter'))
    for i, x in enumerate(d.get('estimate', {}).get('wh_extra', [])):
        A(f"x{i+1}", x['label'], x['amount'])
    return [dict(k=w['k'], label=w['label'], **{'def': w['def_']}) for w in wh]


def totals(floors, wh, pct, RB):
    rate = lambda l: l.get('rate') if l.get('rk') is None else RB[l['rk']]['def']
    rooms = {}; fl = {}
    for f in floors:
        t = 0
        for r in f['rooms']:
            a = sum(l['qty'] * rate(l) for l in r['lines'] if not l.get('opt'))
            rooms[r['id']] = a; t += a
        fl[f['k']] = t
    sub = sum(fl.values()) + sum(w['def'] for w in wh)
    pcs = sum(sub * p['def'] / 100 for p in pct)
    return dict(rooms=rooms, floors=fl, wh=sum(w['def'] for w in wh), sub=sub, pct=pcs, total=sub + pcs)


def short(n, cur):
    if cur.get('grouping') == 'lakh':
        return f"{cur['symbol']} {n/1e7:.2f} crore" if n >= 1e7 else f"{cur['symbol']} {n/1e5:.1f} lakh"
    return f"{cur['symbol']} {n/1e6:.2f} million" if n >= 1e6 else money(n, cur)


def money(n, cur):
    if cur.get('grouping') != 'lakh': return f"{cur['symbol']} {round(n):,}"
    s = str(int(round(n))); last = s[-3:]; rest = s[:-3]; parts = []
    while len(rest) > 2: parts.insert(0, rest[-2:]); rest = rest[:-2]
    if rest: parts.insert(0, rest)
    return f"{cur['symbol']} " + ','.join(parts + [last])


def build(d, rates_path=None):
    BK = Book(d, rates_path); RB, cur = BK.rb, BK.cur
    fs = CK.run(d)
    floors = build_lines(d, BK)
    wh = whole_house(d, fs, BK)
    pct = list(BK.pct.values())
    for k, v in d.get('estimate', {}).get('pct', {}).items():
        for p in pct:
            if p['k'] == k: p['def'] = v
    for p in pct: BK.price(p)
    BK.check()
    gross = round(total_built(d))
    D = dict(rates=[r for r in BK.R['rates'] if 'h' in r or r.get('def') is not None], wh=wh, pct=pct, floors=floors, gross=gross,
             cur=dict(symbol=cur['symbol'], locale='en-IN' if cur.get('grouping') == 'lakh' else 'en-US'))
    T = totals(floors, wh, pct, RB)
    est = d.get('estimate', {})
    notice = est.get('notice', 'Quantities are taken off the design file: finished (plaster-to-plaster) room sizes for floors, ceilings, paint and tile; '
                     'brick-to-brick areas for structure; every door, window, fixture, stack and balustrade as drawn. ' + (codes(d).get('estimate_note') or ''))
    where = ' '.join(x for x in (BK.R.get('place'), BK.R.get('year')) if x)
    if BK.sample:
        notice = f'SAMPLE RATES: not quotes for this project. Replace every rate with local prices before using any total. ' + notice
    basis = est.get('basis', 'Concept-stage budget' + ''.join(f', {x}' for x in (where, BK.R.get('tax')) if x) + '. ' + ('Rates are samples from one study, not quotes. ' if BK.sample else '') +
                    'Check each rate against three local quotes. Not included: land, appliances, curtains, loose furniture (tick to include), lift, difficult soil.')
    key = 'est-' + ''.join(c for c in d['project']['name'].lower() if c.isalnum())[:24]
    if not BK.sample: key += '-' + ''.join(c for c in f"{where}{cur['symbol']}".lower() if c.isalnum() or c == '$')   # own saved edits: never mix currencies
    page = open(os.path.join(HERE, '..', 'templates', 'estimate_page.html')).read()
    page = page.replace('/*__D__*/null', json.dumps(D, ensure_ascii=False).replace('</', '<\\/')).replace('{{TITLE}}', E(d['project']['name'])) \
               .replace('{{WHERE}}', E(', '.join(x for x in ('SAMPLE RATES' if BK.sample else '', where, cur.get('name') or cur['symbol']) if x))).replace('{{KEY}}', key).replace('{{NOTICE}}', E(notice)).replace('{{BASIS}}', E(basis))
    summ = dict(total=round(T['total']), total_txt=short(T['total'], cur), cur=cur, sample_rates=BK.sample, per_sqft=round(T['total'] / max(1, gross)), gross=gross,
                floors={k: round(v) for k, v in T['floors'].items()}, rooms={k: round(v) for k, v in T['rooms'].items()},
                wh=round(T['wh']), wh_items={w['k']: w['def'] for w in wh})
    return page, summ


def compare(old, new):
    cur = new.get('cur') or {'symbol': '¤', 'grouping': 'western'}; co = old.get('cur') or cur
    if co.get('symbol') != cur.get('symbol'): return f"Currency changed ({co.get('symbol')} → {cur.get('symbol')}): totals cannot be compared"
    inr = lambda n: money(n, cur)
    out = [f"Total {inr(old['total'])} → {inr(new['total'])} ({'+' if new['total']>=old['total'] else '−'}{inr(abs(new['total']-old['total']))})"]
    for k in sorted(set(old['rooms']) | set(new['rooms'])):
        a, b = old['rooms'].get(k, 0), new['rooms'].get(k, 0)
        if abs(a - b) >= 10 * (cur.get('round') or 100): out.append(f"  {k}: {inr(a)} → {inr(b)}")
    for k in sorted(set(old['wh_items']) | set(new['wh_items'])):
        a, b = old['wh_items'].get(k, 0), new['wh_items'].get(k, 0)
        if abs(a - b) >= 10 * (cur.get('round') or 100): out.append(f"  whole-house {k}: {inr(a)} → {inr(b)}")
    if new.get('sample_rates'): out.append('SAMPLE RATES: not local prices')
    return '\n'.join(out)


if __name__ == '__main__':
    a = sys.argv
    d = load(a[1])
    if '--rates' in a: d.setdefault('estimate', {})['rates'] = a[a.index('--rates') + 1]
    try: require_intake(d); page, summ = build(d)
    except IntakeError as e: sys.exit(str(e))
    open(a[2], 'w').write(page)
    if '--summary' in a: json.dump(summ, open(a[a.index('--summary') + 1], 'w'), indent=1)
    print('wrote', a[2], '·', summ['total_txt'], f"({money(summ['total'], summ['cur'])}), {money(summ['per_sqft'], summ['cur'])}/sq ft on {summ['gross']:,} sq ft",
          '· SAMPLE RATES, not local prices' if summ['sample_rates'] else '')
    if '--compare' in a:
        print(compare(json.load(open(a[a.index('--compare') + 1])), summ))
