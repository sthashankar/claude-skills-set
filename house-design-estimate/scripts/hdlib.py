"""hdlib: shared model code for the house-design-estimate skill.

Units: inches. Origin = south-west OUTER corner of the building. x grows east, y grows north.
Room rects r=[x, y, w, d] are brick-to-brick clear spaces (inside faces of the walls), the way
room sizes are quoted on site. Walls are generated in the gaps between rooms (see walls_for).
"""
import json, math, copy, os

KINDS_OPEN = {'deck', 'terrace', 'court', 'void', 'roof', 'yard'}      # no walls of their own
KINDS_NOSLAB = {'void', 'court'}                                        # no floor slab above/below
WET_USES = {'bath', 'wc', 'ensuite', 'laundry'}
WET_FIX = {'wc', 'basin', 'shower', 'tub', 'sink', 'wm', 'dw', 'floor_trap', 'bar_sink'}
PLASTER = 0.5


def load(path):
    with open(path) as f:
        d = json.load(f)
    d['_dir'] = os.path.dirname(os.path.abspath(path))
    normalise(d)
    return d


# ---------------- intake, building codes and rate books ----------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
SAMPLE = {'codes': 'codes_sample.json', 'rates': 'rates_sample.json'}     # used only when the user chose "sample"
INTAKE = [
    ('project.location', 'Which city and country is the site in (with latitude, longitude and time zone)?'),
    ('project.north_deg', 'Which way is true north relative to the plan?'),
    ('project.road', 'Which side(s) is the road on?'),
    ('project.plot', 'What are the plot width and depth?'),
    ('project.boundary', 'Which walls stand on the plot boundary (empty list for none)?'),
    ('project.occupants', 'How many people will live there?'),
    ('project.codes', 'Which building codes and local rules apply, and which edition? (codes file, or "sample" for the demo codes)'),
    ('estimate.rates', 'Which local rates and currency should the estimate use? (rate book, or "sample" for the demo rates)'),
    ('vastu.enabled', 'Should Vastu be checked (true or false)?'),
]


class IntakeError(ValueError):
    pass


def missing_intake(d):
    out = []
    for key, q in INTAKE:
        a, b = key.split('.'); v = (d.get(a) or {}).get(b)
        blank = v is None or v == '' or v == {} or (b == 'boundary' and not isinstance(v, list))
        if b == 'location' and not blank:
            blank = bool(v.get('assumed')) or any(v.get(x) in (None, '') for x in ('city', 'lat', 'lon', 'tz'))
        if b == 'plot' and not blank: blank = not (v.get('w') and v.get('d'))
        if blank: out.append((key, q))
    return out


def require_intake(d):
    m = missing_intake(d)
    if m:
        raise IntakeError('Not built: ask the user for these first, then add them to the design JSON:\n' +
                          '\n'.join(f'  - {k}: {q}' for k, q in m))


def data_file(d, kind, v):
    """Read a codes file or rate book: inline dict, "sample", or a path beside the design, in the working folder or in data/."""
    if isinstance(v, dict): return copy.deepcopy(v)
    v = SAMPLE[kind] if v == 'sample' else v
    for p in (v, os.path.join(d.get('_dir', '.'), v), os.path.join(DATA_DIR, v)):
        if os.path.isfile(p):
            with open(p) as f: return json.load(f)
    raise IntakeError(f'{kind} file not found: {v}')


def codes(d):
    if '_codes' not in d:
        v = d['project'].get('codes')
        d['_codes'] = data_file(d, 'codes', v or 'sample'); d['_codes']['_unset'] = not v
    return d['_codes']


def lim(d, key):
    """A limit from the project's building codes; None = not known, so the check is skipped."""
    return codes(d).get('limits', {}).get(key)


def cite(d, key):
    t = codes(d).get('cite', {}).get(key)
    return f' ({t})' if t else ''


def seismic(d):
    return d['structure'].get('seismic') or codes(d).get('seismic') or {}


