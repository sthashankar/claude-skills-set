#!/usr/bin/env python3
"""Build the single-file design page: 2D plan (left) + 3D model (right) + walk pane + detail tabs.
usage: build_design.py design.json out.html [--estimate-summary est_summary.json]
"""
import sys, os, json, html
from mep3d import extras3d
from hdlib import *
from plan2d import svg_level
import check_design as CK
import paths as PATHS

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, '..', 'templates')
E = html.escape
VASTU_ROW = ('Vastu Shastra', 'Zones (3×3 + 81 padas), room placement, main door pada, stair turn, Brahmasthan')
SEVC = {'fail': '#C0392B', 'warn': '#B4740E', 'info': '#3B6E8F', 'ok': '#3C8D4F'}
def room_card(d, lv, r, fs):
    a = room_areas(r); L = r.get('_light', {})
    rows = [('Size (finished)', f"{ftin(a['fw'])} × {ftin(a['fd'])}"), ('Area', f"{a['fin']:.0f} sq ft ({a['fin']*0.0929:.1f} m²)"),
            ('Brick to brick', f"{ftin(r['r'][2])} × {ftin(r['r'][3])}"), ('Ceiling', ftin(ceiling_h(d, lv, r)))]
    if L: rows.append(('Glazing / openable', f"{L.get('glaze_pct',0)}% / {L.get('open_pct',0)}% of floor"))
    if d['vastu'].get('enabled'): rows.append(('Vastu zone', CK.zone9(d, centre(r['r']))))
    mine = [f for f in fs if r['id'] in f['ids'] and f['sev'] != 'ok']
    li = ''.join(f"<li><b style='color:{SEVC[f['sev']]}'>{f['sev']}</b> {E(f['msg'])}</li>" for f in mine)
    return (f"<h3>{E(r['n'])} <small>{E(lv['name'])}</small></h3><table>" +
            ''.join(f"<tr><th>{k}</th><td>{E(str(v))}</td></tr>" for k, v in rows) + "</table>" +
            (f"<p>{E(r['note'])}</p>" if r.get('note') else '') + (f"<ul>{li}</ul>" if li else '') +
            f"<button data-walk='{r['id']}'>Walk inside this room</button>")


def findings_table(fs, cats=None, hide_ok=False):
    order = {'fail': 0, 'warn': 1, 'info': 2, 'ok': 3}
    sel = [f for f in fs if (cats is None or f['cat'] in cats) and not (hide_ok and f['sev'] == 'ok')]
    if not sel: return '<p class="muted">Nothing to report.</p>'
    return ('<table class="fs"><thead><tr><th>Result</th><th>Floor</th><th>Finding</th><th>Reference</th></tr></thead><tbody>' +
            ''.join(f"<tr><td><span class='sev' style='background:{SEVC[f['sev']]}'>{f['sev']}</span></td><td>{E(f['lv'] or '')}</td>"
                    f"<td>{E(f['msg'])}</td><td class='muted'>{E(f['ref'])}</td></tr>"
                    for f in sorted(sel, key=lambda f: (order[f['sev']], f['cat']))) + '</tbody></table>')


