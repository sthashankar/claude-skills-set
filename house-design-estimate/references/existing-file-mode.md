# Changing an existing hand-built design file

Some projects already have a design page that was NOT generated from a design JSON, e.g.
`<project>/Design.html` (+ `Estimate.html`,
`Walkthrough.html`). Do not regenerate those from scratch: the client has approved hundreds of details in
them. Patch them, following the same preview → confirm → backup → apply → rebuild loop.

## How such a file is built (read before patching)
- One HTML file, ~500 KB: CSS, a 2D SVG engine (`Plan2D`, `buildSVG(key, opts)`), plan data, a three.js module for 3D
  (+ sun simulation `SunSim`, floor isolation, cutaway), the walk pane (`WK`, `walk_pane.js`), and detail tabs (`#dTabs`).
- Coordinates are inches from the SW outer corner, x east, y north. Plan data: `VIEWS4.gf/ff/tf/roof` with
  `rooms` (`{id, n, r:[x,y,w,d], k, note, dimtxt}`), `doors` (`{o:'h'|'v', at, t, a, b, hg, dir}`), `wins`, `furn`
  (`{t, r, n}`); services in `SVC[4]` (`ducts`, `rwpF/rwpB`, `cowls`, `eq`), Vastu rows `VAS`, light/air `LA`,
  columns `COLS4`. Middle-band rooms carry a `dy` shift, so read the live value, not the source literal.
- Patches are **runtime blocks** inserted just before `;return {setGF:v=>Plan2D_setGF(v),` (or before the previous
  patch's marker, e.g. `/* MYTAG1 <date>:`), each starting with a unique marker comment like
  `/* MYTAG2 <date>: ... */`. They find items by value and mutate them, plus exact string replacements of texts.
- 3D-only items (pipe boxes, cowls, fixtures3D, exposed3D, cctv3D, elec3D, plumb3D) live in the module script; patch
  their call sites by exact string replacement.

## Patch script pattern (`<project>/previews/apply_<tag>.py SRC DST`)
```python
import sys
src, dst = sys.argv[1], sys.argv[2]; h = open(src, encoding='utf-8').read()
assert 'MYTAG <date>' not in h                     # idempotent: refuse to apply twice
def rep(a, b):
    global h; assert h.count(a) == 1, (h.count(a), a[:90]); h = h.replace(a, b)   # every anchor must be unique
rep(";return {setGF:v=>Plan2D_setGF(v),", """
/* MYTAG <date>: one-line description of the change */
{const sh=VIEWS4.ff.furn.find(f=>f.t==='shower'&&f.r[0]===9&&f.r[1]===129); if(sh){sh.r=[9,153,36,36];}}
;return {setGF:v=>Plan2D_setGF(v),""")
open(dst, 'w', encoding='utf-8').write(h); print('ok')
```
1. **Preview**: run it with DST = a scratch copy, screenshot the 2D (and 3D) with `scripts/render.js`
   (`--eval` can click the floor button and call `HD`-like globals present in the file), save the PNG under
   `<project>/previews/<what>_preview.png`, send it, wait for "apply".
2. **Apply**: `cp` the live file to `<project>/backups/Design_pre-<tag>.html` (and the estimate to
   `Estimate_pre-<tag>.html`), then run the script with SRC = DST = the live file.
3. **Estimate**: edit the `const D={...}` JSON in the estimate file with a small script (`apply_<tag>_est.py`): add lines
   after the last `"id":"L10xx"` with the next free id, change `qty`/`rate`/labels in place, never renumber. Recompute
   the total (sum of lines × rate × finish multiplier + whole-house + % items) and quote old → new.
4. **Walkthrough**: `python3 <project>/walkthrough/build.py <project>/Walkthrough.html`
   (the plan file already contains the walk code; never re-run `integrate.py`).
5. **Verify**: load the page headless (route `cdn.jsdelivr.net/npm/three@0.160.0/*` to a local `npm pack three@0.160.0`;
   `render.js` does this), check for `PAGEERROR`, screenshot the changed floor in 2D and 3D.
6. **Texts**: search the file for every sentence that describes the old state (room notes, Vastu rows, "How it is laid
   out", standards rows, compromises list) and fix them in the same patch.
7. **Memory**: append to the matching project memory topic file (`<project>-*.md`) what was applied, the script,
   the backup name and the new estimate total; update the MEMORY.md index line.

## Converting an existing file to the JSON pipeline
If the client wants the new toolkit's checks/impact search on an old design, transcribe its `VIEWS4` data into a
design JSON (rooms → rooms, wins → windows with sill/head from the openings schedule, furn → fixtures, SVC ducts →
stacks, COLS4 → columns) with a small extraction script run in the page (`page.evaluate(() => JSON.stringify(VIEWS4))`),
then run `check_design.py` and `impact.py` on it. Keep the old file as the presentation copy until the client switches.