def normalise(d):
    p = d.setdefault('project', {})
    p.setdefault('name', 'House design')
    p.setdefault('location', {'city': 'Location not given', 'lat': 0, 'lon': 0, 'tz': 0, 'assumed': True})
    s = d.setdefault('structure', {})
    s.setdefault('wall_ext', 9); s.setdefault('wall_int', 4.5)
    s.setdefault('col', [12, 12]); s.setdefault('beam', [9, 18]); s.setdefault('slab', 5)
    s.setdefault('columns', [])
    for lv in d['levels']:
        lv.setdefault('h', 132); lv.setdefault('rooms', []); lv.setdefault('doors', [])
        lv.setdefault('windows', []); lv.setdefault('fixtures', []); lv.setdefault('walls', [])
        lv.setdefault('nowall', []); lv.setdefault('stairs', []); lv.setdefault('points', [])
        for r in lv['rooms']:
            r.setdefault('k', 'room'); r.setdefault('use', r['k']); r.setdefault('open', [])
            r.setdefault('rail', [])
        for i, o in enumerate(lv['doors']):
            o.setdefault('id', f"{lv['id']}-D{i+1}"); o.setdefault('type', 'door'); o.setdefault('h', 84)
            o.setdefault('hg', 'a'); o.setdefault('dir', 1)
        for i, o in enumerate(lv['windows']):
            o.setdefault('id', f"{lv['id']}-W{i+1}"); o.setdefault('type', 'W'); o.setdefault('sill', 36)
            o.setdefault('head', 84)
        for i, f in enumerate(lv['fixtures']):
            f.setdefault('id', f"{lv['id']}-{f['t']}{i+1}")
    d.setdefault('stacks', []); d.setdefault('services', {}); d.setdefault('roof', {})
    d.setdefault('vastu', {}); d.setdefault('log', [])
    z = 0
    for lv in d['levels']:
        lv.setdefault('ffl', z if lv is not d['levels'][0] else lv.get('ffl', 24))
        z = lv['ffl'] + lv['h']
    return d


def save(d, path):
    with open(path, 'w') as f:
        json.dump({k: v for k, v in d.items() if not k.startswith('_')}, f, indent=1, ensure_ascii=False)