def build(d, est=None):
    fs = CK.run(d)
    B = boxes3d(d)
    X = extras3d(d); B += X['boxes']
    rooms = []
    for lv in d['levels']:
        for r in lv['rooms']:
            rooms.append(dict(id=r['id'], n=r['n'], k=r['k'], r=r['r'], ffl=lv['ffl'], lv=lv['id'], lvName=lv['name'],
                              card=room_card(d, lv, r, fs), use=r['use'], zone=CK.zone9(d, centre(r['r'])),
                              glaze=(r.get('_light') or {}).get('glaze_pct'), air=(r.get('_light') or {}).get('open_pct')))
    DATA = dict(project=dict(d['project'], codes=codes(d).get('name')), rcd=cite(d, 'rcd'), building=d['building'], levels=[dict(id=l['id'], name=l['name'], ffl=l['ffl'], h=l['h']) for l in d['levels']],
                boxes=[{k: (round(v, 2) if isinstance(v, float) else v) for k, v in b.items()} for b in B], rooms=rooms,
                doors=X['doors'], lights=X['lights'], fans=X['fans'],
                walk={lv['id']: PATHS.export(d, lv) for lv in d['levels']})
    svgs = '\n'.join(svg_level(d, lv, opts={'vastu': False, 'mep': X}).replace('<svg ', '<svg ' + ('' if i == 0 else 'style="display:none" '), 1)
                     for i, lv in enumerate(d['levels']))
    # ---------- tabs ----------
    built = total_built(d)
    cnt = {s: sum(1 for f in fs if f['sev'] == s) for s in SEVC}
    lvrows = ''.join(f"<tr><td>{E(l['name'])}</td><td>+{ftin(l['ffl'])}</td><td>{ftin(l['h'])}</td>"
                     f"<td>{sum(room_areas(r)['fin'] for r in l['rooms'] if r['k'] not in ('void',)):.0f}</td></tr>" for l in d['levels'])
    estline = ''   # never put prices on the design page: costs live only in the estimate file
    summary = (f"<p>{E(d['project'].get('brief',''))}</p>{estline}"
               f"<p class='big'>Built-up area <b>{built:,.0f} sq ft</b> · building {ftin(d['building']['w'])} × {ftin(d['building']['d'])} · "
               f"{len([l for l in d['levels'] if not l.get('roof_level')])} storeys + roof</p>"
               f"<p>Checks: <b style='color:{SEVC['fail']}'>{cnt['fail']} fail</b> · <b style='color:{SEVC['warn']}'>{cnt['warn']} warn</b> · "
               f"{cnt['info']} info · {cnt['ok']} ok. Fails must be fixed before drawings go to the engineer.</p>"
               f"<table><thead><tr><th>Level</th><th>FFL</th><th>Floor to floor</th><th>Room area (finished, sq ft)</th></tr></thead><tbody>{lvrows}</tbody></table>"
               f"<p class='muted'>Concept design for discussion. Structure, seismic design, MEP sizing and approval need {E(codes(d).get('professionals') or 'locally licensed professionals')}. Codes: {E(codes(d).get('name') or 'not given')}{' (SAMPLE, confirm)' if codes(d).get('_sample') else ''}. Location {E(d['project']['location']['city'])}; plan north = true north + {d['project'].get('north_deg',0)}°.</p>")
    sched = []
    for lv in d['levels']:
        for r in lv['rooms']:
            a = room_areas(r); L = r.get('_light', {})
            sched.append(f"<tr><td>{E(lv['name'])}</td><td>{E(r['n'])}</td><td>{ftin(a['fw'])} × {ftin(a['fd'])}</td><td>{a['fin']:.0f}</td>"
                         f"<td>{L.get('glaze_pct','')}</td><td>{L.get('open_pct','')}</td><td>{', '.join(L.get('faces',[]))}</td>"
                         f"<td>{CK.zone9(d, centre(r['r']))}</td></tr>")
    rooms_tab = ('<table><thead><tr><th>Floor</th><th>Room</th><th>Finished size</th><th>sq ft</th><th>Glazing %</th><th>Openable %</th>'
                 '<th>Opens to</th><th>Vastu zone</th></tr></thead><tbody>' + ''.join(sched) + '</tbody></table>')
    S = d['structure']
    struct_tab = (f"<p>Columns {S['col'][0]}×{S['col'][1]}\" ({len(S['columns'])} no.), beams {S['beam'][0]}×{S['beam'][1]}\", slab {S['slab']}\". "
                  f"Walls {S['wall_ext']}\" outer / {S['wall_int']}\" inner brick. Seismic: {E(', '.join(f'{k} = {v}' if k != 'code' else str(v) for k, v in seismic(d).items() if k in ('code', 'Z', 'soil', 'note')) or 'not given')}.</p>"
                  + findings_table(fs, {'struct'}))
    stk = []
    for s_ in d['stacks']:
        served = []
        for lv in d['levels']:
            for f in lv['fixtures']:
                if f.get('_drain', {}).get('stack') == s_['id']:
                    served.append(f"{lv['id']}: {f['t']} {f['_drain']['run_m']} m (drop {f['_drain']['depth_mm']} mm)")
        stk.append(f"<tr><td>{s_['id']}</td><td>{E(s_.get('n',''))}</td><td>{', '.join(s_.get('levels',[]))}</td><td>{'<br>'.join(served)}</td></tr>")
    gl = [f"{lv['id']}: {f['t']} {f['_drain']['run_m']} m to {f['_drain']['stack']} (drop {f['_drain']['depth_mm']} mm)"
          for lv in d['levels'] for f in lv['fixtures'] if f.get('_drain') and not any(s_['id'] == f['_drain']['stack'] for s_ in d['stacks'])]
    if gl: stk.append(f"<tr><td>Gully</td><td>Ground-floor fixtures draining straight out to a gully / inspection chamber</td><td>gf</td><td>{'<br>'.join(gl)}</td></tr>")
    exh = ''.join(f"<li>{E(e['room'])} → {E(e.get('via',''))}{(' → outlet ' + str(e['out'])) if e.get('out') else ''}</li>" for e in d['services'].get('exhaust', []))
    pts = ''.join(f"<li>{E(l['name'])}: {E(p['t'])} {E(p.get('n',''))}</li>" for l in d['levels'] for p in l['points'])
    svc_tab = ('<div id="eLeg" style="display:none" aria-live="polite"></div><h3>Soil and vent stacks</h3><table><thead><tr><th>Stack</th><th>What</th><th>Floors</th><th>Fixtures (pipe run, drop needed)</th></tr></thead><tbody>'
               + ''.join(stk) + f"</tbody></table><h3>Exhaust</h3><ul>{exh}</ul><h3>Electrical gear</h3><ul>{pts}</ul>"
               + findings_table(fs, {'mep'}))
    light_tab = ('<p>Use the sun slider above the 3D model to see shadows and sun patches for any month and hour at the site latitude.</p>'
                 + findings_table(fs, {'light', 'climate'}))
    vastu_tab = findings_table(fs, {'vastu'})
    std_tab = '<table><tbody>' + ''.join(f"<tr><th>{E(a)}</th><td>{E(b)}</td></tr>" for a, b in codes(d).get('standards', []) + ([VASTU_ROW] if d['vastu'].get('enabled') else [])) + '</tbody></table>' + findings_table(fs, {'safety'})
    log = ''.join(f"<tr><td>{E(x.get('date',''))}</td><td>{E(x.get('change',''))}</td><td>{E(x.get('impacts',''))}</td></tr>" for x in d.get('log', []))
    log_tab = ('<table><thead><tr><th>Date</th><th>Change</th><th>Impacts handled</th></tr></thead><tbody>' + log + '</tbody></table>') if log else '<p class="muted">No changes yet.</p>'
    tabs = [('sum', 'Summary', summary), ('rooms', 'Rooms', rooms_tab), ('checks', 'All checks', findings_table(fs, hide_ok=False)),
            ('struct', 'Structure', struct_tab), ('svc', 'Plumbing, electrical, exhaust', svc_tab), ('light', 'Light and air', light_tab),
            ('vastu', 'Vastu', vastu_tab), ('std', 'Standards and safety', std_tab), ('log', 'Change log', log_tab)]
    if not d['vastu'].get('enabled'): tabs = [t for t in tabs if t[0] != 'vastu']
    tabbar = ''.join(f"<button role='tab' data-tab='{k}' aria-selected='{str(i==0).lower()}'>{E(n)}</button>" for i, (k, n, _) in enumerate(tabs))
    panels = ''.join(f"<section class='dpanel' id='p_{k}' {'hidden' if i else ''}>{c}</section>" for i, (k, n, c) in enumerate(tabs))
    short = lambda n: n.replace(' floor', '').replace(' Floor', '')
    lvbtn = ''.join(f"<button data-lv='{l['id']}'><b>{E(short(l['name']))}</b><small>+{E(ftin(l['ffl']))}</small></button>" for l in d['levels'])
    lvbtn += "<button data-lv=''><b>All + roof</b><small>whole house</small></button>"
    road = (d['project'].get('road') or 'S')[0]
    opp = {'S': 'N', 'N': 'S', 'E': 'W', 'W': 'E'}; sides = [x for x in 'SNEW' if x not in (road, opp[road])]
    nm = {'S': 'South', 'N': 'North', 'E': 'East', 'W': 'West'}
    cambtn = (f"<button data-cam='front'><b>Front</b><small>from the road</small></button><button data-cam='back'><b>Back</b><small>from the garden</small></button>"
              + ''.join(f"<button data-cam='{x}'><b>{nm[x]}</b><small>side</small></button>" for x in sides)
              + "<button data-cam='top'><b>Top</b><small>bird's eye</small></button><button data-cam='iso'><b>3D</b><small>corner view</small></button>")
    elevbtn = ''.join(f"<button data-elev='{x}'><b>{nm[x]}</b><small>{'front' if x == road else 'back' if x == opp[road] else 'side'}</small></button>" for x in 'SNEW')
    page = open(os.path.join(TPL, 'design_page.html')).read()
    viewer = open(os.path.join(TPL, 'viewer.js')).read()
    wlv = ''.join(f"<button data-wlv='{l['id']}'>{E(l['name'])}</button>" for l in d['levels'])
    rep = {'{{WLVBTN}}': wlv, '{{TITLE}}': E(d['project']['name']), '{{LVBTN}}': lvbtn, '{{CAMBTN}}': cambtn, '{{ELEVBTN}}': elevbtn, '{{CITY}}': E(d['project']['location'].get('city', '').split(',')[0]), '{{SVGS}}': svgs, '{{TABBAR}}': tabbar, '{{PANELS}}': panels,
           '{{DATA}}': json.dumps(DATA, separators=(',', ':')).replace('</', '<\\/'), '{{VIEWER}}': viewer,
           '{{SUB}}': E(f"{d['project']['location']['city']} · {ftin(d['building']['w'])} × {ftin(d['building']['d'])} · {built:,.0f} sq ft built-up")}
    for k, v in rep.items(): page = page.replace(k, v)
    return page, fs


if __name__ == '__main__':
    a = sys.argv
    d = load(a[1]); est = None
    try: require_intake(d)
    except IntakeError as e: sys.exit(str(e))
    if '--estimate-summary' in a:
        est = json.load(open(a[a.index('--estimate-summary') + 1]))
    page, fs = build(d, est)
    open(a[2], 'w').write(page)
    print('wrote', a[2], '·', CK.summary(fs))
