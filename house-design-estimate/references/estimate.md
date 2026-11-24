# Estimate method

`build_estimate.py` writes an editable estimate page: floor tabs, one
collapsible block per room with every line (qty × rate), whole-house items, fees and reserves, finish level
(economy ×0.88 / standard / premium ×1.30 on finish lines), optional loose furniture, "Copy as CSV", and the user's own
edits saved in their browser. It also writes a summary JSON used for the cost delta of every change.

## Quantities (all from the design JSON)
- Structure lines on the **brick-to-brick** area by room kind (`sHab`, `sWet`, `sStair`, `sDeck`, `sCourt`); roofs get
  `bRoof` (insulation + membrane + tiles) instead.
- Floors, ceilings, waterproofing on **finished** (plaster-to-plaster) area: brick size minus ½" plaster per walled side.
- Wall paint = finished perimeter × ceiling height − openings − tiled area. Wet rooms tiled to 7'-0"; kitchen
  splashback 2'-0" × counter run.
- Ceiling type by use: false ceiling in living/bedrooms/dining, moisture-proof board in wet rooms, plain elsewhere.
- Doors by type (main, ext, internal, bath, sliding by area); windows by type and by whether they face outside
  (W1, outer aluminium, inner aluminium, fixed). Each opening is priced once, in the indoor room it serves.
- Electrical points from room use and area (lights ≈ 1 per 80 sq ft, fans in habitable rooms and kitchen, sockets by
  use, 15/20 A for kitchen/WM/DW, AC/exhaust/TV/geyser/chimney from fixtures, smoke alarms per bedroom floor).
  Override per room with `elec`.
- Plumbing and fittings from fixtures (WC, basin + vanity + mirror cabinet, shower + screen + TMV, tub, sinks, WM,
  geysers), joinery (wardrobes by face area, counters and wall cabinets by running ft), AC units by room size.
- Balustrades by rail length; stair balustrade by flight length; parapets on roofs.
- Whole-house items are formulas: plinth fill by footprint × plinth height, septic by occupants, tanks by litres,
  PV per kWp, battery per kWh, DBs per floor, external paint by outer wall area (halved when E and W are on the
  boundary), sunshades by outside window width, boundary footings per boundary wall length, RCD count, pipe boxes per
  stack-level, window limiters from the checks. Add one-offs in `estimate.wh_extra`.
- Fees and reserves (% of subtotal): from the rate book (sample: design 2.5, supervision 1.5, contingency 8, escalation 6). Override in `estimate.pct`.

## Rates
The rate book is the user's: named in `estimate.rates`, made from `data/rates_template.json` with their currency, tax
basis and quotes. All prices (unit rates, whole-house `fixed` amounts, loose furniture and percentages) are in it; none are in the code.
A price the design needs but the book leaves `null` stops the build and is listed as a question for the user. Labels fall
back to the template, prices never do. Never convert one country's rates by exchange rate.

`data/rates_sample.json` is **only a sample** in a neutral currency (¤), used when the design says `"rates": "sample"` after the
user's explicit OK. Pages built with it are labelled SAMPLE RATES; repeat that in every reply that quotes a total.

## Every time the design changes
Rebuild the estimate, compare summaries (`build_estimate.py ... --compare old_summary.json`) and quote the delta in
the project's currency (a change of currency is reported, never compared). Record the new total in the change log and in project memory.
