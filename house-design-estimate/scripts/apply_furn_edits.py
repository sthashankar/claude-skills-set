"""Apply the 'Copy my changes' output of the design page's Move furniture tool to a design JSON.

usage: apply_furn_edits.py design.json changes.json proposed.json
changes.json = {"furniture_changes": [{"id": "gf-sofa3", "r": [x, y, w, d]}, {"id": "ff-chair7", "delete": true}]}
Then run impact.py / preview.py on design.json vs proposed.json and apply_change.py after the user confirms.
Every fixture keeps an explicit id when saved, so removing one does not shift the ids of the others.
"""
import sys, json
from hdlib import load, save
d = load(sys.argv[1]); ch = json.load(open(sys.argv[2])).get('furniture_changes', [])
byid = {f['id']: f for lv in d['levels'] for f in lv['fixtures']}
for c in ch:
    f = byid.get(c['id'])
    if not f: print('not found:', c['id']); continue
    if c.get('delete'):
        for lv in d['levels']:
            if f in lv['fixtures']: lv['fixtures'].remove(f)
        print('deleted', c['id'])
    else: print('moved', c['id'], f['r'], '->', c['r']); f['r'] = c['r']
save(d, sys.argv[3])
