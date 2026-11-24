# Change → impact matrix

Run `impact.py old.json proposed.json` for every proposal, then walk this table by eye: the script finds clashes, broken
rules, pipe-run changes and fixture moves it can compute, but it cannot judge comfort, smell, noise or buildability.
Always look at the **same spot on the floors above and below**, not only the floor being changed.

| You change | Re-check | Typical knock-on improvements to offer |
|---|---|---|
| A stack / pipe box / shaft | Every wet fixture on every floor it serves (run, fall, sunken-slab depth), vents and cowl, exhaust ducts that use the shaft, rainwater pipe sharing the box, beam/column it crosses, noise next to bedrooms, Vastu zone | Move showers/WCs/basins to sit beside it (e.g. **pipe box moved to the stair side → master shower moved to the NW corner beside it, shorter run, shower away from the door**); swap fixtures in a room; reuse freed corner for storage; shorter exhaust duct |
| A wet room | Rooms below (no WC over kitchen/puja/bed), sunken slab, waterproofing extents, exhaust/window, door swing (LHD outward/sliding), geyser zone, socket positions, Vastu zone | Stack it over another wet room; share a wall with the kitchen for a short hot-water run; level-entry shower |
| A fixture (WC, shower, basin, sink, WM) | Drain run to stack, clear space in front, door swing, geyser/socket zones, window above (privacy, splash), light point and mirror light, exhaust grille position | Rotate WC to the north–south axis (Vastu), shower into the corner farthest from the door, basin by the door |
| A door | Swing vs furniture and other doors, switch position (latch side, 1.0–1.2 m), circulation path, Vastu pada (main door), security, LHD 820 mm clear | Slide or reverse a door to free a wall for a wardrobe; move switches |
| A window | Light/vent %, cross-ventilation path, boundary wall rule, sun (use the sun slider), privacy, furniture under it (bed head, hob ≥ 300 mm), structure (opening near a column/corner, lintel vs beam soffit), restrictor on upper bedrooms | Fanlight for stack ventilation, sunshade depth, swap to W1 standard |
| A wall or room size | Spans and beam positions, columns inside rooms, furniture fit, door/window still on a wall, estimate quantities, Vastu zones of both rooms, leftover slivers | Align walls floor to floor for load paths; give the gained space to storage |
| A column or beam | Spans ≤ 4.5 m, floating columns, cantilevers, soft storey, column projections into rooms (furniture, wardrobes), pipe penetrations | Hide columns in wardrobes or pipe boxes |
| A stair | Rise/going/2R+G, headroom ≥ 2.0 m under landings, slab opening, what is under it (WC headroom, store), turn direction (Vastu clockwise), balustrade | Store or WC under the high end; skylight over the stair |
| Floor height | Stair risers (re-split), window heads vs beam soffit, ceiling heights, estimate (walls, plaster), elevations | |
| Electrical gear (DB, inverter, battery) | Not in bathrooms, battery ≥ 600 mm from DB and not in habitable rooms or escape paths, riser path, ventilation, access | Group gear in one service room with a louvre |
| Exhaust / hood route | Duct length ≤ 6 m with ≤ 2 bends, outlet ≥ 1.5 m from openable windows and the boundary, cowl ≥ 1 m above the parapet | Share the stack shaft; move the outlet away from bedrooms |
| Roof items (tanks, PV, skylight) | Structure under tanks (≈ 1 t per 1,000 L), shading on PV, Vastu (tanks SW), access, overflow route | |
| Anything | Estimate delta, walkthrough rebuilt, page text and notes still true, change log entry | |

## How to report impacts to the user
1. One line on the change itself.
2. **Problems the change creates** (with the fix you suggest).
3. **Problems it solves.**
4. **Improvements it now allows** — offer them as options, never apply them silently.
5. Cost delta.
Keep it short; put the long list in the preview message or the change log.

| Stack / pipe box next to a living room or bedroom | stack-noise warn; move the shower or WC so the stack sits on a wet or service wall, or line the box with acoustic lagging |
| Wardrobe swing blocks a walkway | set the wardrobe to sliding (default); `"slide": false` only when the clear way stays 750 mm |
