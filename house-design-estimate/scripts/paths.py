"""Walkway check: furniture must not block the way to any door or stair.

A person is a disc of radius R walking on a 3" grid of the floor. Walls, columns, pipe boxes, voids and furniture that
stands on the floor are obstacles grown by R; a corridor straight through every doorway is kept open (doors are sized
by their own check), so only furniture can close it. Every doorway side and every stair is then searched from the main
door (ground floor) or the stair (upper floors).
  R = 15"  -> 750 mm clear path (furniture walkways, AS 1428-style comfort; warn when lost)
  R = 10"  -> 500 mm: nobody gets through (fail)
The same algorithm runs live in the design page while furniture is moved (viewer.js pathCheck).
"""
from collections import deque
from hdlib import opening_rect, walls_for, centre, overlap

G = 3.0
WALK_OK = 15.0      # 750 mm clear
WALK_MIN = 10.0     # 500 mm: blocked
# fixtures that do not block walking: floor finishes, shower trays (step-free), wall-hung or high items
NOBLOCK = {'rug', 'shower', 'skylight', 'solar', 'ac', 'geyser', 'mirror', 'tv', 'car'}


def _blocking(f):
    return f['t'] not in NOBLOCK and f.get('z', 0) < 36 and not f['t'].startswith('_')


def grid_for(d, lv, R, skip=()):
    W, D = d['building']['w'], d['building']['d']; S = d['structure']
    nx, ny = int(W / G) + 1, int(D / G) + 1
    free = [[False] * nx for _ in range(ny)]
    rooms = [r for r in lv['rooms'] if r['k'] not in ('void', 'roof')]
    for r in rooms:                                    # floor that exists
        x, y, w, dd = r['r']
        for j in range(max(0, int(y / G)), min(ny, int((y + dd) / G) + 1)):
            for i in range(max(0, int(x / G)), min(nx, int((x + w) / G) + 1)):
                cx, cy = i * G + G / 2, j * G + G / 2
                if x <= cx <= x + w and y <= cy <= y + dd: free[j][i] = True

    def block(rect, grow):
        x, y, w, dd = rect
        for j in range(max(0, int((y - grow) / G)), min(ny, int((y + dd + grow) / G) + 1)):
            for i in range(max(0, int((x - grow) / G)), min(nx, int((x + w + grow) / G) + 1)):
                cx, cy = i * G + G / 2, j * G + G / 2
                ex, ey = max(x - cx, 0, cx - x - w), max(y - cy, 0, cy - y - dd)      # rounded corners
                if ex * ex + ey * ey < grow * grow: free[j][i] = False

    def carve(rect):
        x, y, w, dd = rect
        for j in range(max(0, int(y / G)), min(ny, int((y + dd) / G) + 1)):
            for i in range(max(0, int(x / G)), min(nx, int((x + w) / G) + 1)):
                cx, cy = i * G + G / 2, j * G + G / 2
                if x <= cx <= x + w and y <= cy <= y + dd: free[j][i] = True

    walls = lv.get('_walls') or walls_for(d, lv)
    for w in walls: block(w, R)
    cw, cd = S['col']
    for c in S['columns']:
        if c[2:] and lv['id'] not in c[2]: continue
        block([c[0] - cw / 2, c[1] - cd / 2, cw, cd], R)
    for s_ in d['stacks']:
        if lv['id'] in s_.get('levels', [lv['id']]):
            b = s_.get('box', [12, 12]); block([s_['x'] - b[0] / 2, s_['y'] - b[1] / 2, b[0], b[1]], R)
    # keep a straight corridor through every doorway (its own width check lives elsewhere)
    targets = []
    for o in lv['doors']:
        rr = opening_rect(o, d, lv)
        if not rr: continue
        a, b = min(o['a'], o['b']), max(o['a'], o['b']); m = (a + b) / 2
        # the whole clear width of the doorway is open; a target is reached when any point across it is
        k = max(1, int((b - a - 2) / G))
        along = [a + 1 + (b - a - 2) * t / k for t in range(k + 1)]
        if o['o'] == 'h':
            carve([a, rr[1] - R - 3, b - a, rr[3] + 2 * R + 6]); sides = [[(u, rr[1] - R - 1) for u in along], [(u, rr[1] + rr[3] + R + 1) for u in along]]
        else:
            carve([rr[0] - R - 3, a, rr[2] + 2 * R + 6, b - a]); sides = [[(rr[0] - R - 1, u) for u in along], [(rr[0] + rr[2] + R + 1, u) for u in along]]
        for pts in sides:
            pts = [p for p in pts if 0 <= p[0] < W and 0 <= p[1] < D and any(r['r'][0] <= p[0] <= r['r'][0] + r['r'][2] and r['r'][1] <= p[1] <= r['r'][1] + r['r'][3] for r in rooms)]
            if pts: targets.append((o['id'], pts))
    fx = [f for f in lv['fixtures'] if _blocking(f) and f['id'] not in skip]
    for f in fx: block(f['r'], R)
    for r in lv['rooms']:
        if r['k'] == 'stair': targets.append((r['id'], [tuple(centre(r['r']))]))
    for st in lv['stairs']:                            # flights are walked on: keep them open
        for fl in st.get('flights', []): carve(fl['r'])
        for ld in st.get('landings', []): carve(ld['r'])
    return free, targets, (nx, ny)


