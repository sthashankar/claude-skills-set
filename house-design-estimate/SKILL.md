---
name: house-design-estimate
description: Design a house from a brief or a hand sketch into a 2D/3D/walkthrough design page and an editable estimate for any country, using the user's own building codes, currency and local rates (bundled codes and rates are samples only; Vastu optional). Asks for missing site, code and rate details before designing; previews, confirms and applies changes with impact checks.
---

# House design + estimate

Turns a client's brief, a hand sketch or an existing 2D plan into:
1. a **design page** (one HTML file): 2D plan per floor on the left, 3D model on the right with floor isolation and a
   sun simulation for the site, a first-person walk pane below (2D room click flashes the room in 3D and walks you
   into it; E opens doors, O/C all doors, L lights; sun slider runs sunrise to dusk with ▶ Play day, lights come on after
   dusk; layer toggles for plumbing, wiring, exhaust (2D plan, 3D and walk) and X-ray; colour schemes
   (5 presets + pickers for walls, slab, railings, frames, glass, doors, floors); Move furniture: drag, R rotate, Del
   delete, undo, with a live walkway check that outlines in red any piece that cuts the 750 mm way to a door or
   stair; then "Copy my changes" gives JSON for `apply_furn_edits.py`). Controls: Floor (levels + All + roof, show floors
   below) · 3D camera (front from the road, back, sides, top) · straight-on elevations · Sun and shadows (real sun, 21st of each
   month, Play day, sun chart, sunrise/noon/sunset line, lights) · Finishes · Show (furniture, move furniture, room names
   3D, dimensions, Vastu zones, columns and beams, electrical, colour by room type/Vastu zone/daylight, plumbing, exhaust,
   light and air, site 3D with plot wall, gate and road, cutaway with floors spread apart, X-ray, Comments). Cut walls and columns show dark cut faces (cutaway at 4', one floor at 7'). Comments: tick it, click the 2D plan, type a note; pins are numbered per floor, kept in the browser, and "Copy all for chat" gives one list (floor, room, position from the SW corner, text) to paste back into the chat and act on. The 2D plan zooms (wheel, pinch, + / − / Fit) and pans (drag) and shows dimensions:
   opening chain, room chain and overall size on every face, D/W width tags, room clear sizes and furniture sizes, and tabs for rooms, all checks, structure, plumbing/electrical/exhaust, light and air, Vastu, standards
   and the change log;
2. an **estimate page** (one HTML file): the project's currency, every room's lines (qty × rate) taken off the drawing,
   whole-house items, fees and reserves, finish levels, CSV export, user edits saved in the browser;
3. and, for every later change, a **before/after preview** plus an **impact report** that lists what the change
   breaks, what it fixes and which knock-on improvements it opens up.

The workflow rules below come from real design decisions. The bundled **codes and rates are only a sample**: they never
apply to a project by default.

## Toolkit
Scripts, templates, sample data and references live beside this file; paths below are relative to this folder. Needs python3 and, for PNGs, node + Playwright
(`render.js` serves three.js locally when the CDN is blocked).

| Script | Does |
|---|---|
| `scripts/make_all.py design.json OUT [--png]` | design page + estimate + checks + per-floor PNGs |
| `scripts/check_design.py design.json [--md f]` | rule checks: clashes, sizes, light/air, structure, MEP, safety, Vastu |
| `scripts/impact.py old.json new.json [--md f] [--all]` | what changed, new problems, solved problems, knock-on moves, pipe-run and daylight changes, things within 10 ft (floor above/below too), cost delta |
| `scripts/preview.py old.json new.json out.png [--levels ff] [--3d out3d.png] [--title t]` | side-by-side Now/Proposed 2D with changes outlined in orange, optional 3D close-up with walls cut at 5 ft |
| `scripts/apply_change.py design.json proposed.json OUT --tag t --change "..."` | backup → swap in → change log → rebuild all → cost delta |
| `scripts/mep3d.py` (used by build_design) | doors that open/slide, ceiling lights + fans (counts = estimate), switches by the latch side, twin sockets at accessible heights, DB/inverter gear, drains to stacks/gullies/septic, cold/hot water, exhaust fans + ducts to stacks or hood outlets, wiring runs |
| `scripts/apply_furn_edits.py design.json changes.json proposed.json` | turns the page's "Copy my changes" furniture JSON into a proposed design; then Workflow C (impact, preview, confirm, apply) |
| `scripts/paths.py` (used by check_design + the page) | walkway check: a 750 mm clear way (warn) / 500 mm (fail) from the main door or stair to every door and stair, naming the furniture that blocks it |
| `scripts/build_design.py`, `scripts/build_estimate.py ... --compare old_summary.json`, `scripts/render.js` | single steps |

