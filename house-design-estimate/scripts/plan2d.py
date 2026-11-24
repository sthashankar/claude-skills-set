"""2D plan SVG for one level. North is up. Used by build_design.py and preview.py."""
import math, html
from hdlib import walls_for, opening_rect, room_areas, ftin, KINDS_OPEN, centre, beams_for, seismic

FILL = {'room': '#FFFFFF', 'wet': '#DAE7EB', 'stair': '#ECE8F3', 'deck': '#F0E8D8', 'terrace': '#ECEFE0',
        'court': '#E0EBD3', 'void': '#FFF6C8', 'roof': '#F2F2EE', 'yard': '#E3EFD9'}
USEFILL = {'kitchen': '#FBEFE4', 'puja': '#F9E6F1', 'store': '#F3F0E8', 'laundry': '#E4EEF0'}
FIXLBL = {'wc': 'WC', 'basin': 'B', 'shower': 'SH', 'tub': 'TUB', 'sink': 'SINK', 'hob': 'HOB', 'fridge': 'FR',
          'wm': 'WM', 'dw': 'DW', 'tv': 'TV', 'wardrobe': 'WARD', 'shelf': 'SHELF', 'altar': 'ALTAR', 'ac': 'AC',
          'geyser': 'GY', 'vanity': 'VAN', 'tank': 'TANK', 'solar': 'PV', 'desk': 'DESK', 'skylight': 'SKYLIGHT',
          'dtable': 'TABLE', 'table': 'T', 'cupboard': 'CUP', 'rack': 'RACK', 'mirror': 'M', 'plant': '✿'}