def _reach(free, start, n):
    nx, ny = n; seen = [[False] * nx for _ in range(ny)]
    si, sj = int(start[0] / G), int(start[1] / G)
    # start from the nearest free cell
    best = None
    for rad in range(0, 12):
        for j in range(sj - rad, sj + rad + 1):
            for i in range(si - rad, si + rad + 1):
                if 0 <= i < nx and 0 <= j < ny and free[j][i]: best = (i, j); break
            if best: break
        if best: break
    if not best: return seen
    q = deque([best]); seen[best[1]][best[0]] = True
    while q:
        i, j = q.popleft()
        for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u, v = i + a, j + b
            if 0 <= u < nx and 0 <= v < ny and free[v][u] and not seen[v][u]:
                seen[v][u] = True; q.append((u, v))
    return seen


def _ok(seen, pts, n):
    return any(_ok1(seen, p, n) for p in pts)


def _ok1(seen, p, n):
    nx, ny = n; i, j = int(p[0] / G), int(p[1] / G)
    return any(0 <= i + a < nx and 0 <= j + b < ny and seen[j + b][i + a] for a in (-1, 0, 1) for b in (-1, 0, 1))


def check(d, lv, li):
    """List of (sev, target_id, blocker_ids) for doors/stairs that furniture cuts off."""
    res = []
    for sev, R in (('fail', WALK_MIN), ('warn', WALK_OK)):
        free, targets, n = grid_for(d, lv, R)
        if not targets: continue
        main = next((p[len(p) // 2] for (tid, p) in targets if li == 0 and any(o['id'] == tid and o['type'] == 'main' for o in lv['doors'])), None)
        start = main or next((p[0] for (tid, p) in targets if any(r['id'] == tid and r['k'] == 'stair' for r in lv['rooms'])), targets[0][1][0])
        seen = _reach(free, start, n)
        bad = [(tid, p) for (tid, p) in targets if not _ok(seen, p, n)]
        # without any furniture: if it is still cut off, it is the layout (walls), not furniture -> skip here
        free0, _, _ = grid_for(d, lv, R, skip={f['id'] for f in lv['fixtures']})
        seen0 = _reach(free0, start, n)
        for tid, p in bad:
            if any(tid == x[1] for x in res): continue
            if not _ok(seen0, p, n): continue
            # name the furniture: the pieces whose removal reopens the way
            q = p[len(p) // 2]
            cands = sorted([f for f in lv['fixtures'] if _blocking(f)], key=lambda f: abs(centre(f['r'])[0] - q[0]) + abs(centre(f['r'])[1] - q[1]))[:8]
            who = []
            for f in cands:
                fr, _, _ = grid_for(d, lv, R, skip={f['id']})
                if _ok(_reach(fr, start, n), p, n): who.append(f['id'])
            res.append((sev, tid, who))
    return res


def export(d, lv):
    """Data the design page needs to run the same check live while furniture is moved."""
    S = d['structure']; cw, cd = S['col']
    solids = [list(w) for w in (lv.get('_walls') or walls_for(d, lv))]
    solids += [[c[0] - cw / 2, c[1] - cd / 2, cw, cd] for c in S['columns'] if not c[2:] or lv['id'] in c[2]]
    for s_ in d['stacks']:
        if lv['id'] in s_.get('levels', [lv['id']]):
            b = s_.get('box', [12, 12]); solids.append([s_['x'] - b[0] / 2, s_['y'] - b[1] / 2, b[0], b[1]])
    doors = []
    for o in lv['doors']:
        rr = opening_rect(o, d, lv)
        if rr: doors.append(dict(id=o['id'], o=o['o'], a=min(o['a'], o['b']), b=max(o['a'], o['b']), rr=rr, main=o['type'] == 'main'))
    return dict(rooms=[r['r'] for r in lv['rooms'] if r['k'] not in ('void', 'roof')], solids=solids, doors=doors,
                stairs=[r['id'] for r in lv['rooms'] if r['k'] == 'stair'],
                stairRects={r['id']: r['r'] for r in lv['rooms'] if r['k'] == 'stair'},
                flights=[x['r'] for st in lv['stairs'] for x in st.get('flights', []) + st.get('landings', [])],
                noblock=sorted(NOBLOCK), roof=bool(lv.get('roof_level')))