Read `references/schema.md` before writing any design JSON. Other references: `standards.md` (the sample's NBC + NCC/AS numbers),
`vastu.md`, `impact-matrix.md` (change → what to re-check), `estimate.md`, `existing-file-mode.md` (patching a
hand-built file). `examples/sample_house.json` (20' × 60' G+2 with light well) and `examples/sample_40x70.json` (36' × 54' house on a 40' × 70' plot, G+1) are complete houses to copy from.

## Intake gate: ask before designing (every workflow, every country)
Do not zone, draw, write the design JSON or price anything until each item is answered by the user or the user says
"use your default" for it. Read the brief, sketch and project memory first; ask only for what is missing, in **one
message**, with a suggested default beside each question (no default for location, codes or rates: these must be chosen).

1. **Place**: city/state/country, and latitude, longitude, time zone (look these up from the city and confirm).
2. **Plot**: size and shape, road side(s), true north, slope, boundary walls, setbacks and coverage/height limits.
3. **Building codes**: which national, state and municipal codes apply and which edition; any extra best practice wanted
   on top; seismic zone, wind, snow, flood, frost, bushfire/wildfire and termite exposure as relevant; who signs off locally.
4. **Construction system**: RCC frame with brick, loadbearing masonry, timber/steel frame, etc.; local materials and wall thickness.
5. **Rates**: currency, tax basis, and the user's rate book, BOQ or quotes (with date). Or: should you research local rates
   for them to confirm, or use the sample numbers purely as a demo?
6. **Household and rooms**: occupants, storeys, floor height, bedrooms and who uses them, bathrooms, kitchen, parking,
   stair, accessibility, outdoor space, cultural needs (Vastu, puja, prayer room, feng shui, etc. Ask, never assume).
7. **Services**: water, sewer or septic, mains voltage, gas, solar, battery, heating/cooling, data.
8. **Budget and finish level**, units the user reads (feet-inches or metric), language, big appliances with real sizes.

If some answers are still missing, ask again for just those; never fill a gap with a sample
value. Items the user defaults go into the reply as an "Assumptions" list and into project memory. The scripts enforce the core of
this: `make_all.py`, `build_design.py`, `build_estimate.py` and `apply_change.py` stop and print the open questions when
`project.location/north_deg/road/plot/boundary/occupants/codes`, `estimate.rates` or `vastu.enabled` is not set.
Never write a placeholder into the JSON just to get past the gate.

## Country setup: codes and rates
- **Codes**: copy `data/codes_template.json` to `codes_<country or state>.json` beside the design and set `project.codes` to it. Fill each
  limit from the code text, edition and clause the user supplies, or that you find in an official source and the user
  confirms; put the clause in `refs`. Leave unknowns `null`: that check is skipped and the report says NOT CHECKED.
  Never borrow another country's number. Show the filled table to the user before the first build, and say that
  local licensed professionals must verify it. `"codes": "sample"` (a mixed demo set) is only for
  demos, or a project whose user confirms those codes.
- **Rates**: copy `data/rates_template.json` to `rates_<place>_<year>.json`, set `estimate.rates` to it, set the currency and fill in prices
  with their quote or source. `0` = not applicable; `null` = unknown, and the estimate stops and lists what it needs.
  Never convert the sample rates by exchange rate. `"rates": "sample"` needs the user's explicit OK; the page is then
  labelled SAMPLE RATES, and you say so every time you quote a total.
- **Structure**: openings only fit walls up to 13.5" thick; the column, beam and slab checks are for RCC frames. For
  other systems leave `structure.columns` empty and those limits `null`, and tell the user structure is not checked.
- **Units**: the JSON is in inches and the pages show feet-inches and sq ft (some checks in metric). Convert for metric users in chat
  and say that the pages are still in feet. Enter rates per sq ft / running ft (per m² ÷ 10.764, per m ÷ 3.281).

## Golden rules (the client's standing preferences)
1. **Never put prices on the design page.** Costs go only in the estimate file (and in chat when the user asks).
2. **Never change the design or estimate files until the user confirms.** First restate your understanding of the
   request plus any problems you see (headroom, structure, Vastu, cost), then propose.
3. **Always show a 2D preview image before applying** (`preview.py`), a 3D close-up when it helps. Save previews under
   the project's `previews/` folder and attach them.
4. **Back up before every change** (`apply_change.py` does it: `backups/<file>_pre-<tag>.*`).
5. **After every change, chase the knock-ons**: run `impact.py`, then walk `references/impact-matrix.md` by eye for
   plumbing, electrical, exhaust, structure, light/air, Vastu, furniture clashes and the floors above and below.
   Offer the improvements the change makes possible as options. Example: moving the front-west pipe
   box to the stair side to take noise out of the living room also put it right beside the master ensuite's
   north-west corner, so the shower could move north into that corner — shorter drain, wet zone away from the door.
6. **On apply, update everything**: estimate (quote old → new total), design page, walkthrough, page texts and notes
   that described the old state, change log, and project memory.
7. Each decision the user makes stays made: do not re-propose an option they declined (keep a "declined" list in memory).
8. Follow the **project's own codes** (`project.codes`) plus any best practice the user asked for, adapted to local materials
   and trades. Cite only those codes. Concept stage only: say that structure, MEP sizing and approval need locally licensed
   professionals. NBC and AS/NZS numbers in this skill belong to the sample.

## Subagent team
Every workflow runs through four subagents, using the prompts in `references/agents/`. Spawn each as a general-purpose
agent (researcher and reviewer may use Explore): give it that file's full text, the absolute path of this skill folder, the project folder,
the file names and everything it needs from the chat, since it sees nothing else. Run independent lookups as parallel researchers.

| Role | Prompt | Used in |
|---|---|---|
| Researcher | `researcher.md` | A1 and B4 (lat/long, code clauses, hazards, rates if asked) |
| Architect | `architect.md` | A2, C1 (zoning, grid, cores, room schedule, knock-ons) |
| Builder | `builder.md` | A3–A4, A6, B3, C2–C3, C5 (JSON, checks, renders, previews, apply) |
| Reviewer | `reviewer.md` | after every builder step, before anything goes to the user |

The main session keeps everything that touches the user: the intake gate, reading the sketch, restating requests,
every confirmation, replies and project memory. Subagents never ask the user anything; when one reports an open
question or a "not found", the main session asks the user. Loop builder → reviewer for must-fix issues up to 2
rounds, then show the user what is left. Show the user only the reviewed results, and do not paste raw agent reports.

## Workflow A: new design from a typed brief
1. **Intake gate** (above): pull what you can from the brief, ask for everything missing in one message, then **stop and
   wait**. Do not start step 2 until the answers are in. Then do the country setup and have the user confirm it.
2. **Zoning first.** Decide bands and grids before rooms: structural grid (spans within the code's limit, columns lined up on every
   floor), one or two wet cores stacked floor over floor with stacks in pipe boxes beside pillars and away from
   bedroom/living walls, stair position and turn, light well / courtyard where the plan is deep. Only if the user wants Vastu: light well centre or NE,
   kitchen SE or NW, master SW, puja NE, toilets W/NW. Orient for the site's hemisphere and climate. A 20'-wide terrace house needs a light well; a deep plan needs cross-ventilation
   north–south.
3. **Write the design JSON** (copy `examples/sample_house.json`): rooms as brick-to-brick rects with wall gaps, every
   door and window, fixtures and furniture at real sizes, stairs with risers that add up, columns, stacks, exhaust
   routes, electrical gear, water/solar/septic. Copy the geometry pattern only: replace the sample's location, `codes`, `rates`,
   `vastu` and `seismic` with the user's answers.
4. **Self-check loop (repeat until clean)**: `check_design.py` → fix every **fail**; fix or justify every **warn**;
   render the PNGs and LOOK at each floor (labels inside rooms, doors swing the sensible way, nothing floating,
   walls where you expect, stair arrives where the hall is); compare each wet room with what is above and below;
   sanity-check the estimate against a local cost per area from the user or a cited local source (not the sample rates).
5. **Show the 2D plans** (all floors in one message) with a short "how it works" and the open compromises. Wait for
   the user's yes or edits before building the full page.
6. **Build** with `make_all.py`, check the page loads without errors (`render.js` prints PAGEERROR), screenshot the 3D
   once, then deliver both HTML files plus the floor PNGs.

## Workflow B: from a hand sketch or an existing 2D plan
1. Read the image carefully (zoom/crop if needed). Write down every number you can read, which walls are outer, the
   scale (from a written dimension, door widths ≈ 3'-0", or a known plot size), where north and the road are.
2. List what is unclear (illegible numbers, rooms that do not add up to the plot, missing stairs/windows) and your
   assumption for each.
3. Transcribe into a design JSON, render the 2D, and send it **next to the sketch** with: "This is how I read your
   sketch — please check sizes and positions", plus the assumptions and the check results that matter (e.g. stair too
   steep, room under minimum, WC over the kitchen). Do not "improve" the layout silently: offer improvements separately.
4. Ask the intake-gate questions the sketch does not answer in that same message. After the user confirms the reading **and**
   answers them, continue with Workflow A steps 4–6.

## Workflow C: a change request
1. Restate the request in one or two sentences and name any problem with it (headroom, span, Vastu, a fixture it
   displaces). If it can be read two ways, say which reading you chose.
2. Copy the JSON to `proposed.json`, make the change (append new items at the end of lists so auto ids stay stable).
3. `impact.py current.json proposed.json --md impact.md` and `preview.py ... --3d ...`. If the change creates new
   fails, fix them in the proposal or present them as a choice.
4. Send: the preview image(s), what changes, new problems + your fix, problems solved, **knock-on improvements now
   possible** (as options), cost delta. Then stop and wait.
5. On "apply" (or a pick on a decision card): `apply_change.py ... --tag <short-tag> --change "..." --impacts "..."`,
   confirm the page loads, send the applied picture and the new estimate total in one short message.
6. If the user picks a knock-on improvement, that is a new change: preview it the same way unless they said "just do it".

## What a complete design covers (use as the review list)
Use what fits the project; standards and fittings named here come from the sample code set, so swap in the local ones.
Structure grid and column sizes, seismic notes, boundary footings · room sizes on finished faces, heights, stair
(rise/going/headroom/turn) · wet cores stacked, sunken slabs for level-entry showers, AS 3740 waterproofing, drain
runs and vents, exhaust routes to roof cowls, rainwater pipes hidden in pipe boxes with overflow scuppers · service
room for meter/DB/RCDs/SPD/inverter/battery/network cabinet, riser, RCD on every circuit, smoke alarms, sockets at
accessible heights · solar PV + hybrid inverter, solar hot water, UG + roof tanks with pressure pump, rainwater harvesting,
septic + soak pit · light well / skylight with louvres, cross-ventilation, sun study (shading, chajjas), window
standard (e.g. W1 = fanlight + fixed + sliding, fixed mesh), 125 mm restrictors upstairs · furniture and appliances at
real sizes with clear spaces and 750 mm walkways to every door and stair (never block a path), wardrobes and joinery · Vastu check with remedies · LHD step-free entry, outward/sliding
WC door, Grade A glass · CCTV, Wi-Fi APs per floor, Cat6 riser · LPG cage outside with copper line · dust control,
finishes, termite barrier · estimate per room with whole-house items and reserves.

Lessons learned (check every design, adapted to local practice): beams shown on the 2D plan between columns · switches inside wet rooms at the
latch side, mirror socket beside each basin · bedside twin socket + two-way switch each side of the bed head · PIR
sensors on halls, passages and stairs, two-way/three-way switching along paths · twin 10 A sockets · utility meter on the GF
road-side face · RW pipes = max(2, roof m²/80), hidden in pipe boxes with scuppers · stacks never on a living or bedroom
wall (move the shower instead) · use the space under the first stair flight · sliding wardrobe doors where a swing
would block the walkway. · every wall between two rooms is really there in 2D and 3D: an opening only cuts the wall
it runs along (checks wall-missing and opening-cuts-wall fail otherwise); every lit room has its light + fan switch INSIDE at
the door you enter by (latch side, 1.1 m; check switch-entry), bedside two-way only as an extra, a second hall door
gets a two-way, ensuite/wardrobe doors don't · look at each floor in 2D and 3D before
sending, and compare against the client's drawing room by room when converting an existing plan.

## Replies
Lead with the result or the decision needed. Short sentences, key numbers in bold, the project's currency and number format
(e.g. 1,234,567 or 12,34,567), feet-inches or metric as the user prefers. Times in the user's
local time. One proposal per message; put long lists in the attached report, not the chat.

## Project memory
Save what a later session must not re-ask: chosen plan and file names, site facts (location, north, boundary walls), codes file and edition, rate book, date and currency,
appliances, the user's preferences, every applied change with its tag, backup and estimate total, and options the
user declined. One topic file per subject.