def svg_level(d, lv, hl=(), opts=None):
    o = dict(vastu=False, dims=True, labels=True, furn=True, services=True, cols=True, scale=1.0, title=True)
    o.update(opts or {})
    W, D = d['building']['w'], d['building']['d']
    m = 92
    Y = lambda y: D - y                      # flip: north up
    out = []
    ap = out.append
    vb = f"{-m} {-m - 30} {W + 2 * m} {D + 2 * m + 40}"
    ap(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" data-level="{lv["id"]}" '
       f'style="font-family:Barlow,Arial,sans-serif;background:#F8F9F6">')
    ap('<defs><pattern id="hx" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
       '<line x1="0" y1="0" x2="0" y2="6" stroke="#B8C4C8" stroke-width="1"/></pattern></defs>')
    if o['title']:
        ap(f'<text x="{W/2}" y="{-m - 8}" text-anchor="middle" font-size="20" font-weight="600" fill="#1C282D">'
           f'{lv["name"]}  ·  FFL +{ftin(lv["ffl"])}</text>')
    # rooms
    for r in lv['rooms']:
        x, y, w, dd = r['r']
        f = USEFILL.get(r['use'], FILL.get(r['k'], '#FFF'))
        cls = 'room hl' if r['id'] in hl else 'room'
        ap(f'<rect class="{cls}" data-room="{r["id"]}" data-fill="{f}" x="{x}" y="{Y(y+dd)}" width="{w}" height="{dd}" fill="{f}" '
           f'stroke="#C9D0CA" stroke-width="0.6"/>')
        if r['k'] == 'void':
            ap(f'<line x1="{x}" y1="{Y(y)}" x2="{x+w}" y2="{Y(y+dd)}" stroke="#C9B85A" stroke-width=".8"/>'
               f'<line x1="{x}" y1="{Y(y+dd)}" x2="{x+w}" y2="{Y(y)}" stroke="#C9B85A" stroke-width=".8"/>')
    # stairs
    for st in lv['stairs']:
        for fl in st.get('flights', []):
            x, y, w, dd = fl['r']; n = fl['n']
            for i in range(1, n):
                if fl['dir'] in 'NS':
                    yy = y + dd * i / n
                    ap(f'<line x1="{x}" y1="{Y(yy)}" x2="{x+w}" y2="{Y(yy)}" stroke="#7A7F8C" stroke-width=".7"/>')
                else:
                    xx = x + w * i / n
                    ap(f'<line x1="{xx}" y1="{Y(y)}" x2="{xx}" y2="{Y(y+dd)}" stroke="#7A7F8C" stroke-width=".7"/>')
            ap(f'<rect x="{x}" y="{Y(y+dd)}" width="{w}" height="{dd}" fill="none" stroke="#7A7F8C" stroke-width=".9"/>')
            cx, cy = x + w / 2, y + dd / 2
            vec = {'N': (0, 1), 'S': (0, -1), 'E': (1, 0), 'W': (-1, 0)}[fl['dir']]
            L = (dd if fl['dir'] in 'NS' else w) * 0.38
            x1, y1, x2, y2 = cx - vec[0] * L, cy - vec[1] * L, cx + vec[0] * L, cy + vec[1] * L
            ap(f'<line x1="{x1}" y1="{Y(y1)}" x2="{x2}" y2="{Y(y2)}" stroke="#B4740E" stroke-width="1.4" '
               f'marker-end="url(#ar)"/>')
            ap(f'<text x="{cx}" y="{Y(cy)+4}" font-size="9" fill="#5A686D" text-anchor="middle" '
               f'transform="rotate({-90 if fl["dir"] in "NS" else 0} {cx} {Y(cy)})">UP {n}R</text>')
        for ld in st.get('landings', []):
            x, y, w, dd = ld['r']
            ap(f'<rect x="{x}" y="{Y(y+dd)}" width="{w}" height="{dd}" fill="#E4DFEE" stroke="#7A7F8C" stroke-width=".8"/>')
    ap('<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
       '<path d="M0,0 L10,5 L0,10 z" fill="#B4740E"/></marker></defs>')
    # furniture / fixtures
    if o['furn']:
        for f in lv['fixtures']:
            x, y, w, dd = f['r']
            c = '#E7F1F5' if f['t'] in ('wc', 'basin', 'shower', 'tub', 'sink', 'wm', 'vanity', 'geyser') else '#F0F2EE'
            cls = ' hl' if f['id'] in hl else ''
            dash = ' stroke-dasharray="3 2"' if f['t'] in ('geyser', 'ac', 'solar', 'skylight', 'mirror') else ''
            ap(f'<g class="fx fu" data-fx="{f["id"]}">')
            ap(f'<rect class="fx{cls}" data-fix="{f["id"]}" x="{x}" y="{Y(y+dd)}" width="{w}" height="{dd}" fill="{c}" '
               f'stroke="#6E7D83" stroke-width=".8"{dash}/>')
            if f['t'] == 'wc':
                ap(f'<ellipse cx="{x+w/2}" cy="{Y(y+dd/2)}" rx="{w*0.36}" ry="{dd*0.36}" fill="none" stroke="#6E7D83" stroke-width=".7"/>')
            if f['t'] == 'shower':
                ap(f'<line x1="{x}" y1="{Y(y)}" x2="{x+w}" y2="{Y(y+dd)}" stroke="#6FAECB" stroke-width=".6"/>'
                   f'<line x1="{x}" y1="{Y(y+dd)}" x2="{x+w}" y2="{Y(y)}" stroke="#6FAECB" stroke-width=".6"/>')
            if f['t'] == 'wardrobe' and f.get('slide') is not False:     # sliding doors: two staggered tracks on the room side
                rr_ = next((r for r in lv['rooms'] if r['r'][0] <= x + w / 2 <= r['r'][0] + r['r'][2] and r['r'][1] <= y + dd / 2 <= r['r'][1] + r['r'][3]), None)
                if rr_:
                    rx, ry, rw_, rd = rr_['r']; bk = min({'s': y - ry, 'n': ry + rd - y - dd, 'w': x - rx, 'e': rx + rw_ - x - w}.items(), key=lambda t: t[1])[0]
                    if bk in 'sn':
                        fy = y + dd if bk == 's' else y
                        ap(f'<path d="M{x+2},{Y(fy)-1.5}H{x+w*.55}M{x+w*.45},{Y(fy)+1.5}H{x+w-2}" stroke="#3A3F44" stroke-width="1.3" fill="none"/>')
                    else:
                        fx = x + w if bk == 'w' else x
                        ap(f'<path d="M{fx-1.5},{Y(y+2)}V{Y(y+dd*.55)}M{fx+1.5},{Y(y+dd*.45)}V{Y(y+dd-2)}" stroke="#3A3F44" stroke-width="1.3" fill="none"/>')
            if f['t'] == 'bed':
                ap(f'<rect x="{x+3}" y="{Y(y+dd)+3}" width="{min(w,dd)*0.25 if w>dd else w-6}" height="{dd-6 if w>dd else min(w,dd)*0.25}" '
                   f'fill="#fff" stroke="#9AA6AA" stroke-width=".5"/>')
            lbl = f.get('lbl', FIXLBL.get(f['t'], ''))
            if lbl and min(w, dd) >= 12:
                fs = max(6, min(10, min(w, dd) / 2.6))
                ap(f'<text x="{x+w/2}" y="{Y(y+dd/2)+fs/3}" font-size="{fs}" fill="#5A686D" text-anchor="middle">{lbl}</text>')
            if o['dims'] and min(w, dd) >= 20 and f['t'] not in ('rug',):
                fs2 = max(4.5, min(6.5, min(w, dd) / 5)); ty = Y(y + dd / 2) + (fs2 * 1.9 if lbl and min(w, dd) >= 12 else fs2 / 3)
                ap(f'<text class="dims" x="{x+w/2}" y="{ty:.1f}" font-size="{fs2:.1f}" fill="#8B5A0C" text-anchor="middle">{ftin(w)} × {ftin(dd)}</text>')
            ap('</g>')
    # columns
    S = d['structure']
    if o['cols']:
        cw, cd = S['col']
        for c in S['columns']:
            if c[2:] and lv['id'] not in c[2]: continue
            ap(f'<rect class="colm" x="{c[0]-cw/2}" y="{Y(c[1]+cd/2)}" width="{cw}" height="{cd}" fill="#1C282D"/>')
    # walls (on top of rooms), then openings cut
    walls = walls_for(d, lv); lv['_walls'] = walls
    for w in walls:
        ap(f'<rect x="{w[0]}" y="{Y(w[1]+w[3])}" width="{w[2]}" height="{w[3]}" fill="#2B3940"/>')
    for r in lv['rooms']:
        for side in r['rail']:
            x, y, w, dd = r['r']
            seg = {'s': (x, y, x + w, y), 'n': (x, y + dd, x + w, y + dd), 'w': (x, y, x, y + dd), 'e': (x + w, y, x + w, y + dd)}[side]
            ap(f'<line x1="{seg[0]}" y1="{Y(seg[1])}" x2="{seg[2]}" y2="{Y(seg[3])}" stroke="#2B3940" stroke-width="2.2" stroke-dasharray="6 3"/>')
    for op in lv['doors']:
        rr = opening_rect(op, d, lv)
        if not rr: continue
        hlc = ' class="hl"' if op['id'] in hl else ''
        ap(f'<rect{hlc} x="{rr[0]}" y="{Y(rr[1]+rr[3])}" width="{rr[2]}" height="{rr[3]}" fill="#F8F9F6"/>')
        a, b = min(op['a'], op['b']), max(op['a'], op['b'])
        if op['type'] in ('arch', 'opening'):
            continue
        if op['type'] == 'slide':
            if op['o'] == 'h':
                ap(f'<line x1="{a}" y1="{Y(op["at"]-1)}" x2="{(a+b)/2+4}" y2="{Y(op["at"]-1)}" stroke="#3d4a52" stroke-width="1.6"/>'
                   f'<line x1="{(a+b)/2-4}" y1="{Y(op["at"]+1)}" x2="{b}" y2="{Y(op["at"]+1)}" stroke="#3d4a52" stroke-width="1.6"/>')
            else:
                ap(f'<line x1="{op["at"]-1}" y1="{Y(a)}" x2="{op["at"]-1}" y2="{Y((a+b)/2+4)}" stroke="#3d4a52" stroke-width="1.6"/>'
                   f'<line x1="{op["at"]+1}" y1="{Y((a+b)/2-4)}" x2="{op["at"]+1}" y2="{Y(b)}" stroke="#3d4a52" stroke-width="1.6"/>')
            continue
        L = b - a; hinge = a if op['hg'] == 'a' else b; free = b if op['hg'] == 'a' else a
        sgn = op['dir']
        face = (rr[1] + rr[3]) if (op['o'] == 'h' and sgn > 0) else rr[1] if op['o'] == 'h' else \
               (rr[0] + rr[2]) if sgn > 0 else rr[0]
        if op['o'] == 'h':
            hx, hy = hinge, face; lx, ly = hinge, face + sgn * L; fx, fy = free, face
        else:
            hx, hy = face, hinge; lx, ly = face + sgn * L, hinge; fx, fy = face, free
        sweep = 1 if ((op['o'] == 'h') == ((op['hg'] == 'a') == (sgn > 0))) else 0
        ap(f'<line x1="{hx}" y1="{Y(hy)}" x2="{lx}" y2="{Y(ly)}" stroke="#3d4a52" stroke-width="1.4"/>'
           f'<path d="M{lx},{Y(ly)} A{L},{L} 0 0 {sweep} {fx},{Y(fy)}" fill="none" stroke="#8A979C" stroke-width=".7" stroke-dasharray="3 2"/>')
    for op in lv['windows']:
        rr = opening_rect(op, d, lv)
        if not rr: continue
        hlc = ' class="hl"' if op['id'] in hl else ''
        ap(f'<rect{hlc} x="{rr[0]}" y="{Y(rr[1]+rr[3])}" width="{rr[2]}" height="{rr[3]}" fill="#fff" stroke="#2B3940" stroke-width=".6"/>')
        if op['o'] == 'h':
            cy = rr[1] + rr[3] / 2
            ap(f'<line x1="{rr[0]}" y1="{Y(cy)}" x2="{rr[0]+rr[2]}" y2="{Y(cy)}" stroke="#6FAECB" stroke-width="2"/>')
        else:
            cx = rr[0] + rr[2] / 2
            ap(f'<line x1="{cx}" y1="{Y(rr[1])}" x2="{cx}" y2="{Y(rr[1]+rr[3])}" stroke="#6FAECB" stroke-width="2"/>')
    # services: stacks, points
    if o['services']:
        for s_ in d['stacks']:
            if lv['id'] not in s_.get('levels', [lv['id']]): continue
            bw, bd = s_.get('box', [12, 12]); cls = ' class="hl"' if s_['id'] in hl else ''
            ap(f'<rect{cls} x="{s_["x"]-bw/2}" y="{Y(s_["y"]+bd/2)}" width="{bw}" height="{bd}" fill="#C8B59A" stroke="#6b4f2a" stroke-width=".8"/>'
               f'<circle cx="{s_["x"]}" cy="{Y(s_["y"])}" r="2.5" fill="#6b4f2a"/>'
               f'<text x="{s_["x"]}" y="{Y(s_["y"]-bd/2)+9}" font-size="7" text-anchor="middle" fill="#6b4f2a">{s_["id"]}</text>')
        for p in lv['points']:
            ap(f'<g><rect x="{p["x"]-7}" y="{Y(p["y"])-5}" width="14" height="10" rx="2" fill="#5B3E8E"/>'
               f'<text x="{p["x"]}" y="{Y(p["y"])+3}" font-size="6.5" fill="#fff" text-anchor="middle">{p["t"]}</text></g>')
    # beams (dashed, as in a structural layout) + column tags, shown with 'Columns and beams'
    if not lv.get('roof_level'):
        bm = ''.join(f'<rect x="{b[0]}" y="{Y(b[1]+b[3])}" width="{b[2]}" height="{b[3]}" fill="#B5574B" fill-opacity=".18" stroke="#B5574B" stroke-width=".9" stroke-dasharray="5 3"/>'
                     for b in beams_for(d, lv))
        cw, cd = S['col']; n = 0; tags = ''
        for c in S['columns']:
            if c[2:] and lv['id'] not in c[2]: continue
            n += 1; tags += f'<text x="{c[0]+cw/2+2}" y="{Y(c[1]+cd/2)-2}" font-size="6.5" fill="#B5574B">C{n}</text>'
        bwd = S.get('beam', [9, 18])
        seis = seismic(d).get('code'); seis = f' ({html.escape(str(seis))})' if seis else ''
        tags += f'<text x="0" y="{D+70}" font-size="8" fill="#B5574B">Columns {ftin(cw)} × {ftin(cd)} · beams {ftin(bwd[0])} × {ftin(bwd[1])} deep (dashed) · concept only, sizes by the engineer{seis}</text>'
        ap(f'<g class="beams" style="display:none">{bm}{tags}</g>')
    # services layers (hidden until the plumbing / wiring / exhaust boxes are ticked)
    if o.get('mep'):
        ap(svc_svg(o['mep'], lv['id'], Y, lv is d['levels'][0]))
    # light and air badges (from check_design: glazing and openable % of floor area)
    la = []
    for r in lv['rooms']:
        L_ = r.get('_light')
        if not L_ or r['k'] in ('void', 'court', 'deck', 'terrace', 'roof', 'stair'): continue
        x, y, w, dd = r['r']
        if w < 40 or dd < 36: continue
        g_, a_ = L_['glaze_pct'], L_['open_pct']
        col = '#2B7A3D' if g_ >= 15 else '#B4740E' if g_ >= 10 else '#C92A2A'
        cx, cy = centre(r['r'])
        la.append(f'<g><rect x="{cx-26}" y="{Y(cy)-34}" width="52" height="14" rx="3" fill="#fff" stroke="{col}" stroke-width=".8"/>'
                  f'<text x="{cx}" y="{Y(cy)-24}" font-size="7" fill="{col}" text-anchor="middle">☀ {g_:.0f}% · air {a_:.0f}%</text></g>')
    ap('<g class="la" style="display:none">' + ''.join(la) + '</g>')
    # labels
    if o['labels']:
        for r in lv['rooms']:
            x, y, w, dd = r['r']
            if w < 30 or dd < 24: continue
            a = room_areas(r)
            cx, cy = r.get('lp', centre(r['r']))
            nm = r.get('short', r['n'])
            fs = 11 if min(w, dd) > 60 else 8.5
            fs = min(fs, (w - 6) / max(1, len(nm) * 0.55))
            ap(f'<text x="{cx}" y="{Y(cy)-2}" font-size="{fs}" font-weight="600" fill="#1C282D" text-anchor="middle" '
               f'pointer-events="none">{nm}</text>')
            if o['dims'] and r['k'] not in ('void',) and min(w, dd) > 40:
                fs = min(11, (w - 6) / 9) if min(w, dd) > 60 else min(8.5, (w - 6) / 9)
                ap(f'<text class="dims" x="{cx}" y="{Y(cy)+fs}" font-size="{fs*0.8}" fill="#8B5A0C" text-anchor="middle" pointer-events="none">'
                   f'{ftin(a["fw"])} × {ftin(a["fd"])}</text>')
    # dims: opening chain, room chain and overall size on all four faces + width tag on every door and window
    if o['dims']:
        ap(dims_svg(d, lv, Y))
    # vastu 3x3 grid
    ap('<g class="vastu" style="display:' + ('inline' if o['vastu'] else 'none') + '">')
    for i in (1, 2):
        ap(f'<line x1="{W*i/3}" y1="0" x2="{W*i/3}" y2="{D}" stroke="#C0392B" stroke-width=".8" stroke-dasharray="5 4"/>'
           f'<line x1="0" y1="{Y(D*i/3)}" x2="{W}" y2="{Y(D*i/3)}" stroke="#C0392B" stroke-width=".8" stroke-dasharray="5 4"/>')
    for (zx, zy, nm) in [(0, 2, 'NW'), (1, 2, 'N'), (2, 2, 'NE'), (0, 1, 'W'), (1, 1, 'Brahma'), (2, 1, 'E'),
                         (0, 0, 'SW'), (1, 0, 'S'), (2, 0, 'SE')]:
        ap(f'<text x="{W*(zx+.5)/3}" y="{Y(D*(zy+1)/3)+14}" font-size="11" fill="#C0392B" text-anchor="middle" opacity=".7">{nm}</text>')
    ap('</g>')
    # north arrow (true north)
    nd = d['project'].get('north_deg', 0)
    ap(f'<g transform="translate({-40},{-m+10}) rotate({nd})"><path d="M0,-16 L7,10 L0,5 L-7,10 z" fill="#1C282D"/>'
       f'<text x="0" y="-20" font-size="11" text-anchor="middle" font-weight="700">N</text></g>')
    ap(f'<text x="{W/2}" y="{-m+12}" font-size="10" fill="#5A686D" text-anchor="middle">Road: {d["project"].get("road","S")} side</text>')
    ap('<style>.hl{stroke:#E8590C!important;stroke-width:3!important;fill-opacity:.9}.room{cursor:pointer}'
       '.room:hover{fill:#FFF3DC}</style>')
    ap('</svg>')
    return '\n'.join(out)


