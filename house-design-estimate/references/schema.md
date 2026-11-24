# Design JSON schema

One JSON file is the single source of truth. The design page, the estimate, the checks and the previews are all
generated from it, so a change is made once (in the JSON) and every output follows.

Units are **inches**. Origin is the **south-west outer corner of the building**. **x grows east, y grows north**.
North in the JSON is plan north; `project.north_deg` says how far plan north is turned clockwise from true north
(0 when the plot is square to the compass). Feet-inch helper: 10'-6" = 126.

```jsonc
{
 "project": {
   "name": "My house",
   "location": {"city": "Sample city", "lat": 25, "lon": 0, "tz": 0},   // ASK the user; any country
   "codes": "codes_mycountry.json",  // ASK: file (beside the design or in data/) made from codes_template.json; "sample" = demo codes
   "north_deg": 0,                 // plan north vs true north, clockwise degrees
   "road": "S",                    // side(s) of the road: S, N, E, W
   "boundary": ["E", "W"],         // walls built on the plot boundary: no openings allowed, eccentric footings
   "plot": {"w": 240, "d": 1800},  // plot size (for gates, garden, site plan)
   "occupants": 6,                 // septic and water sizing
   "brief": "one paragraph of what the client asked for"
 },
 "building": {"w": 240, "d": 720},  // outer size of the building footprint
 "structure": {
   "wall_ext": 9, "wall_int": 4.5,  // brick thickness (9" outer, 4.5" partitions)
   "col": [12, 12], "beam": [9, 18], "slab": 5,
   "columns": [[6, 6], [101.25, 6], [234, 6, ["gf", "ff"]]],   // centres; optional 3rd item = levels it exists on
   "seismic": {"code": "NBC 105:2020", "Z": 0.30, "soil": "D", "I": 1.0, "R_mu": 4.0, "omega_u": 1.5}   // omit to use the codes file; base shear is computed for NBC 105 only
 },
 "levels": [                        // bottom to top; the last one is usually the roof
  {"id": "gf", "name": "Ground floor", "ffl": 24, "h": 132,   // ffl above ground (plinth), floor-to-floor height
   "rooms": [ROOM...], "doors": [OPENING...], "windows": [OPENING...],
   "fixtures": [FIXTURE...], "stairs": [STAIR...], "points": [POINT...],
   "walls": [[x, y, w, d]],         // optional extra wall rects (piers, short returns)
   "nowall": [[x, y, w, d]]},       // optional cuts where an auto wall must not be
  {"id": "rf", "name": "Roof", "h": 96, "roof_level": true, ...}  // roof_level: stair head + roof; skips soft-storey/torsion
 ],
 "stacks": [{"id": "S1", "x": 15, "y": 312, "levels": ["gf", "ff", "tf", "rf"], "box": [12, 12], "n": "Soil and vent stack"}],
 "services": {
   "exhaust": [{"room": "gf-wc", "via": "S1"}, {"room": "gf-kitchen", "via": "hood", "out": [30, 715]}],
   "water": {"ug_tank": {"x": 200, "y": 760, "l": 6000}, "roof_tanks": 2, "solar_hw": 300},
   "septic": {"x": 40, "y": 780}, "pv_kwp": 5.5, "battery_kwh": 5
 },
 "estimate": {"rates": "rates_myplace_2026.json",   // ASK: rate book made from rates_template.json; "sample" = demo rates
   "wh_extra": [{"label": "Lift pit reserve", "amount": 300000}], "pct": {"cont": 8}, "notice": "", "basis": ""},
 "vastu": {"enabled": true},        // ASK: true or false, no default
 "log": [{"date": "2026-11-24", "tag": "s1north", "change": "...", "impacts": "..."}]
}
```

Required before any build (the scripts stop and list what is missing): `project.location`, `north_deg`, `road`, `plot`,
`boundary` (`[]` for none), `occupants`, `codes`; `estimate.rates`; `vastu.enabled`. They must be the user's answers.

## ROOM
`{"id": "ff-master", "n": "Master bedroom", "short": "Master", "r": [x, y, w, d], "k": KIND, "use": USE,
  "open": ["e"], "rail": ["s"], "floor": "parq", "false_ceiling": 12, "sunken": 10, "note": "...", "elec": {"L": 4, "S": 5},
  "extra": [{"label": "Feature wall panelling", "qty": 120, "unit": "sq ft", "rate": 450}]}`

- `r` is the **brick-to-brick clear space** (inside faces of the walls), the size quoted on site. Leave the wall
  thickness as a gap between neighbouring rooms: 4.5 for a partition, 9 for an outer wall. Walls are generated in
  those gaps automatically; the outer shell comes from rooms whose edge is within 9" of the building edge.