# ---------------- formatting ----------------
def ftin(v):
    v = round(v * 2) / 2
    neg = v < 0; v = abs(v)
    f = int(v // 12); i = v - f * 12
    s = f"{int(i)}" if i == int(i) else f"{int(i)}½"
    return ('-' if neg else '') + f"{f}'-{s}\""


def sqft(a_in2):
    return a_in2 / 144.0


# ---------------- rect helpers ----------------
def rect_sub(a, b):
    """a minus b, axis-aligned rects [x,y,w,d]; returns list of rects."""
    ax, ay, aw, ad = a; bx, by, bw, bd = b
    ix0, iy0 = max(ax, bx), max(ay, by); ix1, iy1 = min(ax + aw, bx + bw), min(ay + ad, by + bd)
    if ix0 >= ix1 - 1e-6 or iy0 >= iy1 - 1e-6:
        return [a]
    out = []
    if iy0 > ay: out.append([ax, ay, aw, iy0 - ay])
    if iy1 < ay + ad: out.append([ax, iy1, aw, ay + ad - iy1])
    if ix0 > ax: out.append([ax, iy0, ix0 - ax, iy1 - iy0])
    if ix1 < ax + aw: out.append([ix1, iy0, ax + aw - ix1, iy1 - iy0])
    return [r for r in out if r[2] > 0.01 and r[3] > 0.01]


def overlap(a, b, tol=0.01):
    return (a[0] < b[0] + b[2] - tol and b[0] < a[0] + a[2] - tol and
            a[1] < b[1] + b[3] - tol and b[1] < a[1] + a[3] - tol)


def inside(p, r, tol=0.01):
    return r[0] - tol <= p[0] <= r[0] + r[2] + tol and r[1] - tol <= p[1] <= r[1] + r[3] + tol


def centre(r):
    return (r[0] + r[2] / 2, r[1] + r[3] / 2)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def level(d, lid):
    return next(l for l in d['levels'] if l['id'] == lid)


def room_at(lv, p):
    for r in lv['rooms']:
        if inside(p, r['r']):
            return r
    return None


# ---------------- walls ----------------
def _edges(r):
    x, y, w, dd = r['r']
    return {'s': ('h', y, x, x + w, -1), 'n': ('h', y + dd, x, x + w, 1),
            'w': ('v', x, y, y + dd, -1), 'e': ('v', x + w, y, y + dd, 1)}


def walls_for(d, lv):
    """Wall rects for one level: bands in the gaps between room rects, plus the outer shell."""
    S = d['structure']; W, D = d['building']['w'], d['building']['d']
    te, ti = S['wall_ext'], S['wall_int']
    rooms = lv['rooms']; out = []
    for r in rooms:
        if r['k'] in KINDS_OPEN and r['k'] not in ('court', 'void'):
            continue
        for side, (o, at, a, b, sg) in _edges(r).items():
            if side in r['open'] or side in r['rail']:
                continue
            if r['k'] in ('court', 'void'):      # light wells: only the outer shell wall
                onouter = (o == 'h' and ((sg < 0 and at <= te + 0.5) or (sg > 0 and at >= D - te - 0.5))) or \
                          (o == 'v' and ((sg < 0 and at <= te + 0.5) or (sg > 0 and at >= W - te - 0.5)))
                if not onouter:
                    continue
            # neighbour across a small gap?
            gap = None; skip = False
            for q in rooms:
                if q is r:
                    continue
                qe = _edges(q)[{'s': 'n', 'n': 's', 'w': 'e', 'e': 'w'}[side]]
                g = (qe[1] - at) * sg
                if 0 <= g <= 13 and min(b, qe[3]) - max(a, qe[2]) > 1:
                    if q['k'] in KINDS_OPEN and g < 0.5:
                        continue
                    if {'s': 'n', 'n': 's', 'w': 'e', 'e': 'w'}[side] in q['open'] and q['k'] not in KINDS_OPEN:
                        skip = True
                    gap = g if gap is None else min(gap, g)
            if skip:
                continue
            outer = (o == 'h' and ((sg < 0 and at <= te + 0.5) or (sg > 0 and at >= D - te - 0.5))) or \
                    (o == 'v' and ((sg < 0 and at <= te + 0.5) or (sg > 0 and at >= W - te - 0.5)))
            if outer:
                t = at if sg < 0 else ((D if o == 'h' else W) - at)
            elif gap and gap > 0.5:
                t = gap
            else:
                t = ti
            if t <= 0.2:
                continue
            ext = te if outer else ti
            a0, b0 = max(a - ext, 0), min(b + ext, W if o == 'h' else D)
            if o == 'h':
                band = [a0, at - t, b0 - a0, t] if sg < 0 else [a0, at, b0 - a0, t]
            else:
                band = [at - t, a0, t, b0 - a0] if sg < 0 else [at, a0, t, b0 - a0]
            out.append(band)
    out += [list(w) for w in lv['walls']]
    # walls never sit inside a room or inside a 'nowall' cut
    cuts = [r['r'] for r in rooms] + [list(n) for n in lv['nowall']]
    for c in cuts:
        nxt = []
        for w in out:
            nxt += rect_sub(w, c)
        out = nxt
    # merge exact duplicates
    seen, uniq = set(), []
    for w in out:
        k = tuple(round(v, 2) for v in w)
        if k not in seen:
            seen.add(k); uniq.append(w)
    return uniq


def opening_rect(o, d, lv):
    """2D rect an opening cuts through the wall band it sits in."""
    walls = walls_for(d, lv) if '_walls' not in lv else lv['_walls']
    a, b = min(o['a'], o['b']), max(o['a'], o['b'])
    # only a wall running the same way as the opening (thin across it) can hold it; a wall crossing the
    # opening end-on must never be picked, or the cut would wipe out that whole wall
    best, score = None, -1
    for w in walls:
        if o['o'] == 'h' and w[3] <= 13.5 and w[2] >= w[3] and w[1] - 0.6 <= o['at'] <= w[1] + w[3] + 0.6 and w[0] < b and w[0] + w[2] > a:
            ov = min(b, w[0] + w[2]) - max(a, w[0])
            if ov > score: best, score = [a, w[1], b - a, w[3]], ov
        if o['o'] == 'v' and w[2] <= 13.5 and w[3] >= w[2] and w[0] - 0.6 <= o['at'] <= w[0] + w[2] + 0.6 and w[1] < b and w[1] + w[3] > a:
            ov = min(b, w[1] + w[3]) - max(a, w[1])
            if ov > score: best, score = [w[0], a, w[2], b - a], ov
    return best


def on_wall(o, d, lv):
    return opening_rect(o, d, lv) is not None


# ---------------- areas ----------------
def walled_sides(r):
    return [s for s in 'nsew' if s not in r['open']] if r['k'] not in KINDS_OPEN else []


def room_areas(r):
    x, y, w, dd = r['r']
    ws = walled_sides(r)
    fw = w - PLASTER * (('e' in ws) + ('w' in ws)); fd = dd - PLASTER * (('n' in ws) + ('s' in ws))
    return {'brick': sqft(w * dd), 'fin': sqft(fw * fd), 'fw': fw, 'fd': fd,
            'perim': 2 * (fw + fd) - sum((fd if s in 'ew' else fw) for s in 'nsew' if s not in ws)}


def ceiling_h(d, lv, r):
    drop = r.get('false_ceiling', 12 if r['use'] in ('living', 'bed', 'master', 'dining') else 0)
    return lv['h'] - d['structure']['slab'] - drop


def openings_in(lv, r):
    """Doors/windows that sit on this room's edges (within the wall band)."""
    x, y, w, dd = r['r']; res = []
    for o in lv['doors'] + lv['windows']:
        a, b = min(o['a'], o['b']), max(o['a'], o['b'])
        if o['o'] == 'h' and (abs(o['at'] - y) <= 10 or abs(o['at'] - (y + dd)) <= 10) and a < x + w and b > x:
            res.append(o)
        if o['o'] == 'v' and (abs(o['at'] - x) <= 10 or abs(o['at'] - (x + w)) <= 10) and a < y + dd and b > y:
            res.append(o)
    return res


def facade(d, o):
    """Which outside face an opening is on ('S','N','E','W'), or None if internal."""
    W, D = d['building']['w'], d['building']['d']; te = d['structure']['wall_ext']
    if o['o'] == 'h':
        if o['at'] <= te + 1: return 'S'
        if o['at'] >= D - te - 1: return 'N'
    else:
        if o['at'] <= te + 1: return 'W'
        if o['at'] >= W - te - 1: return 'E'
    return None


def total_built(d):
    tot = 0
    W, D = d['building']['w'], d['building']['d']
    for lv in d['levels']:
        if lv.get('roof_level'):
            tot += sum(sqft(r['r'][2] * r['r'][3]) for r in lv['rooms'] if r['k'] not in KINDS_OPEN) * 1.12
            continue
        tot += sqft(W * D) - sum(sqft(r['r'][2] * r['r'][3]) for r in lv['rooms'] if r['k'] in KINDS_OPEN)
    return tot


# ---------------- 3D boxes ----------------
FIX_H = {'wc': 16, 'basin': 34, 'shower': 2, 'tub': 22, 'sink': 36, 'counter': 36, 'hob': 37, 'fridge': 70,
         'wm': 34, 'dw': 34, 'bed': 20, 'sofa': 32, 'table': 30, 'dtable': 30, 'chair': 34, 'wardrobe': 84,
         'tv': 30, 'desk': 30, 'shelf': 84, 'altar': 30, 'tank': 54, 'solar': 4, 'car': 66, 'ac': 12,
         'geyser': 20, 'plant': 30, 'rug': 0.5, 'cupboard': 84, 'vanity': 34, 'mirror': 30, 'rack': 60, 'skylight': 24}
FIX_Z = {'skylight': 18, 'ac': 84, 'geyser': 72, 'mirror': 42, 'tv': 30}
FIX_C = {'wc': 'san', 'basin': 'san', 'shower': 'glass', 'tub': 'san', 'sink': 'steel', 'counter': 'stone',
         'hob': 'dark', 'fridge': 'steel', 'wm': 'san', 'dw': 'steel', 'bed': 'fab', 'sofa': 'fab2',
         'table': 'wood', 'dtable': 'wood', 'chair': 'wood', 'wardrobe': 'wood2', 'tv': 'dark', 'desk': 'wood',
         'shelf': 'wood2', 'altar': 'stone', 'tank': 'dark', 'solar': 'pv', 'car': 'car', 'ac': 'san',
         'geyser': 'san', 'plant': 'green', 'rug': 'fab', 'cupboard': 'wood2', 'vanity': 'wood', 'mirror': 'glass',
         'rack': 'steel', 'skylight': 'glass'}


def beams_for(d, lv):
    """Plan rects of the beams under this level's ceiling: column to column along each grid line."""
    S = d['structure']; bw = S.get('beam', [9, 18])[0]; out = []
    cols = [c for c in S['columns'] if not c[2:] or lv['id'] in c[2]]
    for yv in sorted({c[1] for c in cols}):
        row = sorted(c[0] for c in cols if c[1] == yv)
        out += [[a_, yv - bw / 2, b_ - a_, bw] for a_, b_ in zip(row, row[1:])]
    for xv in sorted({c[0] for c in cols}):
        col_ = sorted(c[1] for c in cols if c[0] == xv)
        out += [[xv - bw / 2, a_, bw, b_ - a_] for a_, b_ in zip(col_, col_[1:])]
    return out


def boxes3d(d):
    """Flat list of boxes for the 3D viewer: dict(x,y,z,w,d,h,m,lv,k,id)."""
    S = d['structure']; W, D = d['building']['w'], d['building']['d']; B = []
    for li, lv in enumerate(d['levels']):
        z0 = lv['ffl']; H = lv['h']; lid = lv['id']
        walls = walls_for(d, lv); lv['_walls'] = walls
        roofl = lv.get('roof_level')
        wallH = H - S['slab']
        ops = []
        for o in lv['doors']:
            rr = opening_rect(o, d, lv)
            if rr: ops.append((rr, 0, min(o['h'], wallH), o, 'door'))
        for o in lv['windows']:
            rr = opening_rect(o, d, lv)
            if rr: ops.append((rr, o['sill'], min(o['head'], wallH), o, 'win'))
        for w in walls:
            horiz = w[2] >= w[3]
            ax = 0 if horiz else 1
            a0, a1 = w[ax], w[ax] + w[2 + ax]
            cuts = [op for op in ops if overlap(op[0], w)]
            pts = sorted({a0, a1, *[max(a0, min(a1, op[0][ax])) for op in cuts],
                          *[max(a0, min(a1, op[0][ax] + op[0][2 + ax])) for op in cuts]})
            for s0, s1 in zip(pts, pts[1:]):
                if s1 - s0 < 0.05: continue
                mid = (s0 + s1) / 2
                cov = [op for op in cuts if op[0][ax] <= mid <= op[0][ax] + op[0][2 + ax]]
                segs = [(0, wallH)]
                for op in cov:
                    nxt = []
                    for z_a, z_b in segs:
                        if op[2] <= z_a or op[1] >= z_b:
                            nxt.append((z_a, z_b)); continue
                        if op[1] > z_a: nxt.append((z_a, op[1]))
                        if op[2] < z_b: nxt.append((op[2], z_b))
                    segs = [s for s in nxt if s[1] - s[0] > 0.05]
                for z_a, z_b in segs:
                    bx = [s0, w[1], s1 - s0, w[3]] if horiz else [w[0], s0, w[2], s1 - s0]
                    B.append(dict(x=bx[0], y=bx[1], w=bx[2], d=bx[3], z=z0 + z_a, h=z_b - z_a,
                                  m='wall', lv=lid, k='wall'))
                for op in cov:
                    if op[4] == 'win':
                        t = op[0]
                        gx = [s0, t[1] + t[3] / 2 - 0.4, s1 - s0, 0.8] if horiz else [t[0] + t[2] / 2 - 0.4, s0, 0.8, s1 - s0]
                        B.append(dict(x=gx[0], y=gx[1], w=gx[2], d=gx[3], z=z0 + op[1], h=op[2] - op[1],
                                      m='glass', lv=lid, k='glass'))
        # floor slab (under this level): whole building minus voids/courts above ground
        if True:
            base = [[0, 0, W, D]]
            if li > 0:
                holes = [r['r'] for r in lv['rooms'] if r['k'] in KINDS_NOSLAB]
                holes += [r['r'] for r in d['levels'][li - 1]['rooms'] if r['k'] == 'stair']
                for hr in holes:
                    nb = []
                    for s_ in base: nb += rect_sub(s_, hr)
                    base = nb
            for s_ in base:
                B.append(dict(x=s_[0], y=s_[1], w=s_[2], d=s_[3], z=z0 - (S['slab'] if li else 6),
                              h=S['slab'] if li else 6, m='slab', lv=lid, k='slab'))
        for r in lv['rooms']:
            m = {'wet': 'tilew', 'deck': 'deck', 'terrace': 'deck', 'court': 'court', 'stair': 'stone'}.get(
                r['k'], r.get('floor', 'tile'))
            if r['k'] == 'void': continue
            B.append(dict(x=r['r'][0], y=r['r'][1], w=r['r'][2], d=r['r'][3], z=z0, h=0.4, m=m, lv=lid,
                          k='floor', id=r['id']))
            for side in r['rail']:
                o, at, a, b, sg = _edges(r)[side]
                bx = [a, at - 1, b - a, 2] if o == 'h' else [at - 1, a, 2, b - a]
                B.append(dict(x=bx[0], y=bx[1], w=bx[2], d=bx[3], z=z0, h=40, m='rail', lv=lid, k='rail'))
        if True:
            for c in S['columns']:
                if c[2:] and lid not in c[2]: continue
                cw, cd = S['col']
                B.append(dict(x=c[0] - cw / 2, y=c[1] - cd / 2, w=cw, d=cd, z=z0, h=H - S['slab'], m='col',
                              lv=lid, k='col'))
        for f in lv['fixtures']:
            r = f['r']; h = f.get('h', FIX_H.get(f['t'], 30)); z = z0 + f.get('z', FIX_Z.get(f['t'], 0))
            B.append(dict(x=r[0], y=r[1], w=r[2], d=r[3], z=z, h=h, m=f.get('m', FIX_C.get(f['t'], 'furn')),
                          lv=lid, k='fix', id=f['id'], t=f['t']))
            if f['t'] == 'shower':
                B.append(dict(x=r[0], y=r[1], w=r[2], d=r[3], z=z + 2, h=76, m='glass', lv=lid, k='fixg', id=f['id'] + '-screen'))
        for st in lv['stairs']:
            for fl in st.get('flights', []):
                x, y, w, dd = fl['r']; n = fl['n']; rise = st['rise']; dirn = fl['dir']; zb = z0 + fl.get('z', 0)
                for i in range(n):
                    if dirn in 'NS':
                        g = dd / n; yy = y + i * g if dirn == 'N' else y + dd - (i + 1) * g
                        B.append(dict(x=x, y=yy, w=w, d=g, z=zb, h=rise * (i + 1), m='stone', lv=lid, k='step'))
                    else:
                        g = w / n; xx = x + i * g if dirn == 'E' else x + w - (i + 1) * g
                        B.append(dict(x=xx, y=y, w=g, d=dd, z=zb, h=rise * (i + 1), m='stone', lv=lid, k='step'))
            for ld in st.get('landings', []):
                x, y, w, dd = ld['r']
                B.append(dict(x=x, y=y, w=w, d=dd, z=z0 + ld['z'] - 6, h=6, m='stone', lv=lid, k='step'))
    # beams: between neighbouring columns on the same grid line, under each slab (shown with 'Columns and beams')
    bd = S.get('beam', [9, 18])[1]
    for lv in d['levels']:
        if lv.get('roof_level'): continue
        zt = lv['ffl'] + lv['h'] - S['slab'] - bd
        for r_ in beams_for(d, lv):
            B.append(dict(x=r_[0], y=r_[1], w=r_[2], d=r_[3], z=zt, h=bd, m='beam', lv=lv['id'], k='beam'))
    # stacks: one pipe box per level it passes through, plus a vent above the top level
    for s_ in d['stacks']:
        lvls = [l for l in d['levels'] if l['id'] in s_.get('levels', [l['id'] for l in d['levels']])]
        sz = s_.get('box', [12, 12])
        for l in lvls:
            B.append(dict(x=s_['x'] - sz[0] / 2, y=s_['y'] - sz[1] / 2, w=sz[0], d=sz[1], z=l['ffl'], h=l['h'] - S['slab'],
                          m='duct', lv=l['id'], k='stack', id=s_['id']))
        if lvls:
            top = lvls[-1]; zt = top['ffl'] + top['h']
            B.append(dict(x=s_['x'] - 2, y=s_['y'] - 2, w=4, d=4, z=zt, h=24, m='dark', lv=top['id'], k='stack', id=s_['id'] + '-vent'))
    return B


def deep(d):
    return copy.deepcopy(d)