SVC_COL = {'rwp': '#1098AD', 'plumb': '#7E878C', 'cold': '#2F7FD0', 'hot': '#D0462F', 'tankx': '#55626B', 'wire': '#E0A100',
           'elec': '#8A5A00', 'exh': '#7FA7B8', 'exhfan': '#3F7486'}
SVC_LAYER = {'rwp': 'plumb', 'plumb': 'plumb', 'cold': 'plumb', 'hot': 'plumb', 'tankx': 'plumb', 'wire': 'wire', 'elec': 'wire',
             'exh': 'exh', 'exhfan': 'exh'}


def svc_svg(X, lid, Y, first):
    """2D services drawn from the same runs as the 3D (mep3d.extras3d), one <g> per layer."""
    g = {'plumb': [], 'wire': [], 'exh': []}
    for b in X['boxes']:
        lay = SVC_LAYER.get(b['k'])
        if not lay or not (b['lv'] == lid or (b['lv'] == '*' and first)): continue
        w, dd = max(b['w'], 1.2), max(b['d'], 1.2)
        da = (f' data-cct="{b["cct"]}" data-sw="{b.get("sw", "")}"' if b.get('cct') else '') + (f' data-what="{b["what"]}"' if b.get('what') else '')
        if b['k'] in ('tankx', 'elec', 'exhfan'):
            g[lay].append(f'<rect x="{b["x"]:.1f}" y="{Y(b["y"]+dd):.1f}" width="{w:.1f}" height="{dd:.1f}" fill="{SVC_COL[b["k"]]}" '
                          f'fill-opacity=".85" stroke="#fff" stroke-width=".4"{da}/>')
        else:
            g[lay].append(f'<rect x="{b["x"]:.1f}" y="{Y(b["y"]+dd):.1f}" width="{w:.1f}" height="{dd:.1f}" fill="{SVC_COL[b["k"]]}"{da}/>')
    for L in X['lights']:
        if L['lv'] != lid: continue
        g['wire'].append(f'<g stroke="#8A5A00" stroke-width=".8" fill="#FFF4C8" data-cct="{L.get("cct", "")}" data-sw="{L.get("sw", "")}"><circle cx="{L["x"]:.1f}" cy="{Y(L["y"]):.1f}" r="5"/>'
                         f'<path d="M{L["x"]-3.5:.1f},{Y(L["y"])-3.5:.1f}l7,7M{L["x"]-3.5:.1f},{Y(L["y"])+3.5:.1f}l7,-7" fill="none"/></g>')
    for F in X['fans']:
        if F['lv'] != lid: continue
        g['wire'].append(f'<g stroke="#8A5A00" stroke-width=".8" fill="none" data-cct="{F.get("cct", "")}" data-sw="{F.get("sw", "")}"><circle cx="{F["x"]:.1f}" cy="{Y(F["y"]):.1f}" r="9"/>'
                         f'<text x="{F["x"]:.1f}" y="{Y(F["y"])+3:.1f}" font-size="8" fill="#8A5A00" stroke="none" text-anchor="middle">F</text></g>')
    names = {'plumb': 'plumbing', 'wire': 'wiring', 'exh': 'exhaust'}
    return ''.join(f'<g class="svc svc-{k}" data-layer="{names[k]}" style="display:none">{"".join(v)}</g>' for k, v in g.items())