- `k` (kind): `room`, `wet`, `stair`, `deck`, `terrace`, `court` (open courtyard / light well at ground), `void`
  (double-height or light-well opening in an upper slab), `roof`, `yard`. deck/terrace/roof make no walls; court/void
  get only the outer shell wall.
- `use`: living, master, bed, family, study, dining, kitchen, puja, store, hall, stair, wc, bath, ensuite, laundry,
  verandah, balcony, deck, terrace, court, void, roof, skylight, stairhead, garage. Checks and Vastu read `use`.
- `open`: sides (n/s/e/w) with **no wall** because the room runs straight into the next space. Use it only when the
  whole side is open; for a part-width opening use a door of type `arch`.
- `rail`: sides with a 1 m balustrade (balconies, voids, roofs). Every open edge more than 1 m above ground needs one.
- `sunken`: sunken-slab depth in inches for wet rooms on upper floors (drain fall check).
- `elec`: override auto electrical counts: L lights, F fans, S 10A sockets, P 15/20A points, AC, EX exhaust, O other.

## OPENING (doors and windows)
`{"o": "h", "at": 64.5, "a": 140, "b": 182, "type": "main", "hg": "a", "dir": 1, "h": 84}`
`{"o": "h", "at": 64.5, "a": 24, "b": 120, "type": "W1", "sill": 18, "head": 96}`

- `o`: `h` = in a wall running east–west (constant y), `v` = in a wall running north–south (constant x).
- `at`: the wall's centre line (y for h, x for v). For a 9" outer wall whose room edge is y=69, at = 64.5.
- `a`, `b`: start and end along the wall (x for h, y for v).
- Door `type`: `main`, `door` (internal), `bath`, `ext` (back/balcony solid), `slide` (sliding glass), `arch` (opening, no leaf).
  `hg` = hinge end (`a` or `b`), `dir` = swing side (+1 = towards +y for h / +x for v; −1 the other way), `h` height.
- Window `type`: `W` (casement, fully openable), `W1` (fanlight + fixed + sliding, ~40% openable), `W1-F` (fixed),
  `W1-S` (slider), `vent` (high vent), `fixed`, `louvre`. `sill`/`head` above the floor.

## FIXTURE (fittings and furniture)
`{"t": "shower", "r": [x, y, w, d], "z": 0, "h": 2, "lbl": "SH"}`
Types with built-in heights/colours: wc, basin, vanity, shower, tub, sink, bar_sink, counter, hob, fridge, wm, dw,
geyser (z 72), ac (z 84), mirror, bed, sofa, table, dtable, chair, desk, wardrobe, shelf, cupboard, tv, altar, rack,
plant, rug, tank, solar (PV array, give z), skylight, car. A fixture sits against a wall when an edge is within 2" of
the room edge; that wall is its "back" for clear-space, bed-head and cook-facing checks.
Wet fixtures (wc, basin, shower, tub, sink, wm, dw) are measured to the nearest stack on their level.

## STAIR
`{"id": "gf-st", "type": "dogleg", "rise": 6.286, "going": 10, "width": 42, "turn": "clockwise",
  "flights": [{"r": [x, y, w, d], "n": 11, "dir": "N"}, {"r": [...], "n": 10, "dir": "S", "z": 69.1}],
  "landings": [{"r": [x, y, w, d], "z": 69.1}]}`
`dir` = direction of travel going UP. `z` = height of the flight's base / landing top above this floor.
Total risers × rise must equal the floor-to-floor height. Put the same stair on every floor it serves.

## POINT (electrical and service gear)
`{"t": "DB", "x": 84, "y": 372, "n": "First-floor DB"}`  types: MS (meter + main switch), DB, INV, BAT, SI, DCI, NET, SA, AP, CCTV.

## Conventions that keep things consistent
- Ids: `<level>-<name>` for rooms (`ff-master`); doors/windows/fixtures get auto ids (`ff-D3`, `ff-W2`, `ff-shower5`)
  from their order. **Append new items at the end** of a list so existing auto ids do not shift between versions,
  or give them an explicit `id`.
- Keep every level's outer edge identical unless the floor really steps back.
- Stacks must sit in a pipe box, in a corner of a wet room or a shaft, and be in the same x, y on every level.

## Extra service and fixture keys
- `services.rw`: list of `{x, y, levels?}` rainwater pipes; if missing, one pipe per stack that reaches the top level.
- `services.water.rwh`: `[x, y]` rainwater-harvest tank; RW pipes run there first.
- Fixture `slide: false`: a wardrobe with swing doors (default is sliding, mirror on the first panel).
- Fixture `head: "N"|"S"|"E"|"W"`: the wall a bed head sits against (else the nearest wall); sets bedside sockets and switches.
