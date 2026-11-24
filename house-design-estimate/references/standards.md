# Standards and rules of thumb

**Every number on this page is the sample code set** (`data/codes_sample.json`, a demo
set from mixed standards). Use it only when the user confirms these codes.
For any other country or code, fill a copy of `data/codes_template.json` with the user: see "Country setup" in SKILL.md.
The table's topics are a good list of what to look up locally, plus frost depth, snow, wind/cyclone, flood, wildfire, radon,
energy code, egress windows, garage fire separation and insulation where they apply.

Numbers are concept-stage screens; local licensed professionals and the approving authority have the final word.
`check_design.py` automates the ones marked ✓, with limits read from the project's codes file.

## Structure, rooms and municipal bylaws (sample: NBC)
| Topic | Rule | Auto |
|---|---|---|
| Seismic (NBC 105:2020) | Z by location (from the code's table), soil type A–D, I = 1.0 houses, RC MRF Rμ = 4, Ωu = 1.5. Base shear Cd(T)·W | ✓ indicative |
| Regularity (NBC 105 §5) | Avoid L/B ≥ 3, re-entrant corners > 15%, soft storey (GF wall length < 70% of above), torsion (mass/stiffness offset > 10%), slab openings > 50%, floating columns | ✓ |
| RC rules of thumb (NBC 205) | Columns ≥ 300×300 (350×350 now usual for G+2), spans ≤ 4.5 m, beams ≥ 230×355 / depth ≥ span/12, slab ≥ 125 mm, cantilever ≤ 1.0 m, storey height ≤ 3.2 m, columns line up floor to floor, 135° hooks, ties at 100 mm near joints | ✓ partly |
| Boundary walls | Walls on the plot boundary: no windows, doors or vents; eccentric footings with strap beams or raft | ✓ |
| Rooms (NBC 206) | Habitable ≥ 9.5 m² and ≥ 2.4 m wide, ceiling ≥ 2.75 m; kitchen ≥ 5 m², ≥ 1.8 m; bath ≥ 1.8 m², ≥ 1.2 m; WC ≥ 1.1 m², ≥ 0.9 m | ✓ |
| Light and air (NBC 206) | Windows ≥ 1/10 of floor for light, ≥ 1/20 openable | ✓ |
| Bylaws (check the municipality) | Setbacks from road, ground coverage %, FAR, height vs road width (light plane), parking, septic distance from wells (≥ 15 m) | manual |
| Fire (NBC 107) | Escape route from every bedroom to the stair, no locks needing a key from inside, LPG outside | manual |
| Sanitary (NBC 208) | Every trap vented; septic 3 chambers + soak pit; inspection chamber at every change of direction | partly |

## Best practice (sample: NCC 2022 Vol 2 / ABCB Housing Provisions + AS/NZS)
| Topic | Rule | Auto |
|---|---|---|
| Stairs (H5D2) | Rise 115–190 mm, going 240–355, 2R+G 550–700, ≤ 18 risers a flight, open risers < 125 mm gap, handrail 865 mm | ✓ |
| Balustrades (H5D3) | Where fall > 1 m: 1 m high, gaps < 125 mm, no climbable rails 150–760 mm above floor if fall > 4 m | ✓ (presence) |
| Window restrictors (H5D4) | Bedroom openable windows with sill < 1.7 m and floor > 2 m above ground: 125 mm limiter or screen | ✓ |
| Heights (H4D4) | Habitable ≥ 2.4 m, wet/hall ≥ 2.1 m | ✓ via NBC |
| Light (H4D6) / vent (H4D7) | Glazing ≥ 10% floor, openable ≥ 5%; bath exhaust 25 L/s, kitchen 40 L/s ducted outside | ✓ |
| Wet areas (AS 3740) | Shower floor + walls to 1.8 m waterproofed, whole bathroom floor membrane on upper floors, falls 1:60–1:80, upturns, step-free shower needs sunken slab ≥ 50 mm + linear grate | ✓ (sunken) |
| Wiring (AS/NZS 3000) | 30 mA RCD on every final circuit, SPD, earth pit, bathroom zones: no switchgear in zone 0–2 (0.6 m from shower/tub), geyser outside 0.6 m, DB not in a bathroom | ✓ |
| Smoke alarms (AS 3786, H3D6) | Interconnected 230 V with battery backup, in the hall outside each bedroom group and on every storey | ✓ (reminder) |
| Plumbing (AS/NZS 3500) | Grades ≥ 1:60 for 100 mm, ≥ 1:40 for 40–65 mm; vent long branches; TMV 50 °C to bath outlets; backflow + pressure-limiting valve; ORG below the lowest fixture; cleanouts at stack bases | ✓ (runs) |
| Gas (AS/NZS 5601.1) | LPG cylinders outside in a ventilated cage, hob ≥ 200 mm from a window edge (300 used as a screen), flued/ducted hood | ✓ |
| Solar and battery (AS/NZS 5033, 4777, 5139) | PV DC isolators, battery not in habitable rooms or escape paths, ≥ 600 mm clear from DB / appliances, ventilated | ✓ |
| Termites (AS 3660) | Chemical + physical barrier at slab edges and pipe penetrations | estimate |
| Glass (AS 1288) | Grade A safety glass in doors, sidelights, low windows (< 500 mm sill), shower screens | manual |
| Access (Livable Housing Design) | Step-free entry (ramp ≤ 1:14), 820 mm clear entry door, one WC on entry level with outward/sliding door, reinforced walls for grab rails | ✓ partly |
| Energy (H6) | Roof insulation (R3+), shade east/west glass, cross-ventilation, low-E glass where it helps, light-coloured roof | manual + estimate |

## Climate notes
Work out the project's own climate and hemisphere: sun path, rainy season, wind, cold, flooding. Shade low morning and
evening sun, use equator-facing glass with a sized overhang, keep cross-ventilation where it is hot and insulation and
airtightness where it is cold, raise the plinth where it floods, and add mosquito mesh, termite and damp protection as needed.

## Not automated (always look by eye)
Daylight to the back of deep rooms, privacy from neighbours, noise from stacks next to bedrooms, smell routes from WCs
to kitchens, headroom under stairs and beams (≥ 2.0 m), door hardware clearances, furniture you can actually carry up
the stair, where water goes when a tap is left on, maintenance access to every tank, pump, valve and pipe box.

## Walkways (furniture)
- 750 mm clear way to every door and stair (warn below), 500 mm = blocked (fail); 900–1000 mm on main routes (LHD). Checked by scripts/paths.py on a 3" grid; live in the page while moving furniture.

## Electrical layout (sample: AS/NZS 3000 adapted)
- RCD (30 mA) on every final circuit; SPD at the main DB; utility meter on the ground floor road-side face.
- Wet rooms: light/fan switch inside the room at the latch side, IP-rated; one mirror socket beside each basin, outside zone 1.
- Bedrooms: twin socket at 600 mm and a two-way light switch at 850 mm each side of the bed head.
- Halls, passages and stairs: PIR sensor plus two-way or three-way switching at each end.
- General outlets: twin 10 A sockets at 300 mm (kitchen bench 1100 mm, own circuit -K; laundry -W).

## Rainwater
- Downpipes: at least max(2, ceil(roof area m² / 80)); hidden in pipe boxes, each roof outlet with an overflow scupper.
- Run to the rainwater-harvest tank (services.water.rwh), else the UG tank inlet filter, else the drain.

## Switch at the entry (accessibility)
- Every lit room: a switch plate inside the room on the latch side of the entry door, 150–300 mm from the frame, 900–1100 mm up (LHD / AS 1428.1 reach range), controlling the main light and the fan, so the room is lit before you step in.
- The entry door is the one from a hall, passage, lobby, stair or living space, even when the door sits at a wall junction.
- Bedside two-way switches are extra, never a replacement. A second door from circulation gets a two-way switch; ensuite and wardrobe doors don't.