def _chain(ticks, face, off, W, D, Y, col='#8B5A0C'):
    """One dimension chain along a face: ticks in plan units along the face, off = distance out from the wall."""
    t = sorted({round(v, 2) for v in ticks}); out = []
    if len(t) < 2: return ''
    if face in 'SN':
        yy = D + off if face == 'S' else -off
        out.append(f'<line x1="{t[0]}" y1="{yy}" x2="{t[-1]}" y2="{yy}"/>')
        for v in t: out.append(f'<line x1="{v-2.5}" y1="{yy+2.5}" x2="{v+2.5}" y2="{yy-2.5}" stroke-width="1"/>')
        for a, b in zip(t, t[1:]):
            if b - a >= 16: out.append(f'<text x="{(a+b)/2}" y="{yy-2.5}" text-anchor="middle" stroke="none">{ftin(b-a)}</text>')
    else:
        xx = -off if face == 'W' else W + off
        out.append(f'<line x1="{xx}" y1="{Y(t[0])}" x2="{xx}" y2="{Y(t[-1])}"/>')
        for v in t: out.append(f'<line x1="{xx-2.5}" y1="{Y(v)+2.5}" x2="{xx+2.5}" y2="{Y(v)-2.5}" stroke-width="1"/>')
        for a, b in zip(t, t[1:]):
            if b - a >= 16:
                cy = Y((a + b) / 2); out.append(f'<text x="{xx-2.5}" y="{cy}" text-anchor="middle" stroke="none" transform="rotate(-90 {xx-2.5} {cy})">{ftin(b-a)}</text>')
    return ''.join(out)


def dims_svg(d, lv, Y):
    W, D = d['building']['w'], d['building']['d']; S = d['structure']; te = S['wall_ext'] + 3
    out = [f'<g class="dims" stroke="#8B5A0C" stroke-width=".6" fill="#8B5A0C" font-size="7.5">']
    rooms = [r for r in lv['rooms'] if r['k'] != 'void']
    for face in 'SNWE':
        # openings in the outer wall of this face
        ops = []
        for op in lv['doors'] + lv['windows']:
            rr = opening_rect(op, d, lv)
            if not rr: continue
            a, b = min(op['a'], op['b']), max(op['a'], op['b'])
            if face == 'S' and op['o'] == 'h' and rr[1] < te: ops += [a, b]
            if face == 'N' and op['o'] == 'h' and rr[1] + rr[3] > D - te: ops += [a, b]
            if face == 'W' and op['o'] == 'v' and rr[0] < te: ops += [a, b]
            if face == 'E' and op['o'] == 'v' and rr[0] + rr[2] > W - te: ops += [a, b]
        L = W if face in 'SN' else D
        if ops: out.append(_chain([0, L] + ops, face, 16, W, D, Y))
        # rooms along this face
        rt = []
        for r in rooms:
            x, y, w, dd = r['r']
            if face == 'S' and y < te: rt += [x, x + w]
            if face == 'N' and y + dd > D - te: rt += [x, x + w]
            if face == 'W' and x < te: rt += [y, y + dd]
            if face == 'E' and x + w > W - te: rt += [y, y + dd]
        rt = [v for v in rt if v > te or v < 0.5] + [0, L]
        out.append(_chain([v if not (0 < v < te) else 0 for v in rt], face, 34, W, D, Y))
        out.append(_chain([0, L], face, 52, W, D, Y).replace('font-size', 'font-weight="600" font-size'))
    # width tag on every door and window, on the inside of its wall
    for op in lv['doors'] + lv['windows']:
        rr = opening_rect(op, d, lv)
        if not rr: continue
        a, b = min(op['a'], op['b']), max(op['a'], op['b']); m_ = (a + b) / 2
        isd = op in lv['doors']; tag = ('D ' if isd else 'W ') + ftin(b - a)
        if op['o'] == 'h':
            inside = 1 if rr[1] + rr[3] / 2 < D / 2 else -1
            yy = (rr[1] + rr[3] + 7) if inside > 0 else (rr[1] - 7)
            out.append(f'<text x="{m_}" y="{Y(yy)+2.5}" text-anchor="middle" stroke="none" font-size="6.5" fill="{"#7A4B0A" if isd else "#2F6F8F"}">{tag}</text>')
        else:
            inside = 1 if rr[0] + rr[2] / 2 < W / 2 else -1
            xx = (rr[0] + rr[2] + 6) if inside > 0 else (rr[0] - 4)
            out.append(f'<text x="{xx}" y="{Y(m_)}" text-anchor="middle" stroke="none" font-size="6.5" fill="{"#7A4B0A" if isd else "#2F6F8F"}" '
                       f'transform="rotate(-90 {xx} {Y(m_)})">{tag}</text>')
    out.append('</g>')
    return ''.join(out)
